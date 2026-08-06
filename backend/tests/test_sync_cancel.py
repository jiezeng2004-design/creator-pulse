"""Cancellation was implemented in the sync service but unreachable.

`request_cancel` existed and `_run` checked the flag at four checkpoints, yet no
route ever called it, so a long browser scrape could not be stopped from the UI.
"""

from __future__ import annotations

from app.models.account import PlatformAccount
from app.sync import service as sync_service


async def _account(db) -> PlatformAccount:
    account = PlatformAccount(
        platform="zhihu",
        display_name="cancel",
        platform_user_id="zhihu-cancel",
        account_status="connected",
        authentication_type="browser_profile",
    )
    db.add(account)
    await db.flush()
    return account


def test_request_cancel_ignores_idle_accounts():
    """A stale flag would abort the account's *next* sync instead of this one."""
    sync_service.cleanup_sync_state(4242)

    assert sync_service.request_cancel(4242) is False
    assert sync_service._cancelled(4242) is False


async def test_request_cancel_sets_flag_while_running():
    account_id = 4243
    sync_service.cleanup_sync_state(account_id)
    lock = sync_service._lock_for(account_id)

    async with lock:  # simulate an in-flight sync holding the account lock
        assert sync_service.is_sync_running(account_id) is True
        assert sync_service.request_cancel(account_id) is True
        assert sync_service._cancelled(account_id) is True

    sync_service.cleanup_sync_state(account_id)


async def test_cleanup_never_drops_a_held_lock():
    """Dropping a held lock let a second concurrent sync start on one account."""
    account_id = 4244
    sync_service.cleanup_sync_state(account_id)
    lock = sync_service._lock_for(account_id)

    async with lock:
        sync_service.cleanup_sync_state(account_id)
        # The same lock object must still be registered, and still locked.
        assert sync_service._lock_for(account_id) is lock
        assert sync_service.is_sync_running(account_id) is True

    sync_service.cleanup_sync_state(account_id)
    assert sync_service.is_sync_running(account_id) is False


async def test_cancel_endpoint_reports_when_nothing_is_running(client):
    created = await client.post(
        "/api/accounts",
        json={"platform": "zhihu", "display_name": "空闲", "use_mock": True},
    )
    account_id = created.json()["id"]

    resp = await client.post(f"/api/accounts/{account_id}/cancel")

    assert resp.status_code == 200
    body = resp.json()
    assert body["cancelling"] is False
    assert "没有正在进行" in body["message"]


async def test_cancel_endpoint_requests_stop_for_running_sync(client):
    created = await client.post(
        "/api/accounts",
        json={"platform": "zhihu", "display_name": "运行中", "use_mock": True},
    )
    account_id = created.json()["id"]

    lock = sync_service._lock_for(account_id)
    async with lock:  # pretend a sync is mid-flight
        resp = await client.post(f"/api/accounts/{account_id}/cancel")
        assert sync_service._cancelled(account_id) is True

    sync_service.cleanup_sync_state(account_id)

    assert resp.status_code == 200
    body = resp.json()
    assert body["cancelling"] is True
    assert body["account_id"] == account_id


async def test_cancel_endpoint_404s_for_unknown_account(client):
    resp = await client.post("/api/accounts/999999/cancel-sync")
    assert resp.status_code == 404


async def test_second_concurrent_sync_is_rejected(client, db_session):
    """The already_running guard depends on the lock surviving cleanup."""
    account = await _account(db_session)
    await db_session.commit()

    lock = sync_service._lock_for(account.id)
    async with lock:
        svc = sync_service.SyncService(db_session)
        run = await svc.sync_account(account.id)

    sync_service.cleanup_sync_state(account.id)

    assert run.status == "failed"
    assert run.error_code == "already_running"
