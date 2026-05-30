import { normalizeWeeklyPlan } from './weeklyPlan.js'

const TRAINING_DAY_SPAN = 2
const REST_DAY_SPAN = 1
const DESKTOP_TEMPLATE_COLUMNS = '2fr 1fr 2fr 1fr 2fr 1fr 1fr'
const COMPACT_MODE = 'stack'
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

function buildPlanColumn(dayKey, dayPlan) {
  const isTrainingDay = dayPlan.type !== 'rest'
  const desktopSpan = isTrainingDay ? TRAINING_DAY_SPAN : REST_DAY_SPAN

  return {
    dayKey,
    dayLabel: getPlanDayLabel(dayKey),
    plan: dayPlan,
    isTrainingDay,
    exerciseCount: dayPlan.exercises.length,
    width: isTrainingDay ? 'wide' : 'narrow',
    desktopSpan,
  }
}

export function buildWeeklyPlanColumns(weeklyPlan = {}) {
  const normalizedPlan = normalizeWeeklyPlan(weeklyPlan)

  return Object.entries(normalizedPlan).map(([dayKey, dayPlan]) => buildPlanColumn(dayKey, dayPlan))
}

// 布局模型集中输出比例网格约束，避免页面组件重复拼接列跨度与兜底策略。
export function buildWeeklyPlanLayoutModel(weeklyPlan = {}) {
  const columns = buildWeeklyPlanColumns(weeklyPlan)
  const desktopTemplateColumns = columns
    .map((column) => (column.desktopSpan === TRAINING_DAY_SPAN ? '2fr' : '1fr'))
    .join(' ')

  return {
    columns,
    compactMode: COMPACT_MODE,
    desktopGridColumnCount: columns.reduce((total, column) => total + column.desktopSpan, 0),
    desktopTemplateColumns: desktopTemplateColumns || DESKTOP_TEMPLATE_COLUMNS,
    shouldAvoidHorizontalScrollOnDesktop: true,
  }
}
