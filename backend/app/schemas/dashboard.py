"""Dashboard aggregate schemas."""

from datetime import datetime

from pydantic import BaseModel


class PlatformCard(BaseModel):
    platform: str
    platform_label: str
    account_count: int
    posts_last_7d: int | None
    total_views_or_impressions: int | None
    new_comments: int | None
    pending_comments: int | None
    last_sync_at: datetime | None
    metric_primary_label: str
    metric_primary_value: int | None
    metric_secondary_label: str
    metric_secondary_value: int | None
    metric_tertiary_label: str
    metric_tertiary_value: int | None
    metric_note: str | None = None
    status_summary: str
    experimental: bool = False
    is_mock: bool = False


class DashboardSummary(BaseModel):
    posts_last_24h: int
    posts_last_7d: int
    total_views_or_impressions: int | None
    total_engagement: int | None
    new_comments: int
    pending_comments: int
    platforms: list[PlatformCard]
    mock_mode: bool
    last_global_sync_at: datetime | None
