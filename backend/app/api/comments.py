from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.exceptions import AppError, to_http_exception
from app.models.account import PlatformAccount
from app.models.enums import CommentLocalStatus
from app.models.post import Post
from app.schemas.comment import CommentRead, CommentStatusUpdate
from app.schemas.common import Page
from app.services import comment_service

router = APIRouter(prefix="/api/comments", tags=["comments"])


class CommentBatchStatusUpdate(BaseModel):
    comment_ids: list[int] = Field(min_length=1, max_length=500)
    local_status: CommentLocalStatus


@router.post("/batch-status")
async def batch_update_status(
    payload: CommentBatchStatusUpdate,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Set the same local status on many comments at once."""
    updated = await comment_service.batch_update_comment_status(
        db, payload.comment_ids, payload.local_status
    )
    return {"updated": updated, "status": payload.local_status.value}


@router.get("", response_model=Page[CommentRead])
async def list_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    local_status: str | None = None,
    platform: str | None = None,
    account_id: int | None = None,
    post_id: int | None = None,
    search: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_session),
) -> Page[CommentRead]:
    rows, total = await comment_service.list_comments(
        db,
        page=page,
        page_size=page_size,
        local_status=local_status,
        platform=platform,
        account_id=account_id,
        post_id=post_id,
        search=search,
    )
    items = [
        CommentRead(
            id=c.id,
            post_id=c.post_id,
            account_id=c.account_id,
            platform=account.platform,
            platform_comment_id=c.platform_comment_id,
            parent_comment_id=c.parent_comment_id,
            author_name=c.author_name,
            author_platform_id=c.author_platform_id,
            author_avatar_url=c.author_avatar_url,
            content=c.content,
            comment_url=c.comment_url,
            published_at=c.published_at,
            like_count=c.like_count,
            platform_reply_count=c.platform_reply_count,
            local_status=c.local_status,
            replied_by_owner=c.replied_by_owner,
            owner_reply_detected_at=c.owner_reply_detected_at,
            first_seen_at=c.first_seen_at,
            last_seen_at=c.last_seen_at,
            post_title=post.title,
            post_url=post.post_url,
            account_display_name=account.display_name,
        )
        for c, post, account in rows
    ]
    return Page(page=page, page_size=page_size, total=total, items=items)


@router.patch("/{comment_id}/status", response_model=CommentRead)
async def update_status(
    comment_id: int,
    payload: CommentStatusUpdate,
    db: AsyncSession = Depends(get_session),
) -> CommentRead:
    try:
        c = await comment_service.update_comment_status(
            db, comment_id, payload.local_status
        )
        # Fetch post and account info for complete response
        post_result = await db.execute(select(Post).where(Post.id == c.post_id))
        post = post_result.scalar_one_or_none()
        acc_result = await db.execute(select(PlatformAccount).where(PlatformAccount.id == c.account_id))
        account = acc_result.scalar_one_or_none()
        return CommentRead(
            id=c.id,
            post_id=c.post_id,
            account_id=c.account_id,
            platform=account.platform if account else "",
            platform_comment_id=c.platform_comment_id,
            parent_comment_id=c.parent_comment_id,
            author_name=c.author_name,
            author_platform_id=c.author_platform_id,
            author_avatar_url=c.author_avatar_url,
            content=c.content,
            comment_url=c.comment_url,
            published_at=c.published_at,
            like_count=c.like_count,
            platform_reply_count=c.platform_reply_count,
            local_status=c.local_status,
            replied_by_owner=c.replied_by_owner,
            owner_reply_detected_at=c.owner_reply_detected_at,
            first_seen_at=c.first_seen_at,
            last_seen_at=c.last_seen_at,
            post_title=post.title if post else None,
            post_url=post.post_url if post else None,
            account_display_name=account.display_name if account else None,
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc
