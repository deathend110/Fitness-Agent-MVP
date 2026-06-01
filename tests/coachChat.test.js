import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildBackgroundCoachTaskRecord,
  getBackgroundCoachTask,
  mergeBackgroundCoachReply,
  requestCoachReply,
  requestCoachReplyStream,
  shouldShowBackgroundCoachPendingIndicator,
  shouldFallbackCoachStream,
  startBackgroundCoachReply,
} from '../src/utils/coachChat.js'

test('requestCoachReply 会把用户输入交给后端 Agent，不再构建 system prompt', async () => {
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
      requestImpl: async (payload, options) => {
        calls.push({ payload, options })
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
  assert.equal(calls.length, 1)
  assert.deepEqual(calls[0].payload, {
    fileIds: [],
    model: undefined,
    sessionId: null,
    thinking: undefined,
    userInput: '最近疲劳度有点高，要不要调整计划？',
  })
})

test('requestCoachReply 会保留模型和 thinking 配置', async () => {
  await requestCoachReply(
    {
      model: 'deepseek-v4-pro',
      thinking: { enabled: true, budget: 'max' },
      userInput: '深入分析训练计划',
    },
    {
      requestImpl: async (payload) => {
        assert.equal(payload.model, 'deepseek-v4-pro')
        assert.deepEqual(payload.thinking, { enabled: true, budget: 'max' })
        return { text: 'ok', suggestion: null }
      },
    },
  )
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
      streamImpl: async (payload, { onDelta }) => {
        assert.deepEqual(payload, {
          fileIds: [],
          model: undefined,
          sessionId: null,
          thinking: undefined,
          userInput: '这周周一深蹲要不要改轻一点？',
        })

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
      requestImpl: async (payload, options) => {
        assert.equal(payload.userInput, '测试 signal')
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
      streamImpl: async (payload, options) => {
        assert.equal(payload.userInput, '测试 stream signal')
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
      submitImpl: async (payload, options) => {
        assert.equal(options.sessionId, 9)
        assert.equal(payload.userInput, '离页后继续分析')
        assert.deepEqual(payload.fileIds, [])
        return { taskId: 'task-1', sessionId: 9 }
      },
    },
  )

  assert.deepEqual(result, { taskId: 'task-1', sessionId: 9 })
})

test('buildBackgroundCoachTaskRecord 会保存 taskId 和源用户消息用于回页校验', () => {
  const record = buildBackgroundCoachTaskRecord(
    { taskId: 'task-1', sessionId: 9 },
    { sourceUserIndex: 3, userInput: '离页后继续分析' },
  )

  assert.equal(record.taskId, 'task-1')
  assert.equal(record.sessionId, 9)
  assert.equal(record.sourceUserIndex, 3)
  assert.equal(record.userContent, '离页后继续分析')
  assert.equal(typeof record.createdAt, 'string')
})

test('buildBackgroundCoachTaskRecord 缺少 taskId 时返回 null', () => {
  assert.equal(buildBackgroundCoachTaskRecord({}, { userInput: '离页后继续分析' }), null)
})

test('mergeBackgroundCoachReply 只在当前历史仍包含源用户消息时追加 assistant', () => {
  const currentHistory = [{ role: 'user', content: '离页后继续分析' }]
  const mergeResult = mergeBackgroundCoachReply({
    currentHistory,
    reply: { text: '后台分析完成', suggestion: { day: 'Friday' } },
    storedTask: { taskId: 'task-1', userContent: '离页后继续分析' },
  })

  assert.equal(mergeResult.status, 'merged')
  assert.deepEqual(mergeResult.nextHistory, [
    { role: 'user', content: '离页后继续分析' },
    { role: 'assistant', content: '后台分析完成' },
  ])
  assert.equal(mergeResult.assistantIndex, 1)
  assert.deepEqual(mergeResult.suggestion, { day: 'Friday' })
})

test('mergeBackgroundCoachReply 在用户已清空当前聊天时不污染当前对话', () => {
  const mergeResult = mergeBackgroundCoachReply({
    currentHistory: [],
    reply: { text: '后台分析完成', suggestion: null },
    storedTask: { taskId: 'task-1', userContent: '离页后继续分析' },
  })

  assert.equal(mergeResult.status, 'source_user_missing')
  assert.deepEqual(mergeResult.nextHistory, [])
})

test('mergeBackgroundCoachReply 不会把旧后台结果合并到同文本的新用户轮次', () => {
  const mergeResult = mergeBackgroundCoachReply({
    currentHistory: [{ role: 'user', content: '离页后继续分析' }],
    reply: { text: '旧后台分析完成', suggestion: null },
    storedTask: {
      taskId: 'task-1',
      userContent: '离页后继续分析',
      sourceUserIndex: 2,
    },
  })

  assert.equal(mergeResult.status, 'source_user_missing')
  assert.deepEqual(mergeResult.nextHistory, [
    { role: 'user', content: '离页后继续分析' },
  ])
})

test('shouldShowBackgroundCoachPendingIndicator 只在后台任务仍运行且源用户消息存在时显示等待态', () => {
  const currentHistory = [
    { role: 'assistant', content: '之前建议先保守一点。' },
    { role: 'user', content: '离页后继续分析' },
  ]
  const storedTask = {
    taskId: 'task-1',
    sourceUserIndex: 1,
    userContent: '离页后继续分析',
  }

  assert.equal(
    shouldShowBackgroundCoachPendingIndicator({
      currentHistory,
      storedTask,
      taskStatus: 'pending',
    }),
    true,
  )
  assert.equal(
    shouldShowBackgroundCoachPendingIndicator({
      currentHistory,
      storedTask,
      taskStatus: 'running',
    }),
    true,
  )

  for (const taskStatus of ['succeeded', 'failed', 'not_found']) {
    assert.equal(
      shouldShowBackgroundCoachPendingIndicator({
        currentHistory,
        storedTask,
        taskStatus,
      }),
      false,
    )
  }

  assert.equal(
    shouldShowBackgroundCoachPendingIndicator({
      currentHistory: [],
      storedTask,
      taskStatus: 'pending',
    }),
    false,
  )
  assert.equal(
    shouldShowBackgroundCoachPendingIndicator({
      currentHistory: [{ role: 'user', content: '离页后继续分析' }],
      storedTask,
      taskStatus: 'running',
    }),
    false,
  )
  assert.equal(
    shouldShowBackgroundCoachPendingIndicator({
      currentHistory,
      storedTask: { ...storedTask, taskId: '' },
      taskStatus: 'running',
    }),
    false,
  )
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
