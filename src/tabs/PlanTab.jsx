import { useMemo, useState } from 'react'
import PlanDayCard, { createEmptyExerciseDraft } from '../components/PlanDayCard.jsx'
import { createExerciseDraft, draftToExercise } from '../utils/exerciseForm.js'
import { getExerciseKg, getTodayKey } from '../utils/calc.js'
import {
  addExerciseToDay,
  getPlanDayTypes,
  getWeekdayOrder,
  removeExerciseFromDay,
  updateDayType,
  updateExerciseInDay,
} from '../utils/weeklyPlan.js'

const NEW_EXERCISE_ID = '__new__'

function getExerciseDisplay(profile, exercise) {
  if (exercise.ref1RM) {
    const actualKg = getExerciseKg(exercise, profile.oneRM)
    return `${Math.round((exercise.pct ?? 0) * 100)}% -> ${actualKg}kg`
  }

  return `${getExerciseKg(exercise, profile.oneRM)}kg`
}

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
  const days = getWeekdayOrder().map((dayKey) => [
    dayKey,
    weeklyPlan?.[dayKey] ?? { type: 'rest', exercises: [] },
  ])

  const exerciseSummaries = useMemo(() => {
    const summaries = {}

    days.forEach(([, plan]) => {
      plan.exercises.forEach((exercise) => {
        summaries[exercise.id] = `${getExerciseDisplay(profile, exercise)} · ${exercise.sets} 组 × ${exercise.reps} 次`
      })
    })

    return summaries
  }, [days, profile])

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

    const nextExercise = draftToExercise(editingState.draft)

    if (!nextExercise.name) {
      return
    }

    if (editingState.exerciseId === NEW_EXERCISE_ID) {
      onWeeklyPlanChange((currentPlan) =>
        addExerciseToDay(currentPlan, editingState.dayKey, nextExercise),
      )
    } else {
      onWeeklyPlanChange((currentPlan) =>
        updateExerciseInDay(
          currentPlan,
          editingState.dayKey,
          editingState.exerciseId,
          {
            ...nextExercise,
            id: editingState.exerciseId,
          },
        ),
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

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 2</p>
      <h2 className="mt-3 text-2xl font-bold text-white">训练计划</h2>
      <p className="mt-4 max-w-3xl leading-7 text-slate-300">
        这里已经接入真实的训练计划维护能力。你可以修改每天训练类型，新增、编辑、删除动作，
        每次保存都会写回 <code>fitloop_weeklyPlan</code>，刷新页面后仍然保留。
      </p>

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {days.map(([dayKey, plan]) => (
          <PlanDayCard
            dayKey={dayKey}
            dayTypeOptions={dayTypeOptions}
            editingExerciseId={editingState.dayKey === dayKey ? editingState.exerciseId : null}
            exerciseDraft={editingState.dayKey === dayKey ? editingState.draft : createEmptyExerciseDraft(oneRmOptions)}
            exerciseSummaries={exerciseSummaries}
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
          />
        ))}
      </div>
    </section>
  )
}

export default PlanTab
