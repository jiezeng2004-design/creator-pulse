from enum import StrEnum

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.exceptions import AppError, to_http_exception
from app.schemas.common import Page
from app.schemas.post import MetricSnapshotRead, PostRead
from app.services import post_service


class SortDir(StrEnum):
    asc = "asc"
    desc = "desc"


class SortBy(StrEnum):
    published_at = "published_at"
    view_count = "view_count"
    like_count = "like_count"
    comment_count = "comment_count"
    impression_count = "impression_count"


router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("", response_model=Page[PostRead])
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: str | None = None,
    account_id: int | None = None,
    search: str | None = Query(None, max_length=200),
    sort_by: SortBy = Query("published_at"),
    sort_dir: SortDir = Query("desc"),
    db: AsyncSession = Depends(get_session),
) -> Page[PostRead]:
    rows, total = await post_service.list_posts(
        db,
        page=page,
        page_size=page_size,
        platform=platform,
        account_id=account_id,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    items = [
        PostRead(
            id=post.id,
            account_id=post.account_id,
            platform=account.platform,
            account_display_name=account.display_name,
            platform_post_id=post.platform_post_id,
            title=post.title,
            content_preview=post.content_preview,
            post_url=post.post_url,
            post_type=post.post_type,
            published_at=post.published_at,
            metrics_updated_at=post.metrics_updated_at,
            view_count=post.view_count,
            impression_count=post.impression_count,
            like_count=post.like_count,
            favorite_count=post.favorite_count,
            share_count=post.share_count,
            repost_count=post.repost_count,
            comment_count=post.comment_count,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
        for post, account in rows
    ]
    return Page(page=page, page_size=page_size, total=total, items=items)


@router.get("/{post_id}", response_model=PostRead)
async def get_post(post_id: int, db: AsyncSession = Depends(get_session)) -> PostRead:
    try:
        post, account = await post_service.get_post(db, post_id)
        return PostRead(
            id=post.id,
            account_id=post.account_id,
            platform=account.platform,
            account_display_name=account.display_name,
            platform_post_id=post.platform_post_id,
            title=post.title,
            content_preview=post.content_preview,
            post_url=post.post_url,
            post_type=post.post_type,
            published_at=post.published_at,
            metrics_updated_at=post.metrics_updated_at,
            view_count=post.view_count,
            impression_count=post.impression_count,
            like_count=post.like_count,
            favorite_count=post.favorite_count,
            share_count=post.share_count,
            repost_count=post.repost_count,
            comment_count=post.comment_count,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/{post_id}/metrics", response_model=list[MetricSnapshotRead])
async def post_metrics(
    post_id: int, db: AsyncSession = Depends(get_session)
) -> list[MetricSnapshotRead]:
    snaps = await post_service.list_metrics(db, post_id)
    return [MetricSnapshotRead.model_validate(s) for s in snaps]
