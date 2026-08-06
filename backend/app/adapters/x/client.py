"""Thin tweepy AsyncClient wrapper returning plain dicts.

The wrapper owns the tweepy dependency boundary: adapters and mappers only ever
see standard Python dicts, never tweepy model objects. Errors are mapped to
CreatorPulse AdapterErrors here so callers do not need to know tweepy.
"""

from __future__ import annotations

from typing import Any

from app.adapters.exceptions import AuthenticationRequiredError
from app.adapters.x.errors import map_tweepy_error
from app.core.config import get_settings


class _ProxiedSession:
    """Wrap an aiohttp session so tweepy requests go through a fixed proxy.

    tweepy's AsyncClient creates ``aiohttp.ClientSession()`` with no proxy
    support and does ``async with session.request(...)`` per call. aiohttp's
    ``session.request`` returns an async context manager (not a coroutine), so
    this wrapper returns the same manager with the proxy injected, keeping the
    proxy scoped to X API traffic only.
    """

    def __init__(self, proxy: str) -> None:
        import aiohttp

        self._session = aiohttp.ClientSession()
        self._proxy = proxy

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        return self._session.request(method, url, proxy=self._proxy, **kwargs)

    async def close(self) -> None:
        await self._session.close()


def _data_to_dicts(payload: Any) -> list[dict[str, Any]]:
    """Convert a tweepy Response.data (models) into plain dicts."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item.data if hasattr(item, "data") else item for item in payload]
    return [payload.data if hasattr(payload, "data") else payload]


def _users_to_dicts(includes: Any) -> dict[str, dict[str, Any]]:
    """Map tweepy Response.includes['users'] to id -> plain dict."""
    if not includes:
        return {}
    users = includes.get("users") or []
    out: dict[str, dict[str, Any]] = {}
    for user in users:
        data = user.data if hasattr(user, "data") else user
        uid = str(data.get("id"))
        if uid:
            out[uid] = data
    return out


class XClient:
    """Async X API v2 client backed by tweepy."""

    def __init__(
        self,
        bearer_token: str,
        *,
        consumer_key: str = "",
        consumer_secret: str = "",
        access_token: str = "",
        access_token_secret: str = "",
    ) -> None:
        self._token = bearer_token
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._access_token = access_token
        self._access_token_secret = access_token_secret
        self._client: Any = None

    def _get(self) -> Any:
        if self._client is None:
            from tweepy.asynchronous import AsyncClient

            self._client = AsyncClient(
                bearer_token=self._token,
                consumer_key=self._consumer_key or None,
                consumer_secret=self._consumer_secret or None,
                access_token=self._access_token or None,
                access_token_secret=self._access_token_secret or None,
            )
            proxy = get_settings().x_proxy.strip()
            if proxy:
                self._client.session = _ProxiedSession(proxy)
        return self._client

    async def fetch_me(self) -> dict[str, Any]:
        if not (
            self._consumer_key
            and self._consumer_secret
            and self._access_token
            and self._access_token_secret
        ):
            raise AuthenticationRequiredError(
                "未配置 X OAuth 1.0a 用户凭据（Client ID/Secret + Access Token/Secret），"
                "无法调用 /users/me。将改用 X 用户名 + Bearer Token 解析账号。",
                diagnostic={"hint": "Settings -> X API 配置，或仅使用 Bearer Token 模式"},
            )
        try:
            resp = await self._get().get_me(user_auth=True)
            rows = _data_to_dicts(resp.data)
            return {"data": rows[0] if rows else {}}
        except Exception as exc:  # noqa: BLE001 - mapped below
            raise map_tweepy_error(exc, context="fetch_me") from exc

    async def fetch_user_by_username(self, username: str) -> dict[str, Any]:
        try:
            resp = await self._get().get_user(
                username=username,
                user_fields="id,name,username,profile_image_url",
            )
            rows = _data_to_dicts(resp.data)
            return {"data": rows[0] if rows else {}}
        except Exception as exc:  # noqa: BLE001
            raise map_tweepy_error(exc, context="fetch_user_by_username") from exc

    async def fetch_user_tweets(
        self,
        user_id: str,
        *,
        max_results: int = 50,
        start_time: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "max_results": max(5, min(int(max_results), 100)),
            "tweet_fields": "created_at,public_metrics,conversation_id",
            "exclude": "retweets,replies",
        }
        if start_time:
            params["start_time"] = start_time
        try:
            resp = await self._get().get_users_tweets(user_id, **params)
            return {"data": _data_to_dicts(resp.data)}
        except Exception as exc:  # noqa: BLE001
            raise map_tweepy_error(exc, context="fetch_user_tweets") from exc

    async def fetch_tweets_by_ids(self, ids: list[str]) -> dict[str, Any]:
        if not ids:
            return {"data": []}
        try:
            resp = await self._get().get_tweets(
                ids=ids[:100],
                tweet_fields="public_metrics",
            )
            return {"data": _data_to_dicts(resp.data)}
        except Exception as exc:  # noqa: BLE001
            raise map_tweepy_error(exc, context="fetch_tweets_by_ids") from exc

    async def search_recent(
        self,
        query: str,
        *,
        max_results: int = 100,
    ) -> dict[str, Any]:
        try:
            resp = await self._get().search_recent_tweets(
                query,
                max_results=max(10, min(int(max_results), 100)),
                tweet_fields="created_at,public_metrics,author_id,in_reply_to_user_id",
                expansions="author_id",
            )
            includes = resp.includes or {}
            return {
                "data": _data_to_dicts(resp.data),
                "includes": {"users": _users_to_dicts(includes)},
            }
        except Exception as exc:  # noqa: BLE001
            raise map_tweepy_error(exc, context="search_recent") from exc

    async def close(self) -> None:
        if self._client is not None:
            session = getattr(self._client, "session", None)
            if session is not None:
                await session.close()
            self._client = None


__all__ = ["XClient"]
