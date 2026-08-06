"""Web-managed X API credentials.

The X Bearer Token can be configured from the settings page. Writing it into
``backend/.env`` would rewrite a user-edited file, so the app owns a separate
``backend/.env.x`` (gitignored) that overrides ``.env`` at load time. Tokens are
never returned to the browser; the API only reports whether one is configured.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings

CREDENTIALS_FILE = BACKEND_DIR / ".env.x"


def x_token_configured() -> bool:
    """True when a non-empty X Bearer Token is available to the app."""
    return bool((get_settings().x_bearer_token or "").strip())


def save_x_bearer_token(token: str) -> None:
    """Persist the token to the app-owned credentials file.

    The file keeps a leading comment so a future manual edit stays safe, and
    only the token line is written. Permissions are tightened when the platform
    supports it (POSIX); on Windows the file relies on project-local access.
    """
    token = token.strip()
    if not token:
        raise ValueError("X Bearer Token 不能为空")
    CREDENTIALS_FILE.write_text(
        f"# App-managed X credentials (written by CreatorPulse settings UI)\n"
        f"X_BEARER_TOKEN={token}\n",
        encoding="utf-8",
    )
    try:
        CREDENTIALS_FILE.chmod(0o600)
    except OSError:
        pass  # Windows: chmod is a no-op / unsupported; ignore


def credentials_file_path() -> Path:
    return CREDENTIALS_FILE
