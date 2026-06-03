import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import CoachLayout from '../components/coach/CoachLayout.jsx'
import ChatSidebar from '../components/coach/ChatSidebar.jsx'
import ChatTopbar from '../components/coach/ChatTopbar.jsx'
import Composer from '../components/coach/Composer.jsx'
import MessageList from '../components/coach/MessageList.jsx'
import ModelConfigDialog from '../components/coach/ModelConfigDialog.jsx'
import { createBackendClient } from '../api/backendClient.js'
import { buildAdoptCardModel } from '../utils/adoptCard.js'
import {
  getSuggestionCommitKey,
  mergeMessageMeta,
  persistDismissedSuggestionKey,
  readDismissedSuggestionKeys,
} from '../utils/chatSuggestionState.js'
import { mergeCommittedWeeklyPlan } from '../utils/weeklyPlanCommit.js'
import { getCoachBlockReason } from '../utils/coachGuard.js'
import {
  buildBackgroundCoachTaskRecord,
  mergeCoachReplySuggestion,
  requestCoachReply,
  requestCoachReplyStream,
  shouldFallbackCoachStream,
  shouldShowBackgroundCoachPendingIndicator,
  getBackgroundCoachTask,
  mergeBackgroundCoachReply,
  startBackgroundCoachReply,
} from '../utils/coachChat.js'
import { appendChatMessages } from '../utils/chatHistory.js'
import {
  buildSessionTitleFromPrompt,
  buildCoachSessionView,
  getCoachEmptyQuestionView,
  getVisibleStreamText,
} from '../utils/coachView.js'
import { buildModelRuntimeView, buildProviderConfigView } from '../utils/modelConfigView.js'

function getActiveHistoryItem(historyView, activeSessionId) {
  const items = historyView.groups.flatMap((group) => group.items)

  return (
    items.find((item) => item.id === activeSessionId) ||
    items.find((item) => item.isActive) ||
    items[0] ||
    null
  )
}

function buildConversationExportText(messages = []) {
  return messages
    .map((message) => `${message.role === 'user' ? '我' : 'RepMind'}：${message.content}`)
    .join('\n\n')
}

function buildMessageAttachmentSnapshots(files = []) {
  return files.map((file) => ({
    fileId: Number.isInteger(file?.id) ? file.id : null,
    originalName: file?.originalName || file?.name || '',
    mimeType: file?.mimeType || '',
    extension: file?.extension || '',
    sizeBytes: Number.isFinite(file?.sizeBytes) ? file.sizeBytes : null,
  }))
}

function syncSessionActivity(currentSessions = [], sessionId, userInput) {
  if (!Number.isInteger(sessionId)) {
    return currentSessions
  }

  const activeSession = currentSessions.find((session) => session?.id === sessionId)
  if (!activeSession) {
    return currentSessions
  }

  const nextTitle =
    activeSession.title === '新对话' ? buildSessionTitleFromPrompt(userInput) : activeSession.title
  const nextSession = {
    ...activeSession,
    title: nextTitle,
    updatedAt: new Date().toISOString(),
  }

  return [nextSession, ...currentSessions.filter((session) => session?.id !== sessionId)]
}

function normalizeChatMessages(messages = []) {
  if (!Array.isArray(messages)) {
    return []
  }

  return messages.map((message) => ({
    role: message?.role || 'assistant',
    content: typeof message?.content === 'string' ? message.content : '',
    suggestion: message?.suggestion ?? null,
    attachments: Array.isArray(message?.attachments) ? message.attachments : [],
  }))
}

function readStoredActiveSessionId() {
  if (typeof window === 'undefined') {
    return null
  }

  const rawValue = window.localStorage.getItem(ACTIVE_COACH_SESSION_STORAGE_KEY)
  const parsedValue = Number.parseInt(rawValue || '', 10)
  return Number.isInteger(parsedValue) ? parsedValue : null
}

function persistActiveSessionId(sessionId) {
  if (typeof window === 'undefined') {
    return
  }

  if (Number.isInteger(sessionId)) {
    window.localStorage.setItem(ACTIVE_COACH_SESSION_STORAGE_KEY, String(sessionId))
    return
  }

  window.localStorage.removeItem(ACTIVE_COACH_SESSION_STORAGE_KEY)
}

function readStoredBackgroundTask() {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    return JSON.parse(window.localStorage.getItem(BACKGROUND_TASK_STORAGE_KEY) || 'null')
  } catch {
    window.localStorage.removeItem(BACKGROUND_TASK_STORAGE_KEY)
    return null
  }
}

function hydratePendingBackgroundUser(messages = [], sessionId) {
  const storedTask = readStoredBackgroundTask()
  const userContent = typeof storedTask?.userContent === 'string' ? storedTask.userContent.trim() : ''

  if (!storedTask?.taskId || !userContent) {
    return messages
  }

  if (Number.isInteger(storedTask.sessionId) && storedTask.sessionId !== sessionId) {
    return messages
  }

  const hasSourceUser = messages.some(
    (message) => message.role === 'user' && message.content === userContent,
  )

  if (hasSourceUser) {
    return messages
  }

  // 后台任务可能尚未把本轮 user 消息落库，先用本地 task 记录恢复等待态锚点。
  return [...messages, { role: 'user', content: userContent, suggestion: null, attachments: [] }]
}

function hasPendingBackgroundTaskForSession(messages = [], sessionId) {
  const storedTask = readStoredBackgroundTask()
  const userContent = typeof storedTask?.userContent === 'string' ? storedTask.userContent.trim() : ''

  if (!storedTask?.taskId || !userContent) {
    return false
  }

  if (Number.isInteger(storedTask.sessionId) && storedTask.sessionId !== sessionId) {
    return false
  }

  return messages.some((message) => message.role === 'user' && message.content === userContent)
}

const BACKGROUND_TASK_STORAGE_KEY = 'fitloop:coach-background-task'
const ACTIVE_COACH_SESSION_STORAGE_KEY = 'fitloop:coach-active-session-id'
const FALLBACK_MODEL_CONFIG = buildModelRuntimeView({
  defaultModelRef: 'provider_deepseek_default::deepseek-v4-flash',
  models: [
    {
      id: 'provider_deepseek_default::deepseek-v4-flash',
      label: 'DeepSeek 默认账号 / DeepSeek V4 Flash',
      providerId: 'provider_deepseek_default',
      providerType: 'openai_compatible',
      providerLabel: 'DeepSeek 默认账号',
      remoteModelId: 'deepseek-v4-flash',
      supportsThinking: true,
      thinking: {
        supported: true,
        canDisable: true,
        defaultEnabled: false,
        intensityOptions: [
          { id: 'standard', label: '标准' },
          { id: 'deep', label: '深入' },
        ],
        defaultIntensity: 'standard',
      },
    },
  ],
  thinking: { enabled: false, budget: 'auto', options: ['off', 'auto', 'max'] },
})

function resolveThinkingState(models = [], selectedModel, thinking) {
  const activeModel = models.find((model) => model.id === selectedModel) || models[0] || null
  const capability = activeModel?.thinking

  if (!capability?.supported) {
    return { enabled: false, budget: 'auto' }
  }

  const nextBudget = thinking?.budget || capability.defaultIntensity || 'standard'
  const nextEnabled = capability.canDisable === false
    ? true
    : typeof thinking?.enabled === 'boolean'
      ? thinking.enabled
      : Boolean(capability.defaultEnabled)

  return {
    enabled: nextEnabled,
    budget: nextBudget,
  }
}

function CoachTab({
  chatHistory,
  dailyLog,
  onChatHistoryChange,
  onWeeklyPlanChange,
  profile,
  weeklyPlan,
}) {
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [attachedFiles, setAttachedFiles] = useState([])
  const [draft, setDraft] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isBackgroundThinking, setIsBackgroundThinking] = useState(false)
  const [isModelConfigOpen, setIsModelConfigOpen] = useState(false)
  const [isModelConfigSaving, setIsModelConfigSaving] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [messageMeta, setMessageMeta] = useState(() => mergeMessageMeta(chatHistory))
  const [modelConfig, setModelConfig] = useState(FALLBACK_MODEL_CONFIG)
  const [modelConfigDraft, setModelConfigDraft] = useState(() =>
    buildProviderConfigView({ version: 1, defaultModelRef: FALLBACK_MODEL_CONFIG.defaultModelRef, providers: [] }),
  )
  const [modelConfigError, setModelConfigError] = useState('')
  const [sessions, setSessions] = useState([])
  const [selectedModel, setSelectedModel] = useState(FALLBACK_MODEL_CONFIG.defaultModel)
  const [thinking, setThinking] = useState({
    enabled: FALLBACK_MODEL_CONFIG.thinking.enabled,
    budget: FALLBACK_MODEL_CONFIG.thinking.budget,
  })
  const [streamStatusLabel, setStreamStatusLabel] = useState('')
  const [streamingSuggestion, setStreamingSuggestion] = useState(null)
  const [streamingText, setStreamingText] = useState('')
  const activeRequestAbortRef = useRef(null)
  const backgroundFallbackTriggeredRef = useRef(false)
  const backgroundSubmitPromiseRef = useRef(null)
  const backgroundTaskStartedRef = useRef(false)
  const chatHistoryRef = useRef(chatHistory)
  const activeSessionIdRef = useRef(activeSessionId)
  const pendingRequestRef = useRef(null)
  const adoptingSuggestionKeysRef = useRef(new Set())
  const sessionLoadTokenRef = useRef(0)
  const draftHydratedRef = useRef(false)

  const coachBlockReason = useMemo(() => getCoachBlockReason(profile), [profile])
  const emptyQuestions = useMemo(() => getCoachEmptyQuestionView(), [])
  const historyView = useMemo(
    () => buildCoachSessionView(sessions, { activeSessionId }),
    [activeSessionId, sessions],
  )
  const activeHistoryItem = useMemo(
    () => getActiveHistoryItem(historyView, activeSessionId),
    [activeSessionId, historyView],
  )
  const messageList = useMemo(
    () =>
      chatHistory.map((message, index) => {
        const meta = messageMeta[index]
        const suggestion = meta?.isDismissed ? null : meta?.suggestion || message?.suggestion || null

        return {
          ...message,
          onCopy:
            message.role === 'assistant'
              ? () => {
                  if (!navigator?.clipboard?.writeText) {
                    setErrorMessage('当前环境不支持一键复制，请手动复制消息内容。')
                    return
                  }

                  navigator.clipboard
                    .writeText(message.content)
                    .then(() => {
                      setErrorMessage('')
                    })
                    .catch(() => {
                      setErrorMessage('复制失败，请手动复制消息内容。')
                    })
                }
              : undefined,
          onRetry:
            message.role === 'assistant'
              ? () => {
                  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
                    if (chatHistory[cursor]?.role === 'user') {
                      setDraft(chatHistory[cursor].content || '')
                      setErrorMessage('')
                      break
                    }
                  }
                }
              : undefined,
          suggestion,
          suggestionCard: buildAdoptCardModel(suggestion),
        }
      }),
    [chatHistory, messageMeta],
  )

  useEffect(() => {
    setMessageMeta((currentMeta) =>
      mergeMessageMeta(chatHistory, currentMeta, {
        hiddenCommitKeys: new Set(readDismissedSuggestionKeys(activeSessionIdRef.current)),
      }),
    )
    chatHistoryRef.current = chatHistory
  }, [chatHistory])

  useEffect(() => {
    let ignore = false
    const client = createBackendClient()

    client
      .getModels()
      .then((config) => {
        if (ignore) {
          return
        }
        // 当前选择由 draft 接口统一恢复；模型列表只更新可选项，避免慢回包覆盖用户草稿。
        setModelConfig(buildModelRuntimeView(config))
      })
      .catch(() => {
        if (!ignore) {
          setModelConfig(FALLBACK_MODEL_CONFIG)
        }
      })

    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!modelConfig.models.some((model) => model.id === selectedModel)) {
      const nextSelectedModel = modelConfig.defaultModelRef || modelConfig.defaultModel || ''
      setSelectedModel(nextSelectedModel)
      setThinking((current) => resolveThinkingState(modelConfig.models, nextSelectedModel, current))
      return
    }

    setThinking((current) => resolveThinkingState(modelConfig.models, selectedModel, current))
  }, [modelConfig, selectedModel])

  const loadSessionContent = useCallback(
    async (sessionId) => {
      if (!Number.isInteger(sessionId)) {
        return null
      }

      const requestToken = sessionLoadTokenRef.current + 1
      sessionLoadTokenRef.current = requestToken
      draftHydratedRef.current = false

      const client = createBackendClient()
      const [messages, draftPayload] = await Promise.all([
        client.getChatMessages(sessionId),
        client.getCoachDraft(sessionId),
      ])

      if (sessionLoadTokenRef.current !== requestToken) {
        return sessionId
      }

      const nextHistory = hydratePendingBackgroundUser(normalizeChatMessages(messages), sessionId)
      const attachedFileIds = Array.isArray(draftPayload?.attachedFileIds)
        ? draftPayload.attachedFileIds.filter(Number.isInteger)
        : []
      const attachedFilesResult = await Promise.all(
        attachedFileIds.map(async (fileId) => {
          try {
            const response = await client.getFile(fileId)
            return response?.file ?? response ?? null
          } catch {
            return null
          }
        }),
      )

      if (sessionLoadTokenRef.current !== requestToken) {
        return sessionId
      }

      chatHistoryRef.current = nextHistory
      setMessageMeta(
        mergeMessageMeta(nextHistory, [], {
          hiddenCommitKeys: new Set(readDismissedSuggestionKeys(sessionId)),
        }),
      )
      onChatHistoryChange(nextHistory)
      setIsBackgroundThinking(hasPendingBackgroundTaskForSession(nextHistory, sessionId))
      setDraft(draftPayload?.content || '')
      const nextSelectedModel = draftPayload?.model || modelConfig.defaultModelRef || modelConfig.defaultModel
      setSelectedModel(nextSelectedModel)
      setThinking(resolveThinkingState(modelConfig.models, nextSelectedModel, draftPayload?.thinking))
      setAttachedFiles(attachedFilesResult.filter(Boolean))
      draftHydratedRef.current = true
      return sessionId
    },
    [modelConfig, onChatHistoryChange],
  )

  const refreshSessions = useCallback(
    async ({ ensureDefault = false, preferredSessionId = null } = {}) => {
      const client = createBackendClient()
      let nextSessions = await client.getChatSessions()

      if ((!Array.isArray(nextSessions) || !nextSessions.length) && ensureDefault) {
        nextSessions = [await client.getDefaultChatSession()]
      }

      const normalizedSessions = Array.isArray(nextSessions) ? nextSessions : []
      setSessions(normalizedSessions)

      const storedActiveId = preferredSessionId ?? readStoredActiveSessionId()
      const nextActiveSession =
        normalizedSessions.find((session) => session.id === storedActiveId) ||
        normalizedSessions.find((session) => session.id === activeSessionIdRef.current) ||
        normalizedSessions[0] ||
        null

      if (!nextActiveSession) {
        setActiveSessionId(null)
        draftHydratedRef.current = false
        return null
      }

      setActiveSessionId(nextActiveSession.id)
      await loadSessionContent(nextActiveSession.id)
      return nextActiveSession.id
    },
    [loadSessionContent],
  )

  useEffect(() => {
    refreshSessions({ ensureDefault: true }).catch(() => null)
  }, [refreshSessions])

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
    persistActiveSessionId(activeSessionId)
  }, [activeSessionId])

  useEffect(() => {
    if (!Number.isInteger(activeSessionId) || !draftHydratedRef.current) {
      return undefined
    }

    const client = createBackendClient()
    const payload = {
      content: draft,
      model: selectedModel,
      thinking,
      attachedFileIds: attachedFiles.map((file) => file.id).filter(Number.isInteger),
    }
    const timer = window.setTimeout(() => {
      client.saveCoachDraft(activeSessionId, payload).catch(() => null)
    }, 500)

    function flushDraft() {
      client.saveCoachDraft(activeSessionId, payload).catch(() => null)
    }

    window.addEventListener('pagehide', flushDraft)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('pagehide', flushDraft)
    }
  }, [activeSessionId, attachedFiles, draft, selectedModel, thinking])

  useEffect(() => {
    let pollTimer = null

    function clearStoredTask() {
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(BACKGROUND_TASK_STORAGE_KEY)
      }
    }

    function appendBackgroundReply(reply, storedTask) {
      if (
        Number.isInteger(storedTask?.sessionId) &&
        storedTask.sessionId !== activeSessionIdRef.current
      ) {
        return
      }

      const mergeResult = mergeBackgroundCoachReply({
        currentHistory: chatHistoryRef.current,
        reply,
        storedTask,
      })

      if (mergeResult.status === 'source_user_missing') {
        setErrorMessage('后台回复已完成，但当前对话已变化。请回到原问题后重新发送。')
        return
      }

      if (mergeResult.status !== 'merged') {
        return
      }

      const nextHistory = mergeResult.nextHistory.map((message) => ({
        ...message,
        attachments: Array.isArray(message?.attachments) ? message.attachments : [],
      }))

      setMessageMeta((currentMeta) => {
        const nextMeta = mergeMessageMeta(nextHistory, currentMeta, {
          hiddenCommitKeys: new Set(readDismissedSuggestionKeys(activeSessionIdRef.current)),
        })

        nextMeta[mergeResult.assistantIndex] = {
          ...nextMeta[mergeResult.assistantIndex],
          isDismissed: false,
          suggestion: mergeResult.suggestion,
        }

        return nextMeta
      })
      chatHistoryRef.current = nextHistory
      onChatHistoryChange(nextHistory)
    }

    async function pollStoredTask() {
      const storedTask = readStoredBackgroundTask()

      if (!storedTask?.taskId) {
        setIsBackgroundThinking(false)
        return
      }

      if (
        Number.isInteger(storedTask.sessionId) &&
        storedTask.sessionId !== activeSessionIdRef.current
      ) {
        setIsBackgroundThinking(false)
        return
      }

      try {
        const task = await getBackgroundCoachTask(storedTask.taskId)

        if (task.status === 'succeeded') {
          setIsBackgroundThinking(false)
          appendBackgroundReply(task.result, storedTask)
          clearStoredTask()
          return
        }

        if (task.status === 'failed' || task.status === 'not_found') {
          setIsBackgroundThinking(false)
          setErrorMessage(task.message || '后台 AI 教练任务未完成，请重新发送。')
          clearStoredTask()
        }

        if (task.status === 'pending' || task.status === 'running') {
          setIsBackgroundThinking(
            shouldShowBackgroundCoachPendingIndicator({
              currentHistory: chatHistoryRef.current,
              storedTask,
              taskStatus: task.status,
            }),
          )
          pollTimer = window.setTimeout(pollStoredTask, 1500)
        }
      } catch (error) {
        setIsBackgroundThinking(false)
        setErrorMessage(error?.message || '后台 AI 教练任务查询失败，请稍后重试。')
      }
    }

    async function submitBackgroundTask() {
      const payload = pendingRequestRef.current

      if (!payload || backgroundTaskStartedRef.current) {
        return
      }

      backgroundTaskStartedRef.current = true
      activeRequestAbortRef.current?.abort()
      setStreamingText('')

      backgroundSubmitPromiseRef.current = (async () => {
        const task = await startBackgroundCoachReply(payload)
        const taskRecord = buildBackgroundCoachTaskRecord({ ...task, files: payload.files }, {
          sourceUserIndex: payload.sourceUserIndex,
          userInput: payload.userInput,
        })

        if (!taskRecord) {
          throw new Error('后台思考任务提交失败，请重新发送。')
        }

        if (taskRecord && typeof window !== 'undefined') {
          backgroundFallbackTriggeredRef.current = true
          window.localStorage.setItem(BACKGROUND_TASK_STORAGE_KEY, JSON.stringify(taskRecord))
        }

        if (
          shouldShowBackgroundCoachPendingIndicator({
            currentHistory: chatHistoryRef.current,
            storedTask: taskRecord,
            taskStatus: 'pending',
          })
        ) {
          setIsBackgroundThinking(true)
        }

        return taskRecord
      })()

      try {
        await backgroundSubmitPromiseRef.current
      } catch (error) {
        backgroundTaskStartedRef.current = false
        setErrorMessage(error?.message || '后台思考任务提交失败，请重新发送。')
      }
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'hidden') {
        submitBackgroundTask()
        return
      }

      if (document.visibilityState === 'visible') {
        pollStoredTask()
      }
    }

    pollStoredTask()
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('pagehide', submitBackgroundTask)
    window.addEventListener('focus', pollStoredTask)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('pagehide', submitBackgroundTask)
      window.removeEventListener('focus', pollStoredTask)
      if (pollTimer) {
        window.clearTimeout(pollTimer)
      }
    }
  }, [onChatHistoryChange])

  async function requestReplyWithFallback(payload, { signal } = {}) {
    let hasReceivedStreamText = false

    try {
      return await requestCoachReplyStream(payload, {
        onProposal: (proposal) => {
          setStreamingSuggestion((currentSuggestion) =>
            mergeCoachReplySuggestion(currentSuggestion, proposal),
          )
        },
        onStatusLabel: (statusLabel) => {
          if (hasReceivedStreamText) {
            return
          }

          setStreamStatusLabel(statusLabel || '')
        },
        onSuggestion: (suggestion) => {
          setStreamingSuggestion((currentSuggestion) =>
            mergeCoachReplySuggestion(currentSuggestion, suggestion),
          )
        },
        onText: (fullText) => {
          const visibleText = getVisibleStreamText(fullText)

          hasReceivedStreamText = true
          setStreamingText(visibleText)
          if (visibleText.trim()) {
            setStreamStatusLabel('')
          }
        },
        signal,
      })
    } catch (error) {
      setStreamingText('')
      setStreamingSuggestion(null)
      setStreamStatusLabel('')
      if (
        !shouldFallbackCoachStream({
          hasReceivedText: hasReceivedStreamText,
          isBackgroundFallback: backgroundFallbackTriggeredRef.current,
        })
      ) {
        throw error
      }
      return requestCoachReply(payload, { signal })
    }
  }

  async function handleNewChat() {
    if (isSending) {
      return
    }

    setErrorMessage('')
    setAttachedFiles([])
    setDraft('')
    setMessageMeta([])
    setStreamStatusLabel('')
    setStreamingSuggestion(null)
    setStreamingText('')
    chatHistoryRef.current = []
    onChatHistoryChange([])

    try {
      const client = createBackendClient()
      const createdSession = await client.createChatSession({})
      if (!Number.isInteger(createdSession?.id)) {
        throw new Error('创建新对话失败，请稍后重试。')
      }

      await refreshSessions({ preferredSessionId: createdSession.id })
      persistActiveSessionId(createdSession.id)
    } catch (error) {
      setErrorMessage(error?.message || '创建新对话失败，请稍后重试。')
    }
  }

  function handleModelChange(nextModelId) {
    setSelectedModel(nextModelId)
    setThinking((current) => resolveThinkingState(modelConfig.models, nextModelId, current))
  }

  async function handleOpenModelConfig() {
    setModelConfigError('')
    setIsModelConfigOpen(true)

    try {
      const client = createBackendClient()
      const config = await client.getModelConfig()
      setModelConfigDraft(buildProviderConfigView(config))
    } catch (error) {
      setModelConfigError(error?.message || '读取模型配置失败，请稍后重试。')
    }
  }

  async function handleSaveModelConfig(nextConfig) {
    const client = createBackendClient()
    setIsModelConfigSaving(true)
    setModelConfigError('')

    try {
      const savedConfig = await client.saveModelConfig(nextConfig)
      const runtimeConfig = buildModelRuntimeView(await client.getModels())
      const nextSelectedModel = runtimeConfig.models.some((model) => model.id === selectedModel)
        ? selectedModel
        : runtimeConfig.defaultModelRef || runtimeConfig.defaultModel

      setModelConfigDraft(buildProviderConfigView(savedConfig))
      setModelConfig(runtimeConfig)
      setSelectedModel(nextSelectedModel)
      setThinking((current) => resolveThinkingState(runtimeConfig.models, nextSelectedModel, current))
      setIsModelConfigOpen(false)
      setErrorMessage('')
    } catch (error) {
      setModelConfigError(error?.message || '保存模型配置失败，请稍后重试。')
    } finally {
      setIsModelConfigSaving(false)
    }
  }

  async function handleTestProviderConnection(providerConfig) {
    const client = createBackendClient()
    return client.testProviderConnection(providerConfig)
  }

  async function handleDiscoverProviderModels(providerConfig) {
    const client = createBackendClient()
    return client.discoverProviderModels(providerConfig)
  }

  async function handleSelectSession(sessionId) {
    if (isSending || !Number.isInteger(sessionId)) {
      return
    }

    setErrorMessage('')
    setStreamStatusLabel('')
    setStreamingSuggestion(null)
    setStreamingText('')
    setIsBackgroundThinking(false)
    setActiveSessionId(sessionId)
    await loadSessionContent(sessionId)
  }

  async function handleDeleteSession(sessionId) {
    if (isSending || !Number.isInteger(sessionId)) {
      return
    }

    if (typeof window !== 'undefined' && !window.confirm('删除这个对话后将无法恢复，确认删除吗？')) {
      return
    }

    const wasActive = sessionId === activeSessionIdRef.current
    const fallbackSession = sessions.find((session) => session.id !== sessionId) || null

    setErrorMessage('')
    try {
      const client = createBackendClient()
      await client.deleteChatSession(sessionId)

      if (wasActive) {
        setDraft('')
        setAttachedFiles([])
        setMessageMeta([])
        setStreamStatusLabel('')
        setStreamingSuggestion(null)
        setStreamingText('')
        chatHistoryRef.current = []
        onChatHistoryChange([])
      }

      await refreshSessions({
        ensureDefault: wasActive && !fallbackSession,
        preferredSessionId: wasActive ? fallbackSession?.id ?? null : activeSessionIdRef.current,
      })
    } catch (error) {
      setErrorMessage(error?.message || '删除对话失败，请稍后重试。')
    }
  }

  function handleSuggestionQuestion(question) {
    setDraft(question)
    setErrorMessage('')
  }

  async function handleDismissSuggestion(targetSuggestion) {
    const commitKey = getSuggestionCommitKey(targetSuggestion)

    if (targetSuggestion?.proposalId) {
      try {
        const client = createBackendClient()
        const ignoreResult = await client.ignorePlanChange({ proposalId: targetSuggestion.proposalId })
        if (!ignoreResult?.ok) {
          setErrorMessage(ignoreResult?.message || '忽略建议失败，请稍后重试。')
          return
        }
      } catch (error) {
        setErrorMessage(error?.message || '忽略建议失败，请确认本地后端服务已启动。')
        return
      }
    }

    persistHideSuggestion(targetSuggestion)
    setMessageMeta((currentMeta) =>
      currentMeta.map((entry) =>
        getSuggestionCommitKey(entry?.suggestion) === commitKey
          ? { ...entry, isDismissed: true, suggestion: null }
          : entry,
      ),
    )
  }

  function hideSuggestionLocally(targetSuggestion) {
    const commitKey = getSuggestionCommitKey(targetSuggestion)

    persistHideSuggestion(targetSuggestion)
    setMessageMeta((currentMeta) =>
      currentMeta.map((entry) =>
        getSuggestionCommitKey(entry?.suggestion) === commitKey
          ? { ...entry, isDismissed: true, suggestion: null }
          : entry,
      ),
    )
  }

  function persistHideSuggestion(targetSuggestion) {
    const commitKey = getSuggestionCommitKey(targetSuggestion)

    if (!commitKey) {
      return
    }

    persistDismissedSuggestionKey(activeSessionIdRef.current, targetSuggestion)
    const nextHistory = chatHistoryRef.current.map((message) =>
      getSuggestionCommitKey(message?.suggestion) === commitKey
        ? { ...message, suggestion: null }
        : message,
    )

    chatHistoryRef.current = nextHistory
    onChatHistoryChange(nextHistory)
  }

  async function handleAdoptSuggestion(targetSuggestion) {
    const commitKey = getSuggestionCommitKey(targetSuggestion)

    if (!commitKey) {
      return
    }

    if (adoptingSuggestionKeysRef.current.has(commitKey)) {
      return
    }

    adoptingSuggestionKeysRef.current.add(commitKey)

    try {
      const client = createBackendClient()
      const adoptResult = await client.commitCoachSuggestion(targetSuggestion)

      if (!adoptResult.ok) {
        setErrorMessage(adoptResult.message)
        return
      }

      onWeeklyPlanChange((currentPlan) => mergeCommittedWeeklyPlan(currentPlan, adoptResult.plan))
      setErrorMessage('')
      hideSuggestionLocally(targetSuggestion)
    } catch (error) {
      setErrorMessage(error?.message || '采纳建议失败，请确认本地后端服务已启动。')
    } finally {
      adoptingSuggestionKeysRef.current.delete(commitKey)
    }
  }

  function handleExportConversation() {
    if (!chatHistory.length || typeof window === 'undefined') {
      return
    }

    const exportText = buildConversationExportText(chatHistory)
    const exportBlob = new Blob([exportText], { type: 'text/plain;charset=utf-8' })
    const objectUrl = window.URL.createObjectURL(exportBlob)
    const anchor = document.createElement('a')

    anchor.href = objectUrl
    anchor.download = 'fitloop-coach-chat.txt'
    anchor.click()
    window.URL.revokeObjectURL(objectUrl)
  }

  async function handleSubmit(event) {
    event.preventDefault()

    const userInput = draft.trim()
    const draftBeforeSend = draft
    if (!userInput || isSending) {
      return
    }

    if (coachBlockReason) {
      setErrorMessage(coachBlockReason)
      return
    }

    const messageAttachments = buildMessageAttachmentSnapshots(attachedFiles)
    const userMessage = { role: 'user', content: userInput, attachments: messageAttachments }
    const nextHistory = appendChatMessages(chatHistory, [userMessage])
    const requestPayload = {
      chatHistory,
      dailyLog,
      files: attachedFiles,
      fileIds: attachedFiles.map((file) => file.id).filter(Number.isInteger),
      profile,
      sessionId: Number.isInteger(activeSessionId) ? activeSessionId : null,
      sourceUserIndex: nextHistory.length - 1,
      model: selectedModel,
      thinking,
      userInput,
      weeklyPlan,
    }

    setErrorMessage('')
    setIsSending(true)
    activeRequestAbortRef.current =
      typeof AbortController === 'function' ? new AbortController() : null
    backgroundFallbackTriggeredRef.current = false
    backgroundTaskStartedRef.current = false
    pendingRequestRef.current = requestPayload
    setStreamStatusLabel('')
    setStreamingSuggestion(null)
    setStreamingText('')
    setMessageMeta((currentMeta) =>
      mergeMessageMeta(nextHistory, currentMeta, {
        hiddenCommitKeys: new Set(readDismissedSuggestionKeys(activeSessionIdRef.current)),
      }),
    )
    onChatHistoryChange(nextHistory)

    try {
      const reply = await requestReplyWithFallback(requestPayload, {
        signal: activeRequestAbortRef.current?.signal,
      })
      const assistantSuggestion = reply.suggestion || reply.proposal || null
      const assistantMessage = {
        content: reply.text,
        role: 'assistant',
        suggestion: assistantSuggestion,
        attachments: [],
      }
      const finalHistory = appendChatMessages(nextHistory, [assistantMessage])

      setMessageMeta((currentMeta) => {
        const baseMeta = mergeMessageMeta(nextHistory, currentMeta, {
          hiddenCommitKeys: new Set(readDismissedSuggestionKeys(activeSessionIdRef.current)),
        })
        const nextMeta = mergeMessageMeta(finalHistory, baseMeta, {
          hiddenCommitKeys: new Set(readDismissedSuggestionKeys(activeSessionIdRef.current)),
        })
        const assistantIndex = finalHistory.length - 1

        nextMeta[assistantIndex] = {
          ...nextMeta[assistantIndex],
          isDismissed: false,
          suggestion: assistantSuggestion,
        }

        return nextMeta
      })
      chatHistoryRef.current = finalHistory
      setSessions((currentSessions) =>
        syncSessionActivity(currentSessions, activeSessionIdRef.current, userInput),
      )
      onChatHistoryChange(finalHistory)
      setDraft('')
      setAttachedFiles([])
    } catch (error) {
      if (backgroundSubmitPromiseRef.current) {
        await backgroundSubmitPromiseRef.current.catch(() => null)
      }

      if (backgroundFallbackTriggeredRef.current) {
        return
      }
      setDraft(draftBeforeSend)
      setErrorMessage(error?.message || 'AI 教练暂时不可用，请稍后重试。')
    } finally {
      setIsSending(false)
      activeRequestAbortRef.current = null
      backgroundSubmitPromiseRef.current = null
      pendingRequestRef.current = null
      setStreamStatusLabel('')
      setStreamingSuggestion(null)
      setStreamingText('')
    }
  }

  async function handleFilesSelected(files) {
    if (!files.length) {
      return
    }

    const client = createBackendClient()
    setIsUploading(true)
    setErrorMessage('')
    try {
      const uploadedFiles = []
      for (const file of files) {
        uploadedFiles.push(
          await client.uploadFile(file, {
            sessionId: Number.isInteger(activeSessionId) ? activeSessionId : null,
          }),
        )
      }
      setAttachedFiles((current) => [...current, ...uploadedFiles])
    } catch (error) {
      setErrorMessage(error?.message || '文件上传失败，请稍后重试。')
    } finally {
      setIsUploading(false)
    }
  }

  const isCoachThinking = isSending || isBackgroundThinking

  return (
    <CoachLayout
      composer={
        <Composer
          attachedFiles={attachedFiles}
          draft={draft}
          errorMessage={errorMessage}
          isSending={isSending}
          isUploading={isUploading}
          modelOptions={modelConfig.models}
          onDraftChange={setDraft}
          onFilesSelected={handleFilesSelected}
          onModelChange={handleModelChange}
          onRemoveFile={(fileId) =>
            setAttachedFiles((current) => current.filter((file) => file.id !== fileId))
          }
          onSubmit={handleSubmit}
          onThinkingChange={setThinking}
          selectedModel={selectedModel}
          thinking={thinking}
        />
      }
      messages={
        <MessageList
          emptyQuestions={emptyQuestions}
          isSending={isCoachThinking}
          messages={messageList}
          onAdopt={handleAdoptSuggestion}
          onDismissSuggestion={handleDismissSuggestion}
          onSuggestionClick={handleSuggestionQuestion}
          autoScrollKey={`${messageList.length}:${isCoachThinking ? 'sending' : 'idle'}`}
          streamStatusLabel={streamStatusLabel}
          streamingSuggestion={streamingSuggestion}
          streamingText={streamingText}
        />
      }
      sidebar={
        <ChatSidebar
          activeSessionId={activeSessionId}
          groups={historyView.groups}
          onDeleteSession={handleDeleteSession}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
        />
      }
      topbar={
        <ChatTopbar
          modelLabel={
            modelConfig.models.find((model) => model.id === selectedModel)?.label || selectedModel || 'DeepSeek'
          }
          onClear={handleNewChat}
          onExport={handleExportConversation}
          onOpenModelConfig={handleOpenModelConfig}
          title={activeHistoryItem?.isPlaceholder ? '新的对话' : activeHistoryItem?.title || '新的对话'}
        />
      }
    >
      <ModelConfigDialog
        errorMessage={modelConfigError}
        onClose={() => setIsModelConfigOpen(false)}
        onDiscoverProviderModels={handleDiscoverProviderModels}
        onSave={handleSaveModelConfig}
        onTestProviderConnection={handleTestProviderConnection}
        open={isModelConfigOpen}
        saving={isModelConfigSaving}
        value={modelConfigDraft}
      />
    </CoachLayout>
  )
}

export default CoachTab
