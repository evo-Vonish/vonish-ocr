import base64
import logging

from fastapi import APIRouter, Body, File, Form, Request, UploadFile, WebSocket, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


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
        raise HTTPException(status_code=400, detail="缺少 image 字段")

    # 解析 base64（支持 data:image/xxx;base64, 前缀）
    try:
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        image_bytes = base64.b64decode(image_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片 base64 解码失败: {e}")

    engine_mgr = request.app.state.engine_manager

    # 如果引擎未加载，尝试自动加载
    if model_id not in engine_mgr.engines:
        try:
            await engine_mgr.load(model_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.exception("加载模型失败")
            raise HTTPException(status_code=500, detail=f"模型加载失败: {e}")

    try:
        result = await engine_mgr.recognize(image_bytes, model_id=model_id, options=options)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OCR 识别失败")
        raise HTTPException(status_code=500, detail=f"OCR 引擎错误: {e}")


@router.post("/v1/ocr/batch")
async def ocr_batch(request: Request, files: list[UploadFile] = File(...)):
    images = [await f.read() for f in files]
    task_id = request.app.state.queue.submit(images, {})
    return {"task_id": task_id, "status": "queued"}


@router.get("/v1/ocr/batch/{task_id}")
async def ocr_batch_status(request: Request, task_id: str):
    return request.app.state.queue.get_status(task_id)


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


@router.websocket("/ws/batch/{task_id}")
async def ws_batch(websocket: WebSocket, task_id: str):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "task_id": task_id})
    await websocket.close()
