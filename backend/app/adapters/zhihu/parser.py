"""Parse Zhihu creator / member API payloads into DTOs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.adapters.types import PlatformComment, PlatformPost


def _ts_to_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    """Return *value* when it is a dict, otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


def parse_creation_item(item: dict[str, Any]) -> PlatformPost | None:
    """Parse creators/creations/v2/all item."""
    if not isinstance(item, dict):
        return None
    ctype = str(item.get("type") or "")
    data = item.get("data") if isinstance(item.get("data"), dict) else item
    if not isinstance(data, dict):
        return None

    pid = str(data.get("id") or data.get("url_token") or "")
    if not pid:
        return None

    title = data.get("title")
    if not title and isinstance(data.get("question"), dict):
        title = data["question"].get("title")
    excerpt = data.get("excerpt") or data.get("content") or ""
    if isinstance(excerpt, str) and len(excerpt) > 280:
        excerpt = excerpt[:280]

    reaction = _as_dict(item.get("reaction"))
    # Prefer creator-center metrics; leave null when absent (do not fake 0).
    read = _int_or_none(reaction.get("read_count") or reaction.get("view_count"))
    like = _int_or_none(
        reaction.get("vote_up_count")
        if reaction.get("vote_up_count") is not None
        else reaction.get("like_count")
    )
    favorite = _int_or_none(reaction.get("collect_count"))
    comment = _int_or_none(reaction.get("comment_count"))

    post_url = None
    if ctype == "answer" or data.get("answer_type") or data.get("question_id"):
        qid = data.get("question_id")
        if qid:
            post_url = f"https://www.zhihu.com/question/{qid}/answer/{pid}"
        else:
            post_url = f"https://www.zhihu.com/answer/{pid}"
        post_type = "answer"
    elif ctype == "article" or data.get("article_type") is not None:
        post_url = f"https://zhuanlan.zhihu.com/p/{pid}"
        post_type = "article"
    elif ctype == "zvideo":
        post_url = f"https://www.zhihu.com/zvideo/{pid}"
        post_type = "zvideo"
    elif ctype == "pin":
        post_url = f"https://www.zhihu.com/pin/{pid}"
        post_type = "pin"
    else:
        post_type = ctype or "content"
        post_url = data.get("url") if isinstance(data.get("url"), str) else None

    return PlatformPost(
        platform_post_id=f"{post_type}:{pid}" if post_type else pid,
        title=title if isinstance(title, str) else None,
        content_preview=excerpt if isinstance(excerpt, str) and excerpt else None,
        post_url=post_url if isinstance(post_url, str) else None,
        post_type=post_type,
        published_at=_ts_to_dt(data.get("created_time") or data.get("created")),
        view_count=read,
        impression_count=None,
        like_count=like,
        favorite_count=favorite,
        share_count=None,
        repost_count=None,
        comment_count=comment,
        raw_metrics={
            "source": "creations_v2",
            "type": post_type,
            "raw_id": pid,
            "reaction_keys": list(reaction.keys()) if reaction else [],
        },
    )


def parse_member_answer(item: dict[str, Any]) -> PlatformPost | None:
    if not isinstance(item, dict):
        return None
    pid = str(item.get("id") or "")
    if not pid:
        return None
    question = _as_dict(item.get("question"))
    qid = question.get("id")
    title = question.get("title")
    excerpt = item.get("excerpt") or ""
    url = item.get("url")
    if isinstance(url, str) and url.startswith("http"):
        post_url = url.replace("api/v4/answers", "answer") if "/api/" in url else url
    elif qid:
        post_url = f"https://www.zhihu.com/question/{qid}/answer/{pid}"
    else:
        post_url = f"https://www.zhihu.com/answer/{pid}"

    return PlatformPost(
        platform_post_id=f"answer:{pid}",
        title=title if isinstance(title, str) else None,
        content_preview=(excerpt[:280] if isinstance(excerpt, str) else None),
        post_url=post_url,
        post_type="answer",
        published_at=_ts_to_dt(item.get("created_time")),
        view_count=None,  # member API often lacks read_count
        impression_count=None,
        like_count=_int_or_none(item.get("voteup_count")),
        favorite_count=None,
        share_count=None,
        repost_count=None,
        comment_count=_int_or_none(item.get("comment_count")),
        raw_metrics={"source": "member_answers", "raw_id": pid},
    )


def parse_member_article(item: dict[str, Any]) -> PlatformPost | None:
    if not isinstance(item, dict):
        return None
    pid = str(item.get("id") or "")
    if not pid:
        return None
    return PlatformPost(
        platform_post_id=f"article:{pid}",
        title=item.get("title") if isinstance(item.get("title"), str) else None,
        content_preview=(
            (item.get("excerpt") or "")[:280] if item.get("excerpt") else None
        ),
        post_url=f"https://zhuanlan.zhihu.com/p/{pid}",
        post_type="article",
        published_at=_ts_to_dt(item.get("created")),
        view_count=None,
        impression_count=None,
        like_count=_int_or_none(item.get("voteup_count")),
        favorite_count=None,
        share_count=None,
        repost_count=None,
        comment_count=_int_or_none(item.get("comment_count")),
        raw_metrics={"source": "member_articles", "raw_id": pid},
    )


def parse_comment_item(item: Any, post_id: str) -> PlatformComment | None:
    if not isinstance(item, dict):
        return None
    # comment_v5 shape
    cid = str(item.get("id") or item.get("comment_id") or "")
    if not cid:
        return None
    author = item.get("author") or item.get("member") or {}
    if isinstance(author, dict) and isinstance(author.get("member"), dict):
        author = author["member"]
    if not isinstance(author, dict):
        author = {}
    content = item.get("content") or item.get("text") or ""
    if isinstance(content, str) and "<" in content:
        import re

        content = re.sub(r"<[^>]+>", "", content)

    return PlatformComment(
        platform_comment_id=cid,
        content=content if isinstance(content, str) else str(content),
        author_name=author.get("name") or author.get("fullname"),
        author_platform_id=str(author.get("id") or author.get("url_token") or "") or None,
        author_avatar_url=author.get("avatar_url"),
        parent_comment_id=str(item["reply_comment_id"])
        if item.get("reply_comment_id")
        else None,
        comment_url=item.get("url") if isinstance(item.get("url"), str) else None,
        published_at=_ts_to_dt(item.get("created_time") or item.get("created")),
        like_count=_int_or_none(item.get("like_count") or item.get("vote_count")),
        platform_reply_count=_int_or_none(
            item.get("child_comment_count") or item.get("child_comments_count")
        ),
        replied_by_owner=None,
        raw={"post_id": post_id},
    )


def parse_posts_from_list(payload: Any) -> list[PlatformPost]:
    items: list[Any]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("data") or payload.get("list") or []
    else:
        items = []
    posts: list[PlatformPost] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # creations/v2 style
        if "reaction" in item or (item.get("type") and isinstance(item.get("data"), dict)):
            post = parse_creation_item(item)
        elif item.get("type") == "answer" or "question" in item:
            post = parse_member_answer(item)
        elif item.get("type") == "article" or "title" in item and "voteup_count" in item:
            post = parse_member_article(item)
        else:
            post = parse_creation_item(item)
        if post:
            posts.append(post)
    return posts
