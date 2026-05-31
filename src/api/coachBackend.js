const DEFAULT_BASE_URL = 'http://127.0.0.1:8000/api'

const HTTP_ERROR_MESSAGES = {
  400: '后端聊天请求参数不合法，请检查发送内容。',
  404: '后端聊天接口不存在，请确认本地后端服务版本。',
  422: '后端未通过聊天消息校验，请检查当前输入。',
  500: '后端聊天服务内部错误，请稍后重试。',
  503: 'AI 教练暂时不可用，请稍后重试。',
}

export class BackendCoachApiError extends Error {
  constructor(message, options = {}) {
    super(message)
    this.name = 'BackendCoachApiError'
    this.status = options.status ?? null
    this.code = options.code ?? 'backend_coach_error'
    this.cause = options.cause
  }
}

function trimTrailingSlash(url = '') {
  return typeof url === 'string' ? url.replace(/\/+$/, '') : DEFAULT_BASE_URL
}

function createRequestUrl(baseUrl, path, query = {}) {
  const url = new URL(`${trimTrailingSlash(baseUrl)}${path}`)

  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }

    url.searchParams.set(key, value)
  })

  return url.toString()
}

function normalizeFileIds(payload = {}) {
  if (Array.isArray(payload.fileIds)) {
    return payload.fileIds.filter(Number.isInteger)
  }

  if (Array.isArray(payload.files)) {
    return payload.files
      .map((file) => (Number.isInteger(file) ? file : file?.id))
      .filter(Number.isInteger)
  }

  return []
}

async function readJsonResponse(response) {
  if (typeof response?.json !== 'function') {
    return null
  }

  try {
    return await response.json()
  } catch {
    return null
  }
}

function readErrorDetail(data) {
  if (!data || typeof data !== 'object') {
    return ''
  }

  if (typeof data.detail === 'string') {
    return data.detail.trim()
  }

  if (typeof data.message === 'string') {
    return data.message.trim()
  }

  return ''
}

function buildHttpErrorMessage(status, detail = '') {
  const baseMessage =
    HTTP_ERROR_MESSAGES[status] ?? `后端聊天请求失败（状态码 ${status}），请稍后重试。`

  return detail ? `${baseMessage}（HTTP ${status}）：${detail}` : `${baseMessage}（HTTP ${status}）`
}

async function assertOkResponse(response) {
  if (response?.ok) {
    return
  }

  const data = await readJsonResponse(response)
  throw new BackendCoachApiError(buildHttpErrorMessage(response?.status, readErrorDetail(data)), {
    code: 'http_error',
    status: response?.status ?? null,
  })
}

function assertFetchAvailable(fetchImpl) {
  if (typeof fetchImpl === 'function') {
    return
  }

  throw new BackendCoachApiError('当前环境不支持 fetch，无法连接后端 AI 教练。', {
    code: 'fetch_unavailable',
  })
}

function normalizeReplyPayload(data) {
  return {
    text: typeof data?.text === 'string' ? data.text : '',
    suggestion: data?.suggestion ?? null,
    proposal: data?.proposal ?? null,
  }
}

function normalizeBackgroundTask(data) {
  return {
    taskId: typeof data?.task_id === 'string' ? data.task_id : data?.taskId || '',
    status: typeof data?.status === 'string' ? data.status : 'unknown',
    result: data?.result ?? null,
    message: typeof data?.message === 'string' ? data.message : '',
  }
}

function parseSseBlock(block) {
  let event = ''
  const dataLines = []

  block.split(/\r?\n/).forEach((line) => {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
      return
    }

    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  })

  if (!event) {
    return null
  }

  try {
    return {
      event,
      data: dataLines.length ? JSON.parse(dataLines.join('\n')) : {},
    }
  } catch (error) {
    throw new BackendCoachApiError('后端流式响应解析失败，请稍后重试。', {
      code: 'stream_parse_error',
      cause: error,
    })
  }
}

function consumeCoachEvent(state, parsedEvent, onDelta) {
  if (!parsedEvent) {
    return false
  }

  const { data, event } = parsedEvent

  if (event === 'delta') {
    const delta = typeof data?.text === 'string' ? data.text : ''

    if (delta) {
      state.fullText += delta
      onDelta?.(delta, state.fullText)
    }

    return false
  }

  if (event === 'suggestion') {
    state.suggestion = data?.suggestion ?? null
    return false
  }

  if (event === 'proposal') {
    state.proposal = data?.proposal ?? null
    return false
  }

  if (event === 'tool_status') {
    state.toolStatus = data ?? null
    return false
  }

  if (event === 'done') {
    state.done = true
    state.finalText = typeof data?.text === 'string' ? data.text : state.fullText
    return true
  }

  if (event === 'error') {
    throw new BackendCoachApiError(data?.message || 'AI 教练暂时不可用，请稍后重试。', {
      code: data?.code || 'stream_error',
    })
  }

  return false
}

export async function requestBackendCoachReply(messages, options = {}) {
  const {
    baseUrl = DEFAULT_BASE_URL,
    fetchImpl = globalThis.fetch,
    model,
    sessionId,
    signal,
  } = options

  assertFetchAvailable(fetchImpl)

  try {
    const body = {
      ...(sessionId === undefined || sessionId === null ? {} : { sessionId }),
      ...(Array.isArray(messages) ? { messages } : normalizeAgentRequestBody(messages)),
      ...(model ? { model } : {}),
    }
    const response = await fetchImpl(createRequestUrl(baseUrl, '/chat/reply'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal,
    })

    await assertOkResponse(response)
    return normalizeReplyPayload(await readJsonResponse(response))
  } catch (error) {
    if (error instanceof BackendCoachApiError) {
      throw error
    }

    throw new BackendCoachApiError(`后端 AI 教练连接失败，请确认本地后端已启动：${error.message}`, {
      code: 'network_error',
      cause: error,
    })
  }
}

export async function streamBackendCoachReply(messages, options = {}) {
  const {
    baseUrl = DEFAULT_BASE_URL,
    fetchImpl = globalThis.fetch,
    model,
    onDelta,
    sessionId,
    signal,
  } = options

  assertFetchAvailable(fetchImpl)

  try {
    const query = Array.isArray(messages)
      ? { messages: JSON.stringify(messages), model, session_id: sessionId }
      : {
          userInput: messages?.userInput,
          model: messages?.model || model,
          session_id: messages?.sessionId ?? sessionId,
          fileIds: normalizeFileIds(messages).join(','),
        }
    const response = await fetchImpl(
      createRequestUrl(baseUrl, '/chat/stream', query),
      {
        method: 'GET',
        signal,
      },
    )

    await assertOkResponse(response)

    if (!response.body || typeof response.body.getReader !== 'function') {
      throw new BackendCoachApiError('后端流式响应不可读，当前无法使用流式输出。', {
        code: 'stream_unavailable',
      })
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    const state = {
      done: false,
      finalText: '',
      fullText: '',
      suggestion: null,
      proposal: null,
      toolStatus: null,
    }
    let buffer = ''

    while (!state.done) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })

      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop() ?? ''

      for (const block of blocks) {
        if (consumeCoachEvent(state, parseSseBlock(block), onDelta)) {
          break
        }
      }

      if (done) {
        break
      }
    }

    if (!state.done) {
      throw new BackendCoachApiError('后端流式响应在完成前中断，已尝试切换普通请求。', {
        code: 'stream_interrupted',
      })
    }

    return {
      text: state.finalText || state.fullText,
      suggestion: state.suggestion,
      proposal: state.proposal,
    }
  } catch (error) {
    if (error instanceof BackendCoachApiError) {
      throw error
    }

    throw new BackendCoachApiError(`后端 AI 教练连接失败，请确认本地后端已启动：${error.message}`, {
      code: 'network_error',
      cause: error,
    })
  }
}

async function resolveBackgroundSessionId({ baseUrl, fetchImpl, sessionId, signal }) {
  if (Number.isInteger(sessionId)) {
    return sessionId
  }

  const response = await fetchImpl(createRequestUrl(baseUrl, '/chat/sessions/default'), {
    method: 'GET',
    signal,
  })

  await assertOkResponse(response)
  const data = await readJsonResponse(response)
  return Number.isInteger(data?.id) ? data.id : null
}

export async function submitBackendCoachBackgroundTask(messages, options = {}) {
  const {
    baseUrl = DEFAULT_BASE_URL,
    fetchImpl = globalThis.fetch,
    model,
    sessionId,
    signal,
  } = options

  assertFetchAvailable(fetchImpl)

  try {
    const payloadSessionId = Array.isArray(messages) ? null : messages?.sessionId
    const resolvedSessionId = await resolveBackgroundSessionId({
      baseUrl,
      fetchImpl,
      sessionId: sessionId ?? payloadSessionId,
      signal,
    })

    if (!Number.isInteger(resolvedSessionId)) {
      throw new BackendCoachApiError('后端默认会话解析失败，暂时无法提交后台思考任务。', {
        code: 'invalid_session',
      })
    }

    const response = await fetchImpl(
      createRequestUrl(baseUrl, `/chat/${resolvedSessionId}/background`),
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...(Array.isArray(messages) ? { messages } : normalizeAgentRequestBody(messages)),
          ...(model ? { model } : {}),
        }),
        keepalive: true,
        signal,
      },
    )

    await assertOkResponse(response)
    const data = await readJsonResponse(response)
    return {
      taskId: typeof data?.task_id === 'string' ? data.task_id : data?.taskId || '',
      sessionId: resolvedSessionId,
    }
  } catch (error) {
    if (error instanceof BackendCoachApiError) {
      throw error
    }

    throw new BackendCoachApiError(`后台思考任务提交失败，请确认本地后端已启动：${error.message}`, {
      code: 'network_error',
      cause: error,
    })
  }
}

export async function requestAgentReplyStream(payload, options = {}) {
  return streamBackendCoachReply(payload, options)
}

function normalizeAgentRequestBody(payload = {}) {
  const fileIds = normalizeFileIds(payload)

  return {
    ...(payload.sessionId === undefined || payload.sessionId === null ? {} : { sessionId: payload.sessionId }),
    userInput: payload.userInput || '',
    ...(payload.model ? { model: payload.model } : {}),
    ...(payload.thinking ? { thinking: payload.thinking } : {}),
    ...(fileIds.length ? { fileIds } : {}),
  }
}

export async function getBackendCoachBackgroundTask(taskId, options = {}) {
  const {
    baseUrl = DEFAULT_BASE_URL,
    fetchImpl = globalThis.fetch,
    signal,
  } = options

  assertFetchAvailable(fetchImpl)

  try {
    const response = await fetchImpl(createRequestUrl(baseUrl, `/chat/background/${taskId}`), {
      method: 'GET',
      signal,
    })

    await assertOkResponse(response)
    return normalizeBackgroundTask(await readJsonResponse(response))
  } catch (error) {
    if (error instanceof BackendCoachApiError) {
      throw error
    }

    throw new BackendCoachApiError(`后台思考任务查询失败，请确认本地后端已启动：${error.message}`, {
      code: 'network_error',
      cause: error,
    })
  }
}

export const coachBackendDefaults = {
  baseUrl: DEFAULT_BASE_URL,
}
