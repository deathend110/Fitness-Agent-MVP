import ShellIcon from './ShellIcon.jsx'

function ShellStatusBar({ status }) {
  return (
    <section className="border-t border-slate-100 px-2 pt-4">
      <div className="flex items-start gap-3 rounded-2xl bg-slate-50 px-3 py-3">
        <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
          <ShellIcon className="h-4 w-4" name="check" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-700">{status.saveStateLabel}</p>
          <p className="mt-1 text-xs text-slate-400">{status.storageLabel}</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">{status.helperLabel}</p>
        </div>
      </div>
    </section>
  )
}

export default ShellStatusBar
