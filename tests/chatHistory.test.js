import assert from 'node:assert/strict'
import test from 'node:test'

import {
  appendChatMessages,
  CHAT_HISTORY_LIMIT,
} from '../src/utils/chatHistory.js'

test('appendChatMessages 会按顺序追加消息', () => {
  const nextHistory = appendChatMessages(
    [{ role: 'user', content: '第一句' }],
    [{ role: 'assistant', content: '第二句' }],
  )

  assert.deepEqual(nextHistory, [
    { role: 'user', content: '第一句' },
    { role: 'assistant', content: '第二句' },
  ])
})

test('appendChatMessages 只保留最近 20 条消息', () => {
  const history = Array.from({ length: CHAT_HISTORY_LIMIT }, (_, index) => ({
    role: index % 2 === 0 ? 'user' : 'assistant',
    content: `消息-${index + 1}`,
  }))

  const nextHistory = appendChatMessages(history, [
    { role: 'user', content: '最新消息' },
  ])

  assert.equal(nextHistory.length, CHAT_HISTORY_LIMIT)
  assert.equal(nextHistory[0].content, '消息-2')
  assert.equal(nextHistory.at(-1).content, '最新消息')
})
