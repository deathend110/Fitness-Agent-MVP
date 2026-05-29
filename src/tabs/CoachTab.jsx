function CoachTab({ chatHistory, dailyLog }) {
  const recentDates = Object.keys(dailyLog)
    .sort((left, right) => right.localeCompare(left))
    .slice(0, 3)

  return (
    <section className="rounded-lg border border-fitloop-line bg-fitloop-panel p-8 shadow-2xl shadow-black/20">
      <p className="text-sm font-semibold text-fitloop-mint">Tab 4</p>
      <h2 className="mt-3 text-2xl font-bold text-white">AI 教练</h2>
      <p className="mt-4 max-w-2xl leading-7 text-slate-300">
        当前先展示默认聊天记录和最近日志摘要，后续会在这里接入 DeepSeek 上下文注入与建议采纳。
      </p>

      <div className="mt-8 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
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
                    {log.kcal} kcal · 蛋白质 {log.protein} g · 疲劳度 {log.fatigue}/5
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-400">{log.trainingNotes}</p>
                </li>
              )
            })}
          </ul>
        </article>
      </div>
    </section>
  )
}

export default CoachTab
