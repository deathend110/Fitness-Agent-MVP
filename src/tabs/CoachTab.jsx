import { useMemo } from 'react'
import { deepSeekDefaults, getDeepSeekApiKeyStatus } from '../api/deepseek.js'
import { buildSystemPrompt } from '../utils/prompt.js'

function CoachTab({ chatHistory, dailyLog, profile, weeklyPlan }) {
  const recentDates = Object.keys(dailyLog)
    .sort((left, right) => right.localeCompare(left))
    .slice(0, 3)
  const apiKeyStatus = getDeepSeekApiKeyStatus()
  const contextPreview = useMemo(
    () => buildSystemPrompt(profile, weeklyPlan, dailyLog),
    [dailyLog, profile, weeklyPlan],
  )
  const statusTone = apiKeyStatus.hasKey
    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
    : 'border-amber-500/40 bg-amber-500/10 text-amber-100'

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 4</p>
      <h2 className="mt-3 text-2xl font-bold text-white">AI 教练</h2>
      <p className="mt-4 max-w-3xl leading-7 text-slate-300">
        当前先展示默认聊天记录、最近日志摘要，以及供 Task 3.3 验收使用的临时上下文预览。
        这里还没有接入真正的 DeepSeek 请求，只用于确认 prompt 中已经包含档案、计划、日志和 TDEE。
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
        <p className="mt-4 text-xs leading-5 text-slate-300">
          Task 4.1 当前只完成 API 封装和状态提示，正式对话发送会在后续任务接入。
        </p>
      </article>

      <div className="mt-8 grid gap-4 xl:grid-cols-[0.9fr_0.9fr_1.2fr]">
        <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
          <h3 className="text-lg font-semibold text-white">对话预览</h3>
          <ul className="mt-4 space-y-3">
            {chatHistory.map((message, index) => (
              <li
                className="rounded-md border border-fitloop-line/80 bg-fitloop-panel/70 p-3"
                key={`${message.role}-${index}`}
              >
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  {message.role === 'user' ? '用户' : 'AI 教练'}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-200">{message.content}</p>
              </li>
            ))}
          </ul>
        </article>

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
              Task 3.3
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            该内容会在后续真正发送 AI 请求前作为 system prompt 使用，当前先直接展示出来，便于检查是否包含训练备注和 TDEE。
          </p>
          <pre className="mt-4 overflow-x-auto rounded-md border border-fitloop-line/80 bg-fitloop-panel/70 p-4 text-xs leading-6 text-slate-200 whitespace-pre-wrap">
            {contextPreview}
          </pre>
        </article>
      </div>
    </section>
  )
}

export default CoachTab
