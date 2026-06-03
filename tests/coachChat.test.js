import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildBackgroundCoachTaskRecord,
  getBackgroundCoachTask,
  mergeCoachReplySuggestion,
  mergeBackgroundCoachReply,
  requestCoachReply,
  requestCoachReplyStream,
  resolveCoachStreamStatusLabel,
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
    proposal: null,
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
  const statusLabels = []
  const proposals = []
  const suggestions = []

  const reply = await requestCoachReplyStream(
    {
      chatHistory: [],
      userInput: '这周周一深蹲要不要改轻一点？',
      profile: {},
      weeklyPlan: {},
      dailyLog: {},
    },
    {
      streamImpl: async (payload, { onDelta, onProposal, onSuggestion, onToolStatus }) => {
        assert.deepEqual(payload, {
          fileIds: [],
          model: undefined,
          sessionId: null,
          thinking: undefined,
          userInput: '这周周一深蹲要不要改轻一点？',
        })

        const chunks = ['建议先降低深蹲强度，', '优先恢复动作质量。']
        let fullText = ''

        onToolStatus({ tool: 'get_weekly_plan', status: 'running' })
        chunks.forEach((chunk) => {
          fullText += chunk
          onDelta(chunk, fullText)
        })
        onProposal({
          proposalId: 'proposal-stream-1',
          day: 'Monday',
          summary: '降低深蹲强度',
        })
        onSuggestion({
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
      onProposal: (proposal) => {
        proposals.push(proposal)
      },
      onStatusLabel: (statusLabel) => {
        statusLabels.push(statusLabel)
      },
      onSuggestion: (suggestion) => {
        suggestions.push(suggestion)
      },
      onText: (text) => {
        streamSnapshots.push(text)
      },
    },
  )

  assert.deepEqual(statusLabels, ['正在读取训练计划'])
  assert.deepEqual(streamSnapshots, [
    '建议先降低深蹲强度，',
    '建议先降低深蹲强度，优先恢复动作质量。',
  ])
  assert.deepEqual(proposals, [
    {
      proposalId: 'proposal-stream-1',
      day: 'Monday',
      summary: '降低深蹲强度',
    },
  ])
  assert.deepEqual(suggestions, [
    {
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
  ])
  assert.equal(reply.text, '建议先降低深蹲强度，优先恢复动作质量。')
  assert.deepEqual(reply.suggestion, {
    proposalId: 'proposal-stream-1',
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

test('requestCoachReplyStream 会用更完整的 suggestion 升级早到的 proposal，并保留 proposalId', async () => {
  const reply = await requestCoachReplyStream(
    {
      userInput: '把周一训练调整得更保守一点',
    },
    {
      streamImpl: async (_payload, { onProposal, onSuggestion, onDelta }) => {
        onProposal({
          proposalId: 'proposal-stream-upgrade',
          day: 'Monday',
          summary: '先降一点主项强度',
        })
        onDelta('建议先降低一点主项强度。', '建议先降低一点主项强度。')
        onSuggestion({
          suggest_plan_update: true,
          day: 'Monday',
          summary: '建议先降低一点主项强度。',
          changes: [
            {
              action: 'update',
              exerciseName: '深蹲',
              field: 'pct',
              oldValue: 0.8,
              newValue: 0.72,
            },
          ],
        })

        return {
          text: '建议先降低一点主项强度。',
          proposal: {
            proposalId: 'proposal-stream-upgrade',
            day: 'Monday',
            summary: '先降一点主项强度',
          },
          suggestion: {
            suggest_plan_update: true,
            day: 'Monday',
            summary: '建议先降低一点主项强度。',
            changes: [
              {
                action: 'update',
                exerciseName: '深蹲',
                field: 'pct',
                oldValue: 0.8,
                newValue: 0.72,
              },
            ],
          },
        }
      },
    },
  )

  assert.deepEqual(reply.suggestion, {
    proposalId: 'proposal-stream-upgrade',
    suggest_plan_update: true,
    day: 'Monday',
    summary: '建议先降低一点主项强度。',
    changes: [
      {
        action: 'update',
        exerciseName: '深蹲',
        field: 'pct',
        oldValue: 0.8,
        newValue: 0.72,
      },
    ],
  })
})

test('resolveCoachStreamStatusLabel 会优先使用 message/label，并为已知工具生成轻量阶段文案', () => {
  assert.equal(resolveCoachStreamStatusLabel(null), '')
  assert.equal(resolveCoachStreamStatusLabel({ message: '读取计划中' }), '读取计划中')
  assert.equal(resolveCoachStreamStatusLabel({ label: '整理上下文中' }), '整理上下文中')
  assert.equal(
    resolveCoachStreamStatusLabel({ tool: 'get_weekly_plan', status: 'running' }),
    '正在读取训练计划',
  )
  assert.equal(
    resolveCoachStreamStatusLabel({ tool: 'unknown_tool', status: 'running' }),
    '正在整理上下文',
  )
  assert.equal(
    resolveCoachStreamStatusLabel({ tool: 'get_profile', status: 'completed' }),
    '',
  )
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
    { role: 'assistant', content: '后台分析完成', suggestion: { day: 'Friday' } },
  ])
  assert.equal(mergeResult.assistantIndex, 1)
  assert.deepEqual(mergeResult.suggestion, { day: 'Friday' })
})

test('mergeBackgroundCoachReply 成功合并时会把 suggestion 持久到 assistant 消息', () => {
  const suggestion = {
    proposalId: 'proposal-bg-1',
    summary: '把周五硬拉改轻',
    day: 'Friday',
    changes: [{ action: 'update', exerciseName: '硬拉', field: 'pct', newValue: 0.65 }],
  }
  const mergeResult = mergeBackgroundCoachReply({
    currentHistory: [{ role: 'user', content: '离页后继续分析' }],
    reply: { text: '建议把硬拉强度下调。', suggestion },
    storedTask: { taskId: 'task-1', userContent: '离页后继续分析' },
  })

  assert.equal(mergeResult.status, 'merged')
  assert.deepEqual(mergeResult.nextHistory.at(-1), {
    role: 'assistant',
    content: '建议把硬拉强度下调。',
    suggestion,
  })
})

test('mergeBackgroundCoachReply 会优先持久化更完整的 suggestion，同时保留 proposalId', () => {
  const mergeResult = mergeBackgroundCoachReply({
    currentHistory: [{ role: 'user', content: '离页后继续分析' }],
    reply: {
      text: '建议把周五硬拉调轻一点。',
      proposal: {
        proposalId: 'proposal-bg-upgrade',
        day: 'Friday',
        summary: '下调硬拉强度',
      },
      suggestion: {
        suggest_plan_update: true,
        day: 'Friday',
        summary: '建议把周五硬拉调轻一点。',
        changes: [
          {
            action: 'update',
            exerciseName: '硬拉',
            field: 'pct',
            oldValue: 0.78,
            newValue: 0.7,
          },
        ],
      },
    },
    storedTask: { taskId: 'task-1', userContent: '离页后继续分析' },
  })

  assert.equal(mergeResult.status, 'merged')
  assert.deepEqual(mergeResult.suggestion, {
    proposalId: 'proposal-bg-upgrade',
    suggest_plan_update: true,
    day: 'Friday',
    summary: '建议把周五硬拉调轻一点。',
    changes: [
      {
        action: 'update',
        exerciseName: '硬拉',
        field: 'pct',
        oldValue: 0.78,
        newValue: 0.7,
      },
    ],
  })
})

test('mergeCoachReplySuggestion 会用更完整的一份作为主体，并补齐 proposalId 等缺失字段', () => {
  assert.deepEqual(
    mergeCoachReplySuggestion(
      {
        proposalId: 'proposal-merge-1',
        day: 'Monday',
        summary: '轻量 proposal',
      },
      {
        suggest_plan_update: true,
        day: 'Monday',
        summary: '完整 suggestion',
        changes: [
          {
            action: 'update',
            exerciseName: '卧推',
            field: 'sets',
            oldValue: 5,
            newValue: 4,
          },
        ],
      },
    ),
    {
      proposalId: 'proposal-merge-1',
      suggest_plan_update: true,
      day: 'Monday',
      summary: '完整 suggestion',
      changes: [
        {
          action: 'update',
          exerciseName: '卧推',
          field: 'sets',
          oldValue: 5,
          newValue: 4,
        },
      ],
    },
  )
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
