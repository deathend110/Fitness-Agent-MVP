from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.agent.chat_session import run_tool_calling_chat
from backend.agent.deepseek_client import DeepSeekClient, DeepSeekClientError
from backend.agent.response_parser import parse_ai_response
from backend.agent.tool_calling import build_default_tool_registry
from backend.db.models import ChatMessage, ChatSession, utc_now

BackgroundTaskStatus = Literal["pending", "running", "succeeded", "failed", "not_found"]


@dataclass
class BackgroundTaskRecord:
    task_id: str
    session_id: int
    status: BackgroundTaskStatus = "pending"
    result: dict[str, Any] | None = None
    message: str = ""


class BackgroundWorker:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        client_factory: Callable[[], DeepSeekClient],
        default_model: str,
    ) -> None:
        self.session_factory = session_factory
        self.client_factory = client_factory
        self.default_model = default_model
        self._tasks: dict[str, BackgroundTaskRecord] = {}

    async def submit(
        self,
        *,
        session_id: int,
        messages: list[dict[str, Any]],
        user_content: str,
        model: str | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> BackgroundTaskRecord:
        task_id = uuid4().hex
        record = BackgroundTaskRecord(task_id=task_id, session_id=session_id)
        self._tasks[task_id] = record
        asyncio.create_task(
            self._run_task(
                record=record,
                messages=messages,
                user_content=user_content,
                model=model or self.default_model,
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )
        )
        return record

    def get(self, task_id: str) -> BackgroundTaskRecord:
        record = self._tasks.get(task_id)
        if record is not None:
            return record

        return BackgroundTaskRecord(
            task_id=task_id,
            session_id=0,
            status="not_found",
            result=None,
            message="未找到对应的后台思考任务。",
        )

    async def _run_task(
        self,
        *,
        record: BackgroundTaskRecord,
        messages: list[dict[str, Any]],
        user_content: str,
        model: str,
        thinking: dict[str, Any] | None,
        reasoning_effort: str | None,
    ) -> None:
        record.status = "running"

        try:
            client = self.client_factory()
            thinking_kwargs: dict[str, Any] = {}
            if thinking is not None:
                thinking_kwargs["thinking"] = thinking
            if reasoning_effort is not None:
                thinking_kwargs["reasoning_effort"] = reasoning_effort
            proposal: dict[str, Any] | None = None
            if hasattr(client, "request_chat_with_usage"):
                async with self.session_factory() as session:
                    # 后台任务也必须走同一套工具循环，否则离页后的计划卡片会退化成旧 suggestion。
                    tool_result = await run_tool_calling_chat(
                        session=session,
                        session_id=record.session_id,
                        messages=messages,
                        model=model,
                        deepseek_client=client,
                        registry=build_default_tool_registry(),
                        **thinking_kwargs,
                    )
                content = tool_result.content
                proposal = tool_result.proposals[-1] if tool_result.proposals else None
            else:
                content = await client.request_chat(
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
            if not content.strip():
                raise DeepSeekClientError(
                    "DeepSeek 已返回成功响应，但没有可展示的消息内容。",
                    code="empty_content",
                )

            parsed_reply = parse_ai_response(content)
            suggestion = proposal or parsed_reply["suggestion"]
            await self._persist_successful_chat_turn(
                session_id=record.session_id,
                user_content=user_content,
                assistant_text=parsed_reply["text"],
                suggestion=suggestion,
            )
            record.result = {
                "text": parsed_reply["text"],
                "suggestion": suggestion,
            }
            record.status = "succeeded"
            record.message = ""
        except Exception as exc:
            record.status = "failed"
            record.result = None
            record.message = self._build_failed_message(exc)

    async def _persist_successful_chat_turn(
        self,
        *,
        session_id: int,
        user_content: str,
        assistant_text: str,
        suggestion: dict[str, Any] | None,
    ) -> None:
        async with self.session_factory() as session:
            chat_session = await session.get(ChatSession, session_id)
            if chat_session is None:
                raise ValueError("Chat session not found")

            now = utc_now()
            # 后台任务离开请求生命周期后才写库，必须在自己的 DB session 中提交完整一轮对话。
            session.add_all(
                [
                    ChatMessage(
                        session_id=session_id,
                        role="user",
                        content=user_content,
                        suggestion=None,
                        created_at=now,
                    ),
                    ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=assistant_text,
                        suggestion=suggestion,
                        created_at=now,
                    ),
                ]
            )
            chat_session.updated_at = now
            await session.commit()

    def _build_failed_message(self, error: Exception) -> str:
        if isinstance(error, DeepSeekClientError):
            return str(error)

        return "后台 AI 教练任务执行失败，请稍后重试。"
