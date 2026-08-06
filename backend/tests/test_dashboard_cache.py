"""The dashboard TTL cache must not outlive a sync."""

from __future__ import annotations

from conftest import wait_for_sync_run
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.account import PlatformAccount
from app.services import dashboard_service
from app.sync import service as sync_service


async def test_sync_invalidates_dashboard_cache(client):
    """A freshly synced account must change the dashboard immediately.

    The summary is cached for 60s, so without explicit invalidation the UI would
    keep showing pre-sync numbers right after the user clicked sync.
    """
    await dashboard_service.invalidate_cache()

    create = await client.post(
        "/api/accounts",
        json={"platform": "zhihu", "display_name": "demo", "use_mock": True},
    )
    assert create.status_code == 200, create.text
    account_id = create.json()["id"]

    # Prime the cache while there is still no synced content.
    before = (await client.get("/api/dashboard/summary")).json()
    assert before["posts_last_7d"] == 0

    sync = await client.post(f"/api/accounts/{account_id}/sync")
    assert sync.status_code == 200, sync.text
    assert sync.json()["status"] == "queued"
    run = await wait_for_sync_run(client, sync.json()["sync_run_id"])
    assert run["status"] == "success"

    after = (await client.get("/api/dashboard/summary")).json()
    assert after["posts_last_7d"] > 0, "dashboard still served the pre-sync cache"


async def test_terminal_event_fires_after_timestamp_commit_and_cache_invalidation(
    client,
    db_engine,
    monkeypatch,
):
    """A terminal SSE event must be a reliable signal that fresh data is readable.

    The frontend refetches immediately when it receives this event. Publishing
    before either the transaction commit or dashboard-cache invalidation made
    the UI keep showing the previous relative sync time.
    """
    await dashboard_service.invalidate_cache()
    create = await client.post(
        "/api/accounts",
        json={"platform": "zhihu", "display_name": "timestamp demo", "use_mock": True},
    )
    assert create.status_code == 200, create.text
    account_id = create.json()["id"]

    # Prime the server-side dashboard cache with a missing sync timestamp.
    before = (await client.get("/api/dashboard/summary")).json()
    platform_before = next(item for item in before["platforms"] if item["platform"] == "zhihu")
    assert platform_before["last_sync_at"] is None
    assert dashboard_service._cache

    terminal_checked = False
    original_publish = sync_service.publish
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def assert_fresh_before_publish(event):
        nonlocal terminal_checked
        if event.account_id == account_id and event.status == "success":
            assert dashboard_service._cache == {}, "terminal event preceded cache invalidation"
            async with factory() as session:
                account = await session.get(PlatformAccount, account_id)
                assert account is not None
                assert account.last_successful_sync_at is not None, (
                    "terminal event preceded last_successful_sync_at commit"
                )
            terminal_checked = True
        await original_publish(event)

    monkeypatch.setattr(sync_service, "publish", assert_fresh_before_publish)
    sync = await client.post(f"/api/accounts/{account_id}/sync")
    assert sync.status_code == 200, sync.text
    run = await wait_for_sync_run(client, sync.json()["sync_run_id"])
    assert run["status"] == "success"
    assert terminal_checked, "success terminal event was not observed"

    after = (await client.get("/api/dashboard/summary")).json()
    platform_after = next(item for item in after["platforms"] if item["platform"] == "zhihu")
    assert platform_after["last_sync_at"] is not None


async def test_invalidate_cache_clears_entries():
    """`invalidate_cache` empties the module-level cache."""
    from datetime import UTC, datetime, timedelta
    from typing import cast

    from app.schemas.dashboard import DashboardSummary

    stale = cast(DashboardSummary, "stale")
    dashboard_service._cache["dashboard"] = (
        datetime.now(UTC) + timedelta(seconds=60),
        stale,
    )
    assert dashboard_service._cache
    await dashboard_service.invalidate_cache()
    assert dashboard_service._cache == {}


async def test_settings_patch_invalidates_dashboard_cache(client):
    """Settings changes (e.g. mock mode) must not be hidden by the 60s cache."""
    await dashboard_service.invalidate_cache()
    await client.get("/api/dashboard/summary")
    assert dashboard_service._cache, "dashboard summary should be cached"

    response = await client.patch("/api/settings", json={"enable_mock_data": True})
    assert response.status_code == 200, response.text
    assert dashboard_service._cache == {}, "settings change must drop the cache"

    # Restore the default so later tests are not affected.
    response = await client.patch("/api/settings", json={"enable_mock_data": False})
    assert response.status_code == 200, response.text
