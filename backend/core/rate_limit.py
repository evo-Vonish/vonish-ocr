"""Token-bucket rate limiter — per API key, thread-safe.

Handles up to O(1000) tenants efficiently with dict + per-bucket locks.
"""
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """Leaky-bucket: refills continuously, capacity = rate tokens."""

    def __init__(self, rate: int, per_seconds: int = 60):
        self.rate = float(rate)
        self.per_seconds = per_seconds
        self.tokens = float(rate)
        self.last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to consume one token. Returns True if allowed."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last
            fill = elapsed * (self.rate / self.per_seconds)
            self.tokens = min(self.rate, self.tokens + fill)
            self.last = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


class RateLimiter:
    """Manages per-tenant token buckets."""

    def __init__(self):
        self.buckets: dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, tenant_id: str, rate: int) -> bool:
        """Check if *tenant_id* can make one more request at *rate* req/min."""
        bucket = self.buckets.get(tenant_id)
        if bucket is None:
            async with self._lock:
                bucket = self.buckets.setdefault(
                    tenant_id, TokenBucket(rate)
                )
        ok = await bucket.acquire()
        if not ok:
            logger.debug(f"Rate limit hit for tenant={tenant_id} rate={rate}/min")
        return ok


# Singleton — imported by auth.py
rate_limiter = RateLimiter()
