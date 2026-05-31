import { useEffect, useRef } from 'react'
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
  streamingText = '',
}) {
  const scrollRef = useRef(null)
  const isEmpty = messages.length === 0

  useEffect(() => {
    if (!scrollRef.current || isEmpty) {
      return
    }

    const element = scrollRef.current

    // 只有用户本来就在底部附近，或当前处于流式回复时，才自动追到底部。
    if (isSending || shouldAutoScroll(element)) {
      requestAnimationFrame(() => {
        element.scrollTop = element.scrollHeight
      })
    }
  }, [isEmpty, isSending, messages, streamingText])

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
              content: streamingText || '正在整理上下文...',
            }}
          />
        ) : null}
      </div>
    </div>
  )
}

export default MessageList
