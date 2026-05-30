function PlanWeekGridColumn({ children, column, isExpanded = false }) {
  const surfaceClassName = column.isTrainingDay
    ? 'border-fitloop-line bg-fitloop-panel/85 shadow-black/20'
    : 'border-fitloop-line/80 bg-fitloop-ink/35 shadow-black/10'

  return (
    <article
      className={`min-w-0 rounded-[1.25rem] border p-4 shadow-sm transition xl:[grid-column:span_var(--plan-column-span)_/_span_var(--plan-column-span)] ${surfaceClassName} ${
        isExpanded ? 'ring-1 ring-fitloop-orange/20' : ''
      }`}
      style={{ '--plan-column-span': column.desktopSpan }}
    >
      {children}
    </article>
  )
}

export default PlanWeekGridColumn
