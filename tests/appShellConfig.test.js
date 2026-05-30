import assert from 'node:assert/strict'
import test from 'node:test'

import {
  appShellQuickActions,
  appShellTabs,
  buildAppShellStatus,
  getActiveShellTab,
} from '../src/components/app-shell/appShellConfig.js'

test('appShellTabs 保留四个核心导航并按壳层顺序排列', () => {
  assert.deepEqual(
    appShellTabs.map((tab) => tab.id),
    ['profile', 'plan', 'today', 'coach'],
  )

  assert.deepEqual(
    appShellTabs.map((tab) => tab.label),
    ['我的档案', '训练计划', '今日日志', 'AI 教练'],
  )
})

test('getActiveShellTab 在未知 tab id 时回退到我的档案', () => {
  assert.equal(getActiveShellTab('plan').label, '训练计划')
  assert.equal(getActiveShellTab('unknown').id, 'profile')
})

test('buildAppShellStatus 提供底部状态区所需的默认文案', () => {
  assert.deepEqual(buildAppShellStatus(), {
    saveStateLabel: '数据已保存',
    storageLabel: '本地存储',
  })
})

test('appShellQuickActions 在 V1.6 侧栏中保持为空，避免出现底部双按钮', () => {
  assert.deepEqual(appShellQuickActions, [])
})
