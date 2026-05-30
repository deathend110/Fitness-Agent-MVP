# FitLoop MVP 架构说明

本文档面向课程验收、后续维护和迭代开发，重点说明当前 MVP 已实现的结构、数据流、边界和关键设计决策。

## 1. 项目定位

FitLoop MVP 是一个纯前端、本地运行的 AI 健身教练与训练记录应用。当前实现不是追求“大而全”，而是优先打通下面这条最小闭环：

用户档案 -> 周训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 用户采纳 -> 周计划更新

当前技术边界：

- 前端：Vite + React + Tailwind CSS
- 数据：浏览器 `localStorage`
- AI：DeepSeek Chat Completions
- 当前没有后端、数据库、账号系统与多端同步

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
    DataTransferPanel.jsx
    ExerciseEditor.jsx
    PlanDayCard.jsx
    PromptPreviewPanel.jsx
    WeightChart.jsx
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
    coachGuard.js
    dailyLog.js
    dataTransfer.js
    defaultData.js
    exerciseForm.js
    profileForm.js
    prompt.js
    promptPreview.js
    storage.js
    todayPlan.js
    weeklyPlan.js
    weightChart.js
tests/
  *.test.js
docs/
  verification.md
  plan.md
  idea.md
  fitness_coach_mvp_spec.md
task/
  V0/
  V1/
```

## 3. 核心模块职责

### 3.1 页面与顶层状态

- `src/App.jsx`
  - 负责应用入口和四个标签页切换
  - 统一加载 `profile / weeklyPlan / dailyLog / chatHistory`
  - 维护顶层 React state
  - 通过 `useEffect` 将状态写回 `localStorage`

### 3.2 四个主功能页

- `src/tabs/ProfileTab.jsx`
  - 维护用户基础档案、训练目标与三大项 1RM
  - 提供本地备份导入导出入口

- `src/tabs/PlanTab.jsx`
  - 维护一周训练计划
  - 组织每天训练卡片和动作编辑交互
  - 渲染训练动作的摘要展示

- `src/tabs/TodayTab.jsx`
  - 维护今日日志录入
  - 展示今日训练摘要
  - 展示最近体重趋势图

- `src/tabs/CoachTab.jsx`
  - 维护 AI 教练聊天输入、消息列表、加载与错误状态
  - 在发送前校验最小档案条件
  - 在发送前读取最新 `profile / weeklyPlan / dailyLog`
  - 渲染上下文预览与建议采纳卡片
  - 在采纳成功后推动训练计划更新

### 3.3 关键复用组件

- `src/components/CoachConversationPanel.jsx`
  - 承担聊天消息区、输入框和发送按钮的展示层

- `src/components/PromptPreviewPanel.jsx`
  - 渲染发送前的上下文预览
  - 只负责展示，不参与 prompt 计算

- `src/components/AdoptCard.jsx`
  - 渲染 AI 建议中的日期、摘要和字段变化
  - 触发“采纳”与“忽略”回调

- `src/components/DataTransferPanel.jsx`
  - 负责本地 JSON 备份导出与导入提示

- `src/components/WeightChart.jsx`
  - 负责今日页体重趋势图渲染
  - 无有效记录时展示空状态

- `src/components/PlanDayCard.jsx`
  - 负责按天展示训练计划卡片

- `src/components/ExerciseEditor.jsx`
  - 负责单个动作的增删改编辑表单

### 3.4 核心工具模块

- `src/utils/storage.js`
  - 统一封装 `localStorage` 读写与异常兜底

- `src/utils/calc.js`
  - 统一处理 1RM 推算重量、BMR、训练消耗与 TDEE 计算
  - 提供重量、百分比、组数、次数、RPE 的统一格式化函数
  - 作为 `TodayTab`、`PlanTab`、`AdoptCard`、`WeightChart` 的共享数值显示入口

- `src/utils/todayPlan.js`
  - 把当天计划转换成今日页摘要模型
  - 复用 `calc.js` 的展示格式化规则

- `src/utils/adoptCard.js`
  - 把 suggestion 数据转换为采纳卡片展示模型
  - 统一处理字段标签、变更前后文本和数值展示

- `src/utils/adoptPlan.js`
  - 校验建议中的 `day / exerciseName / field`
  - 只支持对已有动作的已有字段执行 `update`
  - 任一变更非法时整次采纳失败，避免部分写回

- `src/utils/prompt.js`
  - 统一构建发送给 AI 的 `system prompt`
  - 汇总用户档案、1RM、周计划、近 14 天体重、近 7 天饮食训练与当日 TDEE

- `src/utils/promptPreview.js`
  - 把 prompt 文本整理成预览面板使用的数据模型

- `src/utils/coachGuard.js`
  - 定义 AI 教练发送前的最小档案校验规则

- `src/utils/coachChat.js`
  - 按 `system -> history -> user` 顺序组装消息
  - 优先走流式回复，失败时回退普通回复
  - 返回纯文本回复与 suggestion 解析结果

- `src/utils/aiResponse.js`
  - 解析 AI 回复中的纯文本与 `---JSON---` 结构化建议
  - JSON 非法或不完整时安全降级为纯文本

- `src/utils/dailyLog.js`
  - 处理今日日志保存、读取与默认结构

- `src/utils/weeklyPlan.js`
  - 处理周计划初始化、更新与基础校验

- `src/utils/weightChart.js`
  - 整理近 14 天体重图表数据
  - 过滤空体重与超出范围的记录

- `src/utils/dataTransfer.js`
  - 生成本地备份 JSON 结构与文件名
  - 执行导入前的最小字段校验

- `src/api/deepseek.js`
  - 统一处理 API Key 检查、请求发送与错误归一化
  - 同时封装普通聊天请求与基于 SSE 的流式请求

## 4. 数据流说明

### 4.1 应用启动

```text
App 启动
  -> loadStorage()
  -> 读取 fitloop_profile / fitloop_weeklyPlan / fitloop_dailyLog / fitloop_chatHistory
  -> 初始化顶层 state
  -> 将 state 与更新函数传给各 Tab
```

四个页面共享同一份顶层本地状态，避免各页面各自维护互不连通的数据。

### 4.2 用户维护档案与计划

```text
ProfileTab / PlanTab
  -> 用户编辑数据
  -> 调用顶层 setter
  -> App state 更新
  -> useEffect 写回 localStorage
```

当前没有远端存储和服务端校验，因此以浏览器本地保存结果为准。

### 4.3 用户保存今日日志

```text
TodayTab
  -> 用户填写体重、热量、蛋白质、睡眠、疲劳度、训练完成情况、训练备注
  -> 生成以当天日期为 key 的日志 payload
  -> 更新 dailyLog 顶层 state
  -> App useEffect 写回 fitloop_dailyLog
  -> buildWeightChartModel(dailyLog, todayDate)
  -> WeightChart 展示近 14 天体重趋势或空状态
```

今日日志不会覆盖其他日期的数据，而是按 `YYYY-MM-DD` 组织。今日摘要与图表中的数值展示统一复用 `src/utils/calc.js` 的格式化函数，因此会与训练计划页、AI 建议采纳卡片保持一致。

### 4.4 AI 教练发送前的上下文注入

```text
CoachTab
  -> 读取最新 profile / weeklyPlan / dailyLog
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
  -> PromptPreviewPanel 展示本次发送前的上下文预览
```

预览面板和真正发给 AI 的 `system prompt` 共用同一套来源，因此预览文本就是本次请求将要注入的上下文。

### 4.5 AI 对话与建议采纳

```text
用户点击发送
  -> requestCoachReply()
      -> buildSystemPrompt()
      -> 优先 streamDeepSeekChat(messages)
      -> 失败时回退 requestDeepSeekChat(messages)
      -> parseAiResponse(content)
  -> 返回 { text, suggestion }
  -> 渲染聊天消息
  -> 若 suggestion 合法，则渲染 AdoptCard

用户点击“采纳并更新计划”
  -> adoptPlanChange(weeklyPlan, day, changes)
  -> 成功：更新 App 顶层 weeklyPlan state
  -> App useEffect 写回 fitloop_weeklyPlan
  -> 失败：保留卡片并显示错误提示
```

这样可以保证 suggestion 只是“建议”，只有用户主动采纳后训练计划才会真正改动。

## 5. localStorage 数据结构

### 5.1 `fitloop_profile`

保存用户基础信息、目标与三大项 1RM。

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

按 `Monday` 到 `Sunday` 保存每天训练类型与动作列表。

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
- 当前计划由用户手动维护，不做自动排周期

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
      -> 优先 streamDeepSeekChat(messages)
          -> POST https://api.deepseek.com/chat/completions
          -> stream: true
      -> 失败时回退 requestDeepSeekChat(messages)
          -> POST https://api.deepseek.com/chat/completions
          -> model: deepseek-v4-flash
      -> parseAiResponse(content)
  -> 若存在 suggestion
      -> buildAdoptCardModel()
      -> AdoptCard
      -> adoptPlanChange()
```

这条链路有两个核心设计点：

1. 每次发送都重新注入最新上下文，避免 AI 基于旧状态给建议。
2. 把“AI 回复解析”和“计划写回”拆开，避免页面组件承担过多业务逻辑。

## 7. 测试与验证结构

- `tests/displayFormat.test.js`
  - 覆盖 Task 1 引入的统一数值显示规则

- `tests/todayPlan.test.js`
  - 验证今日训练摘要模型与展示文本

- `tests/adoptCard.test.js`
  - 验证 AI 建议采纳卡片模型

- `tests/weeklyPlan.test.js`
  - 验证周计划更新逻辑

- `tests/weightChart.test.js`
  - 验证体重趋势图数据整理

- `tests/coachChat.test.js`、`tests/coachGuard.test.js`
  - 验证 AI 请求构建与发送前校验

## 8. 当前 MVP 的诚实边界

下面这些限制是当前版本刻意保留的，而不是遗漏：

- 只有本地存储，没有云端持久化
- 没有用户登录、账号体系和多设备同步
- 没有后端数据库与服务端校验
- suggestion 目前只支持 `action: "update"`
- 只支持更新已存在动作的已存在字段
- 不支持通过 suggestion 新增动作、删除动作或批量改造整周计划
- 档案缺少关键字段时，AI 教练会直接阻止发送

## 9. 后续扩展方向

- 训练表格布局升级为更直观的课表式结构
- 训练模板与训练实例分离
- 更丰富的动作字段与组型表达
- 复杂指标与大模型辅助推算
- 更完整的 AI 对话体验
- 数据导入导出增强与云同步能力
