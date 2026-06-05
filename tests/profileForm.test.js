import test from 'node:test'
import assert from 'node:assert/strict'

import { draftToProfile } from '../src/utils/profileForm.js'

test('draftToProfile 会把越界档案数值转成 null，避免非法业务值落库', () => {
  const profile = draftToProfile({
    basic: {
      name: 'A',
      sex: 'male',
      age: '999',
      height: '9999',
      weight: '-1',
      waist: '300',
    },
    oneRM: {
      squat: '100000',
      bench: '-1',
      deadlift: '600',
    },
    goal: '',
    targetWeight: '9999',
    notes: '',
  })

  assert.equal(profile.basic.age, null)
  assert.equal(profile.basic.height, null)
  assert.equal(profile.basic.weight, null)
  assert.equal(profile.basic.waist, null)
  assert.equal(profile.oneRM.squat, null)
  assert.equal(profile.oneRM.bench, null)
  assert.equal(profile.oneRM.deadlift, null)
  assert.equal(profile.targetWeight, null)
})

test('draftToProfile 会保留空值并透传合法档案数值', () => {
  const profile = draftToProfile({
    basic: {
      name: 'B',
      sex: 'female',
      age: '',
      height: '165.5',
      weight: '60.2',
      waist: '',
    },
    oneRM: {
      squat: '140',
      bench: '',
      deadlift: '180',
    },
    goal: 'cut',
    targetWeight: '',
    notes: 'ok',
  })

  assert.deepEqual(profile, {
    basic: {
      name: 'B',
      sex: 'female',
      age: null,
      height: 165.5,
      weight: 60.2,
      waist: null,
    },
    oneRM: {
      squat: 140,
      bench: null,
      deadlift: 180,
    },
    goal: 'cut',
    targetWeight: null,
    notes: 'ok',
  })
})
