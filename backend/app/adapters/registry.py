"""Adapter factory / registry."""

from __future__ import annotations

from pathlib import Path

from app.adapters.base import PlatformAdapter
from app.adapters.mock import build_mock_adapter
from app.adapters.toutiao import ToutiaoAdapter
from app.adapters.x import XAdapter
from app.adapters.x.browser import XBrowserAdapter
from app.adapters.xiaohongshu import XiaohongshuAdapter
from app.adapters.zhihu import ZhihuAdapter
from app.core.config import get_settings
from app.core.security import profile_dir_for_account
from app.models.enums import Platform

__all__ = ["create_adapter", "platform_capabilities"]

PLATFORM_LABELS = {
    Platform.X: "X",
    Platform.XIAOHONGSHU: "小红书",
    Platform.ZHIHU: "知乎",
    Platform.TOUTIAO: "今日头条",
}


def create_adapter(
    platform: str,
    *,
    use_mock: bool = False,
    browser_profile_path: str | None = None,
    account_key: str = "default",
    username: str | None = None,
) -> PlatformAdapter:
    settings = get_settings()
    if use_mock or settings.enable_mock_data:
        return build_mock_adapter(platform)

    profile = (
        Path(browser_profile_path)
        if browser_profile_path
        else profile_dir_for_account(platform, account_key)
    )

    if platform == Platform.X.value:
        # A browser profile path means the account is in free browser-login
        # mode; otherwise the official API (Bearer Token) mode is used.
        if browser_profile_path:
            return XBrowserAdapter(profile)
        return XAdapter(username=username)

    if platform == Platform.ZHIHU.value:
        return ZhihuAdapter(profile)
    if platform == Platform.TOUTIAO.value:
        return ToutiaoAdapter(profile)
    if platform == Platform.XIAOHONGSHU.value:
        return XiaohongshuAdapter(profile)

    raise ValueError(f"Unknown platform: {platform}")


def platform_capabilities() -> list[dict]:
    """Capability matrix for API / UI."""
    return [
        {
            "platform": "x",
            "label": "X",
            "login_method": "浏览器登录（免 API 额度）或官方 API Token",
            "posts": "浏览器模式 Experimental / API 模式 Stable",
            "views": "浏览器模式 Experimental（页面可读时返回）",
            "likes": "浏览器模式 Experimental / API 模式 Stable",
            "favorites": "Unsupported（使用 like）",
            "shares": "Repost 可用",
            "comments": "浏览器模式暂不支持；API 模式需额外权限",
            "official_replied": "Not yet implemented",
            "local_status": "Stable",
            "stability": "Experimental",
            "notes": "浏览器模式免费但不消耗 API credits，依赖页面结构；API 模式稳定但消耗月度 credits。",
            "experimental": True,
        },
        {
            "platform": "zhihu",
            "label": "知乎",
            "login_method": "Playwright 手动登录 + 本地 Profile",
            "posts": "Experimental / Stable 取决于页面结构",
            "views": "Experimental（创作中心可读时返回，否则 null）",
            "likes": "Experimental",
            "favorites": "Experimental",
            "shares": "Unsupported / 部分可用",
            "comments": "Experimental",
            "official_replied": "Not yet implemented",
            "local_status": "Stable",
            "stability": "Experimental",
            "notes": "优先拦截创作者后台 JSON；DOM 为回退。不自动回复。",
            "experimental": False,
        },
        {
            "platform": "toutiao",
            "label": "今日头条",
            "login_method": "Playwright 手动登录 + 本地 Profile",
            "posts": "Experimental",
            "views": "Experimental",
            "likes": "Experimental",
            "favorites": "Experimental",
            "shares": "Experimental",
            "comments": "Experimental",
            "official_replied": "Not yet implemented",
            "local_status": "Stable",
            "stability": "Experimental",
            "notes": "mp.toutiao.com；页面/API 变化可能导致空结果，不会伪造数据。",
            "experimental": True,
        },
        {
            "platform": "xiaohongshu",
            "label": "小红书",
            "login_method": "Playwright 手动登录 + 本地 Profile",
            "posts": "Not yet implemented / Experimental skeleton",
            "views": "Not yet implemented",
            "likes": "Not yet implemented",
            "favorites": "Not yet implemented",
            "shares": "Not yet implemented",
            "comments": "Not yet implemented",
            "official_replied": "Not yet implemented",
            "local_status": "Stable",
            "stability": "Experimental",
            "notes": "风控与选择器变化频繁；v1 提供登录骨架与 Mock。",
            "experimental": True,
        },
    ]
