import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

import {
  appShellQuickActions,
  appShellTabs,
  buildAppShellStatus,
  getActiveShellTab,
} from '../src/components/app-shell/appShellConfig.js'
import {
  appShellLayoutModes,
  getAppShellLayout,
} from '../src/components/app-shell/appShellLayout.js'

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
test('appShellLayoutModes 暴露 coach 与默认页的稳定壳层布局契约', () => {
  assert.deepEqual(Object.keys(appShellLayoutModes), ['default', 'coach'])

  assert.deepEqual(appShellLayoutModes.coach, {
    mode: 'coach',
    wrapperClassName: 'flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-canvas p-0',
    contentClassName: 'fitloop-shell__content min-h-0 flex-1 overflow-hidden',
  })

  assert.deepEqual(appShellLayoutModes.default, {
    mode: 'default',
    wrapperClassName:
      'flex min-w-0 flex-1 flex-col overflow-hidden bg-fitloop-canvas p-4 sm:p-5 lg:p-6',
    contentClassName:
      'fitloop-shell__content min-h-0 flex-1 overflow-y-auto overflow-x-hidden',
  })
})

test('getAppShellLayout 让 coach 页使用沉浸承载模式，其他页面回退默认模式', () => {
  assert.deepEqual(getAppShellLayout('coach'), appShellLayoutModes.coach)
  assert.deepEqual(getAppShellLayout('plan'), appShellLayoutModes.default)
  assert.deepEqual(getAppShellLayout('unknown'), appShellLayoutModes.default)
})

test('AppShell 为 coach 页预留独立壳层类名分支', () => {
  const appShellSource = fs.readFileSync(
    new URL('../src/components/app-shell/AppShell.jsx', import.meta.url),
    'utf8',
  )

  assert.match(appShellSource, /getAppShellLayout\(activeTabId\)/)
  assert.match(appShellSource, /shellLayout\.wrapperClassName/)
  assert.match(appShellSource, /shellLayout\.contentClassName/)
})
