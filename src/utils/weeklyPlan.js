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
const RPE_MIN = 0
const RPE_MAX = 10

function createFallbackId() {
  return `exercise-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function normalizeDayType(type) {
  if (typeof type !== 'string') {
    return 'rest'
  }

  const trimmedType = type.trim()

  return trimmedType || 'rest'
}

function normalizeDayPlan(dayPlan = {}) {
  if (!isPlainObject(dayPlan)) {
    return {
      type: 'rest',
      exercises: [],
    }
  }

  return {
    type: normalizeDayType(dayPlan.type),
    exercises: Array.isArray(dayPlan.exercises) ? dayPlan.exercises : [],
  }
}

export function createExerciseId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return createFallbackId()
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

function normalizeExercise(exercise = {}, fallbackId) {
  const usePercentageMode =
    Boolean(exercise.ref1RM) && Number.isFinite(exercise.pct)
  const normalized = {
    id: exercise.id ?? fallbackId ?? createExerciseId(),
    name: (exercise.name ?? '').trim(),
    sets: Number.isFinite(exercise.sets) ? exercise.sets : null,
    reps: Number.isFinite(exercise.reps) ? exercise.reps : null,
    rpe: normalizeRpe(exercise.rpe),
    note: (exercise.note ?? '').trim(),
  }

  if (usePercentageMode) {
    return {
      ...normalized,
      ref1RM: exercise.ref1RM,
      pct: Number.isFinite(exercise.pct) ? exercise.pct : null,
      kg: null,
    }
  }

  return {
    ...normalized,
    ref1RM: null,
    pct: null,
    kg: Number.isFinite(exercise.kg) ? exercise.kg : null,
  }
}

function updateDayPlan(weeklyPlan, dayKey, updater) {
  const safeWeeklyPlan = isPlainObject(weeklyPlan) ? weeklyPlan : {}
  const currentDayPlan = normalizeDayPlan(safeWeeklyPlan[dayKey])
  const nextDayPlan = updater(currentDayPlan)

  return {
    ...safeWeeklyPlan,
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
    exercises: [...dayPlan.exercises, normalizeExercise(exercise)],
  }))
}

export function updateExerciseInDay(weeklyPlan, dayKey, exerciseId, exercise) {
  return updateDayPlan(weeklyPlan, dayKey, (dayPlan) => ({
    ...dayPlan,
    exercises: dayPlan.exercises.map((item) =>
      item.id === exerciseId ? normalizeExercise(exercise, exerciseId) : item,
    ),
  }))
}

export function removeExerciseFromDay(weeklyPlan, dayKey, exerciseId) {
  return updateDayPlan(weeklyPlan, dayKey, (dayPlan) => ({
    ...dayPlan,
    exercises: dayPlan.exercises.filter((exercise) => exercise.id !== exerciseId),
  }))
}
