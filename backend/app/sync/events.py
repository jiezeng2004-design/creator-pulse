"""In-process event bus for sync progress.

The UI polls sync state today; an SSE stream lets it react to progress
instantly instead. This module keeps a set of per-client ``asyncio.Queue``s and
fans out ``SyncEvent`` payloads. It is deliberately process-local: the app is a
single local process, so there is no cross-worker requirement.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# One bounded queue per connected SSE client.
_subscribers: set[asyncio.Queue[str]] = set()
_bus_lock = asyncio.Lock()

# Events that can be raised during a sync. `phase` is a coarse stage label that
# the frontend renders as a progress hint; counts are live best-effort values.
@dataclass
class SyncEvent:
    type: str  # "sync_update"
    run_id: int
    account_id: int
    platform: str
    status: str  # queued | running | success | failed | cancelled
    phase: str  # checking_auth | fetching_profile | fetching_posts | fetching_metrics | fetching_comments | done
    posts_fetched: int = 0
    comments_fetched: int = 0
    message: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    extra: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        """Serialize as an SSE data frame."""
        payload = asdict(self)
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def publish(event: SyncEvent) -> None:
    """Broadcast an event to every connected SSE client (fire-and-forget)."""
    frame = event.to_sse()
    async with _bus_lock:
        stale: list[asyncio.Queue[str]] = []
        for queue in _subscribers:
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:
                # Slow consumer: drop the oldest frame so the connection keeps
                # working instead of buffering unboundedly.
                try:
                    queue.get_nowait()
                    queue.put_nowait(frame)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    stale.append(queue)
        for queue in stale:
            _subscribers.discard(queue)
    logger.debug("published sync event run=%s status=%s phase=%s", event.run_id, event.status, event.phase)


async def subscribe() -> asyncio.Queue[str]:
    """Register a new client queue for the SSE endpoint."""
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    async with _bus_lock:
        _subscribers.add(queue)
    return queue


async def unsubscribe(queue: asyncio.Queue[str]) -> None:
    async with _bus_lock:
        _subscribers.discard(queue)


def active_subscriber_count() -> int:
    return len(_subscribers)


def clear_subscribers() -> None:
    """Drop all subscribers (used by tests)."""
    _subscribers.clear()
