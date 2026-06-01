function ClearChatIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M9 5.5h6m-8 3h10m-8 3v4m4-4v4m-7 4.5h12a1 1 0 0 0 1-1l.6-10.2A1 1 0 0 0 18.6 7H5.4a1 1 0 0 0-1 .8L5 18a1 1 0 0 0 1 1Zm3-13V4.8a.8.8 0 0 1 .8-.8h4.4a.8.8 0 0 1 .8.8V6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  )
}

function ExportChatIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M12 4.5v9m0 0 3.5-3.5M12 13.5 8.5 10M5.5 16.5v1.8A1.2 1.2 0 0 0 6.7 19.5h10.6a1.2 1.2 0 0 0 1.2-1.2v-1.8"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="m10.7 4.5.4-1.1a1 1 0 0 1 1.9 0l.4 1.1a1 1 0 0 0 .9.6l1.1.1a1 1 0 0 1 .6 1.7l-.8.8a1 1 0 0 0-.3 1l.2 1.1a1 1 0 0 1-1.5 1l-.9-.5a1 1 0 0 0-1 0l-.9.5a1 1 0 0 1-1.5-1l.2-1.1a1 1 0 0 0-.3-1l-.8-.8a1 1 0 0 1 .6-1.7l1.1-.1a1 1 0 0 0 .9-.6ZM12 9.4a1.6 1.6 0 1 0 0-3.2 1.6 1.6 0 0 0 0 3.2ZM5 14.6l.7-.4a1 1 0 0 1 1 0l.7.4a1 1 0 0 0 1.5-1.1l-.2-.8a1 1 0 0 1 .3-1l.6-.6a1 1 0 0 0-.6-1.7l-.8-.1a1 1 0 0 1-.8-.6l-.3-.8a1 1 0 0 0-1.9 0l-.3.8a1 1 0 0 1-.8.6l-.8.1a1 1 0 0 0-.6 1.7l.6.6a1 1 0 0 1 .3 1l-.2.8A1 1 0 0 0 5 14.6Zm13.3-.4.7.4a1 1 0 0 0 1.5-1.1l-.2-.8a1 1 0 0 1 .3-1l.6-.6a1 1 0 0 0-.6-1.7l-.8-.1a1 1 0 0 1-.8-.6l-.3-.8a1 1 0 0 0-1.9 0l-.3.8a1 1 0 0 1-.8.6l-.8.1a1 1 0 0 0-.6 1.7l.6.6a1 1 0 0 1 .3 1l-.2.8a1 1 0 0 0 1.5 1.1l.7-.4a1 1 0 0 1 1 0ZM12 19.5a1.8 1.8 0 1 0 0-3.6 1.8 1.8 0 0 0 0 3.6Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.4"
      />
    </svg>
  )
}

function TopbarIconButton({ ariaLabel, children, onClick, tooltip }) {
  return (
    <div className="group relative">
      <button
        aria-label={ariaLabel}
        className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-fitloop-line/80 bg-white/88 text-slate-500 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-fitloop-orange/35 hover:bg-fitloop-orange/10 hover:text-fitloop-orange focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fitloop-orange/35 focus-visible:ring-offset-2"
        onClick={() => onClick?.()}
        title={tooltip}
        type="button"
      >
        {children}
      </button>
      <span className="pointer-events-none absolute right-0 top-[calc(100%+0.5rem)] z-10 whitespace-nowrap rounded-xl bg-slate-900 px-2.5 py-1.5 text-[11px] font-medium text-white opacity-0 shadow-lg transition duration-200 group-hover:opacity-100 group-focus-within:opacity-100">
        {tooltip}
      </span>
    </div>
  )
}

function ChatTopbar({
  modelLabel = 'DeepSeek v4',
  onOpenModelConfig,
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

      <div className="flex items-center gap-2">
        <TopbarIconButton
          ariaLabel="模型设置"
          onClick={onOpenModelConfig}
          tooltip="配置模型供应商与可用模型"
        >
          <SettingsIcon />
        </TopbarIconButton>
        <TopbarIconButton
          ariaLabel="清除对话"
          onClick={onClear}
          tooltip="新建一个空白对话"
        >
          <ClearChatIcon />
        </TopbarIconButton>
        <TopbarIconButton
          ariaLabel="导出对话"
          onClick={onExport}
          tooltip="导出当前对话内容"
        >
          <ExportChatIcon />
        </TopbarIconButton>
      </div>
    </div>
  )
}

export default ChatTopbar
