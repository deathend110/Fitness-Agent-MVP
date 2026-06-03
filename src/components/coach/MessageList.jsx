import { useLayoutEffect, useRef } from 'react'
import { getCoachEmptyQuestionView } from '../../utils/coachView.js'
import EmptyState from './EmptyState.jsx'
import MessageBubble from './MessageBubble.jsx'

function shouldAutoScroll(scrollElement) {
  return (
    scrollElement.scrollHeight - scrollElement.scrollTop - scrollElement.clientHeight < 120
  )
}

function MessageList({
  emptyQuestions = getCoachEmptyQuestionView(),
  isSending = false,
  messages = [],
  onAdopt,
  onDismissSuggestion,
  onSuggestionClick,
  autoScrollKey = '',
  streamStatusLabel = '',
  streamingSuggestion = null,
  streamingText = '',
}) {
  const bottomRef = useRef(null)
  const scrollRef = useRef(null)
  const hasMountedRef = useRef(false)
  const isEmpty = messages.length === 0

  useLayoutEffect(() => {
    if (!scrollRef.current || isEmpty) {
      hasMountedRef.current = true
      return
    }

    const element = scrollRef.current
    const shouldRestoreBottom = !hasMountedRef.current

    // 只有用户本来就在底部附近，或当前处于流式回复时，才自动追到底部。
    // 首次挂载/切回 AI 教练页时，直接恢复到最新消息，避免页面回到历史最早一条。
    if (shouldRestoreBottom || isSending || shouldAutoScroll(element)) {
      requestAnimationFrame(() => {
        bottomRef.current?.scrollIntoView({ block: 'end' })
      })
    }
    hasMountedRef.current = true
  }, [autoScrollKey, isEmpty, isSending, messages.length, streamingText])

  if (isEmpty) {
    return (
      <div className="flex h-full items-center justify-center px-4 py-10 sm:px-7">
        <EmptyState onSuggestionClick={onSuggestionClick} questions={emptyQuestions} />
      </div>
    )
  }

  return (
    <div
      className="h-full overflow-y-auto overflow-x-hidden py-8"
      ref={scrollRef}
      style={{ scrollbarGutter: 'stable' }}
    >
      <div className="mx-auto flex w-full max-w-[720px] flex-col gap-5 px-4 sm:px-7">
        {messages.map((message, index) => (
          <MessageBubble
            key={`${message.role}-${index}-${message.content}`}
            message={message}
            onAdopt={onAdopt}
            onDismissSuggestion={onDismissSuggestion}
          />
        ))}

        {isSending ? (
          <MessageBubble
            isStreaming
            message={{
              role: 'assistant',
              content: streamingText || streamStatusLabel || '思考中',
            }}
            onAdopt={onAdopt}
            onDismissSuggestion={onDismissSuggestion}
          />
        ) : null}
        <div aria-hidden="true" ref={bottomRef} />
      </div>
    </div>
  )
}

export default MessageList
