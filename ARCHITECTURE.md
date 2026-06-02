# RepMind MVP 架构说明

本文档说明当前 MVP 的项目结构、核心模块职责、数据流、`localStorage` 数据结构以及 AI 调用链路，并同步记录 V2.3 后端基建、Phase 2 聊天代理与后台思考、Phase 3 后端 Agent 上下文编排、Phase 4 文件体验与模型配置、Task 4、Task 5、Task 6、V2.7 接口收口与 V2 已完成的训练计划、界面主题、复杂指标升级和 AI 教练页 UI 重构。

## V2.7 收口总览

V2.7 的目标不是新增功能，而是把 AI 教练相关接口统一到当前真实主链路，并把历史入口降级成兼容壳：

- 前端聊天主链路固定为 `CoachTab -> coachChat.js -> coachBackend.js`
- 前端普通后端操作固定为 `backendClient.js`
- 后端聊天主链路固定为 `chat.py -> chat_session.py -> run_tool_calling_chat() -> provider runtime`
- proposal 卡标准协议固定为 `/api/tools/plan/commit` 与 `/api/tools/plan/ignore`
- `DeepSeekClient`、`src/api/deepseek.js`、`/api/weekly-plan/adopt`、聊天 `messages` 旧契约继续保留兼容，但不再作为主流程扩展入口

## V2.3 后端化总览

当前项目已经从“纯前端 + localStorage”演进为“前端 + 本地 Python 后端”的双层结构：

- 前端继续负责 UI、交互、页面状态组织
- 本地 FastAPI 后端负责 `profile / weeklyPlan / dailyLog` 的持久化
- 本地 FastAPI 后端已提供 `chat_session / chat_message` 的存储接口、`/api/chat/stream` SSE 代理、离页后台思考任务和计划采纳校验接口
- Phase 3 已完成 Agent Orchestrator：后端可在只收到 `userInput` 时读取 SQLite 状态、拼装 Agent messages、执行只读工具循环，并生成需用户确认的计划修改 proposal；当前 DeepSeek 默认也已统一走 OpenAI-compatible `/v1` 运行时
- 针对 Gemini-native，工具回环现在会在“用户本轮明确要求生成待确认 proposal 卡”时把首轮 tool choice 提升为 `required`；这样既保留平时 `AUTO` 的自然对话体验，又能避免 Gemini 在关键 proposal 场景里只返回自然语言正文、不返回结构化工具结果
- 针对 DeepSeek `/v1` 兼容链路，当前已进一步收紧为“统一不主动发送 `tool_choice`”；这是因为真实 DeepSeek v4 服务对 `thinking + tool_choice` 以及部分 `auto/required` 组合都会返回 400。DeepSeek 的计划卡稳定性改由 proposal 工具按轮暴露、结构化结果校验，以及必要时追加一轮系统纠偏重试共同保证
- proposal 类工具现在采用“按轮暴露”策略：只有当用户本轮明确表达“生成计划卡 / 修改计划 / 调整卡 / 生成新计划”等计划修改意图时，`propose_plan_change` / `propose_day_plan_replace` 才会进入工具 schema；普通解释、追问和恢复分析只保留只读工具
- 当用户本轮明确要求“生成计划修改卡 / 计划卡 / 修改卡”而模型首轮只输出文字版卡片时，聊天入口会自动追加一条系统纠偏消息，再走一轮同样的工具回环，要求模型必须通过 proposal 工具返回结构化结果；只有仍未拿到 proposal 时，才会向前端返回 `missing_plan_proposal`
- 计划卡处理状态已统一为 `pending / committed / ignored`；`commit` 与 `ignore` 都会同步回写 `chat_message.suggestion.status`，这样同会话后续上下文能明确知道上一张卡已处理，避免模型在未被再次唤起时继续重复出卡
- Phase 4 已完成文件上传解析、文件摘要上下文注入、模型列表 fallback、Coach 草稿持久化、安全 Markdown 渲染、对话滚动定位和 Python 指标摘要服务
- SQLite 作为本地结构化存储
- 后端通用配置继续从 `backend/.env` 读取；模型 provider 配置已开始拆到独立 JSON 文件 `backend/config/model_providers.json`，路径由 `MODEL_PROVIDER_CONFIG_PATH` 控制，缺失时会用旧版 DeepSeek 环境变量自动生成首份文件。新版 bootstrap 默认生成 `https://api.deepseek.com/v1 + chat_completions + append_v1`；相对 SQLite 路径按 `backend/` 目录解析，启动时自动创建本地表并播种空白 MVP 数据。保存模型配置后会立刻刷新运行时缓存，前台聊天、流式输出与后台任务都无需重启即可生效
- 本地联调配置现已按职责拆分到两层 `.env`：根目录 `.env` 负责 `VITE_API_BASE_URL / VITE_DEV_PORT`，`vite.config.js` 会读取 `VITE_DEV_PORT` 统一前端 dev server 端口；`backend/.env` 负责 `BACKEND_HOST / BACKEND_PORT`，`npm run dev:backend` 会通过 `backend/run_dev_server.py` 读取它们再启动 uvicorn，避免前后端端口写死在多处
- 当前仓库内对 DeepSeek 的默认口径也已同步固化到 `/v1` 形态：`.env.example` 默认值使用 `https://api.deepseek.com/v1`，README 与运行时文档都以 `chat_completions + append_v1` 为主说明；`DeepSeekClient` 不再承担主路径，只作为 provider runtime 缺失时的 fallback
- AI 教练页发送消息走后端聊天代理，历史侧栏和消息恢复已切到后端 `chat_session / chat_message`

### 当前数据源分工

- `profile / weeklyPlan / dailyLog`
  - 主数据源：后端 SQLite
  - 本地缓存：浏览器 localStorage
- `chatHistory`
  - 后端能力：`chat_session / chat_message` 已支持默认会话、全量消息读取、`suggestion` JSON 存储和 SSE 代理落库
  - 前端现状：侧栏从 `GET /api/chat/sessions` 读取真实会话；选中会话后从 `GET /api/chat/sessions/{id}/messages` 恢复消息；`fitloop_chatHistory` 仅作为当前会话展示缓存和旧导入导出兼容
  - `fitloop:coach-active-session-id` 用于刷新后恢复当前会话；离页时记录后台 task_id，回页查询成功结果并补齐 assistant 消息

### 当前新增目录

```text
backend/
  __init__.py
  api/
    chat.py
    daily_log.py
    drafts.py
    files.py
    memory.py
    metrics.py
    migrate.py
    models.py
    profile.py
    tools.py
    weekly_plan.py
  agent/
    adopt_plan.py
    background_worker.py
    chat_session.py
    context_manager.py
    deepseek_client.py
    memory.py
    prompt_templates.py
    response_parser.py
    tool_calling.py
    tool_loop.py
    usage_ledger.py
  files/
    uploader.py
    parsers/
      docx_parser.py
      excel_parser.py
      image_parser.py
      md_parser.py
  metrics/
    daily_metrics.py
  model_config/
    bootstrap.py
    runtime.py
    service.py
    types.py
  providers/
    base.py
    gemini_client.py
    gemini_native.py
    openai_compatible_client.py
    openai_compatible.py
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
    test_chat_stream.py
    test_adopt_plan.py
    test_background_worker.py
    test_chat_files_context.py
    test_drafts_api.py
    test_file_parsers.py
    test_file_upload.py
    test_migrate.py
    test_metrics_api.py
    test_models_api.py
  config.py
  main.py
  requirements.txt
scripts/
  kill-fitloop.ps1
  kill-repmind.ps1
```

### 测试导入约定

- `backend/` 现在作为常规 Python 包参与导入，避免测试收集阶段依赖临时 `sys.path` 补丁。
- `pyproject.toml` 中的 `tool.pytest.ini_options.pythonpath = ["."]` 让 `uv run pytest ...` 与 `uv run python -m pytest ...` 的导入根路径保持一致。
- 后端测试文件直接使用 `from backend...` 导入，不再在测试体内手动插入项目根目录。

### 浏览器自动化验证

- `tests/e2e/coach_browser_smoke.py`
  - 使用 Python Playwright 打开真实 Vite 页面，后端 API 通过浏览器路由 mock。
  - 覆盖 AI 教练页后台任务恢复、切换 tab 后“正在整理上下文...”继续展示、采纳卡片持久展示与 `/api/tools/plan/commit` 提交参数。
  - 通过 `uv run python ...` 运行，避免依赖全局 Python 环境。

- `src/utils/chatSuggestionState.js`
  - 负责 AI 教练消息里的 suggestion 元数据合并，最新消息优先，避免相同回复内容复用旧 proposalId。
  - 只有同一 proposal 才保留 dismissed 状态，防止旧卡片隐藏标记误伤新卡片。

- `src/components/coach/MessageList.jsx`
  - 首次挂载和切回 AI 教练页时会自动贴到底部，确保用户看到最新消息。
  - 仍保留“用户手动上翻时不强制追底”的滚动判定。

- `src/tabs/CoachTab.jsx`
  - 将“前台发送中”和“后台思考中”拆成两套状态：`isSending` 只控制输入区提交态，`isBackgroundThinking` 只控制消息区提示气泡。
  - 采纳计划卡、切页恢复后台任务等场景下，即使消息区继续显示“思考中”，输入框也不会再被后台 pending/running 状态锁死。
  - 后台任务提交现在只在真实离页相关事件中触发，如 `visibilitychange(hidden)` 与 `pagehide`；不再使用 `blur` 或 effect cleanup 误触发提交。

- `src/components/coach/MessageBubble.jsx`
  - assistant 的“思考中”占位态保留紧凑气泡，但把旧版方块光标替换成三个逐次淡入淡出的圆点动效。
  - 该动效通过 `fitloop-thinking-dot` 关键帧实现，只用于 assistant streaming/pending 提示，不影响普通消息正文与用户侧输入光标。

### 本地运维脚本

- `scripts/kill-repmind.ps1`
  - 负责停止当前仓库关联的 `vite / uvicorn / concurrently / uv` 等本地开发进程。
  - 只匹配命令行中包含当前仓库路径或 `RepMind` 标识的进程，避免误杀其他项目。
- `scripts/kill-fitloop.ps1`
  - 兼容旧脚本入口，内部直接转发到 `kill-repmind.ps1`，避免历史命令或习惯用法失效。

### 当前新增前端接口层

```text
src/
  api/
    coachBackend.js
    appData.js
    backendClient.js
  utils/
    localMigration.js
    markdownMessage.js
```

### 当前阶段边界

当前已覆盖：

- 非 AI 主数据 CRUD
- localStorage 到 SQLite 的一次性迁移
- 后端不可用时的降级提示
- DeepSeek 客户端与 AI 响应解析的后端基础模块
- 聊天会话与消息的后端全量存储 CRUD
- 后端 DeepSeek SSE 代理、非流式回退接口与进程内后台思考任务
- 后端计划采纳校验与写回接口
- Phase 4 文件上传解析、文件摘要注入、模型列表、草稿持久化和每日指标摘要接口
- 前端 AI 教练附件上传、模型/Thinking 选择、安全 Markdown 渲染和自动滚动到底
- 前端 `coachChat` 经 `coachBackend` 调用后端聊天接口

当前不覆盖，留给 Phase 5 / V3：

- 向量知识库、远端文件存储、完整 OCR/视觉理解、完整知识库和周期计划引擎

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
      FileAttachmentTray.jsx
      MarkdownMessage.jsx
      MessageBubble.jsx
      MessageList.jsx
      ModelConfigDialog.jsx
      ModelSelector.jsx
      ProviderConfigEditor.jsx
      ProviderModelPicker.jsx
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
    markdownMessage.js
    modelConfigView.js
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
  - 负责聊天会话与消息的后端 CRUD、SSE 流式代理、非流式回退代理和后台思考任务 API
  - 提供会话列表、创建会话、删除会话、获取或创建默认会话、追加消息、全量读取消息
  - `POST /api/chat/reply` 已支持 Phase 3 新契约 `{sessionId?, userInput, model?}`，同时保留 Phase 2 `{sessionId?, messages, model?}` 兼容路径
  - `reply / stream / background` 入口现在都会先经过统一请求归一层，把 `userInput` 新契约与 `messages` 旧契约收口成一份内部结构，避免三处长期各自维护分支
  - `model` 现已统一兼容旧版 plain modelId 与新版 `modelRef(provider_id::remote_id)`；请求供应商前会先解析运行时配置，再把真实 `remote_model_id` 交给客户端
  - 当工具循环返回 `proposal.status="pending"` 时，只会在 assistant 正文出现“已采纳 / 已写入计划 / 已更新计划”等误导性措辞时做最小后端收口；正常“待确认”文案不会被改写
- 通过 `backend/agent/chat_session.py` 里的共享 provider runtime 选择器，前台聊天与后台任务会使用同一套 provider-bound client：Gemini-native 继续直连 `GeminiNativeClient`，OpenAI-compatible 会按 `wireApi/apiPathMode` 选择 `chat_completions` 或 `responses` 运行时；DeepSeek 默认也绑定到这套 OpenAI-compatible `/v1` 运行时，不再错误回退到旧直连链路
  - `/api/chat/stream` 将统一聊天运行时的文本事件映射为 `delta / suggestion / proposal / done / error`
  - 成功完成后一次性写入本轮 user + assistant；错误时不写半截 assistant，避免污染历史
  - 普通“新对话”会在首条 user prompt 成功落库后自动回填标题，历史侧栏不再长期显示占位文案
  - 当用户通过 `/api/tools/plan/commit` 采纳 proposal 后，系统会同步更新该会话内匹配 assistant 消息里的 `suggestion.status=committed`，避免后续上下文仍把旧 proposal 视为 pending

- `backend/agent/prompt_templates.py`
  - 定义稳定 system prompt，包含健身教练身份、安全边界、非医疗诊断声明和计划写回必须用户确认的约束
  - 稳定前缀不包含时间戳、随机 id 或实时状态，便于后续 DeepSeek Context Caching 命中

- `backend/agent/context_manager.py`
  - 定义 `PromptAssembler` 与 `TokenBudgetConfig`
  - 按稳定 system prompt、当前用户状态、安全记忆、相关记忆、知识、会话摘要、最近消息、当前输入的顺序组装上下文
  - 使用保守 token 估算和回复预留预算，超预算时优先裁剪低优先级历史，并输出 debug metadata
  - `SummaryCompressor` 负责长对话摘要压缩，`StateReinjector` 负责压缩后回注当前 profile、weeklyPlan、today log、pending proposal 与工具 schema 版本

- `backend/agent/chat_session.py`
  - 定义 `build_agent_request()` 后端编排入口
  - 从 SQLite 读取 `profile / weekly_plan / daily_log / memory / knowledge / summary / recent_messages`
  - 返回 Agent messages、模型配置和上下文调试信息，并通过 `run_tool_calling_chat()` 执行工具调用循环
  - 最近消息回放不会只保留纯文本；若 assistant 消息带有结构化 proposal/suggestion，系统会把 `proposalId / status / day / summary` 追加进回放文本，保证重复修改计划或切模型续聊时，模型能看到 proposal 的真实处理状态
  - 同时承载共享 provider runtime 接线：把运行时 provider 配置映射成实际聊天 client，并在工具循环里按 wire 选择 provider wrapper
  - `DeepSeekClient` 现在只作为短期 fallback 保留：仅在 provider runtime 缺失、无有效凭据或尚未初始化时兜底，避免主链路继续绑定旧实现
  - 工具循环现在会按 client/wire 类型选择 provider wrapper：legacy DeepSeek fallback 与 OpenAI-compatible `chat_completions` 统一走 `_ChatCompletionsToolLoopProvider`，OpenAI-compatible `responses` 走 `_OpenAIResponsesToolLoopProvider`，Gemini-native 走 `_GeminiToolLoopProvider`
  - OpenAI-compatible 运行时的网络与 SSE 错误文案会统一使用 provider label，并在异常细节缺失时回退到异常类型名，避免中转站偶发超时被误显示成 DeepSeek 故障或只剩空白提示

- `backend/agent/usage_ledger.py`
  - 负责规范化 DeepSeek `usage` 字段并写入 `UsageRecord`
  - 汇总会话级 prompt/completion/total token 与 prompt cache hit/miss，用于评估稳定 prompt 前缀是否有效

- `backend/agent/memory.py`
  - 负责长期 memory 候选提取、确认后晋升、关键词检索和安全记忆优先排序
  - 区分用户长期事实与单日临时状态，避免把“今天很累”这类一次性日志污染长期记忆

- `backend/agent/tool_calling.py`
  - 负责本地工具注册、参数 schema 生成和执行前的 Pydantic 二次校验
  - 当前开放健身闭环工具：读取档案、周计划、今日日志、轻量指标、搜索 memory、读取上传文件摘要，以及 `propose_plan_change / propose_day_plan_replace`
  - provider-specific 的 tools schema 转换已开始从这里抽离，交给各 provider adapter 处理

- `backend/agent/tool_loop.py`
  - 负责协议无关的工具调用编排：执行本地工具、控制轮次、记录 `ToolCallLog`、收集 proposal，并委托 provider 处理 schema 与 follow-up message 格式
  - 当前 DeepSeek、OpenAI-compatible `chat_completions`、OpenAI-compatible `responses` 与 Gemini-native 都对接到这套统一回环；proposal 工具逻辑不再区分前台聊天和后台任务

- `backend/api/memory.py`
  - 提供长期记忆查询、候选确认和候选忽略接口，供后续前端 memory 面板接入

- `backend/api/files.py`
  - 提供上传文件的创建、列表、metadata 读取和删除接口
  - 上传成功后保存到 `backend/data/uploads`，写入 `UploadedFile`；可解析文本会同步写入 `KnowledgeItem(kind="uploaded_file")`
  - 解析失败使用 `parser_status="failed"` 和 `parser_error` 表达，不让文件问题变成聊天链路 500

- `backend/files/uploader.py` 与 `backend/files/parsers/*`
  - 负责文件名净化、大小/扩展名限制、sha256 去重、本地缓存路径和轻量摘要生成
  - Markdown/TXT、DOCX、Excel 和图片统一输出 `{kind,title,summary,preview,text}`；图片摘要不内嵌完整 base64

- `backend/api/models.py`
  - 提供 `/api/models`，直接读取 `ProviderRuntimeCache` 当前启用模型集合
  - 返回值同时包含 `defaultModel / defaultModelRef / models[] / thinking`；其中 `thinking` 仍是给旧版前端保留的兼容字段

- `backend/model_config/runtime.py`
  - 负责模型配置运行时缓存、`default_model_ref` 暴露、`modelRef` 解析、启用模型列表生成与配置热刷新入口
  - 当前对外返回 provider 副本，避免后续路由或适配层误改共享缓存内部状态
  - OpenAI-compatible provider 的 `wireApi` 与 `apiPathMode` 会随脱敏配置和运行时视图一并暴露，确保设置页回显与运行时解析使用同一份结构

- `backend/api/model_config.py`
  - 提供 `GET /api/model-config`、`PUT /api/model-config`、`POST /api/model-config/providers/test` 与 `POST /api/model-config/providers/discover-models`
  - 读取时返回脱敏后的 provider 配置；保存时写回 JSON 后立刻调用 runtime refresh，确保设置页改动无需重启服务
  - provider 测试连接与模型发现统一通过适配层转发到 OpenAI-compatible / Gemini-native 两套协议
  - 对 OpenAI-compatible 请求体会额外透传 `wireApi` / `apiPathMode`，但仍兼容未声明这两个参数的旧适配器签名

- `backend/providers/base.py` 与 `backend/providers/openai_compatible.py`
  - 定义 Provider 适配层的最小公共接口和统一错误类型
  - OpenAI-compatible provider 现在显式支持 `wireApi(chat_completions / responses)` 与 `apiPathMode(raw_root / append_v1)` 两个运行时参数
  - `/models`、`/chat/completions`、`/responses` 的 endpoint 都通过统一 builder 构造，`append_v1` 会自动避免 `.../v1/v1/...` 双拼接；DeepSeek 配到 `/v1` 根路径时也复用这套规则
  - 模型测试与发现现在会对 OpenAI-compatible `/models` 的瞬时 `502/503/504` 与网络异常做轻量重试，减少代理抖动导致的假失败
  - 工具循环会按 wire 差异分别处理 `assistant.tool_calls -> tool` 与 `function_call -> function_call_output` 两条 follow-up 链路
  - `responses` 路径下的 tools schema 必须使用扁平 `{"type":"function","name":...,"description":...,"parameters":...}` 结构，不能复用 `chat_completions` 的嵌套 `function` 格式；否则真实 OpenAI-compatible 中转站会在首轮工具调用直接返回 HTTP 400
  - 运行时会优先尝试 `responses`，但遇到 SSE 上游抖动、`502/503/504` 或某些中转站对 `function_call_output` HTTP 续传的限制时，会把当前轮次自动回退成 `chat_completions`，并把 mixed responses follow-up 消息回转为标准 `assistant(tool_calls) + tool` 结构；流式回复会直接切到真正的 `chat_completions` 流式请求，避免为了判断 fallback 先多打一轮非流式请求

- `backend/providers/openai_compatible_client.py`
  - 抽出了真正的 OpenAI-compatible HTTP client，统一处理 base URL 规范化、headers、超时、错误映射和 endpoint builder
  - provider test/discover 以及后续 OpenAI-compatible 直连聊天都复用这一层，避免把 DeepSeek 风格 URL 规则写死在 provider 适配层

- `backend/providers/gemini_native.py`
  - 负责 Gemini 原生 `/models` 发现、`functionDeclarations` schema 生成、函数调用归一化以及 tool result 回灌消息格式转换
  - 与 OpenAI-compatible provider 共用同一套本地工具描述，但保留 Gemini 原生消息结构
  - 会把 Pydantic/OpenAI 风格 schema 清洗为 Gemini 可接受的参数结构，移除 `$defs / $ref / additionalProperties` 等 Gemini REST 会拒绝的字段

- `backend/providers/gemini_client.py`
  - 负责把 Gemini `generateContent` 包装成当前聊天主链路可复用的最小客户端
  - 当前用于 `/api/chat/reply`、`/api/chat/stream` 和后台任务的 Gemini 文本请求，先解决“Gemini 模型名误发到 DeepSeek”这一运行时路由问题
  - 现在额外暴露原始 `generateContent` 响应，供 Gemini-native 工具循环直接处理 `functionCall / functionResponse`
  - 当前会把统一工具回环传入的 `tool_choice` 映射为 Gemini 官方 `toolConfig.functionCallingConfig`，避免 Gemini 路径只能“看模型心情”决定是否发起函数调用

- `backend/api/drafts.py`
  - 提供会话级 Coach 草稿读取和 upsert
  - 只保存草稿文本、模型、thinking 和附件 id，不保存浏览器 File 对象或本机绝对路径

- `backend/api/metrics.py` 与 `backend/metrics/daily_metrics.py`
  - 提供 Python 版每日复杂指标摘要，读取后端 profile / weeklyPlan / dailyLog 后统一计算
  - 当前与前端 `buildDailyMetricsSummary()` 固定样本对齐，后续可作为展示、prompt 和工具调用的统一口径源

- `backend/api/tools.py`
  - 提供 `/api/tools/plan/propose` 与 `/api/tools/plan/commit`
  - proposal 只生成建议卡，不写库；commit 必须来自用户确认路径，并复用计划采纳校验
  - 当前 proposal 分为 `field_changes` 与 `day_plan_replace` 两类，统一走 `/api/tools/plan/commit` 写回

- `backend/api/weekly_plan.py`
  - 继续提供周计划 CRUD
  - `POST /api/weekly-plan/adopt` 当前已明确降级为 legacy 兼容壳，仅用于历史 suggestion 或旧联调入口

- `backend/agent/adopt_plan.py`
  - 负责 AI 计划建议的后端采纳校验、proposal store、动作字段更新、整日计划替换和动作结构归一化
  - `field_changes` 继续只支持 `action: "update"`；`day_plan_replace` 支持直接整日覆盖目标日期计划
  - 更新后保留 `template / instance` 与扁平兼容字段，确保后续 AI 建议仍能按字段定位
  - 单日计划归一化已兼容 Gemini 常见字段形态，如 `exerciseName / time / unit / sets / reps`，会把动作名补齐到 `name`，并把时长信息落到 `repsText/note` 这类现有结构中，保证 proposal 卡与训练计划页都能正常展示
  - 当模型错误地把“空训练日新增动作/新增整日安排”生成为 `field_changes(add/replace)` 时，会在 proposal 构建阶段自动升级成 `day_plan_replace`，降低 Gemini 选错工具后整张卡片失效的概率

- `backend/agent/background_worker.py`
  - 负责离页后台思考的进程内任务表和 `asyncio.create_task` 调度
  - 后台任务使用独立 SQLAlchemy session factory 写库，不复用请求生命周期内的 DB session
  - 当请求未显式传模型时，会优先使用运行时默认 `modelRef`，再解析到真实远端模型 ID，保证前台聊天与后台思考使用同一套模型来源
  - 后台任务与前台聊天复用同一套 provider-bound client 选择与工具回环，避免“前台可聊但后台 proposal 失效”的漂移
  - 成功任务解析 `suggestion` 后写入本轮 user + assistant；若 suggestion 是待确认 proposal，也会复用主聊天链路的正文语义收口，避免后台回复把未提交 proposal 说成“已采纳”
  - 失败任务只记录 provider-aware 友好状态，不写脏 assistant

- `backend/db/models.py`
  - 定义 `Profile / WeeklyPlanDay / DailyLog / ChatSession / ChatMessage`
  - Phase 3 新增 `ChatSessionSummary / MemoryItem / KnowledgeItem / ToolCallLog / UsageRecord`
  - Phase 4 新增 `UploadedFile / CoachDraft`，分别承载本地文件缓存 metadata 与 AI 教练草稿
  - `WeeklyPlanDay.exercises` 以 JSON 保存动作数组，计划采纳成功后只更新目标日动作列表
  - `ChatMessage.suggestion` 以 JSON 可空列保存结构化建议，供前端渲染采纳卡片
  - `ChatMessage.attachments` 以 JSON 保存用户消息附件快照，保证刷新、切换历史会话和源文件删除后仍可回显最小附件信息

- `src/api/coachBackend.js`
  - 负责调用 `/api/chat/stream`、`/api/chat/reply` 和后台任务提交 / 查询接口
  - 发送 Phase 3 Agent 请求契约 `{sessionId, userInput, model, thinking, files}`，并保留 Phase 2 函数名包装
  - 解析后端 SSE 帧并把 `delta / suggestion / proposal / tool_status / done / error` 映射给页面
  - 将后端 `error` 事件、HTTP 错误和断流统一成可展示异常

- `src/api/deepseek.js`
  - 当前只保留为历史兼容壳，内部转发到 `coachBackend.js`
  - 文档与新代码不再把它视为 AI 教练主入口

- `src/tabs/CoachTab.jsx`
  - 负责 AI 教练页状态协调
  - 继续管理 `sessions / activeSessionId / draft / errorMessage / isSending / streamingText`
  - 负责发送、流式回退、建议采纳 / 忽略、新建对话和真实会话选中态
  - 现在同时协调模型运行时列表、模型设置弹窗、配置保存后的模型热刷新，以及会话草稿里的 `modelRef`
  - 首次进入会加载后端会话列表，优先恢复 `fitloop:coach-active-session-id`，否则打开最近会话
  - 新建对话会调用 `POST /api/chat/sessions` 创建真实后端会话，旧会话不会被清空
  - 切换会话会调用 `GET /api/chat/sessions/{id}/messages` 和 `GET /api/chat/sessions/{id}/draft` 恢复消息与草稿
  - assistant 消息会携带原始 `suggestion`，用于切页或组件重挂载后恢复采纳卡片；忽略或采纳成功后会把对应消息的 `suggestion` 清空以持久隐藏
  - 采纳动作按 `proposalId` 或旧版 `day + changes` 做 in-flight 去重，避免同一卡片快速重复点击触发二次提交
  - 页面隐藏或离开时中止前台请求并提交后台思考兜底；只有后台任务成功拿到 `task_id` 后才抑制前台错误
  - 页面恢复可见且后台任务仍处于 `pending/running` 时，若源 user 消息仍存在，则恢复消息区“正在整理上下文”等待态
  - 页面恢复可见时查询 task，并在源 user 消息仍存在时把成功结果补进当前消息列表；若当前对话已变化则只提示，不污染新对话
  - 继续复用 `requestCoachReply()` / `requestCoachReplyStream()` 与 `appendChatMessages()`；proposal 采纳统一通过 `backendClient.commitCoachSuggestion()` 写回计划，优先走 `/api/tools/plan/commit`，旧 suggestion 仅在缺少 `proposalId` 时兼容回退 `/api/weekly-plan/adopt`
  - proposal commit 后通过 `mergeCommittedWeeklyPlan()` 只覆盖后端返回的 7 天计划，保留前端顶层 `weekMeta` 等本地元数据
  - 发送带附件的问题时会先从 `attachedFiles` 生成消息级附件快照，写入本地 `userMessage.attachments`；历史恢复时对旧消息补 `attachments: []` 兼容

- `src/components/coach/CoachLayout.jsx`
  - 负责历史侧栏 + 主聊天区的两列布局
  - 保证消息区是主区域唯一纵向滚动容器

- `src/components/coach/ChatSidebar.jsx`
  - 负责渲染“新建对话”和历史侧栏列表
  - 当前消费 `buildCoachSessionView()` 生成的真实会话展示模型

- `src/components/coach/ChatTopbar.jsx`
  - 负责渲染当前对话标题、模型 badge、新建、导出和模型设置入口
  - 顶部不再承载“上下文”切换

- `src/components/coach/MessageList.jsx`
  - 负责空状态和消息流切换
  - 承担自动滚动与流式回复追底逻辑

- `src/components/coach/MessageAttachmentCard.jsx`
  - 负责渲染用户消息附件卡片
  - 展示文件图标、文件名与类型/大小，不承担预览、下载或删除交互

- `src/components/coach/MarkdownMessage.jsx` 与 `src/utils/markdownMessage.js`
  - 负责 assistant 回复的安全 Markdown 渲染
  - 行级解析标题、列表、加粗、行内代码、代码块、表格和分割线，不使用 `dangerouslySetInnerHTML`
  - 表格单元格继续复用 inline markdown 解析；危险链接协议会降级为文本，避免 assistant 回复把原始 HTML 或脚本注入页面

- `src/components/coach/MessageBubble.jsx`
  - 负责渲染用户消息、AI 消息、流式回复和建议卡挂载位
  - 采纳 / 忽略继续把原始 suggestion 往上回传

- `src/components/coach/ModelSelector.jsx`
  - 负责模型下拉和 thinking 开关/强度控制
  - 只消费后端 `/api/models` 返回的模型能力，不在前端自行推断支持情况
  - 新版会优先读取模型级 `thinking` 能力和强度选项，兼容不同 provider 的默认思考设置

- `src/components/coach/ModelConfigDialog.jsx`
  - 负责模型设置弹窗，承接 provider 列表编辑、默认模型选择和保存动作
  - 当前版本支持在页面内维护多 provider 的基础字段和 selectedModels 列表
  - 保存 openai_compatible provider 时会显式带上 `wireApi` 与 `apiPathMode`

- `src/components/coach/ProviderConfigEditor.jsx` 与 `src/components/coach/ProviderModelPicker.jsx`
  - 把单个 provider 的字段编辑与模型列表维护拆开，避免 `CoachTab` 直接承担大表单逻辑
  - 当 provider.type 为 `openai_compatible` 时，额外展示 `wireApi` 与 `apiPathMode` 两个显式设置项；Gemini-native 不展示这两个字段

- `src/utils/modelConfigView.js`
  - 负责把后端模型运行时返回值与脱敏配置文档映射成前端可直接消费的视图模型
  - 统一生成 `modelRef`、provider 标签、默认模型下拉项与模型级 thinking 能力
  - 对 openai_compatible provider 缺失的 `wireApi/apiPathMode` 做前端默认补值，兼容旧配置文件回显

- `src/components/coach/FileAttachmentTray.jsx`
  - 负责文件选择、上传状态、附件 chip 和删除交互
  - 上传成功后只把 `fileId` 交给聊天请求，避免前端把本地路径或大文件内容塞进 Agent payload

- `src/components/coach/Composer.jsx`
  - 负责底部输入框、自适应高度、Enter 发送、Shift+Enter 换行和错误提示

- `src/components/coach/EmptyState.jsx`
  - 负责欢迎页和四个建议问题入口
  - 点击建议问题后直接把文案写回 `CoachTab` 草稿态

- `src/utils/coachView.js`
  - 负责 AI 教练页视图层纯函数
  - `parseCoachTimestamp()` 会把后端返回的无时区 UTC ISO 字符串补齐为 UTC 语义，再统一交给侧栏时间格式化使用，避免浏览器按本地时间误解析
  - 提供流式文本剥离、真实会话侧栏模型和空状态建议问题模型

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
  - 展示星期标签、日期标签、训练日 / 恢复日模式和动作数量
  - 训练日头部不再渲染 `plan.type` 类型胶囊，避免默认「腿日」污染所有训练日；休息日仍保留「休息」状态提示

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
  -> requestCoachReplyStream({sessionId, userInput, model, thinking, files})
  -> /api/chat/stream
  -> build_agent_request()
      -> PromptAssembler 读取 profile / weeklyPlan / dailyLog / summary / memory / recent messages
      -> SummaryCompressor 必要时压缩长对话并 StateReinjector 回注当前状态
  -> run_tool_calling_chat()
      -> DeepSeek tools 只读读取档案、计划、日志、指标和 memory
      -> `propose_plan_change / propose_day_plan_replace` 生成需确认 proposal
      -> 返回文本与 proposal / suggestion
  -> 渲染文本回复与 AdoptCard
  -> 用户点击采纳
  -> POST /api/tools/plan/commit {proposalId} 或兼容 /api/weekly-plan/adopt {day, changes[]}
  -> 后端校验并写回 WeeklyPlanDay.exercises / 目标日整日计划
  -> App 使用响应 plan 刷新 weeklyPlan，并保留本地 `weekMeta`
  -> 写回 fitloop_weeklyPlan
```

### 5. AI 教练页 UI 流

```text
CoachTab
  -> GET /api/chat/sessions
  -> buildCoachSessionView(sessions)
  -> 用户选中会话或首次恢复 activeSessionId
  -> GET /api/chat/sessions/{id}/messages
  -> GET /api/chat/sessions/{id}/draft
  -> 渲染 ChatSidebar + CoachLayout + MessageList + Composer
  -> 空状态展示欢迎文案、建议问题和底部输入区
  -> 已对话状态展示消息流、建议卡片和底部固定输入区
  -> 发送时优先流式输出，失败回退普通请求
  -> 后端成功回复后写入 chat_message，前端同步刷新当前会话展示缓存
  -> 新建对话时 POST /api/chat/sessions，旧会话继续留在历史侧栏
```

### 6. 后端聊天与 SSE 流

```text
后端聊天存储能力
  -> GET /api/chat/sessions/default
      -> 获取或创建“默认对话”
  -> POST /api/chat/sessions/{id}/messages
      -> 追加 user / assistant / system 消息
      -> 可选保存 suggestion JSON
      -> 同步刷新 ChatSession.updated_at
  -> GET /api/chat/sessions/{id}/messages
      -> 按 created_at / id 正序全量返回，不做 20 条裁剪

后端 AI 代理能力
  -> GET /api/chat/stream?userInput=<text>&session_id=<optional>
      -> build_agent_request()
      -> run_tool_calling_chat()
      -> DeepSeek stream_chat() / request_chat_with_usage()
      -> event: delta
      -> parse_ai_response(full_content)
      -> event: suggestion / proposal / tool_status
      -> 成功后写入 user + assistant
      -> event: done
  -> POST /api/chat/reply
      -> 若请求为 userInput，先 build_agent_request()
      -> 若请求为 messages[]，走 Phase 2 兼容路径
      -> DeepSeek request_chat_with_usage()，必要时执行工具循环
      -> parse_ai_response(content)
      -> 成功后写入 user + assistant
      -> 若 DeepSeek 返回 usage，同事务写入 UsageRecord
  -> GET /api/chat/sessions/{id}/context/debug
      -> summarize_session_usage()
      -> 返回 token budget 与 cache hit/miss 汇总
  -> POST /api/chat/{session_id}/background
      -> BackgroundWorker.submit()
      -> asyncio.create_task()
      -> 独立 DB session 写入 user + assistant
  -> GET /api/chat/background/{task_id}
      -> 返回 pending / running / succeeded / failed / not_found

后端计划采纳能力
  -> POST /api/tools/plan/propose
      -> validate_plan_changes()
      -> build_plan_change_proposal()
      -> 返回 proposal/card，不写 weekly_plan_day
  -> POST /api/tools/plan/commit
      -> 校验 proposal 未过期、未重复提交且来自用户确认路径
      -> commit_validated_plan_change()
      -> 成功时仅写回目标 day
      -> 失败时返回原 plan，数据库不变
  -> POST /api/weekly-plan/adopt
      -> 读取当前 weekly_plan_day
      -> adopt_plan_change() 集中校验 day / changes / action / exerciseName / field / 数值字段 / RPE
      -> 成功时仅写回目标 day
      -> 失败时返回原 plan，数据库不变
```

### 7. Phase 4 文件上传与上下文注入流

```text
FileAttachmentTray
  -> POST /api/files/upload multipart
  -> backend/files/uploader.py 保存 backend/data/uploads/<stored_name>
  -> parsers/* 生成轻量 summary / preview / text
  -> UploadedFile(parser_status, summary, storage_path)
  -> KnowledgeItem(kind="uploaded_file", source_file_id)
  -> CoachTab 发送 requestCoachReplyStream({fileIds})
  -> build_agent_request(file_ids)
  -> PromptAssembler 注入 selected_files 摘要与 fileId
  -> read_uploaded_file_summary 工具按需读取 UploadedFile.summary
```

### 8. Phase 4 模型配置流

```text
Settings / backend/.env
  -> BACKEND_HOST / BACKEND_PORT
      -> backend/run_dev_server.py 启动本地 uvicorn
  -> MODEL_PROVIDER_CONFIG_PATH
  -> HTTP_PROXY / HTTPS_PROXY / ALL_PROXY / NO_PROXY
      -> backend/config.py 同步回进程环境，供 httpx 访问 Gemini 等海外模型时复用
  -> backend/model_config/service.py
      -> 优先读取 backend/config/model_providers.json
      -> 缺失时按 deepseek_* 旧字段 bootstrap 首份 JSON
      -> 保存时保留真实 apiKey，但返回脱敏 apiKeyPreview
CoachTab
  -> backendClient.getModels()
  -> GET /api/models
      -> DeepSeekClient.list_models()
      -> 按 MODEL_ALLOWLIST 过滤
      -> 失败时返回 fallback 白名单和 warning
  -> ModelSelector 更新 selectedModel / thinking
  -> 打开 ModelConfigDialog
      -> GET /api/model-config
      -> buildProviderConfigView() 把 openai_compatible 缺失的 `wireApi/apiPathMode` 归一成 `chat_completions/raw_root`
      -> ProviderConfigEditor 允许显式编辑 `wireApi/apiPathMode`
      -> POST /api/model-config/providers/test` / `discover-models` 透传新字段
      -> PUT /api/model-config` 保存后刷新 runtime
  -> coachBackend 发送到 /api/chat/stream 或 /api/chat/reply
```

### 9. Phase 4 草稿流

```text
CoachTab
  -> GET /api/chat/sessions/{id}/draft
  -> 恢复 draft / selectedModel / thinking / attachedFileIds
  -> 输入或配置变化 debounce 500ms
  -> PUT /api/chat/sessions/{id}/draft
  -> CoachDraft 按 session_id upsert
  -> 发送成功后清空 content 与 attachedFileIds，保留模型配置
```

### 10. Phase 4 指标服务流

```text
GET /api/metrics/daily-summary?date=YYYY-MM-DD
  -> 读取 Profile / WeeklyPlanDay / DailyLog
  -> backend.metrics.daily_metrics.build_daily_metrics_summary()
  -> 返回 snake_case 指标
  -> 前端 backendClient.getDailyMetricsSummary() 做 adapter
```

错误边界：SSE 中任意 DeepSeek 密钥缺失、上游错误或断流都会转成 `event: error`；后端不会写入半截 assistant。前端收到流式错误后会尝试 `/api/chat/reply` 非流式回退。工具循环超过 4 轮、工具参数非法、proposal 重复提交或过期，都会返回可解释错误并保留原计划。
后台任务失败或返回空内容时返回 `failed` 与友好 message，不写入 assistant；进程重启后内存任务表清空，旧 task_id 会返回 `not_found`。
计划采纳仅支持显式 `action: "update"`；`pct / kg / sets / reps / rpe` 会做安全数字转换并拒绝 `NaN / Infinity` 等非有限数值，避免“采纳成功但计划未变”或脏值写入。
Phase 4 文件上传中，空文件返回 422、不支持扩展名返回 415、超过大小限制返回 413；解析失败不会删除记录，也不会阻断普通聊天。`/api/models` 上游失败仍返回 200 fallback，draft 保存遇到不存在的附件 id 返回 422。

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

当前 AI 教练页仍使用该 key 保存页面展示状态；V2.3 Phase 2 Task 9 已将发送请求切到后端 chat/SSE，成功回复会同步写入后端 chat 表。

主要持久化：

- `role`
- `content`
- `suggestion`：可选，保存 AI 结构化计划建议，用于本地消息列表恢复采纳卡片

用户点击“忽略”或采纳成功后，前端会把对应消息的 `suggestion` 清空，让已处理卡片在切页、组件重挂载后继续保持隐藏。

AI 教练页的消息展示补充约束：

- `message.suggestion`：原始领域建议对象，供后端 `/api/weekly-plan/adopt` 等业务链路消费
- `message.suggestionCard`：由 `buildAdoptCardModel()` 派生的展示模型，只负责渲染采纳卡片
- `message.suggestion.kind === "day_plan_replace"` 时，卡片会渲染为“单日训练计划预览卡”，展示训练类型与完整动作列表
- 采纳 / 忽略回调必须继续传递 `message.suggestion`，不能把 `suggestionCard` 冒充为领域 suggestion
- 采纳卡片展示状态以 `message.suggestion` 为准；本地 `messageMeta` 只承担当前渲染周期的辅助隐藏状态

### `fitloop:coach-background-task`

保存离页后台思考任务的最小查询信息：

```json
{
  "taskId": "uuid-like-task-id",
  "sessionId": 1,
  "sourceUserIndex": 3,
  "userContent": "离页前发送的用户问题",
  "createdAt": "2026-05-31T00:00:00.000Z"
}
```

页面恢复可见时会调用 `GET /api/chat/background/{task_id}` 查询；成功后优先校验 `sourceUserIndex` 指向的当前消息是否仍是同一条 user 内容，匹配时补 assistant 文本并清理该 key，不匹配时提示用户当前对话已变化并清理该 key。旧格式记录缺少 `sourceUserIndex` 时仍按 `userContent` 存在性兜底。

### 后端 `chat_session / chat_message`

Task 8 新增、Task 9 接入 AI 代理落库的后端聊天表：

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
- 流式回复只在完整成功后落库，避免 delta 阶段写入半截脏消息

### Phase 3 Agent 编排表

Phase 3 Task 13 新增以下表，为后续上下文压缩、长期记忆、工具调用和成本观测打底：

- `chat_session_summary`：保存长对话摘要、覆盖消息范围和 token 估算
- `memory_item`：保存用户长期事实、偏好、目标、约束、器械条件和安全限制
- `knowledge_item`：保存外部资料、上传文件或训练知识片段，与用户 memory 分离
- `tool_call_log`：记录工具名、参数、瘦身结果、状态和错误信息
- `usage_record`：记录 DeepSeek token 用量和 prompt cache hit/miss 字段

### Phase 4 文件与草稿表

Phase 4 新增：

- `uploaded_file`：保存本地上传文件 metadata、相对缓存路径、sha256、解析状态、解析错误和摘要 JSON。它是本地缓存资料，不等同长期 memory。
- `coach_draft`：按 `session_id` 唯一保存 AI 教练输入草稿、模型、thinking 配置和附件 id 列表。
- `chat_message.attachments`：保存消息级附件快照，字段为 `fileId / originalName / mimeType / extension / sizeBytes`。它只负责聊天记录回显，不负责再次打开原文件。

可解析文本上传会额外生成 `knowledge_item(kind="uploaded_file")`，供 Agent 上下文检索；完整文件内容仍保留在本地缓存和 `UploadedFile.summary` 中，进入 prompt 前只注入裁剪摘要。

### `fitloop_storageVersion`

用于标记默认数据迁移版本，避免旧演示数据反复覆盖真实数据。

## AI 调用链路

```text
CoachTab
  -> Phase 3 新契约只传 sessionId + userInput + model/thinking + files
  -> src/api/coachBackend.js
     -> 统一通过 import.meta.env.VITE_API_BASE_URL 解析 API 根地址
  -> GET /api/chat/stream 或 POST /api/chat/reply
  -> build_agent_request()
      -> PromptAssembler
      -> 读取 profile / weeklyPlan / dailyLog / memory / summary / recent messages
      -> SummaryCompressor / StateReinjector
  -> run_tool_calling_chat()
      -> ToolRegistry 执行只读工具
      -> propose_plan_change / propose_day_plan_replace 生成建议卡，不写库
  -> DeepSeekClient.stream_chat() / request_chat_with_usage()
  -> parse_ai_response(content)
  -> 保存 ChatMessage(user + assistant)
  -> visibility hidden / pagehide 时可补交 POST /api/chat/{session_id}/background
      -> BackgroundWorker 对 request_chat_with_usage 客户端复用 run_tool_calling_chat()
      -> proposal or parsed suggestion 写入 ChatMessage.suggestion 与 task.result.suggestion
  -> 回页 GET /api/chat/background/{task_id}
  -> fallback: POST /api/chat/reply
  -> buildAdoptCardModel()
  -> 用户确认后 POST /api/tools/plan/commit 或兼容 POST /api/weekly-plan/adopt
```

关键设计点：

- 每次发送前都重新读取最新上下文
- 前端普通 CRUD、AI 教练聊天和 localStorage 迁移入口都统一优先读取根目录 `.env` 中的 `VITE_API_BASE_URL`，仅在未配置时才回退到本地 `http://127.0.0.1:8000/api`
- DeepSeek API Key 只在后端 `.env` 中读取，前端 bundle 不再包含 `VITE_DEEPSEEK_API_KEY` 或 Authorization 直连逻辑
- AI 回复解析与训练计划写回分离，保留用户最终确认权；只有点击采纳卡片才调用后端写回接口
- 采纳接口失败时返回原始 plan 并不提交事务；成功时返回完整 plan，前端用该响应刷新页面状态
- 单日训练计划卡与字段 patch 卡共享同一 proposal store 和 commit 入口，避免前后端出现两套确认协议
- DeepSeek Context Caching 依赖稳定前缀，`prompt_templates.py` 与 tools schema 不放动态时间戳；真实 hit/miss 由 `UsageRecord` 记录
- memory 保存用户长期事实，knowledge 保存外部资料或上传文件知识，两者不会混写；单日状态不晋升长期 memory
- 上传文件只通过 `fileIds` 和摘要进入 Agent，不把本机路径或完整大文件塞进请求
- 模型与 thinking 配置由后端 `/api/models` 收口，前端仅选择后端声明的可用项
- 聊天、草稿和后台任务共享 `modelRef -> ProviderRuntimeCache -> provider-bound client/runtime -> remote_model_id` 解析链路，避免前端、SSE 与后台任务各自维护一套默认模型逻辑；保存配置后缓存会立即刷新，因此运行时选路不会要求手动重启服务
- OpenAI-compatible provider 在聊天阶段还会继续细分成两条 wire：`chat_completions` 使用传统 `messages/tool_calls` 消息回环，`responses` 使用 `input/function_call/function_call_output` 回环；两者都通过统一 tool loop 驱动 proposal 工具
- 后台任务提交由 `backgroundTaskStartedRef` 去重，窗口 focus 回来后主动轮询，避免 Alt+Tab 或应用内 tab 切换时用户消息看起来丢失
- 后台 pending/running 态只负责渲染消息区“思考中”占位，不再复用为输入框禁用条件，避免 proposal 采纳后出现“卡在思考中且无法继续提问”的假死体验
- Today 页复杂指标面板与 prompt 注入共用 `buildDailyMetricsSummary()`，避免展示层和 AI 上下文口径漂移
- AI 教练页历史侧栏使用后端真实 session id；`buildCoachHistoryView()` 只作为旧测试与兼容工具保留，不再驱动生产侧栏

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
  - 训练日仅展示动作数量和训练预览文案，不把默认训练类型渲染为头部胶囊，训练类型编辑仍由 `PlanDayTypeSection` 承担。
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
