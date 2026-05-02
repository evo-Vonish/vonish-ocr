import base64
import logging
import json
from io import BytesIO

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, Body, File, Form, Request, UploadFile, WebSocket, HTTPException

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

    engine_mgr = request.app.state.engine_manager

    # 如果引擎未加载，尝试自动加载
    if model_id not in engine_mgr.engines:
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
        )

        scene_type = options.get("scene", "print")
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
    MAX_BATCH_SIZE = 50 * 1024 * 1024
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
async def pull_model(model_id: str):
    return {"model_id": model_id, "status": "Phase 0 stub - download not implemented"}


@router.get("/v1/config")
async def get_config(request: Request):
    return request.app.state.config_manager.load().model_dump()


@router.post("/v1/config")
async def save_config(request: Request, payload: dict):
    from config.settings import UserConfig

    cfg = UserConfig(**payload)
    request.app.state.config_manager.save(cfg)
    return {"status": "saved"}


async def _ws_progress_callback(task_id: str, completed: int, total: int, result):
    """进度回调：通过 WebSocket 推送给前端。"""
    ws = _ws_connections.get(task_id)
    if ws:
        try:
            await ws.send_json({
                "type": "progress",
                "task_id": task_id,
                "completed": completed,
                "total": total,
                "progress": round(completed / total, 4) if total > 0 else 0,
            })
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
