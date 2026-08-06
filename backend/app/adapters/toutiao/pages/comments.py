"""Toutiao comments page object (experimental)."""

from __future__ import annotations

from typing import Any

from app.adapters.exceptions import UnsupportedFeatureError
from app.adapters.toutiao import selectors as S
from app.adapters.toutiao.parser import parse_comment
from app.adapters.types import PlatformComment


class CommentsPage:
    def __init__(self, page: Any) -> None:
        self.page = page
        self._captured: list[Any] = []

    async def fetch_comments(self, post_id: str, limit: int = 100) -> list[PlatformComment]:
        comments: list[PlatformComment] = []
        offset = 0
        while offset < limit:
            try:
                resp = await self.page.request.get(
                    S.COMMENT_LIST_API,
                    params={
                        "offset": str(offset),
                        "count": "20",
                        "item_id": post_id,
                        "group_id": post_id,
                        "sort": "time",
                        "app_id": S.COMMENT_APP_ID,
                    },
                )
                data = await resp.json()
            except Exception as exc:  # noqa: BLE001
                raise UnsupportedFeatureError(
                    "头条评论读取实验性功能暂不可用",
                    diagnostic={"error": str(exc)[:200]},
                ) from exc
            if resp.status != 200 or not isinstance(data, dict):
                break
            d = data.get("data")
            if not isinstance(d, dict):
                break
            items = d.get("data") or []
            for item in items:
                if isinstance(item, dict):
                    c = parse_comment(item, post_id)
                    if c:
                        comments.append(c)
            if not d.get("has_more"):
                break
            offset += 20
        return comments[:limit]
