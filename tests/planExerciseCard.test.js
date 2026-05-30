import assert from 'node:assert/strict'
import test from 'node:test'

import { buildPlanExerciseCardModel } from '../src/utils/planExerciseCard.js'

test('buildPlanExerciseCardModel 会把主项动作整理成分层卡片模型', () => {
  const model = buildPlanExerciseCardModel(
    {
      id: 'squat-1',
      name: '深蹲',
      tier: 'main',
      ref1RM: 'squat',
      pct: 0.75,
      kg: null,
      sets: 4,
      reps: 6,
      rpe: 8,
      note: '主项',
    },
    {
      oneRM: {
        squat: 150,
      },
    },
  )

  assert.equal(model.tierLabel, '主项')
  assert.equal(model.tierTone, 'main')
  assert.equal(model.weightLabel, '112.5kg')
  assert.equal(model.volumeLabel, '4 组 x 6 次')
  assert.equal(model.summaryLabel, '112.5kg · 4 组 x 6 次')
  assert.equal(model.noteLabel, '主项 · RPE 8')
  assert.equal(model.cardClassName, 'border-fitloop-orange/35 bg-fitloop-orange/8')
})

test('buildPlanExerciseCardModel 会把辅项动作整理成更轻的视觉层级', () => {
  const model = buildPlanExerciseCardModel(
    {
      id: 'row-1',
      name: '划船',
      tier: 'accessory',
      kg: 60,
      sets: 3,
      reps: 10,
      rpe: 7,
      note: '',
    },
    {},
  )

  assert.equal(model.tierLabel, '辅项')
  assert.equal(model.tierTone, 'accessory')
  assert.equal(model.weightLabel, '60kg')
  assert.equal(model.volumeLabel, '3 组 x 10 次')
  assert.equal(model.noteLabel, 'RPE 7')
  assert.equal(model.cardClassName, 'border-fitloop-line/70 bg-fitloop-ink/50')
})
