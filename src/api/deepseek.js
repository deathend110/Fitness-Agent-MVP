const DEFAULT_BASE_URL = 'https://api.deepseek.com'
const DEFAULT_MODEL = 'deepseek-v4-flash'
const API_KEY_ENV_NAME = 'VITE_DEEPSEEK_API_KEY'

const HTTP_ERROR_MESSAGES = {
  400: '请求参数不合法，请检查发送给 DeepSeek 的消息内容和配置。',
  401: 'DeepSeek API Key 无效或缺失，请检查 .env 中的配置。',
  402: 'DeepSeek 账户余额不足，当前无法完成调用。',
  422: 'DeepSeek 无法处理当前请求内容，请检查消息格式。',
  429: 'DeepSeek 请求过于频繁，请稍后重试。',
  500: 'DeepSeek 服务内部错误，请稍后重试。',
  503: 'DeepSeek 服务暂时不可用，请稍后重试。',
}

export class DeepSeekApiError extends Error {
  constructor(message, options = {}) {
    super(message)
    this.name = 'DeepSeekApiError'
    this.status = options.status ?? null
    this.code = options.code ?? 'deepseek_error'
    this.cause = options.cause
  }
}

function readApiKey(env = {}) {
  const rawValue = env?.[API_KEY_ENV_NAME]
  return typeof rawValue === 'string' ? rawValue.trim() : ''
}

function buildMissingKeyMessage() {
  return `未检测到 ${API_KEY_ENV_NAME}，请在项目根目录的 .env 文件中配置后重启开发服务器。`
}

function readErrorDetail(data) {
  if (!data || typeof data !== 'object') {
    return ''
  }

  if (typeof data.error?.message === 'string') {
    return data.error.message.trim()
  }

  if (typeof data.message === 'string') {
    return data.message.trim()
  }

  return ''
}

function buildHttpErrorMessage(status, detail = '') {
  const baseMessage =
    HTTP_ERROR_MESSAGES[status] ?? `DeepSeek 请求失败（状态码 ${status}），请稍后重试。`

  if (!detail) {
    return `${baseMessage}（HTTP ${status}）`
  }

  return `${baseMessage}（HTTP ${status}）：${detail}`
}

async function readResponseData(response) {
  if (typeof response.json !== 'function') {
    return null
  }

  try {
    return await response.json()
  } catch {
    return null
  }
}

function buildRequestPayload(messages, model, payloadOptions, forceStream = false) {
  return {
    model,
    messages,
    ...payloadOptions,
    ...(forceStream ? { stream: true } : {}),
  }
}

async function performDeepSeekRequest(messages, options = {}, forceStream = false) {
  const {
    apiKey = readApiKey(options.env ?? import.meta.env ?? {}),
    baseUrl = DEFAULT_BASE_URL,
    fetchImpl = globalThis.fetch,
    headers = {},
    model = DEFAULT_MODEL,
    signal,
    ...payloadOptions
  } = options

  if (!apiKey) {
    throw new DeepSeekApiError(buildMissingKeyMessage(), {
      code: 'missing_api_key',
    })
  }

  if (typeof fetchImpl !== 'function') {
    throw new DeepSeekApiError('当前环境不支持 fetch，无法调用 DeepSeek 接口。', {
      code: 'fetch_unavailable',
    })
  }

  try {
    return await fetchImpl(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
        ...headers,
      },
      body: JSON.stringify(buildRequestPayload(messages, model, payloadOptions, forceStream)),
      signal,
    })
  } catch (error) {
    throw new DeepSeekApiError(
      `DeepSeek 网络连接失败，请检查网络后重试：${error.message}`,
      {
        code: 'network_error',
        cause: error,
      },
    )
  }
}

async function assertOkResponse(response) {
  if (response.ok) {
    return
  }

  const data = await readResponseData(response)

  throw new DeepSeekApiError(buildHttpErrorMessage(response.status, readErrorDetail(data)), {
    code: 'http_error',
    status: response.status,
  })
}

function parseStreamLine(line) {
  const trimmedLine = line.trim()

  if (!trimmedLine || trimmedLine.startsWith(':') || !trimmedLine.startsWith('data:')) {
    return null
  }

  return trimmedLine.slice(5).trim()
}

function readDeltaContent(payload) {
  return payload?.choices?.[0]?.delta?.content
}

async function consumeDeepSeekStream(response, onDelta) {
  if (!response.body || typeof response.body.getReader !== 'function') {
    throw new DeepSeekApiError('DeepSeek 流式响应不可读，当前无法使用流式输出。', {
      code: 'stream_unavailable',
    })
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let fullText = ''

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })

    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const data = parseStreamLine(line)

      if (!data) {
        continue
      }

      if (data === '[DONE]') {
        return fullText
      }

      let payload

      try {
        payload = JSON.parse(data)
      } catch (error) {
        throw new DeepSeekApiError('DeepSeek 流式响应解析失败，请稍后重试。', {
          code: 'stream_parse_error',
          cause: error,
        })
      }

      const delta = readDeltaContent(payload)

      if (typeof delta !== 'string' || !delta) {
        continue
      }

      fullText += delta
      onDelta?.(delta, fullText)
    }

    if (done) {
      break
    }
  }

  if (!fullText.trim()) {
    throw new DeepSeekApiError('DeepSeek 流式响应已结束，但没有返回可展示的消息内容。', {
      code: 'empty_content',
    })
  }

  return fullText
}

export function getDeepSeekApiKeyStatus(env = import.meta.env ?? {}) {
  const apiKey = readApiKey(env)

  if (!apiKey) {
    return {
      hasKey: false,
      message: buildMissingKeyMessage(),
    }
  }

  return {
    hasKey: true,
    message: 'DeepSeek API Key 已配置，AI 教练后续可以基于该配置发起调用。',
  }
}

export async function requestDeepSeekChat(messages, options = {}) {
  const response = await performDeepSeekRequest(messages, options)
  await assertOkResponse(response)

  const data = await readResponseData(response)
  const content = data?.choices?.[0]?.message?.content

  if (typeof content !== 'string' || !content.trim()) {
    throw new DeepSeekApiError('DeepSeek 已返回成功响应，但没有可展示的消息内容。', {
      code: 'empty_content',
    })
  }

  return content
}

// DeepSeek 官方流式接口返回 data-only SSE，这里统一负责增量拼接文本。
export async function streamDeepSeekChat(messages, options = {}) {
  const { onDelta, ...requestOptions } = options
  const response = await performDeepSeekRequest(messages, requestOptions, true)
  await assertOkResponse(response)

  return consumeDeepSeekStream(response, onDelta)
}

export const deepSeekDefaults = {
  apiKeyEnvName: API_KEY_ENV_NAME,
  baseUrl: DEFAULT_BASE_URL,
  model: DEFAULT_MODEL,
}
