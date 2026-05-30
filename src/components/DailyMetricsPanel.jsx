import { getMetricToneClassNames } from '../utils/dailyMetricsPanel.js'

function renderMetricCard(metricKey, metric) {
  const toneClasses = getMetricToneClassNames(metric.tone)

  return (
    <article
      className={`rounded-2xl border px-4 py-4 shadow-sm shadow-black/10 ${toneClasses.cardClassName}`}
      key={metricKey}
    >
      <p className={`text-xs uppercase tracking-[0.16em] ${toneClasses.labelClassName}`}>
        {metric.label}
      </p>
      <p className={`mt-3 text-lg font-semibold ${toneClasses.valueClassName}`}>{metric.value}</p>
    </article>
  )
}

/**
 * 展示 Today 页与 AI prompt 共用的复杂指标，避免页面端重复解释数值逻辑。
 */
function DailyMetricsPanel({ model, onOpenCoach }) {
  const metricKeys = [
    'bmr',
    'trainingKcal',
    'steps',
    'tdee',
    'calorie',
    'calorieStatus',
    'protein',
    'proteinStatus',
    'recovery',
    'bmi',
  ]

  return (
    <article className="rounded-2xl border border-fitloop-line bg-fitloop-panel p-5 shadow-sm shadow-black/20">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{model.header.date}</p>
          <h3 className="mt-3 text-lg font-semibold text-slate-100">今日复杂指标</h3>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {model.header.trainingTag} · 计划类型 {model.header.planTypeLabel}
          </p>
        </div>

        <div className="rounded-xl border border-fitloop-line bg-fitloop-ink/30 px-3 py-3">
          <p className="text-sm font-medium text-slate-100">{model.aiEntry.title}</p>
          <p className="mt-2 max-w-sm text-sm leading-6 text-slate-300">{model.aiEntry.description}</p>
          <button
            className="mt-3 rounded-md border border-fitloop-orange bg-fitloop-orange px-4 py-2 text-sm font-medium text-white transition hover:brightness-110"
            onClick={onOpenCoach}
            type="button"
          >
            {model.aiEntry.ctaLabel}
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {metricKeys.map((metricKey) => renderMetricCard(metricKey, model.metrics[metricKey]))}
      </div>
    </article>
  )
}

export default DailyMetricsPanel
