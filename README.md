# FitLoop MVP

FitLoop MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。当前阶段优先跑通一条最小但完整的核心闭环：

用户档案 -> 训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 一键采纳并写回训练计划

## 项目简介

- 前端：Vite + React + Tailwind CSS
- 后端：FastAPI + SQLite（V2.3 Phase 1-4 已接入，覆盖主数据 CRUD、聊天存储、SSE 代理、离页后台思考、计划采纳校验、后端 Agent Orchestrator、上下文压缩、memory、usage 观测、工具调用、文件上传解析、模型选择、草稿持久化和 Python 指标服务）
- 存储：
  - `profile / weeklyPlan / dailyLog` 走本地 Python 后端
  - `chat` 会话与消息已具备后端 SQLite 存储接口
  - AI 教练页发送消息已切到后端 `/api/chat/stream`，失败时回退 `/api/chat/reply`；离页时可提交后台思考任务
- AI：DeepSeek 原生 OpenAI 格式接口
- 目标：可运行、可演示、可验证

## V2.3 后端化当前状态

当前仓库已完成 Python 后端化 Phase 1 + Phase 2 + Phase 3 + Phase 4：

- 新建 `backend/` 本地服务
- 建立 SQLite 数据层与 Alembic 初始化迁移
- 接通 `profile / weeklyPlan / dailyLog` 三类主数据的后端 CRUD
- 前端 `App.jsx` 已切到后端优先加载与保存
- 支持 `localStorage -> SQLite` 一次性迁移
- 后端不可用时，前端会回退到本地缓存并提示降级状态
- Phase 2 Task 7 已把 DeepSeek 客户端、流式解析基础和 `---JSON---` 响应解析迁到后端模块
- Phase 2 Task 8 已新增 `ChatSession / ChatMessage` 两张表与聊天 CRUD 接口，支持默认会话、全量消息读取和 `suggestion` JSON 存储
- Phase 2 Task 9 已完成后端 SSE 流式对话、非流式回退接口和前端代理接入
- Phase 2 Task 10 已新增内存后台思考任务，支持离页提交、回页查询结果并把成功回复落入 `ChatMessage`
- Phase 2 Task 11 已将 AI 计划采纳校验迁到后端，`POST /api/weekly-plan/adopt` 只在用户确认后写回训练计划
- Phase 3 Task 13 已新增 `chat_session_summary / memory_item / knowledge_item / tool_call_log / usage_record`，用于后续摘要压缩、长期记忆、工具审计和 token/cache 观测
- Phase 3 Task 14 已新增后端统一上下文拼装入口：`PromptAssembler` 按稳定 system prompt、当前状态、安全记忆、相关记忆、摘要、最近消息和当前输入组装 DeepSeek messages
- Phase 3 Task 15 已新增 `UsageLedger`，可记录 DeepSeek 返回的 token 用量与 prompt cache hit/miss，并通过 `/api/chat/sessions/{id}/context/debug` 查看汇总
- Phase 3 Task 16 已完成长对话摘要压缩与状态回注，压缩后仍重新注入当前档案、周计划、今日日志、待确认建议与工具 schema 版本
- Phase 3 Task 17 已完成长期 memory 的规则提取、检索、确认与忽略接口，安全类记忆优先注入
- Phase 3 Task 18 已接入 DeepSeek Tool Calls 基础设施与只读工具，工具参数使用 strict schema + Pydantic 二次校验，工具结果进入模型前会瘦身
- Phase 3 Task 19 已完成计划修改 propose/commit 分离：模型只能生成建议卡，用户点击确认后才写回训练计划
- Phase 3 Task 20 已将前端 AI 教练发送链路切到后端 Agent Orchestrator，请求只提交 `sessionId + userInput + model/thinking + files`
- Phase 3 Task 21 已完成文档同步、验收记录和开发完成报告
- Phase 4 Task 22-24 已完成上传文件数据模型、本地缓存解析、`UploadedFile / KnowledgeItem` 写入、真实文件摘要注入和 `read_uploaded_file_summary` 工具读取
- Phase 4 Task 25 已新增 `/api/models`，后端优先读取 DeepSeek `/models`，失败时回退本地白名单；前端 AI 教练页支持模型和 thinking 选择
- Phase 4 Task 26 已新增安全 Markdown 渲染与消息列表自动滚动到底
- Phase 4 Task 27 已新增后端草稿持久化与文件附件 UI，刷新/切页后可恢复输入草稿、模型、thinking 和附件 id
- Phase 4 Task 28 已新增 Python 复杂指标服务 `/api/metrics/daily-summary`，并校准前端 prompt/展示测试口径
- AI 教练后台思考已补齐窗口 blur/focus 与组件卸载接续，后台任务也复用 Tool Calls 计划 proposal 链路，保证切页后生成的采纳卡片仍可提交

当前仍未完成前后端闭环的内容将进入后续 Phase 5 / V3：

- AI 教练页真实多会话 UI 尚未完全接入后端会话列表
- 向量知识库、跨对话知识增强、周期计划与预制计划库仍未实现
- 当前文件上传是本地缓存与摘要注入 MVP；远端文件存储、完整 OCR/视觉理解和向量检索留后续阶段

V2.3 当前重点已经完成：密钥后移、聊天全量落库、SSE 流式代理、离页后台思考、计划采纳后端校验、Phase 3 后端 Agent Orchestrator，以及 Phase 4 文件体验与模型配置增强。前端不再负责拼装 system prompt，后端统一管理上下文窗口、摘要、memory、工具调用、文件摘要和用户确认写回。

## 当前已实现能力

- 维护用户档案、训练目标与三大项 1RM
- 维护一周训练计划
- 使用 7 列课表式布局展示周计划
- 训练计划页头部工具栏展示周区间、周编号、主项/辅项图例与“计划设置”占位入口
- 单日动作卡片支持主项 / 辅项层级展示
- 训练日动作卡片支持高信息密度排版，可同时展示负重来源、组次、RPE、备注和轻量操作菜单
- 动作编辑器支持层级、组型、次数表达和两种负重模式
- 录入今日日志：体重、热量、蛋白质、睡眠、疲劳度、训练备注
- AI 发送前由后端自动读取并注入最新档案、计划、日志、摘要、长期记忆和必要工具结果
- AI 教练可上传并附加图片、Excel、DOCX、Markdown/TXT 文件，后端只注入摘要与 `fileId`
- AI 教练可通过后端模型列表切换 DeepSeek 模型和 thinking 配置
- AI 回复支持安全 Markdown 展示，新消息/流式输出会自动滚动到最新
- AI 输入草稿、模型、thinking 和附件 id 可保存到后端草稿
- AI 教练离页、Alt+Tab 或应用内切页后会把 pending 请求补交后台；回到页面会恢复“正在整理上下文”的等待态，避免误以为消息丢失
- AI 教练采纳卡片会随本地聊天展示状态保留；用户忽略或采纳成功后，本地消息会隐藏对应卡片，避免切页后重复出现
- 后端提供 Python 复杂指标摘要接口，当前与前端展示/prompt 固定样本口径对齐
- 解析 AI 回复中的结构化 JSON 建议
- 渲染采纳卡片，用户确认后通过后端 propose/commit 或兼容 adopt 接口写回训练计划
- 本地 JSON 导入 / 导出

## Task 4 已完成的训练计划升级

- 周计划升级为 7 列课表布局，训练日与休息日宽度区分显示
- 动作卡片支持主项 `main` / 辅项 `accessory` 视觉层级
- 编辑器支持组型：
  - `straight`：常规直组
  - `custom`：自定义组型
- 编辑器支持次数表达：
  - 数值次数，如 `6`
  - 文本次数，如 `6/6/8`、`10-12`
- 动作数据结构升级为“模板 + 实例”双层，同时保留扁平兼容字段，便于当前 AI 采纳链路继续工作

## Task 5 已完成的 UI 主题统一

- 全局主题切换为“冷白底板 + 蓝紫高亮”的明亮桌面风格
- `tailwind.config.js` 中新增 `repmind.*` 语义色 token，供后续组件持续复用
- 应用头部、导航、按钮、聊天面板、提示卡片、趋势图和训练计划页共享同一套颜色逻辑
- 蓝紫色只用于强调、选中、关键按钮和状态提示，避免整页被重色压住
- 四个主页面都统一到更轻的卡片阴影、边框和留白节奏，减少“发灰”和“过暗”的旧观感

## Task 6 已完成的复杂指标闭环

- Today 页新增本地复杂指标面板，统一展示 `BMR / 训练消耗 / TDEE / BMI / 热量状态 / 蛋白质状态 / 恢复数据`
- `buildDailyMetricsSummary()` 作为 Task 6 的单一指标口径，同时被 Today 页、Prompt 预览和 AI 实际注入复用
- prompt 中新增 `structured_metrics` JSON，供 DeepSeek 在已有档案、周计划和今日日志基础上继续解释复杂指标
- `src/utils/calc.js` 与 `src/utils/prompt.js` 已在 6.4 拆分为兼容层，复杂指标汇总与 prompt 分段构建分别下沉到独立工具文件
- 固定样本稳定性验收已覆盖 Today 展示与 prompt 注入一致性，避免页面显示和 AI 上下文口径漂移

## V2 已完成的 AI 教练页 UI 重构

- AI 教练页已重建为更接近主流聊天产品的单页对话形态。
- 页面内部采用左侧历史侧栏 + 中央主对话区的结构，不再展示旧版三栏工具面板。
- 空状态使用居中的欢迎文案与建议问题，点击后可直接填充输入草稿；已对话状态切换为消息流 + 底部固定输入区。
- 侧栏、消息气泡、输入框与空状态都保持和其他页面一致的浅色底板与蓝紫高亮主题。
- 历史侧栏展示项 id 基于 `chatHistory` 原始消息位置生成，新增消息后旧历史项 id 不会漂移。
- 采纳卡片的展示模型与领域建议对象已分离：`suggestionCard` 仅负责展示，采纳 / 忽略回调继续传递原始 `suggestion`。
- 顶部已移除“上下文”按钮；“新建对话”会清空当前聊天记录，但侧栏仍只使用当前假多会话展示模型。
- 本轮只做 UI 重排，不改对话能力、上下文注入、采纳链路和模型请求逻辑。

## 环境要求

- Node.js 24.13.1 或兼容版本
- npm 11.8.0 或兼容版本
- Python 3.11+（当前 worktree 使用 Python 3.14 也可运行）

## 安装命令

```bash
npm install
```

后端与本地 Python 辅助依赖由 `uv` 统一管理，安装项目依赖：

```powershell
uv sync
```

说明：

- `pyproject.toml`
- `uv.lock`
- `requirements.txt`（由 `uv export` 导出的兼容文件）
- `backend/requirements.txt` 仅作为兼容导出文件保留
- 如需重新生成该文件，可执行 `uv export --format requirements-txt -o backend\requirements.txt`

## 运行命令

```bash
npm run dev
```

默认访问地址通常为：

```text
http://localhost:5173/
```

生产构建与本地预览：

```bash
npm run build
npm run preview
```

前后端双进程联调：

```powershell
npm run dev:all
```

后端首次启动会自动在 `backend/data/repmind.db` 创建 SQLite 表，并写入空白档案与一周休息日默认计划。

只启动后端：

```powershell
npm run dev:backend
```

## API Key 配置

- 后端 Agent 模块从 `backend/.env` 读取 `DEEPSEEK_API_KEY`
- 前端不再读取 `VITE_DEEPSEEK_API_KEY`，也不再直连 DeepSeek；浏览器只请求本地后端代理
- `DATABASE_URL=sqlite+aiosqlite:///./data/repmind.db` 会按 `backend/` 目录解析，默认数据文件位于 `backend/data/repmind.db`

前端 `.env` 示例：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

说明：

- 未配置 API Key 时，除 AI 教练外的本地功能仍可使用
- 修改 `.env` 后需要重启开发服务器
- 不要提交真实 API Key

后端环境变量样例见：

- [backend/.env.example](/g:/VSCODE-G/Fitness Agent MVP/backend/.env.example)

Phase 1 + Phase 2 当前主要后端环境变量：

- `DATABASE_URL`
- `CORS_ORIGINS`
- `DATA_DIR`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEFAULT_MODEL`
- `DEEPSEEK_TIMEOUT_SECONDS`

Phase 3 说明：

- DeepSeek Thinking Mode 的 `thinking / reasoning_effort` 由前端请求传给后端，再由后端统一转交 DeepSeek；普通聊天可不显式配置。
- Tool Calls 由后端注册和执行，浏览器不会拿到 DeepSeek API Key，也不会直接执行工具。
- DeepSeek Context Caching 默认由上游处理，本项目通过稳定 system prompt 与工具 schema 前置来提升命中率，并把 `prompt_cache_hit_tokens / prompt_cache_miss_tokens` 写入 usage 记录。

Phase 4 说明：

- 文件上传缓存默认写入 `backend/data/uploads`，数据库只保存相对 `storage_path`，不写用户机器绝对路径。
- 默认上传上限为 `MAX_UPLOAD_MB=15`，支持 `.png/.jpg/.jpeg/.webp/.xlsx/.xlsm/.docx/.md/.txt`。
- `MODEL_ALLOWLIST` 默认推荐 `deepseek-v4-flash,deepseek-v4-pro`；缺少 Key 或 DeepSeek `/models` 不可用时，`/api/models` 会返回本地 fallback。
- `DEFAULT_THINKING_ENABLED=false`、`DEFAULT_THINKING_BUDGET=auto` 作为前端初始 thinking 配置。
- 文件解析状态包含 `parsed / empty / failed`；解析失败会保留记录和错误提示，但不阻断普通聊天。

## 测试命令

运行全部自动化测试：

```bash
npm test
```

按模块快速验证：

```bash
node --test tests/weeklyPlan.test.js tests/planExerciseCard.test.js
node --test tests/adoptPlan.test.js
node --test tests/coachView.test.js tests/coachChat.test.js tests/coachGuard.test.js tests/adoptCard.test.js tests/appShellConfig.test.js
node --test tests/calc.test.js tests/dailyMetricsPanel.test.js tests/prompt.test.js tests/promptPreview.test.js tests/task64MetricsStability.test.js
```

前端构建验证：

```bash
npm run build
```

Python 依赖同步与导出：

```powershell
uv sync
uv export --format requirements-txt -o requirements.txt
```

后端 Phase 1 汇总测试：

```powershell
uv run python -m pytest backend\tests\test_health.py backend\tests\test_models.py backend\tests\test_crud_api.py backend\tests\test_migrate.py
```

也可以直接运行：

```powershell
uv run pytest backend\tests\test_health.py backend\tests\test_models.py backend\tests\test_crud_api.py backend\tests\test_migrate.py
```

后端聊天存储定向测试：

```powershell
uv run pytest backend\tests\test_chat_store.py
```

后端 SSE 流式聊天定向测试：

```powershell
uv run pytest backend\tests\test_chat_stream.py
```

后端后台思考定向测试：

```powershell
uv run pytest backend\tests\test_background_worker.py
```

后端计划采纳定向测试：

```powershell
uv run pytest backend\tests\test_adopt_plan.py
```

后端 Phase 3 上下文拼装定向测试：

```powershell
uv run pytest backend\tests\test_phase3_models.py backend\tests\test_context_manager.py backend\tests\test_chat_session_context.py
uv run pytest backend\tests\test_usage_ledger.py backend\tests\test_deepseek_client.py backend\tests\test_chat_stream.py
uv run pytest backend\tests\test_summary_compressor.py backend\tests\test_memory.py backend\tests\test_memory_api.py
uv run pytest backend\tests\test_tool_calling.py backend\tests\test_chat_tool_loop.py backend\tests\test_plan_tools.py
```

后端 Phase 4 文件、模型、草稿与指标定向测试：

```powershell
uv run pytest backend\tests\test_phase4_models.py backend\tests\test_file_parsers.py backend\tests\test_file_upload.py
uv run pytest backend\tests\test_chat_files_context.py backend\tests\test_models_api.py backend\tests\test_drafts_api.py backend\tests\test_metrics_api.py
```

前端后端客户端定向测试：

```powershell
node --test tests/backendClient.test.js tests/coachComposer.test.js tests/markdownMessage.test.js tests/coachChat.test.js
node --test tests/chatSuggestionState.test.js
```

浏览器自动化冒烟测试：

```powershell
uv run python -m playwright install chromium
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_browser_smoke.py
```

该脚本会用 Playwright 打开真实 Vite 页面，并 mock 本地后端 API，覆盖 AI 教练页切换后仍显示“正在整理上下文...”以及采纳卡片可提交的核心浏览器路径。
同一套冒烟脚本也会检查 AI 教练消息列表在切换页面后是否恢复到最新对话位置。

最小验证记录见 [docs/verification.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification.md)。
V2.3 Phase 1 验收记录见 [task/V2.3/V2.3 Phase 1 验收记录.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 1 验收记录.md)。

## Demo 操作路径

1. 打开首页，确认可以进入四个主标签页。
2. 进入“我的档案”，填写基础信息、训练目标和三大项 1RM。
3. 进入“训练计划”，确认一周计划为 7 列课表布局。
4. 检查“我的档案 / 训练计划 / 今日日志 / AI 教练”四个页面是否都保持白色底板与蓝紫高亮的统一语言。
5. 任选一天新增动作，尝试切换主项 / 辅项、直组 / 自定义组型，并填写次数表达。
6. 保存动作后，使用动作卡片右上角“更多操作”菜单触发编辑 / 删除；分别编辑一个百分比动作和一个固定重量动作，确认卡片展示同步更新。
7. 进入“今日日志”，填写当天体重、热量、蛋白质、睡眠、疲劳度和备注并保存。
8. 在 Today 页确认复杂指标面板已经显示 `TDEE`、热量状态、蛋白质状态和恢复数据。
9. 切换到“AI 教练”，确认顶部不再出现“上下文”按钮，侧栏显示最近问题的假多会话列表。
10. 点击空状态建议问题，确认文案会写入底部输入框草稿。
11. 输入训练调整问题并发送，确认前端只提交用户输入，后端 Agent 自动读取档案、周计划、今日日志、memory 和最近会话。
12. 发送后立刻切到其他标签页，再回到“AI 教练”，确认后台思考完成结果能补回当前对话；如果当前对话已清空，应只提示不污染新对话。
13. 当 AI 回复包含 `---JSON---` 结构化建议时，确认页面在对应 AI 消息下方渲染采纳卡片；切换页面再回来，未处理卡片仍保留。
14. 点击“采纳并更新计划”或“忽略”，确认该卡片从本地聊天展示中隐藏；返回“训练计划”确认采纳时对应动作字段已通过后端 `/api/tools/plan/commit` 或兼容 `/api/weekly-plan/adopt` 更新并持久化。
15. 打开 `GET /api/chat/sessions/{id}/context/debug`，确认能看到 token 预算、上下文选择和 DeepSeek cache hit/miss 汇总。
16. 在 AI 教练输入区上传一个 Markdown/TXT、DOCX、Excel 或图片文件，确认出现附件 chip 和解析状态。
17. 带附件提问，确认请求只携带 `fileIds`，后端上下文 debug 中能看到 `selected_files`。
18. 切换模型和 thinking 配置后发送，确认后端聊天请求携带对应 `model/thinking`。
19. 输入未发送草稿并刷新页面，确认草稿、模型配置和附件 id 从后端恢复；发送成功后草稿与附件清空。
20. 让 AI 回复包含标题、列表或代码块，确认消息以安全 Markdown 渲染并自动滚动到最新。

### V2.3 Phase 1 迁移路径

1. 启动 `npm run dev:all`
2. 如果浏览器 localStorage 中已有旧数据且后端为空库，页面会提示一键导入
3. 点击“导入到后端”或档案页里的“一键导入到后端”
4. 确认提示文案说明旧版 `chatHistory` 暂不随迁移接口入库
5. 刷新页面，确认档案 / 周计划 / 今日日志仍然存在

### V2.3 Phase 2/3 后端 Agent 接口

- `GET /api/chat/sessions`：按最近更新时间列出会话
- `POST /api/chat/sessions`：创建普通会话，未传标题时使用“新对话”
- `GET /api/chat/sessions/default`：获取或创建默认会话，用于承接旧版单条 `chatHistory`
- `GET /api/chat/sessions/{id}/messages`：全量读取会话消息，不再执行 20 条裁剪
- `POST /api/chat/sessions/{id}/messages`：追加 `user / assistant / system` 消息，可保存 AI 结构化 `suggestion`
- `GET /api/chat/stream`：SSE 流式代理 DeepSeek，事件为 `delta / suggestion / done / error`
- `POST /api/chat/reply`：非流式后端代理，用于流式失败后的前端回退
- `POST /api/chat/{session_id}/background`：提交离页后台思考任务，返回 `{task_id}`
- `GET /api/chat/background/{task_id}`：查询后台任务状态，成功时返回 `{text, suggestion}` 并已落库
- `GET /api/chat/sessions/{id}/context/debug`：返回 token budget 与当前会话 usage 汇总，包括 `prompt_cache_hit_tokens / prompt_cache_miss_tokens`
- `GET /api/memory/items?kind&query`：查询已确认长期记忆
- `GET /api/memory/candidates`：查询待确认记忆候选
- `POST /api/memory/candidates/{id}/confirm`：确认低置信度记忆候选并晋升为 memory
- `POST /api/memory/candidates/{id}/ignore`：忽略记忆候选，避免污染上下文
- `POST /api/tools/plan/propose`：生成计划修改建议卡，不写库
- `POST /api/tools/plan/commit`：用户确认后写回计划，重复提交、过期 proposal 或非法字段都会拒绝
- `POST /api/weekly-plan/adopt`：接收 `{day, changes[]}`，返回 `{ok, message, plan}`；只支持显式 `action: "update"` 更新已有动作字段，失败时不写入脏数据
- `POST /api/files/upload`：上传本地文件，返回 metadata、解析摘要和 `fileId`
- `GET /api/files` / `GET /api/files/{id}` / `DELETE /api/files/{id}`：列出、读取 metadata、删除上传缓存
- `GET /api/models`：返回可用模型、默认模型、thinking 配置和 fallback warning
- `GET /api/chat/sessions/{id}/draft` / `PUT /api/chat/sessions/{id}/draft`：读取与保存 AI 教练草稿、模型、thinking 和附件 ids
- `GET /api/metrics/daily-summary?date=YYYY-MM-DD`：返回 Python 版每日复杂指标摘要

说明：Phase 2 旧请求仍可传入完整 `messages[]`；Phase 3 新请求默认只传 `sessionId + userInput + model/thinking + files`，由后端 `chat_session.build_agent_request()` 读取 SQLite 中的档案、周计划、日志、会话摘要、长期记忆和最近消息并拼装 DeepSeek messages。离页后台思考会先中止当前前台请求，只有成功拿到 `task_id` 后才抑制前台错误；回页补结果时会校验源 user 消息的本地下标与内容仍匹配，避免旧后台结果污染已清空或同文本重开的新对话。后台思考使用进程内任务表，服务重启后旧 task_id 不再可查；计划采纳始终保留用户点击确认闸门，AI 建议不会自动写回。

## localStorage 键说明

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`（AI 教练页仍用于本地显示状态；新发送消息同时由后端 chat 表落库）
- `fitloop:coach-background-task`（离页后台思考的待查询 task_id、源 user 下标和内容，回页成功补齐或判定对话已变化后清理）
- `fitloop_storageVersion`

更多模块职责、数据流与数据结构说明见 [ARCHITECTURE.md](/g:/VSCODE-G/Fitness Agent MVP/ARCHITECTURE.md)。
后端启动、迁移与接口速查见 [backend/README.md](/g:/VSCODE-G/Fitness Agent MVP/backend/README.md)。

## V1.5 Task 1 补充记录

- 应用壳层已切换为“左侧侧栏 + 主内容区 + 底部状态区”。
- 侧栏继续承载 `我的档案 / 训练计划 / 今日日志 / AI 教练` 四个核心入口，保留原有 tab 切换逻辑。
- 主内容区改为独立纵向滚动容器，默认隐藏整页横向滚动，为后续 16:9 全屏布局打底。
- 壳层布局模式已下沉到 `src/components/app-shell/appShellLayout.js`，用可导出的纯 JS 契约约束 AI 教练页的沉浸承载模式，避免测试依赖 JSX 源码字符串。
- 底部状态区当前展示“数据已保存 / 本地存储 / 当前浏览器自动保存”以及 `计划设置` 占位快捷按钮。
- 本任务只重构外壳与承载布局，不重写四个 tab 的内部业务结构。

### V1.5 Task 1 最小验收路径

1. 打开首页，确认左侧固定侧栏可见，且四个导航入口完整。
2. 逐个点击四个侧栏导航，确认主内容区切换到原有业务 tab，没有白屏或错位。
3. 检查页面底部状态区是否存在，并显示“数据已保存 / 本地存储”与快捷按钮占位。
4. 进入“训练计划”，确认原有 7 列课表布局仍可显示，且壳层没有制造整页横向滚动。
5. 在桌面宽屏下检查页面，确认主内容区只在需要时自身滚动，而不是整页出现横向滚动条。

## V1.5 Task 2 补充记录

- 训练计划页头部已升级为“标题 + 周区间 + 周编号 + 图例 + 计划设置占位入口”结构。
- 头部区域当前只保留必要信息，不再显示 `AI 优化建议` 或 `列表视图` 这类当前阶段无用入口。
- 周区间与周编号由独立展示模型统一生成，避免页面组件内散落日期拼装逻辑。

### V1.5 Task 2 最小验收路径

1. 打开“训练计划”页面，确认顶部出现“本周训练计划”标题。
2. 检查头部是否同时显示周区间、周编号徽标和主项 / 辅项图例。
3. 确认“计划设置”按钮存在但为占位，不误导为已实现功能。
4. 确认页面中不再出现 `AI 优化建议` 与 `列表视图` 入口。

## V1.5 Task 3 补充记录

- 周视图不再依赖默认横向滚动，而是改为桌面端按训练日 / 休息日比例分配的课表式网格。
- 当前桌面布局模型采用 `2fr / 1fr` 的宽窄列比例，让训练日更宽、休息日更窄。
- 列容器与列内业务内容已拆开，后续 Task 4 / Task 5 可以继续重构动作卡片与休息日表现，而不必再次改动整体网格。
- 为守住桌面无横向滚动目标，动作卡片指标块与编辑表单暂时收紧为更保守的单列流布局。

### V1.5 Task 3 最小验收路径

1. 在桌面宽屏下打开“训练计划”，确认一周 7 列直接显示在主视图内。
2. 检查训练日列明显比休息日列更宽，整体更像课表式看板。
3. 展开今天列并滚动页面，确认页面允许纵向增长，但主区域不依赖横向滚动。
4. 尝试新增 / 编辑动作，确认原有编辑链路没有被新网格打断。

## V1.5 Task 4 补充记录

- 训练日动作卡片已重构为高信息密度样式，主视图同时显示动作名、主辅项、负重模式、实际重量、组次、RPE 与备注。
- 百分比动作会同时显示“实际重量”和“参考 1RM × 百分比”的来源说明，固定 kg 与自重动作也有独立文案兜底。
- 右上角新增稳定的“更多操作”占位入口，先为后续菜单扩展预留位置，不改动当前编辑 / 删除链路。

### V1.5 Task 4 最小验收路径

1. 在训练日新增或编辑主项百分比动作，确认卡片同时显示实际 kg 与 `1RM × 百分比` 来源说明。
2. 检查固定 kg、自重、空备注和长动作名场景，确认卡片不破版、不依赖横向滚动。
3. 连续查看同一天多个动作卡片，确认能快速扫到主辅项、组次、RPE 与备注。
## V1.5 Task 5 补充记录

- 休息日窄列改为更轻的独立模板，顶部补齐“周几 + 月日 + 休息 badge”头部信息，贴近效果稿。
- 空状态现在区分为“训练日暂无动作”和“休息日”两类，文案与视觉层级分别处理，不再像损坏的训练日列。
- 当前阶段已移除休息日里的旧备注入口与重复重型 header 文案，避免出现没有实际能力支撑的伪交互。
- 空休息日保留“改为训练日”的轻量切换入口；休息日若暂时保留历史动作，会继续显示历史保留提示，确保切回训练类型后原有编辑链路仍可继续使用。

### V1.5 Task 5 最小验收路径
1. 打开“训练计划”，确认休息日列比训练日列更轻、更窄，顶部同时显示周几、月日和休息 badge。
2. 检查空训练日列，确认出现“暂未安排动作”提示，并仍可点击“新增动作”进入编辑。
3. 检查空休息日列，确认只显示轻量恢复提示，不出现“备注入口”按钮，并保留轻量“改为训练日”入口。
4. 将已有动作的训练日切换为 `rest`，确认历史动作仍保留且可以在切回训练类型后继续编辑。

## V1.6 收口说明

- V1.6 已完成训练计划页与效果稿的严格对齐，并统一了其余页面左侧栏风格。
- 训练计划页以固定 7 日看板为核心，不再依赖横向滚动。
- 当前训练类型控件已收敛为「训练日 / 休息日」二选一下拉，不再暴露下方多按钮切换区。
- 训练日头部不再展示「腿日 / 推日 / 拉日」等类型胶囊，只保留休息日的「休息」状态提示，避免默认训练类型污染所有训练日视觉。
- 「添加动作」按钮已移到单列底部，并与动作卡片同宽对齐。
- 顶部「第 N 周」现在可以直接点击输入修改。
- 相关总结见 [task/V1.6/V1.6 开发完成总结.md](./task/V1.6/V1.6%20%E5%BC%80%E5%8F%91%E5%AE%8C%E6%88%90%E6%80%BB%E7%BB%93.md)。
