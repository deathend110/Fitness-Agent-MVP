### Task 4.1 实现 DeepSeek API 封装

- **估时**：45 分钟
- **依赖**：Task 3.3
- **目标**：统一调用 AI 接口。
- **额外提醒**：本节开发涉及deepseek api，请多多查看官方文档[https://api-docs.deepseek.com/  ](https://api-docs.deepseek.com/  )
- **主要操作**：
  - 创建 `src/api/deepseek.js`。
  - 从 `import.meta.env.VITE_DEEPSEEK_API_KEY` 读取 API Key。
  - 使用 `POST https://api.deepseek.com/chat/completions`。
  - 返回 `data.choices[0].message.content`。
  - API Key 缺失、网络失败、非 2xx 响应都返回可展示错误。
- **完成信号**：
  - API 调用函数可被 `CoachTab` 调用。
  - API 失败不会导致页面崩溃。
- **验证方式**：
  - 不配置 `.env` 时，AI 教练显示明确错误提示。

### Task 4.2 实现 AI 教练对话 UI

- **估时**：60 分钟
- **依赖**：Task 4.1
- **目标**：用户能在页面内与 AI 对话。
- **主要操作**：
  - 在 `CoachTab.jsx` 中实现聊天气泡区。
  - 实现输入框和发送按钮。
  - 每次发送前调用 `buildSystemPrompt()`。
  - 保存 `fitloop_chatHistory`，只保留最近 20 条。
  - 请求中显示加载状态，避免重复发送。
- **完成信号**：
  - 用户消息和 AI 回复都出现在对话区。
  - 刷新后历史对话仍保留。
- **验证方式**：
  - 输入“最近疲劳度有点高，要不要调整计划”，确认请求被触发并展示结果。

### Task 4.3 实现上下文预览

- **估时**：30 分钟
- **依赖**：Task 4.2
- **目标**：课堂 demo 时能证明 AI 读取了最新数据。
- **主要操作**：
  - 在 `CoachTab.jsx` 增加“当前上下文预览”折叠区域。
  - 展示本次发送前生成的 system prompt。
  - 默认折叠，点击展开。
- **完成信号**：
  - 展开后能看到档案、训练计划、日志和 TDEE。
- **验证方式**：
  - 修改今日日志后回到 AI 教练，预览内容同步变化。

### Task 4.4 实现 AI 返回 JSON 解析

- **估时**：45 分钟
- **依赖**：Task 4.2
- **目标**：识别 AI 是否给出了结构化训练计划建议。
- **主要操作**：
  - 创建 `src/utils/aiResponse.js`。
  - 实现 `parseAiResponse(content)`。
  - 检测 `---JSON---` 分隔符。
  - 分离正文和 JSON。
  - JSON 解析失败时降级为纯文本展示。
- **完成信号**：
  - 含 JSON 的回复能解析出 `text` 和 `suggestion`。
  - 纯文本回复不生成 suggestion。
  - 错误 JSON 不让页面崩溃。
- **验证方式**：
  - 使用 mock 文本分别测试：纯文本、合法 JSON、非法 JSON。

### Task 4.5 实现采纳建议卡片

- **估时**：60 分钟
- **依赖**：Task 4.4、Task 2.4
- **目标**：用户能看到 AI 建议变更并选择采纳。
- **主要操作**：
  - 创建 `src/components/AdoptCard.jsx`。
  - 显示建议日期、summary 和 changes 对比。
  - 提供“采纳并更新计划”和“忽略”按钮。
  - 组件只负责展示和触发回调，不直接读取 API。
- **完成信号**：
  - AI 回复含合法 JSON 时出现采纳卡片。
  - 点击忽略后卡片消失或标记已忽略。
- **验证方式**：
  - 用 mock AI 回复生成“深蹲 75% -> 70%”卡片，检查展示正确。

### Task 4.6 实现一键采纳写回训练计划

- **估时**：45 分钟
- **依赖**：Task 4.5
- **目标**：完成 FitLoop MVP 的核心闭环。
- **主要操作**：
  - 在 `CoachTab.jsx` 或独立工具函数中实现 `adoptPlanChange(day, changes)`。
  - 从 `fitloop_weeklyPlan` 找到目标日期和动作。
  - 按 `field` 更新 `newValue`。
  - 保存回 localStorage。
  - 写回成功后给用户明确反馈。
- **完成信号**：
  - 点击采纳后，训练计划页中对应动作字段变化。
  - 找不到动作时显示失败提示，不静默失败。
- **验证方式**：
  - 完整跑通：AI mock 返回深蹲 pct 从 0.75 改为 0.70，采纳后训练计划显示新重量。