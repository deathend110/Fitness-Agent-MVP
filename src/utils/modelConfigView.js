function normalizeThinkingCapability(thinking = {}, supportsThinking = false) {
  const intensityOptions = Array.isArray(thinking?.intensityOptions)
    ? thinking.intensityOptions
        .filter((option) => option && typeof option.id === 'string')
        .map((option) => ({
          id: option.id,
          label: option.label || option.id,
        }))
    : []

  return {
    supported: Boolean(thinking?.supported ?? supportsThinking),
    canDisable: Boolean(thinking?.canDisable ?? supportsThinking),
    defaultEnabled: Boolean(thinking?.defaultEnabled),
    intensityOptions,
    defaultIntensity:
      thinking?.defaultIntensity ||
      intensityOptions[0]?.id ||
      (supportsThinking ? 'standard' : 'auto'),
  }
}

export function buildSelectableModelView(model = {}) {
  const thinking = normalizeThinkingCapability(model.thinking, model.supportsThinking)

  return {
    id: model.id || '',
    label: model.label || model.id || '',
    providerId: model.providerId || '',
    providerType: model.providerType || '',
    providerLabel: model.providerLabel || '',
    remoteModelId: model.remoteModelId || '',
    supportsThinking: Boolean(model.supportsThinking ?? thinking.supported),
    thinking,
  }
}

export function buildModelRuntimeView(payload = {}) {
  const models = Array.isArray(payload?.models)
    ? payload.models.map((model) => buildSelectableModelView(model))
    : []

  const defaultModelRef = payload?.defaultModelRef || payload?.defaultModel || models[0]?.id || ''

  return {
    defaultModel: defaultModelRef,
    defaultModelRef,
    models,
    thinking:
      payload?.thinking && typeof payload.thinking === 'object'
        ? payload.thinking
        : { enabled: false, budget: 'auto', options: ['off', 'auto', 'max'] },
  }
}

export function buildProviderConfigView(payload = {}) {
  const providers = Array.isArray(payload?.providers)
    ? payload.providers.map((provider, index) => ({
        id: provider?.id || `provider_${index + 1}`,
        type: provider?.type || 'openai_compatible',
        label: provider?.label || '',
        enabled: provider?.enabled !== false,
        apiKey: provider?.apiKey || '',
        apiKeyPreview: provider?.apiKeyPreview || '',
        baseUrl: provider?.baseUrl || '',
        selectedModels: Array.isArray(provider?.selectedModels)
          ? provider.selectedModels.map((model, modelIndex) => ({
              remoteId: model?.remoteId || `model_${modelIndex + 1}`,
              label: model?.label || model?.remoteId || '',
              enabled: model?.enabled !== false,
            }))
          : [],
      }))
    : []

  return {
    version: payload?.version || 1,
    defaultModelRef: payload?.defaultModelRef || '',
    providers,
  }
}

export function listProviderModelRefs(config = {}) {
  const refs = []

  for (const provider of config?.providers || []) {
    for (const model of provider?.selectedModels || []) {
      if (!provider?.id || !model?.remoteId) {
        continue
      }

      refs.push({
        id: `${provider.id}::${model.remoteId}`,
        label: `${provider.label || provider.id} / ${model.label || model.remoteId}`,
        enabled: provider.enabled !== false && model.enabled !== false,
      })
    }
  }

  return refs
}

export function createEmptyProviderConfig(providerType = 'openai_compatible', index = 1) {
  const isGemini = providerType === 'gemini_native'

  return {
    id: `provider_${providerType}_${index}`,
    type: providerType,
    label: isGemini ? 'Gemini 新账号' : 'OpenAI 兼容新账号',
    enabled: true,
    apiKey: '',
    apiKeyPreview: '',
    baseUrl: isGemini
      ? 'https://generativelanguage.googleapis.com/v1beta'
      : 'https://api.deepseek.com',
    selectedModels: [],
  }
}
