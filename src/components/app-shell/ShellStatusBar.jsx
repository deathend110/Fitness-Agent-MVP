import ShellIcon from './ShellIcon.jsx'

function ShellStatusBar({ quickActions, status }) {
  return (
    <footer className="rounded-[1.5rem] border border-fitloop-line bg-fitloop-panel/92 px-4 py-4 shadow-xl shadow-black/20">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600">
            <ShellIcon name="check" />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-100">{status.saveStateLabel}</p>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-fitloop-ink/30 px-2.5 py-1">
                <ShellIcon className="h-3.5 w-3.5" name="storage" />
                {status.storageLabel}
              </span>
              <span>{status.helperLabel}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {quickActions.map((action) => {
            const toneClassName =
              action.tone === 'primary'
                ? 'border-fitloop-orange bg-fitloop-orange text-white'
                : 'border-fitloop-line bg-fitloop-panel text-slate-300 hover:border-fitloop-orange/40 hover:text-fitloop-orange'

            return (
              <button
                className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition ${toneClassName}`}
                key={action.id}
                type="button"
              >
                <ShellIcon className="h-4 w-4" name={action.icon} />
                {action.label}
              </button>
            )
          })}
        </div>
      </div>
    </footer>
  )
}

export default ShellStatusBar
