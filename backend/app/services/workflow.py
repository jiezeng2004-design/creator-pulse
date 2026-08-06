"""Convenience workflow helpers (pure logic + orchestration)."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import AccountStatus, AuthenticationType


@dataclass(frozen=True)
class NextAction:
    """Recommended single primary action for an account card."""

    action: str
    label: str
    description: str
    requires_user_login: bool = False


def recommend_next_action(
    *,
    account_status: str,
    platform: str,
    is_mock: bool,
    has_last_sync_error: bool = False,
    authentication_type: str | None = None,
) -> NextAction:
    """
    Map account state to one primary CTA to reduce multi-step guessing.

    Security: never recommends exposing tokens or deleting profiles.
    """
    if is_mock:
        return NextAction(
            action="sync",
            label="同步演示数据",
            description="演示账号可直接同步示例内容与评论",
        )

    status = (account_status or "").lower()
    if status in {AccountStatus.LOGIN_REQUIRED.value, AccountStatus.DISCONNECTED.value}:
        if platform == "x":
            if authentication_type == AuthenticationType.BROWSER_PROFILE.value:
                return NextAction(
                    action="login",
                    label="打开登录",
                    description="在本机浏览器中手动登录 x.com，完成后点「检查并同步」（免 API 额度）",
                    requires_user_login=True,
                )
            return NextAction(
                action="check_auth",
                label="检查 Token",
                description="请先在设置页「X API 配置」填写 Bearer Token，然后检查连接",
            )
        return NextAction(
            action="login",
            label="打开登录",
            description="在本机浏览器中手动登录，完成后点「检查并同步」",
            requires_user_login=True,
        )

    if status == AccountStatus.SYNCING.value:
        return NextAction(
            action="wait",
            label="同步中…",
            description="请稍候，同一账号不会并发二次同步",
        )

    if status == AccountStatus.RATE_LIMITED.value:
        return NextAction(
            action="sync",
            label="稍后重试同步",
            description="平台限流中，请稍后再试",
        )

    if status == AccountStatus.ERROR.value or has_last_sync_error:
        return NextAction(
            action="refresh",
            label="检查并同步",
            description="先校验登录态，成功后自动拉取最新数据",
        )

    # connected / default
    return NextAction(
        action="refresh",
        label="一键同步",
        description="检查登录态并同步最新内容与评论",
    )


def public_profile_display(path: str | None) -> str | None:
    """Expose only the last two path segments — never full absolute paths."""
    if not path:
        return None
    normalized = path.replace("\\", "/").strip("/")
    parts = [p for p in normalized.split("/") if p]
    if not parts:
        return None
    if len(parts) <= 2:
        return "/".join(parts)
    return "/".join(parts[-2:])
