"""Settings schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class SettingsRead(ORMModel):
    enable_scheduled_sync: bool
    sync_interval_minutes: int
    sync_max_posts: int
    data_retention_days: int
    dev_mode: bool
    enable_mock_data: bool
    data_dir_display: str | None
    browser_profiles_dir_display: str | None
    host: str = "127.0.0.1"
    updated_at: datetime | None = None


class SettingsUpdate(BaseModel):
    enable_scheduled_sync: bool | None = None
    sync_interval_minutes: int | None = Field(default=None, ge=30)
    sync_max_posts: int | None = Field(default=None, ge=1, le=200)
    data_retention_days: int | None = Field(default=None, ge=7, le=3650)
    dev_mode: bool | None = None
    enable_mock_data: bool | None = None


class CleanupResponse(BaseModel):
    """Result of applying the retention policy on demand."""

    retention_days: int
    cutoff: datetime
    posts_deleted: int
    comments_deleted: int
    snapshots_deleted: int
    sync_runs_deleted: int
    total_deleted: int
    message: str
