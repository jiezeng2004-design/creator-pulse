"""SSE endpoint streaming sync progress events to the UI."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from app.sync.events import subscribe, unsubscribe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["events"])

# Heartbeat every 15 s keeps proxies from closing an idle SSE connection.
_HEARTBEAT_SECONDS = 15.0


@router.get("/events")
async def stream_events(request: Request) -> StreamingResponse:
    """Server-Sent Events stream of sync progress.

    The UI opens one long-lived connection; every SyncEvent (queued, phase
    change, terminal status) is pushed over it. Clients that disappear are
    cleaned up when the request is cancelled by Starlette.
    """

    async def event_generator():
        queue = await subscribe()
        try:
            # Standard SSE headers are applied by StreamingResponse; the first
            # line tells EventSource the reconnect policy.
            yield "retry: 2000\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    frame = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_SECONDS)
                    yield frame
                except TimeoutError:
                    # Comment-only keep-alive frame.
                    yield ": keep-alive\n\n"
        finally:
            await unsubscribe(queue)
            logger.debug("SSE client disconnected")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
