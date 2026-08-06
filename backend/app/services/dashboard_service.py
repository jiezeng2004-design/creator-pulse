"""Dashboard aggregation."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import PLATFORM_LABELS, platform_capabilities
from app.models.account import PlatformAccount
from app.models.comment import Comment
from app.models.enums import CommentLocalStatus, Platform
from app.models.post import Post
from app.schemas.dashboard import DashboardSummary, PlatformCard
from app.services.settings_service import get_or_create_settings

# ---------------------------------------------------------------------------
# In-memory async TTL cache (60 s expiry) - no external dependencies
# ---------------------------------------------------------------------------

_cache_lock = asyncio.Lock()
_cache: dict[str, tuple[datetime, DashboardSummary]] = {}
CACHE_TTL_SECONDS = 60


def _cache_key() -> str:
    """Return the cache key. All dashboard queries share one key."""
    return "dashboard"


async def _cache_get(key: str) -> DashboardSummary | None:
    """Return cached value if it exists and has not expired."""
    async with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        expiry, data = entry
        if datetime.now(UTC) < expiry:
            return data
        del _cache[key]
        return None


async def _cache_set(key: str, data: DashboardSummary) -> None:
    """Store *data* in the cache with a 60-second expiry window."""
    async with _cache_lock:
        _cache[key] = (datetime.now(UTC) + timedelta(seconds=CACHE_TTL_SECONDS), data)


async def invalidate_cache() -> None:
    """Drop cached summaries so the next read reflects freshly synced data."""
    async with _cache_lock:
        _cache.clear()


async def build_dashboard(db: AsyncSession) -> DashboardSummary:
    """Build the dashboard summary, using a 60-second in-memory TTL cache."""
    key = _cache_key()

    # Try the cache first
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    result = await _build_dashboard_fresh(db)
    await _cache_set(key, result)
    return result


async def _build_dashboard_fresh(db: AsyncSession) -> DashboardSummary:
    """Core aggregation logic (no cache)."""
    now = datetime.now(UTC)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    settings = await get_or_create_settings(db)

    # Batch 1: Global post counts (24h / 7d)
    posts_24h_result = await db.execute(
        select(func.count(Post.id)).where(Post.published_at >= day_ago)
    )
    posts_24h = posts_24h_result.scalar_one()

    posts_7d_result = await db.execute(
        select(func.count(Post.id)).where(Post.published_at >= week_ago)
    )
    posts_7d = posts_7d_result.scalar_one()

    # Batch 2: Global metrics sums in a single query
    global_metrics = await db.execute(
        select(
            func.sum(Post.view_count).label("view_sum"),
            func.sum(Post.impression_count).label("impr_sum"),
            func.sum(Post.like_count).label("like_sum"),
            func.sum(Post.favorite_count).label("fav_sum"),
            func.sum(Post.share_count).label("share_sum"),
            func.sum(Post.repost_count).label("repost_sum"),
            func.sum(Post.comment_count).label("comment_sum"),
            func.count(Post.id).filter(Post.view_count.is_not(None)).label("has_views"),
            func.count(Post.id).filter(Post.impression_count.is_not(None)).label("has_impr"),
        )
    )
    gm = global_metrics.one()
    view_sum = gm.view_sum
    impr_sum = gm.impr_sum
    like_sum = gm.like_sum
    fav_sum = gm.fav_sum
    share_sum = gm.share_sum
    repost_sum = gm.repost_sum
    comment_sum = gm.comment_sum

    total_views: int | None
    if gm.has_views or gm.has_impr:
        total_views = int(view_sum or 0) + int(impr_sum or 0)
    else:
        total_views = None

    eng_parts = [like_sum, fav_sum, share_sum, repost_sum, comment_sum]
    total_engagement = None
    if any(p is not None for p in eng_parts):
        total_engagement = sum(int(p or 0) for p in eng_parts)

    # Batch 3: Global comment status counts
    comment_status_result = await db.execute(
        select(
            func.count(Comment.id).filter(
                Comment.local_status == CommentLocalStatus.NEW.value
            ).label("new_comments"),
            func.count(Comment.id).filter(
                Comment.local_status == CommentLocalStatus.PENDING.value
            ).label("pending_comments"),
        )
    )
    cs = comment_status_result.one()
    new_comments = cs.new_comments
    pending_comments = cs.pending_comments

    # Batch 4: Last global sync time
    last_sync = (
        await db.execute(select(func.max(PlatformAccount.last_successful_sync_at)))
    ).scalar_one()

    caps = {c["platform"]: c for c in platform_capabilities()}

    # Batch 5: Per-platform aggregated data in a single query using GROUP BY.
    # Do NOT join Comment here - a LEFT JOIN on Comment would duplicate Post rows
    # (one outer row per comment), inflating count(Post.id) and sum(Post.*) when
    # an account has multiple comments. Instead, use correlated scalar subqueries
    # for the comment counts so post metrics are computed from the Post table alone.
    platform_agg = await db.execute(
        select(
            Post.account_id,
            func.count(Post.id).filter(Post.published_at >= week_ago).label("posts_week"),
            func.sum(Post.view_count).label("plat_view_sum"),
            func.sum(Post.impression_count).label("plat_impr_sum"),
            func.count(Post.id).filter(Post.view_count.is_not(None)).label("plat_has_views"),
            func.count(Post.id).filter(Post.impression_count.is_not(None)).label("plat_has_impr"),
            func.sum(Post.like_count).label("plat_like_sum"),
            func.sum(Post.favorite_count).label("plat_fav_sum"),
            func.sum(Post.share_count).label("plat_share_sum"),
            func.sum(Post.repost_count).label("plat_repost_sum"),
            func.sum(Post.comment_count).label("plat_comment_sum"),
            func.count(Post.id).filter(Post.like_count.is_not(None)).label("plat_has_likes"),
            func.count(Post.id).filter(Post.favorite_count.is_not(None)).label("plat_has_favs"),
            func.count(Post.id).filter(Post.share_count.is_not(None)).label("plat_has_shares"),
            func.count(Post.id).filter(Post.repost_count.is_not(None)).label("plat_has_reposts"),
            func.count(Post.id).filter(Post.comment_count.is_not(None)).label("plat_has_post_comments"),
            (
                select(func.count(Comment.id))
                .where(
                    Comment.account_id == Post.account_id,
                    Comment.local_status == CommentLocalStatus.NEW.value,
                )
                .correlate(Post)
                .scalar_subquery()
            ).label("plat_new_c"),
            (
                select(func.count(Comment.id))
                .where(
                    Comment.account_id == Post.account_id,
                    Comment.local_status == CommentLocalStatus.PENDING.value,
                )
                .correlate(Post)
                .scalar_subquery()
            ).label("plat_pend_c"),
        )
        .group_by(Post.account_id)
    )

    # Build per-account accumulators keyed by account_id
    account_data: dict[int, dict] = {}
    for row in platform_agg.all():
        aid = row[0]
        if aid is None:
            continue
        if aid not in account_data:
            account_data[aid] = {
                "posts_week": 0,
                "view_sum": 0,
                "impr_sum": 0,
                "has_views": False,
                "has_impr": False,
                "like_sum": 0,
                "fav_sum": 0,
                "share_sum": 0,
                "repost_sum": 0,
                "comment_sum": 0,
                "has_likes": False,
                "has_favs": False,
                "has_shares": False,
                "has_reposts": False,
                "has_post_comments": False,
                "new_c": 0,
                "pend_c": 0,
            }
        ad = account_data[aid]
        ad["posts_week"] += int(row[1] or 0)
        ad["view_sum"] += int(row[2] or 0)
        ad["impr_sum"] += int(row[3] or 0)
        if row[4]:
            ad["has_views"] = True
        if row[5]:
            ad["has_impr"] = True
        ad["like_sum"] += int(row[6] or 0)
        ad["fav_sum"] += int(row[7] or 0)
        ad["share_sum"] += int(row[8] or 0)
        ad["repost_sum"] += int(row[9] or 0)
        ad["comment_sum"] += int(row[10] or 0)
        ad["has_likes"] = ad["has_likes"] or bool(row[11])
        ad["has_favs"] = ad["has_favs"] or bool(row[12])
        ad["has_shares"] = ad["has_shares"] or bool(row[13])
        ad["has_reposts"] = ad["has_reposts"] or bool(row[14])
        ad["has_post_comments"] = ad["has_post_comments"] or bool(row[15])
        ad["new_c"] += int(row[16] or 0)
        ad["pend_c"] += int(row[17] or 0)

    # Batch 6: Fetch all accounts in one query, grouped by platform
    all_accounts_result = await db.execute(select(PlatformAccount))
    all_accounts = list(all_accounts_result.scalars().all())
    accounts_by_platform: dict[str, list] = {}
    for account in all_accounts:
        accounts_by_platform.setdefault(account.platform, []).append(account)

    cards: list[PlatformCard] = []
    for platform in Platform:
        accounts = accounts_by_platform.get(platform.value, [])
        account_ids = [a.id for a in accounts]

        # Aggregate per-account data for this platform
        posts_week = 0
        plat_view_sum = 0
        plat_impr_sum = 0
        plat_has_views = False
        plat_has_impr = False
        metric_sums = {key: 0 for key in ("likes", "favorites", "shares", "reposts", "comments")}
        metric_presence = {key: False for key in metric_sums}
        new_c = 0
        pend_c = 0
        for aid in account_ids:
            if aid in account_data:
                ad = account_data[aid]
                posts_week += ad["posts_week"]
                plat_view_sum += ad["view_sum"]
                plat_impr_sum += ad["impr_sum"]
                if ad["has_views"] or ad["has_impr"]:
                    plat_has_views = plat_has_views or ad["has_views"]
                    plat_has_impr = plat_has_impr or ad["has_impr"]
                for key, sum_key, present_key in (
                    ("likes", "like_sum", "has_likes"),
                    ("favorites", "fav_sum", "has_favs"),
                    ("shares", "share_sum", "has_shares"),
                    ("reposts", "repost_sum", "has_reposts"),
                    ("comments", "comment_sum", "has_post_comments"),
                ):
                    metric_sums[key] += ad[sum_key]
                    metric_presence[key] = metric_presence[key] or ad[present_key]
                new_c += ad["new_c"]
                pend_c += ad["pend_c"]

        plat_views: int | None
        if plat_has_views or plat_has_impr:
            plat_views = plat_view_sum + plat_impr_sum
        else:
            plat_views = None

        last = max(
            (a.last_successful_sync_at for a in accounts if a.last_successful_sync_at),
            default=None,
        )
        if not accounts:
            status_summary = "未连接"
        else:
            statuses = {a.account_status for a in accounts}
            if "error" in statuses:
                status_summary = "异常"
            elif "syncing" in statuses:
                status_summary = "同步中"
            elif "login_required" in statuses:
                status_summary = "需要登录"
            elif "connected" in statuses:
                status_summary = "已连接"
            else:
                status_summary = "未连接"

        is_mock = any(a.is_mock for a in accounts)
        cap = caps.get(platform.value, {})
        metric_config = {
            "x": (
                ("点赞", "likes"),
                ("转发", "reposts"),
                ("回复", "comments"),
                "官方公开 API 不提供阅读量，优先展示公开互动指标",
            ),
            "zhihu": (
                ("浏览", "views"),
                ("赞同", "likes"),
                ("评论", "comments"),
                "数据来自知乎创作者内容页，取决于当前登录态",
            ),
            "toutiao": (
                ("阅读", "views"),
                ("点赞", "likes"),
                ("评论", "comments"),
                "指标来自头条创作者中心，页面权限可能影响可用性",
            ),
            "xiaohongshu": (
                ("点赞", "likes"),
                ("收藏", "favorites"),
                ("评论", "comments"),
                "指标依赖小红书创作者端，当前适配器仍在完善",
            ),
        }[platform.value]

        metric_values: dict[str, int | None] = {
            "views": plat_views,
            **{
                key: int(metric_sums[key]) if metric_presence[key] else None
                for key in metric_sums
            },
        }

        cards.append(
            PlatformCard(
                platform=platform.value,
                platform_label=PLATFORM_LABELS.get(platform, platform.value),
                account_count=len(accounts),
                posts_last_7d=int(posts_week) if account_ids else 0,
                total_views_or_impressions=plat_views,
                new_comments=int(new_c) if account_ids else 0,
                pending_comments=int(pend_c) if account_ids else 0,
                last_sync_at=last,
                metric_primary_label=metric_config[0][0],
                metric_primary_value=metric_values[metric_config[0][1]],
                metric_secondary_label=metric_config[1][0],
                metric_secondary_value=metric_values[metric_config[1][1]],
                metric_tertiary_label=metric_config[2][0],
                metric_tertiary_value=metric_values[metric_config[2][1]],
                metric_note=metric_config[3],
                status_summary=status_summary,
                experimental=bool(cap.get("experimental")),
                is_mock=is_mock,
            )
        )

    return DashboardSummary(
        posts_last_24h=int(posts_24h),
        posts_last_7d=int(posts_7d),
        total_views_or_impressions=total_views,
        total_engagement=total_engagement,
        new_comments=int(new_comments),
        pending_comments=int(pending_comments),
        platforms=cards,
        mock_mode=settings.enable_mock_data or any(c.is_mock for c in cards),
        last_global_sync_at=last_sync,
    )
