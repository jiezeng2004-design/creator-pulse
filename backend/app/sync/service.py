"""Unified sync orchestration with per-account isolation."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.exceptions import (
    AdapterError,
    AuthenticationRequiredError,
    PermissionDeniedError,
    RateLimitError,
    SelectorChangedError,
    UnsupportedFeatureError,
)
from app.adapters.registry import create_adapter
from app.core.logging import sanitize_diagnostic
from app.models.account import PlatformAccount
from app.models.enums import AccountStatus, SyncStatus, SyncType
from app.models.sync_run import SyncRun
from app.services import comment_service, post_service, settings_service
from app.services.account_service import get_account
from app.sync.events import SyncEvent, publish

logger = logging.getLogger(__name__)

_account_locks: dict[int, asyncio.Lock] = {}
_cancel_flags: dict[int, bool] = {}


def _lock_for(account_id: int) -> asyncio.Lock:
    if account_id not in _account_locks:
        _account_locks[account_id] = asyncio.Lock()
    return _account_locks[account_id]


def is_sync_running(account_id: int) -> bool:
    """True when a sync for this account currently holds the account lock."""
    lock = _account_locks.get(account_id)
    return lock is not None and lock.locked()


def request_cancel(account_id: int) -> bool:
    """Ask a running sync to stop at its next checkpoint.

    Returns True only when a sync was actually in flight. Setting the flag for an
    idle account would leak into that account's *next* sync, so it is a no-op.
    """
    if not is_sync_running(account_id):
        return False
    _cancel_flags[account_id] = True
    return True


def _cancelled(account_id: int) -> bool:
    return _cancel_flags.get(account_id, False)


def cleanup_sync_state(account_id: int) -> None:
    """Drop all in-memory sync state for an account (use when it is deleted).

    Only safe once no sync is in flight: removing a *held* lock would let a
    concurrent caller create a fresh, unlocked one and start a second sync.
    """
    lock = _account_locks.get(account_id)
    if lock is None or not lock.locked():
        _account_locks.pop(account_id, None)
    _cancel_flags.pop(account_id, None)


class SyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync_account(
        self,
        account_id: int,
        *,
        sync_type: SyncType = SyncType.MANUAL,
    ) -> SyncRun:
        lock = _lock_for(account_id)
        if lock.locked():
            run = SyncRun(
                account_id=account_id,
                platform="unknown",
                sync_type=sync_type.value,
                status=SyncStatus.FAILED.value,
                error_code="already_running",
                error_message="该账号同步正在进行中",
                finished_at=datetime.now(UTC),
            )
            self.db.add(run)
            await self.db.flush()
            return run

        async with lock:
            _cancel_flags[account_id] = False
            return await self._run(account_id, sync_type)

    async def run_queued_account(
        self,
        account_id: int,
        run_id: int,
        *,
        sync_type: SyncType = SyncType.MANUAL,
    ) -> SyncRun:
        """Execute a durable run that was created by the background queue."""
        lock = _lock_for(account_id)
        if lock.locked():
            run = await self.db.get(SyncRun, run_id)
            if run is None:
                raise RuntimeError(f"Queued sync run {run_id} does not exist")
            run.status = SyncStatus.FAILED.value
            run.error_code = "already_running"
            run.error_message = "该账号同步正在进行中"
            run.finished_at = datetime.now(UTC)
            await self.db.flush()
            return run

        async with lock:
            _cancel_flags[account_id] = False
            run = await self.db.get(SyncRun, run_id)
            if run is None:
                raise RuntimeError(f"Queued sync run {run_id} does not exist")
            if run.account_id != account_id:
                raise RuntimeError(
                    f"Queued sync run {run_id} belongs to account {run.account_id}"
                )
            if run.status != SyncStatus.QUEUED.value:
                return run
            run.sync_type = sync_type.value
            run.status = SyncStatus.RUNNING.value
            run.started_at = datetime.now(UTC)
            await self.db.flush()
            return await self._run(account_id, sync_type, run=run)

    async def _run(
        self,
        account_id: int,
        sync_type: SyncType,
        *,
        run: SyncRun | None = None,
    ) -> SyncRun:
        account = await get_account(self.db, account_id)
        settings = await settings_service.get_or_create_settings(self.db)
        if run is None:
            run = SyncRun(
                account_id=account.id,
                platform=account.platform,
                sync_type=sync_type.value,
                status=SyncStatus.RUNNING.value,
                started_at=datetime.now(UTC),
            )
            self.db.add(run)
        account.account_status = AccountStatus.SYNCING.value
        account.last_sync_attempt_at = datetime.now(UTC)
        account.last_sync_error = None
        run.phase = "checking_auth"
        await self.db.flush()

        await publish(
            SyncEvent(
                type="sync_update",
                run_id=run.id,
                account_id=account.id,
                platform=account.platform,
                status=run.status,
                phase=run.phase or "checking_auth",
                message="正在检查登录状态…",
            )
        )

        adapter = create_adapter(
            account.platform,
            use_mock=account.is_mock or settings.enable_mock_data,
            browser_profile_path=account.browser_profile_path,
            account_key=account.username or str(account.id),
            username=account.username,
        )
        posts_fetched = 0
        comments_fetched = 0
        try:
            auth = await adapter.check_authentication()
            if not auth.authenticated:
                raise AuthenticationRequiredError(auth.message or "需要登录")

            run.phase = "fetching_profile"
            await self._progress(account, run)
            profile = await adapter.fetch_account_profile()
            account.display_name = profile.display_name or account.display_name
            account.username = profile.username or account.username
            account.platform_user_id = profile.platform_user_id or account.platform_user_id
            account.avatar_url = profile.avatar_url or account.avatar_url
            account.account_status = AccountStatus.CONNECTED.value

            if _cancelled(account_id):
                raise asyncio.CancelledError()

            posts = await adapter.fetch_posts(limit=settings.sync_max_posts)
            post_id_map: dict[str, int] = {}
            run.phase = "fetching_posts"
            await self._progress(account, run)
            for p in posts:
                if _cancelled(account_id):
                    raise asyncio.CancelledError()
                row = await post_service.upsert_post(self.db, account.id, p)
                post_id_map[p.platform_post_id] = row.id
                posts_fetched += 1
                run.posts_fetched = posts_fetched
                # Live progress: persist + push so the UI can show "5/20".
                # Throttle to every 5 rows — a page can have hundreds of
                # posts and flushing + broadcasting per row is wasteful.
                if posts_fetched % 5 == 0:
                    await self._progress(account, run, posts_fetched=posts_fetched, comments_fetched=comments_fetched)

            # metrics + snapshots
            try:
                run.phase = "fetching_metrics"
                await self._progress(account, run, posts_fetched=posts_fetched, comments_fetched=comments_fetched)
                metrics_list = await adapter.fetch_post_metrics(list(post_id_map.keys()))
                for m in metrics_list:
                    await post_service.apply_metrics(self.db, account.id, m)
            except UnsupportedFeatureError as exc:
                logger.info("metrics unsupported for %s: %s", account.platform, exc.message)

            run.phase = "fetching_comments"
            await self._progress(account, run, posts_fetched=posts_fetched, comments_fetched=comments_fetched)
            for platform_post_id, db_post_id in post_id_map.items():
                if _cancelled(account_id):
                    raise asyncio.CancelledError()
                try:
                    comments = await adapter.fetch_comments(platform_post_id)
                    for c in comments:
                        await comment_service.upsert_comment(
                            self.db, account.id, db_post_id, c
                        )
                        comments_fetched += 1
                        run.comments_fetched = comments_fetched
                        # Throttle: flush + broadcast every 10 comments; the
                        # terminal event always carries the final counts.
                        if comments_fetched % 10 == 0:
                            await self._progress(account, run, posts_fetched=posts_fetched, comments_fetched=comments_fetched)
                    # Release the write transaction after each post's comment
                    # batch; posts with few comments would otherwise hold the
                    # DB lock for the whole batch loop.
                    if comments_fetched % 10 != 0:
                        await self._progress(account, run, posts_fetched=posts_fetched, comments_fetched=comments_fetched)
                except UnsupportedFeatureError as exc:
                    logger.info(
                        "comments unsupported for %s post %s: %s",
                        account.platform,
                        platform_post_id,
                        exc.message,
                    )
                except AdapterError as exc:
                    logger.warning(
                        "comment fetch error account=%s: %s", account_id, exc.message
                    )

            run.status = SyncStatus.SUCCESS.value
            run.posts_fetched = posts_fetched
            run.comments_fetched = comments_fetched
            run.phase = "done"
            run.finished_at = datetime.now(UTC)
            account.last_successful_sync_at = run.finished_at
            account.account_status = AccountStatus.CONNECTED.value
            account.last_sync_error = None
            await self.db.flush()
            # Commit before broadcasting the terminal event. The frontend
            # invalidates and refetches on this event; publishing first lets
            # that refetch race the transaction and return the old sync time.
            await self.db.commit()
            # The dashboard has its own 60-second server-side cache. Clear it
            # before the terminal event as well, otherwise the frontend's
            # immediate refetch can still receive the pre-sync timestamp even
            # though the database transaction has already committed.
            await self._invalidate_dashboard_cache()
            await publish(
                self._terminal_event(run, account, message="同步完成")
            )
        except asyncio.CancelledError:
            run.status = SyncStatus.CANCELLED.value
            run.error_code = "cancelled"
            run.error_message = "同步已取消"
            run.phase = "done"
            run.finished_at = datetime.now(UTC)
            run.posts_fetched = posts_fetched
            run.comments_fetched = comments_fetched
            account.account_status = AccountStatus.CONNECTED.value
            await self.db.flush()
            await self.db.commit()
            await self._invalidate_dashboard_cache()
            await publish(
                self._terminal_event(run, account, message="同步已取消")
            )
        except AuthenticationRequiredError as exc:
            await self._fail(run, account, exc, AccountStatus.LOGIN_REQUIRED)
        except RateLimitError as exc:
            await self._fail(run, account, exc, AccountStatus.RATE_LIMITED)
        except PermissionDeniedError as exc:
            await self._fail(run, account, exc, AccountStatus.ERROR)
        except SelectorChangedError as exc:
            await self._fail(run, account, exc, AccountStatus.ERROR)
        except AdapterError as exc:
            await self._fail(run, account, exc, AccountStatus.ERROR)
        except Exception as exc:  # noqa: BLE001 — isolate failure
            logger.exception("Unexpected sync failure account=%s", account_id)
            run.status = SyncStatus.FAILED.value
            run.error_code = "internal_error"
            run.error_message = f"内部错误: {exc.__class__.__name__}"
            run.finished_at = datetime.now(UTC)
            run.posts_fetched = posts_fetched
            run.comments_fetched = comments_fetched
            run.phase = "done"
            account.account_status = AccountStatus.ERROR.value
            account.last_sync_error = run.error_message
            await self.db.flush()
            await self.db.commit()
            await self._invalidate_dashboard_cache()
            await publish(
                self._terminal_event(
                    run,
                    account,
                    message=run.error_message or f"内部错误: {exc.__class__.__name__}",
                    error_code=run.error_code or "internal_error",
                    error_message=run.error_message or f"内部错误: {exc.__class__.__name__}",
                )
            )
        finally:
            try:
                await adapter.close()
            except Exception:  # noqa: BLE001
                pass
            # The account lock is still held here, so only the cancel flag is
            # cleared; `sync_account` resets it before each run anyway.
            _cancel_flags.pop(account_id, None)
            await self.db.flush()
            # Best-effort backstop for exits before a terminal state is
            # persisted. Normal terminal paths invalidate before publishing.
            await self._invalidate_dashboard_cache()
        return run

    async def _progress(
        self,
        account: PlatformAccount,
        run: SyncRun,
        *,
        posts_fetched: int = 0,
        comments_fetched: int = 0,
    ) -> None:
        """Flush the run row and broadcast its current stage to SSE clients.

        Called between (and inside) the fetch loops so the UI can render live
        progress instead of only the terminal counts. The commit ends the
        write transaction so the session never holds the SQLite write lock
        across long scraping phases; concurrent syncs otherwise hit
        ``database is locked``.
        """
        run.posts_fetched = posts_fetched
        run.comments_fetched = comments_fetched
        await self.db.flush()
        await self.db.commit()
        await publish(
            SyncEvent(
                type="sync_update",
                run_id=run.id,
                account_id=account.id,
                platform=account.platform,
                status=run.status,
                phase=run.phase or "",
                posts_fetched=posts_fetched,
                comments_fetched=comments_fetched,
            )
        )

    def _terminal_event(
        self,
        run: SyncRun,
        account: PlatformAccount,
        *,
        message: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> SyncEvent:
        """Build the terminal SSE frame for a finished sync run."""
        return SyncEvent(
            type="sync_update",
            run_id=run.id,
            account_id=account.id,
            platform=account.platform,
            status=run.status,
            phase=run.phase or "done",
            posts_fetched=run.posts_fetched or 0,
            comments_fetched=run.comments_fetched or 0,
            message=message,
            error_code=error_code,
            error_message=error_message,
        )

    async def _invalidate_dashboard_cache(self) -> None:
        """Drop cached dashboard data before clients are told to refetch."""
        from app.services.dashboard_service import invalidate_cache

        await invalidate_cache()

    async def _fail(
        self,
        run: SyncRun,
        account: PlatformAccount,
        exc: AdapterError,
        status: AccountStatus,
    ) -> None:
        run.status = SyncStatus.FAILED.value
        run.error_code = exc.code
        run.error_message = exc.message
        run.phase = "done"
        run.finished_at = datetime.now(UTC)
        diag = sanitize_diagnostic(exc.diagnostic)
        if diag:
            run.diagnostic_json = json.dumps(diag, ensure_ascii=False)
        account.account_status = status.value
        account.last_sync_error = exc.message
        await self.db.flush()
        await self.db.commit()
        await self._invalidate_dashboard_cache()
        await publish(
            self._terminal_event(
                run,
                account,
                message=exc.message,
                error_code=exc.code,
                error_message=exc.message,
            )
        )
