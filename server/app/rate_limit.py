"""Simple in-memory sliding-window rate limiter (per IP)."""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from .config import settings


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        bucket = self._hits[key]
        cutoff = now - self.window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


_api_limiter: SlidingWindowLimiter | None = None
_orders_limiter: SlidingWindowLimiter | None = None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    """HTTP middleware function (mounted in main.py)."""
    if not settings.rate_limit_enabled:
        return await call_next(request)

    global _api_limiter, _orders_limiter
    if _api_limiter is None:
        _api_limiter = SlidingWindowLimiter(settings.rate_limit_api)
    if _orders_limiter is None:
        _orders_limiter = SlidingWindowLimiter(settings.rate_limit_orders)

    path = request.url.path
    if path.startswith("/api/"):
        ip = _client_ip(request)
        limiter = _orders_limiter if (path == "/api/orders" and request.method == "POST") else _api_limiter
        if not limiter.allow(ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Слишком много запросов. Попробуйте позже."},
            )
    return await call_next(request)


def reset_limiters() -> None:
    """Used by tests."""
    global _api_limiter, _orders_limiter
    _api_limiter = None
    _orders_limiter = None
