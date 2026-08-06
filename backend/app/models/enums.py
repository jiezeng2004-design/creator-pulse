"""Shared enumerations for domain models."""

from enum import StrEnum


class Platform(StrEnum):
    X = "x"
    XIAOHONGSHU = "xiaohongshu"
    ZHIHU = "zhihu"
    TOUTIAO = "toutiao"


class AccountStatus(StrEnum):
    DISCONNECTED = "disconnected"
    LOGIN_REQUIRED = "login_required"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class AuthenticationType(StrEnum):
    API_TOKEN = "api_token"
    BROWSER_PROFILE = "browser_profile"
    MOCK = "mock"


class CommentLocalStatus(StrEnum):
    NEW = "new"
    PENDING = "pending"
    HANDLED = "handled"
    IGNORED = "ignored"


class SyncStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncType(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    LOGIN_CHECK = "login_check"
