import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildModelRuntimeView,
  buildProviderConfigView,
  buildSelectableModelView,
  listProviderModelRefs,
} from '../src/utils/modelConfigView.js'

test('buildSelectableModelView keeps modelRef and provider label', () => {
  const model = buildSelectableModelView({
    id: 'provider_gemini_main::gemini-2.5-flash',
    providerLabel: 'Gemini 主账号',
    label: 'Gemini 主账号 / Gemini 2.5 Flash',
    thinking: {
      supported: true,
      canDisable: true,
      defaultEnabled: true,
      intensityOptions: [{ id: 'standard', label: '标准' }],
      defaultIntensity: 'standard',
    },
  })

  assert.equal(model.id, 'provider_gemini_main::gemini-2.5-flash')
  assert.equal(model.providerLabel, 'Gemini 主账号')
  assert.equal(model.thinking.defaultIntensity, 'standard')
})

test('buildModelRuntimeView keeps defaultModelRef and normalized models', () => {
  const runtimeView = buildModelRuntimeView({
    defaultModelRef: 'provider_deepseek_main::deepseek-v4-flash',
    models: [
      {
        id: 'provider_deepseek_main::deepseek-v4-flash',
        providerLabel: 'DeepSeek 主账号',
        label: 'DeepSeek 主账号 / DeepSeek V4 Flash',
        supportsThinking: true,
        thinking: {
          supported: true,
          canDisable: true,
          defaultEnabled: false,
          intensityOptions: [{ id: 'deep', label: '深入' }],
          defaultIntensity: 'deep',
        },
      },
    ],
  })

  assert.equal(runtimeView.defaultModelRef, 'provider_deepseek_main::deepseek-v4-flash')
  assert.equal(runtimeView.models[0].thinking.intensityOptions[0].label, '深入')
})

test('buildProviderConfigView keeps masked preview but not invent real apiKey', () => {
  const configView = buildProviderConfigView({
    version: 1,
    defaultModelRef: 'provider_deepseek_main::deepseek-v4-flash',
    providers: [
      {
        id: 'provider_deepseek_main',
        type: 'openai_compatible',
        label: 'DeepSeek 主账号',
        enabled: true,
        apiKeyPreview: 'sk-t***1234',
        baseUrl: 'https://api.deepseek.com',
        selectedModels: [{ remoteId: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash', enabled: true }],
      },
    ],
  })

  assert.equal(configView.providers[0].apiKey, '')
  assert.equal(configView.providers[0].apiKeyPreview, 'sk-t***1234')
})

test('listProviderModelRefs builds provider-qualified labels', () => {
  const refs = listProviderModelRefs({
    providers: [
      {
        id: 'provider_gemini_main',
        label: 'Gemini 主账号',
        enabled: true,
        selectedModels: [{ remoteId: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', enabled: true }],
      },
    ],
  })

  assert.deepEqual(refs, [
    {
      id: 'provider_gemini_main::gemini-2.5-flash',
      label: 'Gemini 主账号 / Gemini 2.5 Flash',
      enabled: true,
    },
  ])
})
