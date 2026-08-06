"""Toutiao creator center page object."""

from __future__ import annotations

from typing import Any

from app.adapters.toutiao import selectors as S


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
        cookies = await self.page.context.cookies()
        names = {c.get("name") for c in cookies}
        if any(n and ("session" in n.lower() or "uid" in n.lower() or n in {"sso_uid", "sid_tt"}) for n in names):
            return "login" not in url
        el = await self.page.query_selector(S.SELECTORS["user_info"])
        return el is not None
