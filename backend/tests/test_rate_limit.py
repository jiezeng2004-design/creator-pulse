"""Rate limiting must actually be enforced on router-mounted API routes.

Regression context: slowapi's middleware exempts any request whose matched route
has no ``endpoint`` attribute. Starlette >= 1.3 wraps ``include_router`` results
in ``_IncludedRouter``, so every CreatorPulse endpoint was silently exempt and
the configured ``default_limits`` never applied.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.ratelimit import (
    FixedWindowRateLimiter,
    RateLimitMiddleware,
    client_key,
)
from app.main import create_app


def test_allows_up_to_limit_then_blocks():
    limiter = FixedWindowRateLimiter(limit=3, window_seconds=60)
    results = [limiter.check("a") for _ in range(4)]
    assert [allowed for allowed, _, _ in results] == [True, True, True, False]
    assert [remaining for _, remaining, _ in results] == [2, 1, 0, 0]


def test_window_resets_after_expiry():
    limiter = FixedWindowRateLimiter(limit=2, window_seconds=10)
    assert limiter.check("a", now=100.0)[0] is True
    assert limiter.check("a", now=101.0)[0] is True
    assert limiter.check("a", now=102.0)[0] is False
    # A new window starts once the old one elapses.
    assert limiter.check("a", now=111.0)[0] is True


def test_keys_are_tracked_independently():
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=60)
    assert limiter.check("a")[0] is True
    assert limiter.check("a")[0] is False
    assert limiter.check("b")[0] is True


def test_retry_after_is_at_least_one_second():
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=30)
    limiter.check("a", now=0.0)
    allowed, _, retry_after = limiter.check("a", now=29.9)
    assert allowed is False
    assert retry_after >= 1


@pytest.mark.parametrize(
    ("limit", "window"),
    [(0, 60), (5, 0)],
)
def test_rejects_nonsense_configuration(limit, window):
    with pytest.raises(ValueError):
        FixedWindowRateLimiter(limit=limit, window_seconds=window)


def test_client_key_prefers_forwarded_header():
    class _Req:
        headers = {"x-forwarded-for": "9.9.9.9, 10.0.0.1"}
        client = None

    assert client_key(_Req()) == "9.9.9.9"  # type: ignore[arg-type]


async def test_router_routes_are_rate_limited():
    """The real app must return 429 for router-mounted paths once over budget."""
    app = create_app()
    # Replace the app limiter with a strict one on the installed middleware.
    strict = FixedWindowRateLimiter(limit=3, window_seconds=60)
    for middleware in app.user_middleware:
        if middleware.cls is RateLimitMiddleware:
            middleware.kwargs["limiter"] = strict

    transport = ASGITransport(app=app, client=("1.2.3.4", 5555))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        statuses = [(await ac.get("/api/platforms")).status_code for _ in range(5)]
        blocked = await ac.get("/api/platforms")

    assert statuses[:3] == [200, 200, 200], statuses
    assert 429 in statuses, statuses
    assert blocked.status_code == 429
    assert blocked.headers["content-type"].startswith("application/json")
    assert "detail" in blocked.json()
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_docs_are_exempt():
    """Interactive docs stay reachable even when the API budget is spent."""
    app = create_app()
    strict = FixedWindowRateLimiter(limit=1, window_seconds=60)
    for middleware in app.user_middleware:
        if middleware.cls is RateLimitMiddleware:
            middleware.kwargs["limiter"] = strict

    transport = ASGITransport(app=app, client=("1.2.3.4", 5555))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        assert (await ac.get("/api/platforms")).status_code == 200
        assert (await ac.get("/api/platforms")).status_code == 429
        assert (await ac.get("/openapi.json")).status_code == 200


async def test_health_is_exempt():
    """The health probe (polled every 10s by the UI) must never consume budget."""
    app = create_app()
    strict = FixedWindowRateLimiter(limit=1, window_seconds=60)
    for middleware in app.user_middleware:
        if middleware.cls is RateLimitMiddleware:
            middleware.kwargs["limiter"] = strict

    transport = ASGITransport(app=app, client=("1.2.3.4", 5555))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        assert (await ac.get("/api/health")).status_code == 200
        assert (await ac.get("/api/health")).status_code == 200
        assert (await ac.get("/api/health")).status_code == 200
