"""API key authentication for service routes.

Only `/api/v1/*` is protected by the middleware in `main.py`. Legacy desktop
routes under `/v1/*` stay local-first and compatible with the Tauri frontend.
"""
import os

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from core.rate_limit import rate_limiter

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyManager:
    """Verify API keys against AdminDB.

    The database stores only SHA-256 hashes; raw keys are never persisted.
    """

    def __init__(self, db):
        self.db = db

    async def verify(self, key: str | None) -> dict:
        required = os.getenv("VONISH_API_KEY_REQUIRED", "true").lower() == "true"
        if not key:
            if required:
                raise HTTPException(status_code=401, detail={"code": "API_KEY_REQUIRED", "message": "X-API-Key required"})
            return {"id": "default", "tenant_id": "default", "name": "default", "rate_limit": 1000}

        row = await self.db.verify_api_key(key)
        if not row:
            raise HTTPException(status_code=403, detail={"code": "INVALID_API_KEY", "message": "Invalid or revoked API key"})
        return {
            "id": row["key_hash"],
            "tenant_id": row.get("tenant_id") or "default",
            "name": row.get("name") or row.get("key_prefix") or "api-key",
            "rate_limit": int(row.get("rate_limit") or 60),
            "key_prefix": row.get("key_prefix"),
        }


async def require_auth(request: Request, x_api_key: str = Security(api_key_header)) -> dict:
    """FastAPI dependency for API key verification and per-key RPM limiting."""
    manager = APIKeyManager(request.app.state.admin_db)
    tenant = await manager.verify(x_api_key)
    if not await rate_limiter.is_allowed(tenant["id"], tenant["rate_limit"]):
        raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": "Rate limit exceeded"})
    return tenant


async def authenticate_api_request(request: Request) -> dict:
    """Middleware helper for protecting `/api/v1/*` without touching every route."""
    return await require_auth(request, request.headers.get("X-API-Key"))
