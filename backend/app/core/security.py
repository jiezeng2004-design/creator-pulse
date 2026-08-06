"""Path sandboxing and local security helpers."""

from __future__ import annotations

from pathlib import Path

from app.core.config import PROJECT_ROOT, get_settings


class PathSecurityError(ValueError):
    """Raised when a path escapes allowed project directories."""


def resolve_under(base: Path, relative: str | Path) -> Path:
    """Resolve a path and ensure it stays under `base`."""
    base_resolved = base.resolve()
    candidate = (base_resolved / relative).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise PathSecurityError(
            f"Path escapes allowed directory: {candidate} not under {base_resolved}"
        ) from exc
    return candidate


def safe_data_path(relative: str | Path) -> Path:
    settings = get_settings()
    return resolve_under(settings.data_dir, relative)


def safe_browser_profile_path(relative: str | Path) -> Path:
    settings = get_settings()
    return resolve_under(settings.browser_profiles_dir, relative)


def is_under_project(path: Path) -> bool:
    try:
        path.resolve().relative_to(PROJECT_ROOT.resolve())
        return True
    except ValueError:
        return False


def profile_dir_for_account(platform: str, account_key: str) -> Path:
    """Build a browser profile directory for an account within the sandbox."""
    safe_platform = "".join(c if c.isalnum() or c in "-_" else "_" for c in platform)
    safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in account_key)[:64]
    relative = f"{safe_platform}/{safe_key}"
    path = safe_browser_profile_path(relative)
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = [
    "PathSecurityError",
    "resolve_under",
    "safe_data_path",
    "safe_browser_profile_path",
    "is_under_project",
    "profile_dir_for_account",
]
