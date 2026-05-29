import { useEffect, useState } from 'react'
import CoachTab from './tabs/CoachTab.jsx'
import PlanTab from './tabs/PlanTab.jsx'
import ProfileTab from './tabs/ProfileTab.jsx'
import TodayTab from './tabs/TodayTab.jsx'
import {
  defaultChatHistory,
  defaultDailyLog,
  defaultProfile,
  defaultWeeklyPlan,
  storageKeys,
} from './utils/defaultData.js'
import { loadStorage, saveStorage } from './utils/storage.js'

function App() {
  const [activeTabId, setActiveTabId] = useState('profile')
  const [profile, setProfile] = useState(() => loadStorage(storageKeys.profile, defaultProfile))
  const [weeklyPlan, setWeeklyPlan] = useState(() =>
    loadStorage(storageKeys.weeklyPlan, defaultWeeklyPlan),
  )
  const [dailyLog, setDailyLog] = useState(() =>
    loadStorage(storageKeys.dailyLog, defaultDailyLog),
  )
  const [chatHistory, setChatHistory] = useState(() =>
    loadStorage(storageKeys.chatHistory, defaultChatHistory),
  )

  useEffect(() => {
    saveStorage(storageKeys.profile, profile)
  }, [profile])

  useEffect(() => {
    saveStorage(storageKeys.weeklyPlan, weeklyPlan)
  }, [weeklyPlan])

  useEffect(() => {
    saveStorage(storageKeys.dailyLog, dailyLog)
  }, [dailyLog])

  useEffect(() => {
    saveStorage(storageKeys.chatHistory, chatHistory)
  }, [chatHistory])

  const tabs = [
    {
      id: 'profile',
      label: '我的档案',
      component: <ProfileTab profile={profile} onProfileChange={setProfile} />,
    },
    {
      id: 'plan',
      label: '训练计划',
      component: (
        <PlanTab
          onWeeklyPlanChange={setWeeklyPlan}
          profile={profile}
          weeklyPlan={weeklyPlan}
        />
      ),
    },
    {
      id: 'today',
      label: '今日日志',
      component: (
        <TodayTab
          dailyLog={dailyLog}
          onDailyLogChange={setDailyLog}
          profile={profile}
          weeklyPlan={weeklyPlan}
        />
      ),
    },
    {
      id: 'coach',
      label: 'AI 教练',
      component: (
        <CoachTab
          chatHistory={chatHistory}
          dailyLog={dailyLog}
          onChatHistoryChange={setChatHistory}
          onWeeklyPlanChange={setWeeklyPlan}
          profile={profile}
          weeklyPlan={weeklyPlan}
        />
      ),
    },
  ]

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
              当前已接入 localStorage 默认数据。即使浏览器里还没有任何记录，也能直接看到档案、训练计划、今日日志和 AI 对话摘要，方便后续继续做编辑和闭环能力。
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
          {/* App 统一注入本地状态，Tab 只负责呈现和提交变更。 */}
          {activeTab.component}
        </section>
      </section>
    </main>
  )
}

export default App
