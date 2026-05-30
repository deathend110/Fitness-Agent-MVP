function CoachComposer({
  draft,
  errorMessage,
  isSending,
  onDraftChange,
  onSubmit,
  variant = 'default',
}) {
  const isHero = variant === 'hero'

  return (
    <form className="w-full" onSubmit={onSubmit}>
      <div
        className={`rounded-[1.75rem] border border-[#d8e2f4] bg-white shadow-[0_18px_50px_-32px_rgba(73,92,149,0.42)] ${
          isHero ? 'px-4 py-4 sm:px-5 sm:py-5' : 'px-4 py-4'
        }`}
      >
        <label className="block">
          <span className="sr-only">输入你想问 AI 教练的问题</span>
          <textarea
            className={`w-full resize-none border-0 bg-transparent text-[0.98rem] leading-7 text-slate-700 outline-none placeholder:text-slate-400 ${
              isHero ? 'min-h-[7.5rem]' : 'min-h-[10rem]'
            }`}
            disabled={isSending}
            onChange={(event) => onDraftChange(event.target.value)}
            placeholder="Ask RepMind..."
            value={draft}
          />
        </label>

        <div className="mt-4 flex items-end justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              aria-label="添加附件"
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[#d8e2f4] text-fitloop-orange transition hover:bg-[#f2f5ff]"
              disabled={isSending}
              type="button"
            >
              <span className="text-lg leading-none">+</span>
            </button>

            <span className="inline-flex items-center gap-2 rounded-full bg-[#eef1f7] px-3 py-1.5 text-sm text-slate-600">
              <span aria-hidden="true" className="text-fitloop-orange">
                ✦
              </span>
              <span>deepseek/deepseek-v4-flash</span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              aria-label="语音输入"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[#d8e2f4] text-slate-400 transition hover:bg-[#f2f5ff] hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSending}
              type="button"
            >
              <span className="text-lg leading-none">⌁</span>
            </button>
            <button
              aria-label="发送消息"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[#eaf0ff] text-fitloop-orange transition hover:bg-[#dfe8ff] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!draft.trim() || isSending}
              type="submit"
            >
              <span className="text-lg leading-none">➤</span>
            </button>
          </div>
        </div>
      </div>

      {errorMessage ? (
        <p
          className="mt-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-600"
          role="alert"
        >
          {errorMessage}
        </p>
      ) : null}
    </form>
  )
}

export default CoachComposer
