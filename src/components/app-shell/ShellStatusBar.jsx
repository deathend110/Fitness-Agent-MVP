import ShellIcon from './ShellIcon.jsx'

function ShellStatusBar({ status }) {
  return (
    <section className="border-t border-slate-100 px-2 pt-4">
      <div className="flex items-center gap-2">
        <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
          <ShellIcon className="h-3 w-3" name="check" />
        </span>
        <div className="text-xs">
          <p className="font-semibold text-slate-700">{status.saveStateLabel}</p>
          <p className="text-slate-400">{status.storageLabel}</p>
        </div>
      </div>
    </section>
  )
}

export default ShellStatusBar
