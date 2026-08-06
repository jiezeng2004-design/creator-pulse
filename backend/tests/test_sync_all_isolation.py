"""Regression tests for concurrent sync-all behaviour."""

from __future__ import annotations

import asyncio

from conftest import wait_for_all_syncs
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.account import PlatformAccount
from app.models.sync_run import SyncRun
from app.sync import background


async def _create_mock_account(client, platform: str) -> int:
    resp = await client.post(
        "/api/accounts",
        json={"platform": platform, "display_name": f"{platform} demo", "use_mock": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


async def test_sync_all_uses_independent_sessions(client, db_engine):
    """Several accounts sync concurrently without sharing one AsyncSession.

    Sharing the request session caused interleaved flushes; each account must
    record exactly one sync run.
    """
    platforms = ["x", "zhihu", "toutiao", "xiaohongshu"]
    account_ids = [await _create_mock_account(client, p) for p in platforms]

    resp = await client.post("/api/accounts/sync-all")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["total"] == len(account_ids)
    assert body["started"] == len(account_ids), body["items"]
    assert body["skipped"] == 0
    assert {item["account_id"] for item in body["items"]} == set(account_ids)
    for item in body["items"]:
        assert item["status"] == "queued"
        assert item["sync_run_id"] is not None

    await wait_for_all_syncs(db_engine)

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        rows = (
            await session.execute(
                select(SyncRun.account_id, func.count(SyncRun.id)).group_by(SyncRun.account_id)
            )
        ).all()
        counts = {account_id: count for account_id, count in rows}
        assert counts == dict.fromkeys(account_ids, 1), counts

        statuses = (await session.execute(select(SyncRun.status))).scalars().all()
        assert set(statuses) == {"success"}, statuses

        account_rows = (await session.execute(select(PlatformAccount))).scalars().all()
        assert {a.account_status for a in account_rows} == {"connected"}


async def test_sync_all_limits_concurrency(client, db_engine, monkeypatch):
    """Fan-out is bounded so a personal machine is not flooded with browsers."""
    for platform in ["x", "zhihu", "toutiao", "xiaohongshu"]:
        await _create_mock_account(client, platform)

    monkeypatch.setattr(background, "MAX_CONCURRENT_SYNCS", 2)

    state = {"in_flight": 0, "peak": 0}
    original = background.SyncService.run_queued_account

    async def _tracking_sync(self, account_id: int, run_id: int, **kwargs):
        state["in_flight"] += 1
        state["peak"] = max(state["peak"], state["in_flight"])
        try:
            await asyncio.sleep(0)
            return await original(self, account_id, run_id, **kwargs)
        finally:
            state["in_flight"] -= 1

    monkeypatch.setattr(background.SyncService, "run_queued_account", _tracking_sync)

    resp = await client.post("/api/accounts/sync-all")
    assert resp.status_code == 200, resp.text
    await wait_for_all_syncs(db_engine)
    assert state["peak"] <= 2, f"observed {state['peak']} concurrent syncs"


async def test_sync_all_skips_accounts_already_syncing(client, db_engine):
    """An account mid-sync is reported as skipped instead of double-synced."""
    account_id = await _create_mock_account(client, "zhihu")

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        account = await session.get(PlatformAccount, account_id)
        assert account is not None
        account.account_status = "syncing"
        await session.commit()

    resp = await client.post("/api/accounts/sync-all")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["started"] == 0
    assert body["skipped"] == 1
    assert body["items"] == [
        {
            "account_id": account_id,
            "platform": "zhihu",
            "status": "skipped",
            "message": "该账号正在同步，已跳过",
            "sync_run_id": None,
        }
    ]
