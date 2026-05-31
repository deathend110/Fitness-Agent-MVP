import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import { requestCoachReply } from '../src/utils/coachChat.js'

test('ModelSelector 源码包含模型下拉和 thinking 控制契约', () => {
  const source = readFileSync('src/components/coach/ModelSelector.jsx', 'utf-8')

  assert.match(source, /supportsThinking/)
  assert.match(source, /onModelChange/)
  assert.match(source, /onThinkingChange/)
  assert.match(source, /思考/)
  assert.match(source, /value="max"/)
})

test('FileAttachmentTray 源码包含上传状态、文件 chip 和删除契约', () => {
  const source = readFileSync('src/components/coach/FileAttachmentTray.jsx', 'utf-8')

  assert.match(source, /type="file"/)
  assert.match(source, /onFilesSelected/)
  assert.match(source, /onRemoveFile/)
  assert.match(source, /parserStatus/)
})

test('Coach 请求会携带模型和 thinking 配置', async () => {
  await requestCoachReply(
    {
      model: 'deepseek-v4-pro',
      thinking: { enabled: true, budget: 'max' },
      userInput: '需要更深入分析',
    },
    {
      requestImpl: async (payload) => {
        assert.deepEqual(payload, {
          fileIds: [],
          model: 'deepseek-v4-pro',
          sessionId: null,
          thinking: { enabled: true, budget: 'max' },
          userInput: '需要更深入分析',
        })
        return { text: 'ok', suggestion: null }
      },
    },
  )
})
