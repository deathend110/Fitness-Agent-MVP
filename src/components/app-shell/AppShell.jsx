import ShellSidebar from './ShellSidebar.jsx'
import ShellStatusBar from './ShellStatusBar.jsx'

function AppShell({ activeTab, activeTabId, children, onTabChange, quickActions, status, tabs }) {
  return (
    <main className="min-h-screen bg-fitloop-ink text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col gap-4 px-4 py-4 lg:flex-row lg:px-6 lg:py-6">
        <ShellSidebar
          activeTab={activeTab}
          activeTabId={activeTabId}
          onTabChange={onTabChange}
          tabs={tabs}
        />

        {/* 主区域使用 min-w-0 与独立滚动容器，避免壳层默认制造整页横向滚动。 */}
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          <header className="rounded-[1.75rem] border border-fitloop-line bg-fitloop-panel/92 px-5 py-5 shadow-2xl shadow-black/20">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-fitloop-orange">
                  Workspace
                </p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-100">{activeTab.label}</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                  {activeTab.summary}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-400">
                <span className="rounded-full border border-fitloop-line bg-fitloop-ink/30 px-3 py-1.5">
                  4 个核心工作区
                </span>
                <span className="rounded-full border border-fitloop-orange/30 bg-fitloop-orange/10 px-3 py-1.5 text-fitloop-orange">
                  本地优先存储
                </span>
              </div>
            </div>
          </header>

          <section className="fitloop-shell__content min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
            {children}
          </section>

          <ShellStatusBar quickActions={quickActions} status={status} />
        </div>
      </div>
    </main>
  )
}

export default AppShell
