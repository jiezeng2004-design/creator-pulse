"""Browser-based X (Twitter) adapter — free alternative to the paid API.

The official X API v2 consumes monthly read credits for every read call and
returns 402 once the budget is depleted. This adapter instead uses the same
Playwright + persistent Chrome profile approach as the domestic platforms:
the user logs into x.com once in a held browser window, and sync scrapes the
profile feed from the logged-in DOM. No API credits are consumed.

Selectors use X's stable ``data-testid`` attributes (same attributes used by
the web app and by widely deployed scrapers). If X changes its DOM, the
scraper fails with ``SelectorChangedError`` instead of fabricating data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.adapters.base import PlatformAdapter
from app.adapters.browser import BrowserSession
from app.adapters.exceptions import (
    AuthenticationRequiredError,
    NetworkError,
    SelectorChangedError,
    UnsupportedFeatureError,
)
from app.adapters.types import (
    AccountProfile,
    AuthenticationResult,
    PlatformComment,
    PlatformPost,
    PlatformPostMetrics,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

HOME_URL = "https://x.com/home"
LOGIN_URL = "https://x.com/i/flow/login"

# Stable data-testid attributes used by the X web app.
TWEET_ARTICLE = 'article[data-testid="tweet"]'
TWEET_TEXT = 'div[data-testid="tweetText"]'
USER_NAME = 'div[data-testid="User-Name"]'
ACCOUNT_SWITCHER = 'button[data-testid="SideNav_AccountSwitcher_Button"]'
COMPOSE_BOX = 'div[data-testid="tweetTextarea_0"]'
LOGIN_BUTTON = 'a[data-testid="loginButton"]'


def _parse_count(label: str | None) -> int | None:
    """Parse an X metric aria-label like '1,234 replies' / '12K views' / '1.2M'."""
    if not label:
        return None
    import re

    m = re.search(r"([\d.,]+)\s*([KMB]?)", label.replace(",", ""))
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    unit = m.group(2).upper()
    if unit == "K":
        value *= 1_000
    elif unit == "M":
        value *= 1_000_000
    elif unit == "B":
        value *= 1_000_000_000
    return int(value)


def _status_id_from_link(href: str | None) -> str | None:
    """Extract the tweet id from a /status/<id> link."""
    if not href:
        return None
    marker = "/status/"
    idx = href.find(marker)
    if idx < 0:
        return None
    rest = href[idx + len(marker):]
    return rest.split("/")[0].split("?")[0] or None


class XBrowserAdapter(PlatformAdapter):
    """Scrape a logged-in x.com profile feed via the browser profile."""

    platform = "x"
    experimental = True

    def __init__(self, profile_path: Path, *, headless: bool = True) -> None:
        self.profile_path = profile_path
        self.headless = headless
        self._session: BrowserSession | None = None
        self._profile_handle: str | None = None
        self._profile_name: str | None = None

    async def _ensure_session(self, *, headed: bool | None = None) -> BrowserSession:
        if headed is True:
            self.headless = False
        if self._session is not None:
            return self._session
        want_headless = False if headed is True else self.headless
        # X requires the network proxy configured for the X account; the same
        # X_PROXY setting used by the API adapter keeps this scoped to X only.
        proxy = get_settings().x_proxy.strip() or None
        self._session = BrowserSession(
            self.profile_path, headless=want_headless, proxy_server=proxy
        )
        try:
            await self._session.start()
        except Exception as exc:  # noqa: BLE001
            self._session = None
            raise NetworkError(
                f"无法启动浏览器: {exc.__class__.__name__}",
                diagnostic={"error": str(exc)[:200]},
            ) from exc
        return self._session

    async def start_login(self) -> str:
        session = await self._ensure_session(headed=True)
        page = session.page
        try:
            await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45_000)
        except Exception as exc:  # noqa: BLE001
            raise NetworkError(
                f"打开 X 登录页失败: {exc.__class__.__name__}",
                diagnostic={"error": str(exc)[:200]},
            ) from exc
        return (
            "已打开 X 登录窗口，请在浏览器中手动完成登录（含验证码/双重验证）。"
            "登录成功后回到 CreatorPulse 点击「检查并同步」。请勿关闭浏览器窗口。"
        )

    async def _is_logged_in(self) -> bool:
        session = await self._ensure_session()
        page = session.page
        try:
            await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=45_000)
            try:
                await page.wait_for_selector(
                    f"{ACCOUNT_SWITCHER}, {COMPOSE_BOX}, {LOGIN_BUTTON}",
                    timeout=15_000,
                )
            except Exception:  # noqa: BLE001
                return False
            return await page.locator(f"{ACCOUNT_SWITCHER}, {COMPOSE_BOX}").count() > 0
        except Exception as exc:  # noqa: BLE001
            logger.info("X login detection failed: %s", exc)
            return False

    async def check_authentication(self) -> AuthenticationResult:
        try:
            if not await self._is_logged_in():
                return AuthenticationResult(
                    authenticated=False,
                    message="未检测到 X 登录态，请先点击「打开登录」在浏览器中完成登录",
                )
            profile = await self.fetch_account_profile()
            return AuthenticationResult(
                authenticated=True,
                message="X 浏览器登录态有效",
                display_name=profile.display_name,
                username=profile.username,
                platform_user_id=profile.platform_user_id,
                avatar_url=profile.avatar_url,
            )
        except AuthenticationRequiredError as exc:
            return AuthenticationResult(authenticated=False, message=exc.message)
        except Exception as exc:  # noqa: BLE001
            return AuthenticationResult(
                authenticated=False,
                message=f"X 登录检测失败: {exc.__class__.__name__}",
            )

    async def fetch_account_profile(self) -> AccountProfile:
        session = await self._ensure_session()
        page = session.page
        if self._profile_handle:
            username = self._profile_handle
            display = self._profile_name or username
            return AccountProfile(
                platform_user_id=f"x-browser-{username}",
                display_name=display,
                username=username,
            )
        try:
            switcher = page.locator(ACCOUNT_SWITCHER).first
            await switcher.wait_for(timeout=15_000)
            label = (await switcher.get_attribute("aria-label")) or ""
            # aria-label is usually "<display name>, @<handle>" or includes @handle.
            handle = None
            import re

            m = re.search(r"@([A-Za-z0-9_]+)", label)
            if m:
                handle = m.group(1)
            display = label.split(",")[0].strip() or None
            if not handle:
                # fallback: read the account switcher button text
                text = (await switcher.inner_text()) or ""
                m = re.search(r"@([A-Za-z0-9_]+)", text)
                if m:
                    handle = m.group(1)
                if not display:
                    display = text.strip().splitlines()[0] if text.strip() else None
            if not handle:
                raise AuthenticationRequiredError("无法从 X 页面读取账号 handle")
            self._profile_handle = handle
            self._profile_name = display or handle
            return AccountProfile(
                platform_user_id=f"x-browser-{handle}",
                display_name=display or handle,
                username=handle,
            )
        except AuthenticationRequiredError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SelectorChangedError(
                f"读取 X 账号信息失败: {exc.__class__.__name__}",
                diagnostic={"error": str(exc)[:200]},
            ) from exc

    async def _load_profile_feed(
        self,
        username: str,
        *,
        max_scrolls: int = 12,
    ) -> list[dict[str, Any]]:
        """Scroll the profile timeline and collect raw tweet card data."""
        session = await self._ensure_session()
        page = session.page
        url = f"https://x.com/{username}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except Exception as exc:  # noqa: BLE001
            raise NetworkError(
                f"打开 X 主页失败: {exc.__class__.__name__}",
                diagnostic={"url": url, "error": str(exc)[:200]},
            ) from exc
        try:
            await page.wait_for_selector(TWEET_ARTICLE, timeout=20_000)
        except Exception as exc:  # noqa: BLE001
            raise SelectorChangedError(
                "X 主页未找到推文（可能登录态失效或页面结构变化）",
                diagnostic={"url": url, "error": str(exc)[:200]},
            ) from exc

        seen: set[str] = set()
        for _ in range(max_scrolls):
            cards = await page.locator(TWEET_ARTICLE).evaluate_all(
                r"""(els) => els.map((el) => {
                    const link = el.querySelector('a[href*="/status/"]');
                    const statusId = link ? link.getAttribute('href') : null;
                    const textEl = el.querySelector('[data-testid="tweetText"]');
                    const timeEl = el.querySelector('time[datetime]');
                    const nameEl = el.querySelector('[data-testid="User-Name"]');
                    const metrics = {};
                    el.querySelectorAll('[aria-label]').forEach((n) => {
                      const label = n.getAttribute('aria-label') || '';
                      const m = label.match(/^([\d.,]+[KMB]?)\s+(replies?|likes?|reposts?|views?|bookmarks?)$/i);
                      if (m) metrics[m[2].toLowerCase().replace(/s$/, '')] = label;
                    });
                    return {
                      id: statusId,
                      text: textEl ? textEl.innerText : '',
                      time: timeEl ? timeEl.getAttribute('datetime') : null,
                      author: nameEl ? nameEl.innerText : '',
                      metrics,
                    };
                })"""
            )
            for c in cards:
                if not c.get("id"):
                    continue
                status_id = _status_id_from_link(c["id"])
                if status_id:
                    c["status_id"] = status_id
                    seen.add(status_id)
            await page.mouse.wheel(0, 3_000)
            await page.wait_for_timeout(1_200)
            count = await page.locator(TWEET_ARTICLE).count()
            if count <= len(seen) and len(seen) >= 5:
                break

        # Re-read once more for the final set.
        cards = await page.locator(TWEET_ARTICLE).evaluate_all(
            r"""(els) => els.map((el) => {
                const link = el.querySelector('a[href*="/status/"]');
                const textEl = el.querySelector('[data-testid="tweetText"]');
                const timeEl = el.querySelector('time[datetime]');
                const metrics = {};
                el.querySelectorAll('[aria-label]').forEach((n) => {
                  const label = n.getAttribute('aria-label') || '';
                  const m = label.match(/^([\d.,]+[KMB]?)\s+(replies?|likes?|reposts?|views?|bookmarks?)$/i);
                  if (m) metrics[m[2].toLowerCase().replace(/s$/, '')] = label;
                });
                return {
                  id: link ? link.getAttribute('href') : null,
                  text: textEl ? textEl.innerText : '',
                  time: timeEl ? timeEl.getAttribute('datetime') : null,
                  metrics,
                };
            })"""
        )
        out: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for c in cards:
            sid = _status_id_from_link(c.get("id"))
            if not sid or sid in seen_ids:
                continue
            seen_ids.add(sid)
            c["status_id"] = sid
            out.append(c)
        return out

    async def fetch_posts(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[PlatformPost]:
        username = self._profile_handle
        if not username:
            profile = await self.fetch_account_profile()
            username = profile.username or ""
        if not username:
            raise AuthenticationRequiredError("无法确定 X 用户名")

        raw = await self._load_profile_feed(username, max_scrolls=12)
        posts: list[PlatformPost] = []
        for item in raw:
            published_at = None
            if item.get("time"):
                try:
                    dt = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
                    published_at = dt
                except ValueError:
                    published_at = None
            if since and published_at and published_at < since:
                continue
            text = (item.get("text") or "").strip()
            metrics = item.get("metrics") or {}
            posts.append(
                PlatformPost(
                    platform_post_id=item["status_id"],
                    title=text[:80] or None,
                    content_preview=text[:500] or None,
                    post_url=f"https://x.com/{username}/status/{item['status_id']}",
                    post_type="tweet",
                    published_at=published_at,
                    like_count=_parse_count(metrics.get("like")),
                    repost_count=_parse_count(metrics.get("repost")),
                    comment_count=_parse_count(metrics.get("reply")),
                    view_count=_parse_count(metrics.get("view")),
                    impression_count=_parse_count(metrics.get("view")),
                    raw_metrics={k: v for k, v in metrics.items()},
                )
            )
            if len(posts) >= limit:
                break
        return posts

    async def fetch_post_metrics(self, post_ids: list[str]) -> list[PlatformPostMetrics]:
        # Metrics are captured during fetch_posts; re-scraping per id is not
        # supported in browser mode. Return empty so the sync pipeline keeps
        # the values already stored.
        return []

    async def fetch_comments(
        self,
        post_id: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformComment]:
        username = self._profile_handle or ""
        raise UnsupportedFeatureError(
            "X 浏览器模式暂不支持评论抓取（评论页动态加载复杂，后续版本可加）。"
            "内容与互动指标已可同步。",
            diagnostic={"post_id": post_id, "username": username},
        )

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


__all__ = ["XBrowserAdapter"]
