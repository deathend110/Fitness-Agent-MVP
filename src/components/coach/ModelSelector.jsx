function ModelSelector({
  disabled = false,
  models = [],
  onModelChange,
  onThinkingChange,
  selectedModel = '',
  thinking = { enabled: false, budget: 'auto' },
}) {
  const activeModel = models.find((model) => model.id === selectedModel) || models[0] || null
  const supportsThinking = Boolean(activeModel?.supportsThinking)
  const thinkingEnabled = Boolean(thinking?.enabled && supportsThinking)
  const thinkingBudget = thinking?.budget || 'auto'

  function updateThinking(nextPatch) {
    onThinkingChange?.({
      enabled: thinkingEnabled,
      budget: thinkingBudget,
      ...nextPatch,
    })
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
      <label className="sr-only" htmlFor="coach-model-select">
        模型
      </label>
      <select
        className="h-8 max-w-[190px] rounded-md border border-fitloop-line bg-fitloop-canvas px-2 text-xs font-medium text-slate-600 outline-none transition focus:border-fitloop-orange disabled:opacity-50"
        disabled={disabled || !models.length}
        id="coach-model-select"
        onChange={(event) => onModelChange?.(event.target.value)}
        value={activeModel?.id || ''}
      >
        {models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.label || model.id}
          </option>
        ))}
      </select>

      {supportsThinking ? (
        <div className="inline-flex h-8 items-center gap-2 rounded-md border border-fitloop-line bg-fitloop-canvas px-2">
          <label className="inline-flex items-center gap-1">
            <input
              checked={thinkingEnabled}
              className="h-3.5 w-3.5 accent-fitloop-orange"
              disabled={disabled}
              onChange={(event) => updateThinking({ enabled: event.target.checked })}
              type="checkbox"
            />
            <span>思考</span>
          </label>
          {thinkingEnabled ? (
            <select
              aria-label="思考强度"
              className="h-6 rounded border border-fitloop-line bg-white px-1 text-xs outline-none focus:border-fitloop-orange"
              disabled={disabled}
              onChange={(event) => updateThinking({ budget: event.target.value })}
              value={thinkingBudget}
            >
              <option value="auto">auto</option>
              <option value="max">max</option>
            </select>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export default ModelSelector
