export const exerciseWeightModes = [
  { value: 'percentage', label: '挂钩 1RM 百分比' },
  { value: 'fixed', label: '直接填写 kg' },
]

function toInputValue(value) {
  return value === null || value === undefined ? '' : `${value}`
}

export function createExerciseDraft(exercise = {}, fallbackRef1RM = 'squat') {
  return {
    name: exercise.name ?? '',
    weightMode: exercise.ref1RM ? 'percentage' : 'fixed',
    ref1RM: exercise.ref1RM ?? fallbackRef1RM,
    pct: toInputValue(exercise.pct),
    kg: toInputValue(exercise.kg),
    sets: toInputValue(exercise.sets),
    reps: toInputValue(exercise.reps),
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

export function draftToExercise(draft = {}) {
  const weightMode = draft.weightMode === 'percentage' ? 'percentage' : 'fixed'
  const baseExercise = {
    name: (draft.name ?? '').trim(),
    sets: toNumberOrNull(draft.sets),
    reps: toNumberOrNull(draft.reps),
    rpe: toNumberOrNull(draft.rpe),
    note: (draft.note ?? '').trim(),
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

