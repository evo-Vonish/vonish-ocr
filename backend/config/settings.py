import json
import uuid
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from config.secure_store import SecureKeyStore


class AIConfig(BaseModel):
    enabled: bool = False
    provider: str = "deepseek"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: str = "deepseek-chat"
    temperature: float = 0.3
    trigger_mode: str = "auto"  # auto / always / manual


class AIScheme(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    provider_type: str = "deepseek"
    api_base: Optional[str] = None
    model: str = "deepseek-chat"
    weight: int = 5
    enabled: bool = True
    key_saved: bool = False
    api_key: Optional[str] = None


class UserConfig(BaseModel):
    ocr_model: str = "auto"
    ocr_language: str = "pp-ocrv5:ch"
    oobe_completed: bool = False
    tutorial_completed: bool = False
    preprocess: bool = True
    auto_rotate: bool = True
    perspective_correct: bool = False
    scene_detect: bool = True
    ai: AIConfig = Field(default_factory=AIConfig)
    ai_schemes: list[AIScheme] = Field(default_factory=list)
    active_ai_scheme_id: Optional[str] = None
    output_mode: str = "smart"
    include_diff: bool = False
    batch_ai_refine: bool = False
    redact_sensitive: bool = False
    power_mode: str = "balanced"
    performance_overrides: dict = Field(default_factory=dict)
    preload_model: bool = True

    def model_dump(self, **kwargs):
        """返回配置字典，API Key 自动脱敏。"""
        data = super().model_dump(**kwargs)
        if data.get("ai", {}).get("api_key"):
            key = data["ai"]["api_key"]
            data["ai"]["api_key"] = key[:4] + "***" if len(key) > 4 else "***"
        for scheme in data.get("ai_schemes", []):
            scheme.pop("api_key", None)
        return data


class ConfigManager:
    def __init__(self):
        self.config_path = Path(__file__).parent.parent.parent / "config.json"
        self.secret_store = SecureKeyStore(Path(__file__).parent.parent.parent / ".temp" / "ai_keys.dpapi.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> UserConfig:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg = UserConfig(**data)
                return self._ensure_default_ai_schemes(cfg)
            except json.JSONDecodeError:
                # 配置损坏，备份旧文件并返回默认
                backup = self.config_path.with_suffix(".json.bak")
                try:
                    self.config_path.rename(backup)
                except Exception:
                    pass
                return UserConfig()
            except Exception:
                pass
        return self._ensure_default_ai_schemes(UserConfig())

    def save(self, config: UserConfig) -> None:
        config = self._store_scheme_keys(config)
        with open(self.config_path, "w", encoding="utf-8") as f:
            data = config.model_dump()
            for scheme in data.get("ai_schemes", []):
                scheme.pop("api_key", None)
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _scheme_secret_key(self, scheme_id: str) -> str:
        return f"ai_scheme:{scheme_id}"

    def _get_scheme_secret(self, scheme_id: str) -> Optional[str]:
        try:
            return self.secret_store.get_secret(self._scheme_secret_key(scheme_id))
        except Exception:
            return None

    def list_ai_schemes(self, include_keys: bool = False) -> list[dict]:
        cfg = self.load()
        result = []
        for scheme in cfg.ai_schemes:
            data = scheme.model_dump()
            data.pop("api_key", None)
            secret = self._get_scheme_secret(scheme.id)
            data["key_saved"] = bool(secret)
            if include_keys:
                data["api_key"] = secret
            result.append(data)
        return result

    def get_ai_scheme(self, scheme_id: str, include_key: bool = False) -> dict:
        """Return one AI scheme. API Key is only included when explicitly requested."""
        cfg = self.load()
        for scheme in cfg.ai_schemes:
            if scheme.id != scheme_id:
                continue
            data = scheme.model_dump()
            data.pop("api_key", None)
            secret = self._get_scheme_secret(scheme.id)
            data["key_saved"] = bool(secret)
            if include_key:
                data["api_key"] = secret or ""
            return data
        raise ValueError("AI scheme not found")

    def upsert_ai_scheme(self, payload: dict) -> AIScheme:
        cfg = self.load()
        clear_key = bool(payload.pop("clear_key", False))
        existing = next((s for s in cfg.ai_schemes if s.id == payload.get("id")), None)
        merged = existing.model_dump() if existing else {}
        merged.update(payload)
        scheme = AIScheme(**merged)

        if clear_key:
            self.secret_store.delete_secret(self._scheme_secret_key(scheme.id))
            scheme.key_saved = False
        elif scheme.api_key:
            self.secret_store.set_secret(self._scheme_secret_key(scheme.id), scheme.api_key)
            scheme.key_saved = True
        else:
            # Editing metadata with an empty key keeps the encrypted key that was already saved.
            scheme.key_saved = bool(self._get_scheme_secret(scheme.id))
        scheme.api_key = None
        cfg.ai_schemes = [s for s in cfg.ai_schemes if s.id != scheme.id] + [scheme]
        if not cfg.active_ai_scheme_id:
            cfg.active_ai_scheme_id = scheme.id
        self.save(cfg)
        return scheme

    def set_active_ai_scheme(self, scheme_id: str) -> None:
        cfg = self.load()
        if not any(s.id == scheme_id for s in cfg.ai_schemes):
            raise ValueError("AI scheme not found")
        cfg.active_ai_scheme_id = scheme_id
        self.save(cfg)

    def delete_ai_scheme(self, scheme_id: str) -> None:
        cfg = self.load()
        if not any(s.id == scheme_id for s in cfg.ai_schemes):
            raise ValueError("AI scheme not found")
        cfg.ai_schemes = [s for s in cfg.ai_schemes if s.id != scheme_id]
        self.secret_store.delete_secret(self._scheme_secret_key(scheme_id))
        if cfg.active_ai_scheme_id == scheme_id:
            cfg.active_ai_scheme_id = cfg.ai_schemes[0].id if cfg.ai_schemes else None
        self.save(cfg)

    def get_active_ai_scheme_with_failover(self) -> list[dict]:
        cfg = self.load()
        schemes = self.list_ai_schemes(include_keys=True)
        active = cfg.active_ai_scheme_id
        schemes.sort(key=lambda s: (0 if s["id"] == active else 1, -int(s.get("weight") or 0)))
        return [s for s in schemes if s.get("enabled") and s.get("api_key")]

    def _ensure_default_ai_schemes(self, cfg: UserConfig) -> UserConfig:
        if cfg.ai_schemes:
            return cfg
        legacy_key_saved = bool(cfg.ai.api_key)
        scheme = AIScheme(
            id="default-deepseek",
            name="DeepSeek 默认",
            provider_type=cfg.ai.provider or "deepseek",
            api_base=cfg.ai.api_base,
            model=cfg.ai.model or "deepseek-chat",
            weight=5,
            enabled=True,
            key_saved=legacy_key_saved,
            api_key=cfg.ai.api_key,
        )
        cfg.ai_schemes = [scheme]
        cfg.active_ai_scheme_id = scheme.id
        return self._store_scheme_keys(cfg)

    def _store_scheme_keys(self, cfg: UserConfig) -> UserConfig:
        for scheme in cfg.ai_schemes:
            if scheme.api_key:
                self.secret_store.set_secret(f"ai_scheme:{scheme.id}", scheme.api_key)
                scheme.key_saved = True
                scheme.api_key = None
            else:
                scheme.key_saved = bool(self.secret_store.get_secret(f"ai_scheme:{scheme.id}"))
        if cfg.ai.api_key:
            self.secret_store.set_secret("legacy_ai_key", cfg.ai.api_key)
            cfg.ai.api_key = None
        return cfg
