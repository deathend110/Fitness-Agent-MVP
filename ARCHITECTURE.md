# FitLoop MVP 架构说明

本文档说明当前 MVP 的项目结构、核心模块职责、数据流、`localStorage` 数据结构以及 AI 调用链路，并同步记录 Task 4 与 Task 5 已完成的训练计划和界面主题升级。

## 当前项目结构

```text
src/
  api/
    deepseek.js
  components/
    AdoptCard.jsx
    CoachConversationPanel.jsx
    DataTransferPanel.jsx
    ExerciseEditor.jsx
    PlanDayCard.jsx
    PlanDayCardButton.jsx
    PlanDayCardHeader.jsx
    PlanDayTypeSection.jsx
    PlanExerciseEditorCard.jsx
    PlanExerciseItem.jsx
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
    planExerciseCard.js
    planLayout.js
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
  idea.md
  plan.md
  fitness_coach_mvp_spec.md
  verification.md
```

## 核心模块职责

- `src/App.jsx`
  - 负责加载和持久化顶层状态
  - 统一管理 `profile / weeklyPlan / dailyLog / chatHistory`
  - 负责应用级标题区、导航切换和页面外壳视觉节奏

- `src/tabs/PlanTab.jsx`
  - 负责周计划页面组织
  - 通过 `buildWeeklyPlanColumns()` 构建 7 列课表布局
  - 协调单日展开、动作新增、编辑、删除

- `src/components/PlanDayCard.jsx`
  - 作为单日计划卡片的协调壳
  - 只负责组合头部、训练类型区、动作编辑区和动作列表

- `src/components/PlanDayCardHeader.jsx`
  - 展示日期、训练类型、动作数量和展开状态

- `src/components/PlanDayTypeSection.jsx`
  - 负责训练类型输入
  - 使用“文本输入 + datalist 联想 + 快捷按钮”组合

- `src/components/PlanExerciseEditorCard.jsx`
  - 封装新增动作 / 编辑动作的表单容器

- `src/components/PlanExerciseItem.jsx`
  - 负责单个动作卡片的展示和局部编辑切换

- `src/components/ExerciseEditor.jsx`
  - 负责动作编辑表单本体
  - 支持层级、组型、次数表达、负重模式、RPE、备注

- `src/utils/weeklyPlan.js`
  - 负责周计划结构归一化
  - 负责训练类型更新、动作增删改、RPE 边界兜底

- `src/utils/exerciseForm.js`
  - 负责表单草稿与计划动作结构之间的转换

- `src/utils/planExerciseCard.js`
  - 负责把动作结构转换成卡片展示模型

- `tailwind.config.js` + `src/index.css`
  - 负责定义 `repmind.*` 语义色 token
  - 负责明亮主题基底、边框、阴影和强调色策略
  - 在过渡阶段兼容旧的 `fitloop-*` 类名

## 数据流说明

### 1. 启动与持久化

```text
App 启动
  -> 读取 fitloop_profile / fitloop_weeklyPlan / fitloop_dailyLog / fitloop_chatHistory
  -> 初始化顶层 state
  -> useEffect 写回 localStorage
```

### 2. 周计划编辑流

```text
PlanTab
  -> buildWeeklyPlanColumns(weeklyPlan)
  -> 渲染 7 列 PlanDayCard
  -> 用户修改训练类型 / 新增动作 / 编辑动作 / 删除动作
  -> weeklyPlan.updateDayType() / addExerciseToDay() / updateExerciseInDay() / removeExerciseFromDay()
  -> normalizeWeeklyPlan()
  -> App 顶层状态更新
  -> 写回 fitloop_weeklyPlan
```

### 3. 今日日志流

```text
TodayTab
  -> 用户填写日志
  -> 更新 dailyLog
  -> 写回 fitloop_dailyLog
  -> buildWeightChartModel()
  -> WeightChart 展示近 14 天体重趋势
```

### 4. AI 调用与采纳流

```text
CoachTab
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
  -> requestCoachReply()
      -> 优先流式请求
      -> 失败时回退普通请求
      -> parseAiResponse()
  -> 渲染文本回复与 AdoptCard
  -> 用户点击采纳
  -> adoptPlanChange()
  -> App 更新 weeklyPlan
  -> 写回 fitloop_weeklyPlan
```

## localStorage 数据结构

### `fitloop_profile`

保存用户基础资料、目标与三大项 1RM。

### `fitloop_weeklyPlan`

按 `Monday` 到 `Sunday` 保存一周计划。每天包含：

- `type`：训练类型
- `exercises`：动作数组

动作对象已升级为“模板 + 实例 + 扁平兼容字段”并存的结构：

```json
{
  "id": "stable-id",
  "name": "深蹲",
  "tier": "main",
  "template": {
    "loadMode": "percentage",
    "ref1RM": "squat",
    "setType": "straight",
    "sets": 4,
    "repsText": "6"
  },
  "instance": {
    "pct": 0.75,
    "kg": null,
    "rpe": 8,
    "note": "主项"
  },
  "ref1RM": "squat",
  "pct": 0.75,
  "kg": null,
  "sets": 4,
  "reps": 6,
  "rpe": 8,
  "note": "主项"
}
```

这个结构的目的：

- `template` 保存相对稳定的编排信息
- `instance` 保存更贴近执行层的负重、RPE、备注
- 扁平字段继续兼容当前 AI 采纳链路

### `fitloop_dailyLog`

按 `YYYY-MM-DD` 保存每日记录：

- `weight`
- `kcal`
- `protein`
- `sleep`
- `fatigue`
- `trainingDone`
- `trainingNotes`

### `fitloop_chatHistory`

只持久化：

- `role`
- `content`

结构化建议卡片不落盘，仅存在于当前页面状态中。

### `fitloop_storageVersion`

用于标记默认数据迁移版本，避免旧演示数据反复覆盖真实数据。

## AI 调用链路

```text
CoachTab
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
  -> streamDeepSeekChat(messages)
  -> fallback: requestDeepSeekChat(messages)
  -> parseAiResponse(content)
  -> buildAdoptCardModel()
  -> adoptPlanChange()
```

关键设计点：

- 每次发送前都重新读取最新上下文
- AI 回复解析与训练计划写回分离，保留用户最终确认权

## Task 4 已完成升级说明

### 1. 7 列课表布局

- `src/utils/planLayout.js` 负责将周计划转换成 7 列展示模型
- 训练日列宽更大，休息日列宽更小

### 2. 主项 / 辅项卡片

- `src/utils/planExerciseCard.js` 负责构建动作卡片模型
- 主项使用更高对比度样式
- 辅项使用更轻的视觉层级

### 3. 编辑器支持层级 / 组型 / 次数表达

- 层级：`main` / `accessory`
- 组型：`straight` / `custom`
- 次数表达：数值或文本表达并存
- 负重模式：按 1RM 百分比 / 直接 kg
- RPE 在表单层和存储层双重校验

## 后续扩展方向

- 将训练模板与训练实例进一步拆开
- 支持更复杂的动作块和组型
- 增加趋势图、热力图和训练负荷统计
- 增强 AI 建议类型和对话体验

## Task 5 已完成升级说明

### 1. 全局主题 token

- `tailwind.config.js` 新增 `repmind.bg / panel / border / text / accent / success / warning / danger`
- `src/index.css` 建立冷白底板、浅蓝紫径向高光和统一选区颜色

### 2. 通用壳层与控件

- `src/App.jsx` 把应用头部和导航统一为白色面板 + 蓝紫选中态
- `PlanDayCardButton / CoachConversationPanel / DataTransferPanel / AdoptCard / PromptPreviewPanel / WeightChart`
  统一到同一套边框、阴影和强调色逻辑

### 3. 页面级视觉细修

- `ProfileTab / PlanTab / TodayTab / CoachTab` 统一标题层级、说明文密度、表单区留白和信息卡对比度
- `ExerciseEditor / PlanDayCard / PlanExerciseItem / PlanDayTypeSection`
  跟随页面语法调整为更轻的卡片和输入样式

### 4. 当前主题策略

- 主视觉：白色或冷白色底板
- 强调色：清亮蓝紫，仅用于主按钮、选中态、重要标签和焦点反馈
- 次级信息：灰蓝与冷灰，避免页面发灰或过暗
- 阴影：轻量、低对比，用于区分桌面级信息层级而不是制造漂浮感
