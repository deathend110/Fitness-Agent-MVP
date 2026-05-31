import ShellSidebar from './ShellSidebar.jsx'

function AppShell({ activeTabId, children, onTabChange, status, tabs }) {
  const isCoachTab = activeTabId === 'coach'
  const shellContentWrapperClassName = isCoachTab
    ? 'flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-canvas p-0'
    : 'flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-canvas p-4 sm:p-5 lg:p-6'
  const shellContentClassName = isCoachTab
    ? 'fitloop-shell__content min-h-0 flex-1 overflow-hidden'
    : 'fitloop-shell__content min-h-0 flex-1 overflow-y-auto overflow-x-hidden'

  return (
    <main className="flex h-screen overflow-hidden bg-fitloop-ink text-slate-800">
      <div className="flex min-h-0 w-full flex-col overflow-hidden lg:flex-row">
        <ShellSidebar
          activeTabId={activeTabId}
          onTabChange={onTabChange}
          status={status}
          tabs={tabs}
        />

        {/* AI 教练页需要把滚动和留白控制下沉给内部布局，其他页面继续沿用默认壳层。 */}
        <div className={shellContentWrapperClassName}>
          <section className={shellContentClassName}>
            {children}
          </section>
        </div>
      </div>
    </main>
  )
}

export default AppShell
