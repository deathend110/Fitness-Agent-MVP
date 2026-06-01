function CoachLayout({ sidebar, topbar, messages, composer }) {
  return (
    <div className="flex h-full overflow-hidden bg-fitloop-canvas">
      <aside className="hidden h-full w-[230px] shrink-0 overflow-hidden border-r border-fitloop-line bg-[#f0f3fd] lg:flex lg:flex-col">
        {sidebar}
      </aside>

      <section className="flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-panel">
        <header className="shrink-0 px-4 py-3 sm:px-7">
          {topbar}
        </header>

        <main className="relative min-h-0 flex-1 overflow-hidden">
          <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-10 bg-gradient-to-b from-fitloop-panel via-fitloop-panel/88 to-transparent" />
          {messages}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-12 bg-gradient-to-t from-fitloop-panel via-fitloop-panel/92 to-transparent" />
        </main>

        <footer className="shrink-0 px-4 py-4 sm:px-7">
          {composer}
        </footer>
      </section>
    </div>
  )
}

export default CoachLayout
