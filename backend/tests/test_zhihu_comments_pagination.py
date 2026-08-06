"""Zhihu comment fetch must paginate past the first 20-item page."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.adapters.zhihu.adapter import ZhihuAdapter


def _page(start: int, count: int, is_end: bool) -> dict:
    return {
        "data": [
            {
                "id": str(start + i),
                "content": f"comment {start + i}",
                "author": {"name": f"user {start + i}"},
                "created_time": 1786000000 + start + i,
            }
            for i in range(count)
        ],
        "paging": {"is_end": is_end, "totals": 35},
    }


@pytest.mark.asyncio
async def test_fetch_comments_paginates_until_is_end(tmp_path: Path):
    profile = tmp_path / "zhihu" / "user"
    profile.mkdir(parents=True)
    adapter = ZhihuAdapter(profile, headless=True)

    requested: list[str] = []

    async def fake_fetch_json(url: str):
        requested.append(url)
        if "offset=0" in url:
            return _page(1, 20, is_end=False)
        if "offset=20" in url:
            return _page(21, 15, is_end=True)
        return {"data": [], "paging": {"is_end": True}}

    with patch.object(adapter, "_fetch_json", side_effect=fake_fetch_json):
        comments = await adapter.fetch_comments("answer:123", limit=100)

    assert len(comments) == 35
    assert requested == [
        "https://www.zhihu.com/api/v4/comment_v5/answers/123/root_comment?order_by=ts&limit=20&offset=0",
        "https://www.zhihu.com/api/v4/comment_v5/answers/123/root_comment?order_by=ts&limit=20&offset=20",
    ]
    assert comments[0].platform_comment_id == "1"
    assert comments[34].platform_comment_id == "35"


@pytest.mark.asyncio
async def test_fetch_comments_respects_limit(tmp_path: Path):
    profile = tmp_path / "zhihu" / "user2"
    profile.mkdir(parents=True)
    adapter = ZhihuAdapter(profile, headless=True)

    requested: list[str] = []

    async def fake_fetch_json(url: str):
        requested.append(url)
        offset = int(url.split("offset=")[1]) if "offset=" in url else 0
        return _page(offset + 1, 20, is_end=False)

    with patch.object(adapter, "_fetch_json", side_effect=fake_fetch_json):
        comments = await adapter.fetch_comments("answer:123", limit=45)

    # 20 + 20 + 5 from the third page; stops once limit is reached.
    assert len(comments) == 45
    assert len(requested) == 3
    assert "offset=40" in requested[-1]


@pytest.mark.asyncio
async def test_fetch_comments_dedupes_child_comments(tmp_path: Path):
    profile = tmp_path / "zhihu" / "user3"
    profile.mkdir(parents=True)
    adapter = ZhihuAdapter(profile, headless=True)

    async def fake_fetch_json(url: str):
        return {
            "data": [
                {
                    "id": "root-1",
                    "content": "root",
                    "author": {"name": "a"},
                    "child_comments": [
                        {"id": "root-1", "content": "dup root", "author": {"name": "a"}},
                        {"id": "child-1", "content": "child", "author": {"name": "b"}},
                    ],
                }
            ],
            "paging": {"is_end": True},
        }

    with patch.object(adapter, "_fetch_json", side_effect=fake_fetch_json):
        comments = await adapter.fetch_comments("answer:123", limit=100)

    ids = [c.platform_comment_id for c in comments]
    assert ids == ["root-1", "child-1"]
