import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildBackupFilename,
  buildBackupPayload,
  parseBackupJson,
} from '../src/utils/dataTransfer.js'

test('buildBackupPayload 会打包四类本地数据并附带导出元信息', () => {
  const payload = buildBackupPayload(
    {
      profile: { basic: { name: '小林' } },
      weeklyPlan: { Monday: { type: '腿日', exercises: [] } },
      dailyLog: { '2026-05-30': { weight: 81.2 } },
      chatHistory: [{ role: 'user', content: 'test' }],
    },
    '2026-05-30T09:00:00.000Z',
  )

  assert.equal(payload.app, 'repmind-mvp')
  assert.equal(payload.version, 1)
  assert.equal(payload.exportedAt, '2026-05-30T09:00:00.000Z')
  assert.deepEqual(payload.profile, { basic: { name: '小林' } })
  assert.deepEqual(payload.weeklyPlan, { Monday: { type: '腿日', exercises: [] } })
  assert.deepEqual(payload.dailyLog, { '2026-05-30': { weight: 81.2 } })
  assert.deepEqual(payload.chatHistory, [{ role: 'user', content: 'test' }])
})

test('parseBackupJson 会拒绝缺少必要字段的备份文件', () => {
  assert.throws(
    () => parseBackupJson('{"profile":{},"weeklyPlan":{},"dailyLog":{}}'),
    /chatHistory/,
  )
})

test('parseBackupJson 会在结构合法时返回可直接写回本地的数据', () => {
  const nextData = parseBackupJson(`{
    "app": "repmind-mvp",
    "version": 1,
    "exportedAt": "2026-05-30T09:00:00.000Z",
    "profile": { "basic": { "name": "小林" } },
    "weeklyPlan": { "Monday": { "type": "腿日", "exercises": [] } },
    "dailyLog": { "2026-05-30": { "weight": 81.2 } },
    "chatHistory": [{ "role": "assistant", "content": "ok" }]
  }`)

  assert.deepEqual(nextData, {
    profile: { basic: { name: '小林' } },
    weeklyPlan: { Monday: { type: '腿日', exercises: [] } },
    dailyLog: { '2026-05-30': { weight: 81.2 } },
    chatHistory: [{ role: 'assistant', content: 'ok' }],
  })
})

test('buildBackupFilename 会输出带日期的 json 文件名', () => {
  assert.equal(buildBackupFilename('2026-05-30T09:00:00.000Z'), 'repmind-backup-2026-05-30.json')
})
