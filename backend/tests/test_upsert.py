from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.adapters.types import PlatformComment, PlatformPost, PlatformPostMetrics
from app.models.account import PlatformAccount
from app.models.enums import AccountStatus, AuthenticationType, CommentLocalStatus, Platform
from app.models.metric_snapshot import MetricSnapshot
from app.services import comment_service, post_service


@pytest.mark.asyncio
async def test_post_upsert_and_null_metrics(db_session):
    account = PlatformAccount(
        platform=Platform.ZHIHU.value,
        display_name="t",
        platform_user_id="u1",
        account_status=AccountStatus.CONNECTED.value,
        authentication_type=AuthenticationType.MOCK.value,
        is_mock=True,
    )
    db_session.add(account)
    await db_session.flush()

    p = PlatformPost(
        platform_post_id="p1",
        title="hello",
        view_count=None,
        like_count=10,
        published_at=datetime.now(UTC),
    )
    post = await post_service.upsert_post(db_session, account.id, p)
    assert post.view_count is None
    assert post.like_count == 10

    p2 = PlatformPost(
        platform_post_id="p1",
        title="hello2",
        view_count=100,
        like_count=None,  # should not overwrite with null
    )
    post2 = await post_service.upsert_post(db_session, account.id, p2)
    assert post2.id == post.id
    assert post2.view_count == 100
    assert post2.like_count == 10
    assert post2.title == "hello2"


@pytest.mark.asyncio
async def test_comment_dedupe_and_status(db_session):
    account = PlatformAccount(
        platform=Platform.X.value,
        display_name="t",
        platform_user_id="u2",
        account_status=AccountStatus.CONNECTED.value,
        authentication_type=AuthenticationType.MOCK.value,
        is_mock=True,
    )
    db_session.add(account)
    await db_session.flush()
    post = await post_service.upsert_post(
        db_session,
        account.id,
        PlatformPost(platform_post_id="px", title="t"),
    )
    c = PlatformComment(platform_comment_id="c1", content="hi", author_name="a")
    c1 = await comment_service.upsert_comment(db_session, account.id, post.id, c)
    c2 = await comment_service.upsert_comment(db_session, account.id, post.id, c)
    assert c1.id == c2.id
    assert c1.local_status == CommentLocalStatus.NEW.value

    updated = await comment_service.update_comment_status(
        db_session, c1.id, CommentLocalStatus.HANDLED
    )
    assert updated.local_status == CommentLocalStatus.HANDLED.value


@pytest.mark.asyncio
async def test_apply_metrics_snapshots_only_on_change(db_session):
    """Identical metrics must not grow the trend history with duplicate rows."""
    account = PlatformAccount(
        platform=Platform.ZHIHU.value,
        display_name="t",
        platform_user_id="u3",
        account_status=AccountStatus.CONNECTED.value,
        authentication_type=AuthenticationType.MOCK.value,
        is_mock=True,
    )
    db_session.add(account)
    await db_session.flush()
    await post_service.upsert_post(
        db_session,
        account.id,
        PlatformPost(platform_post_id="pm", title="t", view_count=10),
    )

    async def snapshot_count() -> int:
        return (
            await db_session.execute(select(func.count(MetricSnapshot.id)))
        ).scalar_one()

    first = PlatformPostMetrics(platform_post_id="pm", view_count=10, like_count=5)
    await post_service.apply_metrics(db_session, account.id, first)
    assert await snapshot_count() == 1

    # Same values again: nothing changed, no snapshot row.
    await post_service.apply_metrics(db_session, account.id, first)
    assert await snapshot_count() == 1

    # A real metric change appends exactly one new snapshot.
    await post_service.apply_metrics(
        db_session, account.id, PlatformPostMetrics(platform_post_id="pm", view_count=11)
    )
    assert await snapshot_count() == 2
