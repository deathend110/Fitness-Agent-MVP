function readPresetLabel(activeCyclePlan = null) {
  return (
    activeCyclePlan?.cycle?.presetLabel ??
    activeCyclePlan?.cycle?.presetKey ??
    activeCyclePlan?.preset?.label ??
    activeCyclePlan?.preset?.key ??
    ''
  )
}

export function hasOpenCyclePlan(activeCyclePlan = null) {
  const cycleId = activeCyclePlan?.cycle?.id
  const cycleStatus = activeCyclePlan?.cycle?.status

  return Number.isInteger(cycleId) && (cycleStatus === 'draft' || cycleStatus === 'active')
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

export function resolvePlanSettingsMode(
  planSource = {},
  activeCyclePlan = null,
  preferredMode = null,
) {
  if (preferredMode === 'manual' || preferredMode === 'cycle') {
    return preferredMode
  }

  if (planSource?.activeSource === 'cycle' && hasOpenCyclePlan(activeCyclePlan)) {
    return 'cycle'
  }

  return 'manual'
}

export function buildCycleSettingsStatus({ planSource = {}, activeCyclePlan = null } = {}) {
  const hasOpenCycle = hasOpenCyclePlan(activeCyclePlan)
  const activeSource = planSource?.activeSource === 'cycle' && hasOpenCycle ? 'cycle' : 'manual'
  const currentWeekIndex = activeCyclePlan?.cycle?.currentWeekIndex
  const pendingWeekIndex = activeCyclePlan?.cycle?.pendingWeekIndex
  const summaryLabel = buildCyclePresetSummary(activeCyclePlan) || '未创建周期计划'
  const sourceToken = getCyclePlanSourceLabel({ activeSource })

  return {
    activeSource,
    sourceLabel: sourceToken.label,
    summaryLabel,
    statusLabel: getCycleStatusLabel(activeCyclePlan?.cycle?.status).label,
    pendingWeekLabel:
      Number.isInteger(pendingWeekIndex) && pendingWeekIndex > 0
        ? `已生成待确认的第 ${pendingWeekIndex} 周`
        : '当前没有待确认周',
    currentWeekLabel:
      Number.isInteger(currentWeekIndex) && currentWeekIndex > 0
        ? `当前周期周次：第 ${currentWeekIndex} 周`
        : '当前没有活动周期',
    manualPlanHint: '手动计划与周期计划独立保存，切换当前来源不会覆盖另一份计划。',
    canActivateCycle: hasOpenCycle && activeSource !== 'cycle',
    canSwitchToManual: activeSource === 'cycle',
    canCreateCycle: !hasOpenCycle,
    hasOpenCycle,
  }
}
