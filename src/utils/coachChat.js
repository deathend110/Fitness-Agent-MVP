import { requestDeepSeekChat } from '../api/deepseek.js'
import { parseAiResponse } from './aiResponse.js'
import { buildSystemPrompt } from './prompt.js'

/**
 * 组装一次 AI 教练对话请求，确保每次发送前都注入最新 system prompt。
 * 返回值统一经过解析，页面层只需消费安全文本，后续任务可继续使用 suggestion。
 */
export async function requestCoachReply(
  { chatHistory = [], dailyLog = {}, profile = {}, userInput = '', weeklyPlan = {} },
  { buildPromptImpl = buildSystemPrompt, requestImpl = requestDeepSeekChat } = {},
) {
  const systemPrompt = buildPromptImpl(profile, weeklyPlan, dailyLog)
  const messages = [
    { role: 'system', content: systemPrompt },
    ...chatHistory,
    { role: 'user', content: userInput.trim() },
  ]
  const content = await requestImpl(messages)

  return parseAiResponse(content)
}
