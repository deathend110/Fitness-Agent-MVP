# RepMind MVP — Python 全量后端化重构设计

> 文档类型：分析 + 设计合一
> 生成时间：2026-05-31
> 基准版本：**V2.1**（基线提交 `f33a3f3`，纯前端 + localStorage）
> 分析范围：当前全部源码（`src/`）、`ARCHITECTURE.md` / `README.md`、修改意见记录 V2.5 与 V3
> 决策依据：用户已确认「分析+设计合一」「全量后端化」「新写一份取代旧报告」
> 本文取代已删除的 `docs/RepMind_Python重构分析报告.md`（git HEAD 中仍可追溯）

---

## 一、精简分析过程

**读了什么**：通读 `src/api/deepseek.js`、`src/utils` 下 AI/存储/指标相关模块（`coachChat / coachView / coachGuard / aiResponse / prompt / promptSections / promptMetricsSection / dailyMetrics / chatHistory / storage / adoptPlan`）、`src/tabs/CoachTab.jsx`，并交叉核对 `ARCHITECTURE.md` 与 V2.5/V3 需求文档，最后用 `git log` 锚定真实版本为 V2.1。

**判定准则**：一个模块是否"必须用 Python 重构"，按下面六条判断——满足①~⑤任一即应上后端，只满足⑥才留前端。

| 准则 | 含义 | 典型命中 |
|---|---|---|
| ① 需要后台 / 长任务 | 离开页面仍要继续运行 | 后台思考、长对话推理 |
| ② 需要密钥安全 | 不能把 API Key 暴露给浏览器 | DeepSeek 调用 |
| ③ 需要服务端状态 | 多轮工具调用、会话状态机 | Function Calling、上下文磁盘缓存 |
| ④ 需要超出 localStorage 的存储与检索 | 全量历史、跨会话检索 | 全量聊天记录、知识库 |
| ⑤ 需要 Python 生态库 | 浏览器无对应能力 | Excel/DOCX 解析、图像处理 |
| ⑥ 纯展示 / 即时交互（→留前端） | 无副作用、无持久化 | UI 渲染、表单草稿、格式化 |

**结论先行**：V2.5/V3 的新需求绝大多数命中①~⑤，纯前端架构无法承载，需要引入**本地 Python 后端**并把数据层全量迁移到 SQLite；前端退化为 API 客户端，仅保留 UI 与即时交互。

### 外部参考与取舍（Phase 3 Agent 设计补充）

本次 Phase 3 设计参考两类材料，但不直接照搬：

- **Claude Code 源码分析**（`https://github.com/liuup/claude-code-analysis` / DeepWiki 解析）：取其"上下文治理"思想，而不是取其 coding-agent 领域实现。可借鉴点包括：短期 transcript、会话压缩摘要、长期 memory 分层；压缩前预留输出空间；压缩失败熔断；压缩后回注当前工作状态、工具 schema 与关键附件；工具结果脱水，避免把可重取的大块内容塞回上下文。
- **DeepSeek 官方 API 文档**（`https://api-docs.deepseek.com/`）：具体实现必须按 DeepSeek 的接口语义来做。DeepSeek `/chat/completions` 是无状态接口，每轮都要由后端拼好 `messages`；Context Caching 默认启用，但命中依赖稳定前缀；Tool Calls 需要后端执行函数并把 `tool` 结果再交给模型；Thinking Mode 需要正确处理 `reasoning_content`，尤其是带工具调用时后续轮次必须保留相关 reasoning 字段。
- **领域取舍**：RepMind 是高度特化的健身助手，不是 coding agent。Phase 3 不追求通用 shell/文件编辑/MCP 代理能力，而是优先做"训练计划、恢复、饮食、日志、文件解析、记忆检索"这些健身闭环工具；所有写计划动作仍保留用户确认闸门，避免 AI 自动改坏训练安排。

---

## 二、当前现状画像（V2.1，代码核实）

| 维度 | 现状 | 支撑文件（已读码核实） |
|---|---|---|
| 前端 | React 19 + Vite + Tailwind CSS | `package.json` |
| 数据持久化 | 浏览器 `localStorage`，仅 JSON 导入/导出备份 | `utils/storage.js`、`utils/dataTransfer.js` |
| AI 接入 | 浏览器**直连** DeepSeek `/chat/completions` | `api/deepseek.js` |
| API Key | `VITE_DEEPSEEK_API_KEY` 经 `import.meta.env` **打包进前端 bundle** | `api/deepseek.js` |
| 模型 | **硬编码** `deepseek-v4-flash`，顶栏写死 `DeepSeek v4` | `api/deepseek.js`、`tabs/CoachTab.jsx` |
| Agent 能力 | 仅单轮 system-prompt 注入 + 流式输出，无工具调用 | `utils/coachChat.js`、`utils/prompt.js` |
| 后台思考 | 不支持，流式靠组件挂载，**离页即断** | `tabs/CoachTab.jsx` |
| 聊天记录 | **硬裁剪到最近 20 条**，仅存 `{role, content}` | `utils/chatHistory.js`（`CHAT_HISTORY_LIMIT=20`） |
| 多会话 | **假多会话**：从单条 `chatHistory` 取最近 6 条用户消息派生侧栏 | `utils/coachView.js`（`buildCoachHistoryView`） |
| 知识库 | 无 | — |
| 文件上传 | 无 | — |
| MD 渲染 | 无，AI 回复按纯文本展示 | `components/coach/MessageBubble.jsx` |
| 草稿持久化 | 无，`draft` 是组件 state，**离页丢失** | `tabs/CoachTab.jsx` |
| 计划写回 | 已实现：`---JSON---` 解析 + 采纳卡片 + 校验写回 | `utils/aiResponse.js`、`utils/adoptPlan.js` |
| 复杂指标 | 前端即时计算，单一口径 `buildDailyMetricsSummary()` | `utils/dailyMetrics.js` |
| 周期计划 | 无"周期"概念，仅手动维护的静态周计划 | `utils/weeklyPlan.js` |

---

## 三、需求 → 能力差距矩阵（为什么必须重构）

> 来源：V2.5 `#0/#1/#2/#3` 与 V3。"前端可否实现"列是核心论证。

### V2.5 #0 — AI 对话框功能完善

| 需求 | 当前 | 前端能否独立实现 | 归属 |
|---|---|---|---|
| Enter 发送 / Shift+Enter 换行 | 已实现 | 可 | 前端（已完成） |
| 未发送 prompt 草稿记忆（切页保留） | 无 | 可（localStorage），但全量后端化后归后端 | 前端→后端持久化 |
| **后台思考（离页继续）** | 离页即断 | **不能**（浏览器挂起请求） | **后端 P0** |
| **模型选择（列出可用模型）** | 硬编码 | 不能（需服务端查模型 + 收口密钥） | **后端 P1** + 前端下拉 |
| MD 渲染器 | 裸文本 | 可（前端库） | 前端 |
| **文件上传解析（图片/excel/md/docx）** | 无 | **不能**（需 pandas/python-docx 等） | **后端 P1** + 前端入口 |
| 对话维持最新一条（刷新不回首条） | 切换/刷新回首条 | 可（前端滚动/状态） | 前端 |
| **聊天记录（每个对话框独立、可新建）** | 假多会话 | **不能**（需真实会话存储） | **后端 P0/P1** |
| **跨对话记忆同步 / 知识库建模** | 无 | **不能**（需存储 + 检索 + 注入） | **后端 P0/P2** |
| 模型操控训练计划（等宽卡片+接受/取消） | 已实现单轮 JSON 采纳 | 升级为工具调用需服务端 | 后端 P3 + 前端卡片（部分已有） |

### V2.5 #1 — DeepSeek API 优化

| 需求 | 前端能否实现 | 归属 |
|---|---|---|
| 工具函数调用（Function Calling 完整链路） | 不能（tool_use→tool_result→再推理需服务端状态） | 后端 P0 |
| 多轮对话 / 上下文拼接 | 勉强（但与后台思考、全量记录冲突） | 后端 P0 |
| **上下文磁盘缓存** | 不能（浏览器无磁盘缓存能力） | 后端 P1 |
| 思考模式 / 思考强度设置 | 需服务端按模型参数透传 | 后端 P1 |

### V2.5 #2 — Agent 功能优化

| 需求 | 前端能否实现 | 归属 |
|---|---|---|
| 上下文压缩 / 管理 | 不能（需 token 计数 + 摘要调用 + 状态） | 后端 P1 |
| 聊天记录全量保存（20 条远不够） | localStorage 上限受限，不能长期 | 后端 P0 |
| token 消耗优化（参考 Claude Code/OpenCode） | 不能（需服务端编排） | 后端 P1 |

### V2.5 #3 — 验证 Agent 修改计划能力

| 需求 | 归属 |
|---|---|
| 验证模型能正确改计划，不行就修 bug | 后端 P3 验收项（复用 `adoptPlanChange` 逻辑） |

### V3 — 周期与预制计划

| 需求 | 前端能否实现 | 归属 |
|---|---|---|
| 周期概念（长度可自拟、上周期→下周期自动递增） | 复杂状态逻辑，宜后端 | 后端 P2（预留） |
| 预制计划库（5x5/疯牛5x5/德州/condito6周/黑又壮/线性周期，按 1RM 覆盖） | 宜后端配置 + 生成 | 后端 P2（预留） |

---

## 四、必须用 Python 重构的部分（按优先级）

### 🔴 P0 — AI Agent 核心层

- **当前文件**：`src/api/deepseek.js`、`src/utils/coachChat.js`、`src/utils/aiResponse.js`、`src/utils/prompt.js`
- **问题**：①浏览器无法后台运行，离页中断；②API Key 打包进前端可被提取；③无法做完整多轮 Tool Calling（需服务端维持 `tool_use → tool_result → 再推理`）；④上下文磁盘缓存浏览器做不到。
- **Python 目标模块**：
  ```
  backend/agent/
    deepseek_client.py     # DeepSeek HTTP 客户端（含流式 SSE、错误码映射，迁移自 deepseek.js）
    chat_session.py        # 多轮对话状态机（会话级）
    tool_calling.py        # Function Calling 编排（计划读写工具，复用 adoptPlanChange 校验）
    context_manager.py     # 上下文窗口管理 + 压缩 + system prompt 构建（迁移 prompt*.js）
    memory.py              # 会话摘要、长期记忆、知识片段检索与 memory 晋升
    usage_ledger.py        # token/cache 使用记录，用于成本与压缩效果评估
    response_parser.py     # ---JSON--- / 结构化建议解析（迁移自 aiResponse.js）
    background_worker.py   # asyncio 任务队列，支持离页继续推理
  ```
- **技术选型**：FastAPI + uvicorn（异步）；流式用 SSE（`text/event-stream`）→ 前端 `EventSource`；后台任务初期 `asyncio.Task` 足够，规模上来再上 Celery。

### 🔴 P0 — 数据持久化层（全量迁移）

- **当前文件**：`src/utils/storage.js`、`src/utils/defaultData.js`、`src/utils/dataTransfer.js`、`src/utils/chatHistory.js`
- **问题**：①`localStorage` ~5MB 上限，全量聊天记录会打满；②`CHAT_HISTORY_LIMIT=20` 硬裁剪，违背"全量保存"；③Python Agent 无法直接读 `localStorage`，前后端数据割裂；④假多会话无法承载真实多对话与知识库。
- **决策**：**全量后端化**——`profile / weeklyPlan / dailyLog / chat` 全部迁到 SQLite，前端退化为 API 客户端。
- **Python 目标模块**：
  ```
  backend/db/
    database.py    # SQLAlchemy async 引擎 + 会话
    models.py      # ORM：Profile / WeeklyPlanDay / DailyLog / ChatSession / ChatMessage / KnowledgeItem / UploadedFile / MetricsCorrection
    migrations/    # Alembic
    seed.py        # 默认空白数据（迁移自 defaultData.js）
  ```
- **技术选型**：SQLAlchemy 2.x（async）+ SQLite + Alembic。

### 🟠 P1 — 上下文管理与 Token 优化

- **当前文件**：`src/utils/chatHistory.js`、`src/utils/coachChat.js`、`src/utils/prompt.js`
- **问题**：当前"上下文管理"仅 `.slice(-20)`；V2.5 要求压缩、长对话与多工具调用下的 token 优化。
- **Python 目标**（`backend/agent/context_manager.py` + `backend/agent/memory.py`）：
  - `PromptAssembler`：按"稳定前缀 → 领域状态 → 检索记忆 → 最近对话 → 当前用户输入"拼装 messages。稳定前缀包括 Agent 身份、安全边界、输出格式、工具 schema 摘要，尽量保持字节级稳定，主动利用 DeepSeek Context Caching。
  - `ContextWindow`：维护模型上下文窗口、回复预留 token、工具调用预留 token 与压缩触发阈值。不要把模型最大上下文全部塞满；默认 70% 预警、85% 自动压缩、95% 进入强制瘦身/拒绝超大附件。
  - `SummaryCompressor`：不是简单截断，而是把早期对话压成结构化 Markdown/JSON 摘要，必须保留训练目标、伤病限制、已采纳/拒绝过的建议、当前周期进度、关键体重/热量趋势、用户偏好和未完成承诺。
  - `StateReinjector`：压缩后回注"当前活跃状态"，对应健身领域包括：当前周计划、今日日志、最近一次 AI 建议卡状态、待确认的计划修改、上传文件摘要、工具 schema 版本。避免摘要把正在处理的计划改动吞掉。
  - `ToolResultSlimmer`：工具结果只保留模型下一步决策所需字段。完整数据仍在 SQLite，可重查；上下文中只放 `tool_result_summary`、关键 diff、`file_id/session_id/date` 等引用，避免 Excel/日志全量反复进入 prompt。
  - `MemoryRetriever`：两步检索，先给模型/规则层一个轻量 memory index（类型、时间、关键词、置信度），再取少量相关详情；不要把全部长期记忆直接注入。
  - `UsageLedger`：记录每次 DeepSeek 返回的 `prompt_tokens / completion_tokens / prompt_cache_hit_tokens / prompt_cache_miss_tokens`，用于观察缓存命中、压缩收益和长对话成本。
- **DeepSeek 适配原则**：
  - DeepSeek 多轮对话由客户端/后端拼接上下文，后端必须成为唯一上下文编排者，前端不再手拼 system prompt。
  - Context Caching 默认启用，因此稳定内容应放在 messages 前部，动态日志、当前问题、工具结果放后部；不要在 system prompt 顶部塞时间戳、随机会话 id 或实时指标。
  - Thinking Mode 作为可配置能力：普通聊天默认 `high`，复杂计划重排/多工具任务可升到 `max`；思考模式下不设置无效的 `temperature/top_p`；带工具调用的轮次必须按 DeepSeek 规则保存并回传必要的 `reasoning_content`。
  - Tool Calls 优先使用 DeepSeek OpenAI 兼容格式；可用 strict JSON schema 时给工具参数加 `strict: true` 与 `additionalProperties: false`，后端仍必须用 Pydantic 二次校验。

### 🟠 P1 — 文件上传与解析

- **当前状态**：完全未实现。
- **需求**：图片（喂视觉）、Excel（训练表格）、DOCX、MD；文件存**软件所在目录**的缓存文件夹（不写 C 盘）。
- **Python 目标**：
  ```
  backend/files/
    uploader.py            # 接收 multipart，存 backend/data/uploads/
    parsers/
      image_parser.py      # Pillow + base64，准备喂 DeepSeek vision
      excel_parser.py      # pandas + openpyxl → 结构化 JSON
      docx_parser.py       # python-docx → markdown 文本
      md_parser.py         # 透传 / markdown 解析
  ```

### 🟠 P1 — 模型选择与调用配置

- **当前文件**：`src/api/deepseek.js`（`DEFAULT_MODEL` 硬编码）。
- **需求（V2.5）**：从接入的 API 列出可用模型，输入框旁可展开选择（参考 Gemini）；并支持思考模式/强度透传。
- **Python 目标**：`backend/api/models.py`（`GET /api/models` 返回白名单/可用模型）+ `backend/config.py`（读 `.env`，管理 Key、base URL、模型白名单、思考参数）。前端只渲染下拉，不再硬编码。

### 🟡 P2 — 复杂指标计算服务

- **当前文件**：`src/utils/dailyMetrics.js`、`src/utils/dailyMetricsPanel.js`、`src/utils/promptMetricsSection.js`、`src/utils/calcBase.js`
- **现状评估**：当前纯前端计算可用，但：①AI 动态修正 TDEE/体脂率（V1 意见）无法持久化；②周期计划引入后复杂度上升，JS 难维护。
- **Python 目标**（`backend/metrics/`）：`bmr.py` / `tdee.py`（含 AI 修正持久化）/ `body_composition.py` / `prompt_metrics.py`（生成 `structured_metrics`）。**保持 `buildDailyMetricsSummary()` 的单一口径语义**，后端展示与 prompt 注入共用同一函数。

### 🟡 P2 — 周期计划引擎 + 预制计划库（V3，预留接口）

- **当前状态**：无。
- **Python 目标**（`backend/plans/`）：`cycle_engine.py`（周期状态机：当前第几周、下周如何递增）/ `preset_library.py`（5x5、疯牛5x5、德州、condito 6周、黑又壮、线性周期等预制 JSON，按 1RM 自动填重）/ `plan_generator.py`（按周期配置生成 weeklyPlan 结构）。

---

## 五、保留在前端（不重写）的部分

| 模块 | 原因 |
|---|---|
| 全部 UI 组件（`PlanDayCard`、`coach/*` 等） | 纯展示，React 胜任，重写零收益 |
| Tailwind / `index.css` 主题 token | 纯前端关注点 |
| 表单草稿即时态（`exerciseForm.js`、`planEditorState.js`） | 即时交互；草稿"切页保留"改为调后端持久化 |
| 纯格式化函数（`calc.js` 的 `formatWeightDisplay` 等） | 无状态无副作用，留前端省 API 往返 |
| 路由 / Tab 切换 | 纯前端导航 |
| MD 渲染、滚动到最新、Enter/Shift+Enter | 纯前端交互（部分已实现，仅需补 MD 渲染与滚动定位） |

**前端唯一结构性改动**：`src/api/` 从"直连 DeepSeek"改为"调用后端 REST + 订阅 SSE"；`src/utils` 中 AI/存储相关逻辑删除或改为薄 API 包装。

---

## 六、目标架构（全量后端化）

```
RepMind/
├── frontend/                 # 原 React 项目（UI 保留，数据源改 API）
│   └── src/
│       ├── api/              # → 调 backend REST + SSE（替换 deepseek.js 直连）
│       ├── components/       # 保留
│       ├── tabs/             # 保留，props 数据来自 API
│       └── utils/            # 保留纯 UI/格式化；删除 AI/存储/裁剪逻辑
│
└── backend/                  # 新增 Python 服务
    ├── main.py               # FastAPI 入口
    ├── config.py             # .env、Key、base URL、模型白名单、思考参数
    ├── db/                   # database / models / migrations / seed
    ├── api/                  # profile / weekly_plan / daily_log / chat(SSE) / models / files
    ├── agent/                # deepseek_client / chat_session / tool_calling / context_manager / response_parser / background_worker
    ├── metrics/              # daily_metrics / prompt_metrics
    ├── files/                # uploader / parsers/*
    ├── plans/                # cycle_engine / preset_library / plan_generator（V3 预留）
    ├── data/                 # repmind.db、uploads/（.gitignore）
    └── requirements.txt
```

**前后端通信**：
- 普通 CRUD → REST（JSON）
- AI 流式 → `GET /api/chat/stream` → Server-Sent Events
- 文件上传 → `POST /api/files/upload` → multipart/form-data
- 本地一键启动 → 根目录加 npm script（`concurrently` 同时起 Vite 与 uvicorn）

---

## 七、后端目录结构（详细）

```
backend/
├── main.py                    # FastAPI app、CORS、路由挂载、启动 background_worker
├── config.py                  # pydantic-settings 读取 .env
├── requirements.txt
├── db/
│   ├── database.py            # async engine + AsyncSession 依赖
│   ├── models.py              # ORM 模型（见第八节）
│   ├── seed.py                # 默认空白档案/周计划（迁移 defaultData.js）
│   └── migrations/            # Alembic 版本脚本
├── api/
│   ├── profile.py             # GET/PUT /api/profile
│   ├── weekly_plan.py         # GET/PUT /api/weekly-plan、采纳接口
│   ├── daily_log.py           # GET /api/daily-log、PUT /api/daily-log/{date}
│   ├── chat.py                # 会话/消息 CRUD + GET /api/chat/stream（SSE）
│   ├── models.py              # GET /api/models
│   └── files.py               # POST /api/files/upload
├── agent/
│   ├── deepseek_client.py
│   ├── chat_session.py
│   ├── tool_calling.py
│   ├── context_manager.py
│   ├── memory.py
│   ├── usage_ledger.py
│   ├── response_parser.py
│   └── background_worker.py
├── metrics/
│   ├── daily_metrics.py
│   └── prompt_metrics.py
├── files/
│   ├── uploader.py
│   └── parsers/{image,excel,docx,md}_parser.py
├── plans/
│   ├── cycle_engine.py
│   ├── preset_library.py
│   └── plan_generator.py
└── data/                      # gitignore：repmind.db + uploads/
```

---

## 八、数据模型设计（SQLite 全量迁移）

把 4 个 localStorage key 映射为 ORM 表，并新增多会话与知识库表。

| 表 | 来源 / 用途 | 关键字段 |
|---|---|---|
| `profile` | `fitloop_profile`（单行/单用户 MVP） | basic(JSON)、oneRM(JSON)、goal、targetWeight、notes |
| `weekly_plan_day` | `fitloop_weeklyPlan` 的每一天 | day_key(Mon..Sun)、type、`exercises`(JSON) |
| `daily_log` | `fitloop_dailyLog` 每日一行 | date(PK)、weight、kcal、protein、sleep、fatigue、steps、trainingDone、trainingNotes、tdee_manual |
| `chat_session` | 新增（真实多会话） | id、title、created_at、updated_at |
| `chat_message` | `fitloop_chatHistory`（去掉 20 条裁剪，全量） | id、session_id(FK)、role、content、created_at、suggestion(JSON,可空) |
| `chat_session_summary` | 新增（长对话压缩结果） | session_id、summary_text、covered_message_id_range、token_estimate、created_at、updated_at |
| `knowledge_item` | 新增（跨对话知识库建模） | id、source_session_id、kind、content/embedding、created_at |
| `memory_item` | 新增（长期用户记忆） | id、kind、content、confidence、source_message_id、last_used_at、created_at |
| `tool_call_log` | 新增（工具调用审计） | id、session_id、tool_name、arguments_json、result_summary、status、created_at |
| `uploaded_file` | 新增（文件上传） | id、session_id、path、mime、parsed_text、created_at |
| `metrics_correction` | 新增（AI 修正 TDEE/体脂持久化） | id、date、field、value、reason、created_at |

**关键迁移细节 — exercise 的 `template + instance + 扁平兼容字段`**：
当前动作对象同时含 `template`（编排）、`instance`（执行层负重/RPE/备注）和一组扁平字段（`pct/kg/sets/reps/rpe/note`，供 `adoptPlanChange` 与采纳链路消费）。为**零风险、无损迁移**，Phase 1 推荐把 `weekly_plan_day.exercises` 整体存为 **JSON 列**，原样保留三层结构；不在初期强行规范化为 `exercise` 行表，避免破坏扁平兼容字段与现有前端契约。待 V3 周期计划需要按动作检索时，再评估抽出独立 `exercise` 表（保留 JSON 影子字段过渡）。

**知识库（V2.5 跨对话记忆）建模建议**：MVP 阶段先用 `knowledge_item` 存结构化要点 + 关键词检索；需要语义检索时再引入向量（sqlite-vec / FAISS）。"所有模型聊天从知识库取信息"在 `context_manager.py` 注入时实现。

**Memory 分层建议（借鉴 Claude Code，但适配健身 Agent）**：

- `chat_message`：完整 transcript，不再裁剪，用于审计和重新压缩。
- `chat_session_summary`：会话内压缩摘要，只服务当前会话续聊，保存覆盖到哪条消息，避免重复压缩。
- `memory_item`：跨会话长期记忆，只保存稳定事实和明确偏好，例如伤病史、训练目标、器械条件、作息限制、饮食禁忌、用户明确喜欢/不喜欢的训练方式。临时情绪、一次性抱怨、单日状态不要晋升为长期记忆。
- `knowledge_item`：外部资料/上传文件/训练模板的知识片段，和用户长期记忆分开，避免"资料内容"被误当成"用户事实"。
- `tool_call_log`：记录模型为什么调用工具、传了什么参数、后端如何裁剪结果。后续排查"AI 为什么改错计划"时比纯聊天日志更有价值。

**Memory 晋升规则**：只有满足"用户明确陈述/多次出现/被采纳计划反复验证"之一的事实才可进入 `memory_item`；影响训练安全的记忆（伤病、疼痛、疾病、极端饮食）需要标记 `kind=safety`，注入优先级高于普通偏好。低置信度记忆进入候选区，前端后续可以做"是否记住这点"的小确认。

---

## 九、API 契约草图

```
# 档案
GET  /api/profile                       -> Profile
PUT  /api/profile            {Profile}  -> Profile

# 周计划
GET  /api/weekly-plan                   -> {Mon..Sun: {type, exercises[]}}
PUT  /api/weekly-plan        {plan}     -> plan
POST /api/weekly-plan/adopt  {day, changes[]} -> {ok, message, plan}   # 复用 adoptPlanChange 校验

# 今日日志
GET  /api/daily-log?from&to             -> {date: log}
PUT  /api/daily-log/{date}   {log}      -> log

# 会话与消息
GET  /api/chat/sessions                 -> [session]
POST /api/chat/sessions      {title?}   -> session
GET  /api/chat/sessions/{id}/messages   -> [message]            # 全量，无 20 条裁剪
GET  /api/chat/stream?session_id&model&input  -> text/event-stream   # SSE 流式回复
POST /api/chat/{session_id}/background   {input}   -> {task_id}  # 后台思考

# Phase 3 上下文、记忆与工具
GET  /api/chat/sessions/{id}/context/debug -> {budget, selected_memories, summaries, token_estimate} # 本地调试用
POST /api/memory/candidates/{id}/confirm   -> memory_item        # 用户确认低置信度长期记忆
GET  /api/memory/items?kind&query          -> [memory_item]
POST /api/tools/plan/propose               -> {proposal_id, card} # 只生成建议卡，不直接写计划
POST /api/tools/plan/commit                -> {ok, message, plan} # 用户确认后写回

# 模型与文件
GET  /api/models                        -> [{id, label, supports_thinking}]
POST /api/files/upload  (multipart)     -> {file_id, parsed_text?}
```

- SSE 事件：`delta`（增量文本）/ `suggestion`（结构化建议）/ `done` / `error`。
- 计划采纳：把 `src/utils/adoptPlan.js` 的校验语义搬到后端，既服务 REST `/adopt`，也作为 `tool_calling.py` 的工具实现，保证"用户确认闸门"不丢。
- Phase 3 工具调用：模型只能调用"提议类"工具生成变更卡片，真正写库必须走用户确认后的 commit 接口。这样既保留 DeepSeek Tool Calls 的自动编排能力，又避免健身计划被模型静默修改。

---

## 十、分阶段迁移路线

> 每阶段交付物 + 验收清单（对齐 AGENTS.md 验证要求：1 条核心成功路径 / 2–3 个边界 / 1 个失败场景）。

### Phase 1 — FastAPI 骨架 + SQLite + 全量 CRUD + 前端切源
- 交付：后端骨架、ORM、Alembic、profile/weekly-plan/daily-log CRUD；前端 `api/` 改调后端；一次性 `localStorage → DB` 导入脚本/页面。
- 验收：成功——填档案/改计划/录日志经后端持久化并刷新不丢；边界——空库新用户、日期边界、并发写；失败——后端未启动时前端给友好降级提示。

### Phase 2 — Python Agent（SSE 流式 + 后台任务 + 密钥后移）
- 交付：`deepseek_client` + `chat/stream` SSE + `background_worker`；API Key 移到后端 `.env`，前端不再持有。
- 验收：成功——发消息流式回复、离页后台继续、回页可见结果；边界——离页/超时/取消；失败——Key 缺失/网络错误友好提示，前端不崩。

### Phase 3 — 上下文管理 + token 优化 + 工具调用改计划
- 交付：
  - `context_manager`：完成 PromptAssembler、ContextWindow、SummaryCompressor、StateReinjector、ToolResultSlimmer、UsageLedger。
  - `memory.py`：完成会话摘要、长期用户记忆、知识片段检索与安全记忆优先注入。
  - `tool_calling.py`：完成计划读取、今日日志读取、指标计算、计划修改提议、采纳提交等健身领域工具；所有写计划工具复用 adopt 校验。
  - `chat_session.py`：把前端 system prompt 构建迁到后端，前端只传用户输入、session_id、模型与可选文件/工具开关。
  - 调试接口：提供本地 `/context/debug`，返回本轮选择了哪些摘要/记忆/工具结果与 token 预算，便于课程报告解释"为什么这次上下文没有超限"。
- 实施顺序：
  1. 先做无工具的上下文拼装与 usage 记录，验证 DeepSeek Context Caching 命中稳定前缀。
  2. 再做摘要压缩，把旧消息压成 `chat_session_summary`，但保留全量 `chat_message`。
  3. 再做长期 memory 晋升与检索，先规则/关键词，后续再评估向量检索。
  4. 最后接 DeepSeek Tool Calls。先只读工具，再接"计划修改提议"，确认卡稳定后再允许 commit。
- Token 预算建议：
  - 稳定 system + 工具 schema：优先前置，保持稳定，约 10%–15%。
  - 用户档案、目标、安全限制、当前周计划：约 20%–30%，安全限制永不丢。
  - 检索记忆与知识片段：约 10%–20%，按相关性排序，低相关性不注入。
  - 最近对话窗口：约 20%–30%，优先保留最近用户问题、AI 待办、未确认建议卡。
  - 工具结果与上传文件摘要：约 10%–15%，只放摘要与引用 id。
  - 回复与工具调用预留：至少 15%，避免模型没空间输出完整计划建议。
- 压缩保真要求：
  - 摘要必须区分"事实 / 用户偏好 / AI 建议 / 已采纳计划 / 被拒绝建议 / 待确认事项"。
  - 不能把单日疲劳、偶发疼痛自动写成长期伤病；涉及安全的内容要带时间与来源。
  - 上传文件只保留摘要、表头、关键训练行和 `file_id`，完整解析文本在 DB/文件缓存中按需读取。
  - 压缩连续失败 3 次进入熔断：保留最近窗口 + 安全记忆 + 当前计划，提示用户上下文过长但不阻断普通聊天。
- 工具调用设计：
  - 工具清单限制在健身闭环内：`get_profile`、`get_weekly_plan`、`get_daily_log`、`calculate_metrics`、`propose_plan_change`、`validate_plan_change`、`commit_plan_change_after_user_confirm`、`search_memory`、`read_uploaded_file_summary`。
  - `propose_plan_change` 只返回建议卡片，不写库；`commit_plan_change_after_user_confirm` 只由前端确认按钮触发，不由模型直接触发。
  - 工具参数用严格 schema + Pydantic 双重校验，拒绝未知字段、非法 day、找不到的动作名、非有限数字、越界 RPE。
  - 工具结果进入模型前由 ToolResultSlimmer 裁剪，前端展示可另走 REST 读完整数据。
- 验收（含 V2.5 #3）：
  - 成功路径：连续 80+ 轮对话后仍能回答与当前计划相关的问题；模型提出计划修改，用户确认后计划正确写回。
  - 边界 1：上下文超过 85% 阈值触发摘要，摘要后仍记得伤病限制、目标体重、当前周计划和已拒绝建议。
  - 边界 2：上传大 Excel 后，prompt 只注入摘要和引用 id，不把整表塞入上下文。
  - 边界 3：模型请求不存在的动作名/日期/字段时，工具返回可解释错误，计划不变。
  - 失败场景：DeepSeek 工具调用参数不合法或上游超时时，不写脏数据，前端显示可重试提示；`chat_message` 不保存半截 assistant。

### Phase 4 — 文件上传解析 + 模型选择 + 前端 MD 渲染 + 草稿持久化
- 交付：`files/*`、`/api/models` + 前端下拉、前端 MD 渲染器、草稿后端持久化、对话滚动定位到最新。
- 验收：成功——上传 excel/docx/图片可解析喂模型、切模型生效、回复 MD 渲染、切页回来草稿与最新消息都在；边界——超大/不支持格式、空文件；失败——解析失败给提示且不影响主对话。

### Phase 5 — 多会话 + 知识库 + 周期计划引擎/预制库（V3）
- 交付：真实多会话（取代假多会话）、`knowledge_item` 跨对话记忆注入、`cycle_engine` + `preset_library`。
- 验收：成功——多对话独立、越聊越"认识你"、选预制计划按 1RM 覆盖、周期自动递增；边界——空知识库、周期切换；失败——预制计划缺 1RM 时给提示。

---

## 十一、风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| localStorage→DB 迁移丢数据 | 用户历史全失 | Phase 1 提供导入脚本 + 迁移前自动 JSON 备份；迁移幂等可重试 |
| 前后端契约漂移 | 前端报错/数据错位 | 用 pydantic schema 固化契约；保留现有数据形状（exercise JSON 原样）；加契约测试 |
| 本地需起两个进程 | 启动复杂、上手成本 | 根目录 `npm run dev` 用 `concurrently` 同起 Vite + uvicorn；README 写清 |
| API Key 管理 | 泄露/缺失 | Key 只存后端 `.env`；前端永不接触；缺失时 `/api/models` 与 chat 返回明确错误 |
| SSE 兼容/断连 | 流式中断 | `EventSource` 自动重连 + 后台任务兜底（离页用 background_worker 持久化结果） |
| 长对话 token 成本 | 费用/超限 | `context_manager` 压缩 + 工具结果裁剪 + 分层 prompt（参考 Claude Code/OpenCode） |
| DeepSeek 缓存命中低 | 成本上升、延迟变高 | 稳定 system/tool schema 前置；动态数据后置；禁用在前缀中插入时间戳、随机 id；记录 cache hit/miss |
| Thinking Mode 与工具调用串联错误 | 后续轮次报错或丢推理状态 | `chat_session.py` 按 DeepSeek 文档保存必要 `reasoning_content`，工具结果与 assistant tool_calls 成对落库 |
| Memory 污染 | 把临时状态误记成长期事实 | memory 晋升规则 + 置信度 + 来源消息；安全类记忆单独标记；低置信度记忆让用户确认 |
| 工具误写计划 | 训练安排被静默改坏 | 模型只调用 propose 工具；写库必须经过前端采纳按钮和后端 Pydantic/adopt 双重校验 |
| 知识库语义检索复杂度 | 过度工程 | MVP 先关键词/结构化检索，确有需要再上向量库 |

---

## 十二、对 AGENTS.md 与既有文档的影响

- **技术边界更新**：AGENTS.md 原「不在 MVP 阶段引入后端、数据库」需更新为「进入 agent 生态阶段，引入**本地** Python 后端（FastAPI + SQLite），仍不引入账号系统/云同步」。
- **文档同步**：重构落地时需为 `backend/` 补充 README/ARCHITECTURE 段落（启动、依赖、API、数据模型、迁移），并保持前端文档相应更新。
- **协作流程不变**：仍按 plan → code → review；后端编码同样走 `superpowers:subagent-driven-development`，主 agent 两轮审查；每个验证通过的子任务用中文 commit。
- **取代关系**：本文取代已删除的 `docs/RepMind_Python重构分析报告.md`；后续每完成一个 Phase 应回写更新本文的进度。

---

*本文基于 V2.1 全量代码核实生成。落地顺序：Phase 1 → 5，先解除存储/密钥/后台三大硬约束，再叠加文件、知识库与周期计划。*
