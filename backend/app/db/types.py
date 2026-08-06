"""SQLAlchemy column types shared across models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Store naive UTC in the database, return tz-aware UTC on read.

    SQLite cannot persist timezone offsets, so ``DateTime(timezone=True)``
    silently drops them: a tz-aware value written by ``datetime.now(UTC)``
    comes back naive, and Pydantic then serializes it without an offset.
    Browsers parse such strings as local time, shifting every timestamp by
    the machine's UTC offset (8 hours for Asia/Shanghai).

    This type makes the UTC contract explicit on both sides of the boundary:
    naive values written are treated as UTC, and values read back are always
    re-attached to the UTC timezone so the API emits ``+00:00``.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        # SQLite stores a naive string; keep the stored format identical to
        # legacy rows so existing databases stay readable.
        return value.replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value
