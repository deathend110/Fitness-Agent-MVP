from __future__ import annotations

from backend.db.models import ChatSession

DEFAULT_SESSION_TITLE = "默认对话"
UNTITLED_SESSION_TITLE = "新对话"
SESSION_TITLE_MAX_LENGTH = 48


def build_session_title_from_user_prompt(user_content: str) -> str:
    """把用户首条提问压成历史标题，避免侧栏长期停留在“新对话”占位文案。"""

    normalized = " ".join(str(user_content or "").split())
    if not normalized:
        return UNTITLED_SESSION_TITLE
    return normalized[:SESSION_TITLE_MAX_LENGTH]


def update_session_title_from_user_prompt(chat_session: ChatSession, user_content: str) -> None:
    """只有未命名会话才会被首条 user prompt 回填标题，默认会话语义保持不变。"""

    if chat_session.title != UNTITLED_SESSION_TITLE:
        return
    chat_session.title = build_session_title_from_user_prompt(user_content)
