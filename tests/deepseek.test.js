import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getDeepSeekApiKeyStatus,
  requestDeepSeekChat,
  streamDeepSeekChat,
} from '../src/api/deepseek.js'

function createSseBody(chunks) {
  const encoder = new TextEncoder()

  return new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  })
}

test('getDeepSeekApiKeyStatus 在未配置 API Key 时返回明确错误提示', () => {
  const status = getDeepSeekApiKeyStatus({})

  assert.equal(status.hasKey, false)
  assert.match(status.message, /VITE_DEEPSEEK_API_KEY/)
})

test('getDeepSeekApiKeyStatus 在已配置 API Key 时返回可调用状态', () => {
  const status = getDeepSeekApiKeyStatus({
    VITE_DEEPSEEK_API_KEY: 'sk-test',
  })

  assert.equal(status.hasKey, true)
  assert.match(status.message, /已配置/)
})

test('requestDeepSeekChat 在缺少 API Key 时抛出可展示错误', async () => {
  await assert.rejects(
    () => requestDeepSeekChat([{ role: 'user', content: '你好' }], { env: {} }),
    (error) => {
      assert.match(error.message, /VITE_DEEPSEEK_API_KEY/)
      return true
    },
  )
})

test('requestDeepSeekChat 在网络失败时抛出可展示错误', async () => {
  await assert.rejects(
    () =>
      requestDeepSeekChat(
        [{ role: 'user', content: '你好' }],
        {
          env: { VITE_DEEPSEEK_API_KEY: 'sk-test' },
          fetchImpl: async () => {
            throw new Error('socket hang up')
          },
        },
      ),
    (error) => {
      assert.match(error.message, /网络连接失败/)
      assert.match(error.message, /socket hang up/)
      return true
    },
  )
})

test('requestDeepSeekChat 在非 2xx 响应时抛出带状态码的错误', async () => {
  await assert.rejects(
    () =>
      requestDeepSeekChat(
        [{ role: 'user', content: '你好' }],
        {
          env: { VITE_DEEPSEEK_API_KEY: 'sk-test' },
          fetchImpl: async () => ({
            ok: false,
            status: 401,
            json: async () => ({
              error: {
                message: 'Authentication failed',
              },
            }),
          }),
        },
      ),
    (error) => {
      assert.match(error.message, /401/)
      assert.match(error.message, /API Key/)
      assert.match(error.message, /Authentication failed/)
      return true
    },
  )
})

test('requestDeepSeekChat 在成功时返回首条消息 content', async () => {
  const content = await requestDeepSeekChat(
    [{ role: 'user', content: '给我今天的训练建议' }],
    {
      env: { VITE_DEEPSEEK_API_KEY: 'sk-test' },
      fetchImpl: async () => ({
        ok: true,
        json: async () => ({
          choices: [
            {
              message: {
                content: '今天建议把深蹲降到 70%。',
              },
            },
          ],
        }),
      }),
    },
  )

  assert.equal(content, '今天建议把深蹲降到 70%。')
})

test('streamDeepSeekChat 会按 SSE 增量拼接文本并回调 onDelta', async () => {
  const deltas = []

  const content = await streamDeepSeekChat(
    [{ role: 'user', content: '给我今天的训练建议' }],
    {
      env: { VITE_DEEPSEEK_API_KEY: 'sk-test' },
      fetchImpl: async () => ({
        ok: true,
        body: createSseBody([
          ': keep-alive\n\n',
          'data: {"choices":[{"delta":{"content":"先把"}}]}\n\n',
          'data: {"choices":[{"delta":{"content":"周一主项降一点。"}}]}\n\n',
          'data: [DONE]\n\n',
        ]),
      }),
      onDelta: (delta, fullText) => {
        deltas.push({ delta, fullText })
      },
    },
  )

  assert.equal(content, '先把周一主项降一点。')
  assert.deepEqual(deltas, [
    { delta: '先把', fullText: '先把' },
    { delta: '周一主项降一点。', fullText: '先把周一主项降一点。' },
  ])
})
