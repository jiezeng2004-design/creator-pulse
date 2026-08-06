"""Post schemas."""

from datetime import datetime

from app.schemas.common import ORMModel


class PostRead(ORMModel):
    id: int
    account_id: int
    platform: str | None = None
    account_display_name: str | None = None
    platform_post_id: str
    title: str | None
    content_preview: str | None
    post_url: str | None
    post_type: str | None
    published_at: datetime | None
    metrics_updated_at: datetime | None
    view_count: int | None
    impression_count: int | None
    like_count: int | None
    favorite_count: int | None
    share_count: int | None
    repost_count: int | None
    comment_count: int | None
    created_at: datetime
    updated_at: datetime


class MetricSnapshotRead(ORMModel):
    id: int
    post_id: int
    captured_at: datetime
    view_count: int | None
    impression_count: int | None
    like_count: int | None
    favorite_count: int | None
    share_count: int | None
    repost_count: int | None
    comment_count: int | None
