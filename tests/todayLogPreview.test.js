import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

test('今日日志预览稿包含记录优先工作台的核心区块与真实字段文案', () => {
  const source = readFileSync('docs/today-log-page-preview.html', 'utf8')

  assert.match(source, /今日日志/)
  assert.match(source, /今天的数据录入/)
  assert.match(source, /身体数据/)
  assert.match(source, /摄入记录/)
  assert.match(source, /恢复与状态/)
  assert.match(source, /体重/)
  assert.match(source, /热量/)
  assert.match(source, /蛋白质/)
  assert.match(source, /睡眠/)
  assert.match(source, /步数/)
  assert.match(source, /TDEE/)
  assert.match(source, /疲劳度/)
  assert.match(source, /今天已完成训练/)
  assert.match(source, /训练备注/)
  assert.match(source, /今日复杂指标/)
  assert.match(source, /已保存摘要/)
  assert.match(source, /体重趋势/)
  assert.match(source, /今日计划/)
  assert.match(source, /查看 AI 教练/)
})
