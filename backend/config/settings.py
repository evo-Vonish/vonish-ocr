import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class AIConfig(BaseModel):
    enabled: bool = False
    provider: str = "deepseek"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: str = "deepseek-chat"
    temperature: float = 0.3
    trigger_mode: str = "auto"  # auto / always / manual


class UserConfig(BaseModel):
    ocr_model: str = "auto"
    preprocess: bool = True
    auto_rotate: bool = True
    perspective_correct: bool = False
    scene_detect: bool = True
    ai: AIConfig = Field(default_factory=AIConfig)
    output_mode: str = "smart"
    include_diff: bool = False
    redact_sensitive: bool = False
    power_mode: str = "balanced"
    preload_model: bool = True

    def model_dump(self, **kwargs):
        """返回配置字典，API Key 自动脱敏。"""
        data = super().model_dump(**kwargs)
        if data.get("ai", {}).get("api_key"):
            key = data["ai"]["api_key"]
            data["ai"]["api_key"] = key[:4] + "***" if len(key) > 4 else "***"
        return data


class ConfigManager:
    def __init__(self):
        self.config_path = Path(__file__).parent.parent.parent / "config.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> UserConfig:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return UserConfig(**data)
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
        return UserConfig()

    def save(self, config: UserConfig) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)
