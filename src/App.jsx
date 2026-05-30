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
import { loadStorage, migrateLegacyDemoData, saveStorage } from './utils/storage.js'
import { normalizeWeeklyPlan } from './utils/weeklyPlan.js'

function loadInitialState(key, fallback) {
  // 先执行一次性迁移，再读取当前版本的本地数据，避免旧 demo 数据继续灌入页面。
  migrateLegacyDemoData()
  return loadStorage(key, fallback)
}

function App() {
  const [activeTabId, setActiveTabId] = useState('profile')
  const [profile, setProfile] = useState(() => loadInitialState(storageKeys.profile, defaultProfile))
  const [weeklyPlan, setWeeklyPlan] = useState(() =>
    normalizeWeeklyPlan(loadInitialState(storageKeys.weeklyPlan, defaultWeeklyPlan)),
  )
  const [dailyLog, setDailyLog] = useState(() =>
    loadInitialState(storageKeys.dailyLog, defaultDailyLog),
  )
  const [chatHistory, setChatHistory] = useState(() =>
    loadInitialState(storageKeys.chatHistory, defaultChatHistory),
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

  function handleImportData({
    profile: nextProfile,
    weeklyPlan: nextWeeklyPlan,
    dailyLog: nextDailyLog,
    chatHistory: nextChatHistory,
  }) {
    setProfile(nextProfile)
    setWeeklyPlan(normalizeWeeklyPlan(nextWeeklyPlan))
    setDailyLog(nextDailyLog)
    setChatHistory(nextChatHistory)
  }

  function handleOpenCoachTab() {
    setActiveTabId('coach')
  }

  const tabs = [
    {
      id: 'profile',
      label: '我的档案',
      component: (
        <ProfileTab
          appState={{ profile, weeklyPlan, dailyLog, chatHistory }}
          onImportData={handleImportData}
          onProfileChange={setProfile}
          profile={profile}
        />
      ),
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
          onOpenCoach={handleOpenCoachTab}
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
        <header className="rounded-2xl border border-fitloop-line bg-fitloop-panel/80 px-6 py-6 shadow-xl shadow-black/20">
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-fitloop-orange">
                FitLoop MVP
              </p>
              <h1 className="mt-2 text-3xl font-bold text-slate-100 md:text-4xl">
                AI 健身教练与训练记录闭环
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                首次进入请先填写你的真实档案、训练计划和今日日志。AI 教练会基于你当前保存的本地数据自动注入上下文，并给出可采纳的训练建议。
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
                        ? 'border-fitloop-orange bg-fitloop-orange text-white shadow-sm shadow-black/20'
                        : 'border-fitloop-line bg-fitloop-panel text-slate-300 hover:border-fitloop-orange/30 hover:bg-fitloop-orange/8 hover:text-fitloop-orange'
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
          </div>
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
