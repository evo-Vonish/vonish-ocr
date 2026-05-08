"""Admin API for service API keys."""
import secrets
import time

from fastapi import APIRouter, Body, Header, HTTPException, Request

router = APIRouter()


@router.post("/keys")
async def create_api_key(request: Request, payload: dict = Body(...)):
    """Create an API key.

    The raw key is returned once. SQLite stores only a SHA-256 hash plus a short
    prefix for display/revocation.
    """
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail={"code": "MISSING_NAME", "message": "缺少密钥名称"})
    rate_limit = int(payload.get("rate_limit") or 60)
    tenant_id = (payload.get("tenant_id") or "default").strip() or "default"
    raw_key = "vocr_" + secrets.token_urlsafe(32)
    key = await request.app.state.admin_db.create_api_key(
        name=name,
        raw_key=raw_key,
        tenant_id=tenant_id,
        rate_limit=max(1, min(6000, rate_limit)),
    )
    return key


@router.get("/keys")
async def list_api_keys(request: Request):
    rows = await request.app.state.admin_db.list_api_keys()
    return {"keys": rows, "time": time.time()}


@router.delete("/keys/{key_or_prefix}")
async def revoke_api_key(request: Request, key_or_prefix: str):
    ok = await request.app.state.admin_db.revoke_api_key(key_or_prefix)
    return {"revoked": ok, "key": key_or_prefix}


@router.post("/config/reload")
async def reload_config(admin_key: str | None = Header(None)):
    """HTTP trigger for dynamic config reload.

    TODO: validate admin_key once administrator roles are separated from normal API keys.
    """
    try:
        from core.config import config

        config.reload()
        return {"reloaded": True, "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "CONFIG_RELOAD_FAILED", "message": str(e)})
