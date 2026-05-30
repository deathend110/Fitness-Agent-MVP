export const exerciseWeightModes = [
  { value: 'percentage', label: '挂钩 1RM 百分比' },
  { value: 'fixed', label: '直接填写 kg' },
]
export const exerciseTierOptions = [
  { value: 'main', label: '主项' },
  { value: 'accessory', label: '辅项' },
]
export const exerciseSetTypeOptions = [
  { value: 'straight', label: '直组' },
  { value: 'custom', label: '自定义' },
]

const RPE_MIN = 0
const RPE_MAX = 10
const RPE_RANGE_ERROR = 'RPE 只能在 0-10 之间'
const RPE_RANGE_HINT = 'RPE 请输入 0-10 之间的数值'

function toInputValue(value) {
  return value === null || value === undefined ? '' : `${value}`
}

export function createExerciseDraft(exercise = {}, fallbackRef1RM = 'squat') {
  const setType = exercise.template?.setType === 'custom' ? 'custom' : 'straight'
  const repsText = exercise.template?.repsText ?? exercise.reps
  const repsValue =
    setType === 'custom'
      ? ''
      : toInputValue(exercise.reps ?? toNumberOrNull(exercise.template?.repsText ?? ''))

  return {
    name: exercise.name ?? '',
    tier: exercise.tier === 'main' ? 'main' : 'accessory',
    setType,
    weightMode:
      exercise.ref1RM || exercise.template?.loadMode === 'percentage' ? 'percentage' : 'fixed',
    ref1RM: exercise.ref1RM ?? exercise.template?.ref1RM ?? fallbackRef1RM,
    pct: toInputValue(exercise.pct),
    kg: toInputValue(exercise.kg),
    sets: toInputValue(exercise.sets),
    reps: repsValue,
    repsText: toInputValue(repsText),
    rpe: toInputValue(exercise.rpe),
    note: exercise.note ?? '',
  }
}

function toNumberOrNull(value) {
  if (value === '') {
    return null
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

// RPE 只允许落在课程要求的闭区间里，避免计划被写入越界训练强度。
export function getRpeValidationError(rpeValue) {
  const parsed = toNumberOrNull(rpeValue)

  if (parsed === null) {
    return null
  }

  if (parsed < RPE_MIN || parsed > RPE_MAX) {
    return RPE_RANGE_ERROR
  }

  return null
}

export function getRpeFieldHint(rpeError) {
  return rpeError ?? RPE_RANGE_HINT
}

function toRepsText(draftRepsText, reps) {
  const normalizedText = typeof draftRepsText === 'string' ? draftRepsText.trim() : ''

  if (normalizedText) {
    return normalizedText
  }

  return reps === null ? '' : `${reps}`
}

function toNumericReps(reps, repsText) {
  if (reps !== null) {
    return reps
  }

  const parsedFromText = Number(repsText)
  return Number.isFinite(parsedFromText) ? parsedFromText : null
}

export function draftToExercise(draft = {}) {
  const weightMode = draft.weightMode === 'percentage' ? 'percentage' : 'fixed'
  const tier = draft.tier === 'main' ? 'main' : 'accessory'
  const setType = draft.setType === 'custom' ? 'custom' : 'straight'
  const parsedReps = toNumberOrNull(draft.reps)
  const repsText =
    setType === 'custom' ? toRepsText(draft.repsText, null) : toRepsText(draft.repsText, parsedReps)
  const nextReps = setType === 'custom' ? toNumericReps(null, repsText) : parsedReps
  const baseExercise = {
    name: (draft.name ?? '').trim(),
    sets: toNumberOrNull(draft.sets),
    reps: nextReps,
    rpe: toNumberOrNull(draft.rpe),
    note: (draft.note ?? '').trim(),
    tier,
    template: {
      setType,
      repsText,
    },
  }

  if (weightMode === 'percentage') {
    return {
      ...baseExercise,
      ref1RM: draft.ref1RM || null,
      pct: toNumberOrNull(draft.pct),
      kg: null,
    }
  }

  return {
    ...baseExercise,
    ref1RM: null,
    pct: null,
    kg: toNumberOrNull(draft.kg),
  }
}

export function buildExerciseSavePayload(draft = {}) {
  if (getRpeValidationError(draft.rpe)) {
    return null
  }

  return draftToExercise(draft)
}
