import PlanHeaderLegend from './PlanHeaderLegend.jsx'

function PlanHeaderToolbar({ headerModel }) {
  return (
    <header className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 flex-col gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-3">
          <h2 className="text-[1.75rem] font-bold leading-none text-slate-900">本周训练计划</h2>
          <span className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-600 shadow-sm shadow-black/20">
            {headerModel.weekRangeLabel}
          </span>
          <span className="inline-flex items-center rounded-md bg-fitloop-orange/10 px-2.5 py-1 text-xs font-bold text-fitloop-orange">
            {headerModel.weekBadgeLabel}
          </span>
        </div>

        <button
          aria-label={headerModel.settingsButton.label}
          className="inline-flex w-fit items-center rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 shadow-sm shadow-black/20 transition hover:border-slate-300 hover:text-slate-800"
          title={headerModel.settingsButton.hint}
          type="button"
        >
          {headerModel.settingsButton.label}
        </button>
      </div>

      <div className="flex min-w-0 flex-col gap-3 lg:items-end">
        <div className="inline-flex w-fit items-center rounded-xl border border-slate-200/80 bg-slate-100 p-0.5">
          {headerModel.viewTabs.map((tab) => {
            const tabClassName = tab.isActive
              ? 'bg-white text-fitloop-orange shadow-sm shadow-black/20'
              : 'text-slate-500'

            return (
              <button
                aria-pressed={tab.isActive}
                className={`rounded-lg px-4 py-1.5 text-xs font-semibold transition ${tabClassName}`}
                key={tab.key}
                type="button"
              >
                {tab.label}
              </button>
            )
          })}
        </div>

        <PlanHeaderLegend items={headerModel.legendItems} />
      </div>
    </header>
  )
}

export default PlanHeaderToolbar
