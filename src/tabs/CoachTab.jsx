import { useMemo, useState } from 'react'
import CoachConversationPanel from '../components/CoachConversationPanel.jsx'
import { deepSeekDefaults, getDeepSeekApiKeyStatus } from '../api/deepseek.js'
import { requestCoachReply } from '../utils/coachChat.js'
import { appendChatMessages } from '../utils/chatHistory.js'
import { buildSystemPrompt } from '../utils/prompt.js'

function buildRecentDates(dailyLog) {
  return Object.keys(dailyLog)
    .sort((left, right) => right.localeCompare(left))
    .slice(0, 3)
}

function CoachTab({
  chatHistory,
  dailyLog,
  onChatHistoryChange,
  profile,
  weeklyPlan,
}) {
  const [draft, setDraft] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isSending, setIsSending] = useState(false)

  const recentDates = useMemo(() => buildRecentDates(dailyLog), [dailyLog])
  const apiKeyStatus = getDeepSeekApiKeyStatus()
  const contextPreview = useMemo(
    () => buildSystemPrompt(profile, weeklyPlan, dailyLog),
    [dailyLog, profile, weeklyPlan],
  )
  const statusTone = apiKeyStatus.hasKey
    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
    : 'border-amber-500/40 bg-amber-500/10 text-amber-100'

  async function handleSubmit(event) {
    event.preventDefault()

    const userInput = draft.trim()
    if (!userInput || isSending) {
      return
    }

    const userMessage = { role: 'user', content: userInput }
    const nextHistory = appendChatMessages(chatHistory, [userMessage])

    setErrorMessage('')
    setIsSending(true)
    setDraft('')
    onChatHistoryChange(nextHistory)

    try {
      const reply = await requestCoachReply({
        chatHistory,
        dailyLog,
        profile,
        userInput,
        weeklyPlan,
      })

      onChatHistoryChange(
        appendChatMessages(nextHistory, [{ role: 'assistant', content: reply }]),
      )
    } catch (error) {
      setErrorMessage(error?.message || 'AI 教练暂时不可用，请稍后重试。')
    } finally {
      setIsSending(false)
    }
  }

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 4</p>
      <h2 className="mt-3 text-2xl font-bold text-white">AI 教练</h2>
      <p className="mt-4 max-w-3xl leading-7 text-slate-300">
        这里已经接入真实对话流程。每次发送都会重新构建最新训练上下文，再调用
        DeepSeek 聊天接口；聊天历史会写入 <code>fitloop_chatHistory</code>，刷新后仍会保留最近
        20 条消息。
      </p>

      <article className={`mt-6 rounded-md border p-4 ${statusTone}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold">配置与调用状态</h3>
            <p className="mt-2 text-sm leading-6">{apiKeyStatus.message}</p>
          </div>
          <span className="text-xs font-semibold uppercase tracking-[0.16em]">
            {apiKeyStatus.hasKey ? 'Ready' : 'Action Required'}
          </span>
        </div>
        <dl className="mt-4 grid gap-3 text-sm text-slate-200 md:grid-cols-2">
          <div className="rounded-md border border-white/10 bg-black/10 p-3">
            <dt className="text-xs uppercase tracking-[0.16em] text-slate-300">Endpoint</dt>
            <dd className="mt-1 break-all">{deepSeekDefaults.baseUrl}/chat/completions</dd>
          </div>
          <div className="rounded-md border border-white/10 bg-black/10 p-3">
            <dt className="text-xs uppercase tracking-[0.16em] text-slate-300">Default Model</dt>
            <dd className="mt-1">{deepSeekDefaults.model}</dd>
          </div>
        </dl>
      </article>

      <div className="mt-8 grid gap-4 xl:grid-cols-[1.05fr_0.85fr_1.1fr]">
        <CoachConversationPanel
          chatHistory={chatHistory}
          draft={draft}
          errorMessage={errorMessage}
          isSending={isSending}
          onDraftChange={setDraft}
          onSubmit={handleSubmit}
        />

        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <h3 className="text-lg font-semibold text-white">最近日志摘要</h3>
          {recentDates.length ? (
            <ul className="mt-4 space-y-3">
              {recentDates.map((date) => {
                const log = dailyLog[date]

                return (
                  <li
                    className="rounded-md border border-fitloop-line/80 bg-fitloop-panel/70 p-3"
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

        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4 xl:min-h-[32rem]">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-semibold text-white">临时上下文预览</h3>
            <span className="text-xs uppercase tracking-[0.16em] text-fitloop-mint">
              buildSystemPrompt()
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            这里继续保留原始预览，方便检查每次正式发送前注入给 AI 的 system prompt 内容。
          </p>
          <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-md border border-fitloop-line/80 bg-fitloop-panel/70 p-4 text-xs leading-6 text-slate-200">
            {contextPreview}
          </pre>
        </article>
      </div>
    </section>
  )
}

export default CoachTab
