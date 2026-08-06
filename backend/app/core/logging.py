"""Logging configuration with automatic secret filtering."""

from __future__ import annotations

import logging
import logging.handlers
import re
from typing import Any

from app.core.config import PROJECT_ROOT

SECRET_PATTERNS: list[re.Pattern[str]] = [
    # Authorization: Bearer <token> or Authorization: <scheme> <token>
    re.compile(r"(?i)(authorization\s*[=:]\s*)(\S+(?:\s+\S+)?)"),
    re.compile(r"(?i)(cookie\s*[=:]\s*)([^\s,;\"']+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9\-._~+/]+=*)"),
    re.compile(r"(?i)(access_token\s*[=:]\s*)([^\s,;\"']+)"),
    re.compile(r"(?i)(refresh_token\s*[=:]\s*)([^\s,;\"']+)"),
    re.compile(r"(?i)(session\s*[=:]\s*)([^\s,;\"']+)"),
    re.compile(r"(?i)(x_bearer_token\s*[=:]\s*)([^\s,;\"']+)"),
    re.compile(r"(?i)(client_secret\s*[=:]\s*)([^\s,;\"']+)"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([^\s,;\"']+)"),
    re.compile(r"(?i)(x-api-key\s*[=:]\s*)([^\s,;\"']+)"),
    # JSON-style "access_token":"..."
    re.compile(r'(?i)("(?:access_token|refresh_token|client_secret|password)"\s*:\s*")([^"]+)(")'),
]


def redact_secrets(message: str) -> str:
    """Replace secret values in a log message with [REDACTED]."""
    redacted = message
    for pattern in SECRET_PATTERNS:
        # Patterns may have 2 or 3 groups (JSON quotes keep trailing quote).
        def _sub(m: re.Match[str], _p: re.Pattern[str] = pattern) -> str:
            if m.lastindex and m.lastindex >= 3:
                return f"{m.group(1)}[REDACTED]{m.group(3)}"
            return f"{m.group(1)}[REDACTED]"

        redacted = pattern.sub(_sub, redacted)
    return redacted


class SecretFilter(logging.Filter):
    """Filter that redacts secrets from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_secrets(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_secrets(a) if isinstance(a, str) else a for a in record.args
                )
        return True


def sanitize_diagnostic(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove sensitive keys from diagnostic payloads before persistence."""
    if data is None:
        return None
    blocked_keys = {
        "cookie",
        "cookies",
        "authorization",
        "bearer",
        "access_token",
        "refresh_token",
        "session",
        "token",
        "password",
        "secret",
        "html",
        "page_html",
        "headers",
        "request_headers",
        "set-cookie",
        "api_key",
        "apikey",
        "client_secret",
        "z_c0",
        "profile_path_absolute",
    }
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        lower = key.lower()
        if any(b in lower for b in blocked_keys):
            cleaned[key] = "[REDACTED]"
            continue
        if isinstance(value, str):
            cleaned[key] = redact_secrets(value)
            if len(cleaned[key]) > 2000:
                cleaned[key] = cleaned[key][:2000] + "...[truncated]"
        elif isinstance(value, dict):
            cleaned[key] = sanitize_diagnostic(value)
        else:
            cleaned[key] = value
    return cleaned


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if not root.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SecretFilter())
        root.addHandler(console_handler)

        # File handler with rotation (10 MB max, 3 backups)
        log_file = PROJECT_ROOT / "data" / "creatorpulse.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SecretFilter())
        root.addHandler(file_handler)
    else:
        for handler in root.handlers:
            handler.addFilter(SecretFilter())

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


__all__ = [
    "redact_secrets",
    "SecretFilter",
    "sanitize_diagnostic",
    "setup_logging",
]
