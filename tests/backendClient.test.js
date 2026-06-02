import assert from 'node:assert/strict'
import test from 'node:test'

import {
  BackendApiError,
  createBackendClient,
  resolveBackendApiBaseUrl,
} from '../src/api/backendClient.js'
import {
  fromBackendDailyLog,
  fromBackendProfile,
  isSameAppDataSnapshot,
  saveDailyLog,
  toBackendDailyLog,
  toBackendProfile,
} from '../src/api/appData.js'

test('createBackendClient 会使用 JSON POST/PUT/GET 调用约定接口', async () => {
  const requests = []
  const client = createBackendClient({
    baseUrl: 'http://127.0.0.1:8000/api',
    fetchImpl: async (url, options) => {
      requests.push({ url, options })

      return {
        ok: true,
        json: async () => ({ ok: true }),
      }
    },
  })

  await client.getProfile()
  await client.updateProfile({ name: 'Ada', oneRm: { squat: 120 } })
  await client.adoptWeeklyPlanChange({
    day: 'Monday',
    changes: [{ action: 'update', exerciseName: '深蹲', field: 'pct', newValue: 0.7 }],
  })
  await client.commitCoachSuggestion({
    proposalId: 'proposal-compat-1',
    day: 'Monday',
    changes: [{ action: 'update', exerciseName: '深蹲', field: 'pct', newValue: 0.7 }],
  })
  await client.commitCoachSuggestion({
    day: 'Tuesday',
    changes: [{ action: 'update', exerciseName: '卧推', field: 'pct', newValue: 0.72 }],
  })
  await client.proposePlanChange({
    sessionId: 1,
    day: 'Monday',
    summary: '降低深蹲强度',
    changes: [{ action: 'update', exerciseName: '深蹲', field: 'pct', newValue: 0.7 }],
  })
  await client.commitPlanChange({ proposalId: 'proposal-1' })
  await client.updateDailyLogEntry('2026-05-31', { tdeeManual: 2600 })
  await client.getModels()
  await client.getDefaultChatSession()
  await client.getChatSessions()
  await client.createChatSession({ title: '训练复盘' })
  await client.deleteChatSession(12)
  await client.getChatMessages(12)
  await client.getFile(99)
  await client.getCoachDraft(12)
  await client.saveCoachDraft(12, { content: 'hello', attachedFileIds: [1] })
  await client.getDailyMetricsSummary({ date: '2026-06-01' })

  assert.equal(requests[0].url, 'http://127.0.0.1:8000/api/profile')
  assert.equal(requests[0].options.method, 'GET')
  assert.equal(requests[1].url, 'http://127.0.0.1:8000/api/profile')
  assert.equal(requests[1].options.method, 'PUT')
  assert.equal(requests[1].options.headers['Content-Type'], 'application/json')
  assert.deepEqual(JSON.parse(requests[1].options.body), {
    name: 'Ada',
    oneRm: { squat: 120 },
  })
  assert.equal(requests[2].url, 'http://127.0.0.1:8000/api/weekly-plan/adopt')
  assert.equal(requests[2].options.method, 'POST')
  assert.deepEqual(JSON.parse(requests[2].options.body), {
    day: 'Monday',
    changes: [{ action: 'update', exerciseName: '深蹲', field: 'pct', newValue: 0.7 }],
  })
  assert.equal(requests[3].url, 'http://127.0.0.1:8000/api/tools/plan/commit')
  assert.equal(requests[3].options.method, 'POST')
  assert.deepEqual(JSON.parse(requests[3].options.body), { proposalId: 'proposal-compat-1' })
  assert.equal(requests[4].url, 'http://127.0.0.1:8000/api/weekly-plan/adopt')
  assert.equal(requests[4].options.method, 'POST')
  assert.deepEqual(JSON.parse(requests[4].options.body), {
    day: 'Tuesday',
    changes: [{ action: 'update', exerciseName: '卧推', field: 'pct', newValue: 0.72 }],
  })
  assert.equal(requests[5].url, 'http://127.0.0.1:8000/api/tools/plan/propose')
  assert.equal(requests[5].options.method, 'POST')
  assert.equal(requests[6].url, 'http://127.0.0.1:8000/api/tools/plan/commit')
  assert.deepEqual(JSON.parse(requests[6].options.body), { proposalId: 'proposal-1' })
  assert.equal(requests[7].url, 'http://127.0.0.1:8000/api/daily-log/2026-05-31')
  assert.equal(requests[7].options.method, 'PUT')
  assert.deepEqual(JSON.parse(requests[7].options.body), { tdeeManual: 2600 })
  assert.equal(requests[8].url, 'http://127.0.0.1:8000/api/models')
  assert.equal(requests[8].options.method, 'GET')
  assert.equal(requests[9].url, 'http://127.0.0.1:8000/api/chat/sessions/default')
  assert.equal(requests[10].url, 'http://127.0.0.1:8000/api/chat/sessions')
  assert.equal(requests[10].options.method, 'GET')
  assert.equal(requests[11].url, 'http://127.0.0.1:8000/api/chat/sessions')
  assert.equal(requests[11].options.method, 'POST')
  assert.deepEqual(JSON.parse(requests[11].options.body), { title: '训练复盘' })
  assert.equal(requests[12].url, 'http://127.0.0.1:8000/api/chat/sessions/12')
  assert.equal(requests[12].options.method, 'DELETE')
  assert.equal(requests[13].url, 'http://127.0.0.1:8000/api/chat/sessions/12/messages')
  assert.equal(requests[13].options.method, 'GET')
  assert.equal(requests[14].url, 'http://127.0.0.1:8000/api/files/99')
  assert.equal(requests[15].url, 'http://127.0.0.1:8000/api/chat/sessions/12/draft')
  assert.equal(requests[16].url, 'http://127.0.0.1:8000/api/chat/sessions/12/draft')
  assert.equal(requests[16].options.method, 'PUT')
  assert.deepEqual(JSON.parse(requests[16].options.body), { content: 'hello', attachedFileIds: [1] })
  assert.equal(requests[17].url, 'http://127.0.0.1:8000/api/metrics/daily-summary?date=2026-06-01')
})

test('commitCoachSuggestion 会优先走 proposal commit，缺少 proposalId 时才回退 legacy adopt', async () => {
  const requests = []
  const client = createBackendClient({
    baseUrl: 'http://127.0.0.1:8000/api',
    fetchImpl: async (url, options) => {
      requests.push({ url, options })
      return {
        ok: true,
        json: async () => ({ ok: true, plan: {} }),
      }
    },
  })

  await client.commitCoachSuggestion({
    proposalId: 'proposal-123',
    day: 'Monday',
    changes: [{ action: 'update', exerciseName: '深蹲', field: 'pct', newValue: 0.68 }],
  })
  await client.commitCoachSuggestion({
    day: 'Tuesday',
    changes: [{ action: 'update', exerciseName: '卧推', field: 'pct', newValue: 0.72 }],
  })

  assert.equal(requests[0].url, 'http://127.0.0.1:8000/api/tools/plan/commit')
  assert.deepEqual(JSON.parse(requests[0].options.body), { proposalId: 'proposal-123' })
  assert.equal(requests[1].url, 'http://127.0.0.1:8000/api/weekly-plan/adopt')
  assert.deepEqual(JSON.parse(requests[1].options.body), {
    day: 'Tuesday',
    changes: [{ action: 'update', exerciseName: '卧推', field: 'pct', newValue: 0.72 }],
  })
})

test('createBackendClient 会把 HTTP 错误归一成可展示异常', async () => {
  const client = createBackendClient({
    fetchImpl: async () => ({
      ok: false,
      status: 503,
      json: async () => ({
        detail: 'database unavailable',
      }),
    }),
  })

  await assert.rejects(
    () => client.getWeeklyPlan(),
    (error) => {
      assert.equal(error instanceof BackendApiError, true)
      assert.equal(error.status, 503)
      assert.equal(error.code, 'http_error')
      assert.match(error.message, /503/)
      assert.match(error.message, /database unavailable/)
      return true
    },
  )
})

test('createBackendClient 会把网络异常归一成统一错误', async () => {
  const client = createBackendClient({
    fetchImpl: async () => {
      throw new Error('connect ECONNREFUSED')
    },
  })

  await assert.rejects(
    () => client.getDailyLog(),
    (error) => {
      assert.equal(error instanceof BackendApiError, true)
      assert.equal(error.code, 'network_error')
      assert.match(error.message, /后端服务连接失败/)
      assert.match(error.message, /ECONNREFUSED/)
      return true
    },
  )
})

test('resolveBackendApiBaseUrl 会优先读取 env 中的 VITE_API_BASE_URL 并保留本地默认兜底', () => {
  assert.equal(
    resolveBackendApiBaseUrl({ VITE_API_BASE_URL: 'http://127.0.0.1:9321/api/' }),
    'http://127.0.0.1:9321/api',
  )

  assert.equal(
    resolveBackendApiBaseUrl({ VITE_API_BASE_URL: '   ' }),
    'http://127.0.0.1:8000/api',
  )

  assert.equal(resolveBackendApiBaseUrl(undefined), 'http://127.0.0.1:8000/api')
})

test('appData 会在前后端 profile 字段之间做 oneRM / oneRm 映射', () => {
  const profile = fromBackendProfile({
    name: 'Ada',
    oneRm: {
      squat: 100,
      bench: 70,
      deadlift: 130,
    },
  })

  assert.deepEqual(profile.oneRM, {
    squat: 100,
    bench: 70,
    deadlift: 130,
  })

  assert.deepEqual(
    toBackendProfile({
      name: 'Ada',
      oneRM: {
        squat: 105,
        bench: 72.5,
      },
    }),
    {
      name: 'Ada',
      oneRm: {
        squat: 105,
        bench: 72.5,
      },
    },
  )
})

test('appData 会在前后端 dailyLog 字段之间做 tdee / tdeeManual 映射', () => {
  const dailyLog = fromBackendDailyLog({
    '2026-05-31': {
      weight: 80.2,
      tdeeManual: 2550,
      note: 'deload',
    },
  })

  assert.deepEqual(dailyLog, {
    '2026-05-31': {
      weight: 80.2,
      tdee: 2550,
      note: 'deload',
    },
  })

  assert.deepEqual(
    toBackendDailyLog({
      '2026-06-01': {
        weight: 79.8,
        tdee: 2400,
        note: 'sleepy',
      },
    }),
    {
      '2026-06-01': {
        weight: 79.8,
        tdeeManual: 2400,
        note: 'sleepy',
      },
    },
  )
})

test('isSameAppDataSnapshot 会判断对象快照是否真的变化', () => {
  assert.equal(
    isSameAppDataSnapshot(
      { basic: { name: 'Ada' }, oneRM: { squat: 100 } },
      { basic: { name: 'Ada' }, oneRM: { squat: 100 } },
    ),
    true,
  )

  assert.equal(
    isSameAppDataSnapshot(
      { basic: { name: 'Ada' }, oneRM: { squat: 100 } },
      { basic: { name: 'Ada' }, oneRM: { squat: 102.5 } },
    ),
    false,
  )
})

test('saveDailyLog 只会把相对上次后端快照发生变化的日期写回后端', async () => {
  const calls = []
  const client = {
    updateDailyLogEntry: async (date, payload) => {
      calls.push({ date, payload })
      return payload
    },
  }

  await saveDailyLog(
    {
      '2026-06-01': { weight: 80, tdee: 2500 },
      '2026-06-02': { weight: 79.8, tdee: 2450 },
    },
    {
      client,
      previousDailyLog: {
        '2026-06-01': { weight: 80, tdee: 2500 },
        '2026-06-02': { weight: 79.6, tdee: 2450 },
      },
    },
  )

  assert.deepEqual(calls, [
    {
      date: '2026-06-02',
      payload: { weight: 79.8, tdeeManual: 2450 },
    },
  ])
})
