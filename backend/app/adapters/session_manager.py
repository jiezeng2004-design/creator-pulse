"""Keep browser adapters alive across login / check-auth API calls."""

from __future__ import annotations

import logging

from app.adapters.base import PlatformAdapter

logger = logging.getLogger(__name__)

__all__ = ["hold_adapter", "release_adapter", "release_all", "get_held_adapter"]

# account_id -> live adapter (Playwright window kept open for manual login)
_held_adapters: dict[int, PlatformAdapter] = {}


def get_held_adapter(account_id: int) -> PlatformAdapter | None:
    return _held_adapters.get(account_id)


async def hold_adapter(account_id: int, adapter: PlatformAdapter) -> None:
    """Store adapter and keep its browser open. Replaces any previous hold."""
    previous = _held_adapters.pop(account_id, None)
    if previous is not None and previous is not adapter:
        try:
            await previous.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed closing previous held adapter: %s", exc)
    _held_adapters[account_id] = adapter


async def release_adapter(account_id: int) -> None:
    adapter = _held_adapters.pop(account_id, None)
    if adapter is None:
        return
    try:
        await adapter.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed releasing adapter %s: %s", account_id, exc)


async def release_all() -> None:
    ids = list(_held_adapters.keys())
    for account_id in ids:
        await release_adapter(account_id)
