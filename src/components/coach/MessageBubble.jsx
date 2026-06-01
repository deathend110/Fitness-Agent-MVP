import AdoptCard from '../AdoptCard.jsx'
import MessageAttachmentCard from './MessageAttachmentCard.jsx'
import MarkdownMessage from './MarkdownMessage.jsx'

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
  const attachments = Array.isArray(message.attachments) ? message.attachments : []
  const senderLabel = message.senderLabel || (isUser ? '我' : 'RepMind')
  const rawSuggestion = message.suggestion || null
  const handleAdopt = rawSuggestion ? () => onAdopt?.(rawSuggestion) : undefined
  const handleDismissSuggestion = rawSuggestion
    ? () => onDismissSuggestion?.(rawSuggestion)
    : undefined

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

        {isUser && attachments.length ? (
          <div className="mb-2 flex w-full max-w-[600px] flex-col gap-2">
            {attachments.map((attachment, index) => (
              <MessageAttachmentCard
                attachment={attachment}
                key={`${attachment.fileId || attachment.originalName || 'attachment'}-${index}`}
              />
            ))}
          </div>
        ) : null}

        <div
          className={`max-w-[600px] rounded-2xl border px-4 py-3 text-sm leading-7 text-slate-800 ${
            isUser
              ? 'border-fitloop-orange/20 bg-fitloop-orange/10'
              : 'border-fitloop-line bg-fitloop-canvas'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">
              {message.content}
              {isStreaming ? (
                <span aria-hidden="true" className="ml-0.5 animate-pulse text-fitloop-orange">
                  ▋
                </span>
              ) : null}
            </p>
          ) : (
            <div>
              <MarkdownMessage content={message.content} />
            {isStreaming ? (
              <span aria-hidden="true" className="ml-0.5 animate-pulse text-fitloop-orange">
                ▋
              </span>
            ) : null}
            </div>
          )}
        </div>

        {!isUser && !isStreaming ? (
          <AssistantActions onCopy={message.onCopy} onRetry={message.onRetry} />
        ) : null}

        {message.suggestionCard ? (
          <div className="mt-3 w-full max-w-[600px]">
            <AdoptCard
              card={message.suggestionCard}
              onAdopt={handleAdopt}
              onDismiss={handleDismissSuggestion}
            />
          </div>
        ) : null}
      </div>
    </article>
  )
}

export default MessageBubble
