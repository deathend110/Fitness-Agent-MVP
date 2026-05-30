import ExerciseEditor from './ExerciseEditor.jsx'
import { createExerciseDraft } from '../utils/exerciseForm.js'
import { buildPlanExerciseCardModel } from '../utils/planExerciseCard.js'
import { getPlanDayTypeSuggestions } from '../utils/weeklyPlan.js'

function getButtonClassName(kind = 'secondary') {
  if (kind === 'danger') {
    return 'rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm font-medium text-rose-200 transition hover:border-rose-400 hover:bg-rose-500/20'
  }

  if (kind === 'primary') {
    return 'rounded-md border border-fitloop-orange bg-fitloop-orange px-3 py-2 text-sm font-medium text-white transition hover:opacity-90'
  }

  return 'rounded-md border border-fitloop-line bg-fitloop-panel/70 px-3 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-400 hover:text-white'
}

function ExerciseItem({
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
        <div className="space-y-3">
          <ExerciseEditor
            oneRmOptions={oneRmOptions}
            onChange={onDraftChange}
            rpeError={rpeError}
            value={draft}
          />
          <div className="flex flex-wrap gap-2">
            <button className={getButtonClassName('primary')} onClick={onSave} type="button">
              保存动作
            </button>
            <button className={getButtonClassName()} onClick={onCancel} type="button">
              取消
            </button>
          </div>
        </div>
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
                <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{item.label}</p>
                <p className={`mt-1 text-sm font-semibold ${cardModel.metricValueClassName}`}>
                  {item.value}
                </p>
              </div>
            ))}
          </div>

          <div className="rounded-md border border-fitloop-line/60 bg-black/10 px-3 py-2">
            <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">备注</p>
            <p className={`mt-1 text-xs leading-6 ${cardModel.noteClassName}`}>{cardModel.noteLabel}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button className={getButtonClassName()} onClick={onEdit} type="button">
              编辑
            </button>
            <button className={getButtonClassName('danger')} onClick={onDelete} type="button">
              删除
            </button>
          </div>
        </div>
      )}
    </li>
  )
}

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
      <button
        aria-expanded={expanded}
        className="flex w-full items-center justify-between gap-3 text-left"
        onClick={onToggle}
        type="button"
      >
        <div className="min-w-0">
          <h3 className="truncate text-lg font-semibold text-white">{dayKey}</h3>
          <p className="mt-1 text-sm text-slate-400">{plan.exercises.length} 个动作</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-fitloop-orange/15 px-2 py-1 text-xs font-medium text-fitloop-orange">
            {plan.type}
          </span>
          <span className="text-xs text-slate-400">{expanded ? '收起' : '展开'}</span>
        </div>
      </button>

      <div className="mt-3 rounded-md border border-fitloop-line/60 bg-black/10 px-3 py-2">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">训练日</p>
        <p className="mt-1 text-sm font-semibold text-slate-100">{plan.type}</p>
        <p className="mt-1 text-xs text-slate-400">{plan.exercises.length} 个动作</p>
      </div>

      {expanded ? (
        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <label className="block space-y-2">
              <span className="text-sm text-slate-300">训练类型</span>
              <input
                className="w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition focus:border-fitloop-orange"
                list={dayTypeListId}
                onChange={(event) => onDayTypeChange(event.target.value)}
                value={plan.type}
              />
            </label>
            <datalist id={dayTypeListId}>
              {dayTypeSuggestions.map((option) => (
                <option key={option} value={option} />
              ))}
            </datalist>
            <div className="flex flex-wrap gap-2">
              {dayTypeOptions.map((option) => (
                <button
                  className={getButtonClassName()}
                  key={option}
                  onClick={() => onDayTypeChange(option)}
                  type="button"
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button className={getButtonClassName('primary')} onClick={onStartAdd} type="button">
              新增动作
            </button>
          </div>

          {editingExerciseId === '__new__' ? (
            <div className="space-y-3 rounded-md border border-dashed border-fitloop-line p-3">
              <ExerciseEditor
                oneRmOptions={oneRmOptions}
                onChange={onDraftChange}
                rpeError={rpeError}
                value={exerciseDraft}
              />
              <div className="flex flex-wrap gap-2">
                <button className={getButtonClassName('primary')} onClick={onSaveExercise} type="button">
                  保存新增动作
                </button>
                <button className={getButtonClassName()} onClick={onCancelEditing} type="button">
                  取消
                </button>
              </div>
            </div>
          ) : null}

          {plan.exercises.length === 0 ? (
            <p className="text-sm text-slate-400">
              当前还没有安排动作。即使训练类型设为 rest，也会保留已有动作，避免误删除历史计划。
            </p>
          ) : (
            <ul className="space-y-3">
              {plan.exercises.map((exercise) => (
                <ExerciseItem
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
