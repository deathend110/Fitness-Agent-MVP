import { useMemo, useState } from 'react'
import PlanDayCard, { createEmptyExerciseDraft } from '../components/PlanDayCard.jsx'
import PlanWeekGrid from '../components/plan-grid/PlanWeekGrid.jsx'
import PlanWeekGridColumn from '../components/plan-grid/PlanWeekGridColumn.jsx'
import PlanHeaderToolbar from '../components/plan-header/PlanHeaderToolbar.jsx'
import { getTodayKey } from '../utils/calc.js'
import {
  buildExerciseSavePayload,
  createExerciseDraft,
  getRpeValidationError,
} from '../utils/exerciseForm.js'
import { buildPlanHeaderModel } from '../utils/planHeader.js'
import { buildWeeklyPlanLayoutModel } from '../utils/planLayout.js'
import {
  addExerciseToDay,
  getPlanDayTypes,
  removeExerciseFromDay,
  updateDayType,
  updateExerciseInDay,
} from '../utils/weeklyPlan.js'

const NEW_EXERCISE_ID = '__new__'

function getOneRmOptions(profile = {}) {
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
  const layoutModel = useMemo(() => buildWeeklyPlanLayoutModel(weeklyPlan), [weeklyPlan])
  // 头部展示信息集中在独立模型中，避免页面组件继续承担日期格式和图例拼装职责。
  const headerModel = useMemo(() => buildPlanHeaderModel(), [])

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
    <section className="rounded-[1.5rem] border border-fitloop-line bg-fitloop-panel/90 p-6 shadow-2xl shadow-black/20 xl:p-7">
      <div className="space-y-5">
        <PlanHeaderToolbar headerModel={headerModel} />

        <p className="max-w-3xl text-sm leading-7 text-slate-300">
          这里已经接入真实的训练计划维护能力。你可以修改每天训练类型，新增、编辑、删除动作，
          每次保存都会写回 <code>fitloop_weeklyPlan</code>，刷新页面后依然保留。
        </p>

        <div className="rounded-[1.25rem] border border-fitloop-line bg-fitloop-ink/30 p-3 shadow-sm shadow-black/20 xl:p-4">
          <PlanWeekGrid
            layoutModel={layoutModel}
            renderColumn={(column) => {
              const isEditingDay = editingState.dayKey === column.dayKey

              return (
                <PlanWeekGridColumn
                  column={column}
                  isExpanded={expandedDay === column.dayKey}
                  key={column.dayKey}
                >
                  <PlanDayCard
                    dayKey={column.dayKey}
                    dayLabel={column.dayLabel}
                    dayTypeOptions={dayTypeOptions}
                    editingExerciseId={isEditingDay ? editingState.exerciseId : null}
                    exerciseDraft={
                      isEditingDay ? editingState.draft : createEmptyExerciseDraft(oneRmOptions)
                    }
                    expanded={expandedDay === column.dayKey}
                    isTrainingDay={column.isTrainingDay}
                    onCancelEditing={cancelEditing}
                    onDayTypeChange={(nextType) => handleDayTypeChange(column.dayKey, nextType)}
                    onDeleteExercise={(exerciseId) => deleteExercise(column.dayKey, exerciseId)}
                    onDraftChange={updateDraft}
                    onEditExercise={(exercise) => startEditExercise(column.dayKey, exercise)}
                    onSaveExercise={saveExercise}
                    onStartAdd={() => startAddExercise(column.dayKey)}
                    onToggle={() => toggleDay(column.dayKey)}
                    oneRmOptions={oneRmOptions}
                    plan={column.plan}
                    profile={profile}
                    rpeError={isEditingDay ? currentRpeError : null}
                  />
                </PlanWeekGridColumn>
              )
            }}
          />
        </div>
      </div>
    </section>
  )
}

export default PlanTab
