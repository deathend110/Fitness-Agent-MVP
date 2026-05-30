import assert from 'node:assert/strict'
import test from 'node:test'

import {
  defaultChatHistory,
  defaultDailyLog,
  defaultProfile,
  defaultWeeklyPlan,
  demoChatHistory,
  demoDailyLog,
  demoProfile,
  demoWeeklyPlan,
  storageKeys,
} from '../src/utils/defaultData.js'
import { emptyDefaultsStorageVersion, migrateLegacyDemoData } from '../src/utils/storage.js'

function createLocalStorageMock(initialEntries = {}) {
  const store = new Map(
    Object.entries(initialEntries).map(([key, value]) => [key, JSON.stringify(value)]),
  )

  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null
    },
    setItem(key, value) {
      store.set(key, String(value))
    },
    removeItem(key) {
      store.delete(key)
    },
    clear() {
      store.clear()
    },
  }
}

test('default* 应保持为空白可填写结构，demo* 单独保留演示数据', () => {
  assert.equal(defaultProfile.basic.name, '')
  assert.equal(defaultProfile.goal, '')
  assert.deepEqual(defaultWeeklyPlan.Monday, { type: 'rest', exercises: [] })
  assert.deepEqual(defaultDailyLog, {})
  assert.deepEqual(defaultChatHistory, [])

  assert.equal(demoProfile.basic.name.length > 0, true)
  assert.equal(demoWeeklyPlan.Monday.exercises.length > 0, true)
  assert.equal(Object.keys(demoDailyLog).length > 0, true)
  assert.equal(demoChatHistory.length > 0, true)
})

test('migrateLegacyDemoData 首次执行会清空旧 demo 数据并写入版本标记，再次执行不会重复覆盖', () => {
  const localStorage = createLocalStorageMock({
    [storageKeys.profile]: demoProfile,
    [storageKeys.weeklyPlan]: demoWeeklyPlan,
    [storageKeys.dailyLog]: demoDailyLog,
    [storageKeys.chatHistory]: demoChatHistory,
  })

  globalThis.window = { localStorage }

  migrateLegacyDemoData()

  assert.deepEqual(JSON.parse(localStorage.getItem(storageKeys.profile)), defaultProfile)
  assert.deepEqual(JSON.parse(localStorage.getItem(storageKeys.weeklyPlan)), defaultWeeklyPlan)
  assert.deepEqual(JSON.parse(localStorage.getItem(storageKeys.dailyLog)), defaultDailyLog)
  assert.deepEqual(JSON.parse(localStorage.getItem(storageKeys.chatHistory)), defaultChatHistory)
  assert.equal(
    localStorage.getItem(storageKeys.storageVersion),
    JSON.stringify(emptyDefaultsStorageVersion),
  )

  localStorage.setItem(storageKeys.profile, JSON.stringify({ basic: { name: '真实用户' } }))

  migrateLegacyDemoData()

  assert.deepEqual(JSON.parse(localStorage.getItem(storageKeys.profile)), {
    basic: { name: '真实用户' },
  })

  delete globalThis.window
})
