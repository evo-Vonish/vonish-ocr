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
    env["VONISH_HOME"] = str(root)
    env.setdefault("VONISH_STATE_DIR", str(root / ".vocr" / "cli"))
    env.setdefault("VONISH_ADMIN_DIR", str(root / ".vocr" / "admin"))
    env.setdefault("VONISH_QUEUE_UPLOAD_DIR", str(root / ".vocr" / "queue_uploads"))
    env["VONISH_IGNORE_CONSOLE_SIGNALS"] = "1"
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
    return proc.pid


def ensure_service(port=8000):
    status = read_status()
    probe_port = status.get("port") or port
    try:
        VonishOCRClient(service_url(probe_port)).health()
        return probe_port
    except Exception:
        pass
    start_service(port=port, foreground=False)
    return port


def stop_service():
    status = read_status()
    pid = status.get("pid")
    if pid:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            if is_pid_alive(pid):
                os.kill(pid, signal.SIGTERM)
    pid_file().unlink(missing_ok=True)
    port_file().unlink(missing_ok=True)
    return pid


def _creation_flags():
    if os.name == "nt":
        create_no_window = 0x08000000
        create_new_process_group = 0x00000200
        return create_no_window | create_new_process_group
    return 0
