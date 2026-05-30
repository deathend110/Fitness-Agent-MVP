function PlanDayCardHeader({ dayLabel, displayModel, exerciseCount, isTrainingDay, planType }) {
  const typeLabel = !isTrainingDay && planType === 'rest' ? '休息' : planType
  const preview = displayModel?.preview ?? {
    eyebrow: isTrainingDay ? '训练日' : '轻安排',
    title: typeLabel,
    meta: `${exerciseCount} 个动作`,
  }

  const rootClassName = isTrainingDay
    ? 'flex w-full flex-col gap-3 text-left'
    : 'flex w-full flex-col gap-3 text-center'
  const typeBadgeClassName = isTrainingDay
    ? 'border-fitloop-orange/30 bg-fitloop-orange/10 text-fitloop-orange'
    : 'border-fitloop-line/70 bg-fitloop-panel text-slate-300'

  return (
    <div className={rootClassName}>
      <div
        className={`flex w-full gap-3 ${
          isTrainingDay ? 'items-start justify-between' : 'items-center justify-between'
        }`}
      >
        <div className={`min-w-0 ${isTrainingDay ? '' : 'flex-1'}`}>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            {preview.eyebrow}
          </p>
          <h3 className="mt-2 truncate text-lg font-semibold text-slate-100">{dayLabel}</h3>
        </div>
      </div>

      <div
        className={`flex w-full ${
          isTrainingDay ? 'flex-wrap items-center gap-2' : 'flex-col items-center gap-2'
        }`}
      >
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${typeBadgeClassName}`}
        >
          {typeLabel}
        </span>

        {isTrainingDay ? (
          <span className="rounded-full border border-fitloop-line/70 bg-black/10 px-2.5 py-1 text-xs text-slate-400">
            {exerciseCount} 个动作
          </span>
        ) : null}

        <p className="text-xs leading-5 text-slate-400">
          {isTrainingDay ? preview.meta : `${preview.title} · ${preview.meta}`}
        </p>
      </div>
    </div>
  )
}

export default PlanDayCardHeader
