import { useEffect, useRef, useState } from 'react'
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
import {
  isSameAppDataSnapshot,
  loadAppData,
  saveDailyLog,
  saveProfile,
  saveWeeklyPlan,
} from './api/appData.js'
import {
  hasLocalMigrationFlag,
  importLocalStorageToBackend,
  isLocalMigrationCandidate,
} from './utils/localMigration.js'
import { loadStorage, migrateLegacyDemoData, saveStorage } from './utils/storage.js'
import { normalizeWeeklyPlan } from './utils/weeklyPlan.js'

function loadInitialState(key, fallback) {
  // 先执行一次性迁移，再读取当前版本的本地数据，避免旧 demo 数据继续灌入页面。
  migrateLegacyDemoData()
  return loadStorage(key, fallback)
}

function App() {
  const [activeTabId, setActiveTabId] = useState('profile')
  const [hasVisitedCoachTab, setHasVisitedCoachTab] = useState(false)
  const [profile, setProfile] = useState(() => loadInitialState(storageKeys.profile, defaultProfile))
  const [weeklyPlan, setWeeklyPlan] = useState(() =>
    normalizeWeeklyPlan(loadInitialState(storageKeys.weeklyPlan, defaultWeeklyPlan)),
  )
  const [planSource, setPlanSource] = useState(() => ({ activeSource: 'manual' }))
  const [effectiveWeeklyPlan, setEffectiveWeeklyPlan] = useState(() =>
    normalizeWeeklyPlan(loadInitialState(storageKeys.weeklyPlan, defaultWeeklyPlan)),
  )
  const [activeCyclePlan, setActiveCyclePlan] = useState(null)
  const [dailyLog, setDailyLog] = useState(() =>
    loadInitialState(storageKeys.dailyLog, defaultDailyLog),
  )
  const [chatHistory, setChatHistory] = useState(() =>
    loadInitialState(storageKeys.chatHistory, defaultChatHistory),
  )
  const [isBootstrapping, setIsBootstrapping] = useState(true)
  const [backendStatus, setBackendStatus] = useState({
    mode: 'loading',
    message: '正在连接本地后端并加载训练数据...',
  })
  const [migrationPrompt, setMigrationPrompt] = useState({
    visible: false,
    reason: '',
  })
  const syncedProfileRef = useRef(null)
  const syncedWeeklyPlanRef = useRef(null)
  const syncedDailyLogRef = useRef(null)

  function handleWeeklyPlanChange(nextWeeklyPlanOrUpdater) {
    setWeeklyPlan((currentWeeklyPlan) => {
      const nextWeeklyPlan = normalizeWeeklyPlan(
        typeof nextWeeklyPlanOrUpdater === 'function'
          ? nextWeeklyPlanOrUpdater(currentWeeklyPlan)
          : nextWeeklyPlanOrUpdater,
      )

      // 只有真正进入活动周期后，effectiveWeeklyPlan 才应脱离 manual weeklyPlan。
      if (planSource.activeSource === 'manual' || !Number.isInteger(activeCyclePlan?.cycle?.id)) {
        setEffectiveWeeklyPlan(nextWeeklyPlan)
      }

      return nextWeeklyPlan
    })
  }

  useEffect(() => {
    let cancelled = false
    const abortController = new AbortController()

    async function bootstrapAppData() {
      try {
        const nextData = await loadAppData({ signal: abortController.signal })

        if (cancelled) {
          return
        }

        setProfile(nextData.profile)
        setWeeklyPlan(normalizeWeeklyPlan(nextData.weeklyPlan))
        setPlanSource(nextData.planSource ?? { activeSource: 'manual' })
        setEffectiveWeeklyPlan(
          normalizeWeeklyPlan(nextData.effectiveWeeklyPlan ?? nextData.weeklyPlan),
        )
        setActiveCyclePlan(nextData.activeCyclePlan ?? null)
        setDailyLog(nextData.dailyLog)
        syncedProfileRef.current = nextData.profile
        syncedWeeklyPlanRef.current = normalizeWeeklyPlan(nextData.weeklyPlan)
        syncedDailyLogRef.current = nextData.dailyLog
        const localDataSnapshot = { profile, weeklyPlan, dailyLog, chatHistory }
        const backendIsEmpty =
          isSameAppDataSnapshot(nextData.profile, defaultProfile) &&
          isSameAppDataSnapshot(normalizeWeeklyPlan(nextData.weeklyPlan), defaultWeeklyPlan) &&
          isSameAppDataSnapshot(nextData.dailyLog, defaultDailyLog)

        if (
          backendIsEmpty &&
          isLocalMigrationCandidate(localDataSnapshot) &&
          !hasLocalMigrationFlag()
        ) {
          setMigrationPrompt({
            visible: true,
            reason: 'local_data_detected',
          })
        } else {
          setMigrationPrompt({
            visible: false,
            reason: '',
          })
        }
        setBackendStatus({
          mode: 'ready',
          message: '当前档案、周计划和今日日志已切换为后端数据源。',
        })
      } catch (error) {
        if (cancelled) {
          return
        }

        setBackendStatus({
          mode: 'fallback',
          message: `${error.message} 当前先展示本地缓存数据，页面仍可继续演示。`,
        })
        setMigrationPrompt({
          visible: false,
          reason: '',
        })
      } finally {
        if (!cancelled) {
          setIsBootstrapping(false)
        }
      }
    }

    bootstrapAppData()

    return () => {
      cancelled = true
      abortController.abort()
    }
  }, [])

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

  useEffect(() => {
    if (isBootstrapping || backendStatus.mode !== 'ready') {
      return
    }

    if (isSameAppDataSnapshot(syncedProfileRef.current, profile)) {
      return
    }

    saveProfile(profile)
      .then((savedProfile) => {
        syncedProfileRef.current = savedProfile
      })
      .catch((error) => {
        console.warn('[app] 同步 profile 到后端失败，当前仅保留本地缓存。', error)
        setBackendStatus({
          mode: 'fallback',
          message: `${error.message} 当前改动已保留在本地缓存，后端恢复后可继续同步。`,
        })
      })
  }, [backendStatus.mode, isBootstrapping, profile])

  useEffect(() => {
    if (isBootstrapping || backendStatus.mode !== 'ready') {
      return
    }

    if (isSameAppDataSnapshot(syncedWeeklyPlanRef.current, weeklyPlan)) {
      return
    }

    saveWeeklyPlan(weeklyPlan)
      .then((savedWeeklyPlan) => {
        syncedWeeklyPlanRef.current = savedWeeklyPlan
      })
      .catch((error) => {
        console.warn('[app] 同步 weeklyPlan 到后端失败，当前仅保留本地缓存。', error)
        setBackendStatus({
          mode: 'fallback',
          message: `${error.message} 当前改动已保留在本地缓存，后端恢复后可继续同步。`,
        })
      })
  }, [backendStatus.mode, isBootstrapping, weeklyPlan])

  useEffect(() => {
    if (isBootstrapping || backendStatus.mode !== 'ready') {
      return
    }

    if (isSameAppDataSnapshot(syncedDailyLogRef.current, dailyLog)) {
      return
    }

    saveDailyLog(dailyLog, {
      previousDailyLog: syncedDailyLogRef.current ?? defaultDailyLog,
    })
      .then((savedDailyLog) => {
        syncedDailyLogRef.current = savedDailyLog
      })
      .catch((error) => {
        console.warn('[app] 同步 dailyLog 到后端失败，当前仅保留本地缓存。', error)
        setBackendStatus({
          mode: 'fallback',
          message: `${error.message} 当前改动已保留在本地缓存，后端恢复后可继续同步。`,
        })
      })
  }, [backendStatus.mode, dailyLog, isBootstrapping])

  function handleImportData({
    profile: nextProfile,
    weeklyPlan: nextWeeklyPlan,
    dailyLog: nextDailyLog,
    chatHistory: nextChatHistory,
  }) {
    const normalizedWeeklyPlan = normalizeWeeklyPlan(nextWeeklyPlan)

    setProfile(nextProfile)
    setWeeklyPlan(normalizedWeeklyPlan)
    setEffectiveWeeklyPlan(normalizedWeeklyPlan)
    setPlanSource({ activeSource: 'manual' })
    setActiveCyclePlan(null)
    setDailyLog(nextDailyLog)
    setChatHistory(nextChatHistory)
  }

  function handleOpenCoachTab() {
    setHasVisitedCoachTab(true)
    setActiveTabId('coach')
  }

  useEffect(() => {
    if (activeTabId === 'coach') {
      // AI 教练存在发送中和流式中的页内状态，切换到其他 tab 时不能卸载。
      setHasVisitedCoachTab(true)
    }
  }, [activeTabId])

  function handleDismissMigrationPrompt() {
    setMigrationPrompt((currentPrompt) => ({
      ...currentPrompt,
      visible: false,
    }))
  }

  async function handleImportToBackend() {
    const localDataSnapshot = { profile, weeklyPlan, dailyLog, chatHistory }
    const result = await importLocalStorageToBackend(localDataSnapshot)

    syncedProfileRef.current = profile
    syncedWeeklyPlanRef.current = weeklyPlan
    syncedDailyLogRef.current = dailyLog
    setMigrationPrompt({
      visible: false,
      reason: 'completed',
    })
    setBackendStatus({
      mode: 'ready',
      message: '已将 localStorage 数据导入后端；chatHistory 仍继续保留在本地。',
    })

    return result
  }

  function renderMainTab(tabId) {
    switch (tabId) {
      case 'profile':
        return (
          <ProfileTab
            appState={{ profile, weeklyPlan, dailyLog, chatHistory }}
            backendStatus={backendStatus}
            migrationPrompt={migrationPrompt}
            onDismissMigrationPrompt={handleDismissMigrationPrompt}
            onImportData={handleImportData}
            onImportToBackend={handleImportToBackend}
            onProfileChange={setProfile}
            profile={profile}
          />
        )
      case 'plan':
        return (
          <PlanTab
            activeCyclePlan={activeCyclePlan}
            effectiveWeeklyPlan={effectiveWeeklyPlan}
            onActiveCyclePlanChange={setActiveCyclePlan}
            onEffectiveWeeklyPlanChange={(nextPlan) =>
              setEffectiveWeeklyPlan(normalizeWeeklyPlan(nextPlan))
            }
            onPlanSettingsClick={() => {}}
            onPlanSourceChange={setPlanSource}
            planSource={planSource}
            onWeeklyPlanChange={handleWeeklyPlanChange}
            profile={profile}
            weeklyPlan={weeklyPlan}
          />
        )
      case 'today':
        return (
          <TodayTab
            dailyLog={dailyLog}
            effectiveWeeklyPlan={effectiveWeeklyPlan}
            onDailyLogChange={setDailyLog}
            onOpenCoach={handleOpenCoachTab}
            profile={profile}
          />
        )
      default:
        return (
          <ProfileTab
            appState={{ profile, weeklyPlan, dailyLog, chatHistory }}
            backendStatus={backendStatus}
            migrationPrompt={migrationPrompt}
            onDismissMigrationPrompt={handleDismissMigrationPrompt}
            onImportData={handleImportData}
            onImportToBackend={handleImportToBackend}
            onProfileChange={setProfile}
            profile={profile}
          />
        )
    }
  }

  function renderCoachTab() {
    return (
      <CoachTab
        chatHistory={chatHistory}
        dailyLog={dailyLog}
        effectiveWeeklyPlan={effectiveWeeklyPlan}
        onChatHistoryChange={setChatHistory}
        onWeeklyPlanChange={handleWeeklyPlanChange}
        profile={profile}
      />
    )
  }

  // 壳层元信息与业务内容拆开，后续 V1.5 页面换肤只需替换承载层或 tab 本身。
  const activeTab = getActiveShellTab(activeTabId)
  const shellStatus = buildAppShellStatus()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {backendStatus.mode === 'fallback' ? (
        <div className="mx-auto max-w-[1600px] px-4 pt-4 sm:px-6">
          {/* 只在后端不可用时提醒用户，正常同步成功不再占用顶部空间。 */}
          <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            {backendStatus.message}
          </div>
        </div>
      ) : null}
      <AppShell
        activeTabId={activeTabId}
        onTabChange={setActiveTabId}
        status={shellStatus}
        tabs={appShellTabs}
      >
        {/* App 统一注入状态；训练主数据优先来自后端，chatHistory 仍只保留在本地。 */}
        {activeTab.id === 'coach' ? null : renderMainTab(activeTab.id)}
        {hasVisitedCoachTab ? (
          <div
            aria-hidden={activeTab.id !== 'coach'}
            className={activeTab.id === 'coach' ? '' : 'hidden'}
          >
            {renderCoachTab()}
          </div>
        ) : null}
      </AppShell>
    </div>
  )
}

export default App
