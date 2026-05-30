# Task 9 Agent 功能优化

- **估时**：60 分钟
- **依赖**：Task 8
- **目标**：优化上下文压缩、聊天记录保存和 token 使用效率。
- **主要文件**：
  - `src/utils/chatHistory.js`
  - `src/utils/prompt.js`
  - `src/tabs/CoachTab.jsx`
  - `src/utils/contextSummary.js`（如需新建）
- **主要操作**：
  - 压缩和整理上下文。
  - 保留关键聊天记录。
  - 降低无效 token 消耗。
- **完成信号**：
  - 聊天记录更耐用。
  - 上下文更短但仍保留关键内容。
- **验证方式**：
  - 连续多轮发送消息，确认历史保存与上下文压缩正常。
