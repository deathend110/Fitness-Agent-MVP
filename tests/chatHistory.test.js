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
    { role: 'user', content: '第一句', attachments: [] },
    { role: 'assistant', content: '第二句', attachments: [] },
  ])
})

test('appendChatMessages 只保留最近 20 条消息', () => {
  const history = Array.from({ length: CHAT_HISTORY_LIMIT }, (_, index) => ({
    role: index % 2 === 0 ? 'user' : 'assistant',
    content: `消息-${index + 1}`,
    attachments: index === 0 ? [{ fileId: 7, originalName: '减脂容量型计划.xlsx' }] : [],
  }))

  const nextHistory = appendChatMessages(history, [
    { role: 'user', content: '最新消息' },
  ])

  assert.equal(nextHistory.length, CHAT_HISTORY_LIMIT)
  assert.equal(nextHistory[0].content, '消息-2')
  assert.deepEqual(nextHistory[0].attachments, [])
  assert.equal(nextHistory.at(-1).content, '最新消息')
  assert.deepEqual(nextHistory.at(-1).attachments, [])
})

test('appendChatMessages 会保留 assistant 消息上的 suggestion 对象', () => {
  const suggestion = {
    proposalId: 'proposal-1',
    summary: '降低周一深蹲强度',
    day: 'Monday',
    changes: [{ action: 'update', exerciseName: '深蹲', field: 'pct', newValue: 0.7 }],
  }

  const nextHistory = appendChatMessages([], [
    { role: 'assistant', content: '建议调整训练计划。', suggestion },
  ])

  assert.deepEqual(nextHistory[0], {
    role: 'assistant',
    content: '建议调整训练计划。',
    suggestion,
    attachments: [],
  })
})

test('appendChatMessages 裁剪历史时仍保留剩余消息上的 suggestion 对象', () => {
  const history = Array.from({ length: CHAT_HISTORY_LIMIT }, (_, index) => ({
    role: index % 2 === 0 ? 'user' : 'assistant',
    content: `消息-${index + 1}`,
    attachments: index === 1 ? [{ fileId: 7, originalName: '减脂容量型计划.xlsx' }] : [],
  }))
  const suggestion = {
    day: 'Tuesday',
    changes: [{ action: 'add', exercise: { name: '暂停深蹲', sets: 2, reps: 8 } }],
  }

  const nextHistory = appendChatMessages(history, [
    { role: 'assistant', content: '新增一个技术动作。', suggestion },
  ])

  assert.equal(nextHistory.length, CHAT_HISTORY_LIMIT)
  assert.deepEqual(nextHistory.at(-1), {
    role: 'assistant',
    content: '新增一个技术动作。',
    suggestion,
    attachments: [],
  })
  assert.deepEqual(nextHistory[0].attachments, [{ fileId: 7, originalName: '减脂容量型计划.xlsx' }])
})

test('appendChatMessages 会为缺失 attachments 的消息补齐空数组', () => {
  const nextHistory = appendChatMessages(
    [{ role: 'user', content: '第一句' }],
    [{ role: 'assistant', content: '第二句' }],
  )

  assert.deepEqual(nextHistory.map((message) => message.attachments), [[], []])
})
