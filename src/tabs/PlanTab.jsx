import { useMemo, useState } from 'react'
import { createBackendClient } from '../api/backendClient.js'
import PlanDayCard, { createEmptyExerciseDraft } from '../components/PlanDayCard.jsx'
import PlanWeekGrid from '../components/plan-grid/PlanWeekGrid.jsx'
import PlanWeekGridColumn from '../components/plan-grid/PlanWeekGridColumn.jsx'
import PlanHeaderToolbar from '../components/plan-header/PlanHeaderToolbar.jsx'
import PlanSettingsPanel from '../components/plan-settings/PlanSettingsPanel.jsx'
import {
  buildCreateCyclePlanPayload,
  createCyclePlanDraft,
} from '../utils/cyclePlanForm.js'
import {
  buildCreateCustomStrengthCyclePayload,
  createCustomStrengthDraft,
} from '../utils/customStrengthPlanForm.js'
import {
  buildCycleSettingsStatus,
  resolvePlanSettingsMode,
} from '../utils/cyclePlanView.js'
import { getTodayStr } from '../utils/calc.js'
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
  removeExerciseFromDay,
  reorderExercisesInDay,
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

function PlanTab({
  activeCyclePlan,
  effectiveWeeklyPlan,
  onActiveCyclePlanChange,
  onEffectiveWeeklyPlanChange,
  onPlanSourceChange,
  planSource = { activeSource: 'manual' },
  profile,
  weeklyPlan,
  onWeeklyPlanChange,
}) {
  const [editingState, setEditingState] = useState(() => clearPlanEditorState())
  const [isPlanSettingsOpen, setIsPlanSettingsOpen] = useState(false)
  const [cycleDraft, setCycleDraft] = useState(() =>
    createCyclePlanDraft(profile, activeCyclePlan),
  )
  const [customStrengthDraft, setCustomStrengthDraft] = useState(() =>
    createCustomStrengthDraft(),
  )
  const [planSettingsMode, setPlanSettingsMode] = useState(() =>
    resolvePlanSettingsMode(planSource, activeCyclePlan),
  )
  const [cyclePresets, setCyclePresets] = useState([])
  const [isCyclePresetsLoading, setIsCyclePresetsLoading] = useState(false)
  const [isCycleSubmitting, setIsCycleSubmitting] = useState(false)
  const [cycleActionMessage, setCycleActionMessage] = useState('')

  const backendClient = useMemo(() => createBackendClient(), [])
  const oneRmOptions = getOneRmOptions(profile)
  const todayStr = getTodayStr()
  const hasActiveCycle = Number.isInteger(activeCyclePlan?.cycle?.id)
  const displayedWeeklyPlan =
    planSource.activeSource === 'cycle' && hasActiveCycle && effectiveWeeklyPlan
      ? effectiveWeeklyPlan
      : weeklyPlan
  const layoutModel = useMemo(
    () =>
      buildWeeklyPlanLayoutModel(displayedWeeklyPlan, {
        referenceDate: todayStr,
      }),
    [displayedWeeklyPlan, todayStr],
  )
  // 头部周信息优先复用 weeklyPlan 内的真实元数据，日期基准必须传入可解析的真实日期字符串。
  const headerModel = useMemo(
    () =>
      buildPlanHeaderModel({
        referenceDate: todayStr,
        weeklyPlan: displayedWeeklyPlan,
      }),
    [displayedWeeklyPlan, todayStr],
  )
  const cycleSettingsStatus = buildCycleSettingsStatus({ planSource, activeCyclePlan })

  function isCycleOverrideMode() {
    return (
      planSource.activeSource === 'cycle' &&
      Boolean(activeCyclePlan?.cycle?.id) &&
      Number.isInteger(activeCyclePlan?.cycle?.currentWeekIndex)
    )
  }

  async function applyPlanMutation(planUpdater) {
    if (!isCycleOverrideMode()) {
      onWeeklyPlanChange(planUpdater)
      return true
    }

    const nextPlan = planUpdater(displayedWeeklyPlan)
    const response = await backendClient.updateCycleWeekOverride(
      activeCyclePlan.cycle.id,
      activeCyclePlan.cycle.currentWeekIndex,
      nextPlan,
    )
    const nextEffectivePlan = readNextEffectivePlan(response) ?? nextPlan
    onEffectiveWeeklyPlanChange?.(nextEffectivePlan)
    return true
  }

  async function handleDayTypeChange(dayKey, nextType) {
    try {
      await applyPlanMutation((currentPlan) => updateDayType(currentPlan, dayKey, nextType))
    } catch (error) {
      setCycleActionMessage(error.message)
    }
  }

  function handleWeekNumberChange(nextWeekNumber) {
    if (isCycleOverrideMode()) {
      return
    }

    onWeeklyPlanChange((currentPlan) => ({
      ...currentPlan,
      weekMeta: {
        ...(currentPlan?.weekMeta ?? {}),
        weekNumber: nextWeekNumber,
      },
    }))
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

  async function saveExercise() {
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

    try {
      if (editingState.exerciseId === NEW_PLAN_EXERCISE_ID) {
        await applyPlanMutation((currentPlan) =>
          addExerciseToDay(currentPlan, editingState.dayKey, nextExercise),
        )
      } else {
        await applyPlanMutation((currentPlan) =>
          updateExerciseInDay(currentPlan, editingState.dayKey, editingState.exerciseId, {
            ...nextExercise,
            id: editingState.exerciseId,
          }),
        )
      }

      cancelEditing()
    } catch (error) {
      setCycleActionMessage(error.message)
    }
  }

  async function deleteExercise(dayKey, exerciseId) {
    try {
      await applyPlanMutation((currentPlan) =>
        removeExerciseFromDay(currentPlan, dayKey, exerciseId),
      )
      setEditingState((current) => clearPlanEditorStateAfterDelete(current, dayKey, exerciseId))
    } catch (error) {
      setCycleActionMessage(error.message)
    }
  }

  async function handleReorderExercise(dayKey, fromExerciseId, toExerciseId) {
    try {
      await applyPlanMutation((currentPlan) =>
        reorderExercisesInDay(currentPlan, dayKey, fromExerciseId, toExerciseId),
      )
    } catch (error) {
      setCycleActionMessage(error.message)
    }
  }

  async function openPlanSettings() {
    setIsPlanSettingsOpen((current) => {
      const nextOpen = !current
      if (nextOpen) {
        setPlanSettingsMode(resolvePlanSettingsMode(planSource, activeCyclePlan))
      }
      return nextOpen
    })

    if (cyclePresets.length > 0 || isCyclePresetsLoading) {
      return
    }

    setIsCyclePresetsLoading(true)
    try {
      const presets = await backendClient.getCyclePresets()
      setCyclePresets(Array.isArray(presets) ? presets : [])
    } catch (error) {
      setCycleActionMessage(error.message)
    } finally {
      setIsCyclePresetsLoading(false)
    }
  }

  function updateCycleDraft(nextDraft) {
    setCycleDraft(nextDraft)
  }

  function updateCustomStrengthDraft(nextDraft) {
    setCustomStrengthDraft(nextDraft)
  }

  function handleSelectPlanSettingsMode(nextMode) {
    setPlanSettingsMode(resolvePlanSettingsMode(planSource, activeCyclePlan, nextMode))
  }

  async function handleSwitchToManualSource() {
    setIsCycleSubmitting(true)
    setCycleActionMessage('')

    try {
      const nextPlanSource = await backendClient.updatePlanSource({ activeSource: 'manual' })
      onPlanSourceChange?.(nextPlanSource ?? { activeSource: 'manual' })
      onEffectiveWeeklyPlanChange?.(weeklyPlan)
      setPlanSettingsMode('manual')
      setCycleActionMessage('已切换回非周期计划。')
    } catch (error) {
      setCycleActionMessage(error.message)
    } finally {
      setIsCycleSubmitting(false)
    }
  }

  async function handleSwitchToCycleSource() {
    if (!activeCyclePlan?.cycle?.id) {
      setCycleActionMessage('请先创建周期计划，再启用周期计划来源。')
      return
    }

    setIsCycleSubmitting(true)
    setCycleActionMessage('')
    try {
      const nextPlanSource = await backendClient.updatePlanSource({ activeSource: 'cycle' })
      const nextActiveCyclePlan = await backendClient.getActiveCyclePlan()
      const nextEffectivePlan = readNextEffectivePlan(nextActiveCyclePlan)

      onPlanSourceChange?.(nextPlanSource ?? { activeSource: 'cycle' })
      if (nextActiveCyclePlan) {
        onActiveCyclePlanChange?.(nextActiveCyclePlan)
      }
      if (nextEffectivePlan) {
        onEffectiveWeeklyPlanChange?.(nextEffectivePlan)
      }
      setPlanSettingsMode('cycle')
      setCycleActionMessage('已切换到周期计划。')
    } catch (error) {
      setCycleActionMessage(error.message)
    } finally {
      setIsCycleSubmitting(false)
    }
  }

  function buildNextActiveCyclePayload(response) {
    if (response?.activeCyclePlan) {
      return response.activeCyclePlan
    }

    if (response?.currentWeek || response?.effectivePlan) {
      return response ?? null
    }

    return response ?? null
  }

  function readNextEffectivePlan(response) {
    return response?.effectivePlan ?? response?.currentWeek?.effectivePlan ?? response?.plan ?? null
  }

  async function handleCreateCyclePlan() {
    setIsCycleSubmitting(true)
    setCycleActionMessage('')

    try {
      const response = await backendClient.createCyclePlan(buildCreateCyclePlanPayload(cycleDraft))
      const nextActiveCyclePlan = buildNextActiveCyclePayload(response)
      const nextEffectivePlan = readNextEffectivePlan(response)

      onPlanSourceChange?.({ activeSource: 'cycle' })
      onActiveCyclePlanChange?.(nextActiveCyclePlan)
      if (nextEffectivePlan) {
        onEffectiveWeeklyPlanChange?.(nextEffectivePlan)
      }
      setPlanSettingsMode('cycle')
      setCycleActionMessage('周期计划已创建。')
    } catch (error) {
      setCycleActionMessage(error.message)
    } finally {
      setIsCycleSubmitting(false)
    }
  }

  async function handleCreateCustomStrengthCyclePlan() {
    setIsCycleSubmitting(true)
    setCycleActionMessage('')

    try {
      const response = await backendClient.createCyclePlan(
        buildCreateCustomStrengthCyclePayload(customStrengthDraft),
      )
      const nextActiveCyclePlan = buildNextActiveCyclePayload(response)
      const nextEffectivePlan = readNextEffectivePlan(response)

      onPlanSourceChange?.({ activeSource: 'cycle' })
      onActiveCyclePlanChange?.(nextActiveCyclePlan)
      if (nextEffectivePlan) {
        onEffectiveWeeklyPlanChange?.(nextEffectivePlan)
      }
      setPlanSettingsMode('cycle')
      setCycleActionMessage('自定义力量周期计划已创建。')
    } catch (error) {
      setCycleActionMessage(error.message)
    } finally {
      setIsCycleSubmitting(false)
    }
  }

  async function handleGenerateNextWeek() {
    if (!activeCyclePlan?.cycle?.id) {
      return
    }

    setIsCycleSubmitting(true)
    setCycleActionMessage('')
    try {
      await backendClient.generateNextCycleWeek(activeCyclePlan.cycle.id)
      const nextActiveCyclePlan = await backendClient.getActiveCyclePlan()

      if (nextActiveCyclePlan) {
        onActiveCyclePlanChange?.(nextActiveCyclePlan)
      }
      setCycleActionMessage('已生成下一周。')
    } catch (error) {
      setCycleActionMessage(error.message)
    } finally {
      setIsCycleSubmitting(false)
    }
  }

  async function handleConfirmNextWeek() {
    if (!activeCyclePlan?.cycle?.id) {
      return
    }

    setIsCycleSubmitting(true)
    setCycleActionMessage('')
    try {
      const response = await backendClient.confirmNextCycleWeek(activeCyclePlan.cycle.id)
      const nextActiveCyclePlan = buildNextActiveCyclePayload(response)
      const nextEffectivePlan = readNextEffectivePlan(response)

      if (nextActiveCyclePlan) {
        onActiveCyclePlanChange?.(nextActiveCyclePlan)
      }
      if (nextEffectivePlan) {
        onEffectiveWeeklyPlanChange?.(nextEffectivePlan)
      }
      setCycleActionMessage('已确认进入下一周。')
    } catch (error) {
      setCycleActionMessage(error.message)
    } finally {
      setIsCycleSubmitting(false)
    }
  }

  async function handleStopCyclePlan() {
    if (!activeCyclePlan?.cycle?.id) {
      return
    }

    setIsCycleSubmitting(true)
    setCycleActionMessage('')
    try {
      const response = await backendClient.stopCyclePlan(activeCyclePlan.cycle.id)
      const nextActiveCyclePlan = buildNextActiveCyclePayload(response)

      onPlanSourceChange?.({ activeSource: 'manual' })
      onActiveCyclePlanChange?.(nextActiveCyclePlan)
      onEffectiveWeeklyPlanChange?.(weeklyPlan)
      setPlanSettingsMode('manual')
      setCycleActionMessage('已停止当前周期。')
    } catch (error) {
      setCycleActionMessage(error.message)
    } finally {
      setIsCycleSubmitting(false)
    }
  }

  const currentRpeError = editingState.draft ? getRpeValidationError(editingState.draft.rpe) : null

  return (
    <div className="space-y-5">
      <PlanHeaderToolbar
        canEditWeekNumber={!isCycleOverrideMode()}
        headerModel={headerModel}
        onPlanSettingsClick={openPlanSettings}
        onWeekNumberChange={handleWeekNumberChange}
      />

      {isPlanSettingsOpen ? (
        <PlanSettingsPanel
          activeCyclePlan={activeCyclePlan}
          cycleActionMessage={cycleActionMessage}
          cycleDraft={cycleDraft}
          cyclePresets={cyclePresets}
          customStrengthDraft={customStrengthDraft}
          isCyclePresetsLoading={isCyclePresetsLoading}
          isCycleSubmitting={isCycleSubmitting}
          onConfirmNextWeek={handleConfirmNextWeek}
          onCreateCyclePlan={handleCreateCyclePlan}
          onCreateCustomStrengthCyclePlan={handleCreateCustomStrengthCyclePlan}
          onGenerateNextWeek={handleGenerateNextWeek}
          onSelectSettingsMode={handleSelectPlanSettingsMode}
          onStopCyclePlan={handleStopCyclePlan}
          onSwitchToCycleSource={handleSwitchToCycleSource}
          onSwitchToManualSource={handleSwitchToManualSource}
          onUpdateCustomStrengthDraft={updateCustomStrengthDraft}
          onUpdateCycleDraft={updateCycleDraft}
          planSettingsMode={planSettingsMode}
          settingsStatus={cycleSettingsStatus}
        />
      ) : null}

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
                dateLabel={column.dateLabel}
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
                onMoveExercise={(fromId, toId) =>
                  handleReorderExercise(column.dayKey, fromId, toId)
                }
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
