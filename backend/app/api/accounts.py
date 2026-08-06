"""Accounts API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.exceptions import AdapterError
from app.adapters.registry import create_adapter
from app.adapters.session_manager import get_held_adapter, hold_adapter, release_adapter
from app.api.deps import get_session, get_session_factory
from app.core.exceptions import AppError, ConflictError, to_http_exception
from app.core.security import profile_dir_for_account
from app.models.enums import AccountStatus, AuthenticationType, SyncType
from app.schemas.account import (
    AccountCreate,
    AccountPatch,
    AccountRead,
    AuthCheckResponse,
    LoginStartResponse,
    NextActionRead,
    QuickRefreshResponse,
    SyncAllItem,
    SyncAllResponse,
)
from app.schemas.sync import SyncCancelResponse, SyncStartResponse
from app.services import account_service, settings_service
from app.services.workflow import public_profile_display, recommend_next_action
from app.sync.background import (
    cancel_background_sync,
    is_background_sync_active,
    queue_background_sync,
)
from app.sync.service import is_sync_running

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _to_read(account) -> AccountRead:
    # Never expose absolute secret-laden paths beyond relative display
    display_path = public_profile_display(account.browser_profile_path)
    next_act = recommend_next_action(
        account_status=account.account_status,
        platform=account.platform,
        is_mock=bool(account.is_mock),
        has_last_sync_error=bool(account.last_sync_error),
        authentication_type=account.authentication_type,
    )
    return AccountRead(
        id=account.id,
        platform=account.platform,
        display_name=account.display_name,
        platform_user_id=account.platform_user_id,
        username=account.username,
        avatar_url=account.avatar_url,
        account_status=account.account_status,
        authentication_type=account.authentication_type,
        browser_profile_path=display_path,
        last_successful_sync_at=account.last_successful_sync_at,
        last_sync_attempt_at=account.last_sync_attempt_at,
        last_sync_error=account.last_sync_error,
        is_mock=account.is_mock,
        created_at=account.created_at,
        updated_at=account.updated_at,
        next_action=NextActionRead(
            action=next_act.action,
            label=next_act.label,
            description=next_act.description,
            requires_user_login=next_act.requires_user_login,
        ),
    )


async def _run_check_auth(db: AsyncSession, account_id: int):
    account = await account_service.get_account(db, account_id)
    settings = await settings_service.get_or_create_settings(db)
    held = get_held_adapter(account_id)
    created_temp = False
    if held is not None:
        adapter = held
    else:
        adapter = create_adapter(
            account.platform,
            use_mock=account.is_mock or settings.enable_mock_data,
            browser_profile_path=account.browser_profile_path,
            account_key=account.username or str(account.id),
            username=account.username,
        )
        created_temp = True
    try:
        result = await adapter.check_authentication()
        if result.authenticated:
            account.account_status = AccountStatus.CONNECTED.value
            if result.display_name:
                account.display_name = result.display_name
            if result.username:
                account.username = result.username
            if result.platform_user_id:
                account.platform_user_id = result.platform_user_id
            if result.avatar_url:
                account.avatar_url = result.avatar_url
            if held is not None:
                await release_adapter(account_id)
                held = None
                created_temp = False
        else:
            account.account_status = AccountStatus.LOGIN_REQUIRED.value
        return account, result
    finally:
        if created_temp:
            await adapter.close()


@router.get("", response_model=list[AccountRead])
async def list_accounts(db: AsyncSession = Depends(get_session)) -> list[AccountRead]:
    items = await account_service.list_accounts(db)
    return [_to_read(a) for a in items]


@router.post("", response_model=AccountRead)
async def create_account(
    payload: AccountCreate, db: AsyncSession = Depends(get_session)
) -> AccountRead:
    try:
        account = await account_service.create_account(db, payload)
        return _to_read(account)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: int,
    payload: AccountPatch,
    db: AsyncSession = Depends(get_session),
) -> AccountRead:
    """Update account username and/or switch X auth mode (browser vs API)."""
    account = await account_service.get_account(db, account_id)
    if payload.username is not None:
        username = payload.username.strip().lstrip("@")
        if not username:
            raise HTTPException(status_code=422, detail="用户名不能为空")
        account.username = username
    if payload.auth_mode is not None and account.platform == "x":
        if payload.auth_mode == "browser":
            account.authentication_type = AuthenticationType.BROWSER_PROFILE.value
            if not account.browser_profile_path:
                key = account.username or account.display_name or "default"
                account.browser_profile_path = str(
                    profile_dir_for_account(account.platform, key)
                )
            account.account_status = AccountStatus.LOGIN_REQUIRED.value
        else:
            account.authentication_type = AuthenticationType.API_TOKEN.value
            account.browser_profile_path = None
            account.account_status = AccountStatus.DISCONNECTED.value
    await db.commit()
    await db.refresh(account)
    return _to_read(account)


@router.post("/sync-all", response_model=SyncAllResponse)
async def sync_all_accounts(
    db: AsyncSession = Depends(get_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> SyncAllResponse:
    """Queue every idle account and return without waiting for scraping."""
    accounts = await account_service.list_accounts(db)
    await db.commit()
    items: list[SyncAllItem] = []
    started = 0
    skipped = 0
    for account in accounts:
        if account.account_status == AccountStatus.SYNCING.value:
            skipped += 1
            items.append(
                SyncAllItem(
                    account_id=account.id,
                    platform=account.platform,
                    status="skipped",
                    message="该账号正在同步，已跳过",
                )
            )
            continue
        try:
            queued = await queue_background_sync(
                session_factory,
                account.id,
                sync_type=SyncType.MANUAL,
            )
            started += 1
            items.append(
                SyncAllItem(
                    account_id=queued.account_id,
                    platform=queued.platform,
                    status=queued.status,
                    message="同步已加入后台队列",
                    sync_run_id=queued.sync_run_id,
                )
            )
        except ConflictError:
            skipped += 1
            items.append(
                SyncAllItem(
                    account_id=account.id,
                    platform=account.platform,
                    status="skipped",
                    message="该账号正在同步，已跳过",
                )
            )

    return SyncAllResponse(
        total=len(accounts),
        started=started,
        skipped=skipped,
        items=items,
    )


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: int, db: AsyncSession = Depends(get_session)
) -> AccountRead:
    try:
        account = await account_service.get_account(db, account_id)
        return _to_read(account)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    delete_profile: bool = Query(default=False),
    db: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await account_service.get_account(db, account_id)
        if is_background_sync_active(account_id) or is_sync_running(account_id):
            raise ConflictError("账号正在同步，请先取消同步再删除")
        await account_service.delete_account(db, account_id, delete_profile=delete_profile)
        return {"message": "已删除账号绑定", "delete_profile": delete_profile}
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/{account_id}/login", response_model=LoginStartResponse)
async def start_login(
    account_id: int, db: AsyncSession = Depends(get_session)
) -> LoginStartResponse:
    try:
        account = await account_service.get_account(db, account_id)
        settings = await settings_service.get_or_create_settings(db)
        # Keep browser open for manual login — do not close when API returns.
        adapter = get_held_adapter(account_id) or create_adapter(
            account.platform,
            use_mock=account.is_mock or settings.enable_mock_data,
            browser_profile_path=account.browser_profile_path,
            account_key=account.username or str(account.id),
            username=account.username,
        )
        msg = await adapter.start_login()
        if (
            account.authentication_type == AuthenticationType.BROWSER_PROFILE.value
            and not account.is_mock
        ):
            await hold_adapter(account_id, adapter)
            account.account_status = AccountStatus.LOGIN_REQUIRED.value
        else:
            # API-token platforms do not need a held browser window.
            if get_held_adapter(account_id) is None:
                await adapter.close()
        return LoginStartResponse(
            started=True,
            message=msg,
            authentication_type=(
                AuthenticationType.MOCK
                if account.is_mock
                else AuthenticationType(account.authentication_type)
            ),
            instructions=msg,
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc
    except AdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": f"浏览器操作失败: {exc.message}"},
        ) from exc


@router.post("/{account_id}/check-auth", response_model=AuthCheckResponse)
async def check_auth(
    account_id: int, db: AsyncSession = Depends(get_session)
) -> AuthCheckResponse:
    try:
        account, result = await _run_check_auth(db, account_id)
        auth_status = (
            AccountStatus.CONNECTED
            if result.authenticated
            else AccountStatus.LOGIN_REQUIRED
        )
        return AuthCheckResponse(
            authenticated=result.authenticated,
            status=auth_status,
            message=result.message,
            display_name=result.display_name or account.display_name,
            username=result.username or account.username,
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc
    except AdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": f"浏览器操作失败: {exc.message}"},
        ) from exc


@router.post("/{account_id}/refresh", response_model=QuickRefreshResponse)
async def quick_refresh(
    account_id: int,
    db: AsyncSession = Depends(get_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> QuickRefreshResponse:
    """One-click: verify login, then sync if authenticated."""
    try:
        account, result = await _run_check_auth(db, account_id)
        if not result.authenticated:
            next_act = recommend_next_action(
                account_status=AccountStatus.LOGIN_REQUIRED.value,
                platform=account.platform,
                is_mock=bool(account.is_mock),
                authentication_type=account.authentication_type,
            )
            return QuickRefreshResponse(
                account_id=account_id,
                authenticated=False,
                needs_login=True,
                message=result.message or "需要登录",
                next_action=next_act.action,
            )

        await db.commit()
        queued = await queue_background_sync(
            session_factory,
            account_id,
            sync_type=SyncType.MANUAL,
        )
        return QuickRefreshResponse(
            account_id=account_id,
            authenticated=True,
            needs_login=False,
            sync_run_id=queued.sync_run_id,
            sync_status=queued.status,
            message="已检查登录态，同步已加入后台队列",
            next_action="wait",
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc
    except AdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": f"浏览器操作失败: {exc.message}"},
        ) from exc


@router.post("/{account_id}/sync", response_model=SyncStartResponse)
async def sync_account(
    account_id: int,
    db: AsyncSession = Depends(get_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> SyncStartResponse:
    try:
        await account_service.get_account(db, account_id)
        await db.commit()
        queued = await queue_background_sync(
            session_factory,
            account_id,
            sync_type=SyncType.MANUAL,
        )
        return SyncStartResponse(
            sync_run_id=queued.sync_run_id,
            status=queued.status,
            message="同步已加入后台队列",
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/{account_id}/cancel", response_model=SyncCancelResponse)
async def cancel_sync(
    account_id: int, db: AsyncSession = Depends(get_session)
) -> SyncCancelResponse:
    """Ask an in-flight sync to stop at its next checkpoint.

    Cooperative by design: browser scraping is only interrupted between steps so
    the adapter can close its Chromium window cleanly instead of being killed.
    """
    try:
        # Validates the id so a typo returns 404 rather than a silent no-op.
        await account_service.get_account(db, account_id)
    except AppError as exc:
        raise to_http_exception(exc) from exc

    if await cancel_background_sync(account_id):
        return SyncCancelResponse(
            account_id=account_id,
            cancelling=True,
            message="已请求取消，同步将在下一个检查点停止",
        )
    return SyncCancelResponse(
        account_id=account_id,
        cancelling=False,
        message="该账号当前没有正在进行的同步",
    )
