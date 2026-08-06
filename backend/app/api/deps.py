"""API dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Expose the session factory for handlers that need independent sessions.

    An ``AsyncSession`` is not safe for concurrent use, so fan-out work (for
    example syncing several accounts at once) must open one session per task
    instead of sharing the request-scoped session. Tests override this to point
    at an isolated engine.
    """
    return AsyncSessionLocal
