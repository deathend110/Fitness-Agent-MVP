function TopbarIconButton({ ariaLabel, children, onClick }) {
  return (
    <button
      aria-label={ariaLabel}
      className="inline-flex h-8 w-8 items-center justify-center rounded-xl text-slate-400 transition hover:bg-fitloop-canvas hover:text-slate-700"
      onClick={() => onClick?.()}
      type="button"
    >
      {children}
    </button>
  )
}

function ChatTopbar({
  modelLabel = 'DeepSeek v4',
  title = '新的对话',
  onClear,
  onExport,
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h2 className="truncate text-sm font-semibold text-slate-800">{title}</h2>
          <span className="inline-flex items-center gap-1 rounded-full border border-fitloop-orange/20 bg-fitloop-orange/10 px-2 py-1 text-[11px] font-semibold text-fitloop-orange">
            <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-fitloop-orange" />
            {modelLabel}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <TopbarIconButton ariaLabel="清除对话" onClick={onClear}>
          <span className="text-sm leading-none">⌫</span>
        </TopbarIconButton>
        <TopbarIconButton ariaLabel="导出对话" onClick={onExport}>
          <span className="text-sm leading-none">⇩</span>
        </TopbarIconButton>
      </div>
    </div>
  )
}

export default ChatTopbar
