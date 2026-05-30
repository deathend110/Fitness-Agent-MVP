import PlanDayCardButton from './PlanDayCardButton.jsx'

function PlanDayTypeSection({
  compact = false,
  compactLabel = '改为训练日',
  dayTypeListId,
  dayTypeOptions,
  dayTypeSuggestions,
  planType,
  onDayTypeChange,
}) {
  const quickOptions = compact
    ? dayTypeOptions.filter((option) => option !== 'rest')
    : dayTypeOptions

  if (compact) {
    return (
      <div className="mt-3 border-t border-fitloop-line/60 pt-3">
        <p className="mb-2 text-[11px] font-medium text-slate-500">{compactLabel}</p>
        <div className="flex flex-wrap justify-center gap-1.5">
          {quickOptions.map((option) => (
            <PlanDayCardButton key={option} onClick={() => onDayTypeChange(option)}>
              {option}
            </PlanDayCardButton>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <label className="block space-y-2">
        <span className="text-sm text-slate-300">训练类型</span>
        <input
          className="w-full rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 text-slate-100 outline-none transition focus:border-fitloop-orange"
          list={dayTypeListId}
          onChange={(event) => onDayTypeChange(event.target.value)}
          value={planType}
        />
      </label>
      <datalist id={dayTypeListId}>
        {dayTypeSuggestions.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
      <div className="flex flex-wrap gap-2">
        {dayTypeOptions.map((option) => (
          <PlanDayCardButton key={option} onClick={() => onDayTypeChange(option)}>
            {option}
          </PlanDayCardButton>
        ))}
      </div>
    </div>
  )
}

export default PlanDayTypeSection
