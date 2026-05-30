import ShellIcon from './ShellIcon.jsx'
import ShellStatusBar from './ShellStatusBar.jsx'

function ShellSidebar({ activeTabId, onTabChange, status, tabs }) {
  return (
    <aside className="w-full flex-shrink-0 border-b border-slate-100 bg-white lg:h-screen lg:w-60 lg:border-b-0 lg:border-r">
      <div className="flex h-full flex-col justify-between p-5">
        <div className="space-y-8">
          <div className="px-2">
            <h1 className="text-xl font-bold tracking-wide text-fitloop-orange">RepMind</h1>
          </div>

          <nav aria-label="主功能导航" className="space-y-1">
            {tabs.map((tab) => {
              const isActive = tab.id === activeTabId

              return (
                <button
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${
                    isActive
                      ? 'bg-fitloop-orange/10 font-semibold text-fitloop-orange'
                      : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                  }`}
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  type="button"
                >
                  <span
                    className={`flex h-5 w-5 flex-shrink-0 items-center justify-center ${
                      isActive ? 'text-fitloop-orange' : 'text-slate-400'
                    }`}
                  >
                    <ShellIcon name={tab.icon} />
                  </span>
                  <span className="min-w-0 flex-1 text-sm font-medium">{tab.label}</span>
                </button>
              )
            })}
          </nav>
        </div>

        <ShellStatusBar status={status} />
      </div>
    </aside>
  )
}

export default ShellSidebar
