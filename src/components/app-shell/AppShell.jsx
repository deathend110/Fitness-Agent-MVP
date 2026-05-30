import ShellSidebar from './ShellSidebar.jsx'

function AppShell({ activeTabId, children, onTabChange, status, tabs }) {
  return (
    <main className="flex h-screen overflow-hidden bg-fitloop-ink text-slate-800">
      <div className="flex min-h-0 w-full flex-col overflow-hidden lg:flex-row">
        <ShellSidebar
          activeTabId={activeTabId}
          onTabChange={onTabChange}
          status={status}
          tabs={tabs}
        />

        {/* 主区域保留独立滚动，避免页面级横向滚动并为各 tab 复用同一浅色壳层。 */}
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-canvas p-4 sm:p-5 lg:p-6">
          <section className="fitloop-shell__content fitloop-shell__main min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
            {children}
          </section>
        </div>
      </div>
    </main>
  )
}

export default AppShell
