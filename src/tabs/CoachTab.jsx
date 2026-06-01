import { useEffect, useMemo, useRef, useState } from 'react'
import CoachLayout from '../components/coach/CoachLayout.jsx'
import ChatSidebar from '../components/coach/ChatSidebar.jsx'
import ChatTopbar from '../components/coach/ChatTopbar.jsx'
import Composer from '../components/coach/Composer.jsx'
import MessageList from '../components/coach/MessageList.jsx'
import { createBackendClient } from '../api/backendClient.js'
import { buildAdoptCardModel } from '../utils/adoptCard.js'
import {
  getSuggestionCommitKey,
  mergeMessageMeta,
} from '../utils/chatSuggestionState.js'
import { getCoachBlockReason } from '../utils/coachGuard.js'
import {
  buildBackgroundCoachTaskRecord,
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
  buildCoachHistoryView,
  getCoachEmptyQuestionView,
  getVisibleStreamText,
} from '../utils/coachView.js'

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

function getBackendSessionId(sessionId) {
  // 当前侧栏仍是本地历史生成的临时 id；只有后续接入真实会话列表后才把数字 sessionId 传给后端。
  return Number.isInteger(sessionId) ? sessionId : null
}

const BACKGROUND_TASK_STORAGE_KEY = 'fitloop:coach-background-task'
const FALLBACK_MODEL_CONFIG = {
  defaultModel: 'deepseek-v4-flash',
  models: [{ id: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash', supportsThinking: true }],
  thinking: { enabled: false, budget: 'auto', options: ['off', 'auto', 'max'] },
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
  const [backendSessionId, setBackendSessionId] = useState(null)
  const [draft, setDraft] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isBackgroundThinking, setIsBackgroundThinking] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [messageMeta, setMessageMeta] = useState(() => mergeMessageMeta(chatHistory))
  const [modelConfig, setModelConfig] = useState(FALLBACK_MODEL_CONFIG)
  const [selectedModel, setSelectedModel] = useState(FALLBACK_MODEL_CONFIG.defaultModel)
  const [thinking, setThinking] = useState({
    enabled: FALLBACK_MODEL_CONFIG.thinking.enabled,
    budget: FALLBACK_MODEL_CONFIG.thinking.budget,
  })
  const [streamingText, setStreamingText] = useState('')
  const activeRequestAbortRef = useRef(null)
  const backgroundFallbackTriggeredRef = useRef(false)
  const backgroundSubmitPromiseRef = useRef(null)
  const backgroundTaskStartedRef = useRef(false)
  const chatHistoryRef = useRef(chatHistory)
  const pendingRequestRef = useRef(null)
  const adoptingSuggestionKeysRef = useRef(new Set())

  const coachBlockReason = useMemo(() => getCoachBlockReason(profile), [profile])
  const emptyQuestions = useMemo(() => getCoachEmptyQuestionView(), [])
  const historyView = useMemo(
    () => buildCoachHistoryView(chatHistory, { activeSessionId }),
    [activeSessionId, chatHistory],
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
    setMessageMeta((currentMeta) => mergeMessageMeta(chatHistory, currentMeta))
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
        setModelConfig(config)
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
    let ignore = false
    const client = createBackendClient()

    client
      .getDefaultChatSession()
      .then(async (session) => {
        if (ignore || !Number.isInteger(session?.id)) {
          return
        }
        setBackendSessionId(session.id)
        const draftPayload = await client.getCoachDraft(session.id)
        if (ignore) {
          return
        }
        setDraft(draftPayload.content || '')
        if (draftPayload.model) {
          setSelectedModel(draftPayload.model)
        }
        if (draftPayload.thinking) {
          setThinking(draftPayload.thinking)
        }
      })
      .catch(() => {
        if (!ignore) {
          setBackendSessionId(null)
        }
      })

    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!Number.isInteger(backendSessionId)) {
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
      client.saveCoachDraft(backendSessionId, payload).catch(() => null)
    }, 500)

    function flushDraft() {
      client.saveCoachDraft(backendSessionId, payload).catch(() => null)
    }

    window.addEventListener('pagehide', flushDraft)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('pagehide', flushDraft)
    }
  }, [attachedFiles, backendSessionId, draft, selectedModel, thinking])

  useEffect(() => {
    let pollTimer = null

    function readStoredTask() {
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

    function clearStoredTask() {
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(BACKGROUND_TASK_STORAGE_KEY)
      }
    }

    function appendBackgroundReply(reply, storedTask) {
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

      setMessageMeta((currentMeta) => {
        const nextMeta = mergeMessageMeta(mergeResult.nextHistory, currentMeta)

        nextMeta[mergeResult.assistantIndex] = {
          ...nextMeta[mergeResult.assistantIndex],
          isDismissed: false,
          suggestion: mergeResult.suggestion,
        }

        return nextMeta
      })
      chatHistoryRef.current = mergeResult.nextHistory
      onChatHistoryChange(mergeResult.nextHistory)
    }

    async function pollStoredTask() {
      const storedTask = readStoredTask()

      if (!storedTask?.taskId) {
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
    window.addEventListener('blur', submitBackgroundTask)
    window.addEventListener('focus', pollStoredTask)

    return () => {
      submitBackgroundTask()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('pagehide', submitBackgroundTask)
      window.removeEventListener('blur', submitBackgroundTask)
      window.removeEventListener('focus', pollStoredTask)
      if (pollTimer) {
        window.clearTimeout(pollTimer)
      }
    }
  }, [onChatHistoryChange])

  useEffect(() => {
    if (!chatHistory.length) {
      setActiveSessionId(null)
      return
    }

    const nextActiveItem = getActiveHistoryItem(historyView, activeSessionId)
    if (nextActiveItem && nextActiveItem.id !== activeSessionId) {
      setActiveSessionId(nextActiveItem.id)
    }
  }, [activeSessionId, chatHistory.length, historyView])

  async function requestReplyWithFallback(payload, { signal } = {}) {
    let hasReceivedStreamText = false

    try {
      return await requestCoachReplyStream(payload, {
        onText: (fullText) => {
          hasReceivedStreamText = true
          setStreamingText(getVisibleStreamText(fullText))
        },
        signal,
      })
    } catch (error) {
      setStreamingText('')
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

  function handleNewChat() {
    if (isSending) {
      return
    }

    setActiveSessionId(null)
    setAttachedFiles([])
    setDraft('')
    setErrorMessage('')
    setMessageMeta([])
    setStreamingText('')
    onChatHistoryChange([])
  }

  function handleSelectSession(sessionId) {
    setActiveSessionId(sessionId)
  }

  function handleSuggestionQuestion(question) {
    setDraft(question)
    setErrorMessage('')
  }

  function handleDismissSuggestion(targetSuggestion) {
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
      const adoptResult = targetSuggestion?.proposalId
        ? await client.commitPlanChange({ proposalId: targetSuggestion.proposalId })
        : await client.adoptWeeklyPlanChange({
            day: targetSuggestion?.day,
            changes: targetSuggestion?.changes,
          })

      if (!adoptResult.ok) {
        setErrorMessage(adoptResult.message)
        return
      }

      onWeeklyPlanChange(adoptResult.plan)
      setErrorMessage('')
      handleDismissSuggestion(targetSuggestion)
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

    const userMessage = { role: 'user', content: userInput }
    const nextHistory = appendChatMessages(chatHistory, [userMessage])
    const requestPayload = {
      chatHistory,
      dailyLog,
      files: attachedFiles,
      profile,
      sessionId: backendSessionId ?? getBackendSessionId(activeSessionId),
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
    setStreamingText('')
    setMessageMeta((currentMeta) => mergeMessageMeta(nextHistory, currentMeta))
    onChatHistoryChange(nextHistory)

    try {
      const reply = await requestReplyWithFallback(requestPayload, {
        signal: activeRequestAbortRef.current?.signal,
      })
      const assistantSuggestion = reply.proposal || reply.suggestion || null
      const assistantMessage = {
        content: reply.text,
        role: 'assistant',
        suggestion: assistantSuggestion,
      }
      const finalHistory = appendChatMessages(nextHistory, [assistantMessage])

      setMessageMeta((currentMeta) => {
        const baseMeta = mergeMessageMeta(nextHistory, currentMeta)
        const nextMeta = mergeMessageMeta(finalHistory, baseMeta)
        const assistantIndex = finalHistory.length - 1

        nextMeta[assistantIndex] = {
          ...nextMeta[assistantIndex],
          isDismissed: false,
          suggestion: assistantSuggestion,
        }

        return nextMeta
      })
      chatHistoryRef.current = finalHistory
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
        uploadedFiles.push(await client.uploadFile(file, { sessionId: backendSessionId }))
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
          isSending={isCoachThinking}
          isUploading={isUploading}
          modelOptions={modelConfig.models}
          onDraftChange={setDraft}
          onFilesSelected={handleFilesSelected}
          onModelChange={setSelectedModel}
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
          streamingText={streamingText}
        />
      }
      sidebar={
        <ChatSidebar
          activeSessionId={activeSessionId}
          groups={historyView.groups}
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
          title={activeHistoryItem?.isPlaceholder ? '新的对话' : activeHistoryItem?.title || '新的对话'}
        />
      }
    />
  )
}

export default CoachTab
