# FitLoop MVP 架构说明

本文档说明当前 MVP 的项目结构、核心模块职责、数据流、`localStorage` 数据结构以及 AI 调用链路，并同步记录 Task 4、Task 5 与 Task 6 已完成的训练计划、界面主题和复杂指标升级。

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
    plan-header/
      PlanHeaderLegend.jsx
      PlanHeaderToolbar.jsx
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
    calcBase.js
    chatHistory.js
    coachChat.js
    coachGuard.js
    dailyLog.js
    dailyMetrics.js
    dataTransfer.js
    defaultData.js
    exerciseForm.js
    planExerciseCard.js
    planHeader.js
    planLayout.js
    profileForm.js
    prompt.js
    promptSections.js
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
  - 通过 `buildPlanHeaderModel()` 与 `PlanHeaderToolbar` 组装头部工具栏
  - 通过 `buildWeeklyPlanColumns()` 构建 7 列课表布局
  - 协调单日展开、动作新增、编辑、删除

- `src/components/plan-header/PlanHeaderToolbar.jsx`
  - 负责训练计划页头部工具栏的布局编排
  - 展示标题、周区间、周编号、主项/辅项图例与“计划设置”占位按钮

- `src/components/plan-header/PlanHeaderLegend.jsx`
  - 负责主项 / 辅项图例渲染

- `src/utils/planHeader.js`
  - 负责训练计划页头部展示模型
  - 统一生成周区间、ISO 周编号、图例配置与占位按钮配置

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

- `src/utils/calc.js`
  - 作为兼容导出层保留原有调用入口
  - 将日期/数值工具与复杂指标汇总拆分到独立文件，降低 Task 6 后续维护成本

- `src/utils/calcBase.js`
  - 负责日期键、动作负重换算、数值格式化、BMR 与训练消耗等基础计算

- `src/utils/dailyMetrics.js`
  - 负责 `buildDailyMetricsSummary()` 与 `calcTDEE()` 的复杂指标汇总
  - 统一生成 Today 页展示、prompt 注入与测试验收共用的核心指标口径

- `src/utils/prompt.js`
  - 作为 system prompt 的薄入口，只负责组织各个上下文段落

- `src/utils/promptSections.js`
  - 负责档案、周计划、体重历史、饮食摘要、训练完成情况与复杂指标段的分段构建
  - `buildMetricsSection()` 会把 `structured_metrics` JSON 注入 prompt，供 AI 继续解释复杂指标

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
  -> buildDailyMetricsPanelModel()
      -> buildDailyMetricsSummary()
      -> 生成 TDEE / 热量状态 / 蛋白质状态 / 恢复数据展示模型
  -> buildWeightChartModel()
  -> WeightChart 展示近 14 天体重趋势
```

### 4. AI 调用与采纳流

```text
CoachTab
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
      -> buildMetricsSection(profile, weeklyPlan, dailyLog)
      -> buildDailyMetricsSummary()
      -> 注入 structured_metrics
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

Task 6 的复杂指标不单独持久化，而是运行时根据 `profile + weeklyPlan + dailyLog` 即时汇总，避免出现第二份派生状态。

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
- Today 页复杂指标面板与 prompt 注入共用 `buildDailyMetricsSummary()`，避免展示层和 AI 上下文口径漂移

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
## Task 6 已完成升级说明
### 1. 复杂指标计算口径

- `buildDailyMetricsSummary()` 当前统一汇总：
  - `BMR`
  - `trainingKcal`
  - `TDEE`
  - `BMI`
  - `calorie.intake / delta / status`
  - `protein.intake / gramsPerKg / status`
  - `recovery.sleepHours / fatigueLevel`
- 热量状态规则：
  - `delta > 100` 记为 `surplus`
  - `delta < -100` 记为 `deficit`
  - 其余记为 `balanced`
- 蛋白质状态规则：
  - `protein_g_per_kg >= 1.6` 记为 `met`
  - 否则记为 `low`

### 2. Today 页展示链路

- `TodayTab.jsx` 调用 `buildDailyMetricsPanelModel()`
- `buildDailyMetricsPanelModel()` 只消费 `buildDailyMetricsSummary()` 的结果，不在页面层重复推导复杂数值
- 状态文案与色彩映射由 `dailyMetricsPanel.js` 负责，避免组件层散落业务规则

### 3. Prompt 注入链路

```text
CoachTab / PromptPreviewPanel
  -> buildSystemPrompt()
  -> buildMetricsSection()
  -> buildDailyMetricsSummary()
  -> structured_metrics JSON
  -> DeepSeek
```

- Prompt 预览与 AI 实际发送都复用 `buildSystemPrompt()`，保证所见即所发
- 6.4 新增可选参考日期入口，用于固定样本稳定性测试，不影响运行时默认行为

## V1.5 Task 1 壳层补充

### 新增结构

```text
src/
  components/
    app-shell/
      AppShell.jsx
      ShellIcon.jsx
      ShellSidebar.jsx
      ShellStatusBar.jsx
      appShellConfig.js
```

### 壳层职责

- `src/App.jsx`
  - 继续负责顶层状态加载、持久化和四个 tab 的切换协调。
  - 通过 `renderActiveTab()` 把现有业务 tab 装配到统一壳层中，不改动 tab 内部业务逻辑。

- `src/components/app-shell/AppShell.jsx`
  - 负责整体“侧栏 + 主内容区 + 底部状态区”的编排。
  - 使用 `min-w-0` 与独立内容滚动区约束宽度和 overflow，避免默认制造整页横向滚动。

- `src/components/app-shell/ShellSidebar.jsx`
  - 负责品牌区、四个导航入口和当前工作区提示。
  - 只消费壳层元信息，不直接依赖业务 tab 内部数据结构。

- `src/components/app-shell/ShellStatusBar.jsx`
  - 负责底部保存状态提示与 MVP 占位快捷按钮。

- `src/components/app-shell/appShellConfig.js`
  - 负责四个导航项、快捷按钮和状态文案配置。
  - 提供可被 `node --test` 直接验证的最小壳层契约。

### 验证补充

- 新增 `tests/appShellConfig.test.js`，覆盖四个核心导航顺序、未知 tab 回退、状态区文案和快捷按钮占位。
- 该测试承担本任务的 TDD 自动化部分；UI 展示层通过 `npm run build` 和手动验收路径共同验证。
