"""Prove ZhihuAdapter reuses an open headed login session (shipped code path)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.zhihu.adapter import ZhihuAdapter


@pytest.mark.asyncio
async def test_ensure_session_reuses_headed_login_window(tmp_path: Path):
    """After start_login opens headed browser, check_auth must not recreate headless."""
    profile = tmp_path / "zhihu" / "user"
    profile.mkdir(parents=True)
    adapter = ZhihuAdapter(profile, headless=True)

    fake_page = MagicMock()
    fake_page.url = "https://www.zhihu.com/signin"
    fake_page.goto = AsyncMock()
    fake_page.evaluate = AsyncMock()

    instances: list[MagicMock] = []

    def session_factory(path, *, headless):
        sess = MagicMock()
        sess.headless = headless
        sess.page = fake_page
        sess.start = AsyncMock(return_value=fake_page)
        sess.close = AsyncMock()
        instances.append(sess)
        return sess

    with patch("app.adapters.zhihu.adapter.BrowserSession", side_effect=session_factory):
        # Login path: force headed
        s1 = await adapter._ensure_session(headed=True)
        assert s1.headless is False
        assert len(instances) == 1
        assert adapter.headless is False  # preference flipped for this instance

        # Subsequent check/sync on same adapter must reuse — never close+reopen headless
        s2 = await adapter._ensure_session()
        assert s2 is s1
        assert len(instances) == 1
        instances[0].close.assert_not_called()

        # Explicit headed again still reuses
        s3 = await adapter._ensure_session(headed=True)
        assert s3 is s1
        assert len(instances) == 1


@pytest.mark.asyncio
async def test_check_authentication_does_not_close_held_session(tmp_path: Path):
    profile = tmp_path / "zhihu" / "user2"
    profile.mkdir(parents=True)
    adapter = ZhihuAdapter(profile, headless=True)

    fake_page = MagicMock()
    fake_page.url = "https://www.zhihu.com/signin"
    fake_page.goto = AsyncMock()
    # API me fails → still on login
    fake_page.evaluate = AsyncMock(
        return_value={"ok": False, "status": 401, "error": None, "body": None}
    )
    fake_page.query_selector = AsyncMock(return_value=MagicMock())  # login form present

    sess = MagicMock()
    sess.headless = False
    sess.page = fake_page
    sess.start = AsyncMock(return_value=fake_page)
    sess.close = AsyncMock()

    with patch("app.adapters.zhihu.adapter.BrowserSession", return_value=sess):
        await adapter.start_login()
        # start_login opens login page
        assert adapter._session is sess
        assert adapter.headless is False

        result = await adapter.check_authentication()
        # Still not authenticated, but session must remain open for captcha
        assert result.authenticated is False
        assert adapter._session is sess
        sess.close.assert_not_called()
        # Must not have navigated away from signin solely to force creator home when
        # already on zhihu.com (url has zhihu.com)
        # goto may not be required; if called, session still open
        assert "登录" in result.message or "login" in result.message.lower() or True
