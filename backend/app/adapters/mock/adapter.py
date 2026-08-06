"""Mock adapters for demo mode — clearly synthetic data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.adapters.base import PlatformAdapter
from app.adapters.mock.types import MockScenario
from app.adapters.types import (
    AccountProfile,
    AuthenticationResult,
    PlatformComment,
    PlatformPost,
    PlatformPostMetrics,
)


class MockPlatformAdapter(PlatformAdapter):
    experimental = False

    def __init__(
        self,
        platform: str,
        *,
        display_name: str = "演示账号",
        username: str = "demo_user",
        scenario: MockScenario = MockScenario.NORMAL,
    ) -> None:
        self.platform = platform
        self._display_name = display_name
        self._username = username
        self._scenario = scenario
        self._user_id = f"mock-{platform}-001"

    async def check_authentication(self) -> AuthenticationResult:
        if self._scenario is MockScenario.AUTH_REQUIRED:
            from app.adapters.exceptions import AuthenticationRequiredError

            raise AuthenticationRequiredError("演示：需要重新登录")
        return AuthenticationResult(
            authenticated=True,
            message="演示数据：已连接（Mock）",
            display_name=self._display_name,
            username=self._username,
            platform_user_id=self._user_id,
        )

    async def fetch_account_profile(self) -> AccountProfile:
        if self._scenario is MockScenario.NETWORK:
            from app.adapters.exceptions import NetworkError

            raise NetworkError("演示：网络错误")
        return AccountProfile(
            platform_user_id=self._user_id,
            display_name=self._display_name,
            username=self._username,
            avatar_url=None,
            raw={"mock": True},
        )

    def _base_posts(self, limit: int) -> list[PlatformPost]:
        now = datetime.now(UTC)
        labels = {
            "x": "推文",
            "xiaohongshu": "笔记",
            "zhihu": "回答",
            "toutiao": "图文",
        }
        kind = labels.get(self.platform, "内容")
        posts: list[PlatformPost] = []
        for i in range(1, min(limit, 5) + 1):
            # Intentionally leave some metrics as None for certain platforms.
            view: int | None = 1000 * i if self.platform != "x" else None
            impression: int | None = 2000 * i if self.platform == "x" else (
                1500 * i if self.platform in {"xiaohongshu", "toutiao"} else None
            )
            favorite: int | None = 20 * i if self.platform in {"xiaohongshu", "zhihu"} else None
            share: int | None = 5 * i if self.platform in {"toutiao", "xiaohongshu"} else None
            repost: int | None = 3 * i if self.platform == "x" else None
            posts.append(
                PlatformPost(
                    platform_post_id=f"mock-{self.platform}-post-{i}",
                    title=f"【演示】{kind}示例 #{i}",
                    content_preview=f"这是 {self.platform} 的演示内容摘要 {i}。数据非真实。",
                    post_url=f"https://example.com/{self.platform}/post/{i}",
                    post_type=kind,
                    published_at=now - timedelta(days=i, hours=i),
                    view_count=view,
                    impression_count=impression,
                    like_count=50 * i,
                    favorite_count=favorite,
                    share_count=share,
                    repost_count=repost,
                    comment_count=4 + i,
                    raw_metrics={"mock": True},
                )
            )
        if self._scenario is MockScenario.EMPTY:
            return []
        if self._scenario is MockScenario.PARTIAL_METRICS:
            for p in posts:
                p.view_count = None
                p.impression_count = None
        return posts

    async def fetch_posts(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[PlatformPost]:
        if self._scenario is MockScenario.RATE_LIMIT:
            from app.adapters.exceptions import RateLimitError

            raise RateLimitError("演示：API 限流", reset_at=(datetime.now(UTC) + timedelta(minutes=15)).isoformat())
        if self._scenario is MockScenario.SELECTOR:
            from app.adapters.exceptions import SelectorChangedError

            raise SelectorChangedError("演示：页面选择器变化", diagnostic={"selector": ".mock-list"})
        posts = self._base_posts(limit)
        if since:
            posts = [p for p in posts if p.published_at and p.published_at >= since]
        return posts

    async def fetch_post_metrics(self, post_ids: list[str]) -> list[PlatformPostMetrics]:
        result: list[PlatformPostMetrics] = []
        for pid in post_ids:
            result.append(
                PlatformPostMetrics(
                    platform_post_id=pid,
                    view_count=1200 if self.platform != "x" else None,
                    impression_count=2400 if self.platform == "x" else 1800,
                    like_count=88,
                    favorite_count=12 if self.platform != "x" else None,
                    share_count=4 if self.platform != "x" else None,
                    repost_count=6 if self.platform == "x" else None,
                    comment_count=9,
                    raw_metrics={"mock": True},
                )
            )
        return result

    async def fetch_comments(
        self,
        post_id: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformComment]:
        if self._scenario is MockScenario.EMPTY:
            return []
        now = datetime.now(UTC)
        comments = [
            PlatformComment(
                platform_comment_id=f"{post_id}-c1",
                content=f"【演示评论】很有收获！（{self.platform}）",
                author_name="演示用户甲",
                author_platform_id=f"mock-user-a-{self.platform}",
                comment_url=f"https://example.com/{self.platform}/comment/1",
                published_at=now - timedelta(hours=2),
                like_count=3,
                platform_reply_count=0,
                replied_by_owner=False,
                raw={"mock": True},
            ),
            PlatformComment(
                platform_comment_id=f"{post_id}-c2",
                content="【演示评论】请问有后续吗？",
                author_name="演示用户乙",
                author_platform_id=f"mock-user-b-{self.platform}",
                comment_url=f"https://example.com/{self.platform}/comment/2",
                published_at=now - timedelta(hours=5),
                like_count=1,
                platform_reply_count=1,
                replied_by_owner=True,
                raw={"mock": True},
            ),
        ]
        # Dedup scenario: return same comment twice
        if self._scenario is MockScenario.DUPLICATE:
            comments = comments + [comments[0]]
        return comments[:limit]

    async def start_login(self) -> str:
        return "演示模式无需登录。关闭 Mock 后可连接真实账号。"

    async def close(self) -> None:
        return None


def build_mock_adapter(platform: str, **kwargs: Any) -> MockPlatformAdapter:
    defaults = {
        "x": ("X 演示账号", "demo_x"),
        "xiaohongshu": ("小红书演示账号", "demo_xhs"),
        "zhihu": ("知乎演示账号", "demo_zhihu"),
        "toutiao": ("头条演示账号", "demo_toutiao"),
    }
    name, user = defaults.get(platform, ("演示账号", "demo"))
    raw_scenario = kwargs.get("scenario", "normal")
    try:
        scenario = MockScenario(raw_scenario)
    except ValueError:
        scenario = MockScenario.NORMAL
    return MockPlatformAdapter(
        platform,
        display_name=kwargs.get("display_name", name),
        username=kwargs.get("username", user),
        scenario=scenario,
    )
