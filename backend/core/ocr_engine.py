import asyncio
import gc
import logging
import time
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


class MemoryBudget:
    """简单的显存/内存预算管理。"""
    def __init__(self, vram_total_mb: int = 8192, vram_reserve_mb: int = 2048):
        self.vram_total = vram_total_mb
        self.vram_reserved = vram_reserve_mb
        self.vram_available = vram_total_mb - vram_reserve_mb
        self.current_models: Dict[str, int] = {}
        self._last_used: Dict[str, float] = {}

    def can_load(self, model_id: str, required_mb: int) -> bool:
        used = sum(self.current_models.values())
        return used + required_mb <= self.vram_available

    def record_load(self, model_id: str, size_mb: int):
        self.current_models[model_id] = size_mb
        self._last_used[model_id] = time.time()

    def record_unload(self, model_id: str):
        self.current_models.pop(model_id, None)
        self._last_used.pop(model_id, None)

    def get_lru_model(self) -> Optional[str]:
        if not self._last_used:
            return None
        return min(self._last_used, key=self._last_used.get)


class OCREngineManager:
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.engines: Dict[str, BaseOCREngine] = {}
        self.active: Optional[str] = None
        self._factories: Dict[str, Callable[[Path], BaseOCREngine]] = {}
        self._lock = asyncio.Lock()
        self.memory_budget = MemoryBudget()

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

    def recognize_sync(self, image_bytes: bytes, model_id: Optional[str] = None, options: Optional[dict] = None) -> dict:
        """同步版本，供线程池调用。
        
        注意：ONNXOCREngine.recognize 虽然是 async，但内部没有真正的 await 点，
        可以直接在同步上下文中调用其协程对象。
        """
        import asyncio
        target = model_id or self.active
        if target is None:
            raise RuntimeError("No active OCR engine")
        engine = self.engines.get(target)
        if engine is None:
            raise RuntimeError(f"Engine {target} not loaded")
        
        # 直接获取协程对象并运行（引擎内部没有 await，所以可以直接执行）
        coro = engine.recognize(image_bytes, options or {})
        try:
            # 尝试在当前线程的事件循环中运行
            loop = asyncio.get_running_loop()
            # 如果在事件循环中，需要用 run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=30)
        except RuntimeError:
            # 没有运行中的事件循环，直接创建新的
            return asyncio.run(coro)

    async def unload_all(self) -> None:
        """卸载所有引擎并打印显存日志。"""
        import gc
        model_ids = list(self.engines.keys())
        for mid in model_ids:
            await self.unload(mid)
        gc.collect()
        # 打印显存占用（DirectML 无直接显存查询 API，打印加载状态代替）
        logger.info(f"所有 OCR 引擎已卸载，当前加载: {self.list_loaded()}")

    def list_loaded(self) -> list[str]:
        return list(self.engines.keys())
