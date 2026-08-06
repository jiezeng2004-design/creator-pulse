"""Comment upsert and local status management."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.types import PlatformComment
from app.core.exceptions import NotFoundError
from app.models.account import PlatformAccount
from app.models.comment import Comment
from app.models.enums import CommentLocalStatus
from app.models.post import Post


async def upsert_comment(
    db: AsyncSession,
    account_id: int,
    post_id: int,
    data: PlatformComment,
) -> Comment:
    result = await db.execute(
        select(Comment).where(
            Comment.account_id == account_id,
            Comment.platform_comment_id == data.platform_comment_id,
        )
    )
    existing = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if existing:
        existing.content = data.content or existing.content
        existing.author_name = data.author_name or existing.author_name
        existing.author_avatar_url = data.author_avatar_url or existing.author_avatar_url
        existing.like_count = data.like_count if data.like_count is not None else existing.like_count
        existing.platform_reply_count = (
            data.platform_reply_count
            if data.platform_reply_count is not None
            else existing.platform_reply_count
        )
        existing.comment_url = data.comment_url or existing.comment_url
        existing.last_seen_at = now
        if data.replied_by_owner is not None:
            existing.replied_by_owner = data.replied_by_owner
            if data.replied_by_owner and not existing.owner_reply_detected_at:
                existing.owner_reply_detected_at = now
        await db.flush()
        return existing

    comment = Comment(
        post_id=post_id,
        account_id=account_id,
        platform_comment_id=data.platform_comment_id,
        parent_comment_id=data.parent_comment_id,
        author_name=data.author_name,
        author_platform_id=data.author_platform_id,
        author_avatar_url=data.author_avatar_url,
        content=data.content,
        comment_url=data.comment_url,
        published_at=data.published_at,
        like_count=data.like_count,
        platform_reply_count=data.platform_reply_count,
        local_status=CommentLocalStatus.NEW.value,
        replied_by_owner=data.replied_by_owner,
        owner_reply_detected_at=now if data.replied_by_owner else None,
        first_seen_at=now,
        last_seen_at=now,
        raw_data_json=json.dumps(data.raw, ensure_ascii=False) if data.raw else None,
    )
    db.add(comment)
    await db.flush()
    return comment


async def list_comments(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    local_status: str | None = None,
    platform: str | None = None,
    account_id: int | None = None,
    post_id: int | None = None,
    search: str | None = None,
) -> tuple[list[tuple[Comment, Post, PlatformAccount]], int]:
    q = (
        select(Comment, Post, PlatformAccount)
        .join(Post, Comment.post_id == Post.id)
        .join(PlatformAccount, Comment.account_id == PlatformAccount.id)
    )
    count_q = (
        select(func.count(Comment.id))
        .select_from(Comment)
        .join(Post, Comment.post_id == Post.id)
        .join(PlatformAccount, Comment.account_id == PlatformAccount.id)
    )
    if local_status:
        q = q.where(Comment.local_status == local_status)
        count_q = count_q.where(Comment.local_status == local_status)
    if platform:
        q = q.where(PlatformAccount.platform == platform)
        count_q = count_q.where(PlatformAccount.platform == platform)
    if account_id:
        q = q.where(Comment.account_id == account_id)
        count_q = count_q.where(Comment.account_id == account_id)
    if post_id:
        q = q.where(Comment.post_id == post_id)
        count_q = count_q.where(Comment.post_id == post_id)
    if search:
        like = f"%{search}%"
        q = q.where(Comment.content.ilike(like) | Comment.author_name.ilike(like))
        count_q = count_q.where(Comment.content.ilike(like) | Comment.author_name.ilike(like))

    q = q.order_by(Comment.published_at.desc().nullslast(), Comment.id.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(q)).all()
    return [(row[0], row[1], row[2]) for row in rows], int(total)


async def update_comment_status(
    db: AsyncSession, comment_id: int, status: CommentLocalStatus
) -> Comment:
    comment = await db.get(Comment, comment_id)
    if not comment:
        raise NotFoundError(f"评论 {comment_id} 不存在")
    comment.local_status = status.value
    await db.flush()
    await db.refresh(comment)
    return comment


async def batch_update_comment_status(
    db: AsyncSession, comment_ids: list[int], status: CommentLocalStatus
) -> int:
    """Set the same local status on many comments in one round-trip.

    Returns the number of rows actually updated. Unknown ids are skipped so a
    stale selection cannot fail the whole batch.
    """
    if not comment_ids:
        return 0
    result = await db.execute(
        select(Comment).where(Comment.id.in_(comment_ids))
    )
    comments = list(result.scalars().all())
    for comment in comments:
        comment.local_status = status.value
    await db.flush()
    return len(comments)
