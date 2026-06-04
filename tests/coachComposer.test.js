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

test('Composer 发送中不再锁定输入框、模型选择、思考开关和已挂载附件操作', () => {
  const source = readFileSync('src/components/coach/Composer.jsx', 'utf-8')

  assert.doesNotMatch(source, /<textarea[\s\S]*disabled=\{isSending\}/)
  assert.doesNotMatch(source, /<ModelSelector[\s\S]*disabled=\{isSending\}/)
  assert.doesNotMatch(source, /<FileAttachmentTray[\s\S]*disabled=\{isSending \|\| isUploading\}/)
  assert.match(source, /<FileAttachmentTray[\s\S]*disabled=\{isUploading\}/)
  assert.match(source, /disabled=\{!draft\.trim\(\) \|\| isSending \|\| isUploading\}/)
})

test('Composer 输入区显式关闭浏览器翻译和写作辅助，同时保留现有发送契约', () => {
  const source = readFileSync('src/components/coach/Composer.jsx', 'utf-8')

  assert.match(source, /<textarea[\s\S]*translate="no"/)
  assert.match(source, /<textarea[\s\S]*spellCheck=\{false\}/)
  assert.match(source, /<textarea[\s\S]*autoCorrect="off"/)
  assert.match(source, /<textarea[\s\S]*autoCapitalize="off"/)
  assert.match(source, /onKeyDown=\{handleKeyDown\}/)
  assert.match(source, /if \(event\.key === 'Enter' && !event\.shiftKey\)/)
})

test('index.html 会在页面入口显式声明不触发浏览器翻译', () => {
  const source = readFileSync('index.html', 'utf-8')

  assert.match(source, /<html[^>]*translate="no"/)
  assert.match(source, /<html[^>]*class="notranslate"/)
  assert.match(source, /<meta name="google" content="notranslate"/)
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
  assert.match(source, /isSending=\{isSending\}/)
  assert.match(source, /autoScrollKey=\{`\$\{messageList\.length\}:\$\{isCoachThinking \? 'sending' : 'idle'\}`\}/)
})

test('CoachTab 只在真正离页相关事件时衔接后台任务，不使用 blur 和卸载清理误触发', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /window\.addEventListener\('focus', pollStoredTask\)/)
  assert.match(source, /window\.removeEventListener\('focus', pollStoredTask\)/)
  assert.doesNotMatch(source, /window\.addEventListener\('blur', submitBackgroundTask\)/)
  assert.doesNotMatch(source, /window\.removeEventListener\('blur', submitBackgroundTask\)/)
  assert.match(source, /return \(\) => \{[\s\S]*document\.removeEventListener\('visibilitychange', handleVisibilityChange\)/)
  assert.match(source, /window\.removeEventListener\('pagehide', submitBackgroundTask\)/)
  assert.doesNotMatch(
    source,
    /document\.removeEventListener\('visibilitychange', handleVisibilityChange\)[\s\S]*submitBackgroundTask\(\)/,
  )
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

  assert.match(source, /const assistantSuggestion = reply\.suggestion \|\| reply\.proposal \|\| null/)
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

test('CoachTab 采纳成功后只做本地隐藏，不会再复用忽略接口请求', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /persistHideSuggestion\(targetSuggestion\)/)
  assert.doesNotMatch(source, /await handleDismissSuggestion\(targetSuggestion\)/)
})

test('CoachTab 采纳建议时通过 backendClient 统一提交，不在页面层直接分叉 legacy adopt 接口', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /client\.commitCoachSuggestion\(targetSuggestion\)/)
  assert.doesNotMatch(source, /client\.adoptWeeklyPlanChange\(/)
  assert.doesNotMatch(source, /client\.commitPlanChange\(\{ proposalId: targetSuggestion\.proposalId \}\)/)
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

test('MessageList 和 MessageBubble 会把发送中的 assistant 占位态渲染成“思考中”三点动画气泡，且不挂交互卡片', () => {
  const listSource = readFileSync('src/components/coach/MessageList.jsx', 'utf-8')
  const bubbleSource = readFileSync('src/components/coach/MessageBubble.jsx', 'utf-8')

  assert.match(listSource, /streamingText \|\| streamStatusLabel \|\| '思考中'/)
  assert.doesNotMatch(listSource, /正在整理上下文/)
  assert.doesNotMatch(listSource, /suggestion:\s*streamingSuggestion/)
  assert.doesNotMatch(listSource, /suggestionCard:\s*buildAdoptCardModel\(streamingSuggestion\)/)
  assert.match(bubbleSource, /const bubbleClassName =/)
  assert.match(bubbleSource, /isStreaming && !isUser/)
  assert.match(bubbleSource, /思考中加载动效改成三个呼吸点/)
  assert.match(bubbleSource, /animate-\[fitloop-thinking-dot/)
  assert.match(bubbleSource, /h-2 w-2 rounded-full/)
  assert.match(bubbleSource, /isStreaming \? <ThinkingDots \/> : null/)
})

test('CoachTab 会把 tool_status 映射为 streamStatusLabel，并在流式阶段缓存 proposal/suggestion 供最终消息立即落地', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /const \[streamStatusLabel, setStreamStatusLabel\] = useState\(''\)/)
  assert.match(source, /const \[streamingSuggestion, setStreamingSuggestion\] = useState\(null\)/)
  assert.match(source, /onProposal: \(proposal\) => \{/)
  assert.match(source, /mergeCoachReplySuggestion\(currentSuggestion, proposal\)/)
  assert.match(source, /onStatusLabel: \(statusLabel\) => \{/)
  assert.match(source, /setStreamStatusLabel\(statusLabel \|\| ''\)/)
  assert.match(source, /onSuggestion: \(suggestion\) => \{/)
  assert.match(source, /mergeCoachReplySuggestion\(currentSuggestion, suggestion\)/)
  assert.match(source, /setStreamingText\(visibleText\)/)
  assert.match(source, /setStreamStatusLabel\(''\)/)
  assert.match(source, /streamStatusLabel=\{streamStatusLabel\}/)
  assert.match(source, /streamingSuggestion=\{streamingSuggestion\}/)
})

test('ChatTopbar 会为右上角操作按钮提供 SVG 图标和 hover 提示', () => {
  const source = readFileSync('src/components/coach/ChatTopbar.jsx', 'utf-8')

  assert.match(source, /tooltip=/)
  assert.match(source, /group-hover:opacity-100/)
  assert.match(source, /backdrop-blur-xl/)
  assert.match(source, /rotate-45/)
  assert.match(source, /<svg/)
  assert.doesNotMatch(source, /⌫|⇩/)
  assert.match(source, /onOpenModelConfig/)
  assert.match(source, /配置模型供应商与可用模型/)
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

test('backendClient 暴露模型配置读取与保存接口', () => {
  const source = readFileSync('src/api/backendClient.js', 'utf-8')

  assert.match(source, /getModelConfig/)
  assert.match(source, /saveModelConfig/)
  assert.match(source, /testProviderConnection/)
  assert.match(source, /discoverProviderModels/)
})

test('CoachTab 会挂载模型设置弹窗并在保存后刷新模型列表', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /ModelConfigDialog/)
  assert.match(source, /handleOpenModelConfig/)
  assert.match(source, /client\.getModelConfig\(\)/)
  assert.match(source, /client\.saveModelConfig\(nextConfig\)/)
  assert.match(source, /buildModelRuntimeView\(await client\.getModels\(\)\)/)
  assert.match(source, /handleTestProviderConnection/)
  assert.match(source, /handleDiscoverProviderModels/)
})

test('ModelSelector 支持模型级 thinking 强度选项', () => {
  const source = readFileSync('src/components/coach/ModelSelector.jsx', 'utf-8')

  assert.match(source, /thinkingCapability/)
  assert.match(source, /intensityOptions/)
  assert.match(source, /defaultIntensity/)
  assert.match(source, /option\.label \|\| option\.id/)
})

test('模型设置弹窗源码包含测试连接与发现模型入口', () => {
  const dialogSource = readFileSync('src/components/coach/ModelConfigDialog.jsx', 'utf-8')
  const editorSource = readFileSync('src/components/coach/ProviderConfigEditor.jsx', 'utf-8')
  const pickerSource = readFileSync('src/components/coach/ProviderModelPicker.jsx', 'utf-8')

  assert.match(dialogSource, /handleTestProvider/)
  assert.match(dialogSource, /handleDiscoverProvider/)
  assert.match(dialogSource, /onDiscoverProviderModels/)
  assert.match(editorSource, /测试连接/)
  assert.match(editorSource, /发现模型/)
  assert.match(editorSource, /wireApi/)
  assert.match(editorSource, /apiPathMode/)
  assert.match(editorSource, /Chat Completions/)
  assert.match(editorSource, /Responses/)
  assert.match(pickerSource, /发现模型/)
  assert.match(pickerSource, /onDiscover/)
})
