import assert from 'node:assert/strict'
import test from 'node:test'

import {
  BackendCoachApiError,
  getBackendCoachBackgroundTask,
  requestBackendCoachReply,
  submitBackendCoachBackgroundTask,
  streamBackendCoachReply,
} from '../src/api/coachBackend.js'

function createSseBody(chunks) {
  const encoder = new TextEncoder()

  return new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  })
}

test('streamBackendCoachReply 会解析后端 SSE 事件并返回文本和 suggestion', async () => {
  const deltas = []
  const messages = [{ role: 'user', content: '今天深蹲很累' }]

  const reply = await streamBackendCoachReply(messages, {
    baseUrl: 'http://backend.test/api',
    sessionId: 7,
    fetchImpl: async (url, options) => {
      assert.equal(options.method, 'GET')
      assert.match(url, /^http:\/\/backend\.test\/api\/chat\/stream\?/)

      const requestUrl = new URL(url)
      assert.equal(requestUrl.searchParams.get('session_id'), '7')
      assert.deepEqual(JSON.parse(requestUrl.searchParams.get('messages')), messages)

      return {
        ok: true,
        body: createSseBody([
          'event: delta\ndata: {"text":"建议"}\n\n',
          'event: delta\ndata: {"text":"降低硬拉强度。"}\n\n',
          'event: suggestion\ndata: {"suggestion":{"day":"Friday","summary":"降强度"}}\n\n',
          'event: done\ndata: {"text":"建议降低硬拉强度。"}\n\n',
        ]),
        headers: new Headers({ 'content-type': 'text/event-stream' }),
      }
    },
    onDelta: (delta, fullText) => {
      deltas.push({ delta, fullText })
    },
  })

  assert.deepEqual(deltas, [
    { delta: '建议', fullText: '建议' },
    { delta: '降低硬拉强度。', fullText: '建议降低硬拉强度。' },
  ])
  assert.deepEqual(reply, {
    text: '建议降低硬拉强度。',
    suggestion: { day: 'Friday', summary: '降强度' },
  })
})

test('streamBackendCoachReply 收到 error 事件时抛出友好异常', async () => {
  await assert.rejects(
    () =>
      streamBackendCoachReply([{ role: 'user', content: '你好' }], {
        fetchImpl: async () => ({
          ok: true,
          body: createSseBody([
            'event: error\ndata: {"code":"missing_api_key","message":"未配置后端 DeepSeek API Key"}\n\n',
          ]),
          headers: new Headers({ 'content-type': 'text/event-stream' }),
        }),
      }),
    (error) => {
      assert.equal(error instanceof BackendCoachApiError, true)
      assert.equal(error.code, 'missing_api_key')
      assert.match(error.message, /DeepSeek API Key/)
      return true
    },
  )
})

test('requestBackendCoachReply 使用后端非流式代理返回解析后的回复', async () => {
  const messages = [{ role: 'user', content: '给我建议' }]

  const reply = await requestBackendCoachReply(messages, {
    baseUrl: 'http://backend.test/api',
    sessionId: 3,
    fetchImpl: async (url, options) => {
      assert.equal(url, 'http://backend.test/api/chat/reply')
      assert.equal(options.method, 'POST')
      assert.deepEqual(JSON.parse(options.body), {
        sessionId: 3,
        messages,
      })

      return {
        ok: true,
        json: async () => ({
          text: '今天降低一点容量。',
          suggestion: null,
        }),
      }
    },
  })

  assert.deepEqual(reply, {
    text: '今天降低一点容量。',
    suggestion: null,
  })
})

test('submitBackendCoachBackgroundTask 会提交后台任务并在缺省会话时先解析默认 session', async () => {
  const calls = []
  const messages = [{ role: 'user', content: '离页后继续想' }]

  const result = await submitBackendCoachBackgroundTask(messages, {
    baseUrl: 'http://backend.test/api',
    fetchImpl: async (url, options = {}) => {
      calls.push({ url, options })

      if (url === 'http://backend.test/api/chat/sessions/default') {
        return {
          ok: true,
          json: async () => ({ id: 12 }),
        }
      }

      assert.equal(url, 'http://backend.test/api/chat/12/background')
      assert.equal(options.method, 'POST')
      assert.equal(options.keepalive, true)
      assert.deepEqual(JSON.parse(options.body), { messages })

      return {
        ok: true,
        json: async () => ({ task_id: 'task-1' }),
      }
    },
  })

  assert.deepEqual(result, { taskId: 'task-1', sessionId: 12 })
  assert.equal(calls.length, 2)
})

test('getBackendCoachBackgroundTask 会查询后台任务状态并归一化 result', async () => {
  const result = await getBackendCoachBackgroundTask('task-1', {
    baseUrl: 'http://backend.test/api',
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, 'http://backend.test/api/chat/background/task-1')
      assert.equal(options.method, 'GET')
      return {
        ok: true,
        json: async () => ({
          task_id: 'task-1',
          status: 'succeeded',
          result: {
            text: '后台回复',
            suggestion: { day: 'Friday' },
          },
          message: '',
        }),
      }
    },
  })

  assert.deepEqual(result, {
    taskId: 'task-1',
    status: 'succeeded',
    result: {
      text: '后台回复',
      suggestion: { day: 'Friday' },
    },
    message: '',
  })
})
