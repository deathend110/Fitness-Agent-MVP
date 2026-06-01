import ProviderModelPicker from './ProviderModelPicker.jsx'

function ProviderConfigEditor({
  disabled = false,
  provider,
  onChange,
  onRemove,
}) {
  const providerType = provider?.type || 'openai_compatible'
  const apiKeyValue = provider?.apiKey || provider?.apiKeyPreview || ''

  function updateProvider(patch) {
    onChange?.({
      ...provider,
      ...patch,
    })
  }

  return (
    <div className="space-y-4 rounded-[28px] border border-fitloop-line/80 bg-fitloop-panel p-5 shadow-[0_8px_32px_rgba(30,40,80,0.08)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-800">{provider?.label || '未命名 Provider'}</p>
          <p className="mt-1 text-[11px] text-slate-400">
            {providerType === 'gemini_native' ? 'Gemini 原生 API' : 'OpenAI 兼容 API'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-600">
            <input
              checked={provider?.enabled !== false}
              className="h-4 w-4 accent-fitloop-orange"
              disabled={disabled}
              onChange={(event) => updateProvider({ enabled: event.target.checked })}
              type="checkbox"
            />
            启用
          </label>
          <button
            className="inline-flex h-9 items-center justify-center rounded-full border border-red-200 px-3 text-[11px] font-semibold text-red-500 transition hover:bg-red-50 disabled:opacity-40"
            disabled={disabled}
            onClick={() => onRemove?.(provider?.id)}
            type="button"
          >
            删除 Provider
          </button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="space-y-1.5 text-xs text-slate-500">
          <span>Provider ID</span>
          <input
            className="h-10 w-full rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
            disabled={disabled}
            onChange={(event) => updateProvider({ id: event.target.value })}
            value={provider?.id || ''}
          />
        </label>

        <label className="space-y-1.5 text-xs text-slate-500">
          <span>展示名称</span>
          <input
            className="h-10 w-full rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
            disabled={disabled}
            onChange={(event) => updateProvider({ label: event.target.value })}
            value={provider?.label || ''}
          />
        </label>

        <label className="space-y-1.5 text-xs text-slate-500">
          <span>协议类型</span>
          <select
            className="h-10 w-full rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
            disabled={disabled}
            onChange={(event) => updateProvider({ type: event.target.value })}
            value={providerType}
          >
            <option value="openai_compatible">OpenAI 兼容</option>
            <option value="gemini_native">Gemini 原生</option>
          </select>
        </label>

        <label className="space-y-1.5 text-xs text-slate-500">
          <span>Base URL</span>
          <input
            className="h-10 w-full rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
            disabled={disabled}
            onChange={(event) => updateProvider({ baseUrl: event.target.value })}
            value={provider?.baseUrl || ''}
          />
        </label>
      </div>

      <label className="block space-y-1.5 text-xs text-slate-500">
        <span>API Key</span>
        <input
          className="h-10 w-full rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
          disabled={disabled}
          onChange={(event) => updateProvider({ apiKey: event.target.value, apiKeyPreview: '' })}
          placeholder={
            provider?.apiKeyPreview ? '留空表示沿用当前已保存的密钥' : '输入真实 API Key'
          }
          value={apiKeyValue}
        />
        {provider?.apiKeyPreview && !provider?.apiKey ? (
          <p className="text-[11px] text-slate-400">当前显示的是脱敏预览；若不修改，保存时会沿用已存密钥。</p>
        ) : null}
      </label>

      <ProviderModelPicker
        disabled={disabled}
        models={provider?.selectedModels || []}
        onChange={(selectedModels) => updateProvider({ selectedModels })}
      />
    </div>
  )
}

export default ProviderConfigEditor
