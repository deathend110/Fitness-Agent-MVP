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
  const featuredMetrics = ['tdee', 'proteinStatus']
  const secondaryMetrics = [
    'bmr',
    'trainingKcal',
    'bmi',
    'calorieStatus',
    'steps',
    'recovery',
  ]

  return (
    <article className="rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel/90 p-5 shadow-sm shadow-black/20 sm:p-6">
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fitloop-orange">Metrics</p>
          <h3 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-slate-100">今日复杂指标</h3>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            {model.header.trainingTag} · 计划类型 {model.header.planTypeLabel}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {featuredMetrics.map((metricKey) => renderMetricCard(metricKey, model.metrics[metricKey]))}
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {secondaryMetrics.map((metricKey) => renderMetricCard(metricKey, model.metrics[metricKey]))}
      </div>

      <div className="mt-5 flex flex-col gap-4 rounded-[1.5rem] border border-fitloop-line bg-fitloop-ink/30 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-100">{model.aiEntry.title}</p>
          <p className="mt-2 max-w-xl text-sm leading-7 text-slate-300">{model.aiEntry.description}</p>
        </div>
        <button
          className="rounded-2xl border border-fitloop-orange/30 bg-fitloop-orange/8 px-4 py-3 text-sm font-semibold text-fitloop-orange transition hover:brightness-95"
          onClick={onOpenCoach}
          type="button"
        >
          {model.aiEntry.ctaLabel}
        </button>
      </div>
    </article>
  )
}

export default DailyMetricsPanel
