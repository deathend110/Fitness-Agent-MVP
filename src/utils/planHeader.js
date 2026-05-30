const PLAN_HEADER_TITLE = '本周训练计划'
const PLAN_HEADER_LEGEND_ITEMS = [
  { label: '主项', tone: 'main' },
  { label: '辅项', tone: 'accessory' },
]

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

export function buildPlanHeaderModel(options = {}) {
  const weekStart = getMondayOfWeek(options.referenceDate)
  const weekEnd = getSundayOfWeek(options.referenceDate)

  return {
    title: PLAN_HEADER_TITLE,
    weekRangeLabel: formatWeekRangeLabel(weekStart, weekEnd),
    weekBadgeLabel: `第 ${getIsoWeekNumber(options.referenceDate)} 周`,
    legendItems: PLAN_HEADER_LEGEND_ITEMS,
    // 当前头部只保留必要信息与计划设置占位入口，不回填无效的次级操作按钮。
    secondaryActions: [],
    settingsButton: {
      label: '计划设置',
      hint: '即将支持更完整的周期计划配置',
      isPlaceholder: true,
    },
  }
}
