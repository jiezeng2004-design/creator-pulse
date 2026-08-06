"""Selectors for Xiaohongshu creator center (experimental / not fully implemented)."""

LOGIN_URL = "https://creator.xiaohongshu.com/login"
CREATOR_HOME = "https://creator.xiaohongshu.com/new/home"
CONTENT_LIST = "https://creator.xiaohongshu.com/new/note-manager"
COMMENTS = "https://creator.xiaohongshu.com/new/comment/note"

SELECTORS = {
    "login": ".login-container, .qrcode-img, [class*='login']",
    "user": ".user-info, .account-name, [class*='avatar']",
    "note_row": ".note-item, .content-item, table tbody tr",
    "comment_item": ".comment-item, [class*='comment']",
}

API_HINTS = {
    "notes": "/api/galaxy/v2/creator/note/user/posted",
    "data": "/api/galaxy/creator/data",
    "comment": "/api/galaxy/creator/comment",
}
