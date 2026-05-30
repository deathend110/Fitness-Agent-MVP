import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildPromptPreviewModel,
  promptPreviewLabels,
} from '../src/utils/promptPreview.js'
import {
  demoDailyLog,
  demoProfile,
  demoWeeklyPlan,
} from '../src/utils/defaultData.js'
import { getTodayStr } from '../src/utils/calc.js'
import { buildSystemPrompt } from '../src/utils/prompt.js'

test('buildPromptPreviewModel 默认返回折叠的当前上下文预览', () => {
  const previewModel = buildPromptPreviewModel(
    demoProfile,
    demoWeeklyPlan,
    demoDailyLog,
  )

  assert.equal(previewModel.title, promptPreviewLabels.title)
  assert.equal(previewModel.codeLabel, promptPreviewLabels.codeLabel)
  assert.equal(previewModel.defaultExpanded, false)
  assert.equal(
    previewModel.promptText,
    buildSystemPrompt(demoProfile, demoWeeklyPlan, demoDailyLog),
  )
})

test('buildPromptPreviewModel 会随着今日日志变化生成新的 prompt 预览', () => {
  const todayStr = getTodayStr()
  const originalModel = buildPromptPreviewModel(
    demoProfile,
    demoWeeklyPlan,
    demoDailyLog,
  )
  const updatedDailyLog = {
    ...demoDailyLog,
    [todayStr]: {
      ...demoDailyLog[todayStr],
      trainingNotes: '今天改成轻量恢复训练，深蹲主项只做技术组。',
      kcal: 2460,
    },
  }
  const updatedModel = buildPromptPreviewModel(
    demoProfile,
    demoWeeklyPlan,
    updatedDailyLog,
  )

  assert.notEqual(updatedModel.promptText, originalModel.promptText)
  assert.match(updatedModel.promptText, /今天改成轻量恢复训练/)
  assert.match(updatedModel.promptText, /2460kcal/)
  assert.doesNotMatch(updatedModel.promptText, /深蹲第3组没有按计划完成/)
})
