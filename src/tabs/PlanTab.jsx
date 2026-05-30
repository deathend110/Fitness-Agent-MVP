import { useMemo, useState } from 'react'
import PlanDayCard, { createEmptyExerciseDraft } from '../components/PlanDayCard.jsx'
import PlanWeekGrid from '../components/plan-grid/PlanWeekGrid.jsx'
import PlanWeekGridColumn from '../components/plan-grid/PlanWeekGridColumn.jsx'
import PlanHeaderToolbar from '../components/plan-header/PlanHeaderToolbar.jsx'
import { getTodayKey, getTodayStr } from '../utils/calc.js'
import { buildExerciseSavePayload, getRpeValidationError } from '../utils/exerciseForm.js'
import { buildPlanHeaderModel } from '../utils/planHeader.js'
import { buildWeeklyPlanLayoutModel } from '../utils/planLayout.js'
import {
  NEW_PLAN_EXERCISE_ID,
  clearPlanEditorState,
  clearPlanEditorStateAfterDelete,
  isPlanEditorTarget,
  startAddingExercise,
  startEditingExercise,
  updatePlanEditorDraft,
} from '../utils/planEditorState.js'
import {
  addExerciseToDay,
  getPlanDayTypes,
  removeExerciseFromDay,
  updateDayType,
  updateExerciseInDay,
} from '../utils/weeklyPlan.js'

function getOneRmOptions(profile = {}) {
  return [
    { value: 'squat', label: `深蹲 ${profile.oneRM?.squat ?? '--'}kg` },
    { value: 'bench', label: `卧推 ${profile.oneRM?.bench ?? '--'}kg` },
    { value: 'deadlift', label: `硬拉 ${profile.oneRM?.deadlift ?? '--'}kg` },
  ]
}

function PlanTab({ profile, weeklyPlan, onWeeklyPlanChange }) {
  const [editingState, setEditingState] = useState(() => clearPlanEditorState())

  const oneRmOptions = getOneRmOptions(profile)
  const dayTypeOptions = getPlanDayTypes()
  void getTodayKey
  const layoutModel = useMemo(() => buildWeeklyPlanLayoutModel(weeklyPlan), [weeklyPlan])
  // 头部周信息优先复用 weeklyPlan 内的真实元数据，日期基准必须传入可解析的真实日期字符串。
  const headerModel = useMemo(
    () =>
      buildPlanHeaderModel({
        referenceDate: getTodayStr(),
        weeklyPlan,
      }),
    [weeklyPlan],
  )

  function handleDayTypeChange(dayKey, nextType) {
    onWeeklyPlanChange((currentPlan) => updateDayType(currentPlan, dayKey, nextType))
  }

  function handleStartAddExercise(dayKey) {
    setEditingState(startAddingExercise(dayKey, oneRmOptions))
  }

  function handleStartEditExercise(dayKey, exercise) {
    setEditingState(startEditingExercise(dayKey, exercise, oneRmOptions))
  }

  function updateDraft(nextDraft) {
    setEditingState((current) => updatePlanEditorDraft(current, nextDraft))
  }

  function cancelEditing() {
    setEditingState(clearPlanEditorState())
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
    if (!nextExercise?.name) {
      return
    }

    if (editingState.exerciseId === NEW_PLAN_EXERCISE_ID) {
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
    setEditingState((current) => clearPlanEditorStateAfterDelete(current, dayKey, exerciseId))
  }

  const currentRpeError = editingState.draft ? getRpeValidationError(editingState.draft.rpe) : null

  return (
    <div className="space-y-5">
      <PlanHeaderToolbar headerModel={headerModel} />

      <PlanWeekGrid
        layoutModel={layoutModel}
        renderColumn={(column) => {
          const isEditingDay = editingState.dayKey === column.dayKey
          const editingExerciseId = isEditingDay ? editingState.exerciseId : null

          return (
            <PlanWeekGridColumn column={column} key={column.dayKey}>
              <PlanDayCard
                dayKey={column.dayKey}
                dayLabel={column.dayLabel}
                dayTypeOptions={dayTypeOptions}
                editingExerciseId={editingExerciseId}
                exerciseDraft={
                  isEditingDay ? editingState.draft : createEmptyExerciseDraft(oneRmOptions)
                }
                isExerciseEditing={(exerciseId) =>
                  isPlanEditorTarget(editingState, column.dayKey, exerciseId)
                }
                isTrainingDay={column.isTrainingDay}
                onCancelEditing={cancelEditing}
                onDayTypeChange={(nextType) => handleDayTypeChange(column.dayKey, nextType)}
                onDeleteExercise={(exerciseId) => deleteExercise(column.dayKey, exerciseId)}
                onDraftChange={updateDraft}
                onEditExercise={(exercise) => handleStartEditExercise(column.dayKey, exercise)}
                onSaveExercise={saveExercise}
                onStartAdd={() => handleStartAddExercise(column.dayKey)}
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
  )
}

export default PlanTab
