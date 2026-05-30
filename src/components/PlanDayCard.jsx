import PlanDayCardButton from './PlanDayCardButton.jsx'
import PlanDayCardHeader from './PlanDayCardHeader.jsx'
import PlanDayTypeSection from './PlanDayTypeSection.jsx'
import PlanExerciseEditorCard from './PlanExerciseEditorCard.jsx'
import PlanExerciseItem from './PlanExerciseItem.jsx'
import { createExerciseDraft } from '../utils/exerciseForm.js'
import { getPlanDayTypeSuggestions } from '../utils/weeklyPlan.js'

function PlanDayCard({
  dayKey,
  plan,
  expanded,
  dayTypeOptions,
  editingExerciseId,
  exerciseDraft,
  oneRmOptions,
  onToggle,
  onDayTypeChange,
  onStartAdd,
  onEditExercise,
  onDraftChange,
  onSaveExercise,
  onCancelEditing,
  onDeleteExercise,
  profile,
  rpeError,
  widthClassName = 'min-w-[12rem] flex-[1_1_12rem]',
}) {
  const dayTypeListId = `${dayKey}-day-type-options`
  const dayTypeSuggestions = getPlanDayTypeSuggestions(plan.type)

  return (
    <article
      className={`flex h-full flex-col rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4 ${widthClassName}`}
    >
      <PlanDayCardHeader
        dayKey={dayKey}
        expanded={expanded}
        exerciseCount={plan.exercises.length}
        onToggle={onToggle}
        planType={plan.type}
      />

      {expanded ? (
        <div className="mt-4 space-y-4">
          <PlanDayTypeSection
            dayTypeListId={dayTypeListId}
            dayTypeOptions={dayTypeOptions}
            dayTypeSuggestions={dayTypeSuggestions}
            onDayTypeChange={onDayTypeChange}
            planType={plan.type}
          />

          <div className="flex flex-wrap gap-2">
            <PlanDayCardButton kind="primary" onClick={onStartAdd}>
              新增动作
            </PlanDayCardButton>
          </div>

          {editingExerciseId === '__new__' ? (
            <PlanExerciseEditorCard
              dashed
              oneRmOptions={oneRmOptions}
              onCancel={onCancelEditing}
              onDraftChange={onDraftChange}
              onSave={onSaveExercise}
              rpeError={rpeError}
              saveLabel="保存新增动作"
              value={exerciseDraft}
            />
          ) : null}

          {plan.exercises.length === 0 ? (
            <p className="text-sm text-slate-400">
              当前还没有安排动作。即使训练类型设为 rest，也会保留已有动作，避免误删历史计划。
            </p>
          ) : (
            <ul className="space-y-3">
              {plan.exercises.map((exercise) => (
                <PlanExerciseItem
                  draft={exerciseDraft}
                  exercise={exercise}
                  isEditing={editingExerciseId === exercise.id}
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
          )}
        </div>
      ) : null}
    </article>
  )
}

export function createEmptyExerciseDraft(oneRmOptions = []) {
  const fallbackRef = oneRmOptions[0]?.value ?? 'squat'

  return createExerciseDraft({}, fallbackRef)
}

export default PlanDayCard
