function PlanWeekGridColumn({ children, column, isExpanded = false }) {
  const baseClassName =
    'min-w-0 rounded-[1.25rem] border shadow-sm transition xl:[grid-column:span_var(--plan-column-span)_/_span_var(--plan-column-span)]'

  const trainingClassName = isExpanded
    ? 'border-fitloop-line bg-fitloop-panel/90 p-4 shadow-black/20 ring-1 ring-fitloop-orange/20'
    : 'border-fitloop-line bg-fitloop-panel/85 p-4 shadow-black/20'

  const restClassName = isExpanded
    ? 'border-fitloop-line/80 bg-fitloop-panel/88 px-3 py-4 shadow-black/10 ring-1 ring-fitloop-line'
    : 'border-fitloop-line/70 bg-fitloop-panel/78 px-3 py-4 shadow-black/10'

  return (
    <article
      className={`${baseClassName} ${column.isTrainingDay ? trainingClassName : restClassName}`}
      style={{ '--plan-column-span': column.desktopSpan }}
    >
      {children}
    </article>
  )
}

export default PlanWeekGridColumn
