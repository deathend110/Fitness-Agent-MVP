from __future__ import annotations

from collections.abc import AsyncIterator
import json
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.agent.background_worker import BackgroundTaskRecord, BackgroundWorker
from backend.agent.chat_session import build_agent_request, run_tool_calling_chat
from backend.agent.deepseek_client import DeepSeekClient, DeepSeekClientError
from backend.agent.response_parser import parse_ai_response
from backend.agent.context_manager import TokenBudgetConfig
from backend.agent.tool_calling import build_default_tool_registry
from backend.agent.usage_ledger import record_usage, summarize_session_usage
from backend.config import get_settings
from backend.db.database import get_db_session, session_factory
from backend.db.models import ChatMessage, ChatSession, utc_now
from backend.schemas import (
    ChatMessageCreateSchema,
    ChatMessageSchema,
    ChatSessionCreateSchema,
    ChatSessionSchema,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

DEFAULT_SESSION_TITLE = "默认对话"
UNTITLED_SESSION_TITLE = "新对话"


class ChatReplyRequestSchema(BaseModel):
    sessionId: int | None = None
    userInput: str | None = None
    messages: list[dict[str, Any]] | None = None
    model: str | None = None
    thinking: dict[str, Any] | None = None
    fileIds: list[int] = Field(default_factory=list)


class ChatReplyResponseSchema(BaseModel):
    text: str
    suggestion: dict[str, Any] | None = None
    proposal: dict[str, Any] | None = None


class ChatBackgroundRequestSchema(BaseModel):
    sessionId: int | None = None
    userInput: str | None = None
    messages: list[dict[str, Any]] | None = None
    model: str | None = None
    thinking: dict[str, Any] | None = None
    fileIds: list[int] = Field(default_factory=list)


class ChatBackgroundSubmitResponseSchema(BaseModel):
    task_id: str


class ChatBackgroundTaskResponseSchema(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] | None = None
    message: str = ""


background_worker: BackgroundWorker | None = None


def get_deepseek_client() -> DeepSeekClient:
    settings = get_settings()
    return DeepSeekClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=settings.deepseek_timeout_seconds,
    )


def initialize_background_worker(
    worker: BackgroundWorker | None = None,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    client_factory: Any = get_deepseek_client,
    default_model: str | None = None,
) -> None:
    global background_worker

    if worker is not None or session_factory is None:
        background_worker = worker
        return

    settings = get_settings()
    background_worker = BackgroundWorker(
        session_factory=session_factory,
        client_factory=client_factory,
        default_model=default_model or settings.default_model,
    )


def get_background_worker() -> BackgroundWorker:
    global background_worker

    if background_worker is None:
        settings = get_settings()
        background_worker = BackgroundWorker(
            session_factory=session_factory,
            client_factory=get_deepseek_client,
            default_model=settings.default_model,
        )

    return background_worker


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


async def get_or_create_default_chat_session(session: AsyncSession) -> ChatSession:
    chat_session = await find_default_session(session)
    if chat_session is not None:
        return chat_session

    now = utc_now()
    chat_session = ChatSession(
        title=DEFAULT_SESSION_TITLE,
        created_at=now,
        updated_at=now,
    )
    session.add(chat_session)
    await session.flush()
    return chat_session


async def resolve_chat_session(session_id: int | None, session: AsyncSession) -> ChatSession:
    if session_id is None:
        return await get_or_create_default_chat_session(session)

    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return chat_session


def read_last_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()

    raise HTTPException(status_code=422, detail="messages 中必须包含非空 user 消息")


def read_user_input(user_input: str | None) -> str | None:
    if user_input is None:
        return None

    stripped = user_input.strip()
    if not stripped:
        raise HTTPException(status_code=422, detail="userInput 不能为空")
    return stripped


def read_payload_user_content(payload: ChatReplyRequestSchema) -> str:
    direct_user_input = read_user_input(payload.userInput)
    if direct_user_input is not None:
        return direct_user_input

    if payload.messages is None:
        raise HTTPException(status_code=422, detail="必须提供 userInput 或 messages")

    return read_last_user_message(payload.messages)


def parse_messages_query(raw_messages: str) -> list[dict[str, Any]]:
    try:
        messages = json.loads(raw_messages)
    except JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="messages 必须是 JSON 字符串") from exc

    if not isinstance(messages, list):
        raise HTTPException(status_code=422, detail="messages 必须是数组")

    for message in messages:
        if not isinstance(message, dict):
            raise HTTPException(status_code=422, detail="messages 中每一项都必须是对象")

    return messages


def parse_file_ids_query(raw_file_ids: list[str] | None) -> list[int]:
    if not raw_file_ids:
        return []

    values: list[int] = []
    for item in raw_file_ids:
        for part in str(item).split(","):
            stripped = part.strip()
            if not stripped:
                continue
            try:
                values.append(int(stripped))
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="fileIds 必须是整数列表") from exc
    return list(dict.fromkeys(value for value in values if value > 0))


def build_sse_frame(event: str, payload: dict[str, Any]) -> str:
    # SSE 的 data 始终写 JSON，前端只需要按 event 名称分派，不解析 DeepSeek 原始协议。
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_error_payload(error: Exception) -> dict[str, Any]:
    if isinstance(error, DeepSeekClientError):
        return {
            "code": error.code,
            "message": str(error),
        }

    if isinstance(error, HTTPException):
        return {
            "code": "invalid_request",
            "message": str(error.detail),
        }

    return {
        "code": "chat_stream_error",
        "message": "AI 教练暂时不可用，请稍后重试。",
    }


async def request_agent_tool_reply(
    *,
    deepseek_client: DeepSeekClient,
    messages: list[dict[str, Any]],
    model: str,
    session: AsyncSession,
    session_id: int,
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    if not hasattr(deepseek_client, "request_chat_with_usage"):
        content, _usage = await request_deepseek_reply_with_usage(
            deepseek_client=deepseek_client,
            messages=messages,
            model=model,
        )
        parsed_reply = parse_ai_response(content)
        return parsed_reply["text"], parsed_reply["suggestion"], None

    tool_result = await run_tool_calling_chat(
        session=session,
        session_id=session_id,
        messages=messages,
        model=model,
        deepseek_client=deepseek_client,
        registry=build_default_tool_registry(),
    )
    parsed_reply = parse_ai_response(tool_result.content)
    proposal = tool_result.proposals[-1] if tool_result.proposals else None
    return parsed_reply["text"], parsed_reply["suggestion"], proposal


async def persist_successful_chat_turn(
    *,
    chat_session: ChatSession,
    session: AsyncSession,
    user_content: str,
    assistant_text: str,
    suggestion: dict[str, Any] | None,
    model: str | None = None,
    usage: dict[str, Any] | None = None,
) -> None:
    now = utc_now()
    # 流式阶段不写半截 assistant；只有拿到完整回复并解析成功后，才把本轮 user + assistant 一起落库。
    user_message = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=user_content,
        suggestion=None,
        created_at=now,
    )
    assistant_message = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content=assistant_text,
        suggestion=suggestion,
        created_at=now,
    )
    session.add_all([user_message, assistant_message])
    await session.flush()
    if model is not None and usage is not None:
        await record_usage(
            session,
            session_id=chat_session.id,
            message_id=assistant_message.id,
            model=model,
            usage=usage,
        )
    chat_session.updated_at = now
    await session.commit()


async def request_deepseek_reply_with_usage(
    *,
    deepseek_client: DeepSeekClient,
    messages: list[dict[str, Any]],
    model: str,
) -> tuple[str, dict[str, Any] | None]:
    if hasattr(deepseek_client, "request_chat_with_usage"):
        result = await deepseek_client.request_chat_with_usage(
            messages=messages,
            model=model,
            stream=False,
        )
        return result.content, result.usage

    content = await deepseek_client.request_chat(
        messages=messages,
        model=model,
        stream=False,
    )
    if not isinstance(content, str):
        raise DeepSeekClientError(
            "DeepSeek 非流式响应格式异常，请稍后重试。",
            code="invalid_response",
        )
    return content, None


async def stream_deepseek_reply_with_usage(
    *,
    deepseek_client: DeepSeekClient,
    messages: list[dict[str, Any]],
    model: str,
) -> AsyncIterator[tuple[str | None, dict[str, Any] | None]]:
    if hasattr(deepseek_client, "stream_chat_with_usage"):
        async for event in deepseek_client.stream_chat_with_usage(
            messages=messages,
            model=model,
        ):
            yield (event.text or None, event.usage)
        return

    async for chunk in deepseek_client.stream_chat(
        messages=messages,
        model=model,
    ):
        yield chunk, None


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
        title=payload.title or UNTITLED_SESSION_TITLE,
        created_at=now,
        updated_at=now,
    )
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)
    return build_session_response(chat_session)


@router.get("/sessions/default", response_model=ChatSessionSchema, response_model_by_alias=True)
async def get_or_create_default_session(session: AsyncSession = Depends(get_db_session)) -> ChatSessionSchema:
    # 默认会话承接旧版单条 chatHistory；真实多会话选择留给后续 UI 版本。
    chat_session = await get_or_create_default_chat_session(session)
    await session.commit()
    await session.refresh(chat_session)
    return build_session_response(chat_session)


@router.get("/stream")
async def stream_chat_reply(
    messages: str | None = None,
    user_input: str | None = Query(default=None, alias="userInput"),
    session_id: int | None = None,
    model: str | None = None,
    file_ids: list[str] | None = Query(default=None, alias="fileIds"),
    deepseek_client: DeepSeekClient = Depends(get_deepseek_client),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    chat_session = await resolve_chat_session(session_id, session)
    settings = get_settings()
    selected_model = model or settings.default_model
    direct_user_input = read_user_input(user_input)
    selected_file_ids = parse_file_ids_query(file_ids)

    if direct_user_input is not None:
        user_content = direct_user_input
        agent_request = await build_agent_request(
            session=session,
            session_id=chat_session.id,
            user_input=user_content,
            file_ids=selected_file_ids,
            model_config={"model": selected_model},
        )
        request_messages = agent_request.messages
    else:
        if messages is None:
            raise HTTPException(status_code=422, detail="必须提供 userInput 或 messages")
        request_messages = parse_messages_query(messages)
        user_content = read_last_user_message(request_messages)

    async def event_stream() -> AsyncIterator[str]:
        chunks: list[str] = []
        usage: dict[str, Any] | None = None

        try:
            if direct_user_input is not None:
                assistant_text, suggestion, proposal = await request_agent_tool_reply(
                    deepseek_client=deepseek_client,
                    messages=request_messages,
                    model=selected_model,
                    session=session,
                    session_id=chat_session.id,
                )
                if assistant_text:
                    yield build_sse_frame("delta", {"text": assistant_text})
                await persist_successful_chat_turn(
                    chat_session=chat_session,
                    session=session,
                    user_content=user_content,
                    assistant_text=assistant_text,
                    suggestion=proposal or suggestion,
                    model=selected_model,
                    usage=None,
                )
                if proposal is not None:
                    yield build_sse_frame("proposal", {"proposal": proposal})
                yield build_sse_frame("suggestion", {"suggestion": suggestion})
                yield build_sse_frame("done", {"text": assistant_text})
                return

            async for chunk, event_usage in stream_deepseek_reply_with_usage(
                deepseek_client=deepseek_client,
                messages=request_messages,
                model=selected_model,
            ):
                if event_usage is not None:
                    usage = event_usage
                    continue
                if chunk is None:
                    continue
                chunks.append(chunk)
                yield build_sse_frame("delta", {"text": chunk})

            parsed_reply = parse_ai_response("".join(chunks))
            assistant_text = parsed_reply["text"]
            suggestion = parsed_reply["suggestion"]
            await persist_successful_chat_turn(
                chat_session=chat_session,
                session=session,
                user_content=user_content,
                assistant_text=assistant_text,
                suggestion=suggestion,
                model=selected_model,
                usage=usage,
            )

            yield build_sse_frame("suggestion", {"suggestion": suggestion})
            yield build_sse_frame("done", {"text": assistant_text})
        except Exception as exc:
            await session.rollback()
            yield build_sse_frame("error", build_error_payload(exc))

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post(
    "/reply",
    response_model=ChatReplyResponseSchema,
    response_model_by_alias=True,
)
async def request_chat_reply(
    payload: ChatReplyRequestSchema,
    deepseek_client: DeepSeekClient = Depends(get_deepseek_client),
    session: AsyncSession = Depends(get_db_session),
) -> ChatReplyResponseSchema:
    user_content = read_payload_user_content(payload)
    chat_session = await resolve_chat_session(payload.sessionId, session)
    settings = get_settings()
    selected_model = payload.model or settings.default_model
    if payload.userInput is not None:
        agent_request = await build_agent_request(
            session=session,
            session_id=chat_session.id,
            user_input=user_content,
            file_ids=payload.fileIds,
            model_config={"model": selected_model},
        )
        request_messages = agent_request.messages
    else:
        if payload.messages is None:
            raise HTTPException(status_code=422, detail="必须提供 userInput 或 messages")
        request_messages = payload.messages

    try:
        proposal = None
        usage = None
        if payload.userInput is not None:
            assistant_text, suggestion, proposal = await request_agent_tool_reply(
                deepseek_client=deepseek_client,
                messages=request_messages,
                model=selected_model,
                session=session,
                session_id=chat_session.id,
            )
        else:
            content, usage = await request_deepseek_reply_with_usage(
                deepseek_client=deepseek_client,
                messages=request_messages,
                model=selected_model,
            )
            parsed_reply = parse_ai_response(content)
            assistant_text = parsed_reply["text"]
            suggestion = parsed_reply["suggestion"]

        await persist_successful_chat_turn(
            chat_session=chat_session,
            session=session,
            user_content=user_content,
            assistant_text=assistant_text,
            suggestion=proposal or suggestion,
            model=selected_model,
            usage=usage,
        )
        return ChatReplyResponseSchema(
            text=assistant_text,
            suggestion=suggestion,
            proposal=proposal,
        )
    except DeepSeekClientError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def build_background_task_response(record: BackgroundTaskRecord) -> ChatBackgroundTaskResponseSchema:
    return ChatBackgroundTaskResponseSchema(
        task_id=record.task_id,
        status=record.status,
        result=record.result,
        message=record.message,
    )


@router.post(
    "/{session_id}/background",
    response_model=ChatBackgroundSubmitResponseSchema,
)
async def submit_background_chat_task(
    session_id: int,
    payload: ChatBackgroundRequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> ChatBackgroundSubmitResponseSchema:
    user_content = read_user_input(payload.userInput)
    chat_session = await resolve_chat_session(session_id, session)
    if user_content is None:
        if payload.messages is None:
            raise HTTPException(status_code=422, detail="必须提供 userInput 或 messages")
        user_content = read_last_user_message(payload.messages)
        request_messages = payload.messages
    else:
        settings = get_settings()
        selected_model = payload.model or settings.default_model
        agent_request = await build_agent_request(
            session=session,
            session_id=chat_session.id,
            user_input=user_content,
            file_ids=payload.fileIds,
            model_config={"model": selected_model},
        )
        request_messages = agent_request.messages
    worker = get_background_worker()
    record = await worker.submit(
        session_id=session_id,
        messages=request_messages,
        user_content=user_content,
        model=payload.model,
    )
    return ChatBackgroundSubmitResponseSchema(task_id=record.task_id)


@router.get(
    "/background/{task_id}",
    response_model=ChatBackgroundTaskResponseSchema,
)
async def get_background_chat_task(task_id: str) -> ChatBackgroundTaskResponseSchema:
    return build_background_task_response(get_background_worker().get(task_id))


@router.get("/sessions/{session_id}/context/debug")
async def get_chat_context_debug(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    budget = TokenBudgetConfig()
    return {
        "sessionId": session_id,
        "usageSummary": await summarize_session_usage(session, session_id),
        "tokenBudget": {
            "max_context_tokens": budget.max_context_tokens,
            "reserved_response_tokens": budget.reserved_response_tokens,
            "available_for_prompt": budget.available_for_prompt,
            "warning_ratio": budget.warning_ratio,
            "compression_trigger_ratio": budget.compression_trigger_ratio,
            "hard_trim_ratio": budget.hard_trim_ratio,
        },
        "lastContext": None,
    }


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
