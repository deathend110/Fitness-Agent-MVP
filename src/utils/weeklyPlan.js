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

export function createExerciseId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return createFallbackId()
}

function getDefaultDayPlan(dayPlan = {}) {
  return {
    type: dayPlan.type ?? 'rest',
    exercises: Array.isArray(dayPlan.exercises) ? dayPlan.exercises : [],
  }
}

// 计划数据层只接受 0-10 的 RPE，超出范围时统一压成 null，避免非法强度写入 localStorage。
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
  const currentDayPlan = getDefaultDayPlan(weeklyPlan?.[dayKey])
  const nextDayPlan = updater(currentDayPlan)

  return {
    ...weeklyPlan,
    [dayKey]: nextDayPlan,
  }
}

export function getPlanDayTypes() {
  return PLAN_DAY_TYPES
}

export function getWeekdayOrder() {
  return WEEKDAY_ORDER
}

export function updateDayType(weeklyPlan, dayKey, nextType) {
  const normalizedType = PLAN_DAY_TYPES.includes(nextType) ? nextType : 'rest'

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
