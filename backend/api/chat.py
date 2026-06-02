from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
import json
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.agent.background_worker import BackgroundTaskRecord, BackgroundWorker
from backend.agent.chat_session import (
    build_agent_request,
    build_provider_bound_client,
    convert_messages_to_responses_input,
    provider_client_supports_tool_loop,
    read_openai_compatible_provider_wire_config,
    read_runtime_client_wire_api,
    read_responses_output_text,
    read_openai_usage_payload,
    run_tool_calling_chat,
)
from backend.agent.deepseek_client import DeepSeekClient, DeepSeekClientError
from backend.agent.proposal_text import finalize_assistant_text
from backend.agent.response_parser import parse_ai_response
from backend.agent.session_title import (
    DEFAULT_SESSION_TITLE,
    UNTITLED_SESSION_TITLE,
    update_session_title_from_user_prompt,
)
from backend.agent.context_manager import TokenBudgetConfig
from backend.agent.tool_calling import build_default_tool_registry
from backend.agent.tool_choice import (
    has_explicit_plan_proposal_intent,
    requires_structured_plan_proposal,
    resolve_tool_choice_for_request,
)
from backend.agent.usage_ledger import record_usage, summarize_session_usage
from backend.config import get_settings
from backend.db.database import get_db_session, session_factory
from backend.db.models import ChatMessage, ChatSession, UploadedFile, utc_now
from backend.model_config.runtime import get_provider_runtime
from backend.schemas import (
    ChatMessageCreateSchema,
    ChatMessageSchema,
    ChatSessionCreateSchema,
    ChatSessionSchema,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

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


@dataclass(frozen=True)
class NormalizedChatRequest:
    session_id: int | None
    user_content: str
    model: str | None
    file_ids: list[int]
    thinking: dict[str, Any] | None
    source: str
    messages: list[dict[str, Any]] | None = None


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
    runtime_provider: Any | None = None,
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
        runtime_provider=runtime_provider or get_provider_runtime,
    )


def get_background_worker() -> BackgroundWorker:
    global background_worker

    if background_worker is None:
        settings = get_settings()
        background_worker = BackgroundWorker(
            session_factory=session_factory,
            client_factory=get_deepseek_client,
            default_model=settings.default_model,
            runtime_provider=get_provider_runtime,
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
        attachments=message.attachments or [],
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


def normalize_chat_request_payload(
    payload: ChatReplyRequestSchema | ChatBackgroundRequestSchema,
) -> NormalizedChatRequest:
    """把 Agent 新契约和 legacy messages 契约归一到统一内部结构。"""

    direct_user_input = read_user_input(payload.userInput)
    if direct_user_input is not None:
        return NormalizedChatRequest(
            session_id=payload.sessionId,
            user_content=direct_user_input,
            model=payload.model,
            file_ids=list(dict.fromkeys(file_id for file_id in payload.fileIds if file_id > 0)),
            thinking=payload.thinking,
            source="agent",
            messages=None,
        )

    if payload.messages is None:
        raise HTTPException(status_code=422, detail="必须提供 userInput 或 messages")

    return NormalizedChatRequest(
        session_id=payload.sessionId,
        user_content=read_last_user_message(payload.messages),
        model=payload.model,
        file_ids=[],
        thinking=payload.thinking,
        source="legacy_messages",
        messages=payload.messages,
    )


def normalize_stream_chat_request(
    *,
    session_id: int | None,
    user_input: str | None,
    model: str | None,
    thinking: dict[str, Any] | None,
    file_ids: list[int],
    messages: list[dict[str, Any]] | None,
) -> NormalizedChatRequest:
    direct_user_input = read_user_input(user_input)
    if direct_user_input is not None:
        return NormalizedChatRequest(
            session_id=session_id,
            user_content=direct_user_input,
            model=model,
            file_ids=file_ids,
            thinking=thinking,
            source="agent",
            messages=None,
        )

    if messages is None:
        raise HTTPException(status_code=422, detail="必须提供 userInput 或 messages")

    return NormalizedChatRequest(
        session_id=session_id,
        user_content=read_last_user_message(messages),
        model=model,
        file_ids=[],
        thinking=thinking,
        source="legacy_messages",
        messages=messages,
    )


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


def build_uploaded_file_attachment_snapshot(uploaded_file: UploadedFile) -> dict[str, Any]:
    return {
        "fileId": uploaded_file.id,
        "originalName": uploaded_file.original_name,
        "mimeType": uploaded_file.mime_type,
        "extension": uploaded_file.extension,
        "sizeBytes": uploaded_file.size_bytes,
    }


async def build_message_attachment_snapshots(
    session: AsyncSession,
    file_ids: list[int],
) -> list[dict[str, Any]]:
    unique_ids = list(dict.fromkeys(file_id for file_id in file_ids if file_id > 0))
    if not unique_ids:
        return []

    result = await session.execute(select(UploadedFile).where(UploadedFile.id.in_(unique_ids)))
    files_by_id = {item.id: item for item in result.scalars().all()}
    attachments: list[dict[str, Any]] = []

    for file_id in unique_ids:
        uploaded_file = files_by_id.get(file_id)
        if uploaded_file is None:
            continue
        attachments.append(build_uploaded_file_attachment_snapshot(uploaded_file))

    return attachments


def parse_thinking_query(raw_thinking: str | None) -> dict[str, Any] | None:
    if raw_thinking is None or not raw_thinking.strip():
        return None
    try:
        parsed = json.loads(raw_thinking)
    except JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="thinking 必须是 JSON 对象") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="thinking 必须是 JSON 对象")
    return parsed


def normalize_deepseek_thinking(
    thinking: dict[str, Any] | None,
) -> tuple[dict[str, str] | None, str | None]:
    if thinking is None:
        return None, None

    enabled = bool(thinking.get("enabled"))
    if not enabled:
        return {"type": "disabled"}, None

    budget = str(thinking.get("budget") or "auto").lower()
    return {"type": "enabled"}, "max" if budget == "max" else "high"


def resolve_selected_chat_model(model: str | None) -> tuple[str, Any | None, str]:
    """把聊天入口收到的 model/modelRef 统一解析成可请求的远端模型 ID。"""

    runtime = get_provider_runtime()
    if model is None:
        selected_model = runtime.default_model_ref
    else:
        selected_model = model

    if "::" not in selected_model:
        return selected_model, None, selected_model

    provider, remote_model_id = runtime.resolve_model_ref(selected_model)
    return selected_model, provider, remote_model_id


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


def build_plan_proposal_retry_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """当模型偷懒输出文字卡片时，补一条系统纠偏消息强制它走 proposal 工具。"""

    retry_instruction = (
        "系统纠偏：用户本轮明确要求生成训练计划修改卡。"
        "你必须通过 proposal 工具返回结构化建议卡，"
        "不要输出 markdown 卡片、JSON 示例或口头确认。"
        "若需要替换整天计划，请调用 propose_day_plan_replace；"
        "若只修改部分动作，请调用 propose_plan_change。"
    )
    return [
        *messages,
        {
            "role": "system",
            "content": retry_instruction,
        },
    ]


async def request_agent_tool_reply(
    *,
    deepseek_client: DeepSeekClient,
    messages: list[dict[str, Any]],
    model: str,
    session: AsyncSession,
    session_id: int,
    user_content: str,
    thinking: dict[str, str] | None = None,
    reasoning_effort: str | None = None,
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    allow_proposal_tools = has_explicit_plan_proposal_intent(user_content)
    registry = build_default_tool_registry()
    if not allow_proposal_tools:
        # 只有用户本轮显式要求计划卡时，才向模型暴露 proposal 工具。
        registry = registry.filter_tool_names(
            {
                "get_profile",
                "get_weekly_plan",
                "get_daily_log",
                "calculate_metrics",
                "search_memory",
                "read_uploaded_file_summary",
            }
        )

    if not provider_client_supports_tool_loop(deepseek_client):
        content, _usage = await request_deepseek_reply_with_usage(
            deepseek_client=deepseek_client,
            messages=messages,
            model=model,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )
        parsed_reply = parse_ai_response(content)
        return parsed_reply["text"], parsed_reply["suggestion"], None

    tool_choice = resolve_tool_choice_for_request(
        user_content=user_content,
        provider_client=deepseek_client,
        thinking=thinking,
    )
    tool_result = await run_tool_calling_chat(
        session=session,
        session_id=session_id,
        messages=messages,
        model=model,
        deepseek_client=deepseek_client,
        registry=registry,
        tool_choice=tool_choice,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
    )
    parsed_reply = parse_ai_response(tool_result.content)
    proposal = tool_result.proposals[-1] if tool_result.proposals else None
    if proposal is None and requires_structured_plan_proposal(user_content):
        retry_tool_choice = resolve_tool_choice_for_request(
            user_content=user_content,
            provider_client=deepseek_client,
            thinking=thinking,
        )
        retry_result = await run_tool_calling_chat(
            session=session,
            session_id=session_id,
            messages=build_plan_proposal_retry_messages(messages),
            model=model,
            deepseek_client=deepseek_client,
            registry=registry,
            tool_choice=retry_tool_choice,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )
        retry_parsed_reply = parse_ai_response(retry_result.content)
        retry_proposal = retry_result.proposals[-1] if retry_result.proposals else None
        if retry_proposal is not None:
            return retry_parsed_reply["text"], retry_parsed_reply["suggestion"], retry_proposal
    return parsed_reply["text"], parsed_reply["suggestion"], proposal


def assert_required_plan_proposal(
    *,
    user_content: str,
    proposal: dict[str, Any] | None,
) -> None:
    if proposal is not None:
        return
    if not requires_structured_plan_proposal(user_content):
        return
    raise DeepSeekClientError(
        "本轮请求明确要求生成待确认计划卡，但模型没有通过工具返回结构化 proposal，请稍后重试或切换模型。",
        code="missing_plan_proposal",
    )


async def persist_successful_chat_turn(
    *,
    chat_session: ChatSession,
    session: AsyncSession,
    user_content: str,
    user_attachments: list[dict[str, Any]] | None,
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
        attachments=user_attachments or [],
        created_at=now,
    )
    assistant_message = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content=assistant_text,
        suggestion=suggestion,
        attachments=[],
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
    # 仅对“新对话”占位标题做一次性回填，默认会话仍保留自己的兼容语义。
    update_session_title_from_user_prompt(chat_session, user_content)
    chat_session.updated_at = now
    await session.commit()


async def request_deepseek_reply_with_usage(
    *,
    deepseek_client: DeepSeekClient,
    messages: list[dict[str, Any]],
    model: str,
    thinking: dict[str, str] | None = None,
    reasoning_effort: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    thinking_kwargs: dict[str, Any] = {}
    if thinking is not None:
        thinking_kwargs["thinking"] = thinking
    if reasoning_effort is not None:
        thinking_kwargs["reasoning_effort"] = reasoning_effort

    # 统一优先走 provider runtime 的 usage 接口，让 responses->chat_completions
    # 自动降级、工具协议差异和 usage 解析都收口在 runtime client 内部。
    if hasattr(deepseek_client, "request_chat_with_usage"):
        result = await deepseek_client.request_chat_with_usage(
            messages=messages,
            model=model,
            stream=False,
            **thinking_kwargs,
        )
        return result.content, result.usage

    if hasattr(deepseek_client, "request_responses_with_usage"):
        result = await deepseek_client.request_responses_with_usage(
            input_items=convert_messages_to_responses_input(messages),
            model=model,
            **thinking_kwargs,
        )
        if isinstance(result, dict):
            output_text = read_responses_output_text(result)
            if output_text:
                return output_text, read_openai_usage_payload(result)

    content = await deepseek_client.request_chat(
        messages=messages,
        model=model,
        stream=False,
        **thinking_kwargs,
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
    thinking: dict[str, str] | None = None,
    reasoning_effort: str | None = None,
) -> AsyncIterator[tuple[str | None, dict[str, Any] | None]]:
    thinking_kwargs: dict[str, Any] = {}
    if thinking is not None:
        thinking_kwargs["thinking"] = thinking
    if reasoning_effort is not None:
        thinking_kwargs["reasoning_effort"] = reasoning_effort

    # 流式链路同样统一优先走 runtime client，避免 API 层直接调 responses
    # 时绕开中转站异常恢复与协议降级逻辑。
    if hasattr(deepseek_client, "stream_chat_with_usage"):
        async for event in deepseek_client.stream_chat_with_usage(
            messages=messages,
            model=model,
            **thinking_kwargs,
        ):
            yield (event.text or None, event.usage)
        return

    if hasattr(deepseek_client, "request_responses_with_usage"):
        result = await deepseek_client.request_responses_with_usage(
            input_items=convert_messages_to_responses_input(messages),
            model=model,
            **thinking_kwargs,
        )
        if isinstance(result, dict):
            output_text = read_responses_output_text(result)
            if output_text:
                yield output_text, read_openai_usage_payload(result)
                return

    async for chunk in deepseek_client.stream_chat(
        messages=messages,
        model=model,
        **thinking_kwargs,
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


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    await session.delete(chat_session)
    await session.commit()
    return Response(status_code=204)


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
    thinking: str | None = None,
    file_ids: list[str] | None = Query(default=None, alias="fileIds"),
    deepseek_client: DeepSeekClient = Depends(get_deepseek_client),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    parsed_messages = parse_messages_query(messages) if messages is not None else None
    thinking_query = parse_thinking_query(thinking)
    normalized_request = normalize_stream_chat_request(
        session_id=session_id,
        user_input=user_input,
        model=model,
        thinking=thinking_query,
        file_ids=parse_file_ids_query(file_ids),
        messages=parsed_messages,
    )
    chat_session = await resolve_chat_session(normalized_request.session_id, session)
    selected_model_ref, selected_provider, remote_model_id = resolve_selected_chat_model(
        normalized_request.model
    )
    provider_client = build_provider_bound_client(
        selected_provider,
        deepseek_client,
        timeout=get_settings().deepseek_timeout_seconds,
    )
    thinking_payload, reasoning_effort = normalize_deepseek_thinking(normalized_request.thinking)
    user_attachments: list[dict[str, Any]] = []

    if normalized_request.source == "agent":
        user_attachments = await build_message_attachment_snapshots(
            session, normalized_request.file_ids
        )
        agent_request = await build_agent_request(
            session=session,
            session_id=chat_session.id,
            user_input=normalized_request.user_content,
            file_ids=normalized_request.file_ids,
            model_config={"model": selected_model_ref},
        )
        request_messages = agent_request.messages
    else:
        request_messages = normalized_request.messages or []

    user_content = normalized_request.user_content

    async def event_stream() -> AsyncIterator[str]:
        chunks: list[str] = []
        usage: dict[str, Any] | None = None

        try:
            if normalized_request.source == "agent":
                assistant_text, suggestion, proposal = await request_agent_tool_reply(
                    deepseek_client=provider_client,
                    messages=request_messages,
                    model=remote_model_id,
                    session=session,
                    session_id=chat_session.id,
                    user_content=user_content,
                    thinking=thinking_payload,
                    reasoning_effort=reasoning_effort,
                )
                assert_required_plan_proposal(user_content=user_content, proposal=proposal)
                assistant_text = finalize_assistant_text(assistant_text, proposal)
                if assistant_text:
                    yield build_sse_frame("delta", {"text": assistant_text})
                await persist_successful_chat_turn(
                    chat_session=chat_session,
                    session=session,
                    user_content=user_content,
                    user_attachments=user_attachments,
                    assistant_text=assistant_text,
                    suggestion=proposal or suggestion,
                    model=selected_model_ref,
                    usage=None,
                )
                if proposal is not None:
                    yield build_sse_frame("proposal", {"proposal": proposal})
                yield build_sse_frame("suggestion", {"suggestion": suggestion})
                yield build_sse_frame("done", {"text": assistant_text})
                return

            async for chunk, event_usage in stream_deepseek_reply_with_usage(
                deepseek_client=provider_client,
                messages=request_messages,
                model=remote_model_id,
                thinking=thinking_payload,
                reasoning_effort=reasoning_effort,
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
                user_attachments=user_attachments,
                assistant_text=assistant_text,
                suggestion=suggestion,
                model=selected_model_ref,
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
    normalized_request = normalize_chat_request_payload(payload)
    chat_session = await resolve_chat_session(normalized_request.session_id, session)
    selected_model_ref, selected_provider, remote_model_id = resolve_selected_chat_model(
        normalized_request.model
    )
    provider_client = build_provider_bound_client(
        selected_provider,
        deepseek_client,
        timeout=get_settings().deepseek_timeout_seconds,
    )
    thinking_payload, reasoning_effort = normalize_deepseek_thinking(normalized_request.thinking)
    user_attachments: list[dict[str, Any]] = []
    if normalized_request.source == "agent":
        user_attachments = await build_message_attachment_snapshots(
            session, normalized_request.file_ids
        )
        agent_request = await build_agent_request(
            session=session,
            session_id=chat_session.id,
            user_input=normalized_request.user_content,
            file_ids=normalized_request.file_ids,
            model_config={"model": selected_model_ref},
        )
        request_messages = agent_request.messages
    else:
        request_messages = normalized_request.messages or []
    user_content = normalized_request.user_content

    try:
        proposal = None
        usage = None
        if normalized_request.source == "agent":
            assistant_text, suggestion, proposal = await request_agent_tool_reply(
                deepseek_client=provider_client,
                messages=request_messages,
                model=remote_model_id,
                session=session,
                session_id=chat_session.id,
                user_content=user_content,
                thinking=thinking_payload,
                reasoning_effort=reasoning_effort,
            )
            assert_required_plan_proposal(user_content=user_content, proposal=proposal)
            assistant_text = finalize_assistant_text(assistant_text, proposal)
        else:
            content, usage = await request_deepseek_reply_with_usage(
                deepseek_client=provider_client,
                messages=request_messages,
                model=remote_model_id,
                thinking=thinking_payload,
                reasoning_effort=reasoning_effort,
            )
            parsed_reply = parse_ai_response(content)
            assistant_text = parsed_reply["text"]
            suggestion = parsed_reply["suggestion"]

        await persist_successful_chat_turn(
            chat_session=chat_session,
            session=session,
            user_content=user_content,
            user_attachments=user_attachments,
            assistant_text=assistant_text,
            suggestion=proposal or suggestion,
            model=selected_model_ref,
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
    normalized_request = normalize_chat_request_payload(payload)
    chat_session = await resolve_chat_session(session_id, session)
    user_attachments: list[dict[str, Any]] = []
    if normalized_request.source == "legacy_messages":
        request_messages = normalized_request.messages or []
    else:
        selected_model_ref = normalized_request.model
        user_attachments = await build_message_attachment_snapshots(
            session, normalized_request.file_ids
        )
        agent_request = await build_agent_request(
            session=session,
            session_id=chat_session.id,
            user_input=normalized_request.user_content,
            file_ids=normalized_request.file_ids,
            model_config={"model": selected_model_ref} if selected_model_ref is not None else None,
        )
        request_messages = agent_request.messages
    thinking_payload, reasoning_effort = normalize_deepseek_thinking(normalized_request.thinking)
    worker = get_background_worker()
    record = await worker.submit(
        session_id=session_id,
        messages=request_messages,
        user_content=normalized_request.user_content,
        user_attachments=user_attachments,
        model=normalized_request.model,
        thinking=thinking_payload,
        reasoning_effort=reasoning_effort,
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
        attachments=[attachment.model_dump(by_alias=True) for attachment in payload.attachments],
        created_at=now,
    )
    session.add(message)
    update_session_title_from_user_prompt(chat_session, payload.content if payload.role == "user" else "")
    # 新消息写入时同步触碰会话更新时间，列表页才能按最近对话排序。
    chat_session.updated_at = now
    await session.commit()
    await session.refresh(message)
    return build_message_response(message)
