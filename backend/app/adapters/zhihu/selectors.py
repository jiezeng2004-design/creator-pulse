"""Centralized URLs for Zhihu creator data (cookie-authenticated)."""

LOGIN_URL = "https://www.zhihu.com/signin"
CREATOR_HOME = "https://www.zhihu.com/creator"
CONTENT_MANAGE = "https://www.zhihu.com/creator/manage/creation/all"
API_HINTS = {
    "CREATIONS": "/creators/creations",
    "MEMBER_ANSWERS": "/members/{token}/answers",
    "MEMBER_ARTICLES": "/members/{token}/articles",
}
CREATOR_ANALYSIS = "https://www.zhihu.com/creator/analysis"

# JSON APIs used via browser fetch (reuses login cookies)
API_ME = "https://www.zhihu.com/api/v4/me"
API_CREATIONS = (
    "https://www.zhihu.com/api/v4/creators/creations/v2/all"
    "?start=0&end=0&limit={limit}&offset={offset}&need_co_creation=1&sort_type=created"
)
API_MEMBER_ANSWERS = (
    "https://www.zhihu.com/api/v4/members/{token}/answers"
    "?include=data[*].is_normal,content,voteup_count,comment_count,created_time,"
    "updated_time,question,excerpt"
    "&offset={offset}&limit={limit}&sort_by=created"
)
API_MEMBER_ARTICLES = (
    "https://www.zhihu.com/api/v4/members/{token}/articles"
    "?include=data[*].comment_count,voteup_count,created,updated,title,excerpt"
    "&offset={offset}&limit={limit}"
)
API_ANSWER_COMMENTS_V5 = (
    "https://www.zhihu.com/api/v4/comment_v5/answers/{id}/root_comment"
    "?order_by=ts&limit={limit}&offset={offset}"
)
API_ARTICLE_COMMENTS_V5 = (
    "https://www.zhihu.com/api/v4/comment_v5/articles/{id}/root_comment"
    "?order_by=ts&limit={limit}&offset={offset}"
)

SELECTORS = {
    "login_form": ".SignFlow, .SignContainer, form.Login-options, .Qrcode-container",
    "user_avatar": ".AppHeader-profileEntry, .AppHeader-userInfo, img.Avatar",
}
