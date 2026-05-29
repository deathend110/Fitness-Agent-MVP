import { useState } from 'react'
import CoachTab from './tabs/CoachTab.jsx'
import PlanTab from './tabs/PlanTab.jsx'
import ProfileTab from './tabs/ProfileTab.jsx'
import TodayTab from './tabs/TodayTab.jsx'

const tabs = [
  { id: 'profile', label: '我的档案', component: <ProfileTab /> },
  { id: 'plan', label: '训练计划', component: <PlanTab /> },
  { id: 'today', label: '今日日志', component: <TodayTab /> },
  { id: 'coach', label: 'AI 教练', component: <CoachTab /> },
]

function App() {
  const [activeTabId, setActiveTabId] = useState('profile')
  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0]

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
              Sprint 1 正在搭建主页面入口。当前可以在 4 个核心 Tab 之间切换，后续会逐步接入本地数据和 AI 闭环。
            </p>
          </div>

          <nav aria-label="主功能导航" className="flex flex-wrap gap-2">
            {tabs.map((tab) => {
              const isActive = tab.id === activeTabId

              return (
              <button
                aria-current={isActive ? 'page' : undefined}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'border-fitloop-orange bg-fitloop-orange text-white'
                    : 'border-fitloop-line bg-fitloop-panel text-slate-300 hover:border-slate-400 hover:text-white'
                }`}
                key={tab.id}
                onClick={() => setActiveTabId(tab.id)}
                type="button"
              >
                {tab.label}
              </button>
              )
            })}
          </nav>
        </header>

        <section className="flex-1 py-10">
          {/* Tab 页面内容集中由 App 协调，后续各页面只负责自身业务。 */}
          {activeTab.component}
        </section>
      </section>
    </main>
  )
}

export default App
