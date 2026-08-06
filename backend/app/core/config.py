"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ is the package root for relative paths in .env.example
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # App-written credentials live in .env.x (gitignored) and take
        # precedence over the hand-edited .env so the web UI can manage the
        # X Bearer Token without rewriting the user's file.
        env_file=(
            str(BACKEND_DIR / ".env"),
            str(BACKEND_DIR / ".env.x"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8001
    debug: bool = False

    data_dir: Path = Field(default=PROJECT_ROOT / "data")
    browser_profiles_dir: Path = Field(default=PROJECT_ROOT / "browser-profiles")
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'data' / 'creator_pulse.db').as_posix()}"
    )

    x_bearer_token: str = ""
    x_client_id: str = ""
    x_client_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""
    # Optional HTTP(S) proxy for X API requests only (e.g. http://127.0.0.1:8080).
    # Kept process-scoped: never written to system or Git proxy settings.
    x_proxy: str = ""

    enable_mock_data: bool = False
    dev_mode: bool = False
    enable_scheduled_sync: bool = False
    sync_interval_minutes: int = 60
    sync_max_posts: int = 50
    data_retention_days: int = 365

    log_level: str = "INFO"

    @model_validator(mode="after")
    def resolve_project_paths(self) -> "Settings":
        """Make .env paths independent from the process working directory.

        Relative values in ``backend/.env`` are documented relative to the
        backend directory. Resolving them here keeps scripts, tests, and direct
        module launches pointed at the same project-local data.
        """
        if not self.data_dir.is_absolute():
            self.data_dir = (BACKEND_DIR / self.data_dir).resolve()
        if not self.browser_profiles_dir.is_absolute():
            self.browser_profiles_dir = (BACKEND_DIR / self.browser_profiles_dir).resolve()

        sqlite_prefix = "sqlite+aiosqlite:///"
        if self.database_url.startswith(sqlite_prefix):
            database_path = self.database_url[len(sqlite_prefix) :]
            if database_path != ":memory:" and not Path(database_path).is_absolute():
                resolved = (BACKEND_DIR / database_path).resolve().as_posix()
                self.database_url = f"{sqlite_prefix}{resolved}"
        return self

    @field_validator("host")
    @classmethod
    def host_must_be_local(cls, v: str) -> str:
        allowed = {"127.0.0.1", "localhost", "::1"}
        if v not in allowed:
            # Force localhost for security; do not bind public interfaces in v1.
            return "127.0.0.1"
        return v

    @field_validator("sync_interval_minutes")
    @classmethod
    def min_sync_interval(cls, v: int) -> int:
        return max(v, 30)

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.browser_profiles_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


__all__ = ["Settings", "get_settings", "PROJECT_ROOT"]
