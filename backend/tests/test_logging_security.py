from pathlib import Path

import pytest

from app.core.config import get_settings
from app.core.logging import redact_secrets, sanitize_diagnostic
from app.core.security import PathSecurityError, resolve_under


def test_redact_bearer_token():
    msg = "Authorization: Bearer abc.def.ghi secret"
    out = redact_secrets(msg)
    assert "abc.def.ghi" not in out
    assert "[REDACTED]" in out


def test_redact_cookie():
    msg = "cookie=sessionid12345; path=/"
    out = redact_secrets(msg)
    assert "sessionid12345" not in out


def test_redact_json_access_token():
    msg = '{"access_token":"super-secret-token-value","ok":true}'
    out = redact_secrets(msg)
    assert "super-secret-token-value" not in out
    assert "[REDACTED]" in out


def test_redact_api_key():
    msg = "x-api-key=sk_live_abc123xyz"
    out = redact_secrets(msg)
    assert "sk_live_abc123xyz" not in out


def test_sanitize_diagnostic():
    data = {
        "cookie": "secret",
        "status": 429,
        "nested": {"access_token": "tok", "ok": True},
        "note": "Authorization: Bearer xyz",
        "client_secret": "shh",
    }
    cleaned = sanitize_diagnostic(data)
    assert cleaned is not None
    assert cleaned["cookie"] == "[REDACTED]"
    assert cleaned["status"] == 429
    assert cleaned["nested"]["access_token"] == "[REDACTED]"
    assert "xyz" not in cleaned["note"]
    assert cleaned["client_secret"] == "[REDACTED]"


def test_path_sandbox_blocks_escape(tmp_path: Path):
    base = tmp_path / "data"
    base.mkdir()
    with pytest.raises(PathSecurityError):
        resolve_under(base, Path("..") / "etc" / "passwd")


def test_browser_profile_under_project():
    settings = get_settings()
    settings.ensure_directories()
    # relative safe path should work via profile helper
    from app.core.security import profile_dir_for_account

    p = profile_dir_for_account("zhihu", "testuser")
    assert p.exists()
    assert "zhihu" in str(p)


def test_host_forced_to_localhost():
    from app.core.config import Settings

    s = Settings(host="0.0.0.0")  # type: ignore[arg-type]
    assert s.host == "127.0.0.1"
    s2 = Settings(host="127.0.0.1")
    assert s2.host == "127.0.0.1"


def test_relative_config_paths_resolve_from_backend_directory():
    from app.core.config import BACKEND_DIR, Settings

    settings = Settings(
        data_dir=Path("../data"),
        browser_profiles_dir=Path("../browser-profiles"),
        database_url="sqlite+aiosqlite:///../data/creator_pulse.db",
    )

    assert settings.data_dir == (BACKEND_DIR / "../data").resolve()
    assert settings.browser_profiles_dir == (BACKEND_DIR / "../browser-profiles").resolve()
    expected_database = (BACKEND_DIR / "../data/creator_pulse.db").resolve().as_posix()
    assert settings.database_url == f"sqlite+aiosqlite:///{expected_database}"
