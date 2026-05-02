import sys
import os
import json
import signal
import argparse
import logging
import traceback
from pathlib import Path
from contextlib import asynccontextmanager

# 确保 backend/ 目录在 sys.path 首位，优先解析本地模块
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from config.settings import ConfigManager

_is_sidecar = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    app.state.config = ConfigManager()
    try:
        from task_queue.local_queue import LocalQueue
        from models.model_manager import ModelManager

        app.state.queue = LocalQueue()
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
        logging.info("OCR 引擎管理器初始化完成")
    except Exception as e:
        logging.warning(f"初始化 engine_manager 失败: {e}")

    if _is_sidecar:
        # sidecar 模式下 lifespan 启动即表示服务已就绪
        pass

    yield

    # 关闭时卸载所有引擎
    try:
        if hasattr(app.state, "engine_manager"):
            for model_id in list(app.state.engine_manager.engines.keys()):
                await app.state.engine_manager.unload(model_id)
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


app = FastAPI(title="VonishOCR", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/v1")
app.include_router(router)


@app.get("/")
async def root():
    return {"name": "VonishOCR", "version": "0.1.0", "mode": "local"}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


def _setup_logging(log_dir: Path):
    """日志输出到文件，避免写入控制台"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "backend.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )


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
