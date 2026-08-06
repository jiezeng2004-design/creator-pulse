"""Application settings service."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.settings import AppSettings
from app.schemas.settings import SettingsUpdate


async def get_or_create_settings(db: AsyncSession) -> AppSettings:
    row = await db.get(AppSettings, 1)
    if row:
        return row
    cfg = get_settings()
    row = AppSettings(
        id=1,
        enable_scheduled_sync=cfg.enable_scheduled_sync,
        sync_interval_minutes=max(cfg.sync_interval_minutes, 30),
        sync_max_posts=cfg.sync_max_posts,
        data_retention_days=cfg.data_retention_days,
        dev_mode=cfg.dev_mode,
        enable_mock_data=cfg.enable_mock_data,
        data_dir_display=str(cfg.data_dir),
        browser_profiles_dir_display=str(cfg.browser_profiles_dir),
    )
    db.add(row)
    try:
        # Use a savepoint so a losing insert does not poison the caller's
        # transaction when several requests hit first-access concurrently.
        async with db.begin_nested():
            await db.flush()
        await db.refresh(row)
        return row
    except IntegrityError:
        # Another transaction created id=1 first. The savepoint rollback already
        # discarded our pending insert, so re-read the winning row.
        existing = await db.get(AppSettings, 1)
        if existing is None:
            raise
        return existing


async def update_settings(db: AsyncSession, payload: SettingsUpdate) -> AppSettings:
    row = await get_or_create_settings(db)
    data = payload.model_dump(exclude_unset=True)
    if "sync_interval_minutes" in data and data["sync_interval_minutes"] is not None:
        data["sync_interval_minutes"] = max(int(data["sync_interval_minutes"]), 30)
    for k, v in data.items():
        setattr(row, k, v)
    await db.flush()
    await db.refresh(row)
    return row
