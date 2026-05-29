import assert from 'node:assert/strict'
import test from 'node:test'

import { parseAiResponse } from '../src/utils/aiResponse.js'

test('parseAiResponse 在纯文本回复时只返回文本内容', () => {
  const result = parseAiResponse('今天疲劳有点高，建议主项减一组，附件动作维持。')

  assert.equal(result.text, '今天疲劳有点高，建议主项减一组，附件动作维持。')
  assert.equal(result.suggestion, null)
})

test('parseAiResponse 在包含合法 JSON 时拆分正文和建议结构', () => {
  const result = parseAiResponse(`建议把周一深蹲强度略降，优先恢复动作质量。

---JSON---
{
  "suggest_plan_update": true,
  "day": "Monday",
  "summary": "降低深蹲强度并增加次数",
  "changes": [
    {
      "action": "update",
      "exerciseName": "深蹲",
      "field": "pct",
      "oldValue": 0.75,
      "newValue": 0.7
    }
  ]
}`)

  assert.equal(result.text, '建议把周一深蹲强度略降，优先恢复动作质量。')
  assert.deepEqual(result.suggestion, {
    suggest_plan_update: true,
    day: 'Monday',
    summary: '降低深蹲强度并增加次数',
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

test('parseAiResponse 在 JSON 非法时降级为纯文本，不抛出异常', () => {
  const content = `建议先把周一训练改轻一点。

---JSON---
{
  "suggest_plan_update": true,
  "day": "Monday",
`

  assert.doesNotThrow(() => parseAiResponse(content))

  const result = parseAiResponse(content)

  assert.equal(result.text, content)
  assert.equal(result.suggestion, null)
})
