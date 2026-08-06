import pytest
from conftest import wait_for_sync_run


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_platforms(client):
    r = await client.get("/api/platforms")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4
    assert {p["platform"] for p in data} == {"x", "zhihu", "toutiao", "xiaohongshu"}


@pytest.mark.asyncio
async def test_account_crud_and_sync_mock(client):
    # create mock accounts for all platforms
    created = []
    for platform in ("x", "zhihu", "toutiao", "xiaohongshu"):
        r = await client.post(
            "/api/accounts",
            json={"platform": platform, "display_name": f"{platform} demo", "use_mock": True},
        )
        assert r.status_code == 200, r.text
        created.append(r.json())

    r = await client.get("/api/accounts")
    assert r.status_code == 200
    assert len(r.json()) >= 4

    # sync first account
    aid = created[0]["id"]
    r = await client.post(f"/api/accounts/{aid}/sync")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    run = await wait_for_sync_run(client, body["sync_run_id"])
    assert run["status"] == "success"

    # posts page
    r = await client.get("/api/posts", params={"page": 1, "page_size": 10})
    assert r.status_code == 200
    page = r.json()
    assert "items" in page and "total" in page

    # comments
    r = await client.get("/api/comments", params={"page": 1})
    assert r.status_code == 200
    comments = r.json()
    if comments["total"] > 0:
        cid = comments["items"][0]["id"]
        r = await client.patch(f"/api/comments/{cid}/status", json={"local_status": "handled"})
        assert r.status_code == 200
        assert r.json()["local_status"] == "handled"

    # dashboard
    r = await client.get("/api/dashboard/summary")
    assert r.status_code == 200
    dash = r.json()
    assert "platforms" in dash

    # sync runs
    r = await client.get("/api/sync-runs")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # settings
    r = await client.get("/api/settings")
    assert r.status_code == 200
    r = await client.patch("/api/settings", json={"enable_mock_data": True, "sync_interval_minutes": 30})
    assert r.status_code == 200
    assert r.json()["sync_interval_minutes"] >= 30

    # quick refresh (check + sync) for mock account
    if len(created) > 1:
        r = await client.post(f"/api/accounts/{created[1]['id']}/refresh")
        assert r.status_code == 200
        body = r.json()
        assert "authenticated" in body
        assert "needs_login" in body
        assert body.get("message")
        if body.get("sync_run_id"):
            await wait_for_sync_run(client, body["sync_run_id"])

    # sync-all convenience endpoint
    r = await client.post("/api/accounts/sync-all")
    assert r.status_code == 200
    body = r.json()
    assert "total" in body and "items" in body
    assert body["total"] >= 1
    assert body["started"] + body["skipped"] == body["total"]
    for item in body["items"]:
        if item["sync_run_id"]:
            await wait_for_sync_run(client, item["sync_run_id"])

    # accounts include next_action guidance
    r = await client.get("/api/accounts")
    assert r.status_code == 200
    for acc in r.json():
        assert "next_action" in acc
        if acc.get("next_action"):
            assert acc["next_action"].get("action")
            assert acc["next_action"].get("label")
        # profile path must not expose drive letters / absolute roots
        bp = acc.get("browser_profile_path") or ""
        assert ":" not in bp or bp.count(":") == 0

    # security headers present
    r = await client.get("/api/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"

    # delete
    r = await client.delete(f"/api/accounts/{aid}")
    assert r.status_code == 200
