# FitLoop MVP 最小验证清单

## 1. 文档目的

本文档用于记录 FitLoop MVP 在 Sprint 3 / Sprint 4 完成后的最小验证结果，供课程报告直接引用。当前记录以**已实际执行的自动化测试与构建结果**为主；凡是**尚未实际跑到浏览器端交互**的部分，都会明确标注证据边界，留给最终手动验收补充。

## 2. 本轮已执行验证

- 执行时间：2026-05-30
- 执行命令：`npm test`
- 执行结果：`34` 个测试全部通过，`0` 失败
- 执行命令：`npm run build`
- 执行结果：Vite 生产构建成功

以上结果说明：当前代码至少已经通过核心工具函数、AI 调用封装、建议解析、建议采纳写回、聊天历史、prompt 预览与构建链路的自动化验证，且前端可完成生产构建。

## 3. 核心成功路径

### 3.1 成功路径：今日日志 -> AI 建议 -> 采纳建议 -> 写回训练计划

- 前置数据
  - 用户档案已存在，包含基础信息与 1RM。
  - 周计划中 `Monday` 存在动作 `深蹲`，原始 `pct = 0.75`。
  - 今日日志中存在疲劳度等训练上下文。
  - AI 返回正文 + `---JSON---` 结构化建议，建议把 `Monday / 深蹲 / pct` 从 `0.75` 调整为 `0.7`。

- 操作步骤
  1. 保存今日日志，生成新的 `fitloop_dailyLog` 数据。
  2. 发送 AI 教练消息，请求训练调整建议。
  3. 系统在发送前构建 `system prompt`，将档案、周计划、日志与 TDEE 注入请求上下文。
  4. AI 回复被解析为“文本正文 + suggestion”。
  5. 用户点击“采纳并更新计划”。
  6. 系统按 suggestion 中的 `day / changes` 更新 `weeklyPlan`。

- 预期结果
  - 今日日志写入当天日期键，不覆盖其他日期记录。
  - AI 请求前会拼出完整上下文。
  - AI 的结构化建议能被解析出来。
  - 采纳后训练计划被更新，且只更新目标动作字段。
  - 旧计划对象不被原地污染。

- 实际结果
  - 已通过自动化测试验证整条代码链路中的关键节点：
    - `tests/dailyLog.test.js`：确认今日日志按当天日期写回，且不影响其他日期。
    - `tests/prompt.test.js`：确认 prompt 包含档案、计划、日志、TDEE 等上下文。
    - `tests/coachChat.test.js`：确认发送前先构建 `system prompt`，并能保留 AI 返回的 suggestion 结构。
    - `tests/aiResponse.test.js`：确认正文与 JSON 建议可正确拆分。
    - `tests/adoptPlan.test.js`：确认采纳后 `Monday` 的 `深蹲 pct` 从 `0.75` 更新为 `0.7`，且其他动作字段保持不变。
  - `npm test` 与 `npm run build` 均成功，说明该闭环所依赖的现有模块在当前代码状态下可通过自动化验证并完成构建。
  - 证据边界：**本轮未实际执行浏览器内“填写表单 -> 点击发送 -> 点击采纳”的手工链路**，因此页面层提示文案、按钮交互与 localStorage 实际落盘效果仍需最终人工验收补录。

- 证据来源
  - 自动化测试：`tests/dailyLog.test.js`、`tests/prompt.test.js`、`tests/coachChat.test.js`、`tests/aiResponse.test.js`、`tests/adoptPlan.test.js`
  - 构建结果：`npm run build` 成功

## 4. 边界情况

### 4.1 边界情况 A：今天是休息日时，prompt 中训练消耗应为 0

- 前置数据
  - 当天训练计划为 `rest`。
  - 周计划中另一天包含固定重量动作，用于确认非百分比动作信息不会丢失。

- 操作步骤
  1. 构造“当天为休息日”的周计划数据。
  2. 调用 `buildSystemPrompt()` 生成 AI 发送前上下文。

- 预期结果
  - prompt 中训练消耗显示为 `0kcal`。
  - 固定重量动作仍能正常显示，不因休息日逻辑被破坏。

- 实际结果
  - `tests/prompt.test.js` 已验证：
    - prompt 包含固定重量动作信息；
    - 训练量估算消耗为 `0kcal`。
  - 证据边界：当前仅验证 prompt 构建逻辑，尚未在浏览器 UI 中逐项核对“当前上下文预览”的展示文案。

- 证据来源
  - 自动化测试：`tests/prompt.test.js`

### 4.2 边界情况 B：新用户没有历史日志时，AI 上下文构建不崩溃

- 前置数据
  - 用户档案为空或仅部分填写。
  - `weeklyPlan` 为空。
  - `dailyLog` 为空。

- 操作步骤
  1. 使用空档案、空周计划、空日志调用 `buildSystemPrompt()`。

- 预期结果
  - 系统返回兜底文案，而不是抛错。
  - prompt 中能明确显示“暂无记录 / 未记录”等占位信息。

- 实际结果
  - `tests/prompt.test.js` 已验证空数据场景下不会报错，并会返回“暂无记录”“未记录”等兜底内容。
  - 证据边界：当前只能证明 AI 上下文构建函数安全；尚未实际验证浏览器端新用户首次进入 AI 教练页时的完整展示效果。

- 证据来源
  - 自动化测试：`tests/prompt.test.js`

### 4.3 边界情况 C：AI 只返回纯文本时，不应渲染采纳卡片

- 前置数据
  - AI 返回普通文本回复，不包含 `---JSON---` 建议块。

- 操作步骤
  1. 调用 `parseAiResponse()` 解析纯文本回复。
  2. 调用 `requestCoachReply()` 模拟一次正常 AI 请求。
  3. 检查返回结果中的 `suggestion`。

- 预期结果
  - 返回文本内容正常展示。
  - `suggestion = null`，后续页面不应出现采纳卡片。

- 实际结果
  - `tests/aiResponse.test.js` 已验证纯文本回复会被完整保留，`suggestion` 为 `null`。
  - `tests/coachChat.test.js` 已验证 `requestCoachReply()` 在纯文本场景下返回 `{ text, suggestion: null }`。
  - 证据边界：当前没有实际浏览器截图或 DOM 断言来证明“卡片确实未渲染”；这里只能证明驱动 UI 的数据结果符合预期。

- 证据来源
  - 自动化测试：`tests/aiResponse.test.js`、`tests/coachChat.test.js`

## 5. 失败场景

### 5.1 失败场景：采纳的 AI 建议指向不存在的动作，训练计划不得发生部分写回

- 前置数据
  - `Monday` 的原始周计划存在 `深蹲`，但不存在建议中的另一个目标动作（如 `卧推`）。
  - AI suggestion 同时包含：
    - 一条对已存在动作的更新；
    - 一条对不存在动作的更新。

- 操作步骤
  1. 调用 `adoptPlanChange(defaultWeeklyPlan, 'Monday', changes)`。
  2. 让 `changes` 中包含一个合法动作更新和一个非法动作更新。

- 预期结果
  - 系统返回失败结果。
  - 给出“找不到目标动作”的明确提示。
  - `weeklyPlan` 保持原样，不产生部分写回。

- 实际结果
  - `tests/adoptPlan.test.js` 已验证：
    - 返回 `ok: false`；
    - 返回明确错误消息；
    - 原始 `defaultWeeklyPlan.Monday.exercises[0].pct` 仍保持 `0.75`，说明没有发生部分写回。
  - 证据边界：当前尚未在页面层实际点击“采纳并更新计划”并观察失败提示，因此 UI 提示位置与交互反馈仍待最终手动验收确认。

- 证据来源
  - 自动化测试：`tests/adoptPlan.test.js`

## 6. 当前结论

从最小验证角度看，FitLoop MVP 已具备进入课程演示准备阶段的基础条件：

- 核心闭环中最关键的代码链路已有自动化证据支撑。
- 3 条边界情况与 1 条失败场景均已有明确证据来源。
- 当前剩余的不确定性主要集中在**浏览器端人工验收层**，而不是核心工具函数或业务链路本身。

## 7. 待最终手动验收补充

以下内容本轮**没有实际跑到浏览器交互层**，建议主代理在最终验收时补充截图、录屏或操作日志：

- 表单填写、按钮点击、页面提示文案的真实展示结果。
- AI 教练页“当前上下文预览”的展开/折叠与文案展示效果。
- 采纳成功后计划页数据的页面级刷新结果。
- 采纳失败后卡片是否保留、错误提示是否清晰可见。
- localStorage 中 `fitloop_dailyLog / fitloop_weeklyPlan / fitloop_chatHistory` 的实际浏览器落盘结果。
