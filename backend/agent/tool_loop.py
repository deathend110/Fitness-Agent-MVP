from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.agent.tool_calling import ToolRegistry, ToolResultSlimmer
from backend.db.models import ToolCallLog, utc_now


@dataclass(frozen=True)
class ToolLoopResult:
    content: str
    messages: list[dict[str, Any]]
    tool_rounds: int
    proposals: list[dict[str, Any]]


class ToolLoopOrchestrator:
    def __init__(
        self,
        *,
        registry: ToolRegistry,
        max_rounds: int = 4,
        slimmer: ToolResultSlimmer | None = None,
    ) -> None:
        self.registry = registry
        self.max_rounds = max_rounds
        self.slimmer = slimmer or ToolResultSlimmer()

    async def run(
        self,
        *,
        session,
        provider,
        messages: list[dict[str, Any]],
        model: str,
        session_id: int | None = None,
        **kwargs: Any,
    ) -> ToolLoopResult:
        active_messages = list(messages)
        proposals: list[dict[str, Any]] = []
        tool_schema = provider.build_tool_schema(self.registry.describe_tools())

        for round_index in range(self.max_rounds + 1):
            response = await provider.generate_chat(
                messages=active_messages,
                model=model,
                tools=tool_schema,
                **kwargs,
            )
            normalized_calls = provider.normalize_tool_call_response(response.get("raw") or response)
            if not normalized_calls:
                return ToolLoopResult(
                    content=response.get("text", ""),
                    messages=active_messages,
                    tool_rounds=round_index,
                    proposals=proposals,
                )

            if round_index >= self.max_rounds:
                return ToolLoopResult(
                    content="工具调用次数过多，请稍后重试或缩小问题范围。",
                    messages=active_messages,
                    tool_rounds=round_index,
                    proposals=proposals,
                )

            for tool_call in normalized_calls:
                try:
                    tool_result = await self.registry.execute(session, tool_call["toolName"], tool_call["arguments"])
                    if tool_call["toolName"].startswith("propose_") and isinstance(tool_result, dict):
                        proposal = tool_result.get("proposal")
                        if isinstance(proposal, dict):
                            proposals.append(proposal)
                    result_summary = self.slimmer.slim(tool_call["toolName"], tool_result)
                    status = "succeeded"
                    error_message = None
                    followup_result = tool_result
                except Exception as exc:
                    error_result = {"error": str(exc)}
                    result_summary = self.slimmer.slim(tool_call["toolName"], error_result)
                    status = "failed"
                    error_message = str(exc)
                    followup_result = error_result

                if session_id is not None:
                    session.add(
                        ToolCallLog(
                            session_id=session_id,
                            message_id=None,
                            tool_name=tool_call["toolName"],
                            arguments_json=tool_call["arguments"],
                            result_summary=result_summary,
                            status=status,
                            error_message=error_message,
                            created_at=utc_now(),
                        )
                    )

                active_messages = provider.build_followup_messages_after_tool_result(
                    active_messages,
                    tool_call,
                    # 日志里继续记录瘦身后的摘要，但回灌给模型的 follow-up 必须保留
                    # 完整工具结果，避免 proposal 等结构化 payload 被截断后下一轮退化。
                    followup_result,
                )

            if session_id is not None:
                await session.commit()

        return ToolLoopResult(
            content="工具调用次数过多，请稍后重试或缩小问题范围。",
            messages=active_messages,
            tool_rounds=self.max_rounds,
            proposals=proposals,
        )
