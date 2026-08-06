"""Map X API v2 plain-dict payloads into CreatorPulse DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.adapters.types import PlatformComment, PlatformPost, PlatformPostMetrics


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_tweet(item: dict[str, Any], username: str = "i") -> PlatformPost:
    """Map a tweet payload to a PlatformPost."""
    metrics = item.get("public_metrics") or {}
    text = item.get("text") or ""
    tid = str(item.get("id"))
    return PlatformPost(
        platform_post_id=tid,
        title=text[:80] + ("…" if len(text) > 80 else ""),
        content_preview=text[:280],
        post_url=f"https://x.com/{username}/status/{tid}",
        post_type="tweet",
        published_at=_parse_datetime(item.get("created_at")),
        # impression_count may require elevated access; keep null when absent.
        view_count=None,
        impression_count=metrics.get("impression_count"),
        like_count=metrics.get("like_count"),
        favorite_count=None,
        share_count=None,
        repost_count=metrics.get("retweet_count"),
        comment_count=metrics.get("reply_count"),
        raw_metrics={
            k: metrics.get(k)
            for k in (
                "like_count",
                "retweet_count",
                "reply_count",
                "quote_count",
                "impression_count",
                "bookmark_count",
            )
            if k in metrics
        },
    )


def parse_metrics(item: dict[str, Any]) -> PlatformPostMetrics:
    """Map a tweet payload to metrics (used by the batch /tweets endpoint)."""
    metrics = item.get("public_metrics") or {}
    return PlatformPostMetrics(
        platform_post_id=str(item["id"]),
        view_count=None,
        impression_count=metrics.get("impression_count"),
        like_count=metrics.get("like_count"),
        favorite_count=None,
        share_count=None,
        repost_count=metrics.get("retweet_count"),
        comment_count=metrics.get("reply_count"),
        raw_metrics=dict(metrics),
    )


def parse_reply(
    item: dict[str, Any],
    *,
    post_id: str,
    users: dict[str, dict[str, Any]],
) -> PlatformComment | None:
    """Map a search_recent reply payload to a PlatformComment."""
    if str(item.get("id")) == str(post_id):
        return None
    author = users.get(str(item.get("author_id") or ""), {})
    text = item.get("text") or ""
    cid = str(item["id"])
    uname = author.get("username") or "i"
    metrics = item.get("public_metrics") or {}
    return PlatformComment(
        platform_comment_id=cid,
        content=text,
        author_name=author.get("name") or uname,
        author_platform_id=str(item.get("author_id") or ""),
        comment_url=f"https://x.com/{uname}/status/{cid}",
        published_at=_parse_datetime(item.get("created_at")),
        like_count=metrics.get("like_count"),
        platform_reply_count=metrics.get("reply_count"),
        replied_by_owner=None,
        raw={"conversation_id": post_id},
    )


__all__ = [
    "parse_tweet",
    "parse_metrics",
    "parse_reply",
    "_parse_datetime",
]
