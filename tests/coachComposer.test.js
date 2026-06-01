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

test('CoachTab 会为用户消息构造附件快照并在发送成功后清空输入区附件', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /function buildMessageAttachmentSnapshots\(files = \[\]\)/)
  assert.match(source, /const messageAttachments = buildMessageAttachmentSnapshots\(attachedFiles\)/)
  assert.match(
    source,
    /const userMessage = \{ role: 'user', content: userInput, attachments: messageAttachments \}/,
  )
  assert.match(source, /fileIds: attachedFiles\.map\(\(file\) => file\.id\)\.filter\(Number\.isInteger\)/)
  assert.match(source, /setAttachedFiles\(\[\]\)/)
  assert.match(
    source,
    /attachments: Array\.isArray\(message\?\.attachments\) \? message\.attachments : \[\]/,
  )
})

test('MessageBubble 会在用户消息正文前挂载附件卡片区', () => {
  const source = readFileSync('src/components/coach/MessageBubble.jsx', 'utf-8')

  assert.match(source, /import MessageAttachmentCard from '\.\/MessageAttachmentCard\.jsx'/)
  assert.match(source, /isUser && attachments\.length/)
  assert.match(source, /<MessageAttachmentCard/)
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

test('CoachTab 会用 mergeCommittedWeeklyPlan 安全合并后端写回结果', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /mergeCommittedWeeklyPlan/)
  assert.match(source, /onWeeklyPlanChange\(\(currentPlan\) => mergeCommittedWeeklyPlan\(currentPlan, adoptResult\.plan\)\)/)
})

test('CoachTab 会持久记录已处理 suggestion，并在恢复消息时继续隐藏', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /persistDismissedSuggestionKey/)
  assert.match(source, /readDismissedSuggestionKeys/)
  assert.match(source, /hiddenCommitKeys: new Set\(readDismissedSuggestionKeys\(activeSessionIdRef\.current\)\)/)
})

test('MessageList 和 MessageBubble 会把发送中的 assistant 占位态渲染成“思考中”紧凑气泡', () => {
  const listSource = readFileSync('src/components/coach/MessageList.jsx', 'utf-8')
  const bubbleSource = readFileSync('src/components/coach/MessageBubble.jsx', 'utf-8')

  assert.match(listSource, /streamingText \|\| '思考中'/)
  assert.doesNotMatch(listSource, /正在整理上下文/)
  assert.match(bubbleSource, /const bubbleClassName =/)
  assert.match(bubbleSource, /isStreaming && !isUser/)
})

test('ChatTopbar 会为右上角操作按钮提供 SVG 图标和 hover 提示', () => {
  const source = readFileSync('src/components/coach/ChatTopbar.jsx', 'utf-8')

  assert.match(source, /tooltip=/)
  assert.match(source, /title=\{tooltip\}/)
  assert.match(source, /group-hover:opacity-100/)
  assert.match(source, /<svg/)
  assert.doesNotMatch(source, /⌫|⇩/)
})

test('CoachLayout 会移除上下硬边线，并改为消息区上下渐隐遮罩', () => {
  const source = readFileSync('src/components/coach/CoachLayout.jsx', 'utf-8')

  assert.doesNotMatch(source, /<header className="[^"]*border-b/)
  assert.doesNotMatch(source, /<footer className="[^"]*border-t/)
  assert.match(source, /bg-gradient-to-b/)
  assert.match(source, /bg-gradient-to-t/)
  assert.match(source, /pointer-events-none absolute inset-x-0 top-0/)
  assert.match(source, /pointer-events-none absolute inset-x-0 bottom-0/)
})
