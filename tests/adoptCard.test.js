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
