function PlanWeekGridColumn({ children, column }) {
  const baseClassName = 'min-w-0 rounded-[1.25rem] border shadow-sm transition'
  const trainingClassName = 'border-fitloop-line bg-fitloop-panel/85 p-4 shadow-black/20'
  const restClassName = 'border-fitloop-line/70 bg-fitloop-panel/78 px-3 py-4 shadow-black/10'

  return (
    <article
      className={`${baseClassName} ${column.isTrainingDay ? trainingClassName : restClassName}`}
    >
      {children}
    </article>
  )
}

export default PlanWeekGridColumn
