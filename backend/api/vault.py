"""FastAPI vault routes"""
import logging
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/vault", tags=["vault"])
logger = logging.getLogger(__name__)


def _get_service(request: Request):
    svc = getattr(request.app.state, "vault_service", None)
    if svc is None:
        from services.vault_service import VaultService
        svc = VaultService()
        request.app.state.vault_service = svc
    return svc


class SessionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color_tag: Optional[str] = None


class MoveRequest(BaseModel):
    evidence_ids: list[str]
    session_id: Optional[str] = None


@router.post("/sessions")
async def create_session(request: Request, data: SessionCreate):
    return await _get_service(request).create_session(data.name, data.description, data.color_tag)


@router.get("/sessions")
async def list_sessions(request: Request):
    return await _get_service(request).list_sessions()


@router.get("/file/{relative_path:path}")
async def vault_file(relative_path: str):
    """Serve vault-local image files through the backend.

    中文说明：
    前端运行在 Vite/Tauri WebView 里，不能可靠读取 file:// 或自己拼
    /vault-file 路径。这里做路径校验后返回文件，避免任意文件读取。
    """
    from services.thumbnail import resolve_vault_path

    try:
        path = resolve_vault_path(relative_path)
    except ValueError:
        raise HTTPException(400, "Invalid vault file path")
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Vault file not found")
    return FileResponse(path)


@router.get("/evidences")
async def list_evidences(
    request: Request,
    session_id: Optional[str] = Query(None),
    scene_type: Optional[str] = Query(None),
    model_tier: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await _get_service(request).list_evidences(
        session_id=session_id,
        scene_type=scene_type,
        model_tier=model_tier,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/evidences/{evidence_id}")
async def get_evidence(request: Request, evidence_id: str):
    ev = await _get_service(request).get_evidence(evidence_id)
    if not ev:
        raise HTTPException(404, "Evidence not found")
    return ev


@router.post("/evidences/{evidence_id}/reprocess")
async def reprocess_evidence(request: Request, evidence_id: str):
    ev = await _get_service(request).get_evidence(evidence_id)
    if not ev:
        raise HTTPException(404, "Evidence not found")
    await _get_service(request).update_status(evidence_id, "processing")
    return {"status": "queued", "evidence_id": evidence_id}


@router.post("/evidences/{evidence_id}/save-result")
async def save_ocr_result(request: Request, evidence_id: str, payload: dict):
    """Called after OCR completes for a reprocess request.
    Updates the evidence in vault with new results."""
    svc = _get_service(request)
    ev = await svc.get_evidence(evidence_id)
    if not ev:
        raise HTTPException(404, "Evidence not found")
    await svc.update_status(evidence_id,
                            "complete" if not payload.get("error") else "failed",
                            payload.get("error", {}).get("message"))
    return {"ok": True}


@router.delete("/evidences/{evidence_id}")
async def delete_evidence(request: Request, evidence_id: str):
    await _get_service(request).delete_evidence(evidence_id)
    return {"ok": True}


@router.post("/evidences/batch-delete")
async def batch_delete(request: Request, payload: dict):
    await _get_service(request).batch_delete(payload.get("evidence_ids", []))
    return {"ok": True}


@router.post("/evidences/move-to-session")
async def move_to_session(request: Request, data: MoveRequest):
    await _get_service(request).move_to_session(data.evidence_ids, data.session_id)
    return {"ok": True}


@router.post("/evidences/batch-export")
async def batch_export(request: Request, payload: dict):
    format = payload.get("format", "txt")
    results = await _get_service(request).batch_export(payload.get("evidence_ids", []), format)
    return {"ok": True, "exported": len(results), "format": format}
