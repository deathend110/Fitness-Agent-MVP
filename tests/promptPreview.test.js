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

test('buildPromptPreviewModel 默认返回折叠的当前上下文预览，且内容与真实 prompt 一致', () => {
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
  assert.match(previewModel.promptText, /BMI/)
  assert.match(previewModel.promptText, /热量状态/)
  assert.match(previewModel.promptText, /蛋白质按体重/)
  assert.match(previewModel.promptText, /恢复数据/)
  assert.match(previewModel.promptText, /structured_metrics/)
})

test('buildPromptPreviewModel 会随着今日日志变化生成新的结构化指标预览', () => {
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
      protein: 120,
      sleep: 8,
      fatigue: 2,
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
  assert.match(updatedModel.promptText, /"calorie_status":\s*"surplus"/)
  assert.match(updatedModel.promptText, /"protein_status":\s*"low"/)
  assert.match(updatedModel.promptText, /"sleep_hours":\s*8/)
  assert.match(updatedModel.promptText, /"fatigue_level":\s*2/)
  assert.doesNotMatch(updatedModel.promptText, /深蹲第三组没有按计划完成/)
})
