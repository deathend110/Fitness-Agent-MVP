import test from 'node:test'
import assert from 'node:assert/strict'
import { getCoachBlockReason } from '../src/utils/coachGuard.js'

test('getCoachBlockReason 在档案缺少关键字段时返回阻断提示', () => {
  const message = getCoachBlockReason({
    basic: { name: '', weight: null },
    oneRM: { squat: null },
    goal: '',
  })

  assert.match(message, /请先完善档案/)
  assert.match(message, /深蹲 1RM/)
})

test('getCoachBlockReason 在档案满足最小 AI 上下文要求时返回空字符串', () => {
  const message = getCoachBlockReason({
    basic: { name: '小林', weight: 75 },
    oneRM: { squat: 120 },
    goal: '增肌减脂',
  })

  assert.equal(message, '')
})
