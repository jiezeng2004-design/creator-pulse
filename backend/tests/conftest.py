"""Pytest fixtures with isolated SQLite database."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_session, get_session_factory
from app.db.base import Base
from app.db.session import configure_sqlite_engine
from app.main import create_app
from app.models.sync_run import SyncRun
from app.sync.background import (
    is_background_sync_active,
    reset_background_sync_state_for_tests,
    shutdown_background_syncs,
)

TERMINAL_SYNC_STATUSES = {"success", "partial", "failed", "cancelled"}


async def wait_for_sync_run(
    client: AsyncClient,
    run_id: int,
    *,
    timeout: float = 3.0,
) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get("/api/sync-runs", params={"page_size": 100})
        response.raise_for_status()
        run = next((item for item in response.json()["items"] if item["id"] == run_id), None)
        if run is not None and run["status"] in TERMINAL_SYNC_STATUSES:
            # The run row is committed before the worker's in-memory cleanup
            # finishes; a follow-up DELETE would otherwise race it (409). Wait
            # until the background entry is fully gone before returning.
            account_id = run["account_id"]
            cleanup_deadline = asyncio.get_running_loop().time() + timeout
            while asyncio.get_running_loop().time() < cleanup_deadline:
                if not is_background_sync_active(account_id):
                    return run
                await asyncio.sleep(0.01)
            raise AssertionError(
                f"sync run {run_id} reached terminal state but account {account_id} "
                f"background entry never cleared within {timeout}s"
            )
        # Keep well under the API rate limit (100 req/60s) even for slow syncs.
        await asyncio.sleep(0.1)
    raise AssertionError(f"sync run {run_id} did not finish within {timeout}s")


async def wait_for_all_syncs(db_engine, *, timeout: float = 3.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    while asyncio.get_running_loop().time() < deadline:
        async with factory() as session:
            statuses = (await session.execute(select(SyncRun.status))).scalars().all()
        if statuses and all(status in TERMINAL_SYNC_STATUSES for status in statuses):
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"background syncs did not finish within {timeout}s")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    # Background syncs intentionally use independent sessions. A single
    # in-memory SQLite connection cannot safely exercise concurrent request and
    # worker transactions, so each test gets a real temporary SQLite file.
    database_path = (tmp_path / "creatorpulse-test.db").as_posix()
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", echo=False)
    configure_sqlite_engine(engine)
    async with engine.begin() as conn:
        from app import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app()

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _override
    # Fan-out handlers open their own sessions; point them at the test engine so
    # they never touch the real database file.
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await shutdown_background_syncs()
    reset_background_sync_state_for_tests()
    app.dependency_overrides.clear()
