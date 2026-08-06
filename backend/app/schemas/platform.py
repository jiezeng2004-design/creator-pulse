"""Platform capability metadata."""

from pydantic import BaseModel


class PlatformCapability(BaseModel):
    platform: str
    label: str
    login_method: str
    posts: str
    views: str
    likes: str
    favorites: str
    shares: str
    comments: str
    official_replied: str
    local_status: str
    stability: str
    notes: str
    experimental: bool = False
