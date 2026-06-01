import assert from 'node:assert/strict'
import test from 'node:test'

import { buildAdoptCardModel } from '../src/utils/adoptCard.js'

test('buildAdoptCardModel 会把 AI suggestion 转成卡片展示模型', () => {
  const cardModel = buildAdoptCardModel({
    suggest_plan_update: true,
    day: 'Monday',
    summary: '降低周一深蹲强度，优先恢复动作质量',
    changes: [
      {
        action: 'update',
        exerciseName: '深蹲',
        field: 'pct',
        oldValue: 0.75,
        newValue: 0.7,
      },
      {
        action: 'update',
        exerciseName: '罗马尼亚硬拉',
        field: 'sets',
        oldValue: 4,
        newValue: 3,
      },
    ],
  })

  assert.deepEqual(cardModel, {
    dayLabel: '周一',
    summary: '降低周一深蹲强度，优先恢复动作质量',
    changes: [
      {
        id: '0-update-深蹲-pct',
        actionLabel: '调整',
        exerciseName: '深蹲',
        fieldLabel: '训练百分比',
        beforeLabel: '75%',
        afterLabel: '70%',
      },
      {
        id: '1-update-罗马尼亚硬拉-sets',
        actionLabel: '调整',
        exerciseName: '罗马尼亚硬拉',
        fieldLabel: '组数',
        beforeLabel: '4 组',
        afterLabel: '3 组',
      },
    ],
  })
})

test('buildAdoptCardModel 在 suggestion 缺少可展示内容时返回 null', () => {
  assert.equal(buildAdoptCardModel(null), null)
  assert.equal(
    buildAdoptCardModel({
      suggest_plan_update: true,
      day: 'Monday',
      summary: '   ',
      changes: [],
    }),
    null,
  )
})

test('buildAdoptCardModel 会把 day_plan_replace proposal 转成单日计划卡模型', () => {
  const card = buildAdoptCardModel({
    proposalId: 'proposal-day-plan',
    kind: 'day_plan_replace',
    day: 'Monday',
    summary: '恢复型腿日',
    dayPlan: {
      type: '腿日',
      exercises: [
        {
          name: '深蹲',
          tier: 'main',
          sets: 3,
          reps: 5,
          pct: 0.7,
          rpe: 7,
          note: '恢复周主项',
        },
      ],
    },
  })

  assert.equal(card.variant, 'dayPlan')
  assert.equal(card.dayLabel, '周一')
  assert.equal(card.dayTypeLabel, '腿日')
  assert.equal(card.exercises[0].name, '深蹲')
})
