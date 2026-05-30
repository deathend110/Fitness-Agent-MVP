import { useEffect, useRef } from 'react'
import CoachComposer from './CoachComposer.jsx'
import CoachMessageBubble from './CoachMessageBubble.jsx'

function CoachConversationPanel({
  chatHistory,
  draft,
  errorMessage,
  isSending,
  onDraftChange,
  onSubmit,
  streamingText,
}) {
  const isEmpty = chatHistory.length === 0
  const messageEndRef = useRef(null)

  useEffect(() => {
    if (isEmpty) {
      return
    }

    messageEndRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end',
    })
  }, [chatHistory, isEmpty, isSending, streamingText])

  return (
    <section className="flex min-w-0 flex-1 flex-col bg-white">
      {isEmpty ? (
        <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
          <div className="w-full max-w-[56rem]">
            <div className="text-center">
              <p className="text-[2rem] font-medium leading-tight tracking-tight text-slate-700 sm:text-[2.4rem]">
                Hello, I&apos;m <span className="font-bold text-slate-800">RepMind</span>{' '}
                <span className="text-fitloop-orange">★</span>
              </p>
            </div>

            <div className="mt-10">
              <CoachComposer
                draft={draft}
                errorMessage={errorMessage}
                isSending={isSending}
                onDraftChange={onDraftChange}
                onSubmit={onSubmit}
                variant="hero"
              />
            </div>
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-6 py-8 sm:px-10">
            <div className="mx-auto flex w-full max-w-[56rem] flex-col gap-5">
              {chatHistory.map((message, index) => (
                <CoachMessageBubble
                  key={`${message.role}-${index}-${message.content}`}
                  message={message}
                />
              ))}

              {isSending ? (
                <CoachMessageBubble
                  isStreaming
                  message={{
                    role: 'assistant',
                    content: streamingText || '正在整理你的最新训练上下文，请稍等...',
                  }}
                />
              ) : null}

              <div ref={messageEndRef} />
            </div>
          </div>

          <div className="border-t border-[#e5ebf7] px-6 py-5 sm:px-10">
            <div className="mx-auto w-full max-w-[56rem]">
              <CoachComposer
                draft={draft}
                errorMessage={errorMessage}
                isSending={isSending}
                onDraftChange={onDraftChange}
                onSubmit={onSubmit}
              />
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export default CoachConversationPanel
