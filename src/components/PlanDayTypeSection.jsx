import PlanDayCardButton from './PlanDayCardButton.jsx'

function PlanDayTypeSection({
  dayTypeListId,
  dayTypeOptions,
  dayTypeSuggestions,
  planType,
  onDayTypeChange,
}) {
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
