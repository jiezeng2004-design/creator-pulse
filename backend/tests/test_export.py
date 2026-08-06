"""Tests for the database export API endpoint."""

import io
import sqlite3
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_export_database_success():
    """Export should return a ZIP file when DB exists."""
    from app.main import create_app

    app = create_app()
    client = TestClient(app)

    response = client.post("/api/settings/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    content_disposition = response.headers.get("content-disposition", "")
    assert "creator_pulse_backup_" in content_disposition
    assert ".zip" in content_disposition


@pytest.mark.asyncio
async def test_export_content_is_valid_zip():
    """Exported ZIP should be a valid zip archive."""
    from app.main import create_app

    app = create_app()
    client = TestClient(app)

    response = client.post("/api/settings/export")
    assert response.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = zf.namelist()
    # Should contain at least the .db file
    db_files = [n for n in names if n.endswith(".db")]
    assert len(db_files) >= 1
    zf.close()


@pytest.mark.asyncio
async def test_export_snapshot_includes_wal_commits(monkeypatch, tmp_path):
    """A backup must include rows still sitting in the WAL file.

    The endpoint uses SQLite's backup API, which folds uncheckpointed WAL
    frames into the exported snapshot. Keep the source connection open so the
    commit genuinely lives in the WAL, then verify it survived the export.
    """
    from app.api import export as export_api
    from app.main import create_app

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "creator_pulse.db"

    source = sqlite3.connect(str(db_path))
    try:
        source.execute("PRAGMA journal_mode=WAL")
        source.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        source.execute("INSERT INTO t (v) VALUES ('wal-committed')")
        source.commit()

        monkeypatch.setattr(
            export_api,
            "get_settings",
            lambda: SimpleNamespace(
                data_dir=data_dir,
                browser_profiles_dir=tmp_path,
                database_url="sqlite+aiosqlite:///x",
                host="127.0.0.1",
                port=8001,
                debug=False,
                enable_mock_data=False,
                dev_mode=False,
                enable_scheduled_sync=False,
                sync_interval_minutes=60,
                sync_max_posts=50,
                data_retention_days=365,
                log_level="INFO",
                x_bearer_token="",
                x_client_id="",
                x_client_secret="",
                x_access_token="",
                x_access_token_secret="",
            ),
        )
        # This test intentionally places its disposable SQLite database under
        # pytest's external temp root. Scope enforcement has separate coverage;
        # here we exercise the successful WAL-aware snapshot path.
        monkeypatch.setattr(export_api, "is_under_project", lambda _path: True)

        app = create_app()
        client = TestClient(app)
        response = client.post("/api/settings/export")
        assert response.status_code == 200

        zf = zipfile.ZipFile(io.BytesIO(response.content))
        db_name = next(name for name in zf.namelist() if name.endswith(".db"))
        exported = zf.read(db_name)
        zf.close()

        check_path = tmp_path / "check.db"
        check_path.write_bytes(exported)
        check = sqlite3.connect(str(check_path))
        try:
            rows = check.execute("SELECT v FROM t").fetchall()
        finally:
            check.close()
        assert rows == [("wal-committed",)]
    finally:
        source.close()
