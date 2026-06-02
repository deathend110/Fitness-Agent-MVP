from __future__ import annotations

from typing import Any


def finalize_assistant_text(
    assistant_text: str,
    proposal: dict[str, Any] | None,
) -> str:
    # proposal 工具只会产出待确认卡片；真正写回发生在 commit 接口，因此这里只在模型正文
    # 明确误报“已采纳/已写回计划”时做最小收口，避免把正常的“待确认”说明也改写掉。
    if proposal is None or proposal.get("status") != "pending":
        return assistant_text

    normalized_text = assistant_text.strip()
    misleading_markers = (
        "已采纳",
        "已写入计划",
        "已写回计划",
        "已更新计划",
    )
    if not normalized_text or not any(marker in normalized_text for marker in misleading_markers):
        return assistant_text

    summary = proposal.get("summary")
    if isinstance(summary, str) and summary.strip():
        normalized_summary = summary.strip().rstrip("。.!！？!?")
        return f"已生成待确认的训练计划调整建议：{normalized_summary}。当前仍未写回计划，请确认后再采纳。"
    return "已生成待确认的训练计划调整建议，当前仍未写回计划，请确认后再采纳。"
