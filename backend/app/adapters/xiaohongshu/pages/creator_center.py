"""XHS creator center page object."""

from __future__ import annotations

import logging
from typing import Any

from app.adapters.xiaohongshu import selectors as S

logger = logging.getLogger(__name__)


class CreatorCenterPage:
    def __init__(self, page: Any) -> None:
        self.page = page

    async def open_login(self) -> None:
        await self.page.goto(S.LOGIN_URL, wait_until="domcontentloaded")

    async def open_home(self) -> None:
        await self.page.goto(S.CREATOR_HOME, wait_until="domcontentloaded")

    async def is_authenticated(self) -> bool:
        await self.open_home()
        url = self.page.url or ""
        if "login" in url:
            return False
        el = await self.page.query_selector(S.SELECTORS["user"])
        return el is not None or "login" not in url

    async def is_login_page(self) -> bool:
        url = self.page.url or ""
        return "login" in url or "qrcode" in url

    async def get_display_name(self) -> str | None:
        try:
            el = await self.page.query_selector(S.SELECTORS["user"])
            if el:
                text = await el.inner_text()
                if text and text.strip():
                    return text.strip()[:100]
        except Exception:  # noqa: BLE001
            pass
        return None
