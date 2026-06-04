from __future__ import annotations

from backend.agent.context_manager import PromptAssembler, TokenBudgetConfig


def test_stable_system_prompt_does_not_change_between_user_inputs() -> None:
    assembler = PromptAssembler()

    first = assembler.assemble(
        user_input="今天深蹲很累，明天怎么调？",
        profile={"basic": {"name": "阿杰"}, "goal": "增肌"},
    )
    second = assembler.assemble(
        user_input="卧推卡住了，今晚练什么？",
        profile={"basic": {"name": "阿杰"}, "goal": "增肌"},
    )

    assert first.messages[0] == second.messages[0]
    assert "RepMind" in first.messages[0]["content"]
    assert "当前时间" not in first.messages[0]["content"]
    assert "今天深蹲" not in first.messages[0]["content"]


def test_dynamic_state_is_after_stable_prefix_and_before_recent_history() -> None:
    assembler = PromptAssembler()

    context = assembler.assemble(
        user_input="请根据今天状态调整明天训练",
        profile={"basic": {"name": "阿杰"}, "goal": "力量增长"},
        weekly_plan={"Monday": {"type": "strength", "exercises": [{"name": "深蹲"}]}},
        daily_logs={"2026-05-31": {"fatigue": 5, "trainingNotes": "深蹲速度变慢"}},
        memories=[
            {"kind": "safety", "content": "深蹲到底部时左膝疼痛。"},
            {"kind": "preference", "content": "用户偏好晚间训练。"},
        ],
        recent_messages=[
            {"role": "assistant", "content": "上次建议先降容量。"},
            {"role": "user", "content": "我周五想硬拉。"},
        ],
    )

    contents = [message["content"] for message in context.messages]

    assert context.messages[0]["role"] == "system"
    assert contents[1].startswith("## 当前用户状态")
    assert "力量增长" in contents[1]
    # daily_logs 已移出稳定前缀，不应再出现在 current_state 段。
    assert "深蹲速度变慢" not in contents[1]
    assert contents[2].startswith("## 安全限制")
    assert "左膝疼痛" in contents[2]
    assert contents[3].startswith("## 相关记忆")
    # daily_state 段排在相对稳定块之后，承载按日变化的 daily_logs。
    assert contents[4].startswith("## 今日/近期日志")
    assert "深蹲速度变慢" in contents[4]
    assert "上次建议先降容量" in contents[5]
    assert context.messages[-1] == {
        "role": "user",
        "content": "请根据今天状态调整明天训练",
    }
    assert context.debug["selected_sections"][:3] == [
        "stable_system_prompt",
        "current_state",
        "safety_memory",
    ]
    # daily_state 必须在每轮易变的近期消息之前，保住前缀缓存。
    sections = context.debug["selected_sections"]
    assert sections.index("daily_state") < sections.index("recent_message")


def test_token_budget_reserves_reply_space_and_trims_low_priority_history() -> None:
    assembler = PromptAssembler(
        budget=TokenBudgetConfig(
            # 系统提示扩充（含工具调用规范段）后占约 150 token，调大预算以仍能触发历史裁剪。
            max_context_tokens=400,
            reserved_response_tokens=100,
        )
    )
    recent_messages = [
        {"role": "user", "content": f"第 {index} 轮历史：" + "训练状态很好。" * 20}
        for index in range(12)
    ]

    context = assembler.assemble(
        user_input="现在请给我明天计划",
        profile={"goal": "保持力量"},
        weekly_plan={"Tuesday": {"type": "strength", "exercises": [{"name": "卧推"}]}},
        recent_messages=recent_messages,
    )

    assert context.debug["token_budget"]["available_for_prompt"] == 300
    assert context.debug["estimated_prompt_tokens"] <= 300
    assert context.debug["trimmed_items"]
    assert context.messages[-1]["content"] == "现在请给我明天计划"
    assert any("卧推" in message["content"] for message in context.messages)
