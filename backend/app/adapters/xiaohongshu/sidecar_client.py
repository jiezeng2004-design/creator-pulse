"""Read-only HTTP client for the xiaohongshu-mcp sidecar (optional).

Design constraints (see docs/adapter-design.md):

- Only localhost is accepted as the sidecar base URL.
- Only a read-only allowlist of endpoints is callable; every write endpoint
  (publish / comment / like / favorite / delete-cookies) is blocked here so the
  frontend has no path to them even if the sidecar exposes them.
- Requests time out; responses are shape-checked before returning.
- When the sidecar is down, callers get a typed ``SidecarUnavailableError`` and
  the platform sync fails softly without affecting other platforms.

The sidecar itself is not bundled or downloaded: the user must run
``xiaohongshu-mcp`` themselves if they opt into this integration.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx


class SidecarUnavailableError(RuntimeError):
    """Raised when the xiaohongshu-mcp sidecar cannot be reached."""


class SidecarForbiddenError(RuntimeError):
    """Raised when a caller tries to use a non-read-only sidecar endpoint."""


_READ_ONLY_ENDPOINTS: dict[str, tuple[str, str]] = {
    "check_login_status": ("GET", "/api/v1/login/status"),
    "list_feeds": ("GET", "/api/v1/feeds/list"),
    "search_feeds": ("GET", "/api/v1/feeds/search"),
    "feed_detail": ("POST", "/api/v1/feeds/detail"),
    "user_profile": ("POST", "/api/v1/user/profile"),
    "my_profile": ("GET", "/api/v1/user/me"),
}


class XhsSidecarClient:
    """Minimal read-only client for the local xiaohongshu-mcp sidecar."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float = 15.0,
    ) -> None:
        host = urlparse(base_url).hostname
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise SidecarForbiddenError(
                f"xiaohongshu-mcp sidecar 只允许 localhost，收到: {base_url}"
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def _call(self, name: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> Any:
        if name not in _READ_ONLY_ENDPOINTS:
            raise SidecarForbiddenError(f"非只读接口被拒绝: {name}")
        method, path = _READ_ONLY_ENDPOINTS[name]
        try:
            resp = await self._client.request(method, path, params=params, json=json)
        except httpx.HTTPError as exc:
            raise SidecarUnavailableError(
                f"xiaohongshu-mcp sidecar 不可用: {exc.__class__.__name__}"
            ) from exc
        if resp.status_code >= 500:
            raise SidecarUnavailableError(f"sidecar 返回 {resp.status_code}")
        try:
            return resp.json()
        except ValueError as exc:
            raise SidecarUnavailableError("sidecar 返回非 JSON 响应") from exc

    async def check_health(self) -> bool:
        """Probe the sidecar health endpoint; never raises."""
        try:
            resp = await self._client.get("/health", timeout=3.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def check_login_status(self) -> dict[str, Any]:
        return await self._call("check_login_status")

    async def list_feeds(self, *, limit: int = 50) -> list[dict[str, Any]]:
        data = await self._call("list_feeds", params={"limit": min(max(limit, 1), 100)})
        if isinstance(data, dict):
            return data.get("data") or data.get("feeds") or []
        return data if isinstance(data, list) else []

    async def feed_detail(self, feed_id: str, xsec_token: str) -> dict[str, Any]:
        data = await self._call(
            "feed_detail",
            json={"feed_id": feed_id, "xsec_token": xsec_token},
        )
        return data if isinstance(data, dict) else {}

    async def my_profile(self) -> dict[str, Any]:
        data = await self._call("my_profile")
        return data if isinstance(data, dict) else {}

    async def close(self) -> None:
        await self._client.aclose()


__all__ = [
    "XhsSidecarClient",
    "SidecarUnavailableError",
    "SidecarForbiddenError",
]
