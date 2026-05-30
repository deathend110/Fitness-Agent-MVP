import ShellIcon from './ShellIcon.jsx'

function ShellSidebar({ activeTab, activeTabId, onTabChange, tabs }) {
  return (
    <aside className="w-full shrink-0 lg:w-[15.5rem] xl:w-[16.5rem]">
      <div className="flex h-full flex-col justify-between rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel/92 p-4 shadow-2xl shadow-black/20">
        <div className="space-y-6">
          <div className="rounded-[1.25rem] border border-fitloop-line/70 bg-fitloop-ink/30 px-4 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-fitloop-orange">
              FitLoop MVP
            </p>
            <h1 className="mt-3 text-2xl font-semibold text-slate-100">训练工作台</h1>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              用统一壳层承载档案、计划、日志和 AI 教练四个核心工作区。
            </p>
          </div>

          <nav aria-label="主功能导航" className="space-y-1.5">
            {tabs.map((tab) => {
              const isActive = tab.id === activeTabId

              return (
                <button
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex w-full items-center gap-3 rounded-[1rem] border px-3 py-3 text-left transition ${
                    isActive
                      ? 'border-fitloop-orange/40 bg-fitloop-orange/10 text-fitloop-orange shadow-sm shadow-black/20'
                      : 'border-transparent bg-transparent text-slate-300 hover:border-fitloop-line hover:bg-fitloop-ink/30 hover:text-slate-100'
                  }`}
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  type="button"
                >
                  <span
                    className={`flex h-10 w-10 items-center justify-center rounded-2xl ${
                      isActive
                        ? 'bg-fitloop-orange text-white'
                        : 'bg-fitloop-ink/30 text-slate-300'
                    }`}
                  >
                    <ShellIcon name={tab.icon} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold">{tab.label}</span>
                    <span className="mt-1 block truncate text-xs text-slate-400">{tab.summary}</span>
                  </span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* 侧栏底部只保留当前工作区提示，避免和业务内容产生耦合。 */}
        <section className="mt-6 rounded-[1.25rem] border border-fitloop-line/70 bg-fitloop-ink/30 px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            当前工作区
          </p>
          <div className="mt-3 flex items-start gap-3">
            <span className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-2xl bg-fitloop-orange/10 text-fitloop-orange">
              <ShellIcon name={activeTab.icon} />
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-100">{activeTab.label}</p>
              <p className="mt-1 text-sm leading-6 text-slate-300">{activeTab.summary}</p>
            </div>
          </div>
        </section>
      </div>
    </aside>
  )
}

export default ShellSidebar
