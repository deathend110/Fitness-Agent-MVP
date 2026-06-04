const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const MAIN_LIFT_KEYS = ['squat', 'bench', 'deadlift', 'ohp']

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeNumber(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value !== 'string') {
    return null
  }

  const normalizedValue = value.trim()
  if (!normalizedValue) {
    return null
  }

  const parsedValue = Number(normalizedValue)
  return Number.isFinite(parsedValue) ? parsedValue : null
}

function createEmptyDay(dayIndex) {
  return {
    dayIndex,
    label: DAY_LABELS[dayIndex - 1] ?? '',
    type: 'rest',
    exercises: [],
  }
}

function createEmptyWeek(weekIndex) {
  return {
    weekIndex,
    days: Array.from({ length: 7 }, (_, dayOffset) => createEmptyDay(dayOffset + 1)),
  }
}

function compactMainLifts(mainLifts = {}) {
  return MAIN_LIFT_KEYS.reduce((result, liftKey) => {
    const tm = normalizeNumber(mainLifts?.[liftKey]?.tm)
    if (tm === null) {
      return result
    }

    result[liftKey] = { tm }
    return result
  }, {})
}

function normalizeWeeks(weeks) {
  if (!Array.isArray(weeks)) {
    return []
  }

  // mapper 只稳定外层数组，保留每个 week/day/exercise 的既有结构，避免误改编辑器已维护的内容。
  return weeks
    .filter((week) => week && typeof week === 'object' && !Array.isArray(week))
    .map((week) => ({ ...week }))
}

export function createCustomStrengthDraft() {
  return {
    name: '',
    startDate: '',
    totalWeeks: 4,
    mainLifts: {
      squat: { tm: '' },
      bench: { tm: '' },
      deadlift: { tm: '' },
      ohp: { tm: '' },
    },
    weeks: Array.from({ length: 4 }, (_, weekOffset) => createEmptyWeek(weekOffset + 1)),
  }
}

export function buildCreateCustomStrengthCyclePayload(draft = {}) {
  const mainLifts = compactMainLifts(draft?.mainLifts)
  const weeks = normalizeWeeks(draft?.weeks)

  return {
    presetKey: 'custom_strength',
    startDate: normalizeText(draft?.startDate),
    goal: 'strength',
    baseLifts: { ...mainLifts },
    config: {
      planType: 'custom_strength',
      name: normalizeText(draft?.name),
      startDate: normalizeText(draft?.startDate),
      totalWeeks: weeks.length,
      // 顶层 baseLifts 和 config.mainLifts 必须保持同构，避免后端触发冗余字段冲突校验。
      mainLifts: { ...mainLifts },
      weeks,
    },
  }
}
