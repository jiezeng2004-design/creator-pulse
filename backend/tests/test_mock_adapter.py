import pytest

from app.adapters.exceptions import (
    AuthenticationRequiredError,
    RateLimitError,
    SelectorChangedError,
)
from app.adapters.mock import MockScenario, build_mock_adapter


@pytest.mark.asyncio
async def test_mock_normal():
    ad = build_mock_adapter("zhihu")
    auth = await ad.check_authentication()
    assert auth.authenticated
    posts = await ad.fetch_posts(limit=3)
    assert len(posts) == 3
    # null metrics allowed
    assert any(p.impression_count is None or p.view_count is not None for p in posts)
    comments = await ad.fetch_comments(posts[0].platform_post_id)
    assert len(comments) >= 1
    await ad.close()


@pytest.mark.asyncio
async def test_mock_auth_required():
    ad = build_mock_adapter("x", scenario=MockScenario.AUTH_REQUIRED)
    with pytest.raises(AuthenticationRequiredError):
        await ad.check_authentication()


@pytest.mark.asyncio
async def test_mock_rate_limit():
    ad = build_mock_adapter("x", scenario=MockScenario.RATE_LIMIT)
    with pytest.raises(RateLimitError):
        await ad.fetch_posts()


@pytest.mark.asyncio
async def test_mock_selector():
    ad = build_mock_adapter("xiaohongshu", scenario=MockScenario.SELECTOR)
    with pytest.raises(SelectorChangedError):
        await ad.fetch_posts()


@pytest.mark.asyncio
async def test_mock_empty_and_duplicate():
    empty = build_mock_adapter("toutiao", scenario=MockScenario.EMPTY)
    assert await empty.fetch_posts() == []
    assert await empty.fetch_comments("x") == []

    dup = build_mock_adapter("toutiao", scenario=MockScenario.DUPLICATE)
    comments = await dup.fetch_comments("post-1")
    ids = [c.platform_comment_id for c in comments]
    assert ids.count(ids[0]) >= 2
