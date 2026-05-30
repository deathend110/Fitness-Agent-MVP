import { createExerciseDraft } from './exerciseForm.js'

export const NEW_PLAN_EXERCISE_ID = '__new__'

export function clearPlanEditorState() {
  return {
    dayKey: null,
    exerciseId: null,
    draft: null,
  }
}

export function startAddingExercise(dayKey, oneRmOptions = []) {
  const fallbackRef = oneRmOptions[0]?.value ?? 'squat'

  return {
    dayKey,
    exerciseId: NEW_PLAN_EXERCISE_ID,
    draft: createExerciseDraft({}, fallbackRef),
  }
}

export function startEditingExercise(dayKey, exercise, oneRmOptions = []) {
  const fallbackRef = oneRmOptions[0]?.value ?? 'squat'

  return {
    dayKey,
    exerciseId: exercise?.id ?? null,
    draft: createExerciseDraft(exercise ?? {}, fallbackRef),
  }
}

export function updatePlanEditorDraft(currentState, nextDraft) {
  return {
    ...currentState,
    draft: nextDraft,
  }
}

export function isPlanEditorTarget(currentState, dayKey, exerciseId) {
  return currentState?.dayKey === dayKey && currentState?.exerciseId === exerciseId
}

export function clearPlanEditorStateAfterDelete(currentState, dayKey, exerciseId) {
  if (isPlanEditorTarget(currentState, dayKey, exerciseId)) {
    return clearPlanEditorState()
  }

  return currentState
}

const PLAN_EXERCISE_MENU_ACTIONS = [
  { key: 'edit', label: '编辑动作', tone: 'default' },
  { key: 'delete', label: '删除动作', tone: 'danger' },
]

export function getPlanExerciseMenuActions() {
  return PLAN_EXERCISE_MENU_ACTIONS
}

export function executePlanExerciseMenuAction(actionKey, handlers = {}) {
  if (actionKey === 'edit') {
    handlers.edit?.()
    return true
  }

  if (actionKey === 'delete') {
    handlers.delete?.()
    return true
  }

  return false
}
