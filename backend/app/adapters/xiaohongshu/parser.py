"""Xiaohongshu parser — robust field extraction from Galaxy API responses."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.adapters.types import PlatformComment, PlatformPost

logger = logging.getLogger(__name__)

# Common XHS timestamp formats
_TIMESTAMP_PATTERNS = [
    re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"),
    re.compile(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"),
    re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"),
    re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})"),
]


def _parse_timestamp(value: Any) -> datetime | None:
    """Try to parse a timestamp from various XHS formats."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    for pat in _TIMESTAMP_PATTERNS:
        m = pat.search(s)
        if m:
            try:
                return datetime.fromisoformat(m.group(1))
            except (ValueError, TypeError):
                continue
    # Try Unix timestamp (seconds or milliseconds)
    try:
        ts = float(s)
        if ts > 1e12:
            ts /= 1000
        return datetime.fromtimestamp(ts, tz=UTC)
    except (ValueError, TypeError, OSError):
        pass
    return None


def _int_or_none(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_note(item: dict[str, Any]) -> PlatformPost | None:
    pid = str(item.get("id") or item.get("note_id") or item.get("noteId") or "")
    if not pid:
        return None
    title = item.get("title") or item.get("display_title")
    desc = item.get("desc") or item.get("description") or item.get("content") or ""
    raw_time = (
        item.get("time")
        or item.get("created_at")
        or item.get("createdAt")
        or item.get("publish_time")
        or item.get("publishedAt")
    )
    return PlatformPost(
        platform_post_id=pid,
        title=title if isinstance(title, str) else None,
        content_preview=(desc or "")[:280] or None,
        post_url=item.get("share_link") or f"https://www.xiaohongshu.com/explore/{pid}",
        post_type="note",
        published_at=_parse_timestamp(raw_time),
        view_count=_int_or_none(item.get("view_count") or item.get("read_count")),
        impression_count=_int_or_none(item.get("imp_count") or item.get("exposure_count")),
        like_count=_int_or_none(item.get("like_count") or item.get("liked_count") or item.get("likes")),
        favorite_count=_int_or_none(item.get("collect_count") or item.get("collected_count")),
        share_count=_int_or_none(item.get("share_count") or item.get("shared_count")),
        repost_count=None,
        comment_count=_int_or_none(item.get("comment_count") or item.get("comments_count")),
        raw_metrics={"source": "xhs_parser"},
    )


def parse_comment(item: dict[str, Any], post_id: str) -> PlatformComment | None:
    cid = str(item.get("id") or item.get("comment_id") or item.get("commentId") or "")
    if not cid:
        return None
    user = item.get("user_info") or item.get("user") or {}
    if not isinstance(user, dict):
        user = {}
    raw_time = (
        item.get("create_time")
        or item.get("createdAt")
        or item.get("created_at")
        or item.get("time")
    )
    return PlatformComment(
        platform_comment_id=cid,
        content=str(item.get("content") or ""),
        author_name=user.get("nickname") or user.get("name") or user.get("display_name"),
        author_platform_id=str(user.get("user_id") or user.get("userId") or "") or None,
        published_at=_parse_timestamp(raw_time),
        like_count=_int_or_none(item.get("like_count") or item.get("digg_count")),
        raw={"post_id": post_id},
    )
