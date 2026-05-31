const DEFAULT_BASE_URL = 'http://127.0.0.1:8000/api'

const HTTP_ERROR_MESSAGES = {
  400: '后端请求参数不合法，请检查提交的数据内容。',
  404: '后端接口不存在，请确认后端服务版本与当前前端匹配。',
  422: '后端未通过数据校验，请检查当前页面提交内容。',
  500: '后端服务内部错误，请稍后重试。',
  503: '后端服务暂时不可用，请稍后重试。',
}

export class BackendApiError extends Error {
  constructor(message, options = {}) {
    super(message)
    this.name = 'BackendApiError'
    this.status = options.status ?? null
    this.code = options.code ?? 'backend_error'
    this.cause = options.cause
  }
}

function trimTrailingSlash(url = '') {
  return typeof url === 'string' ? url.replace(/\/+$/, '') : DEFAULT_BASE_URL
}

function readErrorDetail(data) {
  if (!data || typeof data !== 'object') {
    return ''
  }

  if (typeof data.detail === 'string') {
    return data.detail.trim()
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => item?.msg)
      .filter((item) => typeof item === 'string' && item.trim())
      .join('；')
  }

  if (typeof data.message === 'string') {
    return data.message.trim()
  }

  return ''
}

function buildHttpErrorMessage(status, detail = '') {
  const baseMessage =
    HTTP_ERROR_MESSAGES[status] ?? `后端请求失败（状态码 ${status}），请稍后重试。`

  return detail ? `${baseMessage}（HTTP ${status}）：${detail}` : `${baseMessage}（HTTP ${status}）`
}

async function readResponseData(response) {
  if (typeof response?.json !== 'function') {
    return null
  }

  try {
    return await response.json()
  } catch {
    return null
  }
}

async function assertOkResponse(response) {
  if (response?.ok) {
    return
  }

  const data = await readResponseData(response)
  throw new BackendApiError(buildHttpErrorMessage(response?.status, readErrorDetail(data)), {
    code: 'http_error',
    status: response?.status ?? null,
  })
}

function createRequestUrl(baseUrl, path, query) {
  const url = new URL(`${trimTrailingSlash(baseUrl)}${path}`)

  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }

    url.searchParams.set(key, value)
  })

  return url.toString()
}

export function createBackendClient(options = {}) {
  const {
    baseUrl = DEFAULT_BASE_URL,
    fetchImpl = globalThis.fetch,
    headers = {},
  } = options

  if (typeof fetchImpl !== 'function') {
    throw new BackendApiError('当前环境不支持 fetch，无法连接后端服务。', {
      code: 'fetch_unavailable',
    })
  }

  async function request(path, requestOptions = {}) {
    const { body, method = 'GET', query, signal } = requestOptions

    try {
      const response = await fetchImpl(createRequestUrl(baseUrl, path, query), {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        signal,
      })

      await assertOkResponse(response)
      return readResponseData(response)
    } catch (error) {
      if (error instanceof BackendApiError) {
        throw error
      }

      throw new BackendApiError(`后端服务连接失败，请确认本地后端已启动：${error.message}`, {
        code: 'network_error',
        cause: error,
      })
    }
  }

  return {
    getProfile({ signal } = {}) {
      return request('/profile', { signal })
    },
    updateProfile(payload, { signal } = {}) {
      return request('/profile', { method: 'PUT', body: payload, signal })
    },
    getWeeklyPlan({ signal } = {}) {
      return request('/weekly-plan', { signal })
    },
    updateWeeklyPlan(payload, { signal } = {}) {
      return request('/weekly-plan', { method: 'PUT', body: payload, signal })
    },
    adoptWeeklyPlanChange(payload, { signal } = {}) {
      return request('/weekly-plan/adopt', { method: 'POST', body: payload, signal })
    },
    proposePlanChange(payload, { signal } = {}) {
      return request('/tools/plan/propose', { method: 'POST', body: payload, signal })
    },
    commitPlanChange(payload, { signal } = {}) {
      return request('/tools/plan/commit', { method: 'POST', body: payload, signal })
    },
    getDailyLog(query = {}, { signal } = {}) {
      return request('/daily-log', { query, signal })
    },
    updateDailyLogEntry(date, payload, { signal } = {}) {
      return request(`/daily-log/${date}`, { method: 'PUT', body: payload, signal })
    },
  }
}

export const backendClientDefaults = {
  baseUrl: DEFAULT_BASE_URL,
}
