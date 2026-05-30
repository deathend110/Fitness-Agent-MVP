import { useMemo, useState } from 'react'
import CoachConversationPanel from '../components/CoachConversationPanel.jsx'
import CoachSidebar from '../components/CoachSidebar.jsx'
import { getCoachBlockReason } from '../utils/coachGuard.js'
import { requestCoachReply, requestCoachReplyStream } from '../utils/coachChat.js'
import { appendChatMessages } from '../utils/chatHistory.js'

function getVisibleStreamText(fullText) {
  const markerIndex = fullText.indexOf('---JSON---')

  if (markerIndex === -1) {
    return fullText
  }

  return fullText.slice(0, markerIndex).trimEnd()
}

function buildRecentChatRecords(chatHistory) {
  const userMessages = chatHistory.filter((message) => message.role === 'user')

  if (!userMessages.length) {
    return [
      { id: 'record-test', label: '测试', active: true },
      { id: 'record-new-1', label: '新的聊天', active: false },
      { id: 'record-thought', label: '请求隐藏模型思考过...', active: false },
      { id: 'record-new-2', label: '新的聊天', active: false },
      { id: 'record-test-2', label: '测试', active: false },
    ]
  }

  return userMessages
    .slice(-5)
    .reverse()
    .map((message, index) => ({
      id: `record-${index}-${message.content}`,
      label: message.content.trim() || '新的聊天',
      active: index === 0,
    }))
}

function CoachTab({
  chatHistory,
  dailyLog,
  onChatHistoryChange,
  onWeeklyPlanChange,
  profile,
  weeklyPlan,
}) {
  const [draft, setDraft] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [streamingText, setStreamingText] = useState('')

  const coachBlockReason = useMemo(() => getCoachBlockReason(profile), [profile])
  const sidebarRecords = useMemo(
    () => buildRecentChatRecords(chatHistory),
    [chatHistory],
  )

  async function requestReplyWithFallback(payload) {
    try {
      return await requestCoachReplyStream(payload, {
        onText: (fullText) => {
          setStreamingText(getVisibleStreamText(fullText))
        },
      })
    } catch {
      setStreamingText('')
      return requestCoachReply(payload)
    }
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
      userInput,
      weeklyPlan,
    }

    setErrorMessage('')
    setIsSending(true)
    setStreamingText('')
    setDraft('')
    onChatHistoryChange(nextHistory)

    try {
      const reply = await requestReplyWithFallback(requestPayload)
      onChatHistoryChange(
        appendChatMessages(nextHistory, [{ role: 'assistant', content: reply.text }]),
      )
    } catch (error) {
      setErrorMessage(error?.message || 'AI 教练暂时不可用，请稍后重试。')
    } finally {
      setIsSending(false)
      setStreamingText('')
    }
  }

  return (
    <section className="flex min-h-[calc(100vh-8rem)] flex-col overflow-hidden bg-white lg:flex-row">
      <CoachSidebar records={sidebarRecords} />

      <CoachConversationPanel
        chatHistory={chatHistory}
        draft={draft}
        errorMessage={errorMessage}
        isSending={isSending}
        onDraftChange={setDraft}
        onSubmit={handleSubmit}
        streamingText={streamingText}
      />
    </section>
  )
}

export default CoachTab
