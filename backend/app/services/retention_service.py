"""Data retention cleanup.

`DATA_RETENTION_DAYS` is documented in `.env.example` as "超过自动清理", and the
settings UI lets users change it, but nothing ever deleted anything: the database
grew without bound. This module implements that promise.

Deliberate design choices:

- Age is measured from ``published_at`` for posts, falling back to ``created_at``
  when a platform did not give us a publish time. Rows with neither are kept
  rather than guessed at.
- Comments whose ``local_status`` is still actionable (``new`` / ``pending``) are
  never deleted, even when old. Losing a comment the user has not dealt with is
  worse than keeping a stale row.
- Deleting a post cascades to its comments and metric snapshots via the ORM
  relationships, so trend history cannot outlive its parent post.
- ``SyncRun`` history is trimmed on the same horizon; it is pure diagnostics.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import delete, func, or_, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Delete

from app.models.comment import Comment
from app.models.enums import CommentLocalStatus
from app.models.metric_snapshot import MetricSnapshot
from app.models.post import Post
from app.models.sync_run import SyncRun

logger = logging.getLogger(__name__)

MIN_RETENTION_DAYS = 7

# Comments in these states still need the user's attention; never auto-delete.
PROTECTED_COMMENT_STATUSES = (
    CommentLocalStatus.NEW.value,
    CommentLocalStatus.PENDING.value,
)


@dataclass(frozen=True)
class CleanupReport:
    """What a cleanup pass removed. All counts are rows actually deleted."""

    cutoff: datetime
    retention_days: int
    posts_deleted: int = 0
    comments_deleted: int = 0
    snapshots_deleted: int = 0
    sync_runs_deleted: int = 0

    @property
    def total_deleted(self) -> int:
        return (
            self.posts_deleted
            + self.comments_deleted
            + self.snapshots_deleted
            + self.sync_runs_deleted
        )

    def as_dict(self) -> dict:
        data = asdict(self)
        data["cutoff"] = self.cutoff.isoformat()
        data["total_deleted"] = self.total_deleted
        return data


def _effective_age_column():
    """Age by publish time, falling back to ingest time when it is unknown."""
    return func.coalesce(Post.published_at, Post.created_at)


async def _delete_rows(db: AsyncSession, stmt: Delete) -> int:
    """Execute a DELETE and return the number of rows removed.

    ``rowcount`` is declared on ``CursorResult`` rather than the generic
    ``Result`` that ``execute`` is typed to return, so narrow it once here
    instead of ignoring the type error at every call site.
    """
    result = cast(CursorResult, await db.execute(stmt))
    return int(result.rowcount or 0)


async def cleanup_expired_data(
    db: AsyncSession,
    retention_days: int,
    *,
    now: datetime | None = None,
) -> CleanupReport:
    """Delete data older than ``retention_days``.

    Returns a report describing what was removed. The caller owns the
    transaction: this flushes but never commits, so a failure mid-pass cannot
    leave a half-cleaned database behind.
    """
    days = max(int(retention_days), MIN_RETENTION_DAYS)
    reference = now or datetime.now(UTC)
    cutoff = reference - timedelta(days=days)

    # --- Posts (cascades to their comments + snapshots) --------------------
    age = _effective_age_column()
    expired_post_ids = list(
        (
            await db.execute(select(Post.id).where(age.is_not(None), age < cutoff))
        ).scalars()
    )

    comments_deleted = 0
    snapshots_deleted = 0
    posts_deleted = 0

    if expired_post_ids:
        # An expired post may still own an unhandled comment. Keep the post in
        # that case so the comment stays reachable in the UI.
        protected = set(
            (
                await db.execute(
                    select(Comment.post_id).where(
                        Comment.post_id.in_(expired_post_ids),
                        Comment.local_status.in_(PROTECTED_COMMENT_STATUSES),
                    )
                )
            ).scalars()
        )
        deletable = [pid for pid in expired_post_ids if pid not in protected]

        if deletable:
            snapshots_deleted += await _delete_rows(
                db, delete(MetricSnapshot).where(MetricSnapshot.post_id.in_(deletable))
            )
            comments_deleted += await _delete_rows(
                db, delete(Comment).where(Comment.post_id.in_(deletable))
            )
            posts_deleted = await _delete_rows(
                db, delete(Post).where(Post.id.in_(deletable))
            )

    # --- Orphaned old comments on still-live posts ------------------------
    # Long threads on an evergreen post would otherwise never be trimmed.
    comments_deleted += await _delete_rows(
        db,
        delete(Comment).where(
            Comment.local_status.not_in(PROTECTED_COMMENT_STATUSES),
            or_(
                Comment.published_at < cutoff,
                Comment.published_at.is_(None) & (Comment.first_seen_at < cutoff),
            ),
        ),
    )

    # --- Sync run diagnostics --------------------------------------------
    sync_runs_deleted = await _delete_rows(
        db, delete(SyncRun).where(SyncRun.started_at < cutoff)
    )

    await db.flush()

    report = CleanupReport(
        cutoff=cutoff,
        retention_days=days,
        posts_deleted=posts_deleted,
        comments_deleted=comments_deleted,
        snapshots_deleted=snapshots_deleted,
        sync_runs_deleted=sync_runs_deleted,
    )
    if report.total_deleted:
        logger.info(
            "Retention cleanup removed %s rows older than %s (retention=%s days)",
            report.total_deleted,
            cutoff.isoformat(),
            days,
        )
    return report
