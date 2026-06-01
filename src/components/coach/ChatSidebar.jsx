function ChatSidebar({
  activeSessionId,
  groups = [],
  onDeleteSession,
  onNewChat,
  onSelectSession,
  title = 'AI 教练',
}) {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 border-b border-fitloop-line/60 px-4 pb-3 pt-4">
        <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.24em] text-slate-400">
          {title}
        </p>

        <button
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-fitloop-orange px-3 py-2 text-sm font-semibold text-white transition hover:brightness-110"
          onClick={() => onNewChat?.()}
          type="button"
        >
          <span aria-hidden="true" className="text-base leading-none">
            +
          </span>
          <span>新建对话</span>
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-2 py-3">
        {groups.map((group) => (
          <section key={group.label}>
            <p className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              {group.label}
            </p>

            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = item.id === activeSessionId || item.isActive

                return (
                  <div
                    className={`group flex items-start gap-1 rounded-xl border px-2 py-2 transition ${
                      isActive
                        ? 'border-fitloop-line bg-white shadow-sm'
                        : 'border-transparent text-slate-500 hover:bg-white/70 hover:text-slate-700'
                    }`}
                    key={item.id}
                  >
                    <button
                      aria-current={isActive ? 'page' : undefined}
                      className={`min-w-0 flex-1 text-left text-sm leading-5 ${
                        isActive ? 'font-medium text-slate-700' : 'text-slate-500 group-hover:text-slate-700'
                      }`}
                      onClick={() => onSelectSession?.(item.id)}
                      type="button"
                    >
                      <span className="block truncate">{item.title}</span>
                      {item.subtitle ? (
                        <span className="mt-1 block truncate text-[11px] leading-4 text-slate-400">
                          {item.subtitle}
                        </span>
                      ) : null}
                    </button>

                    {item.canDelete ? (
                      <button
                        aria-label={`删除对话：${item.title}`}
                        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-300 opacity-0 transition hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
                        onClick={(event) => {
                          event.stopPropagation()
                          onDeleteSession?.(item.id)
                        }}
                        title="删除对话"
                        type="button"
                      >
                        <span aria-hidden="true" className="text-sm leading-none">
                          ×
                        </span>
                      </button>
                    ) : null}
                  </div>
                )
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}

export default ChatSidebar
