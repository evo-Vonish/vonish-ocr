"""Standalone YAML/JSON config loader with SIGHUP reload support."""
import json
import os
import signal
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # PyYAML is optional in this project.
    yaml = None


class Config:
    def __init__(self):
        self.path = Path(os.environ.get("VONISH_CONFIG", "./config.yaml"))
        self.data: dict[str, Any] = {}
        self.load()

    def load(self):
        if not self.path.exists():
            self.data = {}
            return
        text = self.path.read_text(encoding="utf-8")
        if self.path.suffix.lower() == ".json" or yaml is None:
            self.data = json.loads(text) if text.strip() else {}
        else:
            self.data = yaml.safe_load(text) or {}

    def reload(self) -> bool:
        old = dict(self.data)
        try:
            self.load()
            self._validate()
            self._apply_dynamic()
            return True
        except Exception as exc:
            self.data = old
            raise RuntimeError(f"Config reload failed, rolled back: {exc}") from exc

    def _validate(self):
        perf = self.data.get("performance", {})
        if int(perf.get("batch_size", 1)) < 1:
            raise ValueError("performance.batch_size must be >= 1")
        if int(perf.get("max_concurrent", 1)) < 1:
            raise ValueError("performance.max_concurrent must be >= 1")

    def _apply_dynamic(self):
        """Apply dynamic values only.

        Model paths and engine registrations are intentionally static. Callers
        can read updated values and apply queue/performance knobs in memory.
        """

    def get(self, key: str, default=None):
        return self.data.get(key, default)


config = Config()


def register_sighup():
    if not hasattr(signal, "SIGHUP"):
        return

    def handler(signum, frame):
        try:
            config.reload()
            print(f"[Config] Reloaded at {time.time()}")
        except Exception as exc:
            print(f"[Config] Reload failed: {exc}")

    signal.signal(signal.SIGHUP, handler)
