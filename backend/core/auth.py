"""API Key authentication middleware — verify + rate-limit per key.

Usage (in routes):
    from core.auth import require_auth
    @router.get("/protected")
    async def protected_route(tenant: dict = Depends(require_auth)):
        ...
"""
import hashlib
import os
import logging
from fastapi import Security, HTTPException, Request
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyManager:
    """Verify API keys against a database (lazy-imported)."""

    def __init__(self):
        self._db = None

    async def _get_db(self):
        if self._db is not None:
            return self._db
        # Lazy import — Codex owns backend/db/ schema
        try:
            from db.vault_db import _connect
            self._db = _connect()
        except Exception:
            self._db = False  # mark as unavailable
        return self._db

    async def verify(self, key: str) -> dict:
        """Return tenant dict if valid, raise 401/403 otherwise."""
        api_required = os.environ.get("VONISH_API_KEY_REQUIRED", "true").lower() == "true"

        if not key:
            if api_required:
                raise HTTPException(401, "X-API-Key header required")
            return {"id": "default", "name": "default", "rate_limit": 1000}

        hashed = hashlib.sha256(key.encode()).hexdigest()

        conn = await self._get_db()
        if conn is False:
            raise HTTPException(503, "Auth database unavailable")

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, COALESCE(rate_limit, 60) AS rate_limit "
                "FROM api_keys WHERE key_hash = ? AND revoked = 0",
                (hashed,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(403, "Invalid or revoked API key")
            return {"id": row[0], "name": row[1], "rate_limit": row[2]}
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Auth DB error: {e}")
            raise HTTPException(503, "Auth database error")
        finally:
            try:
                conn.close()
            except Exception:
                pass


# Singleton
key_manager = APIKeyManager()


async def require_auth(
    request: Request,
    x_api_key: str = Security(api_key_header),
) -> dict:
    """FastAPI Dependency: verify key + enforce rate limit."""
    tenant = await key_manager.verify(x_api_key)

    # Rate-limit check — lazy import to avoid cycle
    from core.rate_limit import rate_limiter
    allowed = await rate_limiter.is_allowed(tenant["id"], tenant["rate_limit"])
    if not allowed:
        raise HTTPException(429, "Rate limit exceeded. Retry after a moment.")

    return tenant
