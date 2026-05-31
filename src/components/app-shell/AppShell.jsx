import ShellSidebar from './ShellSidebar.jsx'
import { getAppShellLayout } from './appShellLayout.js'

function AppShell({ activeTabId, children, onTabChange, status, tabs }) {
  const shellLayout = getAppShellLayout(activeTabId)

  return (
    <main className="flex h-screen overflow-hidden bg-fitloop-ink text-slate-800">
      <div className="flex min-h-0 w-full flex-col overflow-hidden lg:flex-row">
        <ShellSidebar
          activeTabId={activeTabId}
          onTabChange={onTabChange}
          status={status}
          tabs={tabs}
        />

        <div className={shellLayout.wrapperClassName}>
          <section className={shellLayout.contentClassName}>
            {children}
          </section>
        </div>
      </div>
    </main>
  )
}

export default AppShell
