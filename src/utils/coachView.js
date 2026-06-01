const COACH_EMPTY_QUESTIONS = [
  { id: 'recovery', label: '恢复分析', text: '分析今天的训练恢复状况' },
  { id: 'nutrition', label: '营养检查', text: '帮我检查本周蛋白质摄入' },
  { id: 'intensity', label: '强度优化', text: '优化今天深蹲的训练强度' },
  { id: 'volume', label: '容量评估', text: '评估一下这周的总体训练容量' },
]

function normalizeText(value, fallback) {
  if (typeof value !== 'string') {
    return fallback
  }

  const trimmed = value.trim()
  return trimmed || fallback
}

export function buildSessionTitleFromPrompt(prompt = '') {
  return normalizeText(String(prompt || '').replace(/\s+/g, ' '), '新对话').slice(0, 48)
}

function formatSessionUpdatedAt(updatedAt) {
  if (!updatedAt) {
    return ''
  }

  const date = new Date(updatedAt)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/**
 * 流式回复末尾可能带结构化 JSON，本函数只保留用户应该先看到的自然语言部分。
 */
export function getVisibleStreamText(fullText = '') {
  const markerIndex = fullText.indexOf('---JSON---')

  if (markerIndex === -1) {
    return fullText
  }

  return fullText.slice(0, markerIndex).trimEnd()
}

/**
 * 当前 MVP 还没有真正的多会话存储，所以这里把历史用户提问整理成“假多会话”列表。
 * 这样 Task 2 先把侧栏骨架站稳，Task 3 再决定是否接真实会话模型。
 */
export function buildCoachHistoryView(chatHistory = [], options = {}) {
  const activeSessionId = options.activeSessionId || null
  const sessions = chatHistory
    .map((message, originalIndex) => ({ message, originalIndex }))
    .filter(({ message }) => message?.role === 'user')
    .slice(-6)
    .reverse()
    .map(({ message, originalIndex }, index) => {
      const title = normalizeText(message.content, '新的对话')
      // 使用原始 chatHistory 位置生成临时会话 id，新增消息时旧历史项不会因展示排序漂移。
      const id = `session-message-${originalIndex}`

      return {
        id,
        title,
        isActive: activeSessionId ? activeSessionId === id : index === 0,
        isPlaceholder: false,
      }
    })

  if (!sessions.length) {
    return {
      groups: [
        {
          label: '最近对话',
          items: [
            {
              id: 'session-empty',
              title: '开始新的对话',
              isActive: true,
              isPlaceholder: true,
            },
          ],
        },
      ],
    }
  }

  return {
    groups: [
      {
        label: '最近对话',
        items: sessions,
      },
    ],
  }
}

export function buildCoachSessionView(sessions = [], options = {}) {
  const activeSessionId = options.activeSessionId ?? null
  const normalizedSessions = sessions
    .map((session) => ({
      id: session?.id,
      title: normalizeText(session?.title, '新对话'),
      updatedAt: session?.updatedAt ?? session?.updated_at ?? null,
      updatedAtLabel: formatSessionUpdatedAt(session?.updatedAt ?? session?.updated_at ?? null),
      canDelete: true,
      isPlaceholder: false,
    }))
    .filter((session) => Number.isInteger(session.id))

  if (!normalizedSessions.length) {
    return {
      groups: [
        {
          label: '最近对话',
          items: [
            {
              id: 'session-empty',
              title: '开始新的对话',
              subtitle: '新建后会保留在这里',
              isActive: true,
              isPlaceholder: true,
            },
          ],
        },
      ],
    }
  }

  return {
    groups: [
      {
        label: '最近对话',
        items: normalizedSessions.map((session, index) => ({
          ...session,
          isActive:
            activeSessionId === null || activeSessionId === undefined
              ? index === 0
              : session.id === activeSessionId,
          subtitle: session.updatedAtLabel || '最近更新',
        })),
      },
    ],
  }
}

/**
 * 空状态建议问题保持固定四项，组件每次渲染都返回新对象，避免意外共享引用。
 */
export function getCoachEmptyQuestionView() {
  return COACH_EMPTY_QUESTIONS.map((item) => ({ ...item }))
}
