import { cyclePlanWeekdayOptions, toggleTrainingDay } from '../../utils/cyclePlanForm.js'
import CustomStrengthPlanEditor from './CustomStrengthPlanEditor.jsx'

function liftLabelMap(liftKey) {
  if (liftKey === 'squat') {
    return '深蹲'
  }
  if (liftKey === 'bench') {
    return '卧推'
  }
  if (liftKey === 'deadlift') {
    return '硬拉'
  }
  return liftKey
}

function weekdayLabelMap(dayKey) {
  const labels = {
    Monday: '周一',
    Tuesday: '周二',
    Wednesday: '周三',
    Thursday: '周四',
    Friday: '周五',
    Saturday: '周六',
    Sunday: '周日',
  }
  return labels[dayKey] ?? dayKey
}

function PlanSettingsPanel({
  activeCyclePlan,
  cycleActionMessage,
  cycleDraft,
  cyclePresets,
  customStrengthDraft,
  isCyclePresetsLoading,
  isCycleSubmitting,
  onConfirmNextWeek,
  onCreateCyclePlan,
  onCreateCustomStrengthCyclePlan,
  onGenerateNextWeek,
  onSelectSettingsMode,
  onStopCyclePlan,
  onSwitchToCycleSource,
  onSwitchToManualSource,
  onUpdateCustomStrengthDraft,
  onUpdateCycleDraft,
  planSettingsMode,
  settingsStatus,
}) {
  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 text-slate-900 shadow-sm shadow-black/10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div>
            <p className="text-sm font-semibold text-slate-900">计划设置入口</p>
            <p className="text-sm text-slate-500">{settingsStatus.sourceLabel}</p>
          </div>
          <div className="grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
            <p>{settingsStatus.currentWeekLabel}</p>
            <p>{settingsStatus.pendingWeekLabel}</p>
            <p>{settingsStatus.summaryLabel}</p>
            <p>周期状态：{settingsStatus.statusLabel}</p>
          </div>
          <p className="text-xs text-slate-500">{settingsStatus.manualPlanHint}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium ${
              planSettingsMode === 'manual'
                ? 'border-slate-900 bg-slate-900 text-white'
                : 'border-slate-200 text-slate-700'
            }`}
            onClick={() => onSelectSettingsMode('manual')}
            type="button"
          >
            非周期计划
          </button>
          <button
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium ${
              planSettingsMode === 'cycle'
                ? 'border-slate-900 bg-slate-900 text-white'
                : 'border-slate-200 text-slate-700'
            }`}
            onClick={() => onSelectSettingsMode('cycle')}
            type="button"
          >
            周期计划
          </button>
        </div>
      </div>

      {planSettingsMode === 'manual' ? (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-800">非周期计划</p>
            <p className="text-sm text-slate-500">
              当前周计划继续使用手动计划表。切回这里不会删除或覆盖已创建的周期计划。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium"
              disabled={isCycleSubmitting || !settingsStatus.canSwitchToManual}
              onClick={onSwitchToManualSource}
              type="button"
            >
              切换为非周期计划
            </button>
          </div>
        </div>
      ) : null}

      {planSettingsMode === 'cycle' ? (
        <div className="space-y-4 rounded-xl bg-slate-50 p-4">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-800">周期计划模式</p>
            <p className="text-sm text-slate-500">
              先在这里选择模板并设置参考数据，只有显式启用后，训练计划页才会切到周期计划来源。
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">周期模板</span>
              <select
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                onChange={(event) =>
                  onUpdateCycleDraft({
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
                  onUpdateCycleDraft({
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
                onUpdateCycleDraft({
                  ...cycleDraft,
                  goal: event.target.value,
                })
              }
              placeholder="例如：力量提升 / 增肌"
              value={cycleDraft.goal}
            />
          </label>

          <div className="grid gap-3 md:grid-cols-3">
            {['squat', 'bench', 'deadlift'].map((liftKey) => (
              <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-3" key={liftKey}>
                <p className="text-sm font-semibold text-slate-800">{liftLabelMap(liftKey)}</p>
                <input
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  onChange={(event) =>
                    onUpdateCycleDraft({
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
                    onUpdateCycleDraft({
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
              {cyclePlanWeekdayOptions.map((dayKey) => {
                const isSelected = cycleDraft.config.trainingDays.includes(dayKey)

                return (
                  <button
                    aria-label={dayKey}
                    className={`rounded-full border px-3 py-1 text-sm ${
                      isSelected
                        ? 'border-slate-900 bg-slate-900 text-white'
                        : 'border-slate-200 text-slate-700'
                    }`}
                    key={dayKey}
                    onClick={() =>
                      onUpdateCycleDraft({
                        ...cycleDraft,
                        config: {
                          ...cycleDraft.config,
                          trainingDays: toggleTrainingDay(cycleDraft.config.trainingDays, dayKey),
                        },
                      })
                    }
                    type="button"
                  >
                    {weekdayLabelMap(dayKey)}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
              disabled={isCycleSubmitting || !settingsStatus.canCreateCycle}
              onClick={onCreateCyclePlan}
              type="button"
            >
              创建周期计划
            </button>
            <button
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium"
              disabled={isCycleSubmitting || !settingsStatus.canActivateCycle}
              onClick={onSwitchToCycleSource}
              type="button"
            >
              启用当前周期计划
            </button>
            <button
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium"
              disabled={isCycleSubmitting || !activeCyclePlan?.cycle?.id}
              onClick={onGenerateNextWeek}
              type="button"
            >
              生成下一周
            </button>
            <button
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium"
              disabled={isCycleSubmitting || !activeCyclePlan?.cycle?.id}
              onClick={onConfirmNextWeek}
              type="button"
            >
              确认进入下一周
            </button>
            <button
              className="rounded-lg border border-rose-200 px-4 py-2 text-sm font-medium text-rose-600"
              disabled={isCycleSubmitting || !activeCyclePlan?.cycle?.id}
              onClick={onStopCyclePlan}
              type="button"
            >
              停止周期
            </button>
          </div>

          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-800">自定义力量周期计划</p>
            <p className="text-sm text-slate-500">
              这里仅负责挂载自定义力量编辑器，具体草稿状态与创建动作仍由 PlanTab 编排。
            </p>
            <p className="text-xs text-slate-500">提交动作：创建自定义力量周期计划</p>
          </div>

          <CustomStrengthPlanEditor
            canCreate={settingsStatus.canCreateCycle}
            draft={customStrengthDraft}
            isSubmitting={isCycleSubmitting}
            onChange={onUpdateCustomStrengthDraft}
            onSubmit={onCreateCustomStrengthCyclePlan}
          />

          {cycleActionMessage ? <p className="text-sm text-slate-500">{cycleActionMessage}</p> : null}
        </div>
      ) : null}
    </section>
  )
}

export default PlanSettingsPanel
