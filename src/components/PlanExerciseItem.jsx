import { buildPlanExerciseCardModel } from '../utils/planExerciseCard.js'
import PlanDayCardButton from './PlanDayCardButton.jsx'
import PlanExerciseEditorCard from './PlanExerciseEditorCard.jsx'

function PlanExerciseItem({
  exercise,
  isEditing,
  draft,
  onEdit,
  onDraftChange,
  onSave,
  onCancel,
  onDelete,
  oneRmOptions,
  profile,
  rpeError,
}) {
  const cardModel = buildPlanExerciseCardModel(exercise, profile)

  return (
    <li className={`rounded-md border p-3 ${cardModel.cardClassName}`}>
      {isEditing ? (
        <PlanExerciseEditorCard
          oneRmOptions={oneRmOptions}
          onCancel={onCancel}
          onDraftChange={onDraftChange}
          onSave={onSave}
          rpeError={rpeError}
          saveLabel="保存动作"
          value={draft}
        />
      ) : (
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className={`truncate text-base font-semibold ${cardModel.titleClassName}`}>
                {cardModel.name}
              </p>
              <p className="mt-1 text-xs text-slate-400">{cardModel.summaryLabel}</p>
            </div>
            <span
              className={`shrink-0 rounded-full border px-2 py-1 text-[11px] font-semibold ${cardModel.tierBadgeClassName}`}
            >
              {cardModel.tierLabel}
            </span>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {cardModel.metricItems.map((item) => (
              <div
                className="rounded-md border border-fitloop-line/60 bg-black/10 px-3 py-2"
                key={item.label}
              >
                <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">
                  {item.label}
                </p>
                <p className={`mt-1 text-sm font-semibold ${cardModel.metricValueClassName}`}>
                  {item.value}
                </p>
              </div>
            ))}
          </div>

          <div className="rounded-md border border-fitloop-line/60 bg-black/10 px-3 py-2">
            <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">备注</p>
            <p className={`mt-1 text-xs leading-6 ${cardModel.noteClassName}`}>
              {cardModel.noteLabel}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <PlanDayCardButton onClick={onEdit}>编辑</PlanDayCardButton>
            <PlanDayCardButton kind="danger" onClick={onDelete}>
              删除
            </PlanDayCardButton>
          </div>
        </div>
      )}
    </li>
  )
}

export default PlanExerciseItem
