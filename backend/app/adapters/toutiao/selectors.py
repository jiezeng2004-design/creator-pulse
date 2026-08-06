"""Selectors for Toutiao creator platform (mp.toutiao.com)."""

LOGIN_URL = "https://mp.toutiao.com/auth/page/login"
CREATOR_HOME = "https://mp.toutiao.com/profile_v4/index"
CONTENT_LIST = "https://mp.toutiao.com/profile_v4/manage/content/all"
COMMENTS = "https://mp.toutiao.com/profile_v4/manage/comment"
COMMENT_LIST_API = "https://mp.toutiao.com/mp/agw/comment/article_comment_list"
COMMENT_APP_ID = "1231"

SELECTORS = {
    "login_form": ".login-form, .sso-login, [class*='login']",
    "user_info": ".user-info, .auth-avator, [class*='avatar']",
    "content_row": ".article-card, .content-item, table tbody tr, [class*='article']",
    "comment_item": ".comment-item, [class*='comment-list'] li",
}

API_HINTS = {
    "articles": "/api/feed/mp_provider/v1",
    "stats": "/mp/agw/statistic",
    "comment": "/mp/agw/comment",
}
