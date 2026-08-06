"""The stored scheduled-sync setting must be authoritative over .env."""

from __future__ import annotations

from types import SimpleNamespace

from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.models.enums import SyncType
from app.models.settings import AppSettings
from app.sync import scheduler


async def test_stored_setting_off_overrides_env_on(db_engine, monkeypatch):
    """`ENABLE_SCHEDULED_SYNC=true` in .env must not defeat the UI toggle.

    Scheduled scraping carries account risk, so turning it off in the UI has to
    stop it even when the environment default enables it.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(AppSettings(id=1, enable_scheduled_sync=False))
        await session.commit()

    env_settings = get_settings()
    monkeypatch.setattr(env_settings, "enable_scheduled_sync", True)
    monkeypatch.setattr(scheduler, "get_settings", lambda: env_settings)
    monkeypatch.setattr(scheduler, "AsyncSessionLocal", factory)

    listed = False

    async def _should_not_run(_db):
        nonlocal listed
        listed = True
        return []

    monkeypatch.setattr(scheduler, "list_accounts", _should_not_run)

    await scheduler._scheduled_job()

    assert listed is False, "scheduled sync ran while the stored setting was off"


async def test_stored_setting_on_runs_job(db_engine, monkeypatch):
    """Enabled jobs queue every account through the shared background runner."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(AppSettings(id=1, enable_scheduled_sync=True))
        await session.commit()

    env_settings = get_settings()
    monkeypatch.setattr(env_settings, "enable_scheduled_sync", False)
    monkeypatch.setattr(scheduler, "get_settings", lambda: env_settings)
    monkeypatch.setattr(scheduler, "AsyncSessionLocal", factory)

    account_ids = [101, 102]

    async def _list(_db):
        return [SimpleNamespace(id=account_id) for account_id in account_ids]

    queued: list[tuple[object, int, SyncType]] = []

    async def _queue(factory_arg, account_id, *, sync_type):
        queued.append((factory_arg, account_id, sync_type))

    monkeypatch.setattr(scheduler, "list_accounts", _list)
    monkeypatch.setattr(scheduler, "queue_background_sync", _queue)

    await scheduler._scheduled_job()

    assert queued == [
        (factory, 101, SyncType.SCHEDULED),
        (factory, 102, SyncType.SCHEDULED),
    ]


async def test_scheduled_job_isolates_account_queue_failures(db_engine, monkeypatch):
    """An active or broken account must not prevent later accounts from queuing."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(AppSettings(id=1, enable_scheduled_sync=True))
        await session.commit()

    async def _list(_db):
        return [SimpleNamespace(id=201), SimpleNamespace(id=202), SimpleNamespace(id=203)]

    attempted: list[int] = []

    async def _queue(_factory, account_id, *, sync_type):
        assert sync_type == SyncType.SCHEDULED
        attempted.append(account_id)
        if account_id == 201:
            raise ConflictError("already active")
        if account_id == 202:
            raise RuntimeError("queue unavailable")

    monkeypatch.setattr(scheduler, "AsyncSessionLocal", factory)
    monkeypatch.setattr(scheduler, "list_accounts", _list)
    monkeypatch.setattr(scheduler, "queue_background_sync", _queue)

    await scheduler._scheduled_job()

    assert attempted == [201, 202, 203]
