function PlanWeekGrid({ layoutModel, renderColumn }) {
  return (
    <div className="overflow-x-hidden">
      <div
        className="grid grid-cols-1 items-start gap-3 xl:grid-cols-[var(--plan-grid-columns)]"
        style={{ '--plan-grid-columns': layoutModel.desktopTemplateColumns }}
      >
        {layoutModel.columns.map((column) => renderColumn(column))}
      </div>
    </div>
  )
}

export default PlanWeekGrid
