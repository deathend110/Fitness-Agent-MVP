import assert from 'node:assert/strict'
import test from 'node:test'

import { requestCoachReply } from '../src/utils/coachChat.js'

test('requestCoachReply 会先构建 system prompt 再调用聊天请求', async () => {
  const calls = []

  const reply = await requestCoachReply(
    {
      chatHistory: [{ role: 'assistant', content: '之前建议' }],
      userInput: '最近疲劳度有点高，要不要调整计划',
      profile: { basic: { name: '测试用户' } },
      weeklyPlan: { Monday: { type: '腿日', exercises: [] } },
      dailyLog: { '2026-05-30': { fatigue: 4 } },
    },
    {
      buildPromptImpl: (profile, weeklyPlan, dailyLog) => {
        calls.push({ profile, weeklyPlan, dailyLog })
        return 'SYSTEM_PROMPT'
      },
      requestImpl: async (messages) => {
        calls.push(messages)
        return '先把下周一主项容量降一点。'
      },
    },
  )

  assert.equal(reply, '先把下周一主项容量降一点。')
  assert.equal(calls.length, 2)
  assert.deepEqual(calls[1], [
    { role: 'system', content: 'SYSTEM_PROMPT' },
    { role: 'assistant', content: '之前建议' },
    { role: 'user', content: '最近疲劳度有点高，要不要调整计划' },
  ])
})
