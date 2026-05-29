const JSON_SEPARATOR = '---JSON---'

/**
 * 解析 AI 回复中的正文与结构化建议。
 * 若 JSON 无法安全解析，则整段内容按纯文本回退，避免页面消费时崩溃。
 */
export function parseAiResponse(content) {
  const rawContent = typeof content === 'string' ? content : ''
  const separatorIndex = rawContent.indexOf(JSON_SEPARATOR)

  if (separatorIndex === -1) {
    return {
      text: rawContent.trim(),
      suggestion: null,
    }
  }

  const text = rawContent.slice(0, separatorIndex).trim()
  const jsonText = rawContent.slice(separatorIndex + JSON_SEPARATOR.length).trim()

  try {
    return {
      text,
      suggestion: JSON.parse(jsonText),
    }
  } catch {
    return {
      text: rawContent,
      suggestion: null,
    }
  }
}
