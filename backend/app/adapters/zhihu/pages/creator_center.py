"""Page object: Zhihu creator center entry & auth detection."""

from __future__ import annotations

import logging
from typing import Any

from app.adapters.exceptions import SelectorChangedError
from app.adapters.zhihu import selectors as S

logger = logging.getLogger(__name__)


class CreatorCenterPage:
    def __init__(self, page: Any) -> None:
        self.page = page

    async def open(self) -> None:
        await self.page.goto(S.CREATOR_HOME, wait_until="domcontentloaded")

    async def open_login(self) -> None:
        await self.page.goto(S.LOGIN_URL, wait_until="domcontentloaded")

    async def is_login_page(self) -> bool:
        url = self.page.url or ""
        if "signin" in url or "login" in url:
            return True
        try:
            el = await self.page.query_selector(S.SELECTORS["login_form"])
            return el is not None
        except Exception:  # noqa: BLE001
            return False

    async def is_authenticated(self) -> bool:
        if await self.is_login_page():
            return False
        # Check cookies for z_c0 roughly
        cookies = await self.page.context.cookies()
        names = {c.get("name") for c in cookies}
        if "z_c0" in names or "SESSIONID" in names:
            # still verify we can open creator home without redirect
            await self.open()
            if await self.is_login_page():
                return False
            return True
        # Try me API via page
        try:
            ok = await self.page.evaluate(
                """async () => {
                  try {
                    const r = await fetch('https://www.zhihu.com/api/v4/me', {credentials:'include'});
                    return r.ok;
                  } catch (e) { return false; }
                }"""
            )
            if ok:
                return True
        except Exception:  # noqa: BLE001
            pass
        # fallback DOM
        avatar = await self.page.query_selector(S.SELECTORS["user_avatar"])
        return avatar is not None

    async def get_display_name(self) -> str | None:
        try:
            # try common profile entry
            el = await self.page.query_selector(".AppHeader-profileEntry, .UserLink-link")
            if el:
                text = (await el.inner_text()).strip()
                return text or None
        except Exception as exc:  # noqa: BLE001
            logger.debug("display name not found: %s", exc)
        return None

    async def ensure_creator_accessible(self) -> None:
        await self.open()
        if await self.is_login_page():
            return
        # creator page may change — do not hard fail on missing nav
        try:
            await self.page.wait_for_timeout(800)
        except Exception as exc:  # noqa: BLE001
            raise SelectorChangedError(
                "知乎创作中心页面加载异常",
                diagnostic={"url": self.page.url, "error": str(exc)[:200]},
            ) from exc
