import ShellIcon from './app-shell/ShellIcon.jsx'

function CoachArrowIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="m15 18-6-6 6-6" />
    </svg>
  )
}

function CoachPlusIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </svg>
  )
}

function CoachFolderIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
    </svg>
  )
}

function CoachChevronUpIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="m6 14 6-6 6 6" />
    </svg>
  )
}

function CoachSidebar({ activeRecordId, onRecordSelect, records }) {
  return (
    <aside className="flex h-full w-full flex-col border-b border-[#d9e2f4] bg-[#edf3ff] lg:w-[15.5rem] lg:border-b-0 lg:border-r">
      <div className="flex items-center justify-between px-4 pt-4">
        <button
          aria-label="返回"
          className="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-500 transition hover:bg-white/70 hover:text-slate-700"
          type="button"
        >
          <CoachArrowIcon />
        </button>

        <button
          className="inline-flex h-8 items-center justify-center rounded-full px-2 text-slate-400 transition hover:bg-white/70 hover:text-slate-600"
          type="button"
        >
          <span className="text-sm">□</span>
        </button>
      </div>

      <div className="mt-5 space-y-4 px-4">
        <button
          className="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left text-sm text-slate-400 transition hover:bg-white/60 hover:text-slate-600"
          type="button"
        >
          <span className="flex h-5 w-5 items-center justify-center">
            <CoachPlusIcon />
          </span>
          <span>创建对话</span>
        </button>

        <div>
          <button
            className="flex w-full items-center justify-between rounded-xl px-2 py-2 text-left text-sm text-slate-600 transition hover:bg-white/60"
            type="button"
          >
            <span className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center text-slate-500">
                <CoachFolderIcon />
              </span>
              <span>项目</span>
            </span>
            <span className="text-slate-400">
              <CoachChevronUpIcon />
            </span>
          </button>

          <button
            className="mt-2 flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left text-sm text-slate-500 transition hover:bg-white/60"
            type="button"
          >
            <span className="flex h-5 w-5 items-center justify-center">
              <CoachPlusIcon />
            </span>
            <span>创建项目</span>
          </button>
        </div>
      </div>

      <div className="mt-5 flex-1 overflow-y-auto px-4 pb-4">
        <p className="px-2 text-xs uppercase tracking-[0.24em] text-slate-400">测试</p>
        <div className="mt-3 space-y-1">
          {records.map((record) => {
            const isActive = record.id === activeRecordId || record.active

            return (
              <button
                aria-current={isActive ? 'page' : undefined}
                className={`flex w-full rounded-2xl px-3 py-2 text-left text-sm transition ${
                  isActive
                    ? 'bg-white/80 font-medium text-slate-700 shadow-sm shadow-black/10'
                    : 'text-slate-600 hover:bg-white/55 hover:text-slate-700'
                }`}
                key={record.id}
                onClick={() => onRecordSelect?.(record.id)}
                type="button"
              >
                <span className="min-w-0 flex-1 truncate">{record.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="border-t border-[#d9e2f4] px-4 py-4">
        <button
          className="flex items-center gap-2 text-sm text-slate-500 transition hover:text-slate-700"
          type="button"
        >
          <ShellIcon className="h-4 w-4" name="settings" />
          <span>设置</span>
        </button>
      </div>
    </aside>
  )
}

export default CoachSidebar
