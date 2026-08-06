from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.schemas.settings import CleanupResponse, SettingsRead, SettingsUpdate
from app.services import retention_service, settings_service
from app.services.dashboard_service import invalidate_cache
from app.services.x_credentials import save_x_bearer_token, x_token_configured
from app.sync.scheduler import start_scheduler, stop_scheduler

router = APIRouter(prefix="/api/settings", tags=["settings"])


class XCredentialsRead(BaseModel):
    configured: bool


class XCredentialsUpdate(BaseModel):
    x_bearer_token: str = Field(min_length=1, max_length=512)


def _to_read(row) -> SettingsRead:
    cfg = get_settings()
    return SettingsRead(
        enable_scheduled_sync=row.enable_scheduled_sync,
        sync_interval_minutes=row.sync_interval_minutes,
        sync_max_posts=row.sync_max_posts,
        data_retention_days=row.data_retention_days,
        dev_mode=row.dev_mode,
        enable_mock_data=row.enable_mock_data,
        data_dir_display=row.data_dir_display or str(cfg.data_dir),
        browser_profiles_dir_display=row.browser_profiles_dir_display
        or str(cfg.browser_profiles_dir),
        host=cfg.host,
        updated_at=row.updated_at,
    )


@router.get("", response_model=SettingsRead)
async def get_settings_api(db: AsyncSession = Depends(get_session)) -> SettingsRead:
    row = await settings_service.get_or_create_settings(db)
    return _to_read(row)


@router.patch("", response_model=SettingsRead)
async def patch_settings(
    payload: SettingsUpdate, db: AsyncSession = Depends(get_session)
) -> SettingsRead:
    row = await settings_service.update_settings(db, payload)
    # Mock-mode and sync flags change what the dashboard reports; the cached
    # summary must not keep serving pre-change numbers for up to 60 s.
    await invalidate_cache()
    # restart scheduler interval if needed
    if payload.enable_scheduled_sync is not None or payload.sync_interval_minutes is not None:
        stop_scheduler()
        start_scheduler()
    return _to_read(row)


@router.post("/cleanup", response_model=CleanupResponse)
async def run_cleanup(db: AsyncSession = Depends(get_session)) -> CleanupResponse:
    """Apply the configured retention policy now instead of waiting for the daily job.

    Unhandled comments (`new` / `pending`) are always preserved regardless of age.
    """
    row = await settings_service.get_or_create_settings(db)
    report = await retention_service.cleanup_expired_data(db, row.data_retention_days)
    return CleanupResponse(
        retention_days=report.retention_days,
        cutoff=report.cutoff,
        posts_deleted=report.posts_deleted,
        comments_deleted=report.comments_deleted,
        snapshots_deleted=report.snapshots_deleted,
        sync_runs_deleted=report.sync_runs_deleted,
        total_deleted=report.total_deleted,
        message=(
            f"已清理 {report.total_deleted} 条超过 {report.retention_days} 天的数据"
            if report.total_deleted
            else "没有需要清理的数据"
        ),
    )


@router.get("/x-credentials", response_model=XCredentialsRead)
async def get_x_credentials() -> XCredentialsRead:
    """Report whether an X Bearer Token is configured (never the token itself)."""
    return XCredentialsRead(configured=x_token_configured())


@router.put("/x-credentials", response_model=XCredentialsRead)
async def put_x_credentials(payload: XCredentialsUpdate) -> XCredentialsRead:
    """Persist a new X Bearer Token for immediate use.

    The token is written to the app-owned ``backend/.env.x`` and takes effect
    on the next adapter creation; it is never echoed back in responses.
    """
    save_x_bearer_token(payload.x_bearer_token)
    return XCredentialsRead(configured=True)
