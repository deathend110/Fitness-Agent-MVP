import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  parseMarkdownMessage,
  sanitizeMarkdownHref,
} from '../src/utils/markdownMessage.js'

test('parseMarkdownMessage 支持标题、列表、加粗、行内代码和代码块', () => {
  const blocks = parseMarkdownMessage(`# 训练建议

- **深蹲** 保留 \`RPE 7\`
1. 热身

\`\`\`
sets x reps
\`\`\``)

  assert.equal(blocks[0].type, 'heading')
  assert.equal(blocks[0].level, 1)
  assert.equal(blocks[1].type, 'list')
  assert.equal(blocks[1].ordered, false)
  assert.deepEqual(blocks[1].items[0].children.map((item) => item.type), ['strong', 'text', 'code'])
  assert.equal(blocks[2].type, 'list')
  assert.equal(blocks[2].ordered, true)
  assert.equal(blocks[3].type, 'code')
})

test('parseMarkdownMessage 支持表格并保留单元格内联 markdown', () => {
  const blocks = parseMarkdownMessage(`| 动作 | 建议 |
| :--- | ---: |
| **深蹲** | \`RPE 7\` |
| 卧推 | 保持容量 |`)

  assert.equal(blocks[0].type, 'table')
  assert.deepEqual(blocks[0].alignments, ['left', 'right'])
  assert.equal(blocks[0].headers[0][0].type, 'text')
  assert.equal(blocks[0].headers[0][0].text, '动作')
  assert.equal(blocks[0].rows[0][0][0].type, 'strong')
  assert.equal(blocks[0].rows[0][0][0].text, '深蹲')
  assert.equal(blocks[0].rows[0][1][0].type, 'code')
  assert.equal(blocks[0].rows[0][1][0].text, 'RPE 7')
})

test('parseMarkdownMessage 会把独立成行的 --- 解析为分割线', () => {
  const blocks = parseMarkdownMessage(`训练建议

---

明天再评估`)

  assert.equal(blocks[0].type, 'paragraph')
  assert.equal(blocks[1].type, 'divider')
  assert.equal(blocks[2].type, 'paragraph')
})

test('parseMarkdownMessage 不把原始 HTML 当作可执行内容', () => {
  const blocks = parseMarkdownMessage('<script>alert(1)</script>')

  assert.equal(blocks[0].type, 'paragraph')
  assert.equal(blocks[0].children[0].text, '<script>alert(1)</script>')
})

test('危险链接协议会降级为纯文本', () => {
  assert.equal(sanitizeMarkdownHref('javascript:alert(1)'), '')
  assert.equal(sanitizeMarkdownHref('data:text/html;base64,abc'), '')
  assert.equal(sanitizeMarkdownHref('https://example.com'), 'https://example.com')
})

test('MarkdownMessage 组件不使用 dangerouslySetInnerHTML', () => {
  const source = readFileSync('src/components/coach/MarkdownMessage.jsx', 'utf-8')

  assert.doesNotMatch(source, /dangerouslySetInnerHTML/)
  assert.match(source, /parseMarkdownMessage/)
  assert.match(source, /block\.type === 'table'/)
  assert.match(source, /block\.type === 'divider'/)
  assert.match(source, /<hr/)
  assert.match(source, /<table/)
})
