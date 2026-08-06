from app.adapters.exceptions import (
    AuthenticationRequiredError,
    NetworkError,
    PermissionDeniedError,
    RateLimitError,
    SelectorChangedError,
    UnsupportedFeatureError,
)


def test_exception_codes():
    assert AuthenticationRequiredError("x").code == "authentication_required"
    assert PermissionDeniedError("x").code == "permission_denied"
    assert RateLimitError("x", reset_at="123").code == "rate_limited"
    assert RateLimitError("x", reset_at="123").diagnostic["rate_limit_reset_at"] == "123"
    assert SelectorChangedError("x").code == "selector_changed"
    assert NetworkError("x").code == "network_error"
    assert UnsupportedFeatureError("x").code == "unsupported_feature"
