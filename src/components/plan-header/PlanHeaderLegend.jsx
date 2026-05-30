function PlanHeaderLegend({ items = [] }) {
  return (
    <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-500">
      {items.map((item) => {
        const dotClassName =
          item.tone === 'main' ? 'bg-fitloop-orange' : item.tone === 'accessory' ? 'bg-sky-600' : 'bg-slate-300'

        return (
          <div className="flex items-center gap-1.5 whitespace-nowrap" key={`${item.tone}-${item.label}`}>
            <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${dotClassName}`} />
            <span>{item.label}</span>
          </div>
        )
      })}
    </div>
  )
}

export default PlanHeaderLegend
