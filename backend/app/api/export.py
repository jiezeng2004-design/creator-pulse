"""Database export API endpoint."""

from __future__ import annotations

import asyncio
import sqlite3
import tempfile
import zipfile
from collections.abc import AsyncIterator
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import BACKEND_DIR, get_settings
from app.core.security import is_under_project

router = APIRouter(prefix="/api", tags=["export"])


def _build_backup_zip(db_path: Path, timestamp: str) -> bytes:
    """Create a consistent SQLite snapshot and pack it into a ZIP.

    The live database runs in WAL mode, so copying the ``.db`` file alone can
    miss uncheckpointed commits. The SQLite backup API folds the WAL into a
    single consistent snapshot, which is what a backup should be.
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        with tempfile.TemporaryDirectory(prefix="creatorpulse-export-") as tmp:
            snapshot = Path(tmp) / f"creator_pulse_{timestamp}.db"
            source = sqlite3.connect(str(db_path))
            try:
                source.execute("PRAGMA busy_timeout=30000")
                destination = sqlite3.connect(str(snapshot))
                try:
                    source.backup(destination)
                finally:
                    destination.close()
            finally:
                source.close()
            zf.write(str(snapshot), arcname=f"creator_pulse_{timestamp}.db")
        # Include .env.example for reference (not actual .env)
        env_example = BACKEND_DIR / ".env.example"
        if env_example.exists():
            zf.write(str(env_example), arcname=".env.example")
    buffer.seek(0)
    return buffer.getvalue()


@router.post("/settings/export")
async def export_database() -> StreamingResponse:
    """Export the SQLite database as a ZIP file for backup purposes."""
    settings = get_settings()
    db_path = settings.data_dir / "creator_pulse.db"

    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database file not found.")

    if not is_under_project(db_path):
        raise HTTPException(status_code=403, detail="Database path outside project scope.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"creator_pulse_backup_{timestamp}.zip"

    # Snapshot + zip is CPU/IO work; keep it off the event loop.
    payload = await asyncio.to_thread(_build_backup_zip, db_path, timestamp)

    async def file_iter() -> AsyncIterator[bytes]:
        yield payload

    return StreamingResponse(
        file_iter(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
        },
    )
