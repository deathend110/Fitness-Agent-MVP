# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 协作约定（必须遵守）

本仓库的 Agent 协作规则以 [AGENTS.md](AGENTS.md) 为权威来源，开始任何任务前先读它。下面是最容易被忽略、但必须执行的几条：

- **流程顺序**：plan → code → review。较大功能先定计划，再编码，最后审查与验证记录。
- **编码默认走子代理**：写代码任务默认调用 `superpowers:subagent-driven-development`，由子代理实现。主 agent 负责规划、拆分、派发与**两轮审查**（先对计划/规格，再查代码质量+验证+文档同步）。子代理产出未经主 agent 审查验证，不算完成。只有用户明确要求、或子代理流程被环境/工具阻塞时，主 agent 才直接编码并说明原因。
- **每个子任务验证通过后立即 `git commit`**，commit message 用**中文**，准确描述本次改动核心。
- **文档同步是硬性要求**：每次改代码都要同步更新 [README.md](README.md) 与 [ARCHITECTURE.md](ARCHITECTURE.md)。
- **注释用中文**，解释业务意图 / 关键数据流 / 边界情况 / 非显而易见的原因，不写“设置变量”这类废话。整体代码 UTF-8。
- **200 行拆分规则**：单文件超过 200 行必须评估拆分。页面组件只做组织与状态协调，可复用 UI、业务计算、localStorage、AI 调用、Prompt 构建都拆到独立文件。
- 实现需求时持续对齐 `docs/idea.md`、`docs/plan.md`、`docs/fitness_coach_mvp_spec.md`；需求冲突时以课程 MVP 要求和 SDD 文档为准。不随意删除用户已有文档/内容。

## 常用命令

```bash
npm install                      # 安装依赖（Node 24.x / npm 11.x）
npm run dev                      # 启动开发服务器，默认 http://localhost:5173/
npm run build                    # 生产构建，同时作为前端验证手段（无类型检查/lint，构建即检查）
npm run preview                  # 本地预览构建产物
npm test                         # 跑全部测试：node --test "tests/*.test.js"
node --test tests/calc.test.js   # 跑单个测试文件
```

- AI 功能需在根目录 `.env` 配置 `VITE_DEEPSEEK_API_KEY`；改 `.env` 后必须重启 dev server。未配置时除 AI 教练外的本地功能仍可用。
- 没有 lint / typecheck 脚本，也没有 jsdom——验证手段是 `npm test` + `npm run build` + 手动验收（见 README 的 Demo 路径与 `docs/verification.md`）。

## 架构要点（需跨文件理解的部分）

详细模块职责见 [ARCHITECTURE.md](ARCHITECTURE.md)。以下是贯穿全局、决定如何写代码的关键设计：

### 逻辑在 utils，渲染在 components —— 由测试策略驱动
这是本仓库最重要的约束。测试用 Node 内置 `node:test` + `node:assert/strict`，**不渲染 React、没有 DOM**。因此：
- 所有业务计算、归一化、展示模型构建都写成 `src/utils/*.js` 里的**纯函数**（如 `buildPlanHeaderModel` / `buildWeeklyPlanLayoutModel` / `buildCoachHistoryView` / `buildAdoptCardModel` / `buildDailyMetricsPanelModel` / `planDayDisplay.js`），由测试直接断言。
- `.jsx` 组件只 import 这些纯函数并渲染结果，尽量不在 JSX 里散落业务分支。
- 个别测试（如 `tests/appShellConfig.test.js`）用 `fs.readFileSync` 读 JSX 源码 + `assert.match` 来验证组件是否正确接线了契约——新增此类约束时沿用这种“契约 + 源码断言”模式，不要引入 DOM 测试依赖。

**含义**：要让新功能可测，先把逻辑下沉到 utils 纯函数，再在组件里消费；不要把可测逻辑埋进 JSX。

### 顶层状态与持久化
[src/App.jsx](src/App.jsx) 拥有 `profile / weeklyPlan / dailyLog / chatHistory` 四份顶层 state，启动时从 localStorage 读取，用 `useEffect` 写回。`src/tabs/*.jsx` 是页面协调层，通过 props 拿状态和回调，不各自持有持久化逻辑。localStorage 键：`fitloop_profile`、`fitloop_weeklyPlan`、`fitloop_dailyLog`、`fitloop_chatHistory`、`fitloop_storageVersion`。

### AI 调用链路（含用户确认闸门）
```
CoachTab
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)   # 每次发送前重新注入最新上下文
  -> streamDeepSeekChat()  （流式优先）
  -> 失败回退 requestDeepSeekChat()  （普通请求）
  -> parseAiResponse(content)   # 以 "---JSON---" 分隔正文与结构化建议，JSON 解析失败安全回退纯文本
  -> 渲染文本 + AdoptCard
  -> 用户点击采纳 -> adoptPlanChange() -> 写回 weeklyPlan
```
- AI 接口实现在 [src/api/deepseek.js](src/api/deepseek.js)：DeepSeek 原生 OpenAI 格式，默认模型 `deepseek-v4-flash`，错误统一包成 `DeepSeekApiError`，`fetchImpl` 可注入以便测试。
- **AI 回复解析与计划写回严格分离**，保留用户最终确认权——不要让 AI 建议直接改计划。
- 展示模型 `suggestionCard` 与领域对象 `suggestion` 必须分开：采纳/忽略回调传原始 `suggestion`，`suggestionCard` 只负责渲染。结构化建议不落盘到 `chatHistory`。

### 复杂指标单一口径
`buildDailyMetricsSummary()`（`src/utils/dailyMetrics.js`）是复杂指标（BMR/TDEE/BMI/热量状态/蛋白质状态/恢复数据）的**唯一来源**，被 Today 页展示、Prompt 注入、测试三方复用，避免页面显示与 AI 上下文口径漂移。指标不单独持久化，运行时按 `profile + weeklyPlan + dailyLog` 即时汇总。

### 兼容层式拆分
为遵守 200 行规则又不破坏调用方，部分模块被拆成“薄入口 + 实现文件”：`src/utils/calc.js` 现在只是兼容层，重新导出 `calcBase.js`（基础计算）与 `dailyMetrics.js`（指标汇总）；`src/utils/prompt.js` 是 system prompt 的薄入口，分段构建下沉到 `promptSections.js`。**拆分时保留原有 import 路径的再导出**，沿用这一模式。

### 动作数据结构：模板 + 实例 + 扁平兼容字段
`weeklyPlan` 里的动作对象同时含 `template`（编排信息）、`instance`（负重/RPE/备注执行层），外加一组扁平字段（`pct/kg/sets/reps/rpe/note` 等）。扁平字段是为了让当前 AI 采纳链路继续工作，改动动作结构时不要删掉它们。
