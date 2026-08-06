"""Optional local scheduled sync (disabled by default)."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.db.session import AsyncSessionLocal
from app.models.enums import SyncType
from app.services.account_service import list_accounts
from app.services.retention_service import cleanup_expired_data
from app.services.settings_service import get_or_create_settings
from app.sync.background import queue_background_sync

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _scheduled_job() -> None:
    """Queue eligible accounts without holding a scheduler-owned DB session."""
    async with AsyncSessionLocal() as db:
        app_settings = await get_or_create_settings(db)
        # The stored setting is authoritative: the UI toggle must be able to stop
        # scheduled scraping even when the .env default enables it.
        if not app_settings.enable_scheduled_sync:
            return
        accounts = await list_accounts(db)
        account_ids = [account.id for account in accounts]
        # Persist a lazily-created settings row before closing this short read
        # session. Every queued worker opens its own independent session.
        await db.commit()

    for account_id in account_ids:
        try:
            await queue_background_sync(
                AsyncSessionLocal,
                account_id,
                sync_type=SyncType.SCHEDULED,
            )
        except ConflictError:
            logger.info("Scheduled sync skipped active account %s", account_id)
        except Exception:  # noqa: BLE001 - isolate queue failures by account
            logger.exception("Could not queue scheduled sync for account %s", account_id)


async def _retention_job() -> None:
    """Apply the configured retention window.

    Runs regardless of ``enable_scheduled_sync``: pruning local rows touches no
    platform and carries none of the risk that made scheduled scraping opt-in.
    """
    async with AsyncSessionLocal() as db:
        try:
            app_settings = await get_or_create_settings(db)
            await cleanup_expired_data(db, app_settings.data_retention_days)
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Retention cleanup failed")
            await db.rollback()


def start_scheduler() -> AsyncIOScheduler | None:
    global _scheduler
    settings = get_settings()
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler()
    minutes = max(settings.sync_interval_minutes, 30)
    # Always register job; it no-ops when scheduled sync disabled.
    _scheduler.add_job(_scheduled_job, "interval", minutes=minutes, id="sync_all")
    _scheduler.add_job(_retention_job, "interval", hours=24, id="retention_cleanup")
    _scheduler.start()
    logger.info("Scheduler started (interval=%s min, enabled=%s)", minutes, settings.enable_scheduled_sync)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
