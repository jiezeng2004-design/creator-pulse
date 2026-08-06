"""Page object: Zhihu content list / creation manage."""

from __future__ import annotations

import logging
from typing import Any

from app.adapters.exceptions import SelectorChangedError
from app.adapters.types import PlatformPost
from app.adapters.zhihu import selectors as S
from app.adapters.zhihu.parser import parse_posts_from_list

logger = logging.getLogger(__name__)


class ContentListPage:
    def __init__(self, page: Any) -> None:
        self.page = page
        self._captured: list[dict[str, Any]] = []

    async def _on_response(self, response: Any) -> None:
        try:
            url = response.url
            if not any(h in url for h in S.API_HINTS.values()) and "creator" not in url:
                return
            if response.status != 200:
                return
            ct = response.headers.get("content-type", "")
            if "json" not in ct:
                return
            data = await response.json()
            if isinstance(data, (dict, list)):
                self._captured.append({"url": url, "data": data})
        except Exception:  # noqa: BLE001
            return

    async def fetch_posts(self, limit: int = 50) -> list[PlatformPost]:
        self._captured.clear()
        self.page.on("response", self._on_response)
        try:
            await self.page.goto(S.CONTENT_MANAGE, wait_until="networkidle")
            await self.page.wait_for_timeout(1500)
            # try analysis page as well
            await self.page.goto(S.CREATOR_ANALYSIS, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(1000)
        except Exception as exc:  # noqa: BLE001
            logger.warning("content list navigation issue: %s", exc)
        finally:
            try:
                self.page.remove_listener("response", self._on_response)
            except Exception:  # noqa: BLE001
                pass

        posts: list[PlatformPost] = []
        for pack in self._captured:
            posts.extend(parse_posts_from_list(pack["data"]))

        if posts:
            # dedupe by platform_post_id
            seen: set[str] = set()
            unique: list[PlatformPost] = []
            for p in posts:
                if p.platform_post_id in seen:
                    continue
                seen.add(p.platform_post_id)
                unique.append(p)
            return unique[:limit]

        # DOM fallback
        return await self._parse_dom(limit)

    async def _parse_dom(self, limit: int) -> list[PlatformPost]:
        try:
            await self.page.goto(S.CONTENT_MANAGE, wait_until="domcontentloaded")
            items = await self.page.query_selector_all(S.SELECTORS["content_list"])
        except Exception as exc:  # noqa: BLE001
            raise SelectorChangedError(
                "无法定位知乎内容列表，页面结构可能已变化",
                diagnostic={"selector": S.SELECTORS["content_list"], "error": str(exc)[:200]},
            ) from exc

        posts: list[PlatformPost] = []
        for idx, item in enumerate(items[:limit]):
            try:
                text = (await item.inner_text()).strip()
                link = await item.query_selector("a")
                href = await link.get_attribute("href") if link else None
                if href and href.startswith("/"):
                    href = "https://www.zhihu.com" + href
                title = text.split("\n")[0][:120] if text else f"知乎内容 #{idx + 1}"
                posts.append(
                    PlatformPost(
                        platform_post_id=f"zhihu-dom-{idx}-{abs(hash(title)) % 10**8}",
                        title=title,
                        content_preview=text[:280] if text else None,
                        post_url=href,
                        post_type="content",
                        published_at=None,
                        view_count=None,
                        impression_count=None,
                        like_count=None,
                        favorite_count=None,
                        share_count=None,
                        repost_count=None,
                        comment_count=None,
                        raw_metrics={"source": "dom_fallback", "partial": True},
                    )
                )
            except Exception:  # noqa: BLE001
                continue
        if not posts:
            raise SelectorChangedError(
                "知乎内容列表为空或选择器失效",
                diagnostic={"selector": S.SELECTORS["content_list"]},
            )
        return posts
