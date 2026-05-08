"""System health and readiness probes."""
import os
import time

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/v1/system", tags=["system"])


@router.get("/health")
async def health():
    return {"status": "alive", "pid": os.getpid(), "timestamp": time.time()}


@router.get("/ready")
async def ready(request: Request):
    engine_ready = hasattr(request.app.state, "engine_manager")
    queue = getattr(request.app.state, "service_queue", None)
    if not engine_ready:
        raise HTTPException(status_code=503, detail={"code": "ENGINE_NOT_READY", "message": "OCR engine manager not ready"})
    if queue is None:
        raise HTTPException(status_code=503, detail={"code": "QUEUE_NOT_READY", "message": "Service queue not ready"})
    if queue.queue.full():
        raise HTTPException(status_code=503, detail={"code": "QUEUE_FULL", "message": "Queue full"})

    loaded = []
    try:
        loaded = request.app.state.engine_manager.list_loaded()
    except Exception:
        loaded = []
    return {
        "status": "ready",
        "models": loaded,
        "queue_depth": queue.queue.qsize(),
        "queue_max": queue.max_pending,
    }
