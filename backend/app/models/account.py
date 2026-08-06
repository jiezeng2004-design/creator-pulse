"""Platform account model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.enums import AccountStatus, AuthenticationType


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    platform_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_status: Mapped[str] = mapped_column(
        String(32), default=AccountStatus.DISCONNECTED.value, index=True
    )
    authentication_type: Mapped[str] = mapped_column(
        String(32), default=AuthenticationType.BROWSER_PROFILE.value
    )
    browser_profile_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    last_sync_attempt_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mock: Mapped[bool] = mapped_column(default=False)
    feature_flags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now(), onupdate=func.now()
    )

    posts = relationship("Post", back_populates="account", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="account", cascade="all, delete-orphan")
    sync_runs = relationship("SyncRun", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PlatformAccount id={self.id} platform={self.platform} status={self.account_status}>"
