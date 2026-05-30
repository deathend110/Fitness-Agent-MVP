import { resolvePlanWeekMeta } from './planHeader.js'
import { getWeekdayOrder, normalizeWeeklyPlan } from './weeklyPlan.js'

const TRAINING_DAY_SPAN = 2
const REST_DAY_SPAN = 1
const DESKTOP_TEMPLATE_COLUMNS = '2fr 1fr 2fr 1fr 2fr 1fr 1fr'
const COMPACT_MODE = 'stack'
const DAY_INDEX_BY_KEY = {
  Monday: 0,
  Tuesday: 1,
  Wednesday: 2,
  Thursday: 3,
  Friday: 4,
  Saturday: 5,
  Sunday: 6,
}
const DAY_LABELS = {
  Monday: '周一',
  Tuesday: '周二',
  Wednesday: '周三',
  Thursday: '周四',
  Friday: '周五',
  Saturday: '周六',
  Sunday: '周日',
}

export function getPlanDayLabel(dayKey = '') {
  return DAY_LABELS[dayKey] ?? dayKey
}

function parseDateKey(dateKey = '') {
  if (typeof dateKey !== 'string' || !dateKey.trim()) {
    return null
  }

  const parsedDate = new Date(`${dateKey.trim()}T00:00:00`)

  if (Number.isNaN(parsedDate.getTime())) {
    return null
  }

  parsedDate.setHours(0, 0, 0, 0)
  return parsedDate
}

function formatMonthDayLabel(date) {
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function buildDateLabelMap(weekMeta = {}) {
  const weekStartDate = parseDateKey(weekMeta.weekStart)

  if (!weekStartDate) {
    return {}
  }

  return Object.keys(DAY_LABELS).reduce((labels, dayKey) => {
    const dayIndex = DAY_INDEX_BY_KEY[dayKey]
    const currentDate = new Date(weekStartDate)

    currentDate.setDate(weekStartDate.getDate() + dayIndex)
    labels[dayKey] = formatMonthDayLabel(currentDate)
    return labels
  }, {})
}

function buildPlanColumn(dayKey, dayPlan, dateLabelMap, weekMeta) {
  const isTrainingDay = dayPlan.type !== 'rest'

  return {
    dayKey,
    dayLabel: getPlanDayLabel(dayKey),
    dateLabel: dateLabelMap[dayKey] ?? '',
    weekMeta,
    plan: dayPlan,
    isTrainingDay,
    exerciseCount: dayPlan.exercises.length,
    width: isTrainingDay ? 'wide' : 'narrow',
    planTypeLabel: dayPlan.type || 'rest',
    dateLabelSource: dateLabelMap[dayKey] ? 'weeklyPlan' : 'referenceDate',
  }
}

export function buildWeeklyPlanColumns(weeklyPlan = {}, options = {}) {
  const normalizedPlan = normalizeWeeklyPlan(weeklyPlan)
  const weekMeta = resolvePlanWeekMeta({
    referenceDate: options.referenceDate,
    weeklyPlan,
  })
  const dateLabelMap = buildDateLabelMap(weekMeta)

  return getWeekdayOrder().map((dayKey) =>
    buildPlanColumn(dayKey, normalizedPlan[dayKey] ?? { type: 'rest', exercises: [] }, dateLabelMap, weekMeta),
  )
}

// 布局模型集中输出比例网格约束，避免页面组件重复拼接列跨度与兜底策略。
export function buildWeeklyPlanLayoutModel(weeklyPlan = {}, options = {}) {
  const columns = buildWeeklyPlanColumns(weeklyPlan, options)
  const weekMeta = columns[0]?.weekMeta ?? resolvePlanWeekMeta({
    referenceDate: options.referenceDate,
    weeklyPlan,
  })
  const desktopTemplateColumns = columns
    .map((column) => (column.isTrainingDay ? `${TRAINING_DAY_SPAN}fr` : `${REST_DAY_SPAN}fr`))
    .join(' ')

  return {
    columns,
    weekMeta,
    compactMode: COMPACT_MODE,
    desktopGridColumnCount: columns.length,
    desktopTemplateColumns: desktopTemplateColumns || DESKTOP_TEMPLATE_COLUMNS,
    shouldAvoidHorizontalScrollOnDesktop: true,
  }
}
