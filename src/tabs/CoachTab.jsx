import { useMemo, useState } from 'react'
import AdoptCard from '../components/AdoptCard.jsx'
import CoachConversationPanel from '../components/CoachConversationPanel.jsx'
import PromptPreviewPanel from '../components/PromptPreviewPanel.jsx'
import { deepSeekDefaults, getDeepSeekApiKeyStatus } from '../api/deepseek.js'
import { buildAdoptCardModel } from '../utils/adoptCard.js'
import { adoptPlanChange } from '../utils/adoptPlan.js'
import { getCoachBlockReason } from '../utils/coachGuard.js'
import { requestCoachReply, requestCoachReplyStream } from '../utils/coachChat.js'
import { appendChatMessages } from '../utils/chatHistory.js'
import { buildPromptPreviewModel } from '../utils/promptPreview.js'

function buildRecentDates(dailyLog) {
  return Object.keys(dailyLog)
    .sort((left, right) => right.localeCompare(left))
    .slice(0, 3)
}

function getVisibleStreamText(fullText) {
  const markerIndex = fullText.indexOf('---JSON---')

  if (markerIndex === -1) {
    return fullText
  }

  return fullText.slice(0, markerIndex).trimEnd()
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
  const [adoptFeedback, setAdoptFeedback] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [pendingSuggestion, setPendingSuggestion] = useState(null)
  const [streamingText, setStreamingText] = useState('')

  const recentDates = useMemo(() => buildRecentDates(dailyLog), [dailyLog])
  const apiKeyStatus = getDeepSeekApiKeyStatus()
  const adoptCard = useMemo(() => buildAdoptCardModel(pendingSuggestion), [pendingSuggestion])
  const promptPreview = useMemo(
    () => buildPromptPreviewModel(profile, weeklyPlan, dailyLog),
    [dailyLog, profile, weeklyPlan],
  )
  const coachBlockReason = useMemo(() => getCoachBlockReason(profile), [profile])
  const statusTone = apiKeyStatus.hasKey
    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
    : 'border-amber-200 bg-amber-50 text-amber-700'
  const adoptFeedbackTone =
    adoptFeedback?.tone === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : 'border-rose-200 bg-rose-50 text-rose-600'

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
    setAdoptFeedback(null)
    setIsSending(true)
    setStreamingText('')
    setDraft('')
    onChatHistoryChange(nextHistory)

    try {
      const reply = await requestReplyWithFallback(requestPayload)
      setPendingSuggestion(reply.suggestion)
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

  function handleAdoptSuggestion() {
    if (!pendingSuggestion) {
      return
    }

    const result = adoptPlanChange(weeklyPlan, pendingSuggestion.day, pendingSuggestion.changes)

    setAdoptFeedback({
      tone: result.ok ? 'success' : 'error',
      message: result.message,
    })

    if (!result.ok) {
      return
    }

    onWeeklyPlanChange(result.nextPlan)
    setPendingSuggestion(null)
  }

  function handleDismissSuggestion() {
    setAdoptFeedback(null)
    setPendingSuggestion(null)
  }

  return (
    <section className="rounded-[1.5rem] border border-fitloop-line bg-fitloop-panel/90 p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-fitloop-orange">Coach</p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-100">AI 教练</h2>
      <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300">
        这里已经接入真实对话流程。每次发送都会重新构建最新训练上下文，再调用 DeepSeek
        聊天接口；默认优先尝试流式输出，失败时自动回退到普通回复。聊天历史会写入
        <code>fitloop_chatHistory</code>，刷新后仍会保留最近 20 条消息。
      </p>

      <article className={`mt-6 rounded-2xl border p-5 shadow-sm shadow-black/20 ${statusTone}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold">配置与调用状态</h3>
            <p className="mt-2 text-sm leading-6">{apiKeyStatus.message}</p>
          </div>
          <span className="text-xs font-semibold uppercase tracking-[0.16em]">
            {apiKeyStatus.hasKey ? 'Ready' : 'Action Required'}
          </span>
        </div>
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <div className="rounded-xl border border-fitloop-line bg-fitloop-panel p-3 text-slate-200">
            <dt className="text-xs uppercase tracking-[0.16em] text-slate-300">Endpoint</dt>
            <dd className="mt-1 break-all">{deepSeekDefaults.baseUrl}/chat/completions</dd>
          </div>
          <div className="rounded-xl border border-fitloop-line bg-fitloop-panel p-3 text-slate-200">
            <dt className="text-xs uppercase tracking-[0.16em] text-slate-300">Default Model</dt>
            <dd className="mt-1">{deepSeekDefaults.model}</dd>
          </div>
        </dl>
      </article>

      <div className="mt-8 grid gap-5 xl:grid-cols-[1.05fr_0.85fr_1.1fr]">
        <div className="space-y-4">
          <CoachConversationPanel
            chatHistory={chatHistory}
            draft={draft}
            errorMessage={errorMessage}
            isSending={isSending}
            onDraftChange={setDraft}
            onSubmit={handleSubmit}
            streamingText={streamingText}
          />
          <AdoptCard
            card={adoptCard}
            onAdopt={handleAdoptSuggestion}
            onDismiss={handleDismissSuggestion}
          />
          {adoptFeedback ? (
            <p className={`rounded-md border px-3 py-2 text-sm leading-6 ${adoptFeedbackTone}`}>
              {adoptFeedback.message}
            </p>
          ) : null}
        </div>

        <article className="rounded-2xl border border-fitloop-line bg-fitloop-panel p-5 shadow-sm shadow-black/20">
          <h3 className="text-lg font-semibold text-slate-100">最近日志摘要</h3>
          {recentDates.length ? (
            <ul className="mt-4 space-y-3">
              {recentDates.map((date) => {
                const log = dailyLog[date]

                return (
                  <li
                    className="rounded-xl border border-fitloop-line/80 bg-fitloop-ink/30 p-3"
                    key={date}
                  >
                    <p className="text-sm font-semibold text-slate-100">{date}</p>
                    <p className="mt-1 text-sm text-slate-300">
                      {log.kcal ?? '未记录'} kcal · 蛋白质 {log.protein ?? '未记录'} g · 疲劳度{' '}
                      {log.fatigue ?? '未记录'}/5
                    </p>
                    <p className="mt-1 text-xs leading-5 text-slate-400">
                      {log.trainingNotes || '暂无记录'}
                    </p>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="mt-4 text-sm leading-6 text-slate-300">暂无记录</p>
          )}
        </article>

        <PromptPreviewPanel previewModel={promptPreview} />
      </div>
    </section>
  )
}

export default CoachTab
