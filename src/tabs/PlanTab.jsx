import { useMemo, useState } from 'react'
import { createBackendClient } from '../api/backendClient.js'
import PlanDayCard, { createEmptyExerciseDraft } from '../components/PlanDayCard.jsx'
import PlanWeekGrid from '../components/plan-grid/PlanWeekGrid.jsx'
import PlanWeekGridColumn from '../components/plan-grid/PlanWeekGridColumn.jsx'
import PlanHeaderToolbar from '../components/plan-header/PlanHeaderToolbar.jsx'
import {
  buildCreateCyclePlanPayload,
  createCyclePlanDraft,
  cyclePlanWeekdayOptions,
  toggleTrainingDay,
} from '../utils/cyclePlanForm.js'
import {
  buildCyclePresetSummary,
  getCyclePlanSourceLabel,
  getCycleStatusLabel,
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
  const [cyclePresets, setCyclePresets] = useState([])
  const [isCyclePresetsLoading, setIsCyclePresetsLoading] = useState(false)
  const [isCycleSubmitting, setIsCycleSubmitting] = useState(false)
  const [cycleActionMessage, setCycleActionMessage] = useState('')

  const backendClient = useMemo(() => createBackendClient(), [])
  const oneRmOptions = getOneRmOptions(profile)
  const todayStr = getTodayStr()
  const displayedWeeklyPlan =
    planSource.activeSource === 'cycle' && effectiveWeeklyPlan ? effectiveWeeklyPlan : weeklyPlan
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
  const planSourceLabel = getCyclePlanSourceLabel(planSource)
  const activeCycleStatus = getCycleStatusLabel(activeCyclePlan?.cycle?.status)
  const activeCycleSummary = buildCyclePresetSummary(activeCyclePlan)

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
    if (planSource.activeSource === 'cycle') {
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

  async function openPlanSettings() {
    setIsPlanSettingsOpen((current) => !current)

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

  function handleCycleSourceSwitch(nextSource) {
    if (nextSource === 'manual') {
      setIsCycleSubmitting(true)
      backendClient
        .updatePlanSource({ activeSource: 'manual' })
        .then((nextPlanSource) => {
          onPlanSourceChange?.(nextPlanSource ?? { activeSource: 'manual' })
          onEffectiveWeeklyPlanChange?.(weeklyPlan)
          setCycleActionMessage('已切换回非周期计划。')
        })
        .catch((error) => {
          setCycleActionMessage(error.message)
        })
        .finally(() => {
          setIsCycleSubmitting(false)
        })
      return
    }

    onPlanSourceChange?.({ activeSource: 'cycle' })
  }

  function buildNextActiveCyclePayload(response) {
    return response?.activeCyclePlan ?? response?.cycle ?? response ?? null
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
      setCycleActionMessage('周期计划已创建。')
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
      const response = await backendClient.generateNextCycleWeek(activeCyclePlan.cycle.id)
      const nextActiveCyclePlan = buildNextActiveCyclePayload(response)

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
        headerModel={headerModel}
        onPlanSettingsClick={openPlanSettings}
        onWeekNumberChange={handleWeekNumberChange}
      />

      {isPlanSettingsOpen ? (
        <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 text-slate-900 shadow-sm shadow-black/10">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">计划设置入口</p>
              <p className="text-sm text-slate-500">{planSourceLabel.label}</p>
              {activeCycleSummary ? (
                <p className="text-xs text-slate-500">
                  {activeCycleSummary} · {activeCycleStatus.label}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium"
                onClick={() => handleCycleSourceSwitch('manual')}
                type="button"
              >
                非周期计划
              </button>
              <button
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium"
                onClick={() => handleCycleSourceSwitch('cycle')}
                type="button"
              >
                周期计划
              </button>
            </div>
          </div>

          {planSource.activeSource === 'cycle' ? (
            <div className="space-y-4 rounded-xl bg-slate-50 p-4">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">周期模板</span>
                  <select
                    className="w-full rounded-lg border border-slate-200 px-3 py-2"
                    onChange={(event) =>
                      updateCycleDraft({
                        ...cycleDraft,
                        presetKey: event.target.value,
                      })
                    }
                    value={cycleDraft.presetKey}
                  >
                    {isCyclePresetsLoading ? <option value="">加载中...</option> : null}
                    {cyclePresets.map((preset) => (
                      <option key={preset.key} value={preset.key}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">开始日期</span>
                  <input
                    className="w-full rounded-lg border border-slate-200 px-3 py-2"
                    onChange={(event) =>
                      updateCycleDraft({
                        ...cycleDraft,
                        startDate: event.target.value,
                      })
                    }
                    type="date"
                    value={cycleDraft.startDate}
                  />
                </label>
              </div>

              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-700">目标</span>
                <input
                  className="w-full rounded-lg border border-slate-200 px-3 py-2"
                  onChange={(event) =>
                    updateCycleDraft({
                      ...cycleDraft,
                      goal: event.target.value,
                    })
                  }
                  placeholder="例如：strength / 增肌"
                  value={cycleDraft.goal}
                />
              </label>

              <div className="grid gap-3 md:grid-cols-3">
                {['squat', 'bench', 'deadlift'].map((liftKey) => (
                  <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-3" key={liftKey}>
                    <p className="text-sm font-semibold text-slate-800">{liftKey}</p>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                      onChange={(event) =>
                        updateCycleDraft({
                          ...cycleDraft,
                          baseLifts: {
                            ...cycleDraft.baseLifts,
                            [liftKey]: {
                              ...cycleDraft.baseLifts[liftKey],
                              oneRm: event.target.value,
                            },
                          },
                        })
                      }
                      placeholder="1RM"
                      value={cycleDraft.baseLifts[liftKey].oneRm}
                    />
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                      onChange={(event) =>
                        updateCycleDraft({
                          ...cycleDraft,
                          baseLifts: {
                            ...cycleDraft.baseLifts,
                            [liftKey]: {
                              ...cycleDraft.baseLifts[liftKey],
                              tm: event.target.value,
                            },
                          },
                        })
                      }
                      placeholder="TM"
                      value={cycleDraft.baseLifts[liftKey].tm}
                    />
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium text-slate-700">训练日</p>
                <div className="flex flex-wrap gap-2">
                  {cyclePlanWeekdayOptions.map((dayKey) => (
                    <button
                      className="rounded-full border border-slate-200 px-3 py-1 text-sm"
                      key={dayKey}
                      onClick={() =>
                        updateCycleDraft({
                          ...cycleDraft,
                          config: {
                            ...cycleDraft.config,
                            trainingDays: toggleTrainingDay(
                              cycleDraft.config.trainingDays,
                              dayKey,
                            ),
                          },
                        })
                      }
                      type="button"
                    >
                      {dayKey}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
                  disabled={isCycleSubmitting}
                  onClick={handleCreateCyclePlan}
                  type="button"
                >
                  创建周期计划
                </button>
                <button
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium"
                  disabled={isCycleSubmitting || !activeCyclePlan?.cycle?.id}
                  onClick={handleGenerateNextWeek}
                  type="button"
                >
                  生成下一周
                </button>
                <button
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium"
                  disabled={isCycleSubmitting || !activeCyclePlan?.cycle?.id}
                  onClick={handleConfirmNextWeek}
                  type="button"
                >
                  确认进入下一周
                </button>
                <button
                  className="rounded-lg border border-rose-200 px-4 py-2 text-sm font-medium text-rose-600"
                  disabled={isCycleSubmitting || !activeCyclePlan?.cycle?.id}
                  onClick={handleStopCyclePlan}
                  type="button"
                >
                  停止周期
                </button>
              </div>

              {cycleActionMessage ? (
                <p className="text-sm text-slate-500">{cycleActionMessage}</p>
              ) : null}
            </div>
          ) : null}
        </section>
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
