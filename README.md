# FitLoop MVP

FitLoop MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。当前版本优先打通最小闭环：用户档案、周训练计划、今日日志、AI 教练对话，以及发送前可验证的上下文预览。

## 项目简介

- 前端技术栈：Vite + React + Tailwind CSS
- 数据存储：localStorage
- AI 接口：DeepSeek 原生 OpenAI 格式
- 当前已完成的核心能力：
  - 用户档案录入与 1RM 维护
  - 一周训练计划编辑与持久化
  - 今日日志录入、保存与刷新恢复
  - AI 教练聊天输入、发送、加载态与历史持久化
  - 默认折叠的“当前上下文预览”，用于检查本次发送前注入的 system prompt
  - AI 回复中的 `---JSON---` 建议解析与纯文本安全降级
  - AI 返回合法建议 JSON 时渲染采纳卡片，并支持本地忽略

## 环境要求

- Node.js 24.13.1 或兼容版本
- npm 11.8.0 或兼容版本

## 安装命令

```bash
npm install
```

## 运行命令

```bash
npm run dev
```

默认地址通常是 `http://localhost:5173/`。

## API Key 配置

在项目根目录创建 `.env`：

```bash
VITE_DEEPSEEK_API_KEY=你的DeepSeek_API_Key
```

不要提交真实 API Key。

## 测试命令

运行全部当前自动化测试：

```bash
npm test
```

仅运行今日日志相关测试：

```bash
node --test tests/dailyLog.test.js
```

仅运行 system prompt 相关测试：

```bash
node --test tests/prompt.test.js
```

仅运行上下文预览相关测试：

```bash
node --test tests/promptPreview.test.js
```

仅运行聊天链路相关测试：

```bash
node --test tests/chatHistory.test.js tests/coachChat.test.js
```

仅运行 AI 回复解析相关测试：

```bash
node --test tests/aiResponse.test.js tests/coachChat.test.js
```

前端构建验证：

```bash
npm run build
```

## Demo 操作路径

1. 打开首页。
2. 切换到“我的档案”，确认基础信息和三大项 1RM。
3. 切换到“训练计划”，查看或调整本周训练安排。
4. 切换到“今日日志”。
5. 输入当天的体重、热量、蛋白质、睡眠、疲劳度、是否完成训练和训练备注。
6. 点击“保存今日日志”。
7. 观察右侧“已保存摘要”是否同步显示最新数据。
8. 确认“今日计划”按 `weeklyPlan[todayKey]` 只读展示训练类型与动作摘要。
9. 切换到“AI 教练”，确认右侧“当前上下文预览”默认折叠。
10. 点击展开，确认预览中包含用户档案、本周计划、近 7/14 天日志摘要与当日 TDEE。
11. 回到“今日日志”修改训练备注或热量，再切回“AI 教练”，确认预览内容同步变化。
12. 在 AI 教练输入问题并发送，确认聊天流程、加载态和历史持久化仍正常。
13. 使用可返回 `---JSON---` 建议的 AI 回复，确认聊天区下方出现“建议采纳卡片”。
14. 检查卡片中的建议日期、summary 和 changes 前后对比是否正确显示。
15. 点击“忽略”，确认卡片消失；点击“采纳并更新计划”，确认页面出现占位提示但本阶段不会真正写回计划。

## 本地数据键

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`

## Task 4.1 补充说明

- 新增 `src/api/deepseek.js`，统一封装 DeepSeek Chat Completions 调用。
- 默认接口地址为 `https://api.deepseek.com/chat/completions`。
- 默认模型为 `deepseek-v4-flash`。
- `CoachTab` 会显示 API Key 配置状态；若未配置 `.env`，页面会直接提示缺少 `VITE_DEEPSEEK_API_KEY`。

## Task 4.1 测试命令

```bash
node --test tests/deepseek.test.js
```

## Task 4.2 补充说明

- `src/App.jsx` 将 `chatHistory` 维护为可写的顶层 state，并持久化到 `fitloop_chatHistory`。
- `src/tabs/CoachTab.jsx` 接入聊天气泡区、输入框、发送按钮、加载态和页内错误提示。
- 每次发送都会先调用 `buildSystemPrompt()`，再通过 DeepSeek 请求 AI 回复。
- 聊天历史只保留最近 20 条，刷新页面后仍可恢复。
- 缺少 API Key、网络失败或接口报错时，错误会直接显示在 AI 教练页内，不会破坏页面。

## Task 4.2 测试命令

```bash
node --test tests/chatHistory.test.js tests/coachChat.test.js
```

## Task 4.3 补充说明

- `src/components/PromptPreviewPanel.jsx` 将原来的临时预览收敛为默认折叠的“当前上下文预览”面板。
- `src/utils/promptPreview.js` 统一整理预览标题、折叠默认值和本次发送前的 `buildSystemPrompt()` 文本。
- 今日日志变更后，回到 AI 教练页时会基于最新 `profile / weeklyPlan / dailyLog` 重新生成预览。

## Task 4.3 测试命令

```bash
node --test tests/promptPreview.test.js
```

## Task 4.4 补充说明

- 新增 `src/utils/aiResponse.js`，统一解析 AI 回复中的正文与 `---JSON---` 结构化建议。
- 当 AI 只返回纯文本时，页面继续按普通聊天文本展示，不生成 suggestion。
- 当 JSON 非法或不完整时，会自动回退为整段纯文本展示，避免页面崩溃。
- 当前 `CoachTab` 仍只渲染文本消息；结构化 `suggestion` 仅为后续 4.5 卡片渲染预留。

## Task 4.4 测试命令

```bash
node --test tests/aiResponse.test.js tests/coachChat.test.js
```

## Task 4.5 补充说明

- 新增 `src/components/AdoptCard.jsx`，只负责展示建议日期、summary、changes 对比以及触发“采纳/忽略”回调。
- 新增 `src/utils/adoptCard.js`，统一把 AI suggestion 转成卡片展示模型，减少 `CoachTab` 中的字段映射与格式化逻辑。
- `src/tabs/CoachTab.jsx` 现在会消费 `requestCoachReply()` 返回的 `reply.suggestion`：
  - 合法 suggestion 会在聊天面板下方显示采纳卡片；
  - 点击“忽略”后卡片立即消失；
  - 点击“采纳并更新计划”目前只触发占位提示，真正写回训练计划放在 Task 4.6。
- 当前 suggestion 仍不写入 localStorage，只在本次页面状态中临时展示。

## Task 4.5 测试命令

```bash
node --test tests/adoptCard.test.js tests/aiResponse.test.js tests/coachChat.test.js
```
