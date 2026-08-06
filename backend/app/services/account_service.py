"""Account CRUD and lifecycle."""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.security import profile_dir_for_account
from app.models.account import PlatformAccount
from app.models.enums import AccountStatus, AuthenticationType, Platform
from app.schemas.account import AccountCreate


async def list_accounts(db: AsyncSession) -> list[PlatformAccount]:
    result = await db.execute(select(PlatformAccount).order_by(PlatformAccount.id.desc()))
    return list(result.scalars().all())


async def get_account(db: AsyncSession, account_id: int) -> PlatformAccount:
    account = await db.get(PlatformAccount, account_id)
    if not account:
        raise NotFoundError(f"账号 {account_id} 不存在")
    return account


async def create_account(db: AsyncSession, payload: AccountCreate) -> PlatformAccount:
    # payload.platform is already validated by Pydantic to be a Platform enum member
    use_mock = payload.use_mock
    if use_mock:
        auth_type = AuthenticationType.MOCK.value
        profile_path = None
        status = AccountStatus.CONNECTED.value
        is_mock = True
        display = payload.display_name or f"{payload.platform} 演示账号"
        platform_user_id = f"mock-{payload.platform}-{payload.username or 'demo'}"
    elif payload.platform == Platform.X:
        if payload.use_browser:
            # Free browser-login mode: same persistent profile flow as the
            # domestic platforms. Username is optional; it is derived after
            # the user logs in.
            key = payload.username or payload.display_name or "default"
            path = profile_dir_for_account(payload.platform.value, key)
            auth_type = AuthenticationType.BROWSER_PROFILE.value
            profile_path = str(path)
            status = AccountStatus.LOGIN_REQUIRED.value
            is_mock = False
            display = payload.display_name or "X 账号"
            platform_user_id = f"x-browser-{key}"
        else:
            if not payload.username:
                raise ValidationAppError("X 账号需要填写 X 用户名（不含 @）")
            auth_type = AuthenticationType.API_TOKEN.value
            profile_path = None
            status = AccountStatus.DISCONNECTED.value
            is_mock = False
            display = payload.display_name or "X 账号"
            platform_user_id = payload.username or f"x-pending-{payload.display_name or 'new'}"
    else:
        auth_type = AuthenticationType.BROWSER_PROFILE.value
        key = payload.username or payload.display_name or "default"
        path = profile_dir_for_account(payload.platform.value, key)
        profile_path = str(path)
        status = AccountStatus.LOGIN_REQUIRED.value
        is_mock = False
        display = payload.display_name or f"{payload.platform.value} 账号"
        platform_user_id = f"{payload.platform.value}-{key}"

    account = PlatformAccount(
        platform=payload.platform.value,
        display_name=display,
        platform_user_id=platform_user_id,
        username=payload.username,
        account_status=status,
        authentication_type=auth_type,
        browser_profile_path=profile_path,
        is_mock=is_mock,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


async def delete_account(
    db: AsyncSession, account_id: int, *, delete_profile: bool = False
) -> None:
    account = await get_account(db, account_id)
    profile = account.browser_profile_path
    await db.delete(account)
    await db.flush()
    from app.sync.service import cleanup_sync_state

    cleanup_sync_state(account_id)
    if delete_profile and profile:
        path = Path(profile)
        # only delete if under project browser-profiles (validated on create)
        from app.core.security import is_under_project

        if is_under_project(path) and path.exists():
            shutil.rmtree(path, ignore_errors=True)
