"""Minimal in-process rate limiting for the local API.

Why not slowapi: its middleware resolves the matched route via
``route.endpoint`` to decide whether a limit applies. Starlette >= 1.3 wraps
``include_router`` results in an ``_IncludedRouter`` object with no ``endpoint``
attribute, so every router-mounted path is treated as exempt and
``default_limits`` never fires. Because every CreatorPulse endpoint lives in a
router, that silently disabled all limiting.

This implementation is intentionally small: a fixed-window counter keyed by
client address, sufficient for protecting a single-user localhost service from
runaway loops or a misbehaving page.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

DEFAULT_LIMIT = 300
DEFAULT_WINDOW_SECONDS = 60


class FixedWindowRateLimiter:
    """Count requests per key inside a fixed time window."""

    def __init__(self, limit: int = DEFAULT_LIMIT, window_seconds: int = DEFAULT_WINDOW_SECONDS):
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # key -> (window_started_at, count)
        self._counters: dict[str, tuple[float, int]] = {}

    def check(self, key: str, *, now: float | None = None) -> tuple[bool, int, int]:
        """Register a hit for *key*.

        Returns ``(allowed, remaining, retry_after_seconds)``.
        """
        current = time.monotonic() if now is None else now
        with self._lock:
            window_start, count = self._counters.get(key, (current, 0))
            elapsed = current - window_start
            if elapsed >= self.window_seconds:
                window_start, count, elapsed = current, 0, 0.0

            retry_after = max(1, int(self.window_seconds - elapsed))
            if count >= self.limit:
                self._counters[key] = (window_start, count)
                return False, 0, retry_after

            count += 1
            self._counters[key] = (window_start, count)
            if len(self._counters) > 1024:
                # Bound memory: drop windows that expired before this sweep.
                expired = [
                    k
                    for k, (start, _) in self._counters.items()
                    if current - start >= self.window_seconds
                ]
                for k in expired:
                    del self._counters[k]
            return True, self.limit - count, retry_after

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()


def client_key(request: Request) -> str:
    """Identify the caller. Falls back to a constant for unknown transports."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a fixed-window limit to API routes."""

    def __init__(
        self,
        app,
        limiter: FixedWindowRateLimiter | None = None,
        *,
        exempt_paths: Iterable[str] = ("/docs", "/redoc", "/openapi.json"),
    ) -> None:
        super().__init__(app)
        self.limiter = limiter or FixedWindowRateLimiter()
        self.exempt_paths = tuple(exempt_paths)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path.startswith(self.exempt_paths):
            return await call_next(request)

        allowed, remaining, retry_after = self.limiter.check(client_key(request))
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试。"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.limiter.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(self.limiter.limit))
        response.headers.setdefault("X-RateLimit-Remaining", str(remaining))
        return response


__all__ = [
    "DEFAULT_LIMIT",
    "DEFAULT_WINDOW_SECONDS",
    "FixedWindowRateLimiter",
    "RateLimitMiddleware",
    "client_key",
]
