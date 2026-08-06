"""Tests for convenience workflow helpers — real shipped functions."""

from app.services.workflow import public_profile_display, recommend_next_action


def test_recommend_mock_is_sync():
    act = recommend_next_action(
        account_status="connected",
        platform="zhihu",
        is_mock=True,
    )
    assert act.action == "sync"
    assert "演示" in act.label or "同步" in act.label


def test_recommend_login_required_domestic():
    act = recommend_next_action(
        account_status="login_required",
        platform="zhihu",
        is_mock=False,
    )
    assert act.action == "login"
    assert act.requires_user_login is True


def test_recommend_x_disconnected_is_check_auth():
    act = recommend_next_action(
        account_status="disconnected",
        platform="x",
        is_mock=False,
    )
    assert act.action == "check_auth"
    assert "Token" in act.description or "token" in act.description.lower() or "X" in act.description


def test_recommend_connected_is_refresh():
    act = recommend_next_action(
        account_status="connected",
        platform="zhihu",
        is_mock=False,
    )
    assert act.action == "refresh"
    assert "同步" in act.label


def test_recommend_error_prefers_refresh():
    act = recommend_next_action(
        account_status="error",
        platform="toutiao",
        is_mock=False,
        has_last_sync_error=True,
    )
    assert act.action == "refresh"


def test_public_profile_display_truncates_absolute_paths():
    path = r"C:\workspace\browser-profiles\zhihu\demo-profile"
    shown = public_profile_display(path)
    assert shown is not None
    assert "C:" not in shown
    assert "workspace" not in shown
    assert shown.endswith("zhihu/demo-profile") or shown == "zhihu/demo-profile"
    assert public_profile_display(None) is None
    assert public_profile_display("") is None
