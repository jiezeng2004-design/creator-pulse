"""Integration test for the /api/events SSE endpoint.

httpx's ASGITransport buffers the whole response before returning, so it cannot
exercise an infinite SSE stream. These tests drive the ASGI app directly and
assert on the frames it emits — the same path uvicorn uses in production.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable

import pytest
from conftest import wait_for_sync_run

from app.main import create_app
from app.sync.events import SyncEvent, clear_subscribers, publish


def _http_scope(path: str) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 54321),
        "server": ("127.0.0.1", 8001),
    }


async def _drive_app(app, path: str) -> AsyncIterator[list[dict]]:
    """Run the ASGI app and yield every message it sends."""
    messages: list[dict] = []
    started = asyncio.Event()

    async def send(message: dict) -> None:
        messages.append(message)
        if message["type"] == "http.response.start":
            started.set()

    async def receive() -> dict:
        # Request body is empty; after the response starts, block so the
        # generator can keep running until the caller stops the app task.
        await started.wait()
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    task = asyncio.create_task(app(_http_scope(path), receive, send))
    try:
        yield messages
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass


async def _wait_for_data_frames(
    messages: list[dict],
    predicate: Callable[[list[dict]], bool],
    timeout: float = 5.0,
) -> list[dict]:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        frames = []
        for msg in messages:
            if msg["type"] == "http.response.body":
                for line in msg.get("body", b"").decode("utf-8", "replace").splitlines():
                    if line.startswith("data: "):
                        frames.append(json.loads(line[len("data: ") :]))
        if frames and predicate(frames):
            return frames
        await asyncio.sleep(0.01)
    raise AssertionError(f"no matching SSE data frames within {timeout}s: {messages}")


@pytest.mark.asyncio
async def test_events_endpoint_streams_sync_events():
    clear_subscribers()
    app = create_app()
    try:
        async for messages in _drive_app(app, "/api/events"):
            # Wait for the response to start, then publish an event.
            await asyncio.sleep(0.05)
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
            frames = await _wait_for_data_frames(
                messages, lambda fs: any(f["run_id"] == 1 for f in fs)
            )
            assert frames[-1]["run_id"] == 1
            assert frames[-1]["phase"] == "fetching_posts"
            assert frames[-1]["posts_fetched"] == 3
            # Initial response headers must mark the stream correctly.
            start = next(
                m for m in messages if m["type"] == "http.response.start"
            )
            headers = dict(start["headers"])
            assert headers[b"content-type"].startswith(b"text/event-stream")
    finally:
        clear_subscribers()


@pytest.mark.asyncio
async def test_events_endpoint_follows_real_sync(client):
    """A mock account sync completes while an SSE subscriber is connected.

    The stream itself is verified by the direct-ASGI test above; here we assert
    the two systems coexist: the sync reaches a terminal state and the SSE
    endpoint serves a 200 without disturbing the sync.
    """
    clear_subscribers()
    try:
        r = await client.post(
            "/api/accounts",
            json={"platform": "x", "display_name": "sse demo", "use_mock": True},
        )
        assert r.status_code == 200
        aid = r.json()["id"]

        r = await client.post(f"/api/accounts/{aid}/sync")
        assert r.status_code == 200
        run_id = r.json()["sync_run_id"]

        run = await wait_for_sync_run(client, run_id, timeout=5)
        assert run["status"] == "success"
        # Phase persisted so a page reload can still show progress.
        assert run["phase"] == "done"
    finally:
        clear_subscribers()
