"""Zhihu adapter: Playwright profile + creator JSON APIs (read-only)."""

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
)
from app.adapters.types import (
    AccountProfile,
    AuthenticationResult,
    PlatformComment,
    PlatformPost,
    PlatformPostMetrics,
)
from app.adapters.zhihu import selectors as S
from app.adapters.zhihu.pages.creator_center import CreatorCenterPage
from app.adapters.zhihu.parser import parse_comment_item, parse_posts_from_list

logger = logging.getLogger(__name__)


class ZhihuAdapter(PlatformAdapter):
    platform = "zhihu"
    experimental = False

    def __init__(self, profile_path: Path, *, headless: bool = True) -> None:
        # headless default True for *fresh* sync sessions only.
        # Once a headed login window is open, keep reusing that session.
        self.profile_path = profile_path
        self.headless = headless
        self._session: BrowserSession | None = None
        self._posts_cache: dict[str, PlatformPost] = {}
        self._url_token: str | None = None

    async def _ensure_session(self, *, headed: bool | None = None) -> BrowserSession:
        # Prefer headed when login UI is requested; remember for this adapter instance.
        if headed is True:
            self.headless = False

        # CRITICAL: never tear down an already-open browser (held login windows).
        if self._session is not None:
            return self._session

        want_headless = False if headed is True else self.headless
        self._session = BrowserSession(self.profile_path, headless=want_headless)
        try:
            await self._session.start()
        except Exception as exc:  # noqa: BLE001
            self._session = None
            raise NetworkError(
                f"无法启动浏览器: {exc.__class__.__name__}",
                diagnostic={"error": str(exc)[:200]},
            ) from exc
        return self._session

    async def _fetch_json(self, url: str) -> Any:
        session = await self._ensure_session()
        page = session.page
        result = await page.evaluate(
            """async (url) => {
                try {
                  const r = await fetch(url, {
                    credentials: 'include',
                    headers: {
                      'accept': 'application/json, text/plain, */*',
                      'x-requested-with': 'fetch'
                    }
                  });
                  const text = await r.text();
                  let body = null;
                  try { body = JSON.parse(text); } catch (e) {
                    return { ok: false, status: r.status, error: 'non_json', snippet: text.slice(0, 200) };
                  }
                  return { ok: r.ok, status: r.status, body };
                } catch (e) {
                  return { ok: false, status: 0, error: String(e) };
                }
            }""",
            url,
        )
        if not result or result.get("error") == "non_json":
            raise SelectorChangedError(
                "知乎接口返回非 JSON，页面或接口可能已变化",
                diagnostic={"url": url[:120], "status": result.get("status") if result else None},
            )
        if result.get("status") in (401, 403):
            raise AuthenticationRequiredError("知乎登录态失效或权限不足，请重新登录")
        if not result.get("ok"):
            raise NetworkError(
                f"知乎接口请求失败 HTTP {result.get('status')}",
                diagnostic={"url": url[:120], "status": result.get("status")},
            )
        return result.get("body")

    async def start_login(self) -> str:
        session = await self._ensure_session(headed=True)
        page = CreatorCenterPage(session.page)
        await page.open_login()
        return (
            "已打开知乎登录窗口，请在浏览器中手动完成登录（含验证码）。"
            "登录成功后回到 CreatorPulse 点击「检查登录状态」。请勿关闭浏览器窗口直至检查完成。"
        )

    async def check_authentication(self) -> AuthenticationResult:
        # Reuse held headed session if present — do not reopen headless mid-login.
        session = await self._ensure_session()
        page = session.page
        center = CreatorCenterPage(page)

        # Prefer cookie API without navigating away from captcha/login UI when possible.
        try:
            current = page.url or ""
            if "zhihu.com" not in current:
                await page.goto(S.CREATOR_HOME, wait_until="domcontentloaded")
            me = await self._fetch_json(S.API_ME)
            if isinstance(me, dict) and me.get("id"):
                self._url_token = me.get("url_token")
                return AuthenticationResult(
                    authenticated=True,
                    message="知乎登录态有效",
                    display_name=me.get("name") or "知乎账号",
                    username=me.get("url_token"),
                    platform_user_id=str(me.get("id")),
                    avatar_url=me.get("avatar_url"),
                )
        except AuthenticationRequiredError:
            # Still on login flow — keep window open for the user.
            if await center.is_login_page():
                return AuthenticationResult(
                    authenticated=False,
                    message="仍在登录页，请完成登录（含验证码）后再检查",
                )
            return AuthenticationResult(authenticated=False, message="需要重新登录知乎")
        except Exception as exc:  # noqa: BLE001
            logger.info("API auth check failed, fallback DOM: %s", exc)

        try:
            if await center.is_login_page():
                return AuthenticationResult(
                    authenticated=False,
                    message="仍在登录页，请完成登录后再检查（登录窗口已保持打开）",
                )
            ok = await center.is_authenticated()
        except Exception as exc:  # noqa: BLE001
            return AuthenticationResult(
                authenticated=False,
                message=f"登录检测失败: {exc.__class__.__name__}",
            )
        if not ok:
            return AuthenticationResult(
                authenticated=False,
                message="未检测到知乎登录态，请先点击「打开登录窗口」",
            )
        name = await center.get_display_name()
        return AuthenticationResult(
            authenticated=True,
            message="知乎登录态有效",
            display_name=name or "知乎账号",
            platform_user_id=f"zhihu-profile-{abs(hash(str(self.profile_path))) % 10**10}",
        )

    async def fetch_account_profile(self) -> AccountProfile:
        auth = await self.check_authentication()
        if not auth.authenticated:
            raise AuthenticationRequiredError(auth.message or "需要登录知乎")
        return AccountProfile(
            platform_user_id=auth.platform_user_id or "zhihu-unknown",
            display_name=auth.display_name or "知乎账号",
            username=auth.username,
            avatar_url=auth.avatar_url,
        )

    async def fetch_posts(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[PlatformPost]:
        await self.fetch_account_profile()
        session = await self._ensure_session()
        # Ensure cookies on zhihu origin
        try:
            await session.page.goto(S.CONTENT_MANAGE, wait_until="domcontentloaded")
        except Exception:  # noqa: BLE001
            await session.page.goto(S.CREATOR_HOME, wait_until="domcontentloaded")

        posts: list[PlatformPost] = []
        offset = 0
        page_size = min(limit, 20)
        while len(posts) < limit:
            url = S.API_CREATIONS.format(limit=page_size, offset=offset)
            try:
                body = await self._fetch_json(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("creations API failed: %s", exc)
                break
            batch = parse_posts_from_list(body)
            if not batch:
                break
            posts.extend(batch)
            paging = body.get("paging") if isinstance(body, dict) else None
            is_end = isinstance(paging, dict) and paging.get("is_end")
            offset += len(batch)
            if is_end or len(batch) < page_size:
                break

        # Fallback to public member content lists if creator API empty
        if not posts and self._url_token:
            for builder in (
                lambda: S.API_MEMBER_ANSWERS.format(
                    token=self._url_token, offset=0, limit=min(limit, 20)
                ),
                lambda: S.API_MEMBER_ARTICLES.format(
                    token=self._url_token, offset=0, limit=min(limit, 20)
                ),
            ):
                try:
                    body = await self._fetch_json(builder())
                    posts.extend(parse_posts_from_list(body))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("member list fallback failed: %s", exc)

        if not posts:
            raise SelectorChangedError(
                "未能从知乎创作中心获取内容列表（接口为空或结构变化）",
                diagnostic={"url_token": self._url_token},
            )

        # dedupe
        seen: set[str] = set()
        unique: list[PlatformPost] = []
        for p in posts:
            if p.platform_post_id in seen:
                continue
            seen.add(p.platform_post_id)
            unique.append(p)
        posts = unique[:limit]

        if since:
            posts = [p for p in posts if p.published_at is None or p.published_at >= since]

        self._posts_cache = {p.platform_post_id: p for p in posts}
        return posts

    async def fetch_post_metrics(self, post_ids: list[str]) -> list[PlatformPostMetrics]:
        result: list[PlatformPostMetrics] = []
        for pid in post_ids:
            p = self._posts_cache.get(pid)
            if not p:
                result.append(PlatformPostMetrics(platform_post_id=pid))
                continue
            result.append(
                PlatformPostMetrics(
                    platform_post_id=pid,
                    view_count=p.view_count,
                    impression_count=p.impression_count,
                    like_count=p.like_count,
                    favorite_count=p.favorite_count,
                    share_count=p.share_count,
                    repost_count=p.repost_count,
                    comment_count=p.comment_count,
                    raw_metrics=p.raw_metrics,
                )
            )
        return result

    def _raw_id_and_type(self, platform_post_id: str) -> tuple[str, str]:
        if ":" in platform_post_id:
            t, rid = platform_post_id.split(":", 1)
            return rid, t
        return platform_post_id, "answer"

    async def fetch_comments(
        self,
        post_id: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformComment]:
        raw_id, ptype = self._raw_id_and_type(post_id)
        template = (
            S.API_ARTICLE_COMMENTS_V5
            if ptype == "article"
            else S.API_ANSWER_COMMENTS_V5
        )

        # comment_v5 root_comment paginates via offset; page through until the
        # platform reports is_end or we reach the requested limit.
        page_size = min(limit, 20)
        comments: list[PlatformComment] = []
        offset = 0
        while len(comments) < limit:
            url = template.format(id=raw_id, limit=page_size, offset=offset)
            try:
                body = await self._fetch_json(url)
            except Exception as exc:  # noqa: BLE001
                logger.info("comments fetch skipped for %s: %s", post_id, exc)
                break

            items: list[Any] = []
            if isinstance(body, dict):
                items = body.get("data") or body.get("comments") or []
            elif isinstance(body, list):
                items = body

            for item in items:
                if not isinstance(item, dict):
                    continue
                node = item.get("comment") if isinstance(item.get("comment"), dict) else item
                c = parse_comment_item(node, post_id)
                if c:
                    comments.append(c)
                for child in item.get("child_comments") or []:
                    if isinstance(child, dict):
                        cc = parse_comment_item(child, post_id)
                        if cc:
                            comments.append(cc)

            paging = body.get("paging") if isinstance(body, dict) else None
            is_end = isinstance(paging, dict) and paging.get("is_end")
            if is_end or len(items) < page_size:
                break
            offset += len(items)

        # The same comment id can appear across pages or as its own reply;
        # keep one canonical row per platform comment.
        seen: set[str] = set()
        unique: list[PlatformComment] = []
        for c in comments:
            if c.platform_comment_id in seen:
                continue
            seen.add(c.platform_comment_id)
            unique.append(c)
        comments = unique

        if since:
            comments = [
                c for c in comments if c.published_at is None or c.published_at >= since
            ]
        return comments[:limit]

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
