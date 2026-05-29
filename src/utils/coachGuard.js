function hasValue(value) {
  return value !== null && value !== undefined && value !== ''
}

// MVP 阶段至少要求档案里有姓名、当前体重、训练目标和深蹲 1RM，避免 AI 在空上下文下给出误导性建议。
export function getCoachBlockReason(profile = {}) {
  const isReady =
    hasValue(profile.basic?.name) &&
    hasValue(profile.basic?.weight) &&
    hasValue(profile.goal) &&
    hasValue(profile.oneRM?.squat)

  if (isReady) {
    return ''
  }

  return '请先完善档案中的姓名、当前体重、训练目标和深蹲 1RM，再使用 AI 教练。'
}
