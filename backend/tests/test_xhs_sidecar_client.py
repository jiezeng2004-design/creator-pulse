"""Read-only sidecar client tests."""

from __future__ import annotations

import httpx
import pytest

from app.adapters.xiaohongshu.sidecar_client import (
    SidecarForbiddenError,
    SidecarUnavailableError,
    XhsSidecarClient,
)


def test_sidecar_rejects_non_localhost():
    with pytest.raises(SidecarForbiddenError):
        XhsSidecarClient("http://evil.example.com:8000")


def test_sidecar_accepts_localhost():
    client = XhsSidecarClient("http://127.0.0.1:8000")
    assert client.base_url == "http://127.0.0.1:8000"


@pytest.mark.asyncio
async def test_sidecar_blocks_write_endpoints(monkeypatch):
    client = XhsSidecarClient()
    with pytest.raises(SidecarForbiddenError):
        await client._call("publish_content")
    with pytest.raises(SidecarForbiddenError):
        await client._call("feeds/comment")


@pytest.mark.asyncio
async def test_sidecar_maps_connection_failure(monkeypatch):
    client = XhsSidecarClient(timeout=2.0)

    async def boom(method, path, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(client._client, "request", boom)
    with pytest.raises(SidecarUnavailableError):
        await client.check_login_status()


@pytest.mark.asyncio
async def test_sidecar_reads_feeds(monkeypatch):
    client = XhsSidecarClient()
    captured = {}

    async def fake_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        return httpx.Response(
            200,
            json={"data": [{"id": "n1", "title": "note"}]},
            request=httpx.Request("GET", "http://127.0.0.1:8000/api/v1/feeds/list"),
        )

    monkeypatch.setattr(client._client, "request", fake_request)
    feeds = await client.list_feeds(limit=10)
    assert len(feeds) == 1
    assert captured["path"] == "/api/v1/feeds/list"
