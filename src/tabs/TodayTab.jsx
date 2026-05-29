import { useEffect, useState } from 'react'
import { getExerciseKg, getTodayKey, getTodayStr } from '../utils/calc.js'
import { buildTodayLogPayload, readTodayLogForm } from '../utils/dailyLog.js'

const metricFields = [
  { key: 'weight', label: '体重 (kg)', inputMode: 'decimal', step: '0.1' },
  { key: 'kcal', label: '热量 (kcal)', inputMode: 'numeric', step: '1' },
  { key: 'protein', label: '蛋白质 (g)', inputMode: 'numeric', step: '1' },
  { key: 'sleep', label: '睡眠 (h)', inputMode: 'decimal', step: '0.1' },
  { key: 'fatigue', label: '疲劳度 (1-5)', inputMode: 'numeric', step: '1', min: '1', max: '5' },
]

function getTodayPlanSummary(plan, profile) {
  if (!plan || !Array.isArray(plan.exercises) || plan.exercises.length === 0) {
    return '今天是休息日，当前没有训练动作安排。'
  }

  return plan.exercises
    .map((exercise) => {
      const actualKg = getExerciseKg(exercise, profile.oneRM)
      return `${exercise.name} ${actualKg}kg × ${exercise.sets} × ${exercise.reps}`
    })
    .join(' | ')
}

function formatMetric(value, suffix = '') {
  if (value === null || value === undefined || value === '') {
    return '--'
  }

  return `${value}${suffix}`
}

function TodayTab({ dailyLog, weeklyPlan, profile, onDailyLogChange }) {
  const todayDate = getTodayStr()
  const todayPlanKey = getTodayKey()
  const todayLog = dailyLog?.[todayDate]
  const todayPlan = weeklyPlan?.[todayPlanKey] ?? { type: 'rest', exercises: [] }
  const [draft, setDraft] = useState(() => readTodayLogForm(todayLog))
  const [saveHint, setSaveHint] = useState('')

  useEffect(() => {
    setDraft(readTodayLogForm(todayLog))
    setSaveHint('')
  }, [todayDate, todayLog])

  function updateDraftField(key, value) {
    setDraft((current) => ({
      ...current,
      [key]: value,
    }))
    setSaveHint('')
  }

  function handleSubmit(event) {
    event.preventDefault()

    onDailyLogChange((currentDailyLog) =>
      buildTodayLogPayload(currentDailyLog, todayDate, draft),
    )
    setSaveHint('今日日志已保存到本地。')
  }

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 3</p>
      <h2 className="mt-3 text-2xl font-bold text-white">今日日志</h2>
      <p className="mt-4 max-w-3xl leading-7 text-slate-300">
        这里先录入当天恢复与训练情况，再在右侧对照已保存摘要和今天的训练计划。
        保存后会写回 <code>fitloop_dailyLog</code>，刷新页面后仍然保留。
      </p>

      <div className="mt-8 grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <form
          className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4"
          onSubmit={handleSubmit}
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{todayDate}</p>
              <h3 className="mt-3 text-lg font-semibold text-white">填写今天的数据</h3>
            </div>
            <button
              className="rounded-md bg-fitloop-orange px-4 py-2 text-sm font-medium text-white transition hover:brightness-110"
              type="submit"
            >
              保存今日日志
            </button>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {metricFields.map((field) => (
              <label className="space-y-2" key={field.key}>
                <span className="text-sm text-slate-300">{field.label}</span>
                <input
                  className="w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
                  inputMode={field.inputMode}
                  max={field.max}
                  min={field.min}
                  onChange={(event) => updateDraftField(field.key, event.target.value)}
                  placeholder="可留空"
                  step={field.step}
                  type="number"
                  value={draft[field.key]}
                />
              </label>
            ))}
          </div>

          <label className="mt-4 flex items-center gap-3 rounded-md border border-fitloop-line bg-fitloop-ink/40 px-3 py-3 text-sm text-slate-200">
            <input
              checked={draft.trainingDone}
              className="h-4 w-4 accent-fitloop-orange"
              onChange={(event) => updateDraftField('trainingDone', event.target.checked)}
              type="checkbox"
            />
            今天已完成训练
          </label>

          <label className="mt-4 block space-y-2">
            <span className="text-sm text-slate-300">训练备注</span>
            <textarea
              className="min-h-28 w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-2 text-white outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange"
              onChange={(event) => updateDraftField('trainingNotes', event.target.value)}
              placeholder="例如：主项速度下降、哪里紧、是否需要下调训练量。"
              value={draft.trainingNotes}
            />
          </label>

          <p className="mt-4 text-sm text-fitloop-mint" role="status">
            {saveHint || '可选字段留空时会以空值保存，不会影响页面渲染。'}
          </p>
        </form>

        <div className="space-y-4">
          <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{todayDate}</p>
            <h3 className="mt-3 text-lg font-semibold text-white">已保存摘要</h3>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <p className="text-sm text-slate-300">体重：{formatMetric(todayLog?.weight, ' kg')}</p>
              <p className="text-sm text-slate-300">热量：{formatMetric(todayLog?.kcal, ' kcal')}</p>
              <p className="text-sm text-slate-300">蛋白质：{formatMetric(todayLog?.protein, ' g')}</p>
              <p className="text-sm text-slate-300">睡眠：{formatMetric(todayLog?.sleep, ' h')}</p>
              <p className="text-sm text-slate-300">疲劳度：{formatMetric(todayLog?.fatigue, ' / 5')}</p>
              <p className="text-sm text-slate-300">
                训练完成：{todayLog?.trainingDone ? '是' : '否'}
              </p>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-300">
              训练备注：{todayLog?.trainingNotes || '今天还没有训练备注。'}
            </p>
          </article>

          <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{todayPlanKey}</p>
            <h3 className="mt-3 text-lg font-semibold text-white">今日计划</h3>
            <p className="mt-4 text-sm text-slate-300">训练类型：{todayPlan?.type ?? 'rest'}</p>
            <p className="mt-4 text-sm leading-6 text-slate-300">
              {getTodayPlanSummary(todayPlan, profile)}
            </p>
          </article>
        </div>
      </div>
    </section>
  )
}

export default TodayTab
