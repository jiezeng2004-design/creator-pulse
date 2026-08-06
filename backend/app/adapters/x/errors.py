"""Map tweepy errors to CreatorPulse adapter errors."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import tweepy

from app.adapters.exceptions import (
    AuthenticationRequiredError,
    NetworkError,
    PermissionDeniedError,
    PlatformTemporaryError,
    RateLimitError,
)


def _message_from(exc: tweepy.HTTPException) -> str:
    """Pick the most useful message from a tweepy HTTP error."""
    if exc.api_messages:
        return "; ".join(str(m) for m in exc.api_messages if m)[:300]
    return exc.response.reason or "X API 请求失败"


def _status_code(response: Any) -> int | None:
    """Read the HTTP status from either a requests or aiohttp response."""
    code = getattr(response, "status_code", None)
    if code is None:
        code = getattr(response, "status", None)
    return code


def map_tweepy_error(exc: BaseException, *, context: str) -> Exception:
    """Convert a tweepy/aiohttp exception into a CreatorPulse AdapterError.

    ``context`` is a short label (e.g. ``fetch_posts``) used for diagnostics.
    """
    if isinstance(exc, tweepy.Unauthorized):
        return AuthenticationRequiredError(
            "X API Token 无效或已过期",
            diagnostic={"context": context, "status_code": 401},
        )
    if isinstance(exc, tweepy.Forbidden):
        detail = _message_from(exc)
        return PermissionDeniedError(
            f"X API 权限不足：{detail}",
            diagnostic={"context": context, "status_code": 403},
        )
    if isinstance(exc, tweepy.TooManyRequests):
        reset_at = None
        if exc.reset_time:
            try:
                reset_at = datetime.fromtimestamp(exc.reset_time, tz=UTC).isoformat()
            except (OverflowError, OSError, ValueError):
                reset_at = None
        return RateLimitError(
            "X API 触发限流",
            reset_at=reset_at,
            diagnostic={"context": context, "status_code": 429},
        )
    if isinstance(exc, tweepy.BadRequest):
        return PlatformTemporaryError(
            f"X API 请求无效：{_message_from(exc)}",
            diagnostic={"context": context, "status_code": 400},
        )
    if isinstance(exc, tweepy.TwitterServerError):
        return PlatformTemporaryError(
            f"X API 服务暂时不可用 ({_status_code(exc.response)})",
            diagnostic={"context": context, "status_code": _status_code(exc.response)},
        )
    if isinstance(exc, tweepy.HTTPException) and _status_code(exc.response) == 402:
        return PlatformTemporaryError(
            "X API 额度不足（credits depleted）。所有 X API v2 读取（含查用户、查推文）都消耗"
            "月度 read credits。请到 X Developer Portal 查看用量/订阅，或等待免费额度月度重置。",
            diagnostic={"context": context, "status_code": 402},
        )
    if isinstance(exc, tweepy.HTTPException):
        return PlatformTemporaryError(
            f"X API 请求失败 ({_status_code(exc.response)})",
            diagnostic={"context": context, "status_code": _status_code(exc.response)},
        )
    if isinstance(exc, TimeoutError):
        return NetworkError("X API 请求超时", diagnostic={"context": context})
    # aiohttp.ClientError / generic transport failures
    # Include the original message (truncated) — for transport errors like
    # proxy misuse or response deserialization, the class name alone is not
    # enough to diagnose the failure.
    detail = str(exc).strip()
    suffix = f": {detail[:200]}" if detail else ""
    return NetworkError(
        f"X API 网络错误: {exc.__class__.__name__}{suffix}",
        diagnostic={"context": context, "error": detail[:300]},
    )


__all__ = ["map_tweepy_error"]
