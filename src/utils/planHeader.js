const PLAN_HEADER_TITLE = '本周训练计划'
const PLAN_HEADER_LEGEND_ITEMS = [
  { label: '主项', tone: 'main' },
  { label: '辅项', tone: 'accessory' },
]
const PLAN_SETTINGS_BUTTON = {
  label: '计划设置',
  hint: '当前仅提供入口占位，周期计划与经典计划模板将在后续版本开放。',
  title: '计划设置（建设中）',
  description:
    '这里会放周模板、周期节奏和经典计划库配置；当前 MVP 先保留统一入口，避免误导为完整功能已上线。',
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
  const weekNumber = Math.ceil(((utcDate - yearStart) / 86400000 + 1) / 7)

  return weekNumber
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

/**
 * 训练计划头部先通过兼容层统一周元信息。
 * 这样旧版 weeklyPlan、缺字段数据和本周空计划都能走同一套稳定展示字段。
 */
export function resolvePlanWeekMeta(options = {}) {
  const weekStartDate = getMondayOfWeek(options.referenceDate)
  const weekEndDate = getSundayOfWeek(options.referenceDate)
  const derivedWeekNumber = getIsoWeekNumber(options.referenceDate)
  const planWeekMeta = readWeekMetaFromPlan(options.weeklyPlan)

  return {
    source: planWeekMeta ? 'weeklyPlan' : 'derived',
    weekNumber: normalizeWeekNumber(planWeekMeta?.weekNumber, derivedWeekNumber),
    weekStart: typeof planWeekMeta?.weekStart === 'string' && planWeekMeta.weekStart.trim()
      ? planWeekMeta.weekStart.trim()
      : formatDateKey(weekStartDate),
    weekEnd: typeof planWeekMeta?.weekEnd === 'string' && planWeekMeta.weekEnd.trim()
      ? planWeekMeta.weekEnd.trim()
      : formatDateKey(weekEndDate),
  }
}

export function buildPlanHeaderModel(options = {}) {
  const weekStartDate = getMondayOfWeek(options.referenceDate)
  const weekEndDate = getSundayOfWeek(options.referenceDate)
  const weekMeta = resolvePlanWeekMeta(options)

  return {
    title: PLAN_HEADER_TITLE,
    weekMeta,
    weekRangeLabel: formatWeekRangeLabel(weekStartDate, weekEndDate),
    weekBadgeLabel: `第 ${weekMeta.weekNumber} 周`,
    legendItems: PLAN_HEADER_LEGEND_ITEMS,
    // 当前头部只保留必要信息与计划设置占位入口，不回填未上线的复杂配置操作。
    secondaryActions: [],
    settingsButton: PLAN_SETTINGS_BUTTON,
  }
}
