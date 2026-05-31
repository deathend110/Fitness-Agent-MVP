from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.models import ChatMessage, ChatSession, utc_now
from backend.schemas import (
    ChatMessageCreateSchema,
    ChatMessageSchema,
    ChatSessionCreateSchema,
    ChatSessionSchema,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

DEFAULT_SESSION_TITLE = "默认对话"


def build_session_response(session: ChatSession) -> ChatSessionSchema:
    return ChatSessionSchema(
        id=session.id,
        title=session.title,
        createdAt=session.created_at,
        updatedAt=session.updated_at,
    )


def build_message_response(message: ChatMessage) -> ChatMessageSchema:
    return ChatMessageSchema(
        id=message.id,
        sessionId=message.session_id,
        role=message.role,
        content=message.content,
        suggestion=message.suggestion,
        createdAt=message.created_at,
    )


async def find_default_session(session: AsyncSession) -> ChatSession | None:
    result = await session.execute(
        select(ChatSession)
        .where(ChatSession.title == DEFAULT_SESSION_TITLE)
        .order_by(ChatSession.id)
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/sessions", response_model=list[ChatSessionSchema], response_model_by_alias=True)
async def list_chat_sessions(session: AsyncSession = Depends(get_db_session)) -> list[ChatSessionSchema]:
    result = await session.execute(select(ChatSession).order_by(ChatSession.updated_at.desc(), ChatSession.id.desc()))
    return [build_session_response(item) for item in result.scalars().all()]


@router.post("/sessions", response_model=ChatSessionSchema, response_model_by_alias=True)
async def create_chat_session(
    payload: ChatSessionCreateSchema,
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionSchema:
    now = utc_now()
    chat_session = ChatSession(
        title=payload.title or DEFAULT_SESSION_TITLE,
        created_at=now,
        updated_at=now,
    )
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)
    return build_session_response(chat_session)


@router.get("/sessions/default", response_model=ChatSessionSchema, response_model_by_alias=True)
async def get_or_create_default_session(session: AsyncSession = Depends(get_db_session)) -> ChatSessionSchema:
    chat_session = await find_default_session(session)
    if chat_session is not None:
        return build_session_response(chat_session)

    # 默认会话承接旧版单条 chatHistory；真实多会话选择留给后续 UI 版本。
    now = utc_now()
    chat_session = ChatSession(
        title=DEFAULT_SESSION_TITLE,
        created_at=now,
        updated_at=now,
    )
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)
    return build_session_response(chat_session)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageSchema],
    response_model_by_alias=True,
)
async def list_chat_messages(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatMessageSchema]:
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    # 历史消息必须全量返回，不能沿用前端上下文窗口的 20 条裁剪策略。
    return [build_message_response(item) for item in result.scalars().all()]


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageSchema,
    response_model_by_alias=True,
)
async def append_chat_message(
    payload: ChatMessageCreateSchema,
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ChatMessageSchema:
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    now = utc_now()
    message = ChatMessage(
        session_id=session_id,
        role=payload.role,
        content=payload.content,
        suggestion=payload.suggestion,
        created_at=now,
    )
    session.add(message)
    # 新消息写入时同步触碰会话更新时间，列表页才能按最近对话排序。
    chat_session.updated_at = now
    await session.commit()
    await session.refresh(message)
    return build_message_response(message)
