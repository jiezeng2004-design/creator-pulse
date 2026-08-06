"""Tests for the SSE sync-progress event bus and endpoint."""

from __future__ import annotations

import asyncio
import json

from app.sync.events import SyncEvent, clear_subscribers, publish, subscribe, unsubscribe


async def test_publish_fans_out_to_subscribers() -> None:
    clear_subscribers()
    queue = await subscribe()
    try:
        await publish(
            SyncEvent(
                type="sync_update",
                run_id=1,
                account_id=2,
                platform="zhihu",
                status="running",
                phase="fetching_posts",
                posts_fetched=3,
            )
        )
        frame = await asyncio.wait_for(queue.get(), timeout=1)
        assert frame.startswith("data: ")
        payload = json.loads(frame[len("data: ") :])
        assert payload["run_id"] == 1
        assert payload["account_id"] == 2
        assert payload["phase"] == "fetching_posts"
        assert payload["posts_fetched"] == 3
        # No sensitive fields leak into the frame.
        assert "cookie" not in json.dumps(payload).lower()
    finally:
        await unsubscribe(queue)
        clear_subscribers()


async def test_unsubscribe_stops_delivery() -> None:
    clear_subscribers()
    queue = await subscribe()
    await unsubscribe(queue)
    await publish(
        SyncEvent(
            type="sync_update",
            run_id=1,
            account_id=2,
            platform="x",
            status="queued",
            phase="queued",
        )
    )
    with_ = queue.qsize()
    assert with_ == 0
    clear_subscribers()


async def test_event_is_json_serializable() -> None:
    event = SyncEvent(
        type="sync_update",
        run_id=1,
        account_id=2,
        platform="toutiao",
        status="failed",
        phase="done",
        error_message="连接超时",
    )
    parsed = json.loads(event.to_sse()[len("data: ") :])
    assert parsed["status"] == "failed"
    assert parsed["error_message"] == "连接超时"
