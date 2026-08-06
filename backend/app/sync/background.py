"""Process-local background sync task management.

The API queues a durable ``SyncRun`` row before returning. The actual scraper
uses a fresh database session so it can outlive the request that started it.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import AppError, ConflictError
from app.models.account import PlatformAccount
from app.models.enums import AccountStatus, SyncStatus, SyncType
from app.models.sync_run import SyncRun
from app.services.account_service import get_account
from app.sync.events import SyncEvent, publish
from app.sync.service import SyncService, is_sync_running, request_cancel

logger = logging.getLogger(__name__)

MAX_CONCURRENT_SYNCS = 3


@dataclass
class BackgroundSync:
    account_id: int
    previous_account_status: str
    session_factory: async_sessionmaker[AsyncSession]
    run_id: int | None = None
    phase: str = SyncStatus.QUEUED.value
    task: asyncio.Task[None] | None = None


@dataclass(frozen=True)
class QueuedSync:
    account_id: int
    platform: str
    sync_run_id: int
    status: str = SyncStatus.QUEUED.value


_active_syncs: dict[int, BackgroundSync] = {}
_semaphore: asyncio.Semaphore | None = None


def _concurrency_limit() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNCS)
    return _semaphore


def is_background_sync_active(account_id: int) -> bool:
    entry = _active_syncs.get(account_id)
    return entry is not None and (entry.task is None or not entry.task.done())


async def queue_background_sync(
    session_factory: async_sessionmaker[AsyncSession],
    account_id: int,
    *,
    sync_type: SyncType = SyncType.MANUAL,
) -> QueuedSync:
    """Persist a queued run and dispatch it without retaining request state."""
    if is_background_sync_active(account_id) or is_sync_running(account_id):
        raise ConflictError("该账号已有同步任务正在排队或运行")

    # Reserve synchronously before the first await so two requests in the same
    # event loop cannot both enqueue the account.
    entry = BackgroundSync(
        account_id=account_id,
        previous_account_status="",
        session_factory=session_factory,
    )
    _active_syncs[account_id] = entry
    try:
        async with session_factory() as db:
            account = await get_account(db, account_id)
            if account.account_status == AccountStatus.SYNCING.value:
                raise ConflictError("该账号已有同步任务正在排队或运行")
            entry.previous_account_status = account.account_status
            run = SyncRun(
                account_id=account.id,
                platform=account.platform,
                sync_type=sync_type.value,
                status=SyncStatus.QUEUED.value,
                started_at=datetime.now(UTC),
            )
            db.add(run)
            account.account_status = AccountStatus.SYNCING.value
            account.last_sync_attempt_at = datetime.now(UTC)
            account.last_sync_error = None
            run.phase = "queued"
            await db.flush()
            entry.run_id = run.id
            platform = account.platform
            await db.commit()

        entry.task = asyncio.create_task(
            _run_background_sync(session_factory, entry, sync_type),
            name=f"creatorpulse-sync-{account_id}-{entry.run_id}",
        )
        assert entry.run_id is not None
        await publish(
            SyncEvent(
                type="sync_update",
                run_id=entry.run_id,
                account_id=account_id,
                platform=platform,
                status=SyncStatus.QUEUED.value,
                phase="queued",
                message="已加入后台队列",
            )
        )
        return QueuedSync(
            account_id=account_id,
            platform=platform,
            sync_run_id=entry.run_id,
        )
    except BaseException:
        if _active_syncs.get(account_id) is entry:
            _active_syncs.pop(account_id, None)
        raise


async def _run_background_sync(
    session_factory: async_sessionmaker[AsyncSession],
    entry: BackgroundSync,
    sync_type: SyncType,
) -> None:
    assert entry.run_id is not None
    try:
        async with _concurrency_limit():
            entry.phase = SyncStatus.RUNNING.value
            async with session_factory() as db:
                service = SyncService(db)
                await service.run_queued_account(
                    entry.account_id,
                    entry.run_id,
                    sync_type=sync_type,
                )
                await db.commit()
    except asyncio.CancelledError:
        await _mark_stopped(
            session_factory,
            entry,
            status=SyncStatus.CANCELLED,
            error_code="cancelled",
            message="同步已取消",
        )
    except Exception as exc:  # noqa: BLE001 - task must persist its own failure
        logger.exception("Background sync failed account=%s", entry.account_id)
        await _mark_stopped(
            session_factory,
            entry,
            status=SyncStatus.FAILED,
            error_code=exc.code if isinstance(exc, AppError) else "internal_error",
            message=exc.message if isinstance(exc, AppError) else f"内部错误: {exc.__class__.__name__}",
        )
    finally:
        if _active_syncs.get(entry.account_id) is entry:
            _active_syncs.pop(entry.account_id, None)


async def _mark_stopped(
    session_factory: async_sessionmaker[AsyncSession],
    entry: BackgroundSync,
    *,
    status: SyncStatus,
    error_code: str,
    message: str,
) -> None:
    """Finish a run only when the service did not already finish it."""
    if entry.run_id is None:
        return
    try:
        async with session_factory() as db:
            run = await db.get(SyncRun, entry.run_id)
            account = await db.get(PlatformAccount, entry.account_id)
            if run is not None and run.status in {
                SyncStatus.QUEUED.value,
                SyncStatus.RUNNING.value,
            }:
                run_was_active = True
                run.status = status.value
                run.error_code = error_code
                run.error_message = message
                run.phase = "done"
                run.finished_at = datetime.now(UTC)
            else:
                run_was_active = False
            if account is not None and account.account_status == AccountStatus.SYNCING.value:
                account.account_status = (
                    entry.previous_account_status
                    if status == SyncStatus.CANCELLED and entry.phase == SyncStatus.QUEUED.value
                    else AccountStatus.ERROR.value
                )
                account.last_sync_error = None if status == SyncStatus.CANCELLED else message
            await db.commit()
            # Only broadcast when this call actually changed the run state;
            # the service's own CancelledError handler already publishes the
            # terminal frame when the run was mid-flight.
            if run_was_active:
                assert run is not None
                await publish(
                    SyncEvent(
                        type="sync_update",
                        run_id=run.id,
                        account_id=entry.account_id,
                        platform=run.platform,
                        status=run.status,
                        phase=run.phase or "done",
                        message=message,
                        error_code=error_code,
                        error_message=message,
                    )
                )
    except Exception:  # noqa: BLE001 - best effort after a task-level failure
        logger.exception("Could not persist stopped sync account=%s", entry.account_id)


async def cancel_background_sync(account_id: int) -> bool:
    """Cancel a queued task, or request cooperative cancellation when running."""
    entry = _active_syncs.get(account_id)
    if entry is None or entry.task is None or entry.task.done():
        return request_cancel(account_id)
    if entry.phase == SyncStatus.QUEUED.value:
        entry.task.cancel()
        # Wait until the task persists its terminal state. This keeps a user
        # refresh immediately after cancellation from showing a stale queue row.
        await asyncio.gather(entry.task, return_exceptions=True)
        await _mark_stopped(
            entry=entry,
            session_factory=entry.session_factory,
            status=SyncStatus.CANCELLED,
            error_code="cancelled",
            message="同步已取消",
        )
        if _active_syncs.get(account_id) is entry:
            _active_syncs.pop(account_id, None)
        return True
    if request_cancel(account_id):
        return True
    # The worker may have acquired the global slot but not the per-account lock
    # yet. In that narrow window it has not started scraping, so direct task
    # cancellation is still safe and avoids a false "nothing is running" reply.
    entry.task.cancel()
    await asyncio.gather(entry.task, return_exceptions=True)
    await _mark_stopped(
        entry=entry,
        session_factory=entry.session_factory,
        status=SyncStatus.CANCELLED,
        error_code="cancelled",
        message="同步已取消",
    )
    if _active_syncs.get(account_id) is entry:
        _active_syncs.pop(account_id, None)
    return True


async def recover_interrupted_syncs(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Close durable active states left behind by a previous process."""
    async with session_factory() as db:
        runs = list(
            (
                await db.execute(
                    select(SyncRun).where(
                        SyncRun.status.in_(
                            [SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        if not runs:
            return 0
        now = datetime.now(UTC)
        account_ids = {run.account_id for run in runs}
        for run in runs:
            run.status = SyncStatus.FAILED.value
            run.error_code = "interrupted"
            run.error_message = "应用上次退出时同步尚未完成"
            run.finished_at = now
        accounts = list(
            (
                await db.execute(
                    select(PlatformAccount).where(PlatformAccount.id.in_(account_ids))
                )
            )
            .scalars()
            .all()
        )
        for account in accounts:
            if account.account_status == AccountStatus.SYNCING.value:
                account.account_status = AccountStatus.ERROR.value
                account.last_sync_error = "应用上次退出时同步尚未完成"
        await db.commit()
        return len(runs)


async def shutdown_background_syncs() -> None:
    """Cancel and await all task-owned sessions before the DB engine closes."""
    entries = list(_active_syncs.values())
    tasks = [entry.task for entry in entries if entry.task is not None and not entry.task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _active_syncs.clear()


def reset_background_sync_state_for_tests() -> None:
    """Reset loop-bound primitives after tests have drained all tasks."""
    global _semaphore
    _active_syncs.clear()
    _semaphore = None
