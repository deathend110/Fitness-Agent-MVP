import ExerciseEditor from './ExerciseEditor.jsx'
import PlanDayCardButton from './PlanDayCardButton.jsx'

function PlanExerciseEditorCard({
  value,
  oneRmOptions,
  onDraftChange,
  onSave,
  onCancel,
  rpeError,
  saveLabel,
  dashed = false,
}) {
  const cardClassName = dashed
    ? 'space-y-3 rounded-md border border-dashed border-fitloop-line p-3'
    : 'space-y-3'

  return (
    <div className={cardClassName}>
      <ExerciseEditor
        oneRmOptions={oneRmOptions}
        onChange={onDraftChange}
        rpeError={rpeError}
        value={value}
      />
      <div className="flex flex-wrap gap-2">
        <PlanDayCardButton kind="primary" onClick={onSave}>
          {saveLabel}
        </PlanDayCardButton>
        <PlanDayCardButton onClick={onCancel}>取消</PlanDayCardButton>
      </div>
    </div>
  )
}

export default PlanExerciseEditorCard
