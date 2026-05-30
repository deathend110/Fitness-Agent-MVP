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
  assert.equal(model.loadDetailLabel, '深蹲 1RM 150kg × 75%')
  assert.equal(model.volumeLabel, '4 组 x 6 次')
  assert.equal(model.effortLabel, 'RPE 8')
  assert.equal(model.summaryLabel, '112.5kg · 4 组 x 6 次 · RPE 8')
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
  assert.equal(model.loadDetailLabel, '固定重量')
  assert.equal(model.volumeLabel, '3 组 x 10 次')
  assert.equal(model.effortLabel, 'RPE 7')
  assert.equal(model.noteLabel, 'RPE 7')
  assert.equal(model.cardClassName, 'border-fitloop-line/70 bg-fitloop-ink/50')
})

test('buildPlanExerciseCardModel 会为自重动作提供清晰的负重与备注兜底', () => {
  const model = buildPlanExerciseCardModel(
    {
      id: 'pull-up-1',
      name: '引体向上',
      tier: 'main',
      kg: null,
      ref1RM: null,
      pct: null,
      sets: 4,
      reps: 8,
      rpe: null,
      note: '   ',
    },
    {},
  )

  assert.equal(model.weightLabel, '自重')
  assert.equal(model.loadDetailLabel, '自重动作')
  assert.equal(model.effortLabel, '未填写 RPE')
  assert.equal(model.noteLabel, '暂无备注')
  assert.equal(model.noteEmpty, true)
})

test('buildPlanExerciseCardModel 会为未命名动作与长动作名保留稳定展示字段', () => {
  const unnamedModel = buildPlanExerciseCardModel(
    {
      id: 'unnamed-1',
      name: '   ',
      tier: 'accessory',
      kg: 25,
      sets: 3,
      reps: 15,
      rpe: 8,
      note: '',
    },
    {},
  )

  const longName = '杠铃保加利亚分腿蹲停顿离心控制强化组'
  const longNameModel = buildPlanExerciseCardModel(
    {
      id: 'long-name-1',
      name: longName,
      tier: 'main',
      ref1RM: 'squat',
      pct: 0.6,
      kg: null,
      sets: 3,
      reps: 8,
      rpe: 7.5,
      note: '',
    },
    {
      oneRM: {
        squat: 140,
      },
    },
  )

  assert.equal(unnamedModel.name, '未命名动作')
  assert.equal(unnamedModel.noteLabel, 'RPE 8')
  assert.equal(longNameModel.name, longName)
  assert.equal(longNameModel.loadDetailLabel, '深蹲 1RM 140kg × 60%')
  assert.equal(longNameModel.summaryLabel, '84kg · 3 组 x 8 次 · RPE 7.5')
})
