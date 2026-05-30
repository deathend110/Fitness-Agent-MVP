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
  title = '',
}) {
  const cardClassName = dashed
    ? 'space-y-3 rounded-xl border border-dashed border-fitloop-line bg-fitloop-ink/30 p-3'
    : 'space-y-3'

  return (
    <div className={cardClassName}>
      {title ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-semibold text-slate-100">{title}</p>
          <span className="text-[11px] text-slate-400">保存后会写回当前日期的训练计划</span>
        </div>
      ) : null}

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
