"""Sync run history model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.enums import SyncStatus, SyncType


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("platform_accounts.id"), index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    sync_type: Mapped[str] = mapped_column(String(32), default=SyncType.MANUAL.value)
    status: Mapped[str] = mapped_column(String(32), default=SyncStatus.RUNNING.value, index=True)
    # Coarse progress stage: checking_auth -> fetching_profile -> fetching_posts
    # -> fetching_metrics -> fetching_comments -> done. Persisted so a page
    # reload after a disconnect can still render the in-flight stage.
    phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    posts_fetched: Mapped[int] = mapped_column(Integer, default=0)
    comments_fetched: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostic_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    account = relationship("PlatformAccount", back_populates="sync_runs")
