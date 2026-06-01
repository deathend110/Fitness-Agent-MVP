from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
import json
from json import JSONDecodeError
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.context_manager import AgentContext, PromptAssembler, SummaryCompressor
from backend.agent.tool_loop import ToolLoopOrchestrator, ToolLoopResult
from backend.agent.deepseek_client import (
    DeepSeekChatResult,
    DeepSeekClient,
    DeepSeekClientError,
    DeepSeekStreamEvent,
)
from backend.agent.memory import MemoryRetriever
from backend.agent.tool_calling import ToolRegistry, ToolResultSlimmer
from backend.providers.gemini_client import GeminiNativeClient
from backend.providers.base import (
    build_responses_followup_messages as build_base_responses_followup_messages,
    convert_messages_to_responses_input as build_base_responses_input,
    normalize_responses_tool_call_response,
    read_responses_output_text as read_base_responses_output_text,
    stringify_tool_result as stringify_base_tool_result,
)
from backend.providers.gemini_native import GeminiNativeProvider
from backend.providers.openai_compatible import OpenAICompatibleProvider
from backend.db.models import (
    ChatMessage,
    ChatSessionSummary,
    DailyLog,
    KnowledgeItem,
    MemoryItem,
    Profile,
    UploadedFile,
    WEEKDAY_ORDER,
    WeeklyPlanDay,
)
from backend.db.seed import DEFAULT_PROFILE_ID


@dataclass(frozen=True)
class AgentRequest:
    messages: list[dict[str, str]]
    debug: dict[str, Any]
    model: str | None = None


class OpenAICompatibleRuntimeClient:
    """按 wireApi/apiPathMode 驱动 OpenAI-compatible provider 的最小聊天客户端。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float = 30.0,
        wire_api: str = "chat_completions",
        api_path_mode: str = "raw_root",
        provider_label: str = "",
        client_factory=httpx.AsyncClient,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout = timeout
        self.wire_api = str(wire_api or "chat_completions").strip() or "chat_completions"
        self.api_path_mode = str(api_path_mode or "raw_root").strip() or "raw_root"
        self.provider_label = str(provider_label or "").strip()
        self.client_factory = client_factory
        self.runtime_wire_api = self.wire_api

    async def request_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> str | AsyncIterator[str]:
        if self.wire_api == "responses":
            if stream:
                return self.stream_chat(
                    messages=messages,
                    model=model,
                    thinking=thinking,
                    tools=tools,
                    tool_choice=tool_choice,
                    reasoning_effort=reasoning_effort,
                )
            payload = await self.request_responses_with_usage(
                input_items=build_base_responses_input(messages),
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )
            return read_base_responses_output_text(payload)

        if stream:
            return self.stream_chat(
                messages=messages,
                model=model,
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )

        result = await self.request_chat_with_usage(
            messages=messages,
            model=model,
            stream=False,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )
        return result.content

    async def request_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> DeepSeekChatResult:
        if self.wire_api == "responses":
            payload = await self.request_responses_with_usage(
                input_items=build_base_responses_input(messages),
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )
            text = read_base_responses_output_text(payload)
            tool_calls = read_responses_tool_calls(payload)
            if not text and not tool_calls:
                raise DeepSeekClientError(
                    f"{self._display_name()} 已返回成功响应，但没有可展示的消息内容。",
                    code="empty_content",
                )
            return DeepSeekChatResult(content=text, usage=read_openai_usage_payload(payload), tool_calls=tool_calls)

        if stream:
            raise DeepSeekClientError(
                "带 usage 的非流式请求不能启用 stream=True，请使用 stream_chat_with_usage。",
                code="invalid_request",
            )

        self._assert_api_key()
        payload = self._build_chat_completions_payload(
            messages=messages,
            model=model,
            stream=False,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )
        response_payload = await self._post_json(self._build_chat_completions_url(), payload)
        content = self._read_chat_message_content(response_payload)
        tool_calls = self._read_chat_tool_calls(response_payload)
        if not content and not tool_calls:
            raise DeepSeekClientError(
                f"{self._display_name()} 已返回成功响应，但没有可展示的消息内容。",
                code="empty_content",
            )
        return DeepSeekChatResult(
            content=content,
            usage=read_openai_usage_payload(response_payload),
            reasoning_content=self._read_chat_reasoning_content(response_payload),
            tool_calls=tool_calls,
        )

    async def stream_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[str]:
        async for event in self.stream_chat_with_usage(
            messages=messages,
            model=model,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        ):
            if event.text:
                yield event.text

    async def stream_chat_with_usage(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[DeepSeekStreamEvent]:
        if self.wire_api == "responses":
            payload = await self.request_responses_with_usage(
                input_items=build_base_responses_input(messages),
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                thinking=thinking,
                reasoning_effort=reasoning_effort,
            )
            text = read_base_responses_output_text(payload)
            if not text:
                raise DeepSeekClientError(
                    f"{self._display_name()} 已返回成功响应，但没有可展示的消息内容。",
                    code="empty_content",
                )
            yield DeepSeekStreamEvent(text=text)
            usage = read_openai_usage_payload(payload)
            if usage is not None:
                yield DeepSeekStreamEvent(usage=usage)
            return

        self._assert_api_key()
        payload = self._build_chat_completions_payload(
            messages=messages,
            model=model,
            stream=True,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )

        try:
            async with self.client_factory(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self._build_chat_completions_url(),
                    json=payload,
                    headers=self._build_headers(),
                ) as response:
                    self._raise_for_error_response(response)

                    saw_done = False
                    yielded_text = False
                    usage: dict[str, int] | None = None

                    async for raw_line in response.aiter_lines():
                        data = self._parse_sse_data_line(raw_line)
                        if data is None:
                            continue
                        if data == "[DONE]":
                            saw_done = True
                            break
                        try:
                            event = json.loads(data)
                        except JSONDecodeError as exc:
                            raise DeepSeekClientError(
                                f"{self._display_name()} 流式响应解析失败，请稍后重试。",
                                code="stream_parse_error",
                            ) from exc

                        event_usage = read_openai_usage_payload(event)
                        if event_usage is not None:
                            usage = event_usage

                        delta = self._read_chat_delta_content(event)
                        if not delta:
                            continue

                        yielded_text = True
                        yield DeepSeekStreamEvent(text=delta)
        except httpx.HTTPError as exc:
            raise DeepSeekClientError(
                f"{self._display_name()} 流式请求失败：{exc}",
                code="network_error",
            ) from exc

        if not saw_done:
            raise DeepSeekClientError(
                f"{self._display_name()} 流式响应在完成前中断，请稍后重试。",
                code="stream_interrupted",
            )
        if not yielded_text:
            raise DeepSeekClientError(
                f"{self._display_name()} 流式响应已结束，但没有返回可展示的消息内容。",
                code="empty_content",
            )
        if usage is not None:
            yield DeepSeekStreamEvent(usage=usage)

    async def request_responses_with_usage(
        self,
        *,
        input_items: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        self._assert_api_key()
        payload: dict[str, Any] = {
            "model": model,
            "input": input_items,
        }
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if reasoning_effort is not None:
            payload["reasoning"] = {"effort": reasoning_effort}
        elif thinking and thinking.get("type") == "enabled":
            payload["reasoning"] = {"effort": "medium"}
        response_payload = await self._post_json(self._build_responses_url(), payload)
        if not isinstance(response_payload, dict):
            raise DeepSeekClientError(
                f"{self._display_name()} 响应格式异常，请稍后重试。",
                code="invalid_response",
            )
        return response_payload

    def _display_name(self) -> str:
        if self.provider_label:
            return self.provider_label
        lowered = self.base_url.lower()
        if "openai.com" in lowered:
            return "OpenAI"
        if "deepseek.com" in lowered:
            return "DeepSeek"
        return "OpenAI-compatible 服务"

    def _assert_api_key(self) -> None:
        if self.api_key:
            return
        raise DeepSeekClientError(
            f"未配置 {self._display_name()} API Key，请先在模型设置中填写有效凭据。",
            code="missing_api_key",
            reason="missing_api_key",
        )

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_api_url(self, endpoint: str) -> str:
        base = self.base_url.rstrip("/")
        if self.api_path_mode == "append_v1" and not base.endswith("/v1"):
            return f"{base}/v1/{endpoint}"
        return f"{base}/{endpoint}"

    def _build_chat_completions_url(self) -> str:
        return self._build_api_url("chat/completions")

    def _build_responses_url(self) -> str:
        return self._build_api_url("responses")

    def _build_chat_completions_payload(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool,
        thinking: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if thinking is not None:
            payload["thinking"] = thinking
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
        return payload

    async def _post_json(self, url: str, payload: dict[str, Any]) -> Any:
        try:
            async with self.client_factory(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._build_headers(),
                )
        except httpx.HTTPError as exc:
            raise DeepSeekClientError(
                f"{self._display_name()} 网络请求失败：{exc}",
                code="network_error",
            ) from exc

        self._raise_for_error_response(response)
        return self._read_json_payload(response)

    def _raise_for_error_response(self, response: Any) -> None:
        if getattr(response, "is_success", False):
            return
        status = getattr(response, "status_code", None)
        reason = self._read_error_detail(response)
        reason_text = f"：{reason}" if reason else ""
        raise DeepSeekClientError(
            f"{self._display_name()} 请求失败（HTTP {status}）{reason_text}",
            status=status,
            code="http_error",
            reason=reason,
        )

    def _read_json_payload(self, response: Any) -> Any:
        try:
            return response.json()
        except Exception as exc:
            reason = str(exc).strip()
            reason_text = f"：{reason}" if reason else ""
            raise DeepSeekClientError(
                f"{self._display_name()} 响应解析失败{reason_text}",
                code="response_parse_error",
                reason=reason,
            ) from exc

    @staticmethod
    def _read_error_detail(response: Any) -> str:
        try:
            payload = response.json()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"].strip()
            if isinstance(payload.get("message"), str):
                return payload["message"].strip()
        reason_phrase = getattr(response, "reason_phrase", "")
        return reason_phrase.strip() if isinstance(reason_phrase, str) else ""

    @staticmethod
    def _parse_sse_data_line(line: str) -> str | None:
        trimmed = line.strip()
        if not trimmed or trimmed.startswith(":") or not trimmed.startswith("data:"):
            return None
        return trimmed[5:].strip()

    @staticmethod
    def _read_chat_message_content(payload: Any) -> str:
        message = OpenAICompatibleRuntimeClient._read_first_chat_message(payload)
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            blocks = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    blocks.append(text.strip())
            return "\n".join(blocks).strip()
        return ""

    @staticmethod
    def _read_chat_reasoning_content(payload: Any) -> str | None:
        message = OpenAICompatibleRuntimeClient._read_first_chat_message(payload)
        if not isinstance(message, dict):
            return None
        reasoning_content = message.get("reasoning_content")
        return reasoning_content if isinstance(reasoning_content, str) else None

    @staticmethod
    def _read_chat_tool_calls(payload: Any) -> list[dict[str, Any]] | None:
        message = OpenAICompatibleRuntimeClient._read_first_chat_message(payload)
        if not isinstance(message, dict):
            return None
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            return None
        return [item for item in tool_calls if isinstance(item, dict)]

    @staticmethod
    def _read_first_chat_message(payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None
        message = first_choice.get("message")
        return message if isinstance(message, dict) else None

    @staticmethod
    def _read_chat_delta_content(payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""
        delta = first_choice.get("delta")
        if not isinstance(delta, dict):
            return ""
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            blocks = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text:
                    blocks.append(text)
            return "".join(blocks)
        return ""


async def build_agent_request(
    *,
    session: AsyncSession,
    session_id: int,
    user_input: str,
    file_ids: list[int] | None = None,
    model_config: dict[str, Any] | None = None,
    assembler: PromptAssembler | None = None,
    compressor: SummaryCompressor | None = None,
) -> AgentRequest:
    active_assembler = assembler or PromptAssembler()
    if compressor is not None:
        await compressor.compress_if_needed(session, session_id=session_id)

    file_context = await _load_selected_file_summaries(session, file_ids or [])
    context = active_assembler.assemble(
        user_input=user_input,
        profile=await _load_profile(session),
        weekly_plan=await _load_weekly_plan(session),
        daily_logs=await _load_recent_daily_logs(session),
        recent_files_summary=file_context["summaries"],
        memories=await _load_memories(session),
        knowledge=await _load_knowledge(session),
        summaries=await _load_session_summaries(session, session_id),
        recent_messages=await _load_recent_messages(session, session_id),
    )
    return AgentRequest(
        messages=context.messages,
        debug={
            **context.debug,
            "source": "agent_orchestrator",
            "session_id": session_id,
            "selected_files": file_context["selected_files"],
            "missing_files": file_context["missing_files"],
            "trimmed_file_summaries": file_context["trimmed_file_summaries"],
        },
        model=(model_config or {}).get("model"),
    )


def read_openai_compatible_provider_wire_config(provider: Any | None) -> tuple[str, str]:
    wire_api = str(
        getattr(provider, "wire_api", None)
        or getattr(provider, "wireApi", None)
        or "chat_completions"
    ).strip() or "chat_completions"
    api_path_mode = str(
        getattr(provider, "api_path_mode", None)
        or getattr(provider, "apiPathMode", None)
        or "raw_root"
    ).strip() or "raw_root"
    return wire_api, api_path_mode


def read_runtime_client_wire_api(client: Any) -> str:
    """统一读取 runtime client 的显式协议，避免再用能力探测误判。"""

    explicit_wire_api = (
        getattr(client, "runtime_wire_api", None)
        or getattr(client, "wire_api", None)
        or getattr(client, "wireApi", None)
    )
    if explicit_wire_api is None:
        # 兼容旧测试替身或外部注入客户端：只有暴露 responses 能力且没有 chat-completions
        # usage 能力时，才把它兜底判定为 responses，避免误把双能力客户端路由错。
        if hasattr(client, "request_responses_with_usage") and not hasattr(client, "request_chat_with_usage"):
            return "responses"
        return "chat_completions"

    wire_api = str(explicit_wire_api).strip() or "chat_completions"
    return wire_api


def build_provider_bound_client(
    provider: Any | None,
    fallback_client: Any,
    *,
    timeout: float = 30.0,
) -> Any:
    """按 provider 类型与 wire 配置选择真正的聊天客户端。"""

    if not isinstance(fallback_client, DeepSeekClient):
        return fallback_client

    if provider is None:
        return fallback_client

    provider_type = getattr(provider, "type", "")
    api_key = str(getattr(provider, "api_key", "") or "").strip()
    base_url = str(getattr(provider, "base_url", "") or "").strip()
    provider_label = str(getattr(provider, "label", "") or "").strip()
    if not api_key or not base_url:
        return fallback_client

    if provider_type == "gemini_native":
        return GeminiNativeClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    if provider_type != "openai_compatible":
        return fallback_client

    wire_api, api_path_mode = read_openai_compatible_provider_wire_config(provider)
    lowered_base_url = base_url.lower()
    is_legacy_deepseek = (
        "deepseek.com" in lowered_base_url
        and wire_api == "chat_completions"
        and api_path_mode == "raw_root"
    )
    if is_legacy_deepseek:
        return DeepSeekClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    return OpenAICompatibleRuntimeClient(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        wire_api=wire_api,
        api_path_mode=api_path_mode,
        provider_label=provider_label,
    )


def provider_client_supports_tool_loop(client: Any) -> bool:
    wire_api = read_runtime_client_wire_api(client)
    if wire_api == "responses":
        return hasattr(client, "request_responses_with_usage")
    return hasattr(client, "request_chat_with_usage")


def convert_messages_to_responses_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_base_responses_input(messages)


def read_responses_output_text(payload: Any) -> str:
    return read_base_responses_output_text(payload)


def read_responses_tool_calls(payload: Any) -> list[dict[str, Any]] | None:
    if not isinstance(payload, dict):
        return None
    output = payload.get("output")
    if not isinstance(output, list):
        return None

    tool_calls: list[dict[str, Any]] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "function_call":
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        tool_calls.append(
            {
                "id": str(item.get("call_id") or item.get("id") or name),
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": item.get("arguments") or "{}",
                },
            }
        )
    return tool_calls or None


def read_openai_usage_payload(payload: Any) -> dict[str, int] | None:
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None

    def _to_non_negative_int(value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int | float):
            return max(0, int(value))
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return 0

    prompt_tokens = _to_non_negative_int(usage.get("prompt_tokens") or usage.get("input_tokens"))
    completion_tokens = _to_non_negative_int(
        usage.get("completion_tokens") or usage.get("output_tokens")
    )
    total_tokens = _to_non_negative_int(usage.get("total_tokens"))
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def stringify_tool_result(tool_result: Any) -> str:
    return stringify_base_tool_result(tool_result)


async def run_tool_calling_chat(
    *,
    session: AsyncSession,
    session_id: int,
    messages: list[dict[str, Any]],
    model: str,
    deepseek_client: Any,
    registry: ToolRegistry,
    thinking: dict[str, Any] | None = None,
    reasoning_effort: str | None = None,
    max_tool_rounds: int = 4,
    slimmer: ToolResultSlimmer | None = None,
) -> ToolLoopResult:
    provider = _build_tool_loop_provider(deepseek_client)
    orchestrator = ToolLoopOrchestrator(
        registry=registry,
        max_rounds=max_tool_rounds,
        slimmer=slimmer,
    )
    return await orchestrator.run(
        session=session,
        session_id=session_id,
        provider=provider,
        messages=messages,
        model=model,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
        tool_choice=None if thinking and thinking.get("type") == "enabled" else "auto",
    )


def _build_tool_loop_provider(client: Any) -> Any:
    if isinstance(client, GeminiNativeClient):
        return _GeminiToolLoopProvider(client=client)
    if read_runtime_client_wire_api(client) == "responses":
        return _OpenAIResponsesToolLoopProvider(client=client)
    return _DeepSeekToolLoopProvider(client=client)


class _DeepSeekToolLoopProvider(OpenAICompatibleProvider):
    """把现有 DeepSeekClient 包装成统一 provider 接口，供新工具循环复用。"""

    def __init__(self, *, client: Any) -> None:
        super().__init__(client_factory=None)
        self.client = client

    async def generate_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]],
        tool_choice: str | dict[str, Any] | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        result: DeepSeekChatResult = await self.client.request_chat_with_usage(
            messages=messages,
            model=model,
            tools=tools,
            tool_choice=tool_choice,
            stream=False,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )
        raw_payload = {
            "choices": [
                {
                    "message": {
                        "content": result.content,
                        "tool_calls": result.tool_calls or [],
                    }
                }
            ]
        }
        if result.reasoning_content:
            raw_payload["choices"][0]["message"]["reasoning_content"] = result.reasoning_content
        return {
            "text": result.content,
            "toolCalls": result.tool_calls or [],
            "raw": raw_payload,
        }


class _OpenAIResponsesToolLoopProvider(OpenAICompatibleProvider):
    """把 Responses API 适配成统一工具回环协议。"""

    def __init__(self, *, client: Any) -> None:
        super().__init__(client_factory=None, wire_api="responses")
        self.client = client

    async def generate_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]],
        tool_choice: str | dict[str, Any] | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        payload = await self.client.request_responses_with_usage(
            input_items=build_base_responses_input(messages),
            model=model,
            tools=tools,
            tool_choice=tool_choice,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )
        return {
            "text": read_base_responses_output_text(payload),
            "toolCalls": self.normalize_tool_call_response(payload),
            "raw": payload,
        }

    def normalize_tool_call_response(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return normalize_responses_tool_call_response(payload)

    def build_followup_messages_after_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call: dict[str, Any],
        tool_result: Any,
    ) -> list[dict[str, Any]]:
        return build_base_responses_followup_messages(messages, tool_call, tool_result)


class _GeminiToolLoopProvider(GeminiNativeProvider):
    """把 Gemini 原生 REST client 接到统一工具回环里。"""

    def __init__(self, *, client: GeminiNativeClient) -> None:
        super().__init__(client_factory=None)
        self.client = client

    async def generate_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: dict[str, Any],
        tool_choice: str | dict[str, Any] | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        raw_payload = await self.client.generate_content_raw(
            messages=messages,
            model=model,
            thinking=thinking,
            tools=tools,
            tool_choice=tool_choice,
            reasoning_effort=reasoning_effort,
        )
        return {
            "text": self.client._read_text_content(raw_payload),
            "toolCalls": self.normalize_tool_call_response(raw_payload),
            "raw": raw_payload,
        }



async def _load_profile(session: AsyncSession) -> dict[str, Any] | None:
    profile = await session.get(Profile, DEFAULT_PROFILE_ID)
    if profile is None:
        return None
    return {
        "basic": profile.basic,
        "oneRm": profile.one_rm,
        "goal": profile.goal,
        "targetWeight": profile.target_weight,
        "notes": profile.notes,
    }


async def _load_weekly_plan(session: AsyncSession) -> dict[str, Any]:
    result = await session.execute(select(WeeklyPlanDay))
    days = {item.day_key: item for item in result.scalars().all()}
    return {
        day_key: {
            "type": days[day_key].type,
            "exercises": days[day_key].exercises,
        }
        for day_key in WEEKDAY_ORDER
        if day_key in days
    }


async def _load_recent_daily_logs(session: AsyncSession, limit: int = 7) -> dict[str, Any]:
    result = await session.execute(select(DailyLog).order_by(DailyLog.date.desc()).limit(limit))
    entries = list(result.scalars().all())
    return {
        entry.date: {
            "weight": entry.weight,
            "kcal": entry.kcal,
            "protein": entry.protein,
            "sleep": entry.sleep,
            "fatigue": entry.fatigue,
            "steps": entry.steps,
            "trainingDone": entry.training_done,
            "trainingNotes": entry.training_notes,
            "tdeeManual": entry.tdee_manual,
        }
        for entry in reversed(entries)
    }


async def _load_memories(session: AsyncSession, limit: int = 12) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "kind": item.kind,
            "content": item.content,
            "confidence": item.confidence,
        }
        for item in await MemoryRetriever().retrieve(session, limit=limit)
    ]


async def _load_knowledge(session: AsyncSession, limit: int = 5) -> list[dict[str, Any]]:
    result = await session.execute(select(KnowledgeItem).order_by(KnowledgeItem.id.desc()).limit(limit))
    return [
        {
            "id": item.id,
            "kind": item.kind,
            "title": item.title,
            "content": item.content,
        }
        for item in result.scalars().all()
    ]


async def _load_selected_file_summaries(session: AsyncSession, file_ids: list[int]) -> dict[str, Any]:
    if not file_ids:
        return {"summaries": [], "selected_files": [], "missing_files": [], "trimmed_file_summaries": []}

    unique_ids = list(dict.fromkeys(int(file_id) for file_id in file_ids if int(file_id) > 0))
    if not unique_ids:
        return {"summaries": [], "selected_files": [], "missing_files": [], "trimmed_file_summaries": []}

    result = await session.execute(select(UploadedFile).where(UploadedFile.id.in_(unique_ids)))
    files_by_id = {item.id: item for item in result.scalars().all()}
    summaries: list[dict[str, Any]] = []
    trimmed: list[int] = []

    for file_id in unique_ids:
        uploaded = files_by_id.get(file_id)
        if uploaded is None:
            continue
        summary = uploaded.summary or {}
        text = str(summary.get("summary") or summary.get("text") or "").strip()
        if len(text) > 800:
            text = text[:800] + "...[trimmed:file_summary]"
            trimmed.append(file_id)
        summaries.append(
            {
                "fileId": uploaded.id,
                "name": uploaded.original_name,
                "kind": summary.get("kind") or uploaded.extension.lstrip("."),
                "status": uploaded.parser_status,
                "summary": text,
            }
        )

    return {
        "summaries": summaries,
        "selected_files": [item["fileId"] for item in summaries],
        "missing_files": [file_id for file_id in unique_ids if file_id not in files_by_id],
        "trimmed_file_summaries": trimmed,
    }


async def _load_session_summaries(
    session: AsyncSession,
    session_id: int,
    limit: int = 2,
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(ChatSessionSummary)
        .where(ChatSessionSummary.session_id == session_id)
        .order_by(ChatSessionSummary.id.desc())
        .limit(limit)
    )
    return [
        {
            "id": item.id,
            "summary_text": item.summary_text,
            "token_estimate": item.token_estimate,
        }
        for item in reversed(result.scalars().all())
    ]


async def _load_recent_messages(
    session: AsyncSession,
    session_id: int,
    limit: int = 12,
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
    )
    return [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in reversed(result.scalars().all())
    ]
