"""Toutiao adapter — login + experimental content read."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.adapters.base import PlatformAdapter
from app.adapters.browser import BrowserSession
from app.adapters.exceptions import (
    AuthenticationRequiredError,
    NetworkError,
    UnsupportedFeatureError,
)
from app.adapters.toutiao.pages.comments import CommentsPage
from app.adapters.toutiao.pages.content_list import ContentListPage
from app.adapters.toutiao.pages.creator_center import CreatorCenterPage
from app.adapters.types import (
    AccountProfile,
    AuthenticationResult,
    PlatformComment,
    PlatformPost,
    PlatformPostMetrics,
)


class ToutiaoAdapter(PlatformAdapter):
    platform = "toutiao"
    experimental = True

    def __init__(self, profile_path: Path, *, headless: bool = False) -> None:
        self.profile_path = profile_path
        self.headless = headless
        self._session: BrowserSession | None = None
        self._posts_cache: dict[str, PlatformPost] = {}

    async def _ensure(self) -> BrowserSession:
        if self._session is None:
            self._session = BrowserSession(self.profile_path, headless=self.headless)
            try:
                await self._session.start()
            except Exception as exc:  # noqa: BLE001
                self._session = None
                raise NetworkError(f"无法启动浏览器: {exc.__class__.__name__}") from exc
        return self._session

    async def start_login(self) -> str:
        s = await self._ensure()
        await CreatorCenterPage(s.page).open_login()
        return "已打开今日头条创作者登录页，请手动登录后点击「检查登录状态」。"

    async def check_authentication(self) -> AuthenticationResult:
        s = await self._ensure()
        ok = await CreatorCenterPage(s.page).is_authenticated()
        if not ok:
            return AuthenticationResult(authenticated=False, message="未检测到头条登录态")
        return AuthenticationResult(
            authenticated=True,
            message="头条登录态有效（实验性）",
            display_name="头条账号",
            platform_user_id=f"toutiao-{abs(hash(str(self.profile_path))) % 10**10}",
        )

    async def fetch_account_profile(self) -> AccountProfile:
        auth = await self.check_authentication()
        if not auth.authenticated:
            raise AuthenticationRequiredError(auth.message)
        return AccountProfile(
            platform_user_id=auth.platform_user_id or "toutiao-unknown",
            display_name=auth.display_name or "头条账号",
        )

    async def fetch_posts(
        self, since: datetime | None = None, limit: int = 50
    ) -> list[PlatformPost]:
        await self.fetch_account_profile()
        s = await self._ensure()
        posts = await ContentListPage(s.page).fetch_posts(limit=limit)
        # If nothing captured, do not invent data — surface unsupported clearly via empty + note
        self._posts_cache = {p.platform_post_id: p for p in posts}
        return posts

    async def fetch_post_metrics(self, post_ids: list[str]) -> list[PlatformPostMetrics]:
        out: list[PlatformPostMetrics] = []
        for pid in post_ids:
            p = self._posts_cache.get(pid)
            if not p:
                out.append(PlatformPostMetrics(platform_post_id=pid))
            else:
                out.append(
                    PlatformPostMetrics(
                        platform_post_id=pid,
                        view_count=p.view_count,
                        impression_count=p.impression_count,
                        like_count=p.like_count,
                        favorite_count=p.favorite_count,
                        share_count=p.share_count,
                        comment_count=p.comment_count,
                    )
                )
        return out

    async def fetch_comments(
        self, post_id: str, since: datetime | None = None, limit: int = 100
    ) -> list[PlatformComment]:
        s = await self._ensure()
        try:
            return await CommentsPage(s.page).fetch_comments(post_id, limit=limit)
        except Exception as exc:  # noqa: BLE001
            raise UnsupportedFeatureError(
                "头条评论读取实验性功能暂不可用",
                diagnostic={"error": str(exc)[:200]},
            ) from exc

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
