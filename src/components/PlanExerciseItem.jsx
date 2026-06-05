import { useEffect, useRef, useState } from 'react'
import { buildPlanExerciseCardModel } from '../utils/planExerciseCard.js'
import {
  executePlanExerciseMenuAction,
  getPlanExerciseMenuActions,
} from '../utils/planEditorState.js'
import PlanExerciseEditorCard from './PlanExerciseEditorCard.jsx'

export function isPlanExerciseNoDragTarget(target) {
  return Boolean(
    target && typeof target.closest === 'function' && target.closest('[data-no-drag="true"]'),
  )
}

export function createPlanExerciseDragState() {
  let dragBlocked = false
  let dropDepth = 0
  let dropActive = false

  return {
    get dragBlocked() {
      return dragBlocked
    },
    get dropDepth() {
      return dropDepth
    },
    get dropActive() {
      return dropActive
    },
    markPointerDown(target) {
      dragBlocked = isPlanExerciseNoDragTarget(target)
      return dragBlocked
    },
    consumeDragBlock() {
      const blocked = dragBlocked
      dragBlocked = false
      return blocked
    },
    enter(enabled) {
      if (!enabled) {
        return dropActive
      }

      dropDepth += 1
      dropActive = true
      return dropActive
    },
    leave() {
      dropDepth = Math.max(0, dropDepth - 1)
      dropActive = dropDepth > 0
      return dropActive
    },
    resetDrop() {
      dropDepth = 0
      dropActive = false
      return dropActive
    },
  }
}

export function shouldBlockPlanExerciseDragStart(dragEnabled, dragState) {
  const blocked = dragState.consumeDragBlock()

  if (!dragEnabled) {
    return true
  }

  return blocked
}

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
  dragEnabled = false,
  onMoveExercise,
}) {
  const cardModel = buildPlanExerciseCardModel(exercise, profile)
  const menuActions = getPlanExerciseMenuActions()
  const [menuOpen, setMenuOpen] = useState(false)
  const [dropActive, setDropActive] = useState(false)
  const dragStateRef = useRef(createPlanExerciseDragState())
  const menuRef = useRef(null)

  useEffect(() => {
    if (!menuOpen) {
      return undefined
    }

    // 局部菜单只服务单个动作卡片，点外部或按 Esc 时立即关闭，避免悬挂出全局弹层体系。
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

  function handleDragStart(event) {
    if (shouldBlockPlanExerciseDragStart(dragEnabled, dragStateRef.current)) {
      event.preventDefault()
      return
    }

    dragStateRef.current.resetDrop()
    setDropActive(false)
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', exercise.id)
  }

  function handleDrop(event) {
    if (!dragEnabled) {
      return
    }

    event.preventDefault()
    dragStateRef.current.resetDrop()
    setDropActive(false)
    const fromExerciseId = event.dataTransfer.getData('text/plain')

    if (!fromExerciseId || fromExerciseId === exercise.id) {
      return
    }

    onMoveExercise?.(fromExerciseId, exercise.id)
  }

  return (
    <li
      className={`rounded-xl border px-3 py-3 shadow-sm shadow-black/20 ${cardModel.cardClassName} ${
        dropActive ? 'ring-2 ring-fitloop-orange/70' : ''
      }`}
      data-exercise-id={exercise.id}
      draggable={dragEnabled}
      onDragEnd={() => {
        dragStateRef.current.resetDrop()
        setDropActive(false)
      }}
      onDragEnter={(event) => {
        if (!dragEnabled) {
          return
        }

        event.preventDefault()
        setDropActive(dragStateRef.current.enter(true))
      }}
      onDragLeave={() => {
        setDropActive(dragStateRef.current.leave())
      }}
      onDragOver={(event) => {
        if (!dragEnabled) {
          return
        }

        event.preventDefault()
      }}
      onDragStart={handleDragStart}
      onDrop={handleDrop}
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
        <div className="space-y-2.5">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              <div className="flex min-w-0 items-start gap-2">
                <p
                  className={`min-w-0 flex-1 break-words text-[17px] font-extrabold leading-6 ${cardModel.titleClassName}`}
                >
                  {cardModel.name}
                </p>
                <span
                  className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${cardModel.tierBadgeClassName}`}
                >
                  {cardModel.tierLabel}
                </span>
              </div>
              <p className={`mt-1 min-h-[1.25rem] text-[11px] leading-5 ${cardModel.topMetaClassName}`}>
                {cardModel.topMetaLabel || '\u00A0'}
              </p>
            </div>

            <div
              className="relative shrink-0"
              data-no-drag="true"
              onPointerDownCapture={(event) => {
                dragStateRef.current.markPointerDown(event.target)
              }}
              ref={menuRef}
            >
              <button
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                aria-label="更多操作"
                className={cardModel.actionSlotClassName}
                onClick={() => setMenuOpen((current) => !current)}
                title="更多操作"
                type="button"
              >
                ⋮
              </button>

              {menuOpen ? (
                <div
                  className="absolute right-0 top-8 z-20 min-w-32 rounded-xl border border-fitloop-line bg-fitloop-panel p-1.5 shadow-lg shadow-black/30"
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

          <div className="flex items-end justify-between gap-3">
            <span
              className={`inline-flex shrink-0 items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${cardModel.volumePillClassName}`}
            >
              {cardModel.volumePill.value}
            </span>

            <div className="min-w-0 text-right">
              <p className={`break-words text-base font-extrabold leading-none ${cardModel.weightValueClassName}`}>
                {cardModel.weightValue}
                {cardModel.weightUnitLabel ? (
                  <span className={`ml-1 text-sm font-bold ${cardModel.weightUnitClassName}`}>
                    {cardModel.weightUnitLabel}
                  </span>
                ) : null}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-dashed border-fitloop-line/70 pt-2 text-[11px]">
            <span
              className={`inline-flex shrink-0 items-center rounded-md border px-1.5 py-0.5 font-medium ${cardModel.effortPillClassName}`}
            >
              {cardModel.effortPill.value}
            </span>
            <p className={`min-w-0 flex-1 truncate text-right leading-5 ${cardModel.noteClassName}`}>
              {cardModel.noteLabel}
            </p>
          </div>
        </div>
      )}
    </li>
  )
}

export default PlanExerciseItem
