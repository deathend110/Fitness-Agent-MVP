function PlanDayCardHeader({ dayLabel, displayModel, exerciseCount, isTrainingDay, planType }) {
  const typeLabel = displayModel?.headerBadgeLabel ?? (!isTrainingDay && planType === 'rest' ? '休息' : planType)
  const header = displayModel?.header ?? {
    title: dayLabel,
    dateLabel: '',
  }
  const preview = displayModel?.preview ?? {
    eyebrow: isTrainingDay ? '训练日' : '轻安排',
    title: typeLabel,
    meta: `${exerciseCount} 个动作`,
  }
  const isCompactRestDay = displayModel?.layout === 'rest-compact'

  const rootClassName = isTrainingDay
    ? 'flex w-full flex-col gap-3 text-left'
    : `flex w-full flex-col text-center ${isCompactRestDay ? 'gap-2.5' : 'gap-3'}`
  const typeBadgeClassName = isTrainingDay
    ? 'border-fitloop-orange/30 bg-fitloop-orange/10 text-fitloop-orange'
    : 'border-fitloop-line/70 bg-fitloop-panel/90 text-slate-300'

  if (isCompactRestDay) {
    return (
      <div className="flex w-full flex-col items-center text-center">
        <h3 className="truncate text-sm font-bold text-slate-100">{header.title}</h3>
        {header.dateLabel ? (
          <p className="mt-1 text-[11px] leading-4 text-slate-400">{header.dateLabel}</p>
        ) : null}
        <span className="mt-2 rounded-full border border-fitloop-line/70 bg-fitloop-panel/90 px-2 py-0.5 text-[11px] font-semibold text-slate-300">
          {typeLabel}
        </span>
      </div>
    )
  }

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
          <h3 className={`truncate font-semibold text-slate-100 ${isCompactRestDay ? 'mt-1 text-base' : 'mt-2 text-lg'}`}>
            {header.title}
          </h3>
          {header.dateLabel ? (
            <p className="mt-1 text-xs leading-5 text-slate-400">{header.dateLabel}</p>
          ) : null}
        </div>
      </div>

      <div
        className={`flex w-full ${
          isTrainingDay
            ? 'flex-wrap items-center gap-2'
            : `flex-col items-center ${isCompactRestDay ? 'gap-1.5' : 'gap-2'}`
        }`}
      >
        <span
          className={`rounded-full border text-xs font-semibold ${isCompactRestDay ? 'px-2 py-0.5' : 'px-2.5 py-1'} ${typeBadgeClassName}`}
        >
          {typeLabel}
        </span>

        {isTrainingDay ? (
          <span className="rounded-full border border-fitloop-line/70 bg-black/10 px-2.5 py-1 text-xs text-slate-400">
            {exerciseCount} 个动作
          </span>
        ) : null}

        <p className={`text-slate-400 ${isCompactRestDay ? 'text-[11px] leading-4' : 'text-xs leading-5'}`}>
          {isTrainingDay ? preview.meta : `${preview.title} · ${preview.meta}`}
        </p>
      </div>
    </div>
  )
}

export default PlanDayCardHeader
