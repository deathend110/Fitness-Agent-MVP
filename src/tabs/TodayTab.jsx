import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import DailyMetricsPanel from '../components/DailyMetricsPanel.jsx'
import { getTodayKey, getTodayStr } from '../utils/calc.js'
import { buildTodayLogPayload, readTodayLogForm } from '../utils/dailyLog.js'
import { buildDailyMetricsPanelModel } from '../utils/dailyMetricsPanel.js'
import { clampNumericInputDraft } from '../utils/numericFieldGuardrails.js'
import { buildTodayLogFieldGroups, buildTodayLogSummaryItems } from '../utils/todayLogView.js'
import { buildTodayPlanSummary } from '../utils/todayPlan.js'
import { buildWeightChartModel } from '../utils/weightChart.js'

const WeightChart = lazy(() => import('../components/WeightChart.jsx'))

function TodayTab({ dailyLog, effectiveWeeklyPlan, profile, onDailyLogChange, onOpenCoach }) {
  const todayDate = getTodayStr()
  const todayPlanKey = getTodayKey()
  const todayLog = dailyLog?.[todayDate]
  const todayPlan = effectiveWeeklyPlan?.[todayPlanKey] ?? { type: 'rest', exercises: [] }
  const todayPlanSummary = buildTodayPlanSummary(todayPlan, profile?.oneRM)
  const dailyMetricsPanel = buildDailyMetricsPanelModel(profile, effectiveWeeklyPlan, dailyLog)
  const weightChartModel = buildWeightChartModel(dailyLog, todayDate)
  const fieldGroups = useMemo(() => buildTodayLogFieldGroups(), [])
  const summaryItems = useMemo(() => buildTodayLogSummaryItems(todayLog), [todayLog])
  const [draft, setDraft] = useState(() => readTodayLogForm(todayLog))
  const [fieldErrors, setFieldErrors] = useState({})
  const [saveHint, setSaveHint] = useState('')

  useEffect(() => {
    setDraft(readTodayLogForm(todayLog))
    setFieldErrors({})
    setSaveHint('')
  }, [todayDate, todayLog])

  function updateDraftField(key, value) {
    setDraft((current) => ({
      ...current,
      [key]: value,
    }))
    setSaveHint('')
  }

  function updateGuardedDraftField(field, value) {
    const { nextValue, error } = clampNumericInputDraft({
      fieldKey: field.guardrailKey,
      previousValue: draft[field.key],
      nextValue: value,
    })

    updateDraftField(field.key, nextValue)
    setFieldErrors((current) => ({
      ...current,
      [field.guardrailKey]: error,
    }))
  }

  function handleSubmit(event) {
    event.preventDefault()

    onDailyLogChange((currentDailyLog) => buildTodayLogPayload(currentDailyLog, todayDate, draft))
    setSaveHint('今日日志已保存到本地。')
  }

  return (
    <section className="overflow-hidden rounded-[2rem] border border-fitloop-line bg-white/80 shadow-2xl shadow-black/20 backdrop-blur-sm">
      <header className="border-b border-fitloop-line bg-gradient-to-b from-white/95 via-white/90 to-[#f7f9ff] px-5 py-6 sm:px-8 sm:py-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-fitloop-orange">Today</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-100 sm:text-4xl">
              今日日志
            </h2>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">
              把今天的身体状态、摄入记录和恢复情况集中写在一处。先完成记录，再快速回看复杂指标、已保存结果、体重趋势和今日计划。
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <div className="rounded-full border border-fitloop-orange/30 bg-fitloop-orange/8 px-4 py-2 text-xs text-slate-300">
                <span className="font-semibold text-slate-100">记录优先</span>
                <span className="ml-2">首屏只聚焦今天的数据输入</span>
              </div>
              <div className="rounded-full border border-fitloop-orange/30 bg-white/90 px-4 py-2 text-xs text-slate-300">
                <span className="font-semibold text-slate-100">当前计划</span>
                <span className="ml-2">{todayPlanSummary.typeLabel}</span>
              </div>
              <div className="rounded-full border border-fitloop-orange/30 bg-white/90 px-4 py-2 text-xs text-slate-300">
                <span className="font-semibold text-slate-100">保存状态</span>
                <span className="ml-2">{saveHint || '等待保存'}</span>
              </div>
            </div>
          </div>

          <div className="w-full max-w-xs rounded-2xl border border-fitloop-orange/30 bg-fitloop-orange/8 px-4 py-4 lg:text-right">
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Today</p>
            <p className="mt-2 text-sm font-semibold text-slate-100">{todayDate}</p>
          </div>
        </div>
      </header>

      <div className="bg-gradient-to-b from-[#f4f7ff]/70 via-white/85 to-white/95 px-5 py-5 sm:px-8 sm:py-7">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)]">
          <form
            className="rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel/90 shadow-sm shadow-black/20"
            onSubmit={handleSubmit}
          >
            <div className="flex flex-col gap-4 border-b border-fitloop-line px-5 py-5 sm:px-7 sm:py-7 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fitloop-orange">Daily Input</p>
                <h3 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-slate-100">
                  今天的数据录入
                </h3>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                  先完成今天的身体、摄入和恢复记录。每个字段都沿用当前真实实现，不引入额外业务项。
                </p>
              </div>

              <div className="rounded-2xl border border-fitloop-orange/30 bg-fitloop-orange/8 px-4 py-4 lg:text-right">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Input State</p>
                <p className="mt-2 text-sm font-semibold text-slate-100">{saveHint ? '已保存' : '等待保存'}</p>
              </div>
            </div>

            <div className="px-5 py-5 sm:px-7 sm:py-7">
              <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
                {fieldGroups.map((group) => (
                  <section
                    className="rounded-[1.5rem] border border-fitloop-line bg-gradient-to-b from-white to-[#f5f7ff] p-4"
                    key={group.key}
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                      {group.title}
                    </p>
                    <p className="mt-3 text-sm leading-6 text-slate-300">{group.description}</p>

                    <div className="mt-4 grid gap-4">
                      {group.fields.map((field) => (
                        <label className="grid gap-2" key={field.key}>
                          <span className="text-sm font-medium text-slate-300">
                            {field.label}
                            {field.unit ? <span className="ml-1 text-slate-400">({field.unit})</span> : null}
                          </span>
                          <input
                            aria-invalid={Boolean(fieldErrors[field.guardrailKey])}
                            className="h-12 w-full rounded-2xl border border-fitloop-line bg-white px-4 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                            inputMode={field.inputMode}
                            max={field.max}
                            min={field.min}
                            onChange={(event) => updateGuardedDraftField(field, event.target.value)}
                            placeholder="可留空"
                            step={field.step}
                            type="number"
                            value={draft[field.key]}
                          />
                          <span className="text-xs leading-6 text-slate-400">
                            {fieldErrors[field.guardrailKey] ?? field.hint}
                          </span>
                        </label>
                      ))}
                    </div>
                  </section>
                ))}
              </div>

              <label className="mt-5 flex flex-col gap-4 rounded-3xl border border-emerald-400/25 bg-emerald-500/10 px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-100">今天已完成训练</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    用独立状态条表达完成情况，而不是一个孤立的裸 checkbox。
                  </p>
                </div>
                <span className="inline-flex items-center gap-3 self-start rounded-full border border-emerald-400/25 bg-white px-4 py-2 text-sm font-semibold text-fitloop-mint sm:self-auto">
                  <input
                    checked={draft.trainingDone}
                    className="h-4 w-4 accent-fitloop-orange"
                    onChange={(event) => updateDraftField('trainingDone', event.target.checked)}
                    type="checkbox"
                  />
                  {draft.trainingDone ? '已完成' : '未完成'}
                </span>
              </label>

              <section className="mt-5 rounded-[1.5rem] border border-fitloop-line bg-fitloop-ink/30 p-4">
                <label className="grid gap-2">
                  <span className="text-sm font-medium text-slate-300">训练备注</span>
                  <textarea
                    className="min-h-36 w-full rounded-2xl border border-fitloop-line bg-white px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                    onChange={(event) => updateDraftField('trainingNotes', event.target.value)}
                    placeholder="例如：主项速度下降、某个部位发紧、是否需要下调训练量。"
                    value={draft.trainingNotes}
                  />
                  <span className="text-xs leading-6 text-slate-400">
                    主观反馈仍然是今日日志的一部分，不只记录数字。
                  </span>
                </label>
              </section>

              <div className="mt-5 flex flex-col gap-4 rounded-[1.5rem] border border-fitloop-line bg-gradient-to-r from-fitloop-orange/8 to-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-100">保存今日日志</p>
                  <p className="mt-2 text-sm leading-6 text-fitloop-mint" role="status">
                    {saveHint || '可选字段留空时会以空值保存，不会影响页面渲染。'}
                  </p>
                </div>
                <button
                  className="rounded-2xl border border-fitloop-orange bg-fitloop-orange px-5 py-3 text-sm font-semibold text-white shadow-sm shadow-black/20 transition hover:brightness-110"
                  type="submit"
                >
                  保存今日日志
                </button>
              </div>
            </div>
          </form>

          <div className="grid gap-6">
            <DailyMetricsPanel model={dailyMetricsPanel} onOpenCoach={onOpenCoach} />

            <article className="rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel/90 p-5 shadow-sm shadow-black/20 sm:p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fitloop-orange">Saved Result</p>
              <h3 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-slate-100">已保存摘要</h3>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                不是再重复一遍表单，而是明确告诉用户当前已经回写成功的今日结果。
              </p>

              <div className="mt-5 grid gap-x-4 gap-y-3 sm:grid-cols-2">
                {summaryItems.map((item) => (
                  <div className="border-b border-dashed border-fitloop-line pb-3" key={item.key}>
                    <p className="text-[11px] uppercase tracking-[0.12em] text-slate-400">{item.label}</p>
                    <p className="mt-2 text-sm font-semibold text-slate-100">{item.value}</p>
                  </div>
                ))}
              </div>

              <div className="mt-5 rounded-2xl border border-fitloop-line bg-fitloop-ink/30 px-4 py-4">
                <p className="text-sm font-semibold text-slate-100">训练备注</p>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  {todayLog?.trainingNotes || '今天还没有训练备注。'}
                </p>
              </div>
            </article>
          </div>
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-2">
          <Suspense
            fallback={(
              <article className="rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel/90 p-5 shadow-sm shadow-black/20">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fitloop-orange">Trend</p>
                <p className="mt-3 text-lg font-semibold text-slate-100">体重趋势</p>
                <p className="mt-3 text-sm leading-6 text-slate-300">图表组件加载中...</p>
              </article>
            )}
          >
            <WeightChart model={weightChartModel} />
          </Suspense>

          <article className="rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel/90 p-5 shadow-sm shadow-black/20 sm:p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fitloop-orange">Today Plan</p>
                <h3 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-slate-100">今日计划</h3>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  保留当前 todayPlanSummary 的语义，只服务今天录完之后的快速回看。
                </p>
              </div>
              <div className="rounded-full border border-fitloop-orange/30 bg-fitloop-orange/8 px-4 py-2 text-xs font-semibold text-fitloop-orange">
                {todayPlanSummary.typeLabel}
              </div>
            </div>

            {todayPlanSummary.isRestDay ? (
              <p className="mt-5 rounded-2xl border border-fitloop-line bg-fitloop-ink/30 px-4 py-4 text-sm leading-7 text-slate-300">
                {todayPlanSummary.message}
              </p>
            ) : (
              <ul className="mt-5 grid gap-3">
                {todayPlanSummary.exercises.map((exercise) => (
                  <li
                    className="rounded-3xl border border-fitloop-line bg-white px-4 py-4"
                    key={exercise.id}
                  >
                    <p className="text-sm font-semibold text-slate-100">{exercise.name}</p>
                    <p className="mt-2 text-sm leading-7 text-slate-300">{exercise.detail}</p>
                  </li>
                ))}
              </ul>
            )}
          </article>
        </div>
      </div>
    </section>
  )
}

export default TodayTab
