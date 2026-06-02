import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  deepSeekDefaults,
  getDeepSeekApiKeyStatus,
  requestDeepSeekChat,
  streamDeepSeekChat,
} from '../src/api/deepseek.js'

test('getDeepSeekApiKeyStatus 提示密钥已迁移到后端', () => {
  const status = getDeepSeekApiKeyStatus({})

  assert.equal(status.hasKey, true)
  assert.match(status.message, /后端/)
})

test('requestDeepSeekChat 通过后端代理返回文本，兼容旧调用方', async () => {
  const content = await requestDeepSeekChat([{ role: 'user', content: '你好' }], {
    requestImpl: async (messages) => {
      assert.deepEqual(messages, [{ role: 'user', content: '你好' }])
      return {
        text: '今天建议降低一点训练量。',
        suggestion: null,
      }
    },
  })

  assert.equal(content, '今天建议降低一点训练量。')
})

test('streamDeepSeekChat 通过后端 SSE 代理回调增量文本，兼容旧调用方', async () => {
  const deltas = []

  const content = await streamDeepSeekChat([{ role: 'user', content: '你好' }], {
    streamImpl: async (messages, { onDelta }) => {
      assert.deepEqual(messages, [{ role: 'user', content: '你好' }])
      onDelta('今天', '今天')
      onDelta('轻一点。', '今天轻一点。')
      return {
        text: '今天轻一点。',
        suggestion: null,
      }
    },
    onDelta: (delta, fullText) => {
      deltas.push({ delta, fullText })
    },
  })

  assert.equal(content, '今天轻一点。')
  assert.deepEqual(deltas, [
    { delta: '今天', fullText: '今天' },
    { delta: '轻一点。', fullText: '今天轻一点。' },
  ])
})

test('deepSeekDefaults 不再暴露前端密钥环境名或 DeepSeek 直连地址', () => {
  assert.equal(deepSeekDefaults.baseUrl, 'http://127.0.0.1:8000/api')
  assert.equal('apiKeyEnvName' in deepSeekDefaults, false)
})

test('deepseek.js 继续作为兼容壳转发到 coachBackend，而不是自带独立请求主逻辑', () => {
  const source = readFileSync('src/api/deepseek.js', 'utf-8')

  assert.match(source, /requestBackendCoachReply/)
  assert.match(source, /streamBackendCoachReply/)
  assert.match(source, /兼容旧导入/)
  assert.doesNotMatch(source, /fetch\(/)
})
