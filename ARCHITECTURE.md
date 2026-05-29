# FitLoop MVP 架构说明

## 当前项目结构

```text
src/
  App.jsx
  api/
    deepseek.js
  components/
    CoachConversationPanel.jsx
    ExerciseEditor.jsx
    PlanDayCard.jsx
    PromptPreviewPanel.jsx
  tabs/
    CoachTab.jsx
    PlanTab.jsx
    ProfileTab.jsx
    TodayTab.jsx
  utils/
    aiResponse.js
    calc.js
    chatHistory.js
    coachChat.js
    dailyLog.js
    defaultData.js
    exerciseForm.js
    profileForm.js
    prompt.js
    promptPreview.js
    storage.js
    todayPlan.js
    weeklyPlan.js
tests/
  aiResponse.test.js
  chatHistory.test.js
  coachChat.test.js
  dailyLog.test.js
  deepseek.test.js
  prompt.test.js
  promptPreview.test.js
  todayPlan.test.js
  weeklyPlan.test.js
```

## 核心模块职责

- `src/App.jsx`
  - 统一加载 `profile / weeklyPlan / dailyLog / chatHistory`
  - 维护顶层 React state
  - 通过 `useEffect` 写回 localStorage
- `src/tabs/ProfileTab.jsx`
  - 维护用户基础档案、目标和三大项 1RM
- `src/tabs/PlanTab.jsx`
  - 维护一周训练计划
  - 协调训练日展开、动作编辑、新增与删除
- `src/tabs/TodayTab.jsx`
  - 维护今日日志表单
  - 展示已保存摘要与今日计划只读视图
- `src/tabs/CoachTab.jsx`
  - 维护 AI 教练输入草稿、发送状态和页内错误
  - 读取最新 `profile / weeklyPlan / dailyLog`
  - 组合最近日志摘要、聊天区和上下文预览面板
- `src/components/CoachConversationPanel.jsx`
  - 负责渲染聊天气泡区、输入区、发送按钮和加载态
- `src/components/PromptPreviewPanel.jsx`
  - 负责渲染默认折叠的“当前上下文预览”
  - 只展示已经生成好的预览数据，不直接参与 prompt 计算
- `src/utils/prompt.js`
  - 统一构建发送给 AI 的 system prompt 文本
  - 汇总档案、1RM、周计划、近 14 天体重、近 7 天饮食/训练和今日 TDEE
- `src/utils/promptPreview.js`
  - 整理上下文预览标题、默认折叠状态和 prompt 文本
  - 让 `CoachTab` 保持页面协调职责，避免同时处理展示文案和 prompt 细节
- `src/utils/aiResponse.js`
  - 统一检测 `---JSON---` 分隔符
  - 负责拆分 AI 正文与结构化 suggestion
  - JSON 非法时回退为纯文本，保证页面消费安全
- `src/utils/coachChat.js`
  - 每次请求前调用 `buildSystemPrompt()`
  - 按 `system -> history -> user` 顺序组装 DeepSeek messages
  - 使用 `parseAiResponse()` 返回安全文本和 suggestion
- `src/utils/chatHistory.js`
  - 统一追加聊天消息
  - 只保留最近 20 条会话记录
- `src/utils/dailyLog.js`
  - 处理今日日志表单草稿读取与保存 payload 生成
- `src/utils/todayPlan.js`
  - 生成 TodayTab 只读计划摘要
- `src/utils/storage.js`
  - 封装 localStorage 读写和兜底逻辑
- `src/api/deepseek.js`
  - 负责 DeepSeek API Key 校验、请求发送与错误归一化

## 数据流说明

```text
App 启动
  -> loadStorage()
  -> 读取 fitloop_profile / fitloop_weeklyPlan / fitloop_dailyLog / fitloop_chatHistory
  -> 将 state 和 setter 注入各个 Tab

TodayTab 保存今日日志
  -> readTodayLogForm() 读取当日草稿
  -> 用户编辑体重、热量、蛋白质、睡眠、疲劳度、训练完成状态和训练备注
  -> buildTodayLogPayload() 使用 todayStr 生成新的 dailyLog
  -> onDailyLogChange(setDailyLog) 更新 App 顶层 state
  -> useEffect(saveStorage) 写回 fitloop_dailyLog

CoachTab 上下文预览
  -> 读取最新 profile / weeklyPlan / dailyLog
  -> buildPromptPreviewModel(profile, weeklyPlan, dailyLog)
      -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
  -> PromptPreviewPanel 默认折叠展示本次发送前的完整 system prompt
  -> 切回今日日志并修改数据后，再返回 CoachTab 时重新生成预览文本

CoachTab 用户点击“发送”
  -> 校验输入是否为空 / 是否正在发送
  -> appendChatMessages(chatHistory, [userMessage])
  -> onChatHistoryChange() 写回 App 顶层 state
  -> requestCoachReply()
      -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
      -> requestDeepSeekChat(messages)
      -> parseAiResponse(content)
  -> appendChatMessages(nextHistory, [assistantTextMessage])
  -> useEffect(saveStorage) 写回 fitloop_chatHistory
```

## localStorage 数据结构

### `fitloop_profile`

保存用户基础信息、训练目标和三大项 1RM。

### `fitloop_weeklyPlan`

按 `Monday` 到 `Sunday` 存储，每天结构如下：

```json
{
  "type": "腿日",
  "exercises": [
    {
      "id": "stable-id",
      "name": "深蹲",
      "ref1RM": "squat",
      "pct": 0.75,
      "kg": null,
      "sets": 4,
      "reps": 6,
      "rpe": null,
      "note": "主项"
    }
  ]
}
```

### `fitloop_dailyLog`

按 `YYYY-MM-DD` 存储今日日志：

```json
{
  "2026-05-30": {
    "weight": 81.2,
    "kcal": 2300,
    "protein": 170,
    "sleep": 6.5,
    "fatigue": 4,
    "trainingDone": true,
    "trainingNotes": "今天完成腿部训练"
  }
}
```

说明：

- `weight / kcal / protein / sleep / fatigue` 可为数字或 `null`
- `trainingDone` 始终为布尔值
- `trainingNotes` 始终为字符串

### `fitloop_chatHistory`

保存 AI 教练会话记录，最多保留最近 20 条。

说明：

- 当前仍只持久化 `role + content` 文本消息
- `suggestion` 仅在本次回复解析阶段保留，供后续 4.5 渲染采纳卡片时接入

## AI 调用链路

```text
CoachTab
  -> 用户输入问题
  -> requestCoachReply()
      -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
      -> requestDeepSeekChat(messages)
          -> POST https://api.deepseek.com/chat/completions
          -> 返回 data.choices[0].message.content
      -> parseAiResponse(content)
  -> appendChatMessages()
  -> saveStorage(fitloop_chatHistory)
```

其中，Task 4.3 的上下文预览与正式发送共用同一套 `buildSystemPrompt()` 数据来源，因此页面上的预览文本就是本次发送前的真实 prompt。

## 后续扩展方向

- AI 返回结构化 JSON 建议并渲染采纳卡片
- 一键采纳训练建议并写回 `fitloop_weeklyPlan`
- 体重趋势图、训练热力图、数据导入导出
- 流式输出与更细粒度的错误处理
