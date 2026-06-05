import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildTodayLogFieldGroups,
  buildTodayLogSummaryItems,
} from '../src/utils/todayLogView.js'

test('buildTodayLogFieldGroups 会把今日日志字段整理成身体 摄入 恢复三组录入区', () => {
  const groups = buildTodayLogFieldGroups()

  assert.deepEqual(
    groups.map((group) => ({
      key: group.key,
      title: group.title,
      fieldKeys: group.fields.map((field) => field.key),
      guardrailKeys: group.fields.map((field) => field.guardrailKey),
    })),
    [
      {
        key: 'body',
        title: '身体数据',
        fieldKeys: ['weight'],
        guardrailKeys: ['today.weight'],
      },
      {
        key: 'intake',
        title: '摄入记录',
        fieldKeys: ['kcal', 'protein'],
        guardrailKeys: ['today.kcal', 'today.protein'],
      },
      {
        key: 'recovery',
        title: '恢复与状态',
        fieldKeys: ['sleep', 'steps', 'tdee', 'fatigue'],
        guardrailKeys: ['today.sleep', 'today.steps', 'today.tdee', 'today.fatigue'],
      },
    ],
  )
})

test('buildTodayLogSummaryItems 会把已保存今日日志整理成稳定摘要并处理空值占位', () => {
  const items = buildTodayLogSummaryItems({
    weight: 81.8,
    kcal: 2430,
    protein: 152,
    sleep: 7.6,
    steps: null,
    tdee: 2670,
    fatigue: 3,
    trainingDone: true,
  })

  assert.deepEqual(items, [
    { key: 'weight', label: '体重', value: '81.8 kg' },
    { key: 'kcal', label: '热量', value: '2430 kcal' },
    { key: 'protein', label: '蛋白质', value: '152 g' },
    { key: 'sleep', label: '睡眠', value: '7.6 h' },
    { key: 'steps', label: '步数', value: '未记录' },
    { key: 'tdee', label: 'TDEE', value: '2670 kcal' },
    { key: 'fatigue', label: '疲劳度', value: '3 / 5' },
    { key: 'trainingDone', label: '训练完成', value: '是' },
  ])
})
