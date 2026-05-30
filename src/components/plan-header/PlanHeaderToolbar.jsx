import PlanHeaderLegend from './PlanHeaderLegend.jsx'

function PlanHeaderToolbar({ headerModel }) {
  return (
    <header className="flex min-w-0 flex-col gap-4 rounded-[1.25rem] border border-fitloop-line bg-fitloop-panel/80 p-5 shadow-sm shadow-black/20">
      <div className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-3">
          <div className="space-y-2">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-fitloop-orange">
              Plan
            </p>
            <div className="flex min-w-0 flex-wrap items-center gap-3">
              <h2 className="text-3xl font-semibold text-slate-100">{headerModel.title}</h2>
              <span className="rounded-full border border-fitloop-orange/30 bg-fitloop-orange/10 px-3 py-1 text-xs font-semibold text-fitloop-orange">
                {headerModel.weekBadgeLabel}
              </span>
            </div>
          </div>

          <div className="flex min-w-0 flex-wrap items-center gap-3 text-sm text-slate-300">
            <span className="rounded-xl border border-fitloop-line/70 bg-black/10 px-3 py-2 font-medium text-slate-300">
              {headerModel.weekRangeLabel}
            </span>
            <PlanHeaderLegend items={headerModel.legendItems} />
          </div>
        </div>

        <button
          className="inline-flex shrink-0 items-center justify-center rounded-xl border border-fitloop-line/70 bg-black/10 px-4 py-2.5 text-sm font-medium text-slate-400"
          disabled
          title={headerModel.settingsButton.hint}
          type="button"
        >
          {headerModel.settingsButton.label}
        </button>
      </div>
    </header>
  )
}

export default PlanHeaderToolbar
