function readPresetLabel(activeCyclePlan = null) {
  return (
    activeCyclePlan?.cycle?.presetLabel ??
    activeCyclePlan?.cycle?.presetKey ??
    activeCyclePlan?.preset?.label ??
    activeCyclePlan?.preset?.key ??
    ''
  )
}

export function getCyclePlanSourceLabel(planSource = {}) {
  if (planSource?.activeSource === 'cycle') {
    return {
      tone: 'cycle',
      label: '当前来源：周期计划',
    }
  }

  return {
    tone: 'manual',
    label: '当前来源：非周期计划',
  }
}

export function buildCyclePresetSummary(activeCyclePlan = null) {
  const presetLabel = readPresetLabel(activeCyclePlan)
  const currentWeekIndex = activeCyclePlan?.cycle?.currentWeekIndex

  if (presetLabel && Number.isInteger(currentWeekIndex) && currentWeekIndex > 0) {
    return `${presetLabel} · 第 ${currentWeekIndex} 周`
  }

  return presetLabel
}

export function getCycleStatusLabel(status) {
  if (status === 'active') {
    return {
      tone: 'active',
      label: '进行中',
    }
  }

  if (status === 'completed' || status === 'archived') {
    return {
      tone: 'completed',
      label: '已停止',
    }
  }

  return {
    tone: 'default',
    label: typeof status === 'string' && status.trim() ? status.trim() : '未开始',
  }
}
