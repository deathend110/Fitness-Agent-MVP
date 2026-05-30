const PLAN_HEADER_TITLE = '本周训练计划'
const PLAN_HEADER_LEGEND_ITEMS = [
  { label: '主项', tone: 'main' },
  { label: '辅项', tone: 'accessory' },
]
const PLAN_HEADER_VIEW_TABS = [
  { key: 'week', label: '周视图', isActive: true, isInteractive: false },
  { key: 'list', label: '列表视图', isActive: false, isInteractive: false },
]
const PLAN_SETTINGS_BUTTON = {
  label: '计划设置',
  hint: '当前仅保留训练计划设置入口，后续版本会接入周期模板与高级配置。',
  title: '计划设置（开发中）',
  description: '训练计划页头部暂时只保留一个统一入口，供后续接入计划模板、周期节奏和高级设置。',
  confirmLabel: '知道了',
  isPlaceholder: true,
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function normalizeReferenceDate(referenceDate) {
  if (referenceDate instanceof Date && !Number.isNaN(referenceDate.getTime())) {
    return new Date(referenceDate)
  }

  if (typeof referenceDate === 'string' && referenceDate.trim()) {
    const normalizedDate = new Date(`${referenceDate.trim()}T00:00:00`)

    if (!Number.isNaN(normalizedDate.getTime())) {
      return normalizedDate
    }
  }

  return new Date()
}

function parseDateString(dateString) {
  if (typeof dateString !== 'string' || !dateString.trim()) {
    return null
  }

  const parsedDate = new Date(`${dateString.trim()}T00:00:00`)

  if (Number.isNaN(parsedDate.getTime())) {
    return null
  }

  parsedDate.setHours(0, 0, 0, 0)
  return parsedDate
}

function getMondayOfWeek(referenceDate) {
  const normalizedDate = normalizeReferenceDate(referenceDate)
  const monday = new Date(normalizedDate)
  const dayOfWeek = monday.getDay()
  const offset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek

  monday.setDate(monday.getDate() + offset)
  monday.setHours(0, 0, 0, 0)

  return monday
}

function getSundayOfWeek(referenceDate) {
  const monday = getMondayOfWeek(referenceDate)
  const sunday = new Date(monday)

  sunday.setDate(monday.getDate() + 6)
  sunday.setHours(0, 0, 0, 0)

  return sunday
}

function formatMonthDayLabel(date) {
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function formatWeekRangeLabel(weekStart, weekEnd) {
  return `${weekStart.getFullYear()}年${formatMonthDayLabel(weekStart)} - ${formatMonthDayLabel(weekEnd)}`
}

function getIsoWeekNumber(referenceDate) {
  const normalizedDate = normalizeReferenceDate(referenceDate)
  const utcDate = new Date(
    Date.UTC(normalizedDate.getFullYear(), normalizedDate.getMonth(), normalizedDate.getDate()),
  )
  const day = utcDate.getUTCDay() || 7

  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - day)

  const yearStart = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1))
  return Math.ceil(((utcDate - yearStart) / 86400000 + 1) / 7)
}

function formatDateKey(date) {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')

  return `${year}-${month}-${day}`
}

function normalizeWeekNumber(weekNumber, fallbackWeekNumber) {
  if (Number.isInteger(weekNumber) && weekNumber > 0) {
    return weekNumber
  }

  return fallbackWeekNumber
}

function readWeekMetaFromPlan(weeklyPlan) {
  if (!isPlainObject(weeklyPlan) || !isPlainObject(weeklyPlan.weekMeta)) {
    return null
  }

  return weeklyPlan.weekMeta
}

function hasCompleteWeekRange(planWeekMeta) {
  return Boolean(parseDateString(planWeekMeta?.weekStart) && parseDateString(planWeekMeta?.weekEnd))
}

function resolvePlanWeekRange(options = {}) {
  const fallbackWeekStart = getMondayOfWeek(options.referenceDate)
  const fallbackWeekEnd = getSundayOfWeek(options.referenceDate)
  const planWeekMeta = readWeekMetaFromPlan(options.weeklyPlan)

  if (!hasCompleteWeekRange(planWeekMeta)) {
    return {
      weekStartDate: fallbackWeekStart,
      weekEndDate: fallbackWeekEnd,
      usesPlanRange: false,
    }
  }

  return {
    weekStartDate: parseDateString(planWeekMeta.weekStart),
    weekEndDate: parseDateString(planWeekMeta.weekEnd),
    usesPlanRange: true,
  }
}

/**
 * 训练计划头部统一从兼容层读取周元信息，确保空计划、旧数据和后续真实周配置都能稳定展示。
 */
export function resolvePlanWeekMeta(options = {}) {
  const derivedWeekNumber = getIsoWeekNumber(options.referenceDate)
  const planWeekMeta = readWeekMetaFromPlan(options.weeklyPlan)
  const { weekStartDate, weekEndDate, usesPlanRange } = resolvePlanWeekRange(options)

  return {
    source: planWeekMeta ? 'weeklyPlan' : 'derived',
    weekNumber: normalizeWeekNumber(planWeekMeta?.weekNumber, derivedWeekNumber),
    weekStart: usesPlanRange ? planWeekMeta.weekStart.trim() : formatDateKey(weekStartDate),
    weekEnd: usesPlanRange ? planWeekMeta.weekEnd.trim() : formatDateKey(weekEndDate),
  }
}

export function buildPlanHeaderModel(options = {}) {
  const { weekStartDate, weekEndDate } = resolvePlanWeekRange(options)
  const weekMeta = resolvePlanWeekMeta(options)

  return {
    title: PLAN_HEADER_TITLE,
    weekMeta,
    weekRangeLabel: formatWeekRangeLabel(weekStartDate, weekEndDate),
    weekBadgeLabel: `第 ${weekMeta.weekNumber} 周`,
    legendItems: PLAN_HEADER_LEGEND_ITEMS,
    viewTabs: PLAN_HEADER_VIEW_TABS,
    settingsButton: PLAN_SETTINGS_BUTTON,
  }
}
