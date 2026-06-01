import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getSuggestionCommitKey,
  mergeMessageMeta,
  persistDismissedSuggestionKey,
  readDismissedSuggestionKeys,
} from '../src/utils/chatSuggestionState.js'

test('mergeMessageMeta 会优先保留最新消息上的 suggestion，避免旧 proposalId 覆盖新卡片', () => {
  const oldSuggestion = {
    proposalId: 'proposal-old',
    day: 'Monday',
    summary: '旧卡片',
  }
  const newSuggestion = {
    proposalId: 'proposal-new',
    day: 'Monday',
    summary: '新卡片',
  }

  const merged = mergeMessageMeta(
    [
      { role: 'assistant', content: '建议你把周一容量降一点。', suggestion: oldSuggestion },
      { role: 'assistant', content: '建议你把周一容量降一点。', suggestion: newSuggestion },
    ],
    [
      { messageKey: 'assistant::建议你把周一容量降一点。::0', suggestion: oldSuggestion, isDismissed: true },
    ],
  )

  assert.equal(merged[0].suggestion.proposalId, 'proposal-old')
  assert.equal(merged[0].isDismissed, true)
  assert.equal(merged[1].suggestion.proposalId, 'proposal-new')
  assert.equal(merged[1].isDismissed, false)
})

test('mergeMessageMeta 只在同一 proposalId 下保留 dismissed 状态', () => {
  const oldSuggestion = {
    proposalId: 'proposal-old',
    day: 'Monday',
    summary: '旧卡片',
  }
  const newSuggestion = {
    proposalId: 'proposal-new',
    day: 'Monday',
    summary: '新卡片',
  }

  const merged = mergeMessageMeta(
    [{ role: 'assistant', content: '相同回复内容', suggestion: newSuggestion }],
    [
      { messageKey: 'assistant::相同回复内容::0', suggestion: oldSuggestion, isDismissed: true },
    ],
  )

  assert.equal(merged[0].suggestion.proposalId, 'proposal-new')
  assert.equal(merged[0].isDismissed, false)
})

test('mergeMessageMeta 会把已持久隐藏的 suggestion 标记为 dismissed', () => {
  const suggestion = {
    proposalId: 'proposal-hidden',
    day: 'Monday',
    summary: '已处理卡片',
  }

  const merged = mergeMessageMeta(
    [{ role: 'assistant', content: '相同回复内容', suggestion }],
    [],
    {
      hiddenCommitKeys: new Set([getSuggestionCommitKey(suggestion)]),
    },
  )

  assert.equal(merged[0].suggestion.proposalId, 'proposal-hidden')
  assert.equal(merged[0].isDismissed, true)
})

test('persistDismissedSuggestionKey 会按 session 持久化并可恢复读取', () => {
  const store = new Map()
  const originalWindow = globalThis.window

  globalThis.window = {
    localStorage: {
      getItem(key) {
        return store.has(key) ? store.get(key) : null
      },
      setItem(key, value) {
        store.set(key, value)
      },
      removeItem(key) {
        store.delete(key)
      },
    },
  }

  try {
    const suggestion = {
      proposalId: 'proposal-persisted',
      day: 'Monday',
      summary: '持久化卡片',
    }

    persistDismissedSuggestionKey(3, suggestion)

    assert.deepEqual(readDismissedSuggestionKeys(3), [getSuggestionCommitKey(suggestion)])
    assert.deepEqual(readDismissedSuggestionKeys(4), [])
  } finally {
    globalThis.window = originalWindow
  }
})
