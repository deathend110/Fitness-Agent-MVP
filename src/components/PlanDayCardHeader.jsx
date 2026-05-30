function PlanDayCardHeader({ dayKey, expanded, exerciseCount, planType, onToggle }) {
  return (
    <>
      <button
        aria-expanded={expanded}
        className="flex w-full items-center justify-between gap-3 text-left"
        onClick={onToggle}
        type="button"
      >
        <div className="min-w-0">
          <h3 className="truncate text-lg font-semibold text-slate-100">{dayKey}</h3>
          <p className="mt-1 text-sm text-slate-400">{exerciseCount} 个动作</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-fitloop-orange/15 px-2 py-1 text-xs font-medium text-fitloop-orange">
            {planType}
          </span>
          <span className="text-xs text-slate-400">{expanded ? '收起' : '展开'}</span>
        </div>
      </button>

      <div className="mt-3 rounded-xl border border-fitloop-line/60 bg-black/10 px-3 py-3">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">训练日</p>
        <p className="mt-1 text-sm font-semibold text-slate-100">{planType}</p>
        <p className="mt-1 text-xs text-slate-400">{exerciseCount} 个动作</p>
      </div>
    </>
  )
}

export default PlanDayCardHeader
