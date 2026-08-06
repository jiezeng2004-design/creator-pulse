"""Adapter parser and SQLite concurrency tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.exceptions import UnsupportedFeatureError
from app.adapters.toutiao.parser import parse_article, parse_comment
from app.adapters.xiaohongshu.pages.comments import CommentsPage
from app.adapters.xiaohongshu.parser import parse_note
from app.db.session import configure_sqlite_engine


def test_toutiao_parse_nested_feed_item() -> None:
    item = {
        "assembleCell": {
            "itemCell": {
                "articleBase": {
                    "groupID": 12345,
                    "gidStr": "12345",
                    "title": "标题",
                    "abstractText": "摘要",
                    "articleURL": "https://www.toutiao.com/item/12345/",
                    "publishTime": 1785891276,
                },
                "itemCounter": {
                    "readCount": 25,
                    "showCount": 58,
                    "diggCount": 3,
                    "repinCount": 1,
                    "commentCount": 2,
                    "shareCount": 4,
                },
            }
        }
    }
    p = parse_article(item)
    assert p is not None
    assert p.platform_post_id == "12345"
    assert p.title == "标题"
    assert p.content_preview == "摘要"
    assert p.view_count == 25
    assert p.impression_count == 58
    assert p.like_count == 3
    assert p.favorite_count == 1
    assert p.share_count == 4
    assert p.comment_count == 2
    assert p.published_at == datetime.fromtimestamp(1785891276, tz=UTC)


def test_toutiao_parse_comment_flat_user() -> None:
    c = parse_comment(
        {
            "id": "c1",
            "content": "你好",
            "user_name": "小明",
            "user_id": "u1",
            "create_time": 1785891276,
            "digg_count": 5,
        },
        "p1",
    )
    assert c is not None
    assert c.platform_comment_id == "c1"
    assert c.author_name == "小明"
    assert c.author_platform_id == "u1"
    assert c.like_count == 5
    assert c.published_at == datetime.fromtimestamp(1785891276, tz=UTC)


def test_xhs_parse_note_new_fields() -> None:
    n = parse_note(
        {
            "id": "n1",
            "display_title": "标题",
            "view_count": 772,
            "likes": 47,
            "shared_count": 8,
            "comments_count": 2,
            "collected_count": 64,
            "time": "2026-07-23 21:24",
        }
    )
    assert n is not None
    assert n.platform_post_id == "n1"
    assert n.view_count == 772
    assert n.like_count == 47
    assert n.share_count == 8
    assert n.comment_count == 2
    assert n.favorite_count == 64
    assert n.published_at is not None
    assert n.published_at.year == 2026


def test_xhs_comments_reports_unsupported() -> None:
    cp = CommentsPage(object())
    try:
        asyncio.run(cp.fetch_comments("n1"))
    except UnsupportedFeatureError as exc:
        assert "评论" in exc.message
    else:
        raise AssertionError("expected UnsupportedFeatureError")


@pytest_asyncio.fixture
async def concurrent_engine(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'concurrent.db').as_posix()}"
    )
    configure_sqlite_engine(engine)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"))
    yield engine
    await engine.dispose()


async def test_sqlite_wal_and_busy_timeout(concurrent_engine) -> None:
    async with concurrent_engine.connect() as conn:
        journal = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
        timeout = (await conn.execute(text("PRAGMA busy_timeout"))).scalar()
    assert journal == "wal"
    assert timeout == 30000


async def test_concurrent_writers_do_not_lock(concurrent_engine) -> None:
    factory = async_sessionmaker(concurrent_engine, expire_on_commit=False)

    async def writer(value: str, delay: float) -> None:
        async with factory() as session:
            await session.execute(
                text("INSERT INTO t (v) VALUES (:v)"), {"v": value}
            )
            await session.commit()
            await asyncio.sleep(delay)

    await asyncio.gather(writer("a", 0.2), writer("b", 0.1), writer("c", 0.0))
    async with factory() as session:
        rows = (await session.execute(text("SELECT v FROM t ORDER BY v"))).scalars().all()
    assert rows == ["a", "b", "c"]
