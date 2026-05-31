function CoachLayout({ sidebar, topbar, messages, composer }) {
  return (
    <div className="flex h-full overflow-hidden bg-fitloop-canvas">
      <aside className="hidden h-full w-[230px] shrink-0 overflow-hidden border-r border-fitloop-line bg-[#f0f3fd] lg:flex lg:flex-col">
        {sidebar}
      </aside>

      <section className="flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-panel">
        <header className="shrink-0 border-b border-fitloop-line/70 px-4 py-3 sm:px-7">
          {topbar}
        </header>

        <main className="min-h-0 flex-1 overflow-hidden">{messages}</main>

        <footer className="shrink-0 border-t border-fitloop-line/70 px-4 py-4 sm:px-7">
          {composer}
        </footer>
      </section>
    </div>
  )
}

export default CoachLayout
