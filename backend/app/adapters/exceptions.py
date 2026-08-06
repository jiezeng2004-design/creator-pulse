"""Platform adapter exceptions — mapped by sync service, never crash the app."""


class AdapterError(Exception):
    code: str = "adapter_error"

    def __init__(self, message: str, *, diagnostic: dict | None = None) -> None:
        self.message = message
        self.diagnostic = diagnostic or {}
        super().__init__(message)


class AuthenticationRequiredError(AdapterError):
    code = "authentication_required"


class PermissionDeniedError(AdapterError):
    code = "permission_denied"


class RateLimitError(AdapterError):
    code = "rate_limited"

    def __init__(
        self,
        message: str,
        *,
        reset_at: str | None = None,
        remaining: int | None = None,
        diagnostic: dict | None = None,
    ) -> None:
        diag = diagnostic or {}
        if reset_at:
            diag["rate_limit_reset_at"] = reset_at
        if remaining is not None:
            diag["rate_limit_remaining"] = remaining
        super().__init__(message, diagnostic=diag)
        self.reset_at = reset_at
        self.remaining = remaining


class SelectorChangedError(AdapterError):
    code = "selector_changed"


class NetworkError(AdapterError):
    code = "network_error"


class UnsupportedFeatureError(AdapterError):
    code = "unsupported_feature"


class PlatformTemporaryError(AdapterError):
    code = "platform_temporary"
