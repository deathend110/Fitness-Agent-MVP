from __future__ import annotations

from typing import Any

PLAN_PROPOSAL_REQUEST_MARKERS = (
    "proposal",
    "计划卡",
    "待确认卡",
    "待确认建议卡",
    "修改卡",
    "调整卡",
    "建议卡",
    "卡片",
    "计划修改卡",
    "生成新计划",
    "改计划",
    "修改计划",
    "恢复型腿日卡",
)

PLAN_PROPOSAL_CONFIRMATION_MARKERS = (
    "不要直接写回",
    "待确认",
    "proposal",
    "计划修改卡",
    "修改计划卡",
    "生成计划修改卡",
)


def has_explicit_plan_proposal_intent(user_content: str) -> bool:
    normalized = str(user_content or "").strip().lower()
    if not normalized:
        return False
    return any(marker in normalized for marker in PLAN_PROPOSAL_REQUEST_MARKERS)


def requires_structured_plan_proposal(user_content: str) -> bool:
    if not has_explicit_plan_proposal_intent(user_content):
        return False
    normalized = str(user_content or "").strip().lower()
    return any(marker in user_content or marker in normalized for marker in PLAN_PROPOSAL_CONFIRMATION_MARKERS)


def _is_deepseek_openai_compatible_client(provider_client: Any) -> bool:
    provider_label = str(getattr(provider_client, "provider_label", "") or "").lower()
    base_url = str(getattr(provider_client, "base_url", "") or "").lower()

    if "deepseek" in provider_label:
        return True
    if "deepseek.com" in base_url:
        return True
    return False


def resolve_tool_choice_for_request(
    *,
    user_content: str,
    provider_client: Any,
    thinking: dict[str, Any] | None,
) -> str | dict[str, Any] | None:
    requires_proposal = requires_structured_plan_proposal(user_content)
    thinking_enabled = bool(thinking and thinking.get("type") == "enabled")
    is_deepseek_compatible = _is_deepseek_openai_compatible_client(provider_client)

    # 保留原有 thinking 默认行为：未显式要求 proposal 时，不主动强塞 tool_choice，
    # 避免影响普通分析/恢复类请求的自然工具回环。
    if thinking_enabled and not requires_proposal:
        return None

    if is_deepseek_compatible:
        # DeepSeek 实际接口在 thinking / v4 系列下会把 required tool_choice 直接判成 400，
        # 因此统一不强塞 required，改由工具暴露范围 + 纠偏提示 + proposal 结果校验兜底。
        return None

    if requires_proposal:
        # 只要本轮明确要求待确认 proposal，就先强制模型经由工具回环产出结构化卡片。
        return "required"
    return "auto"
