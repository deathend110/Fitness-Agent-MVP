import {
  coachBackendDefaults,
  requestBackendCoachReply,
  streamBackendCoachReply,
} from './coachBackend.js'

export class DeepSeekApiError extends Error {
  constructor(message, options = {}) {
    super(message)
    this.name = 'DeepSeekApiError'
    this.status = options.status ?? null
    this.code = options.code ?? 'deepseek_proxy_error'
    this.cause = options.cause
  }
}

export function getDeepSeekApiKeyStatus() {
  return {
    hasKey: true,
    message: 'DeepSeek API Key 已迁移到后端 .env；前端只通过本地后端代理发起 AI 教练请求。',
  }
}

function wrapProxyError(error) {
  if (error instanceof DeepSeekApiError) {
    return error
  }

  return new DeepSeekApiError(error?.message || '后端 AI 教练代理暂时不可用，请稍后重试。', {
    code: error?.code || 'backend_proxy_error',
    status: error?.status ?? null,
    cause: error,
  })
}

// 兼容旧导入：旧函数名仍返回纯文本，但实际调用已经改为后端代理。
export async function requestDeepSeekChat(messages, options = {}) {
  const { requestImpl = requestBackendCoachReply, ...requestOptions } = options

  try {
    const reply = await requestImpl(messages, requestOptions)
    return reply?.text ?? ''
  } catch (error) {
    throw wrapProxyError(error)
  }
}

// 兼容旧导入：旧流式函数仍回调 delta/fullText 并返回纯文本。
export async function streamDeepSeekChat(messages, options = {}) {
  const { onDelta, streamImpl = streamBackendCoachReply, ...requestOptions } = options

  try {
    const reply = await streamImpl(messages, {
      ...requestOptions,
      onDelta,
    })
    return reply?.text ?? ''
  } catch (error) {
    throw wrapProxyError(error)
  }
}

export const deepSeekDefaults = {
  baseUrl: coachBackendDefaults.baseUrl,
  model: 'backend-default',
}
