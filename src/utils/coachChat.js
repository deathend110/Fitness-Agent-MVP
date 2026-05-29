import { requestDeepSeekChat, streamDeepSeekChat } from '../api/deepseek.js'
import { parseAiResponse } from './aiResponse.js'
import { buildSystemPrompt } from './prompt.js'

function buildCoachMessages({ chatHistory = [], dailyLog = {}, profile = {}, userInput = '', weeklyPlan = {} }, buildPromptImpl) {
  const systemPrompt = buildPromptImpl(profile, weeklyPlan, dailyLog)

  return [
    { role: 'system', content: systemPrompt },
    ...chatHistory,
    { role: 'user', content: userInput.trim() },
  ]
}

export async function requestCoachReply(
  { chatHistory = [], dailyLog = {}, profile = {}, userInput = '', weeklyPlan = {} },
  { buildPromptImpl = buildSystemPrompt, requestImpl = requestDeepSeekChat } = {},
) {
  const messages = buildCoachMessages(
    { chatHistory, dailyLog, profile, userInput, weeklyPlan },
    buildPromptImpl,
  )
  const content = await requestImpl(messages)

  return parseAiResponse(content)
}

// 流式模式下每拿到一段新文本就往上抛，让页面能实时刷新回复内容。
export async function requestCoachReplyStream(
  { chatHistory = [], dailyLog = {}, profile = {}, userInput = '', weeklyPlan = {} },
  {
    buildPromptImpl = buildSystemPrompt,
    onText,
    streamImpl = streamDeepSeekChat,
  } = {},
) {
  const messages = buildCoachMessages(
    { chatHistory, dailyLog, profile, userInput, weeklyPlan },
    buildPromptImpl,
  )
  const content = await streamImpl(messages, {
    onDelta: (_delta, fullText) => {
      onText?.(fullText)
    },
  })

  return parseAiResponse(content)
}
