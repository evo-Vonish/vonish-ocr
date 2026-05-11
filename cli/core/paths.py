from pathlib import Path
import os


def app_state_dir() -> Path:
    candidates = []
    if os.environ.get("VONISH_STATE_DIR"):
        candidates.append(Path(os.environ["VONISH_STATE_DIR"]))
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "VonishOCR" / "cli")
    candidates.append(Path.home() / ".vonishocr" / "cli")
    candidates.append(Path.cwd() / ".vocr")

    for base in candidates:
        try:
            base.mkdir(parents=True, exist_ok=True)
            marker = base / ".write-test"
            marker.write_text("ok", encoding="utf-8")
            marker.unlink(missing_ok=True)
            return base
        except Exception:
            continue

    raise RuntimeError("No writable CLI state directory found. Set VONISH_STATE_DIR to a writable path.")


def pid_file() -> Path:
    return app_state_dir() / "serve.pid"


def port_file() -> Path:
    return app_state_dir() / "serve.port"


def log_file() -> Path:
    root = Path(os.environ.get("VONISH_HOME", Path.cwd()))
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs / "cli-serve.log"
