"""Durable background queue lifecycle tests."""

from __future__ import annotations

import asyncio

import pytest
from conftest import wait_for_sync_run
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.account import PlatformAccount
from app.models.sync_run import SyncRun
from app.sync import background


async def _create_mock_account(client, name: str = "后台同步") -> int:
    response = await client.post(
        "/api/accounts",
        json={
            "platform": "zhihu",
            "display_name": name,
            "username": f"background-{name}",
            "use_mock": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def test_sync_returns_queued_then_finishes(client):
    account_id = await _create_mock_account(client)

    response = await client.post(f"/api/accounts/{account_id}/sync")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "queued"
    run = await wait_for_sync_run(client, response.json()["sync_run_id"])
    assert run["status"] == "success"


async def test_duplicate_background_sync_is_rejected(client, monkeypatch):
    account_id = await _create_mock_account(client, "防重复")
    entered = asyncio.Event()
    release = asyncio.Event()
    original = background.SyncService.run_queued_account

    async def _blocked(self, queued_account_id: int, run_id: int, **kwargs):
        entered.set()
        await release.wait()
        return await original(self, queued_account_id, run_id, **kwargs)

    monkeypatch.setattr(background.SyncService, "run_queued_account", _blocked)
    first = await client.post(f"/api/accounts/{account_id}/sync")
    assert first.status_code == 200
    await asyncio.wait_for(entered.wait(), timeout=1)

    duplicate = await client.post(f"/api/accounts/{account_id}/sync")
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "conflict"

    release.set()
    await wait_for_sync_run(client, first.json()["sync_run_id"])


async def test_account_cannot_be_deleted_while_background_sync_is_active(client, monkeypatch):
    account_id = await _create_mock_account(client, "同步时禁止删除")
    entered = asyncio.Event()
    release = asyncio.Event()
    original = background.SyncService.run_queued_account

    async def _blocked(self, queued_account_id: int, run_id: int, **kwargs):
        entered.set()
        await release.wait()
        return await original(self, queued_account_id, run_id, **kwargs)

    monkeypatch.setattr(background.SyncService, "run_queued_account", _blocked)
    sync = await client.post(f"/api/accounts/{account_id}/sync")
    assert sync.status_code == 200
    await asyncio.wait_for(entered.wait(), timeout=1)

    deleted = await client.delete(f"/api/accounts/{account_id}")
    assert deleted.status_code == 409
    assert deleted.json()["detail"]["code"] == "conflict"

    release.set()
    # Drain the background writer before issuing another HTTP request against
    # the same temporary SQLite database.
    await background.shutdown_background_syncs()
    account = await client.get(f"/api/accounts/{account_id}")
    assert account.status_code == 200


async def test_queued_sync_can_be_cancelled(client, monkeypatch):
    account_id = await _create_mock_account(client, "排队取消")
    monkeypatch.setattr(background, "MAX_CONCURRENT_SYNCS", 1)
    gate = asyncio.Event()
    original = background.SyncService.run_queued_account

    async def _hold_first(self, queued_account_id: int, run_id: int, **kwargs):
        if queued_account_id != account_id:
            await gate.wait()
        return await original(self, queued_account_id, run_id, **kwargs)

    monkeypatch.setattr(background.SyncService, "run_queued_account", _hold_first)

    blocker_id = await _create_mock_account(client, "占用并发槽")
    blocker = await client.post(f"/api/accounts/{blocker_id}/sync")
    await asyncio.sleep(0)
    queued = await client.post(f"/api/accounts/{account_id}/sync")
    assert queued.json()["status"] == "queued"

    cancelled = await client.post(f"/api/accounts/{account_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["cancelling"] is True
    run = await wait_for_sync_run(client, queued.json()["sync_run_id"])
    assert run["status"] == "cancelled"

    gate.set()
    await wait_for_sync_run(client, blocker.json()["sync_run_id"])


async def test_recover_interrupted_syncs(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        account = PlatformAccount(
            platform="zhihu",
            display_name="遗留任务",
            platform_user_id="interrupted",
            account_status="syncing",
            authentication_type="mock",
            is_mock=True,
        )
        session.add(account)
        await session.flush()
        queued = SyncRun(account_id=account.id, platform="zhihu", status="queued")
        running = SyncRun(account_id=account.id, platform="zhihu", status="running")
        session.add_all([queued, running])
        await session.commit()
        account_id = account.id
        run_ids = [queued.id, running.id]

    recovered = await background.recover_interrupted_syncs(factory)
    assert recovered == 2

    async with factory() as session:
        runs = [await session.get(SyncRun, run_id) for run_id in run_ids]
        account = await session.get(PlatformAccount, account_id)
        assert all(run is not None and run.status == "failed" for run in runs)
        assert all(run is not None and run.error_code == "interrupted" for run in runs)
        assert account is not None
        assert account.account_status == "error"


@pytest.mark.parametrize("run_status", ["success", "failed", "cancelled"])
async def test_recovery_ignores_terminal_runs(db_engine, run_status):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        account = PlatformAccount(
            platform="zhihu",
            display_name="已结束",
            platform_user_id=f"terminal-{run_status}",
            account_status="connected",
            authentication_type="mock",
            is_mock=True,
        )
        session.add(account)
        await session.flush()
        session.add(SyncRun(account_id=account.id, platform="zhihu", status=run_status))
        await session.commit()

    assert await background.recover_interrupted_syncs(factory) == 0
