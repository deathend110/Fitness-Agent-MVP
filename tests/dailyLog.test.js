import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildTodayLogPayload,
  readTodayLogForm,
} from '../src/utils/dailyLog.js'

test('readTodayLogForm 在当天没有记录时返回可直接绑定表单的默认值', () => {
  const form = readTodayLogForm(undefined)

  assert.deepEqual(form, {
    weight: '',
    kcal: '',
    protein: '',
    sleep: '',
    fatigue: '',
    trainingDone: false,
    trainingNotes: '',
  })
})

test('buildTodayLogPayload 使用当天日期键写回 fitloop_dailyLog 且不影响其他日期', () => {
  const prevLog = {
    '2026-05-29': {
      weight: 80.5,
      kcal: 2200,
      protein: 160,
      sleep: 7,
      fatigue: 3,
      trainingDone: true,
      trainingNotes: '上一天记录',
    },
  }

  const nextLog = buildTodayLogPayload(prevLog, '2026-05-30', {
    weight: '81.2',
    kcal: '2300',
    protein: '170',
    sleep: '6.5',
    fatigue: '4',
    trainingDone: true,
    trainingNotes: '今天完成腿部训练',
  })

  assert.deepEqual(nextLog['2026-05-29'], prevLog['2026-05-29'])
  assert.deepEqual(nextLog['2026-05-30'], {
    weight: 81.2,
    kcal: 2300,
    protein: 170,
    sleep: 6.5,
    fatigue: 4,
    trainingDone: true,
    trainingNotes: '今天完成腿部训练',
  })
})

test('buildTodayLogPayload 遇到可选字段留空时写入空安全值而不是让页面崩溃', () => {
  const nextLog = buildTodayLogPayload({}, '2026-05-30', {
    weight: '',
    kcal: '',
    protein: '',
    sleep: '',
    fatigue: '',
    trainingDone: false,
    trainingNotes: '',
  })

  assert.deepEqual(nextLog['2026-05-30'], {
    weight: null,
    kcal: null,
    protein: null,
    sleep: null,
    fatigue: null,
    trainingDone: false,
    trainingNotes: '',
  })
})
