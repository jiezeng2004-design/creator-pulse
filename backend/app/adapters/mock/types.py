"""Mock scenario types for demo mode adapters."""

from enum import Enum


class MockScenario(str, Enum):  # noqa: UP042 — StrEnum causes MRO error on Python 3.12
    """Available mock data scenarios."""

    NORMAL = "normal"
    EMPTY = "empty"
    RATE_LIMIT = "rate_limit"
    AUTH_REQUIRED = "auth_required"
    SELECTOR = "selector"
    DUPLICATE = "duplicate"
    PARTIAL_METRICS = "partial_metrics"
    NETWORK = "network"
