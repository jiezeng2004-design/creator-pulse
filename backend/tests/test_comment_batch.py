"""Tests for the bulk comment status endpoint."""

from __future__ import annotations

import pytest
from conftest import wait_for_sync_run


@pytest.mark.asyncio
async def test_batch_comment_status_updates_many(client):
    # Create a mock account and sync it so comments exist.
    r = await client.post(
        "/api/accounts",
        json={"platform": "zhihu", "display_name": "batch demo", "use_mock": True},
    )
    assert r.status_code == 200
    aid = r.json()["id"]

    r = await client.post(f"/api/accounts/{aid}/sync")
    assert r.status_code == 200
    await wait_for_sync_run(client, r.json()["sync_run_id"])

    r = await client.get("/api/comments", params={"page_size": 100})
    assert r.status_code == 200
    comments = r.json()
    assert comments["total"] >= 2, "mock adapter should provide comments"
    ids = [c["id"] for c in comments["items"]]

    # Bulk mark handled.
    r = await client.post(
        "/api/comments/batch-status",
        json={"comment_ids": ids, "local_status": "handled"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["updated"] == len(ids)
    assert body["status"] == "handled"

    r = await client.get("/api/comments", params={"local_status": "handled", "page_size": 100})
    assert r.json()["total"] == len(ids)

    # Bulk ignore a subset.
    subset = ids[:1]
    r = await client.post(
        "/api/comments/batch-status",
        json={"comment_ids": subset, "local_status": "ignored"},
    )
    assert r.status_code == 200
    assert r.json()["updated"] == len(subset)

    r = await client.get("/api/comments", params={"local_status": "ignored", "page_size": 100})
    assert r.json()["total"] == len(subset)


@pytest.mark.asyncio
async def test_batch_comment_status_validates_input(client):
    # Unknown ids are skipped rather than erroring.
    r = await client.post(
        "/api/comments/batch-status",
        json={"comment_ids": [999999], "local_status": "handled"},
    )
    assert r.status_code == 200
    assert r.json()["updated"] == 0

    # Empty list rejected.
    r = await client.post(
        "/api/comments/batch-status",
        json={"comment_ids": [], "local_status": "handled"},
    )
    assert r.status_code == 422

    # Invalid status rejected.
    r = await client.post(
        "/api/comments/batch-status",
        json={"comment_ids": [1], "local_status": "bogus"},
    )
    assert r.status_code == 422
