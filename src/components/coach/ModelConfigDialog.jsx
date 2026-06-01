import { useEffect, useMemo, useState } from 'react'
import ProviderConfigEditor from './ProviderConfigEditor.jsx'
import {
  buildProviderConfigView,
  createEmptyProviderConfig,
  listProviderModelRefs,
} from '../../utils/modelConfigView.js'

function buildDraftFromValue(value) {
  return buildProviderConfigView(value)
}

function sanitizeProviderForSave(provider) {
  const nextProvider = {
    id: (provider?.id || '').trim(),
    type: provider?.type || 'openai_compatible',
    label: (provider?.label || '').trim(),
    enabled: provider?.enabled !== false,
    baseUrl: (provider?.baseUrl || '').trim(),
    selectedModels: Array.isArray(provider?.selectedModels)
      ? provider.selectedModels
          .map((model) => ({
            remoteId: (model?.remoteId || '').trim(),
            label: (model?.label || model?.remoteId || '').trim(),
            enabled: model?.enabled !== false,
          }))
          .filter((model) => model.remoteId)
      : [],
  }

  // 如果前端只展示了脱敏预览且用户没有重新填写，就不要把 apiKey 字段发回去，
  // 这样后端保存时会沿用现有真实密钥，而不是被空字符串覆盖。
  const apiKey = (provider?.apiKey || '').trim()
  if (apiKey) {
    nextProvider.apiKey = apiKey
  }

  return nextProvider
}

function ModelConfigDialog({
  errorMessage = '',
  onClose,
  onDiscoverProviderModels,
  onSave,
  onTestProviderConnection,
  open = false,
  saving = false,
  value,
}) {
  const [draft, setDraft] = useState(() => buildDraftFromValue(value))
  const [providerActionState, setProviderActionState] = useState({})

  useEffect(() => {
    if (!open) {
      return
    }

    setDraft(buildDraftFromValue(value))
    setProviderActionState({})
  }, [open, value])

  const modelRefs = useMemo(() => listProviderModelRefs(draft), [draft])

  if (!open) {
    return null
  }

  function updateProvider(providerId, nextProvider) {
    setDraft((current) => ({
      ...current,
      providers: current.providers.map((provider) =>
        provider.id === providerId ? nextProvider : provider,
      ),
    }))
  }

  function removeProvider(providerId) {
    setDraft((current) => {
      const nextProviders = current.providers.filter((provider) => provider.id !== providerId)
      const nextRefs = listProviderModelRefs({ ...current, providers: nextProviders })
      return {
        ...current,
        providers: nextProviders,
        defaultModelRef:
          current.defaultModelRef && nextRefs.some((item) => item.id === current.defaultModelRef)
            ? current.defaultModelRef
            : nextRefs[0]?.id || '',
      }
    })
  }

  function addProvider(providerType) {
    setDraft((current) => ({
      ...current,
      providers: [
        ...current.providers,
        createEmptyProviderConfig(providerType, current.providers.length + 1),
      ],
    }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    const payload = {
      version: draft.version || 1,
      defaultModelRef: draft.defaultModelRef,
      providers: draft.providers.map((provider) => sanitizeProviderForSave(provider)),
    }
    onSave?.(payload)
  }

  function updateProviderActionState(providerId, patch) {
    setProviderActionState((current) => ({
      ...current,
      [providerId]: {
        ...(current[providerId] || {}),
        ...patch,
      },
    }))
  }

  async function handleTestProvider(provider) {
    const sanitizedProvider = sanitizeProviderForSave(provider)
    if (!sanitizedProvider.apiKey) {
      updateProviderActionState(provider.id, {
        message: '请重新输入 API Key 后再测试连接。',
      })
      return
    }

    updateProviderActionState(provider.id, {
      testing: true,
      message: '',
    })

    try {
      const result = await onTestProviderConnection?.(sanitizedProvider)
      updateProviderActionState(provider.id, {
        testing: false,
        message: `连接成功，发现 ${result?.modelCount ?? 0} 个模型。`,
      })
    } catch (error) {
      updateProviderActionState(provider.id, {
        testing: false,
        message: error?.message || '连接测试失败，请检查地址和密钥。',
      })
    }
  }

  async function handleDiscoverProvider(provider) {
    const sanitizedProvider = sanitizeProviderForSave(provider)
    if (!sanitizedProvider.apiKey) {
      updateProviderActionState(provider.id, {
        message: '出于安全原因，发现模型前需要重新输入一次 API Key。',
      })
      return
    }

    updateProviderActionState(provider.id, {
      discovering: true,
      message: '',
    })

    try {
      const result = await onDiscoverProviderModels?.(sanitizedProvider)
      const discoveredModels = Array.isArray(result?.models) ? result.models : []
      const existingModels = Array.isArray(provider?.selectedModels) ? provider.selectedModels : []
      const existingByRemoteId = new Map(existingModels.map((item) => [item.remoteId, item]))
      const mergedModels = discoveredModels.map((model) => {
        const existing = existingByRemoteId.get(model.remoteId)
        return {
          remoteId: model.remoteId,
          label: existing?.label || model.label || model.remoteId,
          enabled: existing ? existing.enabled !== false : model.enabled !== false,
        }
      })
      const mergedRemoteIds = new Set(mergedModels.map((model) => model.remoteId))

      for (const existing of existingModels) {
        if (!mergedRemoteIds.has(existing.remoteId)) {
          mergedModels.push(existing)
        }
      }

      updateProvider(provider.id, {
        ...provider,
        apiKey: sanitizedProvider.apiKey,
        selectedModels: mergedModels,
      })
      updateProviderActionState(provider.id, {
        discovering: false,
        message: `已同步 ${discoveredModels.length} 个远端模型，可按需关闭不想展示的项。`,
      })
    } catch (error) {
      updateProviderActionState(provider.id, {
        discovering: false,
        message: error?.message || '发现模型失败，请检查地址和密钥。',
      })
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6 backdrop-blur-sm">
      <div className="absolute inset-0" onClick={onClose} />

      <form
        className="relative z-10 flex max-h-[min(92vh,900px)] w-full max-w-[1080px] flex-col overflow-hidden rounded-[32px] border border-white/30 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,255,0.96))] shadow-[0_24px_80px_rgba(15,23,42,0.28)]"
        onSubmit={handleSubmit}
      >
        <div className="flex items-start justify-between gap-4 border-b border-fitloop-line/70 px-6 py-5">
          <div>
            <p className="text-lg font-semibold text-slate-900">模型与供应商设置</p>
            <p className="mt-1 text-sm text-slate-500">
              这里保存 AI 教练可用的 Provider、模型列表和默认模型引用。
            </p>
          </div>
          <button
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-fitloop-line bg-white text-slate-500 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange"
            onClick={onClose}
            type="button"
          >
            ×
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
          <div className="grid gap-3 rounded-[28px] border border-fitloop-line/80 bg-fitloop-canvas/55 p-4 md:grid-cols-[1fr,auto,auto] md:items-end">
            <label className="space-y-1.5 text-xs text-slate-500">
              <span>默认模型</span>
              <select
                className="h-11 w-full rounded-xl border border-fitloop-line bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-fitloop-orange"
                onChange={(event) => setDraft((current) => ({ ...current, defaultModelRef: event.target.value }))}
                value={draft.defaultModelRef}
              >
                {modelRefs.length ? (
                  modelRefs.map((item) => (
                    <option key={item.id} disabled={!item.enabled} value={item.id}>
                      {item.label}
                    </option>
                  ))
                ) : (
                  <option value="">请先为 Provider 添加可用模型</option>
                )}
              </select>
            </label>

            <button
              className="inline-flex h-11 items-center justify-center rounded-xl border border-fitloop-line bg-white px-4 text-sm font-semibold text-slate-700 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange"
              onClick={() => addProvider('openai_compatible')}
              type="button"
            >
              添加 OpenAI 兼容 Provider
            </button>

            <button
              className="inline-flex h-11 items-center justify-center rounded-xl border border-fitloop-line bg-white px-4 text-sm font-semibold text-slate-700 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange"
              onClick={() => addProvider('gemini_native')}
              type="button"
            >
              添加 Gemini Provider
            </button>
          </div>

          <div className="space-y-4">
            {draft.providers.map((provider) => (
              <ProviderConfigEditor
                key={provider.id}
                connectionMessage={providerActionState[provider.id]?.message || ''}
                disabled={saving}
                isDiscovering={Boolean(providerActionState[provider.id]?.discovering)}
                isTesting={Boolean(providerActionState[provider.id]?.testing)}
                onChange={(nextProvider) => updateProvider(provider.id, nextProvider)}
                onDiscoverModels={handleDiscoverProvider}
                onRemove={removeProvider}
                onTestConnection={handleTestProvider}
                provider={provider}
              />
            ))}
          </div>

          {errorMessage ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {errorMessage}
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-fitloop-line/70 px-6 py-4">
          <p className="text-[11px] text-slate-400">
            保存后会立即刷新后端运行时缓存；未修改的脱敏密钥预览会继续沿用原值。
          </p>

          <div className="flex items-center gap-3">
            <button
              className="inline-flex h-10 items-center justify-center rounded-xl border border-fitloop-line bg-white px-4 text-sm font-semibold text-slate-600 transition hover:border-fitloop-orange/30 hover:text-fitloop-orange"
              onClick={onClose}
              type="button"
            >
              取消
            </button>
            <button
              className="inline-flex h-10 items-center justify-center rounded-xl bg-fitloop-orange px-5 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-40"
              disabled={saving || !draft.providers.length || !draft.defaultModelRef}
              type="submit"
            >
              {saving ? '保存中...' : '保存配置'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}

export default ModelConfigDialog
