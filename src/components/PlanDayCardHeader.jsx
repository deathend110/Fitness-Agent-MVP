function PlanDayCardHeader({
  dayLabel,
  expanded,
  exerciseCount,
  isTrainingDay,
  onToggle,
  planType,
}) {
  const modeLabel = isTrainingDay ? '训练日' : '恢复日'
  const toggleLabel = expanded ? '收起' : '展开'
  const typeBadgeClassName = isTrainingDay
    ? 'border-fitloop-orange/30 bg-fitloop-orange/10 text-fitloop-orange'
    : 'border-slate-500/30 bg-slate-500/10 text-slate-300'

  return (
    <button
      aria-expanded={expanded}
      className="flex w-full flex-col gap-3 text-left"
      onClick={onToggle}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            {modeLabel}
          </p>
          <h3 className="mt-2 truncate text-lg font-semibold text-slate-100">{dayLabel}</h3>
        </div>

        <span className="shrink-0 rounded-full border border-fitloop-line/70 bg-black/10 px-2.5 py-1 text-[11px] font-medium text-slate-400">
          {toggleLabel}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${typeBadgeClassName}`}
        >
          {planType}
        </span>
        <span className="rounded-full border border-fitloop-line/70 bg-black/10 px-2.5 py-1 text-xs text-slate-400">
          {exerciseCount} 个动作
        </span>
      </div>
    </button>
  )
}

export default PlanDayCardHeader
