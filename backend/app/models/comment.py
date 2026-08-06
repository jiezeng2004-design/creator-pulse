"""Comment model with local operational status."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.enums import CommentLocalStatus


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("account_id", "platform_comment_id", name="uq_account_comment"),
        Index("ix_comments_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("platform_accounts.id"), index=True)
    platform_comment_id: Mapped[str] = mapped_column(String(128), index=True)
    parent_comment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_platform_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    author_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    comment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    platform_reply_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    local_status: Mapped[str] = mapped_column(
        String(32), default=CommentLocalStatus.NEW.value, index=True
    )
    # Platform-detected owner reply (separate from local_status handled).
    replied_by_owner: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    owner_reply_detected_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime, server_default=func.now()
    )
    raw_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    post = relationship("Post", back_populates="comments")
    account = relationship("PlatformAccount", back_populates="comments")
