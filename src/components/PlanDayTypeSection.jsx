function PlanDayTypeSection({
  compact = false,
  dayTypeListId,
  planType,
  onDayTypeChange,
}) {
  const isRestDay = planType === 'rest'
  const modeValue = isRestDay ? 'rest' : 'training'

  function handleModeChange(event) {
    const nextMode = event.target.value
    if (nextMode === 'rest') {
      onDayTypeChange('rest')
      return
    }

    if (planType === 'rest') {
      onDayTypeChange('腿日')
    }
  }

  return (
    <div className={compact ? 'mt-3 border-t border-fitloop-line/60 pt-3' : 'space-y-2'}>
      <label className="block">
        <div className="relative">
          <select
            aria-label="训练类型"
            className="w-full appearance-none rounded-xl border border-fitloop-line bg-fitloop-panel px-3 py-2.5 pr-10 text-slate-100 outline-none transition focus:border-fitloop-orange"
            id={dayTypeListId}
            onChange={handleModeChange}
            value={modeValue}
          >
            <option value="training">训练日</option>
            <option value="rest">休息日</option>
          </select>
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-500">
            <span className="h-0 w-0 border-x-[5px] border-x-transparent border-t-[7px] border-t-slate-500" />
          </span>
        </div>
      </label>
    </div>
  )
}

export default PlanDayTypeSection
