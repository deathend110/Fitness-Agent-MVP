import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

test('MessageAttachmentCard 源码包含标准版附件信息展示', () => {
  const source = readFileSync('src/components/coach/MessageAttachmentCard.jsx', 'utf-8')

  assert.match(source, /originalName/)
  assert.match(source, /sizeBytes/)
  assert.match(source, /XLSX/)
  assert.match(source, /DOCX/)
  assert.match(source, /IMG/)
  assert.match(source, /KB/)
  assert.match(source, /MB/)
})

test('MessageBubble 只在用户消息有 attachments 时渲染附件卡片区', () => {
  const source = readFileSync('src/components/coach/MessageBubble.jsx', 'utf-8')

  assert.match(source, /MessageAttachmentCard/)
  assert.match(source, /const attachments = Array\.isArray\(message\.attachments\) \? message\.attachments : \[\]/)
  assert.match(source, /isUser && attachments\.length/)
  assert.match(source, /attachments\.map\(\(attachment, index\) =>/)
})
