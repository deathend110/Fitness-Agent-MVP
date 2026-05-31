import AdoptCard from '../AdoptCard.jsx'

function AssistantActions({ onCopy, onRetry }) {
  return (
    <div className="mt-1.5 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
      <button
        className="rounded-lg border border-fitloop-line bg-white px-2 py-1 text-xs text-slate-500 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange"
        onClick={() => onCopy?.()}
        type="button"
      >
        复制
      </button>
      <button
        className="rounded-lg border border-fitloop-line bg-white px-2 py-1 text-xs text-slate-500 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange"
        onClick={() => onRetry?.()}
        type="button"
      >
        重试
      </button>
    </div>
  )
}

function MessageBubble({ message, isStreaming = false, onAdopt, onDismissSuggestion }) {
  const isUser = message.role === 'user'
  const senderLabel = message.senderLabel || (isUser ? '我' : 'RepMind')

  return (
    <article className={`group flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          isUser
            ? 'bg-gradient-to-br from-indigo-100 to-blue-200 text-indigo-600'
            : 'border border-fitloop-orange/20 bg-fitloop-orange/10 text-fitloop-orange'
        }`}
      >
        {isUser ? '我' : 'R'}
      </div>

      <div className={`flex min-w-0 flex-1 flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <p className="mb-1.5 text-[11px] text-slate-400">
          {senderLabel}
          {message.timeLabel ? (
            <span className="ml-2 text-fitloop-line">{message.timeLabel}</span>
          ) : null}
        </p>

        <div
          className={`max-w-[600px] rounded-2xl border px-4 py-3 text-sm leading-7 text-slate-800 ${
            isUser
              ? 'border-fitloop-orange/20 bg-fitloop-orange/10'
              : 'border-fitloop-line bg-fitloop-canvas'
          }`}
        >
          <p className="whitespace-pre-wrap">
            {message.content}
            {isStreaming ? (
              <span aria-hidden="true" className="ml-0.5 animate-pulse text-fitloop-orange">
                ▋
              </span>
            ) : null}
          </p>
        </div>

        {!isUser && !isStreaming ? (
          <AssistantActions onCopy={message.onCopy} onRetry={message.onRetry} />
        ) : null}

        {message.suggestionCard ? (
          <div className="mt-3 w-full max-w-[600px]">
            <AdoptCard
              card={message.suggestionCard}
              onAdopt={() => onAdopt?.(message.suggestionCard)}
              onDismiss={() => onDismissSuggestion?.(message.suggestionCard)}
            />
          </div>
        ) : null}
      </div>
    </article>
  )
}

export default MessageBubble
