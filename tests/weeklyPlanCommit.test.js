import assert from 'node:assert/strict'
import test from 'node:test'

import { mergeCommittedWeeklyPlan } from '../src/utils/weeklyPlanCommit.js'

test('mergeCommittedWeeklyPlan 会保留本地顶层 weekMeta 并覆盖后端返回的七天计划', () => {
  const currentPlan = {
    weekMeta: { weekNumber: 8 },
    Monday: { type: 'rest', exercises: [] },
    Tuesday: { type: 'rest', exercises: [] },
    Wednesday: { type: 'rest', exercises: [] },
    Thursday: { type: 'rest', exercises: [] },
    Friday: { type: 'rest', exercises: [] },
    Saturday: { type: 'rest', exercises: [] },
    Sunday: { type: 'rest', exercises: [] },
  }

  const committedPlan = {
    Monday: { type: '腿日', exercises: [{ name: '深蹲', sets: 3 }] },
    Tuesday: { type: 'rest', exercises: [] },
    Wednesday: { type: 'rest', exercises: [] },
    Thursday: { type: 'rest', exercises: [] },
    Friday: { type: 'rest', exercises: [] },
    Saturday: { type: 'rest', exercises: [] },
    Sunday: { type: 'rest', exercises: [] },
  }

  const merged = mergeCommittedWeeklyPlan(currentPlan, committedPlan)
  assert.equal(merged.weekMeta.weekNumber, 8)
  assert.equal(merged.Monday.exercises[0].name, '深蹲')
})
