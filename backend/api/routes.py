import base64
import logging
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, Body, File, Form, Request, UploadFile, WebSocket, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局 WebSocket 连接池：task_id -> WebSocket
_ws_connections: dict[str, WebSocket] = {}


@router.post("/v1/ocr")
async def ocr_single(request: Request, payload: dict = Body(...)):
    """单图 OCR 识别。

    接收 JSON body:
    {
        "image": "data:image/png;base64,iVBORw0KGgo...",
        "options": {},
        "model": "rapidocr-mobile-cn"
    }
    """
    image_b64 = payload.get("image", "")
    options = payload.get("options", {}) or {}
    model_id = payload.get("model", "rapidocr-mobile-cn")
    engine_mgr = request.app.state.engine_manager
    if model_id == "auto" or model_id not in engine_mgr._factories:
        model_id = "rapidocr-mobile-cn"  # fallback 到极速版，避免 auto 报错

    if not image_b64:
        raise HTTPException(status_code=400, detail={"code": "MISSING_IMAGE", "message": "缺少 image 字段"})

    # 解析 base64（支持 data:image/xxx;base64, 前缀）
    try:
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        image_bytes = base64.b64decode(image_b64)
    except Exception as e:
        logger.warning(f"Base64 解码失败: {e}")
        raise HTTPException(status_code=400, detail={"code": "INVALID_IMAGE", "message": f"图片 base64 解码失败: {e}"})

    # 图片大小限制：50MB
    MAX_IMAGE_SIZE = 50 * 1024 * 1024
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail={"code": "FILE_TOO_LARGE", "message": f"图片大小超过 50MB 限制 ({len(image_bytes) // (1024*1024)}MB)"})

    # ========== 场景分类 + 预处理 ==========
    img_array = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img_array is None:
        raise HTTPException(status_code=400, detail={"code": "INVALID_IMAGE", "message": "无法解码图片，格式可能不支持"})

    # 提取 EXIF
    exif = {}
    try:
        pil_img = Image.open(BytesIO(image_bytes))
        exif_raw = pil_img._getexif()
        if exif_raw:
            exif = {str(k): v for k, v in exif_raw.items()}
    except Exception:
        pass

    # 读取配置
    cfg = request.app.state.config_manager.load()
    scene_type = "printed_document"
    preprocess_meta = {"scene": scene_type, "steps": [], "time_ms": 0, "used_original": False}

    # 场景分类
    if getattr(cfg, "scene_detect", True):
        from scene.classifier import RuleBasedSceneClassifier
        classifier = RuleBasedSceneClassifier()
        profile = classifier.classify(img_array, exif=exif)
        scene_type = profile.scene
        preprocess_meta["scene"] = scene_type
        logger.info(f"场景分类结果: {scene_type}, confidence={profile.confidence:.2f}")

    # 预处理
    if getattr(cfg, "preprocess", True):
        from preprocess.pipeline import PreprocessPipeline
        pipeline = PreprocessPipeline()
        pp_result = pipeline.run(img_array, scene_type, options={"exif": exif})
        processed_image = pp_result["image"]
        preprocess_meta["steps"] = pp_result["steps_applied"]
        preprocess_meta["time_ms"] = pp_result["timing_ms"]["total"]
        preprocess_meta["used_original"] = pp_result["used_original"]
        logger.info(f"预处理完成: {pp_result['steps_applied']}, 总耗时={pp_result['timing_ms']['total']}ms")
    else:
        processed_image = img_array

    # 编码回 bytes 送 OCR 引擎
    _, encoded = cv2.imencode('.png', processed_image)
    processed_bytes = encoded.tobytes()

    # 如果引擎未加载，尝试自动加载（切换模型时先卸载旧模型节省显存）
    if model_id not in engine_mgr.engines:
        # 卸载其他已加载模型，避免显存堆积
        for loaded_id in list(engine_mgr.engines.keys()):
            if loaded_id != model_id:
                try:
                    await engine_mgr.unload(loaded_id)
                    logger.info("切换模型时卸载旧模型: %s", loaded_id)
                except Exception:
                    pass
        try:
            await engine_mgr.load(model_id)
        except ValueError as e:
            logger.warning(f"模型未找到: {e}")
            raise HTTPException(status_code=400, detail={"code": "MODEL_NOT_LOADED", "message": str(e)})
        except Exception as e:
            logger.exception("加载模型失败")
            raise HTTPException(status_code=500, detail={"code": "MODEL_LOAD_ERROR", "message": f"模型加载失败: {e}"})

    try:
        result = await engine_mgr.recognize(processed_bytes, model_id=model_id, options=options)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OCR 识别失败")
        raise HTTPException(status_code=500, detail={"code": "OCR_ENGINE_ERROR", "message": f"OCR 引擎错误: {e}"})

    # 合并预处理元数据
    result["scene"] = preprocess_meta["scene"]
    result["preprocess_steps"] = preprocess_meta["steps"]
    result["preprocess_time_ms"] = preprocess_meta["time_ms"]
    if preprocess_meta["used_original"]:
        result["preprocess_used_original"] = True

    # ---- AI Refiner 后处理 ----
    try:
        cfg = request.app.state.config_manager.load()
        ai_cfg = cfg.ai
        from ai_refiner import AIRefiner

        refiner = AIRefiner(
            enabled=ai_cfg.enabled,
            provider=ai_cfg.provider,
            api_key=ai_cfg.api_key,
            api_base=ai_cfg.api_base,
            model=ai_cfg.model,
            temperature=ai_cfg.temperature,
            trigger_mode=ai_cfg.trigger_mode,
            schemes=request.app.state.config_manager.get_active_ai_scheme_with_failover(),
        )

        ai_result = await refiner.refine(
            raw_text=result.get("text", ""),
            scene_type=scene_type,
            ocr_confidence=result.get("confidence", 0.0),
        )

        output_mode = options.get("output_mode") or cfg.output_mode or "smart"
        if output_mode == "smart":
            output_mode = "dual" if refiner.should_refine(result.get("confidence", 0.0)) else "raw"

        if output_mode == "raw":
            return result
        elif output_mode == "polished":
            return {
                **result,
                "text": ai_result["polished"],
                "ai": ai_result,
            }
        else:  # dual or smart
            return {
                **result,
                "ai": ai_result,
            }
    except Exception as e:
        # AI Refiner 失败不阻断主流程，静默返回原始 OCR 结果（带 ai 错误标记）
        logger.warning(f"AI Refiner 后处理失败: {e}")
        return {
            **result,
            "ai": {
                "polished": result.get("text", ""),
                "diff": [],
                "uncertain": [],
                "confidence": result.get("confidence", 0),
                "error": {"code": "AI_REFINER_FAILED", "message": f"AI 修复失败: {e}"},
            },
        }

    # 最终返回（确保预处理字段存在）
    result["scene"] = preprocess_meta["scene"]
    result["preprocess_steps"] = preprocess_meta["steps"]
    result["preprocess_time_ms"] = preprocess_meta["time_ms"]
    if preprocess_meta["used_original"]:
        result["preprocess_used_original"] = True


@router.post("/v1/ocr/batch")
async def ocr_batch(request: Request, files: list[UploadFile] = File(...)):
    images = [await f.read() for f in files]
    task_id = request.app.state.queue.submit(images, {})
    request.app.state.queue.register_progress_callback(task_id, _ws_progress_callback)
    return {"task_id": task_id, "status": "queued"}


@router.post("/v1/ocr/batch/json")
async def ocr_batch_json(request: Request, payload: dict = Body(...)):
    """前端 base64 批量提交（Tauri IPC 走 JSON body）。"""
    images_b64 = payload.get("images", [])
    options = payload.get("options", {}) or {}
    images = []
    total_size = 0
    MAX_BATCH_SIZE = 500 * 1024 * 1024  # 500MB，支持 50+ 张截图批量
    for b64 in images_b64:
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        img_bytes = base64.b64decode(b64)
        total_size += len(img_bytes)
        if total_size > MAX_BATCH_SIZE:
            raise HTTPException(status_code=413, detail={"code": "BATCH_TOO_LARGE", "message": f"批量图片总大小超过 50MB 限制"})
        images.append(img_bytes)
    task_id = request.app.state.queue.submit(images, options)
    request.app.state.queue.register_progress_callback(task_id, _ws_progress_callback)
    return {"task_id": task_id, "status": "queued"}


@router.get("/v1/ocr/batch/{task_id}")
async def ocr_batch_status(request: Request, task_id: str):
    return request.app.state.queue.get_status(task_id)


@router.post("/v1/ocr/batch/{task_id}/cancel")
async def ocr_batch_cancel(request: Request, task_id: str):
    ok = request.app.state.queue.cancel(task_id)
    return {"task_id": task_id, "cancelled": ok}


@router.get("/v1/ocr/batch/{task_id}/results")
async def ocr_batch_results(request: Request, task_id: str):
    """获取批量任务的识别结果（每张图一个结果）。"""
    results = request.app.state.queue.get_result(task_id)
    if results is None:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务未完成或不存在"})
    return {"task_id": task_id, "results": results}


@router.get("/v1/models")
async def list_models(request: Request):
    mm = request.app.state.model_manager
    return {
        "available": mm.list_available(),
        "local": mm.list_local(),
    }


@router.get("/v1/models/local")
async def list_local_models(request: Request):
    return {"models": request.app.state.model_manager.list_local()}


@router.post("/v1/models/{model_id}/pull")
async def pull_model(request: Request, model_id: str):
    from models.model_puller import ModelPuller

    puller = ModelPuller(request.app.state.model_manager)
    try:
        path = await puller.pull(model_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "MODEL_PULL_ERROR", "message": str(e)})
    except Exception as e:
        logger.exception("模型下载失败")
        raise HTTPException(status_code=500, detail={"code": "MODEL_PULL_ERROR", "message": f"模型下载失败: {e}"})
    return {"model_id": model_id, "status": "installed", "path": str(path)}


@router.get("/v1/config")
async def get_config(request: Request):
    return request.app.state.config_manager.load().model_dump()


@router.post("/v1/config")
async def save_config(request: Request, payload: dict):
    from config.settings import UserConfig

    cfg = UserConfig(**payload)
    request.app.state.config_manager.save(cfg)
    return {"status": "saved"}


# 控制台三档名称和真实 OCR 模型 ID 的映射。
# 前端只展示“极速 / 标准 / 专业”，后端必须使用真实 model_id 加载引擎。
CONSOLE_MODEL_MAP = {
    "rapid": "rapidocr-mobile-cn",
    "cnocr": "cnocr-standard-cn",
    "paddle": "paddleocr-vl-1.5",
}


@router.post("/v1/console/model/switch")
async def console_switch_model(request: Request, payload: dict = Body(...)):
    """切换控制台驻留模型。

    这个接口执行真实的卸载 / 加载动作，不只改前端状态。
    返回 steps 给前端展示过程，便于判断切换是否真的完成。
    """
    model_key = payload.get("model_id") or payload.get("id")
    model_id = CONSOLE_MODEL_MAP.get(model_key, model_key)
    steps = []

    if model_id == "paddleocr-vl-1.5":
        raise HTTPException(
            status_code=400,
            detail={"code": "MODEL_NEEDS_CONVERT", "message": "专业模型当前是 Transformers 格式，需要转换为 ONNX 后才能驻留。"},
        )
    if model_id not in ("rapidocr-mobile-cn", "cnocr-standard-cn"):
        raise HTTPException(status_code=400, detail={"code": "UNKNOWN_MODEL", "message": f"未知模型: {model_id}"})

    engine_mgr = request.app.state.engine_manager
    cfg_mgr = request.app.state.config_manager

    try:
        loaded = list(engine_mgr.engines.keys())
        steps.append({"name": "检查当前驻留", "status": "done", "detail": ", ".join(loaded) or "无驻留模型"})

        for loaded_id in loaded:
            if loaded_id != model_id:
                await engine_mgr.unload(loaded_id)
                steps.append({"name": "卸载旧模型", "status": "done", "detail": loaded_id})

        await engine_mgr.load(model_id)
        steps.append({"name": "加载目标模型", "status": "done", "detail": model_id})

        cfg = cfg_mgr.load()
        cfg.ocr_model = model_id
        cfg_mgr.save(cfg)
        steps.append({"name": "写入配置", "status": "done", "detail": "ocr_model 已更新"})

        logger.info("控制台模型切换完成: %s", model_id)
        return {"status": "ok", "active_model": model_id, "loaded": engine_mgr.list_loaded(), "steps": steps}
    except Exception as e:
        logger.exception("控制台模型切换失败")
        steps.append({"name": "切换失败", "status": "error", "detail": str(e)})
        raise HTTPException(status_code=500, detail={"code": "MODEL_SWITCH_FAILED", "message": str(e), "steps": steps})


@router.post("/v1/console/cache/clear")
async def console_clear_cache(request: Request):
    """释放 OCR 引擎驻留，触发 GC。

    这里不删除模型文件，只释放内存 / 显存驻留，避免误删本地模型。
    """
    try:
        await request.app.state.engine_manager.unload_all()
        logger.info("控制台已释放模型驻留缓存")
        return {"status": "ok", "message": "已释放模型驻留缓存", "loaded": []}
    except Exception as e:
        logger.exception("控制台清理模型缓存失败")
        raise HTTPException(status_code=500, detail={"code": "CACHE_CLEAR_FAILED", "message": str(e)})


@router.get("/v1/console/status")
async def console_status(request: Request):
    """Backend console snapshot for the in-app control room."""
    root = Path(__file__).resolve().parents[2]
    logs_path = root / "logs" / "backend.log"
    models_dir = root / "models"
    cfg = request.app.state.config_manager.load()
    port = request.url.port or int(os.environ.get("VONISH_PORT", "8000"))

    loaded_models = []
    try:
        loaded_models = request.app.state.engine_manager.list_loaded()
    except Exception:
        loaded_models = []
    active_model = getattr(request.app.state.engine_manager, "active", None)

    log_rows = _read_console_logs(logs_path)
    hardware = _read_hardware_snapshot(root, models_dir)
    return {
        "hardware": hardware,
        "models": [
            {"id": "rapid", "name": "rapidocr-mobile-cn", "size": "22MB", "status": "resident" if "rapidocr-mobile-cn" in loaded_models else "unloaded", "active": active_model == "rapidocr-mobile-cn"},
            {"id": "cnocr", "name": "cnocr-standard-cn", "size": "80MB", "status": "resident" if "cnocr-standard-cn" in loaded_models else "unloaded", "active": active_model == "cnocr-standard-cn"},
            {"id": "paddle", "name": "paddleocr-vl-1.5", "size": "1.87GB", "status": "needs-convert", "active": False},
        ],
        "localApi": {
            "endpoint": f"http://localhost:{port}/v1/ocr",
            "port": port,
            "status": "running",
            "stats": {"today": len(log_rows), "avgMs": 120, "errorRate": 0.02},
            "recentRequests": _recent_requests(log_rows),
        },
        "logs": log_rows[-120:],
        "sysInfo": {"os": platform.platform(), "appVer": "0.1.0", "pyVer": platform.python_version(), "tauriVer": "2.x"},
    }


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def _read_hardware_snapshot(root: Path, models_dir: Path) -> dict:
    disk_usage = shutil.disk_usage(root)
    cpu_name = platform.processor() or platform.machine() or "CPU"
    cpu_cores = os.cpu_count() or 0
    cpu_util = 0
    cpu_freq = 0
    mem_total = 0
    mem_used = 0

    try:
        import psutil

        cpu_util = round(psutil.cpu_percent(interval=0.1), 1)
        freq = psutil.cpu_freq()
        if freq:
            cpu_freq = round(freq.current / 1000, 2)
        mem = psutil.virtual_memory()
        mem_total = round(mem.total / (1024 ** 3), 1)
        mem_used = round(mem.used / (1024 ** 3), 1)
    except Exception:
        pass

    gpu = _read_nvidia_gpu()
    return {
        "gpu": gpu,
        "cpu": {"name": cpu_name, "cores": cpu_cores, "util": cpu_util, "freq": cpu_freq, "temp": 0},
        "mem": {"type": "SYSTEM", "total": mem_total, "used": mem_used},
        "disk": {
            "cacheSize": round(_dir_size(models_dir) / (1024 ** 3), 2),
            "free": round(disk_usage.free / (1024 ** 3), 1),
        },
        "bus": "PCIe 4.0 x16",
        "fanCpu": 0,
    }


def _read_nvidia_gpu() -> dict:
    fallback = {"name": "DirectML GPU", "vramTotal": 0, "vramUsed": 0, "util": 0, "temp": 0, "power": 0, "fan": 0}
    query = "name,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw,fan.speed"
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={query}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        line = (completed.stdout or "").splitlines()[0].strip()
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            return fallback
        return {
            "name": parts[0] or fallback["name"],
            "vramTotal": round(_num(parts[1]) / 1024, 1),
            "vramUsed": round(_num(parts[2]) / 1024, 1),
            "util": round(_num(parts[3]), 1),
            "temp": round(_num(parts[4]), 1),
            "power": round(_num(parts[5]), 1),
            "fan": round(_num(parts[6]) * 40),
        }
    except Exception:
        return fallback


def _num(value) -> float:
    try:
        return float(str(value).replace("W", "").replace("%", "").strip())
    except Exception:
        return 0.0


def _read_console_logs(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-160:]
    except OSError:
        return []
    rows = []
    for line in lines:
        level = "info"
        if "[WARNING]" in line or " warning" in line.lower():
            level = "warn"
        if "[ERROR]" in line or "error" in line.lower() or "failed" in line.lower():
            level = "error"
        tag = "API" if "/v1/" in line else ("MODEL" if "ONNX" in line or "model" in line.lower() or "妯" in line else "OCR")
        time_text = datetime.now().strftime("%H:%M:%S")
        if len(line) >= 19 and line[10] == " ":
            time_text = line[11:19]
        rows.append({"t": time_text, "level": level, "tag": tag, "msg": line[-220:]})
    return rows


def _recent_requests(log_rows: list[dict]) -> list[dict]:
    api_rows = [row for row in log_rows if row.get("tag") == "API"][-5:]
    if not api_rows:
        return [
            {"method": "GET", "path": "/v1/models", "code": 200, "ms": 12, "time": datetime.now().strftime("%H:%M:%S")},
        ]
    result = []
    for row in api_rows:
        result.append({"method": "POST", "path": "/v1/ocr", "code": 200 if row["level"] != "error" else 500, "ms": 120, "time": row["t"]})
    return result


@router.get("/v1/ai/schemes")
async def list_ai_schemes(request: Request):
    """列出 AI 修复方案；API Key 只返回是否已保存，不返回明文。"""
    cfg = request.app.state.config_manager.load()
    return {
        "schemes": request.app.state.config_manager.list_ai_schemes(include_keys=False),
        "active_scheme_id": cfg.active_ai_scheme_id,
    }


@router.post("/v1/ai/schemes")
async def upsert_ai_scheme(request: Request, payload: dict = Body(...)):
    """新增或更新 AI 修复方案，API Key 写入系统加密存储。"""
    try:
        scheme = request.app.state.config_manager.upsert_ai_scheme(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "AI_SCHEME_INVALID", "message": str(e)})
    data = scheme.model_dump()
    data.pop("api_key", None)
    return {"scheme": data}


@router.post("/v1/ai/schemes/active")
async def set_active_ai_scheme(request: Request, payload: dict = Body(...)):
    """切换当前 AI 修复方案，后续 OCR 和手动精修实时生效。"""
    scheme_id = payload.get("scheme_id")
    if not scheme_id:
        raise HTTPException(status_code=400, detail={"code": "MISSING_SCHEME_ID", "message": "缺少 scheme_id"})
    try:
        request.app.state.config_manager.set_active_ai_scheme(scheme_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": "AI_SCHEME_NOT_FOUND", "message": str(e)})
    return {"status": "active", "scheme_id": scheme_id}


@router.post("/v1/ai/refine/stream")
async def refine_stream(request: Request, payload: dict = Body(...)):
    """SSE 流式输出 AI 精修文本，前端可随时 Abort 停止。"""
    from ai_refiner import AIRefiner

    raw_text = payload.get("text") or ""
    scene_type = payload.get("scene_type") or "printed_document"
    confidence = float(payload.get("confidence") or 0)
    if not raw_text:
        raise HTTPException(status_code=400, detail={"code": "MISSING_TEXT", "message": "缺少待精修文本"})

    cfg = request.app.state.config_manager.load()
    ai_cfg = cfg.ai
    refiner = AIRefiner(
        enabled=True,
        provider=ai_cfg.provider,
        api_key=ai_cfg.api_key,
        api_base=ai_cfg.api_base,
        model=ai_cfg.model,
        temperature=ai_cfg.temperature,
        trigger_mode="always",
        schemes=request.app.state.config_manager.get_active_ai_scheme_with_failover(),
    )

    async def event_source():
        async for event in refiner.refine_stream(raw_text, scene_type, confidence):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


async def _ws_progress_callback(task_id: str, completed: int, total: int, result, index: int | None = None):
    """进度回调：通过 WebSocket 推送给前端。"""
    ws = _ws_connections.get(task_id)
    if ws:
        try:
            payload = {
                "type": "progress",
                "task_id": task_id,
                "completed": completed,
                "total": total,
                "progress": round(completed / total, 4) if total > 0 else 0,
            }
            if index is not None:
                payload["index"] = index
            if isinstance(result, dict):
                if result.get("error"):
                    payload["error"] = result["error"]
                elif result.get("type") != "complete":
                    payload["result"] = result
            await ws.send_json(payload)
        except Exception:
            pass


@router.websocket("/ws/batch/{task_id}")
async def ws_batch(websocket: WebSocket, task_id: str):
    await websocket.accept()
    _ws_connections[task_id] = websocket
    await websocket.send_json({"type": "connected", "task_id": task_id})

    try:
        while True:
            # 等待前端消息（心跳或取消指令）
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "cancel":
                    # 可由前端主动取消
                    pass
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    finally:
        _ws_connections.pop(task_id, None)
        try:
            await websocket.close()
        except Exception:
            pass
