"""Toutiao JSON parser (best-effort)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.adapters.types import PlatformComment, PlatformPost


def _int_or_none(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _ts(v: Any) -> datetime | None:
    if v is None:
        return None
    try:
        if isinstance(v, (int, float)):
            ts = float(v)
            if ts > 1e12:
                ts /= 1000
            return datetime.fromtimestamp(ts, tz=UTC)
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def parse_article(item: dict[str, Any]) -> PlatformPost | None:
    # Current mp.toutiao.com feed wraps each item as assembleCell.itemCell;
    # keep legacy flat fields as fallback for older API shapes.
    cell = item.get("assembleCell") or {}
    if isinstance(cell, dict):
        cell = cell.get("itemCell") or cell
    base = cell.get("articleBase") or {}
    counter = cell.get("itemCounter") or {}
    if isinstance(base, dict) and isinstance(counter, dict):
        merged = {**base, **counter}
        merged.setdefault("item_id", base.get("groupID") or base.get("gidStr"))
        merged.setdefault("id", base.get("groupID") or base.get("gidStr"))
        merged.setdefault("title", base.get("title"))
        merged.setdefault("abstract", base.get("abstractText"))
        merged.setdefault("article_url", base.get("articleURL"))
        merged.setdefault("create_time", base.get("publishTime"))
        item = merged
    pid = str(item.get("item_id") or item.get("id") or item.get("GroupId") or "")
    if not pid:
        return None
    title = item.get("title") or item.get("Title")
    url = item.get("article_url") or item.get("display_url") or item.get("share_url")
    return PlatformPost(
        platform_post_id=pid,
        title=title if isinstance(title, str) else None,
        content_preview=(item.get("abstract") or item.get("content") or "")[:280] or None,
        post_url=url if isinstance(url, str) else f"https://www.toutiao.com/article/{pid}",
        post_type=str(item.get("article_type") or "article"),
        published_at=_ts(item.get("create_time") or item.get("publish_time")),
        view_count=_int_or_none(
            item.get("go_detail_count")
            or item.get("impression_count")
            or item.get("read_count")
            or item.get("readCount")
        ),
        impression_count=_int_or_none(
            item.get("show_count") or item.get("impr_count") or item.get("showCount")
        ),
        like_count=_int_or_none(
            item.get("digg_count") or item.get("like_count") or item.get("diggCount")
        ),
        favorite_count=_int_or_none(
            item.get("repin_count") or item.get("favor_count") or item.get("repinCount")
        ),
        share_count=_int_or_none(item.get("share_count") or item.get("shareCount")),
        repost_count=None,
        comment_count=_int_or_none(item.get("comment_count") or item.get("commentCount")),
        raw_metrics={"source": "toutiao_parser"},
    )


def parse_comment(item: dict[str, Any], post_id: str) -> PlatformComment | None:
    cid = str(item.get("id") or item.get("comment_id") or "")
    if not cid:
        return None
    user = item.get("user") or item.get("user_info") or {}
    if not isinstance(user, dict):
        user = {}
    return PlatformComment(
        platform_comment_id=cid,
        content=str(item.get("text") or item.get("content") or ""),
        author_name=(
            user.get("name")
            or user.get("screen_name")
            or item.get("user_name")
            or item.get("screen_name")
        ),
        author_platform_id=(
            str(user.get("user_id") or user.get("id") or item.get("user_id") or "") or None
        ),
        author_avatar_url=user.get("avatar_url") or item.get("avatar_url"),
        comment_url=None,
        published_at=_ts(item.get("create_time")),
        like_count=_int_or_none(item.get("digg_count")),
        platform_reply_count=_int_or_none(item.get("reply_count")),
        replied_by_owner=None,
        raw={"post_id": post_id},
    )
