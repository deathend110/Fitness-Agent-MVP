import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  buildCoachHistoryView,
  getCoachEmptyQuestionView,
  getVisibleStreamText,
} from '../src/utils/coachView.js'

test('getVisibleStreamText 会剥离结构化 JSON 之后的流式内容', () => {
  const visibleText = getVisibleStreamText(
    '先给用户可读建议\n---JSON---\n{"summary":"结构化建议"}',
  )

  assert.equal(visibleText, '先给用户可读建议')
})

test('getVisibleStreamText 在没有 JSON 标记时返回原始文本', () => {
  assert.equal(getVisibleStreamText('只有自然语言回复'), '只有自然语言回复')
})

test('buildCoachHistoryView 会从用户消息生成轻量历史展示模型', () => {
  const view = buildCoachHistoryView([
    { role: 'assistant', content: '欢迎回来' },
    { role: 'user', content: '今天深蹲做多少重量合适？' },
    { role: 'assistant', content: '建议从 70% 1RM 开始。' },
    { role: 'user', content: '帮我看看本周蛋白质摄入。' },
  ])

  assert.equal(view.groups.length, 1)
  assert.equal(view.groups[0].label, '最近对话')
  assert.equal(view.groups[0].items.length, 2)
  assert.equal(view.groups[0].items[0].title, '帮我看看本周蛋白质摄入。')
  assert.equal(view.groups[0].items[0].id, 'session-message-3')
  assert.equal(view.groups[0].items[0].isActive, true)
  assert.equal(view.groups[0].items[1].title, '今天深蹲做多少重量合适？')
  assert.equal(view.groups[0].items[1].id, 'session-message-1')
})

test('buildCoachHistoryView 会用 activeSessionId 稳定命中指定历史项', () => {
  const view = buildCoachHistoryView(
    [
      { role: 'assistant', content: '欢迎回来' },
      { role: 'user', content: '今天深蹲做多少重量合适？' },
      { role: 'assistant', content: '建议从 70% 1RM 开始。' },
      { role: 'user', content: '帮我看看本周蛋白质摄入。' },
    ],
    { activeSessionId: 'session-message-1' },
  )

  assert.equal(view.groups[0].items[0].id, 'session-message-3')
  assert.equal(view.groups[0].items[0].isActive, false)
  assert.equal(view.groups[0].items[1].id, 'session-message-1')
  assert.equal(view.groups[0].items[1].isActive, true)
})

test('buildCoachHistoryView 新增消息后已有历史 id 不漂移', () => {
  const baseHistory = [
    { role: 'assistant', content: '欢迎回来' },
    { role: 'user', content: '今天深蹲做多少重量合适？' },
    { role: 'assistant', content: '建议从 70% 1RM 开始。' },
    { role: 'user', content: '帮我看看本周蛋白质摄入。' },
  ]
  const beforeView = buildCoachHistoryView(baseHistory)
  const afterView = buildCoachHistoryView([
    ...baseHistory,
    { role: 'assistant', content: '蛋白质建议已整理。' },
    { role: 'user', content: '再帮我看一下睡眠恢复。' },
  ])

  const beforeOlderIds = beforeView.groups[0].items.map((item) => item.id)
  const afterOlderIds = afterView.groups[0].items.slice(1).map((item) => item.id)

  assert.deepEqual(beforeOlderIds, afterOlderIds)
})

test('buildCoachHistoryView 在没有用户消息时返回空状态占位记录', () => {
  const view = buildCoachHistoryView([])

  assert.equal(view.groups.length, 1)
  assert.equal(view.groups[0].items[0].title, '开始新的对话')
  assert.equal(view.groups[0].items[0].isPlaceholder, true)
})

test('getCoachEmptyQuestionView 返回固定四条空状态建议问题', () => {
  const questions = getCoachEmptyQuestionView()

  assert.equal(questions.length, 4)
  assert.deepEqual(
    questions.map((item) => item.label),
    ['恢复分析', '营养检查', '强度优化', '容量评估'],
  )
})

test('MessageList 使用底部 sentinel 和 autoScrollKey 控制滚动', () => {
  const source = readFileSync('src/components/coach/MessageList.jsx', 'utf-8')

  assert.match(source, /bottomRef/)
  assert.match(source, /autoScrollKey/)
  assert.match(source, /scrollIntoView/)
})
