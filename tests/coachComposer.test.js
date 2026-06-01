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

test('CoachTab 模型列表回包不会覆盖后端草稿恢复的模型和 thinking', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.doesNotMatch(source, /setSelectedModel\(config\.defaultModel/)
  assert.doesNotMatch(source, /enabled: Boolean\(config\.thinking\?\.enabled\)/)
})

test('CoachTab 会把后台 pending/running 任务映射为教练思考中状态', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /shouldShowBackgroundCoachPendingIndicator/)
  assert.match(source, /const \[isBackgroundThinking, setIsBackgroundThinking\] = useState\(false\)/)
  assert.match(source, /const isCoachThinking = isSending \|\| isBackgroundThinking/)
  assert.match(source, /isSending=\{isCoachThinking\}/)
  assert.match(source, /autoScrollKey=\{`\$\{messageList\.length\}:\$\{isCoachThinking \? 'sending' : 'idle'\}`\}/)
})

test('CoachTab 在窗口 blur/focus 和组件卸载时衔接后台任务', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /window\.addEventListener\('blur', submitBackgroundTask\)/)
  assert.match(source, /window\.addEventListener\('focus', pollStoredTask\)/)
  assert.match(source, /window\.removeEventListener\('blur', submitBackgroundTask\)/)
  assert.match(source, /window\.removeEventListener\('focus', pollStoredTask\)/)
  assert.match(source, /return \(\) => \{[\s\S]*submitBackgroundTask\(\)[\s\S]*\}/)
})

test('CoachTab 后台任务提交成功后立即进入后台思考态且只提交一次', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /if \(!payload \|\| backgroundTaskStartedRef\.current\) \{/)
  assert.match(source, /backgroundTaskStartedRef\.current = true/)
  assert.match(source, /if \(taskRecord &&[\s\S]*shouldShowBackgroundCoachPendingIndicator\(/)
  assert.match(source, /setIsBackgroundThinking\(true\)/)
})

test('CoachTab 会把新回复的 proposal 或 suggestion 写入 assistant message', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /const assistantSuggestion = reply\.proposal \|\| reply\.suggestion \|\| null/)
  assert.match(source, /suggestion: assistantSuggestion/)
  assert.doesNotMatch(
    source,
    /appendChatMessages\(nextHistory,\s*\[\{ role: 'assistant', content: reply\.text \}\]\)/,
  )
})

test('CoachTab 会从 message.suggestion 恢复采纳卡片并在处理后持久隐藏', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /message\?\.suggestion \|\| null/)
  assert.match(source, /function persistHideSuggestion/)
  assert.match(source, /suggestion: null/)
  assert.match(source, /onChatHistoryChange\(nextHistory\)/)
  assert.match(source, /handleDismissSuggestion\(targetSuggestion\)/)
})

test('CoachTab 对同一卡片采纳请求有 in-flight 去重保护', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /const adoptingSuggestionKeysRef = useRef\(new Set\(\)\)/)
  assert.match(source, /from '\.\.\/utils\/chatSuggestionState\.js'/)
  assert.match(source, /adoptingSuggestionKeysRef\.current\.has\(commitKey\)/)
  assert.match(source, /adoptingSuggestionKeysRef\.current\.add\(commitKey\)/)
  assert.match(source, /adoptingSuggestionKeysRef\.current\.delete\(commitKey\)/)
})
