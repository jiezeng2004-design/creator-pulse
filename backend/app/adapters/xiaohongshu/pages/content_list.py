"""XHS content list — experimental skeleton."""

from __future__ import annotations

from typing import Any

from app.adapters.types import PlatformPost
from app.adapters.xiaohongshu import selectors as S
from app.adapters.xiaohongshu.parser import parse_note


class ContentListPage:
    def __init__(self, page: Any) -> None:
        self.page = page
        self._captured: list[Any] = []

    async def _on_response(self, response: Any) -> None:
        try:
            if S.API_HINTS["notes"] not in response.url and S.API_HINTS["data"] not in response.url:
                return
            if response.status != 200:
                return
            if "json" not in response.headers.get("content-type", ""):
                return
            self._captured.append(await response.json())
        except Exception:  # noqa: BLE001
            pass

    async def fetch_posts(self, limit: int = 50) -> list[PlatformPost]:
        return await self.fetch_all_posts(limit)

    async def fetch_all_posts(self, limit: int = 50) -> list[PlatformPost]:
        """Fetch posts across pages by scrolling the creator list.

        The note manager loads one page at a time (``?tab=0&page=N``) when the
        ``.content`` container is scrolled to the bottom; the response carries
        no ``has_more`` flag, so keep scrolling until two consecutive scrolls
        add no new notes (or the limit is reached).
        """
        self._captured.clear()
        self.page.on("response", self._on_response)
        try:
            await self.page.goto(S.CONTENT_LIST, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(3000)
            seen: set[str] = set()
            empty_rounds = 0
            while empty_rounds < 2:
                posts = self._parse_captured()
                new_ids = [
                    p.platform_post_id for p in posts if p.platform_post_id not in seen
                ]
                if not new_ids:
                    empty_rounds += 1
                else:
                    empty_rounds = 0
                    seen.update(new_ids)
                if len(seen) >= limit:
                    break
                await self.page.evaluate(
                    """() => {
                        const c = document.querySelector('.content');
                        if (c) c.scrollTop = c.scrollHeight;
                        window.scrollTo(0, document.body.scrollHeight);
                    }"""
                )
                await self.page.wait_for_timeout(2000)
        finally:
            try:
                self.page.remove_listener("response", self._on_response)
            except Exception:  # noqa: BLE001
                pass

        return self._parse_captured()[:limit]

    def _parse_captured(self) -> list[PlatformPost]:
        posts: list[PlatformPost] = []
        for data in self._captured:
            if not isinstance(data, dict):
                continue
            d = data.get("data") or data
            notes = []
            if isinstance(d, dict):
                notes = d.get("notes") or d.get("list") or d.get("note_list") or []
            for n in notes if isinstance(notes, list) else []:
                if isinstance(n, dict):
                    p = parse_note(n)
                    if p:
                        posts.append(p)
        seen: set[str] = set()
        unique: list[PlatformPost] = []
        for p in posts:
            if p.platform_post_id in seen:
                continue
            seen.add(p.platform_post_id)
            unique.append(p)
        return unique
