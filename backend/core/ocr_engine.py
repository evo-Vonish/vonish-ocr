import asyncio
import gc
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class BaseOCREngine(ABC):
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.loaded = False

    @abstractmethod
    async def load(self) -> None:
        """加载模型到内存/显存"""

    @abstractmethod
    async def unload(self) -> None:
        """卸载模型，彻底释放资源"""

    @abstractmethod
    async def recognize(self, image_bytes: bytes, options: dict) -> dict:
        """返回识别结果"""
        ...


class OCREngineManager:
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.engines: Dict[str, BaseOCREngine] = {}
        self.active: Optional[str] = None
        self._factories: Dict[str, Callable[[Path], BaseOCREngine]] = {}
        self._lock = asyncio.Lock()

    def register_engine_factory(self, model_id: str, factory: Callable[[Path], BaseOCREngine]) -> None:
        """注册某个 model_id 对应的引擎工厂。"""
        self._factories[model_id] = factory

    def _get_factory(self, model_id: str) -> Callable[[Path], BaseOCREngine]:
        factory = self._factories.get(model_id)
        if factory is None:
            raise ValueError(f"Model {model_id} 没有对应的引擎工厂，请检查模型 ID 是否正确")
        return factory

    async def load(self, model_id: str, engine_factory: Callable[[Path], BaseOCREngine] = None) -> BaseOCREngine:
        async with self._lock:
            if model_id in self.engines:
                self.active = model_id
                return self.engines[model_id]

            model_path = self.model_manager.get_model_path(model_id)
            if model_path is None:
                raise ValueError(f"模型未加载，请先 pull {model_id}")

            factory = engine_factory or self._get_factory(model_id)
            engine = factory(model_path)
            await engine.load()
            self.engines[model_id] = engine
            self.active = model_id
            return engine

    async def unload(self, model_id: str) -> None:
        async with self._lock:
            engine = self.engines.pop(model_id, None)
            if engine:
                await engine.unload()
                if self.active == model_id:
                    self.active = None
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
                gc.collect()

    async def recognize(self, image_bytes: bytes, model_id: Optional[str] = None, options: Optional[dict] = None) -> dict:
        options = options or {}
        target = model_id or self.active
        if target is None:
            raise RuntimeError("No active OCR engine")
        engine = self.engines.get(target)
        if engine is None:
            raise RuntimeError(f"Engine {target} not loaded")
        return await engine.recognize(image_bytes, options)

    def list_loaded(self) -> list[str]:
        return list(self.engines.keys())
