# FitLoop MVP 架构说明

本文档说明当前 MVP 的项目结构、核心模块职责、数据流、`localStorage` 数据结构以及 AI 调用链路，并同步记录 V2.3 后端基建、Phase 2 Task 8 聊天存储、Task 4、Task 5、Task 6 与 V2 已完成的训练计划、界面主题、复杂指标升级和 AI 教练页 UI 重构。

## V2.3 后端化总览

当前项目已经从“纯前端 + localStorage”演进为“前端 + 本地 Python 后端”的双层结构：

- 前端继续负责 UI、交互、页面状态组织
- 本地 FastAPI 后端负责 `profile / weeklyPlan / dailyLog` 的持久化
- 本地 FastAPI 后端已提供 `chat_session / chat_message` 的存储接口
- SQLite 作为本地结构化存储
- AI 教练页前端仍暂用 `fitloop_chatHistory`，等待 Task 9 切换到后端聊天接口与 SSE

### 当前数据源分工

- `profile / weeklyPlan / dailyLog`
  - 主数据源：后端 SQLite
  - 本地缓存：浏览器 localStorage
- `chatHistory`
  - 后端能力：`chat_session / chat_message` 已支持默认会话、全量消息读取和 `suggestion` JSON 存储
  - 前端现状：AI 教练页仍使用浏览器 `localStorage`
  - 切换计划：Task 9 将前端 `coachChat` 改接后端 chat/SSE

### 当前新增目录

```text
backend/
  __init__.py
  api/
    chat.py
    daily_log.py
    migrate.py
    profile.py
    weekly_plan.py
  agent/
    deepseek_client.py
    response_parser.py
  db/
    database.py
    models.py
    seed.py
    migrations/
  tests/
    test_health.py
    test_models.py
    test_crud_api.py
    test_chat_store.py
    test_migrate.py
  config.py
  main.py
  requirements.txt
```

### 测试导入约定

- `backend/` 现在作为常规 Python 包参与导入，避免测试收集阶段依赖临时 `sys.path` 补丁。
- `pyproject.toml` 中的 `tool.pytest.ini_options.pythonpath = ["."]` 让 `uv run pytest ...` 与 `uv run python -m pytest ...` 的导入根路径保持一致。
- 后端测试文件直接使用 `from backend...` 导入，不再在测试体内手动插入项目根目录。

### 当前新增前端接口层

```text
src/
  api/
    appData.js
    backendClient.js
  utils/
    localMigration.js
```

### 当前阶段边界

当前已覆盖：

- 非 AI 主数据 CRUD
- localStorage 到 SQLite 的一次性迁移
- 后端不可用时的降级提示
- DeepSeek 客户端与 AI 响应解析的后端基础模块
- 聊天会话与消息的后端全量存储 CRUD

当前不覆盖：

- AI 教练页前端切换到后端聊天接口
- DeepSeek 后端代理 API
- SSE 流式
- 后台思考
- 计划采纳后端化

这些内容属于 V2.3 Phase 2。

## 当前项目结构

```text
src/
  api/
    deepseek.js
  components/
    AdoptCard.jsx
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
    coach/
      ChatSidebar.jsx
      ChatTopbar.jsx
      CoachLayout.jsx
      Composer.jsx
      EmptyState.jsx
      MessageBubble.jsx
      MessageList.jsx
    plan-grid/
      PlanWeekGrid.jsx
      PlanWeekGridColumn.jsx
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
    coachView.js
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
  - 当前 `profile / weeklyPlan / dailyLog` 已后端优先；`chatHistory` 前端切源留给 Task 9

- `backend/api/chat.py`
  - 负责聊天会话与消息的后端 CRUD
  - 提供会话列表、创建会话、获取或创建默认会话、追加消息、全量读取消息
  - 只做存储，不触发 DeepSeek 调用，避免提前吞并 SSE 与后台思考职责

- `backend/db/models.py`
  - 定义 `Profile / WeeklyPlanDay / DailyLog / ChatSession / ChatMessage`
  - `ChatMessage.suggestion` 以 JSON 可空列保存结构化建议，便于后续 Task 9/11 复用

- `src/tabs/CoachTab.jsx`
  - 负责 AI 教练页状态协调
  - 继续管理 `draft / errorMessage / isSending / streamingText`
  - 负责发送、流式回退、建议采纳 / 忽略、新建对话和假多会话选中态
  - 继续复用 `requestCoachReply()` / `requestCoachReplyStream()`、`appendChatMessages()` 与 `adoptPlanChange()`

- `src/components/coach/CoachLayout.jsx`
  - 负责历史侧栏 + 主聊天区的两列布局
  - 保证消息区是主区域唯一纵向滚动容器

- `src/components/coach/ChatSidebar.jsx`
  - 负责渲染“新建对话”和历史侧栏列表
  - 当前只消费 `buildCoachHistoryView()` 生成的假多会话展示模型

- `src/components/coach/ChatTopbar.jsx`
  - 负责渲染当前对话标题、模型 badge、清空和导出操作
  - 顶部不再承载“上下文”切换

- `src/components/coach/MessageList.jsx`
  - 负责空状态和消息流切换
  - 承担自动滚动与流式回复追底逻辑

- `src/components/coach/MessageBubble.jsx`
  - 负责渲染用户消息、AI 消息、流式回复和建议卡挂载位
  - 采纳 / 忽略继续把原始 suggestion 往上回传

- `src/components/coach/Composer.jsx`
  - 负责底部输入框、自适应高度、Enter 发送、Shift+Enter 换行和错误提示

- `src/components/coach/EmptyState.jsx`
  - 负责欢迎页和四个建议问题入口
  - 点击建议问题后直接把文案写回 `CoachTab` 草稿态

- `src/utils/coachView.js`
  - 负责 AI 教练页视图层纯函数
  - 提供流式文本剥离、假多会话历史模型和空状态建议问题模型

- `src/tabs/PlanTab.jsx`
  - 负责周计划页面组织
  - 通过 `buildPlanHeaderModel()` 与 `PlanHeaderToolbar` 组装头部工具栏
  - 通过 `buildWeeklyPlanLayoutModel()` 与 `PlanWeekGrid` 组装 7 列比例网格
  - 协调单日展开、动作新增、编辑、删除

- `src/components/plan-grid/PlanWeekGrid.jsx`
  - 负责桌面端周视图比例网格
  - 统一承载训练日宽列、休息日窄列和非目标视口兜底策略

- `src/components/plan-grid/PlanWeekGridColumn.jsx`
  - 负责单列外壳、列跨度和展开态强调
  - 让列容器和列内业务内容分离，降低 `PlanDayCard` 复杂度

- `src/components/plan-header/PlanHeaderToolbar.jsx`
  - 负责训练计划页头部工具栏的布局编排
  - 展示标题、周区间、周编号、主项/辅项图例与“计划设置”占位按钮

- `src/components/plan-header/PlanHeaderLegend.jsx`
  - 负责主项 / 辅项图例渲染

- `src/utils/planHeader.js`
  - 负责训练计划页头部展示模型
  - 统一生成周区间、ISO 周编号、图例配置与占位按钮配置

- `src/components/PlanDayCard.jsx`
  - 作为单列内部业务内容的协调壳
  - 只负责组合头部、训练类型区、动作编辑区和动作列表

- `src/components/PlanDayCardHeader.jsx`
  - 展示星期标签、日期标签、训练日 / 恢复日模式、训练类型和动作数量

- `src/components/PlanDayTypeSection.jsx`
  - 负责训练类型输入
  - 使用“文本输入 + datalist 联想 + 快捷按钮”组合
  - 在空休息日里支持轻量快捷切换模式，避免视觉回退到旧版厚重编辑块

- `src/components/PlanExerciseEditorCard.jsx`
  - 封装新增动作 / 编辑动作的表单容器

- `src/components/PlanExerciseItem.jsx`
  - 负责单个动作卡片的展示和局部编辑切换
  - 当前训练日卡片采用高信息密度布局，统一承载主辅项、负重来源、组次、RPE、备注与右上角轻量操作菜单

- `src/components/ExerciseEditor.jsx`
  - 负责动作编辑表单本体
  - 支持层级、组型、次数表达、负重模式、RPE、备注

- `src/utils/planLayout.js`
  - 负责把 weeklyPlan 映射成周视图列数据
  - 统一生成桌面比例网格模板、训练日 / 休息日列跨度、每天日期标签和布局兜底标记

- `src/utils/weeklyPlan.js`
  - 负责周计划结构归一化
  - 负责训练类型更新、动作增删改、RPE 边界兜底

- `src/utils/exerciseForm.js`
  - 负责表单草稿与计划动作结构之间的转换

- `src/utils/planEditorState.js`
  - 负责训练计划页新增 / 编辑 / 删除动作时的局部编辑状态契约
  - 集中约束“当前编辑的是哪一天哪一个动作”，避免跨日期误编辑，并为卡片菜单动作提供稳定映射

- `src/utils/planExerciseCard.js`
  - 负责把动作结构转换成卡片展示模型
  - 统一处理百分比重量、固定 kg、自重动作、空备注与长动作名的展示兜底

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

### 5. AI 教练页 UI 流

```text
CoachTab
  -> buildCoachHistoryView(chatHistory)
  -> 渲染 ChatSidebar + CoachLayout + MessageList + Composer
  -> 空状态展示欢迎文案、建议问题和底部输入区
  -> 已对话状态展示消息流、建议卡片和底部固定输入区
  -> 发送时优先流式输出，失败回退普通请求
  -> 将结构化 suggestion 只保存在页面级易失状态
  -> 将消息追加到 chatHistory
```

### 6. 后端聊天存储流

```text
Task 9 之前的后端可用能力
  -> GET /api/chat/sessions/default
      -> 获取或创建“默认对话”
  -> POST /api/chat/sessions/{id}/messages
      -> 追加 user / assistant / system 消息
      -> 可选保存 suggestion JSON
      -> 同步刷新 ChatSession.updated_at
  -> GET /api/chat/sessions/{id}/messages
      -> 按 created_at / id 正序全量返回，不做 20 条裁剪
```

这条流当前只作为后端能力存在；AI 教练页正式使用它要等 Task 9 前端切源。

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

当前 AI 教练页前端仍使用该 key；V2.3 Phase 2 Task 8 已提供后端 chat 存储接口，但前端尚未切换。

只持久化：

- `role`
- `content`

结构化建议卡片不落盘，仅存在于当前页面状态中。

AI 教练页的消息展示补充约束：

- `message.suggestion`：原始领域建议对象，供 `adoptPlanChange()` 等业务链路消费
- `message.suggestionCard`：由 `buildAdoptCardModel()` 派生的展示模型，只负责渲染采纳卡片
- 采纳 / 忽略回调必须继续传递 `message.suggestion`，不能把 `suggestionCard` 冒充为领域 suggestion
- 结构化建议不会写回 `fitloop_chatHistory`，避免 localStorage 中混入展示态和易失业务态

### 后端 `chat_session / chat_message`

Task 8 新增的后端聊天表：

- `chat_session`
  - `id`
  - `title`
  - `created_at`
  - `updated_at`
- `chat_message`
  - `id`
  - `session_id`
  - `role`
  - `content`
  - `suggestion`
  - `created_at`

设计约束：

- 默认会话标题为“默认对话”，用于承接旧版单条 `chatHistory`
- 普通创建会话未传标题时使用“新对话”，避免和默认会话语义混淆
- 消息读取必须全量返回，不沿用前端上下文窗口的 20 条裁剪
- `suggestion` 允许为空；非空时保存 AI 结构化建议原始 JSON
- 新增消息时刷新会话 `updated_at`，供后续真实会话列表按最近对话排序

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
- AI 教练页历史侧栏若使用 `buildCoachHistoryView()`，其展示 id 需基于原始 `chatHistory` 下标生成，例如 `session-message-12`，保证新增消息后既有历史项 id 稳定可命中

## Task 4 已完成升级说明

### 1. 7 列课表布局

- `src/utils/planLayout.js` 负责将周计划转换成 7 列展示模型
- 训练日列宽更大，休息日列宽更小

### 2. 主项 / 辅项卡片

- `src/utils/planExerciseCard.js` 负责构建动作卡片模型
- 主项使用更高对比度样式
- 辅项使用更轻的视觉层级
- 卡片主视图同时展示动作名、负重来源、实际重量、组次、RPE 与备注，减少训练日列内的信息折叠
- 右上角保留稳定的“更多操作”占位入口，为 Task 6 之后的菜单扩展预留挂载位

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
  - 只消费 `appShellLayout.js` 输出的壳层布局契约，减少 JSX 内部散落的 coach 特判。
  - `coach` 模式会移除默认 padding，并将 `fitloop-shell__content` 切到 `overflow-hidden`，把滚动权交给 AI 教练页内部。

- `src/components/app-shell/appShellLayout.js`
  - 负责定义壳层布局模式契约。
  - 当前提供 `default / coach` 两种模式，统一约束外层留白与内容区滚动策略。

- `src/components/app-shell/ShellSidebar.jsx`
  - 负责品牌区、四个导航入口和当前工作区提示。
  - 只消费壳层元信息，不直接依赖业务 tab 内部数据结构。

- `src/components/app-shell/ShellStatusBar.jsx`
  - 负责底部保存状态提示与 MVP 占位快捷按钮。

- `src/components/app-shell/appShellConfig.js`
  - 负责四个导航项、快捷按钮和状态文案配置。
  - 提供可被 `node --test` 直接验证的最小壳层契约。

- `tests/appShellConfig.test.js`
  - 直接校验 `appShellConfig.js` 与 `appShellLayout.js` 导出的稳定契约。
  - 不再通过读取 `AppShell.jsx` 源码字符串推断 coach 页承载模式，降低重构噪音。

### 验证补充

- 新增 `tests/appShellConfig.test.js`，覆盖四个核心导航顺序、未知 tab 回退、状态区文案和快捷按钮占位。
- 该测试承担本任务的 TDD 自动化部分；UI 展示层通过 `npm run build` 和手动验收路径共同验证。

## V1.5 Task 3 周视图网格补充

### 新增结构

```text
src/
  components/
    plan-grid/
      PlanWeekGrid.jsx
      PlanWeekGridColumn.jsx
```

### 布局职责

- `src/utils/planLayout.js`
  - 输出 `buildWeeklyPlanLayoutModel()`，统一定义桌面端比例网格模板。
  - 当前训练日列跨度为 `2`，休息日列跨度为 `1`，对应效果稿里的宽窄列结构。

- `src/components/plan-grid/PlanWeekGrid.jsx`
  - 负责把周计划列模型渲染为桌面比例网格。
  - 桌面端默认避免横向滚动，非目标视口再降级为更紧凑堆叠策略。

- `src/components/plan-grid/PlanWeekGridColumn.jsx`
  - 负责每一列的外壳、列跨度和展开态强调。
  - 让 `PlanDayCard` 不再承担宽度类和外层布局职责。

### 组件调整

- `src/components/PlanDayCard.jsx`
  - 改为只承载列内业务内容，不再持有宽度类名。

- `src/components/PlanExerciseItem.jsx`
  - 指标块改为更保守的单列流，优先保证桌面无横向溢出。

- `src/components/ExerciseEditor.jsx`
  - 当前阶段使用单列编辑表单，避免窄列里被响应式多列布局硬撑开。

### 验证补充

- `tests/planLayout.test.js` 已补充桌面比例模板、列跨度与兜底标志断言。
- 本任务的自动化验证重点是布局模型契约；真实 16:9 观感仍需后续 UI 验收继续确认。
## V1.5 Task 5 补充说明

### 新增结构

```text
src/
  components/
    plan-rest/
      PlanDayEmptyState.jsx
      PlanRestDayPanel.jsx
  utils/
    planDayDisplay.js
tests/
  planDayDisplay.test.js
```

### 展示模型职责

- `src/utils/planDayDisplay.js`
  - 负责把单日计划映射为展示模型，集中判断休息日、空训练日、历史动作保留提示、轻量切换入口和无备注入口约束。
  - 让 `PlanDayCard.jsx` 只消费展示结果，减少 JSX 内散落的条件分支。

### 组件职责调整

- `src/components/PlanDayCard.jsx`
  - 根据展示模型切换训练日空状态、休息日轻量面板和历史动作提示。
  - 继续承载训练类型切换、新增动作、动作编辑与删除链路。
- `src/components/PlanDayCardHeader.jsx`
  - 训练日与休息日共用同一入口，但根据展示模型输出不同的头部信息密度。
  - 空休息日窄列只保留“周几 + 月日 + 休息 badge”，避免与中部恢复面板重复表达。
- `src/components/plan-grid/PlanWeekGridColumn.jsx`
  - 继续负责宽窄列比例，同时让休息日列使用更轻的容器样式。
- `src/components/plan-rest/PlanDayEmptyState.jsx`
  - 负责训练日空动作状态的轻量提示。
- `src/components/plan-rest/PlanRestDayPanel.jsx`
  - 负责休息日空列的独立轻量模板，不引入无效备注入口。

- `src/components/PlanDayTypeSection.jsx`
  - 空休息日使用紧凑模式，只暴露“改为训练日”的轻量快捷入口。
  - 有历史动作的休息日与训练日继续保留完整训练类型输入链路。

### 验证补充

- `tests/planDayDisplay.test.js`
  - 覆盖休息日空状态、空训练日状态、休息日保留历史动作、轻量切换入口以及“无备注入口”约束。

## V1.6 收口说明

- V1.6 将训练计划页的壳层、头部、七日看板、卡片和侧栏统一收束到效果稿结构。
- 训练计划页的展示层以固定 7 日布局为核心，数据只负责映射，不再驱动页面骨架变化。
- `PlanDayTypeSection` 已收敛为单个二选一下拉，只保留「训练日 / 休息日」模式，不再渲染下方一组快捷按钮。
- `PlanDayCard` 现在把「添加动作」按钮放到单列底部，并通过 `w-full` 与动作卡片保持同宽。
- `PlanHeaderToolbar` 的周编号已改为可点击输入的内联编辑控件，直接回写 `weeklyPlan.weekMeta.weekNumber`。
- 其余页面继续复用统一壳层，只保留各自必要内容区。
- 版本总结见 `task/V1.6/V1.6 开发完成总结.md`。

## V2 收口说明

- AI 教练页已重构为更接近主流聊天产品的布局。
- 页面内部改为左侧历史侧栏 + 中央主聊天区，不再保留旧版三栏工具面板。
- 空状态与已对话状态分别使用欢迎页建议问题与消息流式输入区。
- 顶部已移除“上下文”按钮；前端新建对话当前仍只清空 `chatHistory`，后端真实会话存储已在 V2.3 Phase 2 Task 8 落地，前端接入留给 Task 9 之后。
- 本轮仅重排 UI，不改变 DeepSeek 接口、上下文注入和采纳链路。
- 版本总结见 `task/V2/V2 开发完成总结.md`。
