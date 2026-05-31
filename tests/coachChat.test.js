import assert from 'node:assert/strict'
import test from 'node:test'

import { requestCoachReply, requestCoachReplyStream } from '../src/utils/coachChat.js'

test('requestCoachReply 会先构建 system prompt 再调用聊天请求，并返回纯文本解析结果', async () => {
  const calls = []

  const reply = await requestCoachReply(
    {
      chatHistory: [{ role: 'assistant', content: '之前建议先保守一点。' }],
      userInput: '最近疲劳度有点高，要不要调整计划？',
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
        return {
          text: '先把下周一主项容量降一点。',
          suggestion: null,
        }
      },
    },
  )

  assert.deepEqual(reply, {
    text: '先把下周一主项容量降一点。',
    suggestion: null,
  })
  assert.equal(calls.length, 2)
  assert.deepEqual(calls[1], [
    { role: 'system', content: 'SYSTEM_PROMPT' },
    { role: 'assistant', content: '之前建议先保守一点。' },
    { role: 'user', content: '最近疲劳度有点高，要不要调整计划？' },
  ])
})

test('requestCoachReply 在 AI 返回合法 JSON 建议时保留 suggestion 结构', async () => {
  const reply = await requestCoachReply(
    {
      chatHistory: [],
      userInput: '这周周一深蹲要不要改轻一点？',
      profile: {},
      weeklyPlan: {},
      dailyLog: {},
    },
    {
      buildPromptImpl: () => 'SYSTEM_PROMPT',
      requestImpl: async () => ({
        text: '建议先降低深蹲强度，优先恢复动作质量。',
        suggestion: {
          suggest_plan_update: true,
          day: 'Monday',
          summary: '降低深蹲强度',
          changes: [
            {
              action: 'update',
              exerciseName: '深蹲',
              field: 'pct',
              oldValue: 0.75,
              newValue: 0.7,
            },
          ],
        },
      }),
    },
  )

  assert.equal(reply.text, '建议先降低深蹲强度，优先恢复动作质量。')
  assert.deepEqual(reply.suggestion, {
    suggest_plan_update: true,
    day: 'Monday',
    summary: '降低深蹲强度',
    changes: [
      {
        action: 'update',
        exerciseName: '深蹲',
        field: 'pct',
        oldValue: 0.75,
        newValue: 0.7,
      },
    ],
  })
})

test('requestCoachReplyStream 会把流式文本拼成最终回复并保留 suggestion 结构', async () => {
  const streamSnapshots = []

  const reply = await requestCoachReplyStream(
    {
      chatHistory: [],
      userInput: '这周周一深蹲要不要改轻一点？',
      profile: {},
      weeklyPlan: {},
      dailyLog: {},
    },
    {
      buildPromptImpl: () => 'SYSTEM_PROMPT',
      streamImpl: async (messages, { onDelta }) => {
        assert.deepEqual(messages, [
          { role: 'system', content: 'SYSTEM_PROMPT' },
          { role: 'user', content: '这周周一深蹲要不要改轻一点？' },
        ])

        const chunks = ['建议先降低深蹲强度，', '优先恢复动作质量。']
        let fullText = ''

        chunks.forEach((chunk) => {
          fullText += chunk
          onDelta(chunk, fullText)
        })

        return {
          text: fullText,
          suggestion: {
            suggest_plan_update: true,
            day: 'Monday',
            summary: '降低深蹲强度',
            changes: [
              {
                action: 'update',
                exerciseName: '深蹲',
                field: 'pct',
                oldValue: 0.75,
                newValue: 0.7,
              },
            ],
          },
        }
      },
      onText: (text) => {
        streamSnapshots.push(text)
      },
    },
  )

  assert.deepEqual(streamSnapshots, [
    '建议先降低深蹲强度，',
    '建议先降低深蹲强度，优先恢复动作质量。',
  ])
  assert.equal(reply.text, '建议先降低深蹲强度，优先恢复动作质量。')
  assert.deepEqual(reply.suggestion, {
    suggest_plan_update: true,
    day: 'Monday',
    summary: '降低深蹲强度',
    changes: [
      {
        action: 'update',
        exerciseName: '深蹲',
        field: 'pct',
        oldValue: 0.75,
        newValue: 0.7,
      },
    ],
  })
})
