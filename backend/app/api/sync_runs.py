import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.logging import sanitize_diagnostic
from app.models.account import PlatformAccount
from app.models.sync_run import SyncRun
from app.schemas.common import Page
from app.schemas.sync import SyncRunRead

router = APIRouter(prefix="/api/sync-runs", tags=["sync-runs"])


@router.get("", response_model=Page[SyncRunRead])
async def list_sync_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    account_id: int | None = None,
    platform: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> Page[SyncRunRead]:
    q = select(SyncRun, PlatformAccount).join(
        PlatformAccount, SyncRun.account_id == PlatformAccount.id
    )
    count_q = select(func.count(SyncRun.id)).select_from(SyncRun)
    if account_id:
        q = q.where(SyncRun.account_id == account_id)
        count_q = count_q.where(SyncRun.account_id == account_id)
    if platform:
        q = q.where(SyncRun.platform == platform)
        count_q = count_q.where(SyncRun.platform == platform)
    q = q.order_by(SyncRun.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(q)).all()
    items: list[SyncRunRead] = []
    for run, account in rows:
        diag = None
        if run.diagnostic_json:
            try:
                diag = sanitize_diagnostic(json.loads(run.diagnostic_json))
            except json.JSONDecodeError:
                diag = {"raw": "[invalid diagnostic json]"}
        items.append(
            SyncRunRead(
                id=run.id,
                account_id=run.account_id,
                platform=run.platform,
                account_display_name=account.display_name,
                sync_type=run.sync_type,
                status=run.status,
                phase=run.phase,
                started_at=run.started_at,
                finished_at=run.finished_at,
                posts_fetched=run.posts_fetched,
                comments_fetched=run.comments_fetched,
                error_code=run.error_code,
                error_message=run.error_message,
                diagnostic=diag,
            )
        )
    return Page(page=page, page_size=page_size, total=int(total), items=items)
