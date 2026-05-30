const PLAN_DAY_TYPES = ['腿日', '推日', '拉日', '有氧', 'rest']
const WEEKDAY_ORDER = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
]
const EXERCISE_TIERS = ['main', 'accessory']
const DEFAULT_SET_TYPE = 'straight'
const RPE_MIN = 0
const RPE_MAX = 10

function createFallbackId() {
  return `exercise-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function readStringValue(...values) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim()
    }
  }

  return ''
}

function readNumberValue(...values) {
  for (const value of values) {
    if (Number.isFinite(value)) {
      return value
    }
  }

  return null
}

function normalizeDayType(type) {
  return readStringValue(type) || 'rest'
}

function normalizeExerciseTier(exercise = {}, note = '') {
  const directTier = readStringValue(exercise.tier, exercise.role)
  if (EXERCISE_TIERS.includes(directTier)) {
    return directTier
  }

  if (note.includes('主项') || note.includes('次主项')) {
    return 'main'
  }

  return 'accessory'
}

function normalizeSetType(setType) {
  return readStringValue(setType) || DEFAULT_SET_TYPE
}

// 训练计划层只保留合法的 0-10 RPE，越界或空值统一归一成 null，避免脏数据写回本地存储。
function normalizeRpe(rpe) {
  if (!Number.isFinite(rpe)) {
    return null
  }

  if (rpe < RPE_MIN || rpe > RPE_MAX) {
    return null
  }

  return rpe
}

export function createExerciseId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return createFallbackId()
}

/**
 * 将旧版扁平动作和新版结构化动作统一归一化。
 * 这里同时保留顶层兼容字段，确保后续 AI 仍能按 day / exercise / field 稳定修改。
 */
export function normalizePlannedExercise(exercise = {}, fallbackId) {
  const template = isPlainObject(exercise.template) ? exercise.template : {}
  const instance = isPlainObject(exercise.instance) ? exercise.instance : {}
  const name = readStringValue(exercise.name)
  const sets = readNumberValue(exercise.sets, template.sets)
  const reps = readNumberValue(exercise.reps)
  const note = readStringValue(exercise.note, instance.note)
  const ref1RM = readStringValue(exercise.ref1RM, template.ref1RM) || null
  const pct = readNumberValue(exercise.pct, instance.pct)
  const kg = readNumberValue(exercise.kg, instance.kg)
  const rpe = normalizeRpe(readNumberValue(exercise.rpe, instance.rpe))
  const repsText =
    readStringValue(template.repsText) ||
    (Number.isFinite(reps) ? `${reps}` : '')
  const loadMode =
    ref1RM || readStringValue(template.loadMode) === 'percentage' ? 'percentage' : 'fixed'
  const tier = normalizeExerciseTier(exercise, note)

  return {
    id: exercise.id ?? fallbackId ?? createExerciseId(),
    name,
    tier,
    template: {
      loadMode,
      ref1RM: loadMode === 'percentage' ? ref1RM : null,
      setType: normalizeSetType(template.setType),
      sets,
      repsText,
    },
    instance: {
      pct: loadMode === 'percentage' ? pct : null,
      kg: loadMode === 'percentage' ? null : kg,
      rpe,
      note,
    },
    ref1RM: loadMode === 'percentage' ? ref1RM : null,
    pct: loadMode === 'percentage' ? pct : null,
    kg: loadMode === 'percentage' ? null : kg,
    sets,
    reps,
    rpe,
    note,
  }
}

function normalizeDayPlan(dayPlan = {}) {
  if (!isPlainObject(dayPlan)) {
    return {
      type: 'rest',
      exercises: [],
    }
  }

  const exercises = Array.isArray(dayPlan.exercises)
    ? dayPlan.exercises.map((exercise) => normalizePlannedExercise(exercise))
    : []

  return {
    type: normalizeDayType(dayPlan.type),
    exercises,
  }
}

export function normalizeWeeklyPlan(weeklyPlan = {}) {
  const safeWeeklyPlan = isPlainObject(weeklyPlan) ? weeklyPlan : {}

  return WEEKDAY_ORDER.reduce((plan, dayKey) => {
    plan[dayKey] = normalizeDayPlan(safeWeeklyPlan[dayKey])
    return plan
  }, {})
}

function updateDayPlan(weeklyPlan, dayKey, updater) {
  const normalizedPlan = normalizeWeeklyPlan(weeklyPlan)
  const currentDayPlan = normalizedPlan[dayKey] ?? { type: 'rest', exercises: [] }
  const nextDayPlan = normalizeDayPlan(updater(currentDayPlan))

  return {
    ...normalizedPlan,
    [dayKey]: nextDayPlan,
  }
}

export function getPlanDayTypes() {
  return PLAN_DAY_TYPES
}

export function getPlanDayTypeSuggestions(currentType = '') {
  const suggestions = [...PLAN_DAY_TYPES]
  const normalizedCurrentType = normalizeDayType(currentType)

  if (normalizedCurrentType !== 'rest' && !suggestions.includes(normalizedCurrentType)) {
    suggestions.push(normalizedCurrentType)
  }

  return suggestions
}

export function getWeekdayOrder() {
  return WEEKDAY_ORDER
}

export function updateDayType(weeklyPlan, dayKey, nextType) {
  const normalizedType = normalizeDayType(nextType)

  return updateDayPlan(weeklyPlan, dayKey, (dayPlan) => ({
    ...dayPlan,
    type: normalizedType,
  }))
}

export function addExerciseToDay(weeklyPlan, dayKey, exercise) {
  return updateDayPlan(weeklyPlan, dayKey, (dayPlan) => ({
    ...dayPlan,
    exercises: [...dayPlan.exercises, normalizePlannedExercise(exercise)],
  }))
}

export function updateExerciseInDay(weeklyPlan, dayKey, exerciseId, exercise) {
  return updateDayPlan(weeklyPlan, dayKey, (dayPlan) => ({
    ...dayPlan,
    exercises: dayPlan.exercises.map((item) =>
      item.id === exerciseId ? normalizePlannedExercise(exercise, exerciseId) : item,
    ),
  }))
}

export function removeExerciseFromDay(weeklyPlan, dayKey, exerciseId) {
  return updateDayPlan(weeklyPlan, dayKey, (dayPlan) => ({
    ...dayPlan,
    exercises: dayPlan.exercises.filter((exercise) => exercise.id !== exerciseId),
  }))
}
