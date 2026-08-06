"""Application settings stored in SQLite."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class AppSettings(Base):
    """Singleton-style settings row (id always 1)."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, default=1)
    enable_scheduled_sync: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    sync_max_posts: Mapped[int] = mapped_column(Integer, default=50)
    data_retention_days: Mapped[int] = mapped_column(Integer, default=365)
    dev_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_mock_data: Mapped[bool] = mapped_column(Boolean, default=False)
    data_dir_display: Mapped[str | None] = mapped_column(Text, nullable=True)
    browser_profiles_dir_display: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now(), onupdate=func.now()
    )
