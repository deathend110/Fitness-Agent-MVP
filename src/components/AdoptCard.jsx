function AdoptCard({ card, onAdopt, onDismiss }) {
  if (!card) {
    return null
  }

  return (
    <article className="rounded-2xl border border-fitloop-orange/25 bg-fitloop-orange/5 p-4 shadow-[0_8px_30px_rgba(109,94,252,0.08)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fitloop-orange">
            建议采纳卡片
          </p>
          <h3 className="mt-2 text-base font-semibold text-slate-800">训练计划调整建议</h3>
        </div>
        <div className="rounded-xl border border-fitloop-line bg-white px-3 py-2 text-right shadow-sm">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">建议日期</p>
          <p className="mt-1 text-sm font-medium text-slate-700">{card.dayLabel}</p>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-fitloop-line bg-white p-3 shadow-sm">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Summary</p>
        <p className="mt-2 text-sm leading-6 text-slate-700">{card.summary}</p>
      </div>

      <div className="mt-4 space-y-3">
        {card.changes.map((change) => (
          <div
            className="rounded-xl border border-fitloop-line bg-white p-3"
            key={change.id}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-slate-800">
                {change.actionLabel} {change.exerciseName}
              </p>
              <span className="text-xs text-slate-400">{change.fieldLabel}</span>
            </div>
            <div className="mt-2 grid gap-2 text-sm md:grid-cols-2">
              <p className="text-slate-500">调整前：{change.beforeLabel}</p>
              <p className="font-medium text-fitloop-orange">调整后：{change.afterLabel}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          className="rounded-xl border border-fitloop-orange bg-fitloop-orange px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:brightness-110"
          onClick={onAdopt}
          type="button"
        >
          采纳并更新计划
        </button>
        <button
          className="rounded-xl border border-fitloop-line bg-white px-4 py-2 text-sm font-medium text-slate-500 transition hover:border-fitloop-orange/30 hover:bg-fitloop-orange/8 hover:text-fitloop-orange"
          onClick={onDismiss}
          type="button"
        >
          忽略
        </button>
      </div>
    </article>
  )
}

export default AdoptCard
