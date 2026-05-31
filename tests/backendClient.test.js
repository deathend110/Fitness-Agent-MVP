import assert from 'node:assert/strict'
import test from 'node:test'

import {
  BackendApiError,
  createBackendClient,
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
  await client.updateDailyLogEntry('2026-05-31', { tdeeManual: 2600 })

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
  assert.equal(requests[3].url, 'http://127.0.0.1:8000/api/daily-log/2026-05-31')
  assert.equal(requests[3].options.method, 'PUT')
  assert.deepEqual(JSON.parse(requests[3].options.body), { tdeeManual: 2600 })
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
