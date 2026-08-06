from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health() -> JSONResponse:
    try:
        from app.db.session import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok", "db": "connected"})
    except Exception:  # noqa: BLE001 - health probe must never raise
        return JSONResponse(
            {"status": "degraded", "db": "error"},
            status_code=503,
        )
