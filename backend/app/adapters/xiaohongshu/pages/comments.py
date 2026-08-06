"""XHS comments page."""

from __future__ import annotations

from typing import Any

from app.adapters.exceptions import UnsupportedFeatureError
from app.adapters.types import PlatformComment


class CommentsPage:
    def __init__(self, page: Any) -> None:
        self.page = page

    async def fetch_comments(self, post_id: str, limit: int = 100) -> list[PlatformComment]:
        # The current creator platform (creator.xiaohongshu.com) has no comment
        # management entry: /new/comment/note and related routes 404, note
        # cards expose no comment action, and the legacy galaxy comment APIs
        # reject unsigned requests. Report the limitation instead of silently
        # returning an empty list.
        raise UnsupportedFeatureError(
            "小红书创作平台当前无评论管理入口，评论读取暂不可用",
            diagnostic={
                "hint": "creator.xiaohongshu.com 新版 UI 未提供评论管理页面"
            },
        )
