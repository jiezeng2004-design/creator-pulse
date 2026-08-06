"""Retention cleanup: `DATA_RETENTION_DAYS` was documented but never enforced."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models.account import PlatformAccount
from app.models.comment import Comment
from app.models.enums import CommentLocalStatus
from app.models.metric_snapshot import MetricSnapshot
from app.models.post import Post
from app.models.sync_run import SyncRun
from app.services import retention_service

NOW = datetime(2026, 8, 3, tzinfo=UTC)


async def _account(db) -> PlatformAccount:
    account = PlatformAccount(
        platform="zhihu",
        display_name="retention",
        platform_user_id="zhihu-retention",
        account_status="connected",
        authentication_type="browser_profile",
    )
    db.add(account)
    await db.flush()
    return account


async def _count(db, model) -> int:
    return int((await db.execute(select(func.count(model.id)))).scalar_one())


async def test_old_posts_are_deleted_and_recent_kept(db_session):
    account = await _account(db_session)
    old = Post(
        account_id=account.id,
        platform_post_id="old",
        published_at=NOW - timedelta(days=400),
    )
    recent = Post(
        account_id=account.id,
        platform_post_id="recent",
        published_at=NOW - timedelta(days=5),
    )
    db_session.add_all([old, recent])
    await db_session.flush()

    report = await retention_service.cleanup_expired_data(db_session, 365, now=NOW)

    assert report.posts_deleted == 1
    remaining = list((await db_session.execute(select(Post.platform_post_id))).scalars())
    assert remaining == ["recent"]


async def test_unhandled_comments_are_never_deleted(db_session):
    """Losing a comment the user has not dealt with is worse than a stale row."""
    account = await _account(db_session)
    post = Post(
        account_id=account.id,
        platform_post_id="ancient",
        published_at=NOW - timedelta(days=900),
    )
    db_session.add(post)
    await db_session.flush()

    pending = Comment(
        post_id=post.id,
        account_id=account.id,
        platform_comment_id="c-pending",
        content="还没处理",
        published_at=NOW - timedelta(days=800),
        local_status=CommentLocalStatus.PENDING.value,
    )
    db_session.add(pending)
    await db_session.flush()

    report = await retention_service.cleanup_expired_data(db_session, 365, now=NOW)

    # The post is kept alive because it still owns an actionable comment.
    assert report.posts_deleted == 0
    assert await _count(db_session, Comment) == 1
    assert await _count(db_session, Post) == 1


async def test_handled_comments_on_live_post_are_trimmed(db_session):
    account = await _account(db_session)
    post = Post(
        account_id=account.id,
        platform_post_id="evergreen",
        published_at=NOW - timedelta(days=3),
    )
    db_session.add(post)
    await db_session.flush()

    db_session.add_all(
        [
            Comment(
                post_id=post.id,
                account_id=account.id,
                platform_comment_id="c-old-handled",
                content="旧的已处理",
                published_at=NOW - timedelta(days=500),
                local_status=CommentLocalStatus.HANDLED.value,
            ),
            Comment(
                post_id=post.id,
                account_id=account.id,
                platform_comment_id="c-new-handled",
                content="新的已处理",
                published_at=NOW - timedelta(days=2),
                local_status=CommentLocalStatus.HANDLED.value,
            ),
        ]
    )
    await db_session.flush()

    report = await retention_service.cleanup_expired_data(db_session, 365, now=NOW)

    assert report.comments_deleted == 1
    assert report.posts_deleted == 0
    kept = list((await db_session.execute(select(Comment.platform_comment_id))).scalars())
    assert kept == ["c-new-handled"]


async def test_snapshots_do_not_outlive_their_post(db_session):
    account = await _account(db_session)
    post = Post(
        account_id=account.id,
        platform_post_id="with-history",
        published_at=NOW - timedelta(days=500),
    )
    db_session.add(post)
    await db_session.flush()
    db_session.add(MetricSnapshot(post_id=post.id, view_count=10))
    await db_session.flush()

    report = await retention_service.cleanup_expired_data(db_session, 365, now=NOW)

    assert report.posts_deleted == 1
    assert report.snapshots_deleted == 1
    assert await _count(db_session, MetricSnapshot) == 0


async def test_sync_run_history_is_trimmed(db_session):
    account = await _account(db_session)
    db_session.add_all(
        [
            SyncRun(
                account_id=account.id,
                platform="zhihu",
                sync_type="manual",
                status="success",
                started_at=NOW - timedelta(days=400),
            ),
            SyncRun(
                account_id=account.id,
                platform="zhihu",
                sync_type="manual",
                status="success",
                started_at=NOW - timedelta(days=1),
            ),
        ]
    )
    await db_session.flush()

    report = await retention_service.cleanup_expired_data(db_session, 365, now=NOW)

    assert report.sync_runs_deleted == 1
    assert await _count(db_session, SyncRun) == 1


async def test_retention_floor_is_enforced(db_session):
    """A too-small retention window is clamped, not honoured literally."""
    report = await retention_service.cleanup_expired_data(db_session, 1, now=NOW)
    assert report.retention_days == retention_service.MIN_RETENTION_DAYS


async def test_cleanup_endpoint_reports_counts(client):
    resp = await client.post("/api/settings/cleanup")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_deleted"] == 0
    assert body["retention_days"] >= retention_service.MIN_RETENTION_DAYS
    assert "没有需要清理" in body["message"]
