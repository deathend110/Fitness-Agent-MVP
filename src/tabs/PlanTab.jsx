import { useMemo, useState } from 'react'
import PlanDayCard, { createEmptyExerciseDraft } from '../components/PlanDayCard.jsx'
import {
  buildExerciseSavePayload,
  createExerciseDraft,
  getRpeValidationError,
} from '../utils/exerciseForm.js'
import { getTodayKey } from '../utils/calc.js'
import { buildWeeklyPlanColumns } from '../utils/planLayout.js'
import {
  addExerciseToDay,
  getPlanDayTypes,
  removeExerciseFromDay,
  updateDayType,
  updateExerciseInDay,
} from '../utils/weeklyPlan.js'

const NEW_EXERCISE_ID = '__new__'

function getOneRmOptions(profile) {
  return [
    { value: 'squat', label: `深蹲 ${profile.oneRM?.squat ?? '--'}kg` },
    { value: 'bench', label: `卧推 ${profile.oneRM?.bench ?? '--'}kg` },
    { value: 'deadlift', label: `硬拉 ${profile.oneRM?.deadlift ?? '--'}kg` },
  ]
}

function PlanTab({ profile, weeklyPlan, onWeeklyPlanChange }) {
  const [expandedDay, setExpandedDay] = useState(() => getTodayKey())
  const [editingState, setEditingState] = useState({
    dayKey: null,
    exerciseId: null,
    draft: null,
  })
  const oneRmOptions = getOneRmOptions(profile)
  const dayTypeOptions = getPlanDayTypes()
  const dayColumns = useMemo(() => buildWeeklyPlanColumns(weeklyPlan), [weeklyPlan])

  function toggleDay(dayKey) {
    setExpandedDay((currentDay) => (currentDay === dayKey ? null : dayKey))
  }

  function handleDayTypeChange(dayKey, nextType) {
    onWeeklyPlanChange((currentPlan) => updateDayType(currentPlan, dayKey, nextType))
  }

  function startAddExercise(dayKey) {
    setEditingState({
      dayKey,
      exerciseId: NEW_EXERCISE_ID,
      draft: createEmptyExerciseDraft(oneRmOptions),
    })
  }

  function startEditExercise(dayKey, exercise) {
    setEditingState({
      dayKey,
      exerciseId: exercise.id,
      draft: createExerciseDraft(exercise, oneRmOptions[0]?.value ?? 'squat'),
    })
  }

  function updateDraft(nextDraft) {
    setEditingState((current) => ({
      ...current,
      draft: nextDraft,
    }))
  }

  function cancelEditing() {
    setEditingState({
      dayKey: null,
      exerciseId: null,
      draft: null,
    })
  }

  function saveExercise() {
    if (!editingState.dayKey || !editingState.draft) {
      return
    }

    const rpeError = getRpeValidationError(editingState.draft.rpe)

    if (rpeError) {
      return
    }

    const nextExercise = buildExerciseSavePayload(editingState.draft)

    if (!nextExercise.name) {
      return
    }

    if (editingState.exerciseId === NEW_EXERCISE_ID) {
      onWeeklyPlanChange((currentPlan) =>
        addExerciseToDay(currentPlan, editingState.dayKey, nextExercise),
      )
    } else {
      onWeeklyPlanChange((currentPlan) =>
        updateExerciseInDay(currentPlan, editingState.dayKey, editingState.exerciseId, {
          ...nextExercise,
          id: editingState.exerciseId,
        }),
      )
    }

    cancelEditing()
  }

  function deleteExercise(dayKey, exerciseId) {
    onWeeklyPlanChange((currentPlan) => removeExerciseFromDay(currentPlan, dayKey, exerciseId))

    setEditingState((current) => {
      if (current.dayKey === dayKey && current.exerciseId === exerciseId) {
        return { dayKey: null, exerciseId: null, draft: null }
      }

      return current
    })
  }

  const currentRpeError = editingState.draft ? getRpeValidationError(editingState.draft.rpe) : null

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 2</p>
      <h2 className="mt-3 text-2xl font-bold text-white">训练计划</h2>
      <p className="mt-4 max-w-3xl leading-7 text-slate-300">
        这里已经接入真实的训练计划维护能力。你可以修改每天训练类型，新增、编辑、删除动作，
        每次保存都会写回 <code>fitloop_weeklyPlan</code>，刷新页面后依然保留。
      </p>

      <div className="mt-8 overflow-x-auto pb-2">
        <div className="flex min-w-max gap-4">
          {dayColumns.map(({ dayKey, plan, widthClassName }) => (
            <PlanDayCard
              dayKey={dayKey}
              dayTypeOptions={dayTypeOptions}
              editingExerciseId={editingState.dayKey === dayKey ? editingState.exerciseId : null}
              exerciseDraft={
                editingState.dayKey === dayKey
                  ? editingState.draft
                  : createEmptyExerciseDraft(oneRmOptions)
              }
              expanded={expandedDay === dayKey}
              key={dayKey}
              onCancelEditing={cancelEditing}
              onDayTypeChange={(nextType) => handleDayTypeChange(dayKey, nextType)}
              onDeleteExercise={(exerciseId) => deleteExercise(dayKey, exerciseId)}
              onDraftChange={updateDraft}
              onEditExercise={(exercise) => startEditExercise(dayKey, exercise)}
              onSaveExercise={saveExercise}
              onStartAdd={() => startAddExercise(dayKey)}
              onToggle={() => toggleDay(dayKey)}
              oneRmOptions={oneRmOptions}
              plan={plan}
              profile={profile}
              rpeError={editingState.dayKey === dayKey ? currentRpeError : null}
              widthClassName={widthClassName}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

export default PlanTab
