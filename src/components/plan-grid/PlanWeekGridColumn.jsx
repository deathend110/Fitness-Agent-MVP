function PlanWeekGridColumn({ children, column }) {
  const baseClassName =
    'plan-week-grid-column min-w-0 rounded-[1.25rem] border shadow-sm transition'

  const trainingClassName = 'border-fitloop-line bg-fitloop-panel/85 p-4 shadow-black/20'

  const restClassName = 'border-fitloop-line/70 bg-fitloop-panel/78 px-3 py-4 shadow-black/10'

  return (
    <article
      className={`${baseClassName} ${column.isTrainingDay ? trainingClassName : restClassName}`}
    >
      {children}
      <style>{`
        .plan-week-grid-column > div > button {
          pointer-events: none;
        }

        .plan-week-grid-column > div > button[aria-expanded] {
          cursor: default;
        }

        .plan-week-grid-column > div > button > div:first-child > span:last-child {
          display: none;
        }

        .plan-week-grid-column > div > button > div:last-child {
          margin-top: 1rem;
        }
      `}</style>
    </article>
  )
}

export default PlanWeekGridColumn
