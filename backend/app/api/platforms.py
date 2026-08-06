from fastapi import APIRouter

from app.adapters.registry import platform_capabilities
from app.schemas.platform import PlatformCapability

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.get("", response_model=list[PlatformCapability])
async def list_platforms() -> list[PlatformCapability]:
    return [PlatformCapability(**c) for c in platform_capabilities()]
