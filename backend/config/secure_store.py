import base64
import ctypes
import json
from ctypes import wintypes
from pathlib import Path
from typing import Optional


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


class SecureKeyStore:
    """使用 Windows DPAPI 加密保存 API Key。

    加密结果只对当前 Windows 用户可解密，config.json 中不会出现明文 API Key。
    """

    def __init__(self, store_path: Path):
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def set_secret(self, key: str, value: str) -> None:
        data = self._load()
        data[key] = self._protect(value)
        self._save(data)

    def get_secret(self, key: str) -> Optional[str]:
        data = self._load()
        encrypted = data.get(key)
        if not encrypted:
            return None
        return self._unprotect(encrypted)

    def delete_secret(self, key: str) -> None:
        data = self._load()
        if key in data:
            data.pop(key)
            self._save(data)

    def _load(self) -> dict:
        if not self.store_path.exists():
            return {}
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        self.store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _protect(self, value: str) -> str:
        raw = value.encode("utf-8")
        blob_in = DATA_BLOB(len(raw), ctypes.cast(ctypes.create_string_buffer(raw), ctypes.POINTER(ctypes.c_byte)))
        blob_out = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out),
        ):
            raise OSError("DPAPI CryptProtectData failed")
        try:
            protected = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            return base64.b64encode(protected).decode("ascii")
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

    def _unprotect(self, value: str) -> str:
        raw = base64.b64decode(value.encode("ascii"))
        blob_in = DATA_BLOB(len(raw), ctypes.cast(ctypes.create_string_buffer(raw), ctypes.POINTER(ctypes.c_byte)))
        blob_out = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out),
        ):
            raise OSError("DPAPI CryptUnprotectData failed")
        try:
            plain = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            return plain.decode("utf-8")
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
