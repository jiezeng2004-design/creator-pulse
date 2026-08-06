"""Post / content model with nullable metrics."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("account_id", "platform_post_id", name="uq_account_post"),
        Index("ix_posts_published_at", "published_at"),
        Index("ix_posts_account_id_published_at", "account_id", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("platform_accounts.id"), index=True)
    platform_post_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    metrics_updated_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    # Metrics must be nullable — never default to 0 to fake missing data.
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impression_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    favorite_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    share_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repost_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now(), onupdate=func.now()
    )

    account = relationship("PlatformAccount", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    metric_snapshots = relationship(
        "MetricSnapshot", back_populates="post", cascade="all, delete-orphan"
    )
