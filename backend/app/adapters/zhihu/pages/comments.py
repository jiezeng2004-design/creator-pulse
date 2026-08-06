"""Page object: Zhihu comments for a content item."""

from __future__ import annotations

import logging
from typing import Any

from app.adapters.types import PlatformComment
from app.adapters.zhihu.parser import parse_comment_item

logger = logging.getLogger(__name__)


class CommentsPage:
    def __init__(self, page: Any) -> None:
        self.page = page
        self._captured: list[dict[str, Any]] = []

    async def _on_response(self, response: Any) -> None:
        try:
            url = response.url
            if "comment" not in url.lower() and "root_comment" not in url:
                return
            if response.status != 200:
                return
            ct = response.headers.get("content-type", "")
            if "json" not in ct:
                return
            data = await response.json()
            self._captured.append({"url": url, "data": data})
        except Exception:  # noqa: BLE001
            return

    async def fetch_for_post(
        self, post_url: str | None, post_id: str, limit: int = 100
    ) -> list[PlatformComment]:
        if not post_url:
            return []
        self._captured.clear()
        self.page.on("response", self._on_response)
        try:
            await self.page.goto(post_url, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(2000)
            # try open comment panel
            for sel in (
                "button:has-text('条评论')",
                "button:has-text('评论')",
                ".ContentItem-action:has-text('评论')",
            ):
                try:
                    btn = await self.page.query_selector(sel)
                    if btn:
                        await btn.click()
                        await self.page.wait_for_timeout(1200)
                        break
                except Exception:  # noqa: BLE001
                    continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("open post for comments failed: %s", exc)
        finally:
            try:
                self.page.remove_listener("response", self._on_response)
            except Exception:  # noqa: BLE001
                pass

        comments: list[PlatformComment] = []
        for pack in self._captured:
            data = pack["data"]
            items = []
            if isinstance(data, dict):
                items = data.get("data") or data.get("comments") or []
            elif isinstance(data, list):
                items = data
            for item in items:
                if not isinstance(item, dict):
                    continue
                # nested comment object
                node = item.get("comment") if isinstance(item.get("comment"), dict) else item
                c = parse_comment_item(node, post_id)
                if c:
                    comments.append(c)
                for child in item.get("child_comments") or []:
                    if isinstance(child, dict):
                        cc = parse_comment_item(child, post_id)
                        if cc:
                            comments.append(cc)

        # dedupe
        seen: set[str] = set()
        unique: list[PlatformComment] = []
        for c in comments:
            if c.platform_comment_id in seen:
                continue
            seen.add(c.platform_comment_id)
            unique.append(c)
        return unique[:limit]
