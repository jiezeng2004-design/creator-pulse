"""CreatorPulse FastAPI entrypoint."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.adapters.session_manager import release_all
from app.api import (
    accounts,
    comments,
    dashboard,
    events,
    export,
    health,
    platforms,
    posts,
    sync_runs,
)
from app.api import (
    settings as settings_api,
)
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.ratelimit import (
    DEFAULT_LIMIT,
    DEFAULT_WINDOW_SECONDS,
    FixedWindowRateLimiter,
    RateLimitMiddleware,
)
from app.db.session import AsyncSessionLocal, close_db, init_db
from app.services.settings_service import get_or_create_settings
from app.sync.background import recover_interrupted_syncs, shutdown_background_syncs
from app.sync.scheduler import start_scheduler, stop_scheduler

_request_logger = logging.getLogger("app.request")


def _internal_error_handler(request: Request, exc: Exception) -> Response:
    logging.getLogger(__name__).exception("Unhandled exception")
    return Response(status_code=500, content='{"detail": "Internal server error"}', media_type="application/json")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    settings.ensure_directories()
    await init_db()
    # Seed singleton settings row so concurrent first requests do not race.
    async with AsyncSessionLocal() as session:
        await get_or_create_settings(session)
        await session.commit()
    recovered = await recover_interrupted_syncs(AsyncSessionLocal)
    if recovered:
        logging.getLogger(__name__).warning(
            "Marked %s interrupted background syncs as failed", recovered
        )
    start_scheduler()
    logging.getLogger(__name__).info("CreatorPulse listening intent host=%s port=%s", settings.host, settings.port)
    yield
    stop_scheduler()
    await shutdown_background_syncs()
    await release_all()
    await close_db()
    logging.getLogger(__name__).info("CreatorPulse shutdown complete")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status_code, and duration_ms for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        _request_logger.info(
            "%s %s %s %.1f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add conservative headers for a local admin UI."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        # Do not cache API payloads that may include account metadata.
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="CreatorPulse",
        description="本地优先的多平台自媒体数据聚合工具",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Rate limiting — local app, generous limits.
    limiter = FixedWindowRateLimiter(
        limit=DEFAULT_LIMIT, window_seconds=DEFAULT_WINDOW_SECONDS
    )
    app.add_exception_handler(Exception, _internal_error_handler)
    # Local-only frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5174",
            "http://localhost:5174",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=limiter,
        exempt_paths=("/docs", "/redoc", "/openapi.json", "/api/events", "/api/health"),
    )
    app.include_router(health.router)
    app.include_router(events.router)
    app.include_router(platforms.router)
    app.include_router(accounts.router)
    app.include_router(posts.router)
    app.include_router(comments.router)
    app.include_router(dashboard.router)
    app.include_router(sync_runs.router)
    app.include_router(settings_api.router)
    app.include_router(export.router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
