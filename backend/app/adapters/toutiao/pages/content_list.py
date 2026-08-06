"""Toutiao content list page object (experimental)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.adapters.toutiao import selectors as S
from app.adapters.toutiao.parser import parse_article
from app.adapters.types import PlatformPost


class ContentListPage:
    def __init__(self, page: Any) -> None:
        self.page = page
        self._captured: list[Any] = []
        self._first_feed_url: str | None = None

    async def _on_request(self, request: Any) -> None:
        try:
            if S.API_HINTS["articles"] in request.url and self._first_feed_url is None:
                self._first_feed_url = request.url
        except Exception:  # noqa: BLE001
            return

    async def _on_response(self, response: Any) -> None:
        try:
            url = response.url
            if not any(h in url for h in S.API_HINTS.values()):
                return
            if response.status != 200:
                return
            if "json" not in response.headers.get("content-type", ""):
                return
            self._captured.append(await response.json())
        except Exception:  # noqa: BLE001
            return

    async def fetch_posts(self, limit: int = 50) -> list[PlatformPost]:
        self._captured.clear()
        self._first_feed_url = None
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)
        try:
            await self.page.goto(S.CONTENT_LIST, wait_until="networkidle")
            await self.page.wait_for_timeout(1500)
        finally:
            try:
                self.page.remove_listener("request", self._on_request)
            except Exception:  # noqa: BLE001
                pass
            try:
                self.page.remove_listener("response", self._on_response)
            except Exception:  # noqa: BLE001
                pass

        posts = await self._fetch_remaining_pages(limit)
        return posts[:limit]

    def _parse_payload(self, data: Any) -> list[PlatformPost]:
        posts: list[PlatformPost] = []
        if not isinstance(data, dict):
            return posts
        items = data.get("data")
        if not isinstance(items, list):
            items = data.get("list") or []
        for item in items:
            if isinstance(item, dict):
                p = parse_article(item)
                if p:
                    posts.append(p)
        return posts

    def _parse_captured(self) -> list[PlatformPost]:
        posts: list[PlatformPost] = []
        for data in self._captured:
            posts.extend(self._parse_payload(data))
        seen: set[str] = set()
        unique: list[PlatformPost] = []
        for p in posts:
            if p.platform_post_id in seen:
                continue
            seen.add(p.platform_post_id)
            unique.append(p)
        return unique

    async def _fetch_remaining_pages(self, limit: int) -> list[PlatformPost]:
        """Replay the first feed request with a higher offset until exhausted.

        The creator UI loads content through ``/api/feed/mp_provider/v1/`` with
        ``offset``/``count``/``page_index`` and signals more pages via
        ``has_more``. Replaying the exact captured URL inside the page context
        keeps the session cookies the API requires. ``page.request`` responses
        do not fire page-level ``response`` events, so the merged list is
        returned directly instead of relying on ``_captured``.
        """
        first = self._first_feed_url
        if not first:
            return self._parse_captured()
        try:
            parts = urlsplit(first)
            qs = dict(parse_qsl(parts.query))
            count = int(qs.get("count") or 10)
        except Exception:  # noqa: BLE001
            return self._parse_captured()

        posts = self._parse_captured()
        page_index = 1
        has_more = True
        while has_more and len(posts) < limit:
            page_index += 1
            offset = (page_index - 1) * count
            q = dict(qs)
            q["offset"] = str(offset)
            q["page_index"] = str(page_index)
            cep_raw = q.get("client_extra_params") or "{}"
            try:
                cep = json.loads(cep_raw)
                cep["page_index"] = str(page_index)
                q["client_extra_params"] = json.dumps(cep, ensure_ascii=False)
            except Exception:  # noqa: BLE001
                pass
            url = urlunsplit(parts._replace(query=urlencode(q)))
            try:
                resp = await self.page.request.get(url)
                if resp.status != 200:
                    break
                data = await resp.json()
            except Exception:  # noqa: BLE001
                break
            has_more = bool(data.get("has_more"))
            new_posts = self._parse_payload(data)
            posts.extend(new_posts)
            if not new_posts:
                break
        seen: set[str] = set()
        unique: list[PlatformPost] = []
        for p in posts:
            if p.platform_post_id in seen:
                continue
            seen.add(p.platform_post_id)
            unique.append(p)
        return unique
