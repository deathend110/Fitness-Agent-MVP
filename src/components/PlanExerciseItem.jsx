import { useEffect, useRef, useState } from 'react'
import { buildPlanExerciseCardModel } from '../utils/planExerciseCard.js'
import {
  executePlanExerciseMenuAction,
  getPlanExerciseMenuActions,
} from '../utils/planEditorState.js'
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
  const menuActions = getPlanExerciseMenuActions()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    if (!menuOpen) {
      return undefined
    }

    // 局部菜单只服务单个动作卡片，点击外部或按 Esc 时立即关闭，避免挂出全局弹窗体系。
    function handlePointerDown(event) {
      if (!menuRef.current?.contains(event.target)) {
        setMenuOpen(false)
      }
    }

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [menuOpen])

  function handleMenuAction(actionKey) {
    const didHandle = executePlanExerciseMenuAction(actionKey, {
      edit: onEdit,
      delete: onDelete,
    })

    if (didHandle) {
      setMenuOpen(false)
    }
  }

  return (
    <li
      className={`rounded-2xl border px-3 py-3.5 shadow-sm shadow-black/20 ${cardModel.cardClassName}`}
    >
      {isEditing ? (
        <PlanExerciseEditorCard
          oneRmOptions={oneRmOptions}
          onCancel={onCancel}
          onDraftChange={onDraftChange}
          onSave={onSave}
          rpeError={rpeError}
          saveLabel="保存动作"
          title={`编辑动作 · ${cardModel.name}`}
          value={draft}
        />
      ) : (
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <p
                  className={`min-w-0 break-words text-[15px] font-semibold leading-6 ${cardModel.titleClassName}`}
                >
                  {cardModel.name}
                </p>
                <span
                  className={`shrink-0 rounded-full border px-2 py-1 text-[11px] font-semibold ${cardModel.tierBadgeClassName}`}
                >
                  {cardModel.tierLabel}
                </span>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] leading-5 text-slate-400">
                <span
                  className={`rounded-full border px-2 py-0.5 font-medium ${cardModel.loadBadgeClassName}`}
                >
                  {cardModel.loadBadgeLabel}
                </span>
                <span className="min-w-0 break-words">{cardModel.loadDetailLabel}</span>
              </div>

              <p className="mt-2 text-xs leading-5 text-slate-400">{cardModel.summaryLabel}</p>
            </div>

            <div className="relative flex shrink-0 items-start gap-2" ref={menuRef}>
              <button
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                aria-label="更多操作"
                className={cardModel.actionSlotClassName}
                onClick={() => setMenuOpen((current) => !current)}
                title="更多操作"
                type="button"
              >
                ...
              </button>

              {menuOpen ? (
                <div
                  className="absolute right-0 top-10 z-20 min-w-32 rounded-xl border border-fitloop-line bg-fitloop-panel p-1.5 shadow-lg shadow-black/30"
                  role="menu"
                >
                  {menuActions.map((action) => (
                    <button
                      className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition ${
                        action.tone === 'danger'
                          ? 'text-rose-300 hover:bg-rose-500/10'
                          : 'text-slate-200 hover:bg-white/5'
                      }`}
                      key={action.key}
                      onClick={() => handleMenuAction(action.key)}
                      role="menuitem"
                      type="button"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {cardModel.metricItems.map((item) => (
              <div
                className="min-w-0 rounded-xl border border-fitloop-line/60 bg-black/10 px-2.5 py-2"
                key={item.key}
              >
                <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
                  {item.label}
                </p>
                <p
                  className={`mt-1 break-words text-sm font-semibold leading-5 ${cardModel.metricValueClassName}`}
                >
                  {item.value}
                </p>
                <p className="mt-1 break-words text-[11px] leading-4 text-slate-400">
                  {item.detail}
                </p>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-fitloop-line/60 bg-black/10 px-3 py-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
                备注
              </p>
              <span className="rounded-full border border-fitloop-line/70 bg-fitloop-panel px-2 py-0.5 text-[10px] font-medium text-slate-400">
                {cardModel.effortLabel}
              </span>
            </div>
            <p className={`mt-2 break-words text-xs leading-5 ${cardModel.noteClassName}`}>
              {cardModel.noteLabel}
            </p>
          </div>
        </div>
      )}
    </li>
  )
}

export default PlanExerciseItem
