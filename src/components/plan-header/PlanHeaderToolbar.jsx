import PlanHeaderLegend from './PlanHeaderLegend.jsx'

function PlanHeaderToolbar({ headerModel }) {
  return (
    <header className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        <h2 className="text-[1.75rem] font-bold leading-none text-slate-900">本周训练计划</h2>

        <span className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-600 shadow-sm shadow-black/20">
          <span>{headerModel.weekRangeLabel}</span>
          <svg
            aria-hidden="true"
            className="h-4 w-4 text-slate-400"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2z" />
          </svg>
        </span>

        <span className="inline-flex items-center rounded-md bg-fitloop-orange/10 px-2.5 py-1 text-xs font-bold text-fitloop-orange">
          {headerModel.weekBadgeLabel}
        </span>

        <button
          aria-label={headerModel.settingsButton.label}
          className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm shadow-black/20 transition hover:border-slate-300 hover:text-slate-800"
          title={headerModel.settingsButton.hint}
          type="button"
        >
          {headerModel.settingsButton.label}
        </button>
      </div>

      <div className="flex min-w-0 items-center gap-6">
        <div className="inline-flex items-center rounded-xl border border-slate-200/80 bg-slate-100 p-0.5">
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
