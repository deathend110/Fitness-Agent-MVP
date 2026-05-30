import { useEffect, useState } from 'react'
import AppShell from './components/app-shell/AppShell.jsx'
import {
  appShellTabs,
  buildAppShellStatus,
  getActiveShellTab,
} from './components/app-shell/appShellConfig.js'
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

  function renderActiveTab(tabId) {
    switch (tabId) {
      case 'profile':
        return (
          <ProfileTab
            appState={{ profile, weeklyPlan, dailyLog, chatHistory }}
            onImportData={handleImportData}
            onProfileChange={setProfile}
            profile={profile}
          />
        )
      case 'plan':
        return (
          <PlanTab
            onWeeklyPlanChange={setWeeklyPlan}
            profile={profile}
            weeklyPlan={weeklyPlan}
          />
        )
      case 'today':
        return (
          <TodayTab
            dailyLog={dailyLog}
            onDailyLogChange={setDailyLog}
            onOpenCoach={handleOpenCoachTab}
            profile={profile}
            weeklyPlan={weeklyPlan}
          />
        )
      case 'coach':
        return (
          <CoachTab
            chatHistory={chatHistory}
            dailyLog={dailyLog}
            onChatHistoryChange={setChatHistory}
            onWeeklyPlanChange={setWeeklyPlan}
            profile={profile}
            weeklyPlan={weeklyPlan}
          />
        )
      default:
        return (
          <ProfileTab
            appState={{ profile, weeklyPlan, dailyLog, chatHistory }}
            onImportData={handleImportData}
            onProfileChange={setProfile}
            profile={profile}
          />
        )
    }
  }

  // 壳层元信息与业务内容拆开，后续 V1.5 页面换肤只需替换承载层或 tab 本身。
  const activeTab = getActiveShellTab(activeTabId)
  const shellStatus = buildAppShellStatus()

  return (
    <AppShell
      activeTabId={activeTabId}
      onTabChange={setActiveTabId}
      status={shellStatus}
      tabs={appShellTabs}
    >
      {/* App 统一注入本地状态，Tab 只负责呈现和提交变更。 */}
      {renderActiveTab(activeTab.id)}
    </AppShell>
  )
}

export default App
