import sys
import os
import json
import signal
import argparse
import logging
import logging.handlers
import traceback
from pathlib import Path
from contextlib import asynccontextmanager

# 确保 backend/ 目录在 sys.path 首位，优先解析本地模块
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import router
from config.settings import ConfigManager

_is_sidecar = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    app.state.config_manager = ConfigManager()
    try:
        from task_queue.local_queue import LocalQueue
        from models.model_manager import ModelManager

        # 根据功耗模式决定 worker 数量
        cfg = app.state.config_manager.load()
        power_mode = getattr(cfg, "power_mode", "balanced")
        worker_map = {"beast": 8, "balanced": 4, "eco": 1}
        concurrency_map = {"beast": 12, "balanced": 3, "eco": 2}
        max_workers = worker_map.get(power_mode, 4)
        concurrency = concurrency_map.get(power_mode, 3)

        app.state.queue = LocalQueue(max_workers=max_workers, concurrency=concurrency)
        app.state.model_manager = ModelManager()
    except Exception as e:
        logging.warning(f"初始化 queue/model_manager 失败: {e}")

    # 初始化 OCR 引擎管理器并注册 ONNX 引擎
    try:
        from core.ocr_engine import OCREngineManager
        from core.engines import ONNXOCREngine

        app.state.engine_manager = OCREngineManager(app.state.model_manager)
        # 注册 ONNX 引擎支持的模型
        for onnx_model_id in ["rapidocr-mobile-cn", "cnocr-standard-cn"]:
            app.state.engine_manager.register_engine_factory(
                onnx_model_id,
                lambda path, mid=onnx_model_id: ONNXOCREngine(path, model_id=mid),
            )
        # 预加载默认模型（根据配置）
        try:
            cfg = app.state.config_manager.load()
            should_preload = cfg.preload_model
            preload_model_id = os.environ.get("VONISH_PRELOAD_MODEL", "rapidocr-mobile-cn")

            if should_preload and app.state.model_manager.is_installed(preload_model_id):
                await app.state.engine_manager.load(preload_model_id)
                logging.info("模型已预加载: %s", preload_model_id)
            elif not should_preload:
                logging.info("启动预加载已禁用（preload_model=false）")
            else:
                logging.warning("预加载模型未安装: %s", preload_model_id)
        except Exception as e:
            logging.warning(f"预加载模型失败: {e}")

        logging.info("OCR 引擎管理器初始化完成")
    except Exception as e:
        logging.warning(f"初始化 engine_manager 失败: {e}")

    # 启动批量队列 worker（每张图独立做场景分类和预处理）
    try:
        import cv2
        import numpy as np
        from scene.classifier import RuleBasedSceneClassifier
        from preprocess.pipeline import PreprocessPipeline

        async def recognize_wrapper(img_bytes, opts):
            model_id = opts.get("model", "rapidocr-mobile-cn")

            # 解码图像
            img_array = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img_array is None:
                raise RuntimeError("批量任务：无法解码图片")

            # 场景分类 + 预处理（与单图路由一致）
            cfg = app.state.config_manager.load()
            scene_type = "printed_document"
            preprocess_meta = {"scene": scene_type, "steps": [], "time_ms": 0, "used_original": False}

            if getattr(cfg, "scene_detect", True):
                classifier = RuleBasedSceneClassifier()
                profile = classifier.classify(img_array)
                scene_type = profile.scene
                preprocess_meta["scene"] = scene_type

            if getattr(cfg, "preprocess", True):
                pipeline = PreprocessPipeline()
                pp_result = pipeline.run(img_array, scene_type, options={})
                processed_image = pp_result["image"]
                preprocess_meta["steps"] = pp_result["steps_applied"]
                preprocess_meta["time_ms"] = pp_result["timing_ms"]["total"]
                preprocess_meta["used_original"] = pp_result["used_original"]
            else:
                processed_image = img_array

            # 编码回 bytes
            _, encoded = cv2.imencode('.png', processed_image)
            processed_bytes = encoded.tobytes()

            # 加载模型并识别
            if model_id not in app.state.engine_manager.engines:
                await app.state.engine_manager.load(model_id)
            result = await app.state.engine_manager.recognize(processed_bytes, model_id=model_id, options=opts)

            # 合并预处理元数据
            result["scene"] = preprocess_meta["scene"]
            result["preprocess_steps"] = preprocess_meta["steps"]
            result["preprocess_time_ms"] = preprocess_meta["time_ms"]
            if preprocess_meta["used_original"]:
                result["preprocess_used_original"] = True

            if opts.get("ai_refine_batch") and getattr(cfg, "ai", None) and cfg.ai.enabled:
                try:
                    import asyncio
                    from ai_refiner import AIRefiner

                    ai_cfg = cfg.ai
                    refiner = AIRefiner(
                        enabled=True,
                        provider=ai_cfg.provider,
                        api_key=ai_cfg.api_key,
                        api_base=ai_cfg.api_base,
                        model=ai_cfg.model,
                        temperature=ai_cfg.temperature,
                        trigger_mode="always",
                        schemes=app.state.config_manager.get_active_ai_scheme_with_failover(),
                    )
                    ai_result = await refiner.refine(
                        raw_text=result.get("text", ""),
                        scene_type=scene_type,
                        ocr_confidence=result.get("confidence", 0.0),
                    )
                    if (opts.get("output_mode") or cfg.output_mode or "smart") == "polished":
                        result["text"] = ai_result.get("polished", result.get("text", ""))
                    result["ai"] = ai_result
                except Exception as e:
                    logging.warning("Batch AI refine failed; raw OCR kept: %s", e)
            return result

        def recognize_sync_wrapper(img_bytes, opts):
            import gc
            model_id = opts.get("model", "rapidocr-mobile-cn")

            # 解码图像
            img_array = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img_array is None:
                raise RuntimeError("批量任务：无法解码图片")

            # 场景分类 + 预处理（同步版本）
            cfg = app.state.config_manager.load()
            scene_type = "printed_document"
            preprocess_meta = {"scene": scene_type, "steps": [], "time_ms": 0, "used_original": False}

            classifier = None
            pipeline = None

            if getattr(cfg, "scene_detect", True):
                classifier = RuleBasedSceneClassifier()
                profile = classifier.classify(img_array)
                scene_type = profile.scene
                preprocess_meta["scene"] = scene_type

            if getattr(cfg, "preprocess", True):
                pipeline = PreprocessPipeline()
                pp_result = pipeline.run(img_array, scene_type, options={})
                processed_image = pp_result["image"]
                preprocess_meta["steps"] = pp_result["steps_applied"]
                preprocess_meta["time_ms"] = pp_result["timing_ms"]["total"]
                preprocess_meta["used_original"] = pp_result["used_original"]
            else:
                processed_image = img_array

            # 编码回 bytes
            _, encoded = cv2.imencode('.png', processed_image)
            processed_bytes = encoded.tobytes()

            # 识别（纯同步，避免 asyncio.run 在线程中反复创建事件循环）
            result = app.state.engine_manager.recognize_sync(processed_bytes, model_id=model_id, options=opts)

            # 合并预处理元数据
            result["scene"] = preprocess_meta["scene"]
            result["preprocess_steps"] = preprocess_meta["steps"]
            result["preprocess_time_ms"] = preprocess_meta["time_ms"]
            if preprocess_meta["used_original"]:
                result["preprocess_used_original"] = True

            # 显式释放大对象，防止内存堆积
            if opts.get("ai_refine_batch") and getattr(cfg, "ai", None) and cfg.ai.enabled:
                try:
                    import asyncio
                    from ai_refiner import AIRefiner

                    ai_cfg = cfg.ai
                    refiner = AIRefiner(
                        enabled=True,
                        provider=ai_cfg.provider,
                        api_key=ai_cfg.api_key,
                        api_base=ai_cfg.api_base,
                        model=ai_cfg.model,
                        temperature=ai_cfg.temperature,
                        trigger_mode="always",
                        schemes=app.state.config_manager.get_active_ai_scheme_with_failover(),
                    )
                    ai_result = asyncio.run(refiner.refine(
                        raw_text=result.get("text", ""),
                        scene_type=scene_type,
                        ocr_confidence=result.get("confidence", 0.0),
                    ))
                    if (opts.get("output_mode") or cfg.output_mode or "smart") == "polished":
                        result["text"] = ai_result.get("polished", result.get("text", ""))
                    result["ai"] = ai_result
                except Exception as e:
                    logging.warning("Batch AI refine failed; raw OCR kept: %s", e)

            del img_array, processed_image, encoded, processed_bytes
            if classifier:
                del classifier
            if pipeline:
                del pipeline
            gc.collect()
            return result

        app.state.queue.start(recognize_wrapper, recognize_sync_wrapper)
        logging.info(f"批量队列已启动: workers={app.state.queue.max_workers}, concurrency={app.state.queue.concurrency}")
    except Exception as e:
        logging.warning(f"启动 queue worker 失败: {e}")

    if _is_sidecar:
        # sidecar 模式下 lifespan 启动即表示服务已就绪
        pass

    yield

    # 关闭时卸载所有引擎
    try:
        if hasattr(app.state, "engine_manager"):
            await app.state.engine_manager.unload_all()
    except Exception:
        pass

    if _is_sidecar:
        try:
            print(
                json.dumps({"status": "shutdown", "reason": "lifespan_end"}),
                flush=True,
            )
        except Exception:
            pass


def _get_cors_origins() -> list[str]:
    """根据运行模式返回允许的 CORS 来源。sidecar 模式只允许本地，开发模式放宽。"""
    if _is_sidecar:
        return ["http://localhost:1420", "http://localhost:8000", "tauri://localhost"]
    return ["*"]


app = FastAPI(title="VonishOCR", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/v1")
app.include_router(router)

# 挂载 VitePress 文档站，供前端 iframe 内嵌
_docs_dist = Path(__file__).parent.parent / "docs" / ".vitepress" / "dist"
if _docs_dist.exists():
    app.mount("/reference", StaticFiles(directory=str(_docs_dist), html=True), name="reference_docs")


@app.get("/")
async def root():
    return {"name": "VonishOCR", "version": "0.1.0", "mode": "local"}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


class _SensitiveDataFilter(logging.Filter):
    """脱敏 Filter：隐藏 API Key 等敏感信息"""
    _SENSITIVE_KEYS = ('api_key', 'apikey', 'api-key', 'authorization', 'token', 'secret')

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        lower = msg.lower()
        for key in self._SENSITIVE_KEYS:
            if key in lower:
                # 简单替换：把包含敏感 key 的那一段替换为 ***
                record.msg = '[REDACTED] 日志包含敏感信息，已脱敏'
                record.args = ()
                break
        return True


def _setup_logging(log_dir: Path):
    """日志输出到文件，10MB 轮转，保留最近 7 个备份"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "backend.log"

    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=7,
        encoding='utf-8',
    )
    handler.setFormatter(
        logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    )
    handler.addFilter(_SensitiveDataFilter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = []
    root.addHandler(handler)

    # 为各模块设置合理的级别
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)


def _signal_handler(signum, frame):
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VonishOCR Backend")
    parser.add_argument(
        "--sidecar",
        action="store_true",
        help="以 sidecar 模式启动（无终端窗口、随机端口、日志到文件）",
    )
    args = parser.parse_args()
    _is_sidecar = args.sidecar

    if _is_sidecar:
        # 日志目录
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # 配置日志输出到文件
        _setup_logging(log_dir)

        # 信号处理（忽略失败）
        try:
            signal.signal(signal.SIGTERM, _signal_handler)
            signal.signal(signal.SIGINT, _signal_handler)
        except Exception:
            pass

        # 端口
        port = int(os.environ.get("VONISH_PORT", 8000))

        # 先输出就绪信号（Rust 正在监听 stdout）
        try:
            print(
                json.dumps({"status": "ready", "port": port, "pid": os.getpid()}),
                flush=True,
            )
        except Exception:
            pass

        # 重定向 stdout/stderr 到日志文件
        # 防止 uvicorn 后续写入控制台句柄导致崩溃
        try:
            sys.stdout = open(log_dir / "stdout.log", "w", buffering=1)
            sys.stderr = open(log_dir / "stderr.log", "w", buffering=1)
        except Exception:
            pass

        import uvicorn

        try:
            # 直接传 app 对象，避免 uvicorn 重新导入 "main" 模块
            # 导致 _is_sidecar 被重置或 sys.path 异常
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=port,
                log_level="warning",
                access_log=False,
            )
        except Exception as e:
            # 将异常写入日志，方便调试
            try:
                with open(log_dir / "crash.log", "w", encoding="utf-8") as f:
                    f.write(f"uvicorn crash: {e}\n")
                    f.write(traceback.format_exc())
            except Exception:
                pass
            raise
    else:
        # 正常开发模式
        import uvicorn

        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
