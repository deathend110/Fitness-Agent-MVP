import { useState } from 'react'

function buildEmptyDraft() {
  return {
    remoteId: '',
    label: '',
  }
}

function ProviderModelPicker({
  disabled = false,
  models = [],
  onChange,
}) {
  const [draft, setDraft] = useState(buildEmptyDraft)

  function updateModel(nextRemoteId, patch) {
    onChange?.(
      models.map((model) =>
        model.remoteId === nextRemoteId
          ? {
              ...model,
              ...patch,
            }
          : model,
      ),
    )
  }

  function removeModel(remoteId) {
    onChange?.(models.filter((model) => model.remoteId !== remoteId))
  }

  function handleAddModel() {
    const remoteId = draft.remoteId.trim()
    if (!remoteId) {
      return
    }

    if (models.some((model) => model.remoteId === remoteId)) {
      return
    }

    onChange?.([
      ...models,
      {
        remoteId,
        label: draft.label.trim() || remoteId,
        enabled: true,
      },
    ])
    setDraft(buildEmptyDraft())
  }

  return (
    <div className="space-y-3 rounded-2xl border border-fitloop-line/80 bg-white/80 p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-slate-700">可用模型</p>
          <p className="text-[11px] text-slate-400">先保存你真正想在 AI 教练页里展示的模型。</p>
        </div>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-500">
          {models.length} 个
        </span>
      </div>

      <div className="space-y-2">
        {models.length ? (
          models.map((model) => (
            <div
              key={model.remoteId}
              className="grid gap-2 rounded-2xl border border-fitloop-line/70 bg-fitloop-canvas/70 p-3 md:grid-cols-[auto,1.2fr,1fr,auto]"
            >
              <label className="inline-flex items-center gap-2 text-xs text-slate-600">
                <input
                  checked={model.enabled !== false}
                  className="h-4 w-4 accent-fitloop-orange"
                  disabled={disabled}
                  onChange={(event) => updateModel(model.remoteId, { enabled: event.target.checked })}
                  type="checkbox"
                />
                启用
              </label>

              <input
                className="h-10 rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
                disabled={disabled}
                onChange={(event) => updateModel(model.remoteId, { remoteId: event.target.value })}
                placeholder="远端模型 ID"
                value={model.remoteId}
              />

              <input
                className="h-10 rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
                disabled={disabled}
                onChange={(event) => updateModel(model.remoteId, { label: event.target.value })}
                placeholder="展示名称"
                value={model.label || ''}
              />

              <button
                className="inline-flex h-10 items-center justify-center rounded-xl border border-red-200 px-3 text-xs font-semibold text-red-500 transition hover:bg-red-50 disabled:opacity-40"
                disabled={disabled}
                onClick={() => removeModel(model.remoteId)}
                type="button"
              >
                删除
              </button>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-fitloop-line px-4 py-5 text-center text-xs text-slate-400">
            还没有可用模型，先手动添加一个远端模型 ID。
          </div>
        )}
      </div>

      <div className="grid gap-2 rounded-2xl border border-dashed border-fitloop-line/80 bg-fitloop-canvas/60 p-3 md:grid-cols-[1.2fr,1fr,auto]">
        <input
          className="h-10 rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
          disabled={disabled}
          onChange={(event) => setDraft((current) => ({ ...current, remoteId: event.target.value }))}
          placeholder="新增远端模型 ID，例如 gemini-2.5-flash"
          value={draft.remoteId}
        />
        <input
          className="h-10 rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
          disabled={disabled}
          onChange={(event) => setDraft((current) => ({ ...current, label: event.target.value }))}
          placeholder="可选展示名称"
          value={draft.label}
        />
        <button
          className="inline-flex h-10 items-center justify-center rounded-xl bg-fitloop-orange px-4 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-40"
          disabled={disabled || !draft.remoteId.trim()}
          onClick={handleAddModel}
          type="button"
        >
          添加模型
        </button>
      </div>
    </div>
  )
}

export default ProviderModelPicker
