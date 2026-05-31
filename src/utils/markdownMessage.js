const SAFE_LINK_PROTOCOLS = ['http:', 'https:', 'mailto:']

export function sanitizeMarkdownHref(href = '') {
  const trimmed = href.trim()

  if (!trimmed) {
    return ''
  }

  try {
    const url = new URL(trimmed, 'https://fitloop.local')
    if (trimmed.startsWith('/') || SAFE_LINK_PROTOCOLS.includes(url.protocol)) {
      return trimmed
    }
  } catch {
    return ''
  }

  return ''
}

export function parseMarkdownMessage(markdown = '') {
  const lines = String(markdown || '').split(/\r?\n/)
  const blocks = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]

    if (!line.trim()) {
      index += 1
      continue
    }

    if (line.trim().startsWith('```')) {
      const codeLines = []
      index += 1
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index])
        index += 1
      }
      index += index < lines.length ? 1 : 0
      blocks.push({ type: 'code', text: codeLines.join('\n') })
      continue
    }

    const tableBlock = readTableBlock(lines, index)
    if (tableBlock) {
      blocks.push({ type: 'code', text: tableBlock.text })
      index = tableBlock.nextIndex
      continue
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      blocks.push({
        type: 'heading',
        level: heading[1].length,
        children: parseInlineMarkdown(heading[2]),
      })
      index += 1
      continue
    }

    const listBlock = readListBlock(lines, index)
    if (listBlock) {
      blocks.push(listBlock.block)
      index = listBlock.nextIndex
      continue
    }

    const paragraphLines = [line]
    index += 1
    while (
      index < lines.length &&
      lines[index].trim() &&
      !isBlockStart(lines[index])
    ) {
      paragraphLines.push(lines[index])
      index += 1
    }
    blocks.push({ type: 'paragraph', children: parseInlineMarkdown(paragraphLines.join('\n')) })
  }

  return blocks
}

export function parseInlineMarkdown(text = '') {
  const segments = []
  const pattern = /(\*\*([^*]+)\*\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)]+)\))/g
  let cursor = 0
  let match

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      segments.push({ type: 'text', text: text.slice(cursor, match.index) })
    }

    if (match[2]) {
      segments.push({ type: 'strong', text: match[2] })
    } else if (match[4]) {
      segments.push({ type: 'code', text: match[4] })
    } else if (match[6]) {
      const href = sanitizeMarkdownHref(match[7])
      segments.push(href ? { type: 'link', text: match[6], href } : { type: 'text', text: match[6] })
    }
    cursor = pattern.lastIndex
  }

  if (cursor < text.length) {
    segments.push({ type: 'text', text: text.slice(cursor) })
  }

  return segments.length ? segments : [{ type: 'text', text }]
}

function isBlockStart(line = '') {
  const trimmed = line.trim()
  return (
    trimmed.startsWith('```') ||
    /^#{1,3}\s+/.test(trimmed) ||
    /^[-*]\s+/.test(trimmed) ||
    /^\d+\.\s+/.test(trimmed)
  )
}

function readListBlock(lines, startIndex) {
  const first = lines[startIndex].trim()
  const ordered = /^\d+\.\s+/.test(first)
  const unordered = /^[-*]\s+/.test(first)

  if (!ordered && !unordered) {
    return null
  }

  const items = []
  let index = startIndex
  const matcher = ordered ? /^\d+\.\s+(.+)$/ : /^[-*]\s+(.+)$/

  while (index < lines.length) {
    const match = lines[index].trim().match(matcher)
    if (!match) {
      break
    }
    items.push({ children: parseInlineMarkdown(match[1]) })
    index += 1
  }

  return { block: { type: 'list', ordered, items }, nextIndex: index }
}

function readTableBlock(lines, startIndex) {
  if (!lines[startIndex].includes('|')) {
    return null
  }

  const tableLines = []
  let index = startIndex
  while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
    tableLines.push(lines[index])
    index += 1
  }

  if (tableLines.length < 2) {
    return null
  }

  return { text: tableLines.join('\n'), nextIndex: index }
}
