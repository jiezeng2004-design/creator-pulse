"""Xiaohongshu adapter — login skeleton + experimental read (may return empty)."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from app.adapters.base import PlatformAdapter
from app.adapters.browser import BrowserSession
from app.adapters.exceptions import (
    AuthenticationRequiredError,
    NetworkError,
)
from app.adapters.types import (
    AccountProfile,
    AuthenticationResult,
    PlatformComment,
    PlatformPost,
    PlatformPostMetrics,
)
from app.adapters.xiaohongshu.pages.comments import CommentsPage
from app.adapters.xiaohongshu.pages.content_list import ContentListPage
from app.adapters.xiaohongshu.pages.creator_center import CreatorCenterPage

logger = logging.getLogger(__name__)


class XiaohongshuAdapter(PlatformAdapter):
    platform = "xiaohongshu"
    experimental = True

    def __init__(self, profile_path: Path, *, headless: bool = False) -> None:
        self.profile_path = profile_path
        self.headless = headless
        self._session: BrowserSession | None = None
        self._posts_cache: dict[str, PlatformPost] = {}

    async def _ensure(self, *, headed: bool | None = None) -> BrowserSession:
        if headed is True:
            self.headless = False
        if self._session is not None:
            return self._session
        want_headless = False if headed is True else self.headless
        self._session = BrowserSession(self.profile_path, headless=want_headless)
        try:
            await self._session.start()
        except Exception as exc:  # noqa: BLE001
            self._session = None
            raise NetworkError(
                f"无法启动浏览器: {exc.__class__.__name__}",
                diagnostic={"error": str(exc)[:200]},
            ) from exc
        return self._session

    async def start_login(self) -> str:
        s = await self._ensure(headed=True)
        await CreatorCenterPage(s.page).open_login()
        return (
            "已打开小红书创作者登录页（实验性）。请手动登录；"
            "若遇验证码请在浏览器内完成。登录后点击「检查登录状态」。"
        )

    async def check_authentication(self) -> AuthenticationResult:
        s = await self._ensure()
        page = s.page
        center = CreatorCenterPage(page)

        # Check if still on login page
        try:
            if await center.is_login_page():
                return AuthenticationResult(
                    authenticated=False,
                    message="仍在登录页，请完成登录（含验证码）后再检查",
                )
        except Exception:  # noqa: BLE001
            pass

        ok = await center.is_authenticated()
        if not ok:
            return AuthenticationResult(authenticated=False, message="未检测到小红书登录态")

        name = await center.get_display_name()
        return AuthenticationResult(
            authenticated=True,
            message="小红书登录态有效（实验性，页面结构变化频繁）",
            display_name=name or "小红书账号",
            platform_user_id=f"xhs-{int(hashlib.sha256(str(self.profile_path).encode()).hexdigest(), 16) % 10**10}",
        )

    async def fetch_account_profile(self) -> AccountProfile:
        auth = await self.check_authentication()
        if not auth.authenticated:
            raise AuthenticationRequiredError(auth.message)
        return AccountProfile(
            platform_user_id=auth.platform_user_id or "xhs-unknown",
            display_name=auth.display_name or "小红书账号",
            username=None,
            avatar_url=None,
        )

    async def fetch_posts(
        self, since: datetime | None = None, limit: int = 50
    ) -> list[PlatformPost]:
        await self.fetch_account_profile()
        s = await self._ensure()
        posts = await ContentListPage(s.page).fetch_all_posts(limit=limit)
        if not posts:
            logger.info("XHS content list returned empty (may need manual refresh)")
        self._posts_cache = {p.platform_post_id: p for p in posts}
        return posts

    async def fetch_post_metrics(self, post_ids: list[str]) -> list[PlatformPostMetrics]:
        out: list[PlatformPostMetrics] = []
        for pid in post_ids:
            p = self._posts_cache.get(pid)
            out.append(
                PlatformPostMetrics(
                    platform_post_id=pid,
                    view_count=p.view_count if p else None,
                    impression_count=p.impression_count if p else None,
                    like_count=p.like_count if p else None,
                    favorite_count=p.favorite_count if p else None,
                    share_count=p.share_count if p else None,
                    repost_count=None,
                    comment_count=p.comment_count if p else None,
                    raw_metrics=p.raw_metrics if p else {},
                )
            )
        return out

    async def fetch_comments(
        self, post_id: str, since: datetime | None = None, limit: int = 100
    ) -> list[PlatformComment]:
        s = await self._ensure()
        comments = await CommentsPage(s.page).fetch_comments(post_id, limit=limit)
        if since:
            comments = [
                c for c in comments if c.published_at is None or c.published_at >= since
            ]
        return comments[:limit]

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
