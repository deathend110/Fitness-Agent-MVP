function getLegendDotClassName(tone) {
  if (tone === 'main') {
    return 'bg-fitloop-orange'
  }

  return 'bg-repmind-textSoft'
}

function PlanHeaderLegend({ items = [] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs font-medium text-slate-400">
      {items.map((item) => (
        <div className="flex items-center gap-2 whitespace-nowrap" key={`${item.tone}-${item.label}`}>
          <span
            aria-hidden="true"
            className={`h-2.5 w-2.5 rounded-full ${getLegendDotClassName(item.tone)}`}
          />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  )
}

export default PlanHeaderLegend
