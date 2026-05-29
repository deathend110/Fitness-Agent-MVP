function getRoleLabel(role) {
  return role === 'user' ? '你' : 'AI 教练'
}

function getBubbleTone(role) {
  if (role === 'user') {
    return 'ml-auto border-fitloop-orange/40 bg-fitloop-orange/10'
  }

  return 'mr-auto border-fitloop-line bg-fitloop-panel/80'
}

function CoachConversationPanel({
  chatHistory,
  draft,
  errorMessage,
  isSending,
  onDraftChange,
  onSubmit,
  streamingText,
}) {
  return (
    <article className="rounded-md border border-fitloop-line bg-fitloop-ink/40 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold text-white">对话区</h3>
        <span className="text-xs uppercase tracking-[0.16em] text-slate-400">
          最近 {chatHistory.length} 条
        </span>
      </div>

      <div className="mt-4 flex max-h-[30rem] min-h-[22rem] flex-col gap-3 overflow-y-auto pr-1">
        {chatHistory.map((message, index) => (
          <article
            className={`w-full max-w-[85%] rounded-md border p-3 ${getBubbleTone(message.role)}`}
            key={`${message.role}-${index}-${message.content}`}
          >
            <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
              {getRoleLabel(message.role)}
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-100">
              {message.content}
            </p>
          </article>
        ))}

        {isSending ? (
          <article className="mr-auto w-full max-w-[85%] rounded-md border border-fitloop-line bg-fitloop-panel/80 p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-400">AI 教练</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-100">
              {streamingText || '正在整理你的最新训练上下文，请稍等...'}
            </p>
          </article>
        ) : null}
      </div>

      <form className="mt-4 space-y-3" onSubmit={onSubmit}>
        <label className="block">
          <span className="sr-only">输入你想问 AI 教练的问题</span>
          <textarea
            className="min-h-28 w-full rounded-md border border-fitloop-line bg-fitloop-ink/60 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-500 focus:border-fitloop-orange disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSending}
            onChange={(event) => onDraftChange(event.target.value)}
            placeholder="比如：最近疲劳度有点高，要不要调整计划？"
            value={draft}
          />
        </label>

        {errorMessage ? (
          <p
            className="rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm leading-6 text-rose-100"
            role="alert"
          >
            {errorMessage}
          </p>
        ) : null}

        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-slate-400">
            {isSending
              ? '正在优先尝试流式输出；如果流式失败，会自动回退到普通回复。'
              : '发送前会自动注入最新档案、计划和日志。'}
          </p>
          <button
            className="rounded-md bg-fitloop-orange px-4 py-2 text-sm font-medium text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!draft.trim() || isSending}
            type="submit"
          >
            {isSending ? '发送中...' : '发送'}
          </button>
        </div>
      </form>
    </article>
  )
}

export default CoachConversationPanel
