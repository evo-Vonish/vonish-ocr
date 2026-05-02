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
            except Exception:
                pass
        return UserConfig()

    def save(self, config: UserConfig) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)
