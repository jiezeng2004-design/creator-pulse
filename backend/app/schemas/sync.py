"""Sync run schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class SyncRunRead(ORMModel):
    id: int
    account_id: int
    platform: str
    account_display_name: str | None = None
    sync_type: str
    status: str
    phase: str | None = None
    started_at: datetime
    finished_at: datetime | None
    posts_fetched: int
    comments_fetched: int
    error_code: str | None
    error_message: str | None
    diagnostic: dict[str, Any] | None = None


class SyncStartResponse(BaseModel):
    sync_run_id: int
    status: str
    message: str


class SyncCancelResponse(BaseModel):
    """Result of asking an in-flight sync to stop."""

    account_id: int
    cancelling: bool
    message: str
