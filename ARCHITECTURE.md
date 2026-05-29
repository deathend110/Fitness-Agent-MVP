# FitLoop MVP 架构说明

本文档面向课程验收、助教阅读和后续迭代，重点说明当前 MVP 已实现的结构、数据流和能力边界。

## 1. 项目定位

FitLoop MVP 是一个纯前端、本地运行的 AI 健身教练与训练记录应用。当前实现重点不是“大而全”，而是打通下面这条最小闭环：

用户档案 -> 周训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 用户采纳 -> 周计划更新

当前技术边界：

- 前端：Vite + React + Tailwind CSS
- 数据：浏览器 `localStorage`
- AI：DeepSeek Chat Completions
- 无后端、无数据库、无账号系统
- 本地数据**不会自动云同步**

## 2. 当前项目结构

```text
src/
  App.jsx
  main.jsx
  index.css
  api/
    deepseek.js
  components/
    AdoptCard.jsx
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
    adoptCard.js
    adoptPlan.js
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
  *.test.js
docs/
  verification.md
  plan.md
  idea.md
  fitness_coach_mvp_spec.md
```

## 3. 核心模块职责

### 3.1 页面与状态协调

- `src/App.jsx`
  - 负责应用主入口和四个标签页切换
  - 统一加载 `profile / weeklyPlan / dailyLog / chatHistory`
  - 维护顶层 React state
  - 通过 `useEffect` 将状态写回 `localStorage`

### 3.2 四个主业务页面

- `src/tabs/ProfileTab.jsx`
  - 维护用户基础档案
  - 维护训练目标与三大项 1RM

- `src/tabs/PlanTab.jsx`
  - 维护一周训练计划
  - 组织每天训练卡片与动作编辑流程

- `src/tabs/TodayTab.jsx`
  - 维护今日日志录入
  - 展示今日计划只读摘要
  - 展示已保存的当日信息

- `src/tabs/CoachTab.jsx`
  - 维护 AI 教练聊天输入、加载态和错误提示
  - 在发送前读取最新 `profile / weeklyPlan / dailyLog`
  - 展示聊天区、上下文预览和建议采纳卡片
  - 在采纳成功时推动训练计划更新

### 3.3 关键复用组件

- `src/components/CoachConversationPanel.jsx`
  - 负责聊天消息、输入框和发送按钮的显示层

- `src/components/PromptPreviewPanel.jsx`
  - 负责渲染默认折叠的“当前上下文预览”
  - 只展示已生成好的预览文本，不参与 prompt 计算

- `src/components/AdoptCard.jsx`
  - 展示 AI 建议中的日期、摘要和字段变化
  - 触发“采纳”与“忽略”回调，不直接处理写回逻辑

- `src/components/PlanDayCard.jsx`、`src/components/ExerciseEditor.jsx`
  - 负责训练计划的按天展示和动作编辑交互

### 3.4 核心工具模块

- `src/utils/storage.js`
  - 统一封装 `localStorage` 的读写和异常兜底

- `src/utils/prompt.js`
  - 统一构建发送给 AI 的 `system prompt`
  - 汇总用户档案、1RM、周计划、近 14 天体重、近 7 天饮食/训练与当日 TDEE

- `src/utils/promptPreview.js`
  - 将 prompt 文本整理成预览面板使用的数据模型

- `src/utils/coachChat.js`
  - 按 `system -> history -> user` 顺序组装消息
  - 调用 DeepSeek 接口
  - 调用 AI 响应解析逻辑，返回安全文本与 suggestion

- `src/utils/aiResponse.js`
  - 解析 AI 回复中的纯文本与 `---JSON---` 结构化建议
  - 当 JSON 非法或不完整时，安全降级为纯文本

- `src/utils/adoptCard.js`
  - 将 suggestion 数据转换为页面展示模型

- `src/utils/adoptPlan.js`
  - 校验建议中的 `day / exerciseName / field`
  - 只支持对**已有动作的已有字段**执行 `update`
  - 任一变更不合法时整次采纳失败，避免部分写回

- `src/api/deepseek.js`
  - 统一处理 API Key 检查、请求发送和错误归一化
  - 当前默认模型为 `deepseek-v4-flash`

## 4. 数据流说明

### 4.1 应用启动

```text
App 启动
  -> loadStorage()
  -> 读取 fitloop_profile / fitloop_weeklyPlan / fitloop_dailyLog / fitloop_chatHistory
  -> 初始化顶层 state
  -> 将 state 和更新函数传给各 Tab
```

这一层保证四个页面共享同一份本地状态，而不是各自维护互不相通的数据。

### 4.2 用户维护档案与计划

```text
ProfileTab / PlanTab
  -> 用户编辑数据
  -> 调用顶层 setter
  -> App state 更新
  -> useEffect 写回 localStorage
```

这里没有远端存储，也没有服务端校验，因此数据保存结果完全以浏览器本地为准。

### 4.3 用户保存今日日志

```text
TodayTab
  -> 用户填写体重、热量、蛋白质、睡眠、疲劳度、训练完成情况、训练备注
  -> 生成以当天日期为 key 的日志 payload
  -> 更新 dailyLog 顶层 state
  -> App useEffect 写回 fitloop_dailyLog
```

今日日志不会覆盖其他日期的数据，而是按 `YYYY-MM-DD` 组织。

### 4.4 AI 教练发送前的上下文注入

```text
CoachTab
  -> 读取最新 profile / weeklyPlan / dailyLog
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
  -> PromptPreviewPanel 展示本次发送前的上下文预览
```

预览面板和真正发送给 AI 的 `system prompt` 共用同一套来源，因此预览文本就是本次请求将要注入的上下文。

### 4.5 AI 对话与建议采纳

```text
用户点击发送
  -> requestCoachReply()
      -> buildSystemPrompt()
      -> requestDeepSeekChat(messages)
      -> parseAiResponse(content)
  -> 返回 { text, suggestion }
  -> 展示聊天消息
  -> 若 suggestion 合法，则展示 AdoptCard

用户点击“采纳并更新计划”
  -> adoptPlanChange(weeklyPlan, day, changes)
  -> 成功：更新 App 顶层 weeklyPlan state
  -> App useEffect 写回 fitloop_weeklyPlan
  -> 失败：保留卡片并显示错误提示
```

这个流程保证 suggestion 只是“建议”，只有用户主动采纳后，训练计划才会真正改动。

## 5. localStorage 数据结构

当前所有业务数据都只存在浏览器 `localStorage` 中，不会自动上传，也不会自动同步到其他设备。

### 5.1 `fitloop_profile`

保存用户基础信息、目标和三大项 1RM。

参考结构：

```json
{
  "basic": {
    "name": "",
    "sex": "male",
    "age": 23,
    "height": 178,
    "weight": 82.1
  },
  "oneRM": {
    "squat": 120,
    "bench": 90,
    "deadlift": 150
  },
  "goal": "增肌减脂",
  "targetWeight": 78,
  "notes": "每周训练 3 次"
}
```

### 5.2 `fitloop_weeklyPlan`

按 `Monday` 到 `Sunday` 保存每一天的训练类型和动作列表。

参考结构：

```json
{
  "Monday": {
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
  },
  "Tuesday": {
    "type": "rest",
    "exercises": []
  }
}
```

说明：

- 若动作配置了 `ref1RM + pct`，系统会根据 1RM 计算展示重量
- 若未使用 1RM 百分比，则直接使用 `kg`
- 当前计划由用户手动维护，不做自动排周期或自动编程

### 5.3 `fitloop_dailyLog`

按日期保存每日记录。

参考结构：

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
- `trainingDone` 为布尔值
- `trainingNotes` 为字符串

### 5.4 `fitloop_chatHistory`

保存 AI 教练聊天文本，最多保留最近 20 条消息。

参考结构：

```json
[
  { "role": "user", "content": "最近训练后恢复比较慢，怎么调？" },
  { "role": "assistant", "content": "可以先从训练容量和睡眠一起看。" }
]
```

说明：

- 当前只持久化 `role + content`
- suggestion 不写入 `localStorage`
- suggestion 只在当前页面状态中临时存在

## 6. AI 调用链路

```text
CoachTab
  -> requestCoachReply()
      -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
      -> requestDeepSeekChat(messages)
          -> POST https://api.deepseek.com/chat/completions
          -> model: deepseek-v4-flash
      -> parseAiResponse(content)
  -> 若存在 suggestion
      -> buildAdoptCardModel()
      -> AdoptCard
      -> adoptPlanChange()
```

这条链路的设计原则有两个：

1. 每次发送都重新注入最新上下文，避免 AI 基于旧状态给建议。
2. 将“AI 回复解析”和“计划写回”拆开，避免页面组件直接处理过多业务细节。

## 7. 当前 MVP 的诚实边界

下面这些限制是当前版本刻意保留的，而不是遗漏：

- 只有本地存储，没有云端持久化
- 没有用户登录、账号体系和多设备同步
- 没有后端数据库，也没有服务端校验
- suggestion 目前只支持 `action: "update"`
- 只支持更新已存在动作的已存在字段
- 不支持通过 suggestion 新增动作、删除动作或批量改造一整周计划
- 当前更偏向演示闭环，不追求复杂训练编程能力

## 8. 后续扩展方向

在核心闭环稳定之后，可以继续扩展：

- 体重趋势图、训练热力图
- 数据导入导出
- AI 流式输出
- 更细粒度的错误提示
- 更丰富的建议结构，例如新增动作或替换动作
- 本地备份或云同步机制
