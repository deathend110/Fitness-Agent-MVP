import assert from 'node:assert/strict'
import test from 'node:test'

import {
  BackendCoachApiError,
  getBackendCoachBackgroundTask,
  requestBackendCoachReply,
  resolveCoachBackendBaseUrl,
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
      assert.equal(url, 'http://backend.test/api/chat/stream')
      assert.equal(options.method, 'POST')
      assert.equal(options.headers['Content-Type'], 'application/json')
      assert.deepEqual(JSON.parse(options.body), {
        sessionId: 7,
        messages,
      })

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
    proposal: null,
  })
})

test('streamBackendCoachReply 支持 Agent 请求契约并解析 proposal/tool_status 事件', async () => {
  const toolStatuses = []
  const proposals = []
  const reply = await streamBackendCoachReply(
    { sessionId: 8, userInput: '读取计划再建议', model: 'deepseek-chat', thinking: { enabled: true, budget: 'max' }, fileIds: [2, 5] },
    {
      baseUrl: 'http://backend.test/api',
      fetchImpl: async (url, options) => {
        assert.equal(url, 'http://backend.test/api/chat/stream')
        assert.equal(options.method, 'POST')
        assert.equal(options.headers['Content-Type'], 'application/json')
        assert.deepEqual(JSON.parse(options.body), {
          sessionId: 8,
          userInput: '读取计划再建议',
          model: 'deepseek-chat',
          thinking: { enabled: true, budget: 'max' },
          fileIds: [2, 5],
        })

        return {
          ok: true,
          body: createSseBody([
            'event: tool_status\ndata: {"tool":"get_weekly_plan","status":"running"}\n\n',
            'event: delta\ndata: {"text":"建议保守调整。"}\n\n',
            'event: proposal\ndata: {"proposal":{"proposalId":"p1","day":"Monday"}}\n\n',
            'event: done\ndata: {"text":"建议保守调整。"}\n\n',
          ]),
          headers: new Headers({ 'content-type': 'text/event-stream' }),
        }
      },
      onProposal: (proposal) => {
        proposals.push(proposal)
      },
      onToolStatus: (toolStatus) => {
        toolStatuses.push(toolStatus)
      },
    },
  )

  assert.deepEqual(toolStatuses, [{ tool: 'get_weekly_plan', status: 'running' }])
  assert.deepEqual(proposals, [{ proposalId: 'p1', day: 'Monday' }])
  assert.deepEqual(reply, {
    text: '建议保守调整。',
    suggestion: null,
    proposal: { proposalId: 'p1', day: 'Monday' },
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
    proposal: null,
  })
})

test('requestBackendCoachReply 支持 Agent 非流式请求体', async () => {
  const reply = await requestBackendCoachReply(
    { sessionId: 3, userInput: '给我建议', model: 'deepseek-chat', thinking: { enabled: true, budget: 'auto' }, fileIds: [11] },
    {
      baseUrl: 'http://backend.test/api',
      fetchImpl: async (_url, options) => {
        assert.deepEqual(JSON.parse(options.body), {
          sessionId: 3,
          userInput: '给我建议',
          model: 'deepseek-chat',
          thinking: { enabled: true, budget: 'auto' },
          fileIds: [11],
        })
        return {
          ok: true,
          json: async () => ({ text: '后端编排回复', suggestion: null, proposal: null }),
        }
      },
    },
  )

  assert.equal(reply.text, '后端编排回复')
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

test('submitBackendCoachBackgroundTask 支持 Agent 后台请求契约', async () => {
  const result = await submitBackendCoachBackgroundTask(
    { sessionId: 12, userInput: '离页后继续想', thinking: { enabled: true, budget: 'max' }, fileIds: [3] },
    {
      baseUrl: 'http://backend.test/api',
      fetchImpl: async (url, options = {}) => {
        assert.equal(url, 'http://backend.test/api/chat/12/background')
        assert.deepEqual(JSON.parse(options.body), {
          userInput: '离页后继续想',
          sessionId: 12,
          thinking: { enabled: true, budget: 'max' },
          fileIds: [3],
        })
        return { ok: true, json: async () => ({ task_id: 'task-2' }) }
      },
    },
  )

  assert.deepEqual(result, { taskId: 'task-2', sessionId: 12 })
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

test('resolveCoachBackendBaseUrl 会复用统一 env 配置并在缺失时回退本地默认值', () => {
  assert.equal(
    resolveCoachBackendBaseUrl({ VITE_API_BASE_URL: 'http://localhost:9000/api/' }),
    'http://localhost:9000/api',
  )

  assert.equal(resolveCoachBackendBaseUrl({}), 'http://127.0.0.1:8000/api')
})
