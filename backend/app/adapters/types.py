"""Standardized DTOs returned by platform adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AuthenticationResult:
    authenticated: bool
    message: str = ""
    display_name: str | None = None
    username: str | None = None
    platform_user_id: str | None = None
    avatar_url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountProfile:
    platform_user_id: str
    display_name: str
    username: str | None = None
    avatar_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformPost:
    platform_post_id: str
    title: str | None = None
    content_preview: str | None = None
    post_url: str | None = None
    post_type: str | None = None
    published_at: datetime | None = None
    view_count: int | None = None
    impression_count: int | None = None
    like_count: int | None = None
    favorite_count: int | None = None
    share_count: int | None = None
    repost_count: int | None = None
    comment_count: int | None = None
    raw_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformPostMetrics:
    platform_post_id: str
    view_count: int | None = None
    impression_count: int | None = None
    like_count: int | None = None
    favorite_count: int | None = None
    share_count: int | None = None
    repost_count: int | None = None
    comment_count: int | None = None
    raw_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformComment:
    platform_comment_id: str
    content: str
    author_name: str | None = None
    author_platform_id: str | None = None
    author_avatar_url: str | None = None
    parent_comment_id: str | None = None
    comment_url: str | None = None
    published_at: datetime | None = None
    like_count: int | None = None
    platform_reply_count: int | None = None
    replied_by_owner: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)
