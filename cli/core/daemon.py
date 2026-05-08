import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .client import VonishOCRClient
from .paths import log_file, pid_file, port_file


def project_root() -> Path:
    env_root = os.environ.get("VONISH_HOME")
    if env_root:
        return Path(env_root)
    here = Path(__file__).resolve()
    for parent in [*here.parents, Path.cwd()]:
        if (parent / "backend" / "main.py").exists():
            return parent
    return Path.cwd()


def read_status():
    pid = None
    port = None
    if pid_file().exists():
        try:
            pid = int(pid_file().read_text(encoding="utf-8").strip())
        except Exception:
            pid = None
    if port_file().exists():
        try:
            port = int(port_file().read_text(encoding="utf-8").strip())
        except Exception:
            port = None
    return {"pid": pid, "port": port}


def is_pid_alive(pid):
    if not pid:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            creationflags=_creation_flags(),
        )
        return str(pid) in (result.stdout or "")
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def service_url(port=None):
    port = port or read_status().get("port") or 8000
    return f"http://127.0.0.1:{port}"


def wait_ready(port, timeout=120, pid=None):
    client = VonishOCRClient(service_url(port))
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if pid and not is_pid_alive(pid):
            raise RuntimeError(f"service process exited before ready: pid={pid}")
        try:
            client.health()
            return True
        except Exception as exc:
            last = exc
            # FastAPI may answer 503 while lifespan startup is still loading models.
            # Treat every HTTP/connection failure as transient until the process exits
            # or the deadline is reached.
            time.sleep(0.5)
    if last:
        raise RuntimeError(f"service not ready: {last}")
    return False


def start_service(port=8000, foreground=False, profile=None):
    root = project_root()
    env = os.environ.copy()
    env["VONISH_PORT"] = str(port)
    if profile:
        env["VONISH_PROFILE"] = profile
    script = root / "backend" / "main.py"
    cmd = [sys.executable, str(script), "--sidecar"]
    if foreground:
        return subprocess.call(cmd, cwd=str(root), env=env)

    log = open(log_file(), "a", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=str(root), env=env, stdout=log, stderr=log, creationflags=_creation_flags())
    pid_file().write_text(str(proc.pid), encoding="utf-8")
    port_file().write_text(str(port), encoding="utf-8")
    try:
        wait_ready(port, timeout=120, pid=proc.pid)
    except Exception:
        if is_pid_alive(proc.pid):
            stop_service()
        raise
    pid = proc.pid
    if os.name == "nt":
        # The service intentionally outlives this CLI process. Close our handle
        # after startup so later taskkill/stop does not make Popen.__del__ print
        # an ignored WinError 6 traceback.
        try:
            proc._handle.Close()
            proc._child_created = False
        except Exception:
            pass
    return pid


def ensure_service(port=8000):
    status = read_status()
    if status["pid"] and is_pid_alive(status["pid"]):
        try:
            VonishOCRClient(service_url(status["port"])).health()
            return status["port"]
        except Exception:
            pass
    start_service(port=port, foreground=False)
    return port


def stop_service():
    status = read_status()
    pid = status.get("pid")
    if pid and is_pid_alive(pid):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGTERM)
    pid_file().unlink(missing_ok=True)
    port_file().unlink(missing_ok=True)
    return pid


def _creation_flags():
    if os.name == "nt":
        return 0x08000000
    return 0
