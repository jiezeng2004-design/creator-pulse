"""X (Twitter) official API v2 adapter backed by tweepy."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.adapters.base import PlatformAdapter
from app.adapters.exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    UnsupportedFeatureError,
)
from app.adapters.types import (
    AccountProfile,
    AuthenticationResult,
    PlatformComment,
    PlatformPost,
    PlatformPostMetrics,
)
from app.adapters.x.client import XClient
from app.adapters.x.mapper import parse_metrics, parse_reply, parse_tweet
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class XAdapter(PlatformAdapter):
    platform = "x"
    experimental = False

    def __init__(
        self,
        bearer_token: str | None = None,
        username: str | None = None,
    ) -> None:
        settings = get_settings()
        self._token = (bearer_token or settings.x_bearer_token or "").strip()
        self._username = (username or "").strip().lstrip("@")
        self._client: XClient | None = None
        self._me: dict[str, Any] | None = None

    def _ensure_token(self) -> None:
        if not self._token:
            raise AuthenticationRequiredError(
                "未配置 X Bearer Token。请在设置页「X API 配置」中填写 X Developer Portal 的 Bearer Token。",
                diagnostic={"hint": "Settings -> X API 配置"},
            )

    def _client_or_create(self) -> XClient:
        self._ensure_token()
        if self._client is None:
            settings = get_settings()
            self._client = XClient(
                self._token,
                consumer_key=settings.x_client_id,
                consumer_secret=settings.x_client_secret,
                access_token=settings.x_access_token,
                access_token_secret=settings.x_access_token_secret,
            )
        return self._client

    async def check_authentication(self) -> AuthenticationResult:
        try:
            self._ensure_token()
            profile = await self.fetch_account_profile()
            return AuthenticationResult(
                authenticated=True,
                message="X API 鉴权成功",
                display_name=profile.display_name,
                username=profile.username,
                platform_user_id=profile.platform_user_id,
                avatar_url=profile.avatar_url,
            )
        except AuthenticationRequiredError as exc:
            return AuthenticationResult(authenticated=False, message=exc.message)
        except PermissionDeniedError as exc:
            return AuthenticationResult(authenticated=False, message=exc.message)

    async def _fetch_me(self) -> dict[str, Any]:
        """Fetch the authenticated user via /users/me (user-context tokens)."""
        payload = await self._client_or_create().fetch_me()
        user = payload.get("data") or {}
        if not user.get("id"):
            raise AuthenticationRequiredError("无法获取 X 账号信息")
        self._me = user
        return user

    async def _resolve_user(self) -> dict[str, Any]:
        """Resolve the account by username (app-only Bearer Token flow)."""
        if self._me:
            return self._me
        if not self._username:
            raise AuthenticationRequiredError(
                "X 账号需要填写 X 用户名（不含 @）。请在添加账号或编辑账号时填写。",
                diagnostic={"hint": "Accounts -> 添加 X 账号 -> X 用户名"},
            )
        payload = await self._client_or_create().fetch_user_by_username(self._username)
        user = payload.get("data") or {}
        if not user.get("id"):
            raise AuthenticationRequiredError(
                f"未找到 X 用户 @{self._username}，请检查用户名是否拼写正确",
            )
        self._me = user
        return user

    async def fetch_account_profile(self) -> AccountProfile:
        try:
            user = await self._fetch_me()
        except (AuthenticationRequiredError, PermissionDeniedError):
            # App-only Bearer Token: /users/me is unavailable, resolve by
            # the account username instead.
            user = await self._resolve_user()
        return AccountProfile(
            platform_user_id=str(user["id"]),
            display_name=user.get("name") or user.get("username") or "X User",
            username=user.get("username"),
            avatar_url=user.get("profile_image_url"),
            raw={"id": user.get("id"), "username": user.get("username")},
        )

    async def fetch_posts(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[PlatformPost]:
        user = await self._resolve_user()
        start_time = None
        if since:
            start_time = since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = await self._client_or_create().fetch_user_tweets(
            str(user["id"]),
            max_results=limit,
            start_time=start_time,
        )
        username = user.get("username") or "i"
        return [parse_tweet(item, username=username) for item in payload.get("data") or []][:limit]

    async def fetch_post_metrics(self, post_ids: list[str]) -> list[PlatformPostMetrics]:
        if not post_ids:
            return []
        payload = await self._client_or_create().fetch_tweets_by_ids(post_ids)
        return [parse_metrics(item) for item in payload.get("data") or []]

    async def fetch_comments(
        self,
        post_id: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformComment]:
        """Fetch replies via recent search on conversation_id.

        May require elevated API access; surface UnsupportedFeatureError clearly.
        """
        try:
            payload = await self._client_or_create().search_recent(
                f"conversation_id:{post_id}",
                max_results=limit,
            )
        except PermissionDeniedError as exc:
            raise UnsupportedFeatureError(
                "当前 X API 权限无法检索会话回复。可在原平台查看评论。",
                diagnostic=exc.diagnostic,
            ) from exc

        users = payload.get("includes", {}).get("users", {})
        comments: list[PlatformComment] = []
        for item in payload.get("data") or []:
            c = parse_reply(item, post_id=post_id, users=users)
            if c:
                comments.append(c)
            if len(comments) >= limit:
                break
        if since:
            comments = [
                c for c in comments if c.published_at is None or c.published_at >= since
            ]
        return comments[:limit]

    async def start_login(self) -> str:
        return (
            "X 使用官方 API Token，无需浏览器登录。"
            "请在设置页「X API 配置」填写 Bearer Token 后点击「检查登录状态」."
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
