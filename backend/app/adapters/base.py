"""Abstract platform adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.adapters.types import (
    AccountProfile,
    AuthenticationResult,
    PlatformComment,
    PlatformPost,
    PlatformPostMetrics,
)


class PlatformAdapter(ABC):
    """Adapters return standardized data only — never write to DB or UI."""

    platform: str
    experimental: bool = False

    @abstractmethod
    async def check_authentication(self) -> AuthenticationResult: ...

    @abstractmethod
    async def fetch_account_profile(self) -> AccountProfile: ...

    @abstractmethod
    async def fetch_posts(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[PlatformPost]: ...

    @abstractmethod
    async def fetch_post_metrics(
        self,
        post_ids: list[str],
    ) -> list[PlatformPostMetrics]: ...

    @abstractmethod
    async def fetch_comments(
        self,
        post_id: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformComment]: ...

    async def start_login(self) -> str:
        """Open login UI if needed. Returns user-facing instructions."""
        return "此平台无需浏览器登录，或请使用设置中的 API Token。"

    async def close(self) -> None:
        return None
