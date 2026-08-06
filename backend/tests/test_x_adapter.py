"""X adapter authentication flow tests (tweepy-backed client)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.exceptions import (
    AuthenticationRequiredError,
    NetworkError,
    PermissionDeniedError,
    RateLimitError,
)
from app.adapters.x import XAdapter
from app.adapters.x.client import XClient
from app.adapters.x.errors import map_tweepy_error


class _FakeClient:
    """Stand-in for XClient that records calls and returns canned payloads."""

    def __init__(self, **responses) -> None:
        self.responses = responses
        self.calls: list[str] = []

    async def fetch_me(self):
        self.calls.append("fetch_me")
        if "fetch_me" in self.responses:
            raise self.responses["fetch_me"]
        return {"data": {"id": "123", "name": "Test User", "username": "testuser"}}

    async def fetch_user_by_username(self, username):
        self.calls.append(f"fetch_user:{username}")
        if "fetch_user" in self.responses:
            raise self.responses["fetch_user"]
        return {
            "data": {
                "id": "44196397",
                "name": "Elon Musk",
                "username": "elonmusk",
                "profile_image_url": "https://example.com/avatar.png",
            }
        }

    async def fetch_user_tweets(self, user_id, **kwargs):
        self.calls.append(f"tweets:{user_id}")
        return {
            "data": [
                {
                    "id": "t1",
                    "text": "hello",
                    "created_at": "2026-01-01T00:00:00Z",
                    "public_metrics": {"like_count": 3, "reply_count": 1},
                }
            ]
        }

    async def fetch_tweets_by_ids(self, ids):
        self.calls.append("metrics")
        return {"data": []}

    async def search_recent(self, query, **kwargs):
        self.calls.append("search")
        return {"data": [], "includes": {"users": {}}}

    async def close(self):
        self.calls.append("close")


def _adapter_with(monkeypatch, fake: _FakeClient, *, username: str | None = "elonmusk") -> XAdapter:
    adapter = XAdapter(bearer_token="tok", username=username)
    monkeypatch.setattr(adapter, "_client_or_create", lambda: fake)
    return adapter


@pytest.mark.asyncio
async def test_me_preferred_for_user_context_token(monkeypatch):
    """User-context tokens authenticate directly via /users/me."""
    fake = _FakeClient()
    adapter = _adapter_with(monkeypatch, fake)
    profile = await adapter.fetch_account_profile()
    assert profile.platform_user_id == "123"
    assert fake.calls == ["fetch_me"]


@pytest.mark.asyncio
async def test_username_lookup_used_when_me_unavailable(monkeypatch):
    """App-only Bearer Token: /users/me 401 -> /users/by/username."""
    fake = _FakeClient(
        fetch_me=AuthenticationRequiredError("Token 无效或已过期"),
    )
    adapter = _adapter_with(monkeypatch, fake)
    profile = await adapter.fetch_account_profile()
    assert profile.platform_user_id == "44196397"
    assert profile.username == "elonmusk"
    assert fake.calls == ["fetch_me", "fetch_user:elonmusk"]


@pytest.mark.asyncio
async def test_username_required_for_app_only_flow(monkeypatch):
    """Without a username the app-only flow fails with a clear message."""
    fake = _FakeClient(
        fetch_me=AuthenticationRequiredError("Token 无效或已过期"),
    )
    adapter = _adapter_with(monkeypatch, fake, username=None)
    with pytest.raises(AuthenticationRequiredError) as exc:
        await adapter.fetch_account_profile()
    assert "X 用户名" in str(exc.value)


@pytest.mark.asyncio
async def test_fetch_posts_uses_resolved_user_id(monkeypatch):
    """fetch_posts must target the resolved user id, not a pending id."""
    fake = _FakeClient(
        fetch_me=PermissionDeniedError("app-only"),
    )
    adapter = _adapter_with(monkeypatch, fake, username="creatorpulse")
    posts = await adapter.fetch_posts(limit=5)
    assert len(posts) == 1
    assert posts[0].platform_post_id == "t1"
    assert posts[0].like_count == 3
    assert fake.calls[0] == "fetch_user:creatorpulse"
    assert any(c.startswith("tweets:") for c in fake.calls)


def test_map_tweepy_errors():
    """tweepy error types map to CreatorPulse adapter errors."""
    import tweepy

    class _Resp:
        status_code = 429
        reason = "Too Many Requests"

        def json(self):
            return {}

    rate = map_tweepy_error(
        tweepy.TooManyRequests(_Resp(), response_json={}, reset_time=1700000000),
        context="test",
    )
    assert isinstance(rate, RateLimitError)
    assert rate.diagnostic.get("rate_limit_reset_at")

    auth = map_tweepy_error(tweepy.Unauthorized(_Resp()), context="test")
    assert isinstance(auth, AuthenticationRequiredError)

    forbidden = map_tweepy_error(tweepy.Forbidden(_Resp()), context="test")
    assert isinstance(forbidden, PermissionDeniedError)

    net = map_tweepy_error(TimeoutError(), context="test")
    assert isinstance(net, NetworkError)


def test_generic_error_keeps_message():
    """Transport failures keep their message, not just the class name."""
    err = map_tweepy_error(
        ValueError("Invalid proxy URL"),
        context="fetch_user",
    )
    assert isinstance(err, NetworkError)
    assert "ValueError" in err.message
    assert "Invalid proxy URL" in err.message
    assert err.diagnostic.get("error") == "Invalid proxy URL"


@pytest.mark.asyncio
async def test_x_client_close_closes_session():
    """XClient.close closes the wrapped aiohttp session when one is set.

    tweepy 4.x AsyncClient has no ``close`` method; it creates a throwaway
    aiohttp session per request unless a session is assigned. XClient assigns
    one when a proxy is configured, so close must release that session.
    """
    class _Session:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    class _Inner:
        def __init__(self) -> None:
            self.session = _Session()

    inner = _Inner()
    client = XClient("tok")
    client._client = inner
    await client.close()
    assert inner.session.closed is True
    assert client._client is None


@pytest.mark.asyncio
async def test_fetch_posts_passes_start_time(monkeypatch):
    """since is forwarded to the X API as start_time."""
    captured = {}

    class _CaptureClient(_FakeClient):
        async def fetch_user_tweets(self, user_id, **kwargs):
            captured.update(kwargs)
            return {"data": []}

    fake = _CaptureClient(fetch_me=PermissionDeniedError("app-only"))
    adapter = XAdapter(bearer_token="tok", username="u")
    monkeypatch.setattr(adapter, "_client_or_create", lambda: fake)
    adapter._me = {"id": "1", "username": "u"}
    since = datetime(2026, 1, 1, tzinfo=UTC)
    await adapter.fetch_posts(since=since, limit=5)
    assert captured["start_time"] == "2026-01-01T00:00:00Z"
    assert captured["max_results"] == 5
