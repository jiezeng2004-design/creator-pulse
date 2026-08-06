"""Comment schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CommentLocalStatus
from app.schemas.common import ORMModel


class CommentRead(ORMModel):
    id: int
    post_id: int
    account_id: int
    platform: str | None = None
    platform_comment_id: str
    parent_comment_id: str | None
    author_name: str | None
    author_platform_id: str | None
    author_avatar_url: str | None
    content: str
    comment_url: str | None
    published_at: datetime | None
    like_count: int | None
    platform_reply_count: int | None
    local_status: str
    replied_by_owner: bool | None
    owner_reply_detected_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    post_title: str | None = None
    post_url: str | None = None
    account_display_name: str | None = None


class CommentStatusUpdate(BaseModel):
    local_status: CommentLocalStatus = Field(..., description="Local operational status only")
