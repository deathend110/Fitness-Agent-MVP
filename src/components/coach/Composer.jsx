import { useEffect, useRef } from 'react'
import FileAttachmentTray from './FileAttachmentTray.jsx'
import ModelSelector from './ModelSelector.jsx'

function Composer({
  attachedFiles = [],
  draft = '',
  errorMessage = '',
  helperText = 'AI 教练基于你的本地数据作答，不上传到服务器',
  isSending = false,
  isUploading = false,
  modelOptions = [],
  onDraftChange,
  onFilesSelected,
  onModelChange,
  onRemoveFile,
  onSubmit,
  onThinkingChange,
  placeholder = 'Ask RepMind...',
  selectedModel = '',
  thinking = { enabled: false, budget: 'auto' },
}) {
  const textareaRef = useRef(null)

  useEffect(() => {
    const element = textareaRef.current

    if (!element) {
      return
    }

    // 输入框高度跟随内容增长，但在 MVP 阶段限制上限，避免输入区吃掉消息区空间。
    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, 160)}px`
  }, [draft])

  function handleKeyDown(event) {
    // 对话产品里 Enter 发送是高频路径，Shift+Enter 留给手动换行。
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSubmit?.(event)
    }
  }

  return (
    <form className="mx-auto w-full max-w-[720px]" onSubmit={onSubmit}>
      <div className="rounded-[22px] border border-fitloop-line bg-fitloop-panel shadow-[0_4px_24px_rgba(30,40,80,0.09)] transition hover:border-fitloop-orange/35 focus-within:border-fitloop-orange focus-within:shadow-[0_0_0_4px_rgba(109,94,252,0.10),0_4px_24px_rgba(30,40,80,0.09)]">
        <textarea
          className="min-h-[48px] max-h-[160px] w-full resize-none border-0 bg-transparent px-5 pb-2 pt-4 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400"
          disabled={isSending}
          onChange={(event) => onDraftChange?.(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          ref={textareaRef}
          rows={1}
          value={draft}
        />

        <div className="flex items-center justify-between gap-3 px-3 pb-3">
          <FileAttachmentTray
            attachedFiles={attachedFiles}
            disabled={isSending || isUploading}
            isUploading={isUploading}
            onFilesSelected={onFilesSelected}
            onRemoveFile={onRemoveFile}
          />

          <div className="flex items-center gap-1.5">
            <ModelSelector
              disabled={isSending}
              models={modelOptions}
              onModelChange={onModelChange}
              onThinkingChange={onThinkingChange}
              selectedModel={selectedModel}
              thinking={thinking}
            />
            <button
              aria-label="语音输入占位"
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-fitloop-line text-slate-400 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange disabled:opacity-40"
              disabled
              type="button"
            >
              <span className="text-sm leading-none">⌁</span>
            </button>

            <button
              aria-label="发送消息"
              className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-fitloop-orange text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!draft.trim() || isSending || isUploading}
              type="submit"
            >
              <span className="text-sm leading-none">{isSending ? '…' : '➤'}</span>
            </button>
          </div>
        </div>
      </div>

      {errorMessage ? (
        <p
          className="mt-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm leading-6 text-red-600"
          role="alert"
        >
          {errorMessage}
        </p>
      ) : null}

      <p className="mt-2 text-center text-[11px] text-slate-400">{helperText}</p>
    </form>
  )
}

export default Composer
