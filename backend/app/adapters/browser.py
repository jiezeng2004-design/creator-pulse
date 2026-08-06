"""Shared Playwright helpers for domestic platforms."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.security import PathSecurityError, is_under_project

logger = logging.getLogger(__name__)

# Lazy import playwright so unit tests without browser still import app.


class BrowserSession:
    """Persistent Chromium context for a single account profile."""

    def __init__(
        self,
        profile_path: Path,
        *,
        headless: bool = False,
        proxy_server: str | None = None,
    ) -> None:
        if not is_under_project(profile_path):
            raise PathSecurityError(f"Browser profile outside project: {profile_path}")
        self.profile_path = profile_path
        self.headless = headless
        self.proxy_server = proxy_server
        self._playwright: Any = None
        self._context: Any = None
        self._page: Any = None

    async def start(self) -> Any:
        from playwright.async_api import async_playwright

        self.profile_path.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        launch_kwargs: dict[str, Any] = dict(
            user_data_dir=str(self.profile_path),
            headless=self.headless,
            channel="chrome",  # use system-installed Google Chrome
            accept_downloads=False,  # security: disable downloads
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            args=["--disable-dev-shm-usage"],
        )
        if self.proxy_server:
            launch_kwargs["proxy"] = {"server": self.proxy_server}
        self._context = await self._playwright.chromium.launch_persistent_context(
            **launch_kwargs
        )
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()
        self._page.set_default_timeout(30_000)
        self._page.set_default_navigation_timeout(45_000)
        return self._page

    @property
    def page(self) -> Any:
        if self._page is None:
            raise RuntimeError("Browser session not started")
        return self._page

    @property
    def context(self) -> Any:
        if self._context is None:
            raise RuntimeError("Browser session not started")
        return self._context

    async def close(self) -> None:
        try:
            if self._context is not None:
                await self._context.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error closing browser context: %s", exc)
        try:
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error stopping playwright: %s", exc)
        self._context = None
        self._page = None
        self._playwright = None
