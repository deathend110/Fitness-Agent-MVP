import test from 'node:test'
import assert from 'node:assert/strict'

import { mergeMessageMeta } from '../src/utils/chatSuggestionState.js'

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
