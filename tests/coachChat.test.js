import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getBackgroundCoachTask,
  requestCoachReply,
  requestCoachReplyStream,
  shouldFallbackCoachStream,
  startBackgroundCoachReply,
} from '../src/utils/coachChat.js'

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

test('shouldFallbackCoachStream 只允许在尚未收到流式文本时回退普通请求', () => {
  assert.equal(shouldFallbackCoachStream({ hasReceivedText: false }), true)
  assert.equal(shouldFallbackCoachStream({ hasReceivedText: true }), false)
  assert.equal(shouldFallbackCoachStream({ hasReceivedText: false, isBackgroundFallback: true }), false)
})

test('requestCoachReply 和 requestCoachReplyStream 会把 AbortSignal 传给底层请求', async () => {
  const controller = new AbortController()

  await requestCoachReply(
    {
      chatHistory: [],
      userInput: '测试 signal',
      profile: {},
      weeklyPlan: {},
      dailyLog: {},
      sessionId: 5,
    },
    {
      buildPromptImpl: () => 'SYSTEM_PROMPT',
      requestImpl: async (_messages, options) => {
        assert.equal(options.sessionId, 5)
        assert.equal(options.signal, controller.signal)
        return { text: '普通回复', suggestion: null }
      },
      signal: controller.signal,
    },
  )

  await requestCoachReplyStream(
    {
      chatHistory: [],
      userInput: '测试 stream signal',
      profile: {},
      weeklyPlan: {},
      dailyLog: {},
      sessionId: 6,
    },
    {
      buildPromptImpl: () => 'SYSTEM_PROMPT',
      streamImpl: async (_messages, options) => {
        assert.equal(options.sessionId, 6)
        assert.equal(options.signal, controller.signal)
        return { text: '流式回复', suggestion: null }
      },
      signal: controller.signal,
    },
  )
})

test('startBackgroundCoachReply 会复用上下文构建逻辑提交后台任务', async () => {
  const result = await startBackgroundCoachReply(
    {
      chatHistory: [{ role: 'assistant', content: '先休息。' }],
      userInput: '离页后继续分析',
      profile: { basic: { name: '测试用户' } },
      weeklyPlan: { Friday: { type: '拉日', exercises: [] } },
      dailyLog: { '2026-05-31': { fatigue: 5 } },
      sessionId: 9,
    },
    {
      buildPromptImpl: () => 'SYSTEM_PROMPT',
      submitImpl: async (messages, options) => {
        assert.equal(options.sessionId, 9)
        assert.deepEqual(messages, [
          { role: 'system', content: 'SYSTEM_PROMPT' },
          { role: 'assistant', content: '先休息。' },
          { role: 'user', content: '离页后继续分析' },
        ])
        return { taskId: 'task-1', sessionId: 9 }
      },
    },
  )

  assert.deepEqual(result, { taskId: 'task-1', sessionId: 9 })
})

test('getBackgroundCoachTask 会转交后台任务查询实现', async () => {
  const result = await getBackgroundCoachTask('task-1', {
    getTaskImpl: async (taskId) => {
      assert.equal(taskId, 'task-1')
      return { taskId, status: 'not_found', result: null, message: '未找到对应的后台思考任务。' }
    },
  })

  assert.deepEqual(result, {
    taskId: 'task-1',
    status: 'not_found',
    result: null,
    message: '未找到对应的后台思考任务。',
  })
})
