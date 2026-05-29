# FitLoop MVP 架构说明

## 当前项目结构

```text
src/
  App.jsx
  components/
    ExerciseEditor.jsx
    PlanDayCard.jsx
  tabs/
    CoachTab.jsx
    PlanTab.jsx
    ProfileTab.jsx
    TodayTab.jsx
  utils/
    calc.js
    dailyLog.js
    defaultData.js
    exerciseForm.js
    prompt.js
    profileForm.js
    storage.js
    todayPlan.js
    weeklyPlan.js
tests/
  dailyLog.test.js
  prompt.test.js
  todayPlan.test.js
  weeklyPlan.test.js
```

## 核心模块职责

- `src/App.jsx`
  - 统一加载 `profile / weeklyPlan / dailyLog / chatHistory`
  - 维护顶层 React state
  - 通过 `useEffect` 将状态写回 localStorage
- `src/tabs/ProfileTab.jsx`
  - 维护用户基础档案、目标和三大项 1RM
- `src/tabs/PlanTab.jsx`
  - 维护一周训练计划
  - 协调训练日展开、动作编辑、新增与删除
- `src/tabs/TodayTab.jsx`
  - 维护今日日志表单
  - 读取 `weeklyPlan[todayKey]`，只读展示当日训练类型与动作摘要
  - 展示已保存摘要与今日计划，避免表单录入与只读信息割裂
- `src/tabs/CoachTab.jsx`
  - 读取最新 `profile / weeklyPlan / dailyLog`
  - 调用 `buildSystemPrompt()` 生成临时上下文预览
  - 当前只做本地预览，不发起真实 DeepSeek 请求
- `src/utils/dailyLog.js`
  - 将已保存的今日日志转成受控表单草稿
  - 将表单输入规范化为可安全保存的数据结构
  - 使用当天日期键生成新的 `dailyLog` 对象
- `src/utils/prompt.js`
  - 统一拼装系统提示词文本
  - 汇总用户档案、三大项 1RM、本周计划、近 14 天体重、近 7 天饮食/训练和今日 TDEE
  - 对空数据输出“暂无记录 / 未记录”兜底文案
- `src/utils/todayPlan.js`
  - 统一整理 TodayTab 的只读计划摘要结构
  - 区分训练日、休息日和“有训练类型但暂无动作”的空计划场景
- `src/utils/weeklyPlan.js`
  - 封装周计划的新增、修改、删除逻辑
- `src/utils/storage.js`
  - 统一封装 localStorage 的读写与异常兜底

## 数据流说明

```text
App 启动
  -> loadStorage()
  -> 读取 fitloop_profile / fitloop_weeklyPlan / fitloop_dailyLog / fitloop_chatHistory
  -> 将 state 和 setter 传给各 Tab

TodayTab 录入今日日志
  -> readTodayLogForm() 将当天记录转成受控表单草稿
  -> 用户编辑体重、热量、蛋白质、睡眠、疲劳度、训练完成状态和备注
  -> buildTodayLogPayload() 使用 getTodayStr() 作为日期键生成新 dailyLog
  -> onDailyLogChange(setDailyLog) 更新 App 顶层状态

TodayTab 展示今日计划摘要
  -> getTodayKey() 计算今天对应的 weekday key
  -> 读取 weeklyPlan[todayKey]
  -> buildTodayPlanSummary() 生成训练类型、休息提示或动作摘要列表
  -> 页面以只读方式渲染，不在此处承担训练计划编辑职责

CoachTab 临时上下文预览
  -> 读取 profile / weeklyPlan / dailyLog
  -> buildSystemPrompt() 格式化完整 system prompt
  -> 将 prompt 文本直接渲染到预览面板，供 Task 3.3 验收

App 状态变化
  -> useEffect(saveStorage)
  -> 写回 fitloop_dailyLog
  -> 刷新页面后再次 loadStorage() 恢复当天数据
```

## localStorage 数据结构

### `fitloop_profile`

保存用户基础信息、目标信息和三大项 1RM。

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

按 `YYYY-MM-DD` 存储今日日志，当前字段如下：

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
- 可选字段留空时会规范化为空安全值，避免页面摘要和后续上下文读取崩溃

### `fitloop_chatHistory`

保存 AI 教练会话记录，供后续上下文注入与建议采纳闭环使用。

## AI 调用链路

当前项目已经补齐 system prompt 构建与本地预览，正式调用链路仍按以下方向扩展：

```text
CoachTab
  -> 读取最新 profile / weeklyPlan / dailyLog
  -> buildSystemPrompt() 组装上下文 prompt
  -> 当前阶段先本地展示预览，不发送请求
  -> 调用 DeepSeek Chat Completions
  -> 解析建议
  -> 在后续 Sprint 中支持结构化建议采纳
```

## 后续扩展方向

- 今日日志的输入校验与历史浏览
- 基于今日日志和计划的 AI 上下文注入
- AI 返回结构化 JSON 建议并一键写回训练计划
- 体重趋势图、训练热力图、数据导入导出

## Task 4.1 补充结构

### 新增模块

- `src/api/deepseek.js`
  - 负责读取 `import.meta.env.VITE_DEEPSEEK_API_KEY`
  - 统一向 `POST https://api.deepseek.com/chat/completions` 发起请求
  - 默认模型使用 `deepseek-v4-flash`
  - 将缺少 API Key、网络失败、HTTP 非 2xx 响应统一转换为可直接展示的错误消息

### CoachTab 当前状态

- `src/tabs/CoachTab.jsx`
  - 继续展示本地对话预览、最近日志摘要和 system prompt 预览
  - 额外展示 DeepSeek 配置/调用状态，避免 `.env` 未配置时用户不知道问题出在哪里
  - 当前不直接发起正式聊天请求，后续 Task 4.2 再接入发送流程

### Task 4.1 调用链

```text
CoachTab
  -> getDeepSeekApiKeyStatus()
  -> 显示“已配置 / 未配置”状态提示

后续对话发送（预留）
  -> requestDeepSeekChat(messages, options)
  -> POST https://api.deepseek.com/chat/completions
  -> 返回 data.choices[0].message.content
  -> 若失败则抛出可展示错误，由 UI 接住并提示
```
