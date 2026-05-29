const tabs = ['我的档案', '训练计划', '今日日志', 'AI 教练']

function App() {
  return (
    <main className="min-h-screen bg-fitloop-ink text-slate-100">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8">
        <header className="flex flex-col gap-5 border-b border-fitloop-line pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-fitloop-orange">
              FitLoop MVP
            </p>
            <h1 className="mt-2 text-3xl font-bold text-white md:text-4xl">
              AI 健身教练与训练记录闭环
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
              Sprint 0 已建立 React + Vite + Tailwind 基础界面，后续会逐步接入档案、训练计划、今日日志和 AI 教练。
            </p>
          </div>

          <nav className="flex flex-wrap gap-2">
            {tabs.map((tab, index) => (
              <button
                className={`rounded-md border px-3 py-2 text-sm font-medium transition ${
                  index === 0
                    ? 'border-fitloop-orange bg-fitloop-orange text-white'
                    : 'border-fitloop-line bg-fitloop-panel text-slate-300 hover:border-slate-400 hover:text-white'
                }`}
                key={tab}
                type="button"
              >
                {tab}
              </button>
            ))}
          </nav>
        </header>

        <section className="grid flex-1 place-items-center py-16">
          <div className="w-full max-w-3xl rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
            <p className="text-sm font-semibold text-fitloop-mint">当前阶段：Sprint 0</p>
            <h2 className="mt-3 text-2xl font-bold text-white">项目准备完成后进入核心骨架开发</h2>
            <p className="mt-4 leading-7 text-slate-300">
              本页用于确认开发服务器、Tailwind 样式和 React 入口已可用。下一步会按照任务文档实现 4 个 Tab 的真实路由框架和 localStorage 数据工具。
            </p>
          </div>
        </section>
      </section>
    </main>
  )
}

export default App
