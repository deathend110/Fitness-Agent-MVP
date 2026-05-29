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
