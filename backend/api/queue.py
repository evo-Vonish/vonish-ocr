"""Service queue REST API."""
import asyncio
import json
import os
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter()

_rate_windows: dict[str, list[float]] = {}


async def _tenant_from_key(request: Request, x_api_key: str | None):
    """Verify API key and apply a simple in-memory RPM limiter.

    Missing key maps to the built-in local tenant so existing desktop use stays
    frictionless. External callers should use keys from /api/v1/admin/keys.
    """
    if hasattr(request.state, "tenant"):
        return request.state.tenant

    if not x_api_key:
        return {"tenant_id": "default", "rate_limit": 600, "name": "local"}

    row = await request.app.state.admin_db.verify_api_key(x_api_key)
    if not row:
        raise HTTPException(status_code=401, detail={"code": "INVALID_API_KEY", "message": "API Key 无效或已撤销"})

    now = time.time()
    bucket_key = row["key_hash"]
    window = [ts for ts in _rate_windows.get(bucket_key, []) if now - ts < 60]
    if len(window) >= int(row.get("rate_limit") or 60):
        raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": "请求超过 API Key 速率限制"})
    window.append(now)
    _rate_windows[bucket_key] = window
    return row


def _upload_dir() -> Path:
    candidates = []
    if os.environ.get("VONISH_QUEUE_UPLOAD_DIR"):
        candidates.append(Path(os.environ["VONISH_QUEUE_UPLOAD_DIR"]))
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "VonishOCR" / "queue_uploads")
    candidates.append(Path.home() / ".vonishocr" / "queue_uploads")
    candidates.append(Path.cwd() / ".vocr" / "queue_uploads")

    for root in candidates:
        try:
            root.mkdir(parents=True, exist_ok=True)
            marker = root / ".write-test"
            marker.write_text("ok", encoding="utf-8")
            marker.unlink(missing_ok=True)
            return root
        except Exception:
            continue

    raise RuntimeError("No writable queue upload directory found. Set VONISH_QUEUE_UPLOAD_DIR to a writable path.")


@router.post("/submit")
async def submit_task(
    request: Request,
    file: UploadFile = File(...),
    model_tier: str = Form("auto"),
    priority: int = Form(0),
    x_api_key: str | None = Header(None),
):
    tenant = await _tenant_from_key(request, x_api_key)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_FILE", "message": "上传文件为空"})
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": "FILE_TOO_LARGE", "message": "单文件超过 50MB 限制"})

    safe_name = Path(file.filename or "upload.bin").name
    upload_path = _upload_dir() / f"{int(time.time() * 1000)}_{safe_name}"
    await asyncio.to_thread(upload_path.write_bytes, content)

    try:
        submitted = await request.app.state.service_queue.submit(
            file_path=upload_path,
            filename=safe_name,
            file_size=len(content),
            model_tier=model_tier,
            priority=priority,
            tenant_id=tenant["tenant_id"],
        )
    except RuntimeError as exc:
        if str(exc) == "QUEUE_BACKPRESSURE":
            raise HTTPException(status_code=429, detail={"code": "QUEUE_BACKPRESSURE", "message": "队列已满，请稍后重试"})
        raise
    return submitted


@router.get("/status/{task_id}")
async def get_status(request: Request, task_id: str, x_api_key: str | None = Header(None)):
    tenant = await _tenant_from_key(request, x_api_key)
    task = await request.app.state.admin_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})
    if tenant["tenant_id"] != "default" and task.get("tenant_id") != tenant["tenant_id"]:
        raise HTTPException(status_code=403, detail={"code": "TENANT_FORBIDDEN", "message": "无权访问该任务"})
    return {"task": request.app.state.service_queue._public_task(task)}


@router.get("/tasks")
async def list_tasks(request: Request, limit: int = 100, x_api_key: str | None = Header(None)):
    tenant = await _tenant_from_key(request, x_api_key)
    snapshot = await request.app.state.service_queue.snapshot(tenant_id=tenant["tenant_id"], limit=max(1, min(500, limit)))
    return snapshot


@router.post("/cancel/{task_id}")
async def cancel_task(request: Request, task_id: str, x_api_key: str | None = Header(None)):
    await _tenant_from_key(request, x_api_key)
    return {"task_id": task_id, "cancelled": await request.app.state.service_queue.cancel(task_id)}


@router.post("/retry/{task_id}")
async def retry_task(request: Request, task_id: str, x_api_key: str | None = Header(None)):
    await _tenant_from_key(request, x_api_key)
    return {"task_id": task_id, "queued": await request.app.state.service_queue.retry(task_id)}


@router.get("/stream")
async def queue_stream(request: Request):
    """SSE stream for the complete queue snapshot."""
    subscriber = request.app.state.service_queue.subscribe()

    async def generator():
        try:
            initial = await request.app.state.service_queue.snapshot()
            yield f"data: {json.dumps(initial, ensure_ascii=False)}\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(subscriber.get(), timeout=15)
                except asyncio.TimeoutError:
                    payload = await request.app.state.service_queue.snapshot()
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            request.app.state.service_queue.unsubscribe(subscriber)

    return StreamingResponse(generator(), media_type="text/event-stream")
