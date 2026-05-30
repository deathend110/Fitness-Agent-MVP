function CoachMessageActions() {
  return (
    <div className="mt-2 flex items-center gap-2 text-slate-400">
      <span className="text-xs">昨天 23:49</span>
      <button
        aria-label="消息信息"
        className="inline-flex h-6 w-6 items-center justify-center rounded-full transition hover:bg-slate-100 hover:text-slate-600"
        type="button"
      >
        <span className="text-xs">i</span>
      </button>
      <button
        aria-label="复制消息"
        className="inline-flex h-6 w-6 items-center justify-center rounded-full transition hover:bg-slate-100 hover:text-slate-600"
        type="button"
      >
        <span className="text-xs">⧉</span>
      </button>
      <button
        aria-label="回复消息"
        className="inline-flex h-6 w-6 items-center justify-center rounded-full transition hover:bg-slate-100 hover:text-slate-600"
        type="button"
      >
        <span className="text-xs">↩</span>
      </button>
    </div>
  )
}

function CoachMessageBubble({ message, isStreaming = false }) {
  const isUser = message.role === 'user'

  return (
    <article className={`flex ${isUser ? 'justify-end' : 'justify-start'} gap-3`}>
      {!isUser ? (
        <span className="mt-2 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#e9efff] text-fitloop-orange shadow-sm shadow-black/10">
          ✦
        </span>
      ) : null}

      <div className="min-w-0">
        <div
          className={`max-w-[42rem] rounded-[1.5rem] border px-4 py-3 text-sm leading-6 ${
            isUser
              ? 'border-[#d3def6] bg-[#eaf0ff] text-slate-700'
              : 'border-[#dde5f3] bg-white text-slate-700 shadow-sm shadow-black/10'
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {!isUser && !isStreaming ? <CoachMessageActions /> : null}
      </div>
    </article>
  )
}

export default CoachMessageBubble
