import PlanDayCardButton from './PlanDayCardButton.jsx'
import PlanDayCardHeader from './PlanDayCardHeader.jsx'
import PlanDayTypeSection from './PlanDayTypeSection.jsx'
import PlanExerciseEditorCard from './PlanExerciseEditorCard.jsx'
import PlanExerciseItem from './PlanExerciseItem.jsx'
import PlanDayEmptyState from './plan-rest/PlanDayEmptyState.jsx'
import PlanRestDayPanel from './plan-rest/PlanRestDayPanel.jsx'
import { createExerciseDraft } from '../utils/exerciseForm.js'
import { NEW_PLAN_EXERCISE_ID } from '../utils/planEditorState.js'
import { buildPlanDayDisplayModel } from '../utils/planDayDisplay.js'
import { getPlanDayTypeSuggestions } from '../utils/weeklyPlan.js'

function PlanDayCard({
  dayKey,
  dayLabel,
  plan,
  isTrainingDay,
  dayTypeOptions,
  editingExerciseId,
  isExerciseEditing,
  exerciseDraft,
  oneRmOptions,
  onDayTypeChange,
  onStartAdd,
  onEditExercise,
  onDraftChange,
  onSaveExercise,
  onCancelEditing,
  onDeleteExercise,
  profile,
  rpeError,
}) {
  const dayTypeListId = `${dayKey}-day-type-options`
  const dayTypeSuggestions = getPlanDayTypeSuggestions(plan.type)
  const displayModel = buildPlanDayDisplayModel({
    dayLabel,
    plan,
    isTrainingDay,
  })
  const showNewExerciseEditor =
    displayModel.showAddExerciseButton && editingExerciseId === NEW_PLAN_EXERCISE_ID
  const hasExercises = plan.exercises.length > 0
  const showDayTypeSection = displayModel.showDayTypeSection !== false
  const isCompactRestDay = displayModel.layout === 'rest-compact'
  // 新增动作时优先展示新增表单，避免和空状态提示同时抢占注意力。
  const visibleEmptyState = showNewExerciseEditor ? null : displayModel.emptyState

  return (
    <div className="min-w-0">
      <PlanDayCardHeader
        dayLabel={dayLabel}
        displayModel={displayModel}
        exerciseCount={plan.exercises.length}
        isTrainingDay={isTrainingDay}
        planType={plan.type}
      />

      <div className={`mt-4 ${isCompactRestDay ? 'flex min-h-[9.5rem] flex-1 flex-col' : 'space-y-4'}`}>
        {showDayTypeSection ? (
          <PlanDayTypeSection
            dayTypeListId={dayTypeListId}
            dayTypeOptions={dayTypeOptions}
            dayTypeSuggestions={dayTypeSuggestions}
            onDayTypeChange={onDayTypeChange}
            planType={plan.type}
          />
        ) : null}

        {displayModel.showAddExerciseButton ? (
          <div className="flex flex-wrap gap-2">
            <PlanDayCardButton kind="primary" onClick={onStartAdd}>
              添加动作
            </PlanDayCardButton>
          </div>
        ) : null}

        {showNewExerciseEditor ? (
          <PlanExerciseEditorCard
            dashed
            oneRmOptions={oneRmOptions}
            onCancel={onCancelEditing}
            onDraftChange={onDraftChange}
            onSave={onSaveExercise}
            rpeError={rpeError}
            saveLabel="保存新增动作"
            title="新增动作"
            value={exerciseDraft}
          />
        ) : null}

        {visibleEmptyState ? (
          visibleEmptyState.tone === 'rest' ? (
            <PlanRestDayPanel
              description={visibleEmptyState.description}
              descriptionLines={visibleEmptyState.descriptionLines}
              title={visibleEmptyState.title}
            />
          ) : (
            <PlanDayEmptyState
              description={visibleEmptyState.description}
              title={visibleEmptyState.title}
              tone={visibleEmptyState.tone}
            />
          )
        ) : null}

        {displayModel.historyHint ? (
          <p className="rounded-2xl border border-fitloop-line/70 bg-fitloop-panel px-3 py-3 text-xs leading-6 text-slate-400">
            {displayModel.historyHint}
          </p>
        ) : null}

        {hasExercises ? (
          <ul className="space-y-3">
            {plan.exercises.map((exercise) => (
              <PlanExerciseItem
                draft={exerciseDraft}
                exercise={exercise}
                isEditing={isExerciseEditing(exercise.id)}
                key={exercise.id}
                onCancel={onCancelEditing}
                onDelete={() => onDeleteExercise(exercise.id)}
                onDraftChange={onDraftChange}
                onEdit={() => onEditExercise(exercise)}
                onSave={onSaveExercise}
                oneRmOptions={oneRmOptions}
                profile={profile}
                rpeError={rpeError}
              />
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  )
}

export function createEmptyExerciseDraft(oneRmOptions = []) {
  const fallbackRef = oneRmOptions[0]?.value ?? 'squat'

  return createExerciseDraft({}, fallbackRef)
}

export default PlanDayCard
