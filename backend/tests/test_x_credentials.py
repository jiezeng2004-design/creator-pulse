"""Web-managed X Bearer Token configuration tests."""

from __future__ import annotations

from app.core.config import Settings
from app.services import x_credentials


async def test_put_x_credentials_saves_token_without_echo(client, monkeypatch, tmp_path):
    """Saving a token persists it locally and never returns it in the response."""
    cred_file = tmp_path / ".env.x"
    monkeypatch.setattr(x_credentials, "CREDENTIALS_FILE", cred_file)

    token = "super-secret-bearer-123"
    response = await client.put(
        "/api/settings/x-credentials",
        json={"x_bearer_token": token},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"configured": True}
    assert token not in response.text, "token must never be echoed back"

    content = cred_file.read_text(encoding="utf-8")
    assert f"X_BEARER_TOKEN={token}" in content


async def test_x_credentials_status_reflects_config(monkeypatch):
    """configured is True only when a non-empty token is available."""
    monkeypatch.setattr(
        x_credentials, "get_settings", lambda: Settings(x_bearer_token="")
    )
    assert x_credentials.x_token_configured() is False

    monkeypatch.setattr(
        x_credentials, "get_settings", lambda: Settings(x_bearer_token="abc")
    )
    assert x_credentials.x_token_configured() is True


async def test_get_x_credentials_endpoint(client):
    """The status endpoint returns the configured flag without a token."""
    response = await client.get("/api/settings/x-credentials")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"configured"}
    assert isinstance(body["configured"], bool)


def test_settings_env_file_precedence(tmp_path):
    """The app-managed credentials file overrides the hand-edited .env."""
    env_file = tmp_path / "env"
    env_file.write_text("X_BEARER_TOKEN=from_env\n", encoding="utf-8")
    cred_file = tmp_path / "env.x"
    cred_file.write_text("X_BEARER_TOKEN=from_credentials\n", encoding="utf-8")

    # pyright does not model pydantic-settings' runtime-only _env_file kwarg.
    settings = Settings(_env_file=(str(env_file), str(cred_file)))  # pyright: ignore[reportCallIssue]
    assert settings.x_bearer_token == "from_credentials"
