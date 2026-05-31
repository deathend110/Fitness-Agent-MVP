import { useEffect, useMemo, useRef, useState } from 'react'
import CoachLayout from '../components/coach/CoachLayout.jsx'
import ChatSidebar from '../components/coach/ChatSidebar.jsx'
import ChatTopbar from '../components/coach/ChatTopbar.jsx'
import Composer from '../components/coach/Composer.jsx'
import MessageList from '../components/coach/MessageList.jsx'
import { createBackendClient } from '../api/backendClient.js'
import { buildAdoptCardModel } from '../utils/adoptCard.js'
import { getCoachBlockReason } from '../utils/coachGuard.js'
import {
  buildBackgroundCoachTaskRecord,
  requestCoachReply,
  requestCoachReplyStream,
  shouldFallbackCoachStream,
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

function buildMessageStableKeys(messages = []) {
  const sameMessageCounts = new Map()

  return messages.map((message) => {
    const baseKey = `${message?.role || 'unknown'}::${message?.content || ''}`
    const occurrence = sameMessageCounts.get(baseKey) || 0

    sameMessageCounts.set(baseKey, occurrence + 1)
    return `${baseKey}::${occurrence}`
  })
}

function mergeMessageMeta(messages = [], currentMeta = []) {
  const currentBuckets = currentMeta.reduce((buckets, entry) => {
    if (!entry?.messageKey) {
      return buckets
    }

    const bucket = buckets.get(entry.messageKey) || []
    bucket.push(entry)
    buckets.set(entry.messageKey, bucket)
    return buckets
  }, new Map())

  return buildMessageStableKeys(messages).map((messageKey) => {
    const bucket = currentBuckets.get(messageKey)

    if (bucket?.length) {
      return bucket.shift()
    }

    return {
      isDismissed: false,
      messageKey,
      suggestion: null,
    }
  })
}

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

function CoachTab({
  chatHistory,
  dailyLog,
  onChatHistoryChange,
  onWeeklyPlanChange,
  profile,
  weeklyPlan,
}) {
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [draft, setDraft] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [messageMeta, setMessageMeta] = useState(() => mergeMessageMeta(chatHistory))
  const [streamingText, setStreamingText] = useState('')
  const activeRequestAbortRef = useRef(null)
  const backgroundFallbackTriggeredRef = useRef(false)
  const backgroundSubmitPromiseRef = useRef(null)
  const backgroundTaskStartedRef = useRef(false)
  const chatHistoryRef = useRef(chatHistory)
  const pendingRequestRef = useRef(null)

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
        const suggestion = meta?.isDismissed ? null : meta?.suggestion || null

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
      onChatHistoryChange(mergeResult.nextHistory)
    }

    async function pollStoredTask() {
      const storedTask = readStoredTask()

      if (!storedTask?.taskId) {
        return
      }

      try {
        const task = await getBackgroundCoachTask(storedTask.taskId)

        if (task.status === 'succeeded') {
          appendBackgroundReply(task.result, storedTask)
          clearStoredTask()
          return
        }

        if (task.status === 'failed' || task.status === 'not_found') {
          setErrorMessage(task.message || '后台 AI 教练任务未完成，请重新发送。')
          clearStoredTask()
        }

        if (task.status === 'pending' || task.status === 'running') {
          pollTimer = window.setTimeout(pollStoredTask, 1500)
        }
      } catch (error) {
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
        const taskRecord = buildBackgroundCoachTaskRecord(task, {
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

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('pagehide', submitBackgroundTask)
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
    setMessageMeta((currentMeta) =>
      currentMeta.map((entry) =>
        entry?.suggestion === targetSuggestion ? { ...entry, isDismissed: true } : entry,
      ),
    )
  }

  async function handleAdoptSuggestion(targetSuggestion) {
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
      profile,
      sessionId: getBackendSessionId(activeSessionId),
      sourceUserIndex: nextHistory.length - 1,
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
    setDraft('')
    setMessageMeta((currentMeta) => mergeMessageMeta(nextHistory, currentMeta))
    onChatHistoryChange(nextHistory)

    try {
      const reply = await requestReplyWithFallback(requestPayload, {
        signal: activeRequestAbortRef.current?.signal,
      })
      const assistantMessage = {
        content: reply.text,
        role: 'assistant',
      }
      const finalHistory = appendChatMessages(nextHistory, [assistantMessage])

      setMessageMeta((currentMeta) => {
        const baseMeta = mergeMessageMeta(nextHistory, currentMeta)
        const nextMeta = mergeMessageMeta(finalHistory, baseMeta)
        const assistantIndex = finalHistory.length - 1

        nextMeta[assistantIndex] = {
          ...nextMeta[assistantIndex],
          isDismissed: false,
          suggestion: reply.proposal || reply.suggestion,
        }

        return nextMeta
      })
      onChatHistoryChange(
        appendChatMessages(nextHistory, [{ role: 'assistant', content: reply.text }]),
      )
    } catch (error) {
      if (backgroundSubmitPromiseRef.current) {
        await backgroundSubmitPromiseRef.current.catch(() => null)
      }

      if (backgroundFallbackTriggeredRef.current) {
        return
      }
      setErrorMessage(error?.message || 'AI 教练暂时不可用，请稍后重试。')
    } finally {
      setIsSending(false)
      activeRequestAbortRef.current = null
      backgroundSubmitPromiseRef.current = null
      pendingRequestRef.current = null
      setStreamingText('')
    }
  }

  return (
    <CoachLayout
      composer={
        <Composer
          draft={draft}
          errorMessage={errorMessage}
          isSending={isSending}
          onDraftChange={setDraft}
          onSubmit={handleSubmit}
        />
      }
      messages={
        <MessageList
          emptyQuestions={emptyQuestions}
          isSending={isSending}
          messages={messageList}
          onAdopt={handleAdoptSuggestion}
          onDismissSuggestion={handleDismissSuggestion}
          onSuggestionClick={handleSuggestionQuestion}
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
          modelLabel="DeepSeek v4"
          onClear={handleNewChat}
          onExport={handleExportConversation}
          title={activeHistoryItem?.isPlaceholder ? '新的对话' : activeHistoryItem?.title || '新的对话'}
        />
      }
    />
  )
}

export default CoachTab
