"""Account request/response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import AccountStatus, AuthenticationType, Platform
from app.schemas.common import ORMModel


class NextActionRead(BaseModel):
    action: str
    label: str
    description: str
    requires_user_login: bool = False


class AccountCreate(BaseModel):
    platform: Platform
    display_name: str = Field(default="", max_length=255)
    username: str | None = Field(default=None, max_length=255)
    use_mock: bool = False
    # X only: use the free browser-login mode instead of the paid API.
    use_browser: bool = False


class AccountRead(ORMModel):
    id: int
    platform: str
    display_name: str
    platform_user_id: str | None
    username: str | None
    avatar_url: str | None
    account_status: str
    authentication_type: str
    browser_profile_path: str | None = None  # relative / display only (never full secrets path)
    last_successful_sync_at: datetime | None
    last_sync_attempt_at: datetime | None
    last_sync_error: str | None
    is_mock: bool
    created_at: datetime
    updated_at: datetime
    next_action: NextActionRead | None = None


class AccountDeleteParams(BaseModel):
    delete_profile: bool = False


class AccountPatch(BaseModel):
    """Optional fields that can be updated on an existing account."""

    username: str | None = Field(default=None, max_length=255)
    # X only: switch between the free browser-login mode and the API-token mode.
    auth_mode: Literal["browser", "api"] | None = None


class AuthCheckResponse(BaseModel):
    authenticated: bool
    status: AccountStatus
    message: str
    display_name: str | None = None
    username: str | None = None


class LoginStartResponse(BaseModel):
    started: bool
    message: str
    authentication_type: AuthenticationType
    instructions: str | None = None


class QuickRefreshResponse(BaseModel):
    """One-click: check auth then sync when possible."""

    account_id: int
    authenticated: bool
    needs_login: bool
    sync_run_id: int | None = None
    sync_status: str | None = None
    message: str
    next_action: str | None = None


class SyncAllItem(BaseModel):
    account_id: int
    platform: str
    status: str
    message: str
    sync_run_id: int | None = None


class SyncAllResponse(BaseModel):
    total: int
    started: int
    skipped: int
    items: list[SyncAllItem]
