"""Post upsert and query."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.types import PlatformPost, PlatformPostMetrics
from app.core.exceptions import NotFoundError
from app.models.account import PlatformAccount
from app.models.metric_snapshot import MetricSnapshot
from app.models.post import Post


async def upsert_post(
    db: AsyncSession, account_id: int, data: PlatformPost
) -> Post:
    result = await db.execute(
        select(Post).where(
            Post.account_id == account_id,
            Post.platform_post_id == data.platform_post_id,
        )
    )
    post = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if post is None:
        post = Post(
            account_id=account_id,
            platform_post_id=data.platform_post_id,
            title=data.title,
            content_preview=data.content_preview,
            post_url=data.post_url,
            post_type=data.post_type,
            published_at=data.published_at,
            view_count=data.view_count,
            impression_count=data.impression_count,
            like_count=data.like_count,
            favorite_count=data.favorite_count,
            share_count=data.share_count,
            repost_count=data.repost_count,
            comment_count=data.comment_count,
            metrics_updated_at=now,
            raw_metrics_json=json.dumps(data.raw_metrics, ensure_ascii=False)
            if data.raw_metrics
            else None,
        )
        db.add(post)
    else:
        post.title = data.title or post.title
        post.content_preview = data.content_preview or post.content_preview
        post.post_url = data.post_url or post.post_url
        post.post_type = data.post_type or post.post_type
        post.published_at = data.published_at or post.published_at
        # Only overwrite metrics when adapter provided a value (keep null honest)
        for field in (
            "view_count",
            "impression_count",
            "like_count",
            "favorite_count",
            "share_count",
            "repost_count",
            "comment_count",
        ):
            val = getattr(data, field)
            if val is not None:
                setattr(post, field, val)
        post.metrics_updated_at = now
        if data.raw_metrics:
            post.raw_metrics_json = json.dumps(data.raw_metrics, ensure_ascii=False)
    await db.flush()
    return post


async def apply_metrics(
    db: AsyncSession, account_id: int, metrics: PlatformPostMetrics
) -> Post | None:
    result = await db.execute(
        select(Post).where(
            Post.account_id == account_id,
            Post.platform_post_id == metrics.platform_post_id,
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        return None
    now = datetime.now(UTC)
    changed = False
    for field in (
        "view_count",
        "impression_count",
        "like_count",
        "favorite_count",
        "share_count",
        "repost_count",
        "comment_count",
    ):
        val = getattr(metrics, field)
        if val is not None:
            if getattr(post, field) != val:
                changed = True
            setattr(post, field, val)
    if changed:
        post.metrics_updated_at = now
        snap = MetricSnapshot(
            post_id=post.id,
            captured_at=now,
            view_count=post.view_count,
            impression_count=post.impression_count,
            like_count=post.like_count,
            favorite_count=post.favorite_count,
            share_count=post.share_count,
            repost_count=post.repost_count,
            comment_count=post.comment_count,
        )
        db.add(snap)
    await db.flush()
    return post


async def list_posts(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    platform: str | None = None,
    account_id: int | None = None,
    search: str | None = None,
    sort_by: str = "published_at",
    sort_dir: str = "desc",
) -> tuple[list[tuple[Post, PlatformAccount]], int]:
    q = select(Post, PlatformAccount).join(
        PlatformAccount, Post.account_id == PlatformAccount.id
    )
    count_q = select(func.count(Post.id)).select_from(Post).join(
        PlatformAccount, Post.account_id == PlatformAccount.id
    )
    if platform:
        q = q.where(PlatformAccount.platform == platform)
        count_q = count_q.where(PlatformAccount.platform == platform)
    if account_id:
        q = q.where(Post.account_id == account_id)
        count_q = count_q.where(Post.account_id == account_id)
    if search:
        like = f"%{search}%"
        q = q.where(Post.title.ilike(like) | Post.content_preview.ilike(like))
        count_q = count_q.where(Post.title.ilike(like) | Post.content_preview.ilike(like))

    sort_map = {
        "published_at": Post.published_at,
        "view_count": Post.view_count,
        "like_count": Post.like_count,
        "comment_count": Post.comment_count,
        "impression_count": Post.impression_count,
    }
    col = sort_map.get(sort_by, Post.published_at)
    q = q.order_by(col.desc().nullslast() if sort_dir == "desc" else col.asc().nullslast())
    q = q.offset((page - 1) * page_size).limit(page_size)

    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(q)).all()
    return [(row[0], row[1]) for row in rows], int(total)


async def get_post(db: AsyncSession, post_id: int) -> tuple[Post, PlatformAccount]:
    result = await db.execute(
        select(Post, PlatformAccount)
        .join(PlatformAccount, Post.account_id == PlatformAccount.id)
        .where(Post.id == post_id)
    )
    row = result.one_or_none()
    if not row:
        raise NotFoundError(f"内容 {post_id} 不存在")
    return row[0], row[1]


async def list_metrics(db: AsyncSession, post_id: int) -> list[MetricSnapshot]:
    result = await db.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.post_id == post_id)
        .order_by(MetricSnapshot.captured_at.asc())
    )
    return list(result.scalars().all())
