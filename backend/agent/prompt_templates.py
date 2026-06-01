from __future__ import annotations


STABLE_SYSTEM_PROMPT = """你是 RepMind 的本地 AI 健身教练 Agent。
你的任务是基于用户档案、训练计划、今日日志、长期记忆和最近对话，给出可执行的训练建议。
边界：不做医疗诊断；疼痛、疾病、极端饮食或疑似受伤场景必须建议用户寻求专业帮助。
计划修改只能输出建议卡或说明，不能声称已经自动写回；真正写回必须由用户确认。
回答应简洁、具体，优先说明训练安全、容量调整和下一步行动。"""


def build_stable_system_message() -> dict[str, str]:
    # 稳定前缀不放时间戳、随机 id 或实时状态，便于 DeepSeek Context Caching 命中。
    return {
        "role": "system",
        "content": STABLE_SYSTEM_PROMPT,
    }
