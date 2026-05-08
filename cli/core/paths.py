from pathlib import Path


def app_state_dir() -> Path:
    base = Path.home() / "AppData" / "Local" / "VonishOCR" / "cli"
    base.mkdir(parents=True, exist_ok=True)
    return base


def pid_file() -> Path:
    return app_state_dir() / "serve.pid"


def port_file() -> Path:
    return app_state_dir() / "serve.port"


def log_file() -> Path:
    logs = Path.cwd() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs / "cli-serve.log"
