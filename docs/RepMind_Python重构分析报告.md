# RepMind MVP — Python 重构分析报告

> 生成时间：2026-05-31  
> 分析范围：当前所有源码、架构文档、修改意见记录 V1/V2/V3

---

## 一、现状快速摘要

| 维度 | 现状 |
|------|------|
| 前端 | React 19 + Vite + Tailwind CSS |
| 数据持久化 | 浏览器 `localStorage`（单标签页，无跨设备同步）|
| AI 接入 | DeepSeek OpenAI 格式 API，直接在浏览器发起 HTTP 请求 |
| Agent 能力 | 无真正 Agent：仅单轮 system-prompt 注入 + 流式输出 |
| 上下文管理 | 裁剪为最近 20 条消息，丢弃超出部分 |
| 文件处理 | 未实现 |
| 后台思考 | 不支持（离开页面即中断请求）|

---

## 二、必须用 Python 重构的部分

下面按**优先级**从高到低排列，标注来源文件和迁移理由。

---

### 🔴 P0 — AI Agent 核心层（最高优先级）

**当前文件：** `src/api/deepseek.js` · `src/utils/coachChat.js` · `src/utils/aiResponse.js`

**核心问题：**

1. **浏览器不能后台运行**：用户离开 `CoachTab` 页面，`fetch` 请求被浏览器挂起或中断。V2 修改意见明确要求「支持后台思考，允许我离开页面」。
2. **API Key 裸露在前端**：`VITE_DEEPSEEK_API_KEY` 通过 Vite 环境变量打包进 JS bundle，任何人打开 DevTools 即可提取。
3. **无法做真正的多轮 Tool Calling**：DeepSeek function calling 的完整链路（tool_use → tool_result → 再次推理）需要服务端维持状态，浏览器单次 HTTP 请求无法实现。
4. **上下文磁盘缓存不可能在浏览器实现**：V2 要求「上下文磁盘缓存」，浏览器只有 `localStorage`（5MB 上限，且无法跨 session 高效检索）。

**Python 重构目标：**

```
backend/
  agent/
    deepseek_client.py      # DeepSeek HTTP 客户端封装（含流式 SSE）
    chat_session.py         # 多轮对话状态机
    tool_calling.py         # Function Calling 编排（健身计划读写工具）
    context_manager.py      # 上下文窗口管理 + 压缩策略
    background_worker.py    # asyncio 任务队列，支持离页继续推理
```

**技术选型建议：**
- HTTP Server：**FastAPI** + **uvicorn**（异步，天然支持 WebSocket SSE 透传）
- 流式输出：Server-Sent Events（`text/event-stream`）→ 前端 `EventSource`
- 后台任务：`asyncio.Task` 或 `Celery`（初期 asyncio 足够）

---

### 🔴 P0 — 数据持久化层

**当前文件：** `src/utils/storage.js` · `src/utils/defaultData.js` · `src/utils/dataTransfer.js`

**核心问题：**

1. `localStorage` 5MB 上限会在长期使用后打满（特别是完整聊天记录）。
2. `chatHistory` 被硬裁剪为 20 条（`CHAT_HISTORY_LIMIT = 20`），V2 要求「本地保存的聊天记录需要保存全部」。
3. `localStorage` 无法被 Python Agent 直接读取，导致前后端数据不同步。
4. 用户数据（体重、训练计划、日志）目前只靠 JSON 导入/导出备份，无自动持久化。

**Python 重构目标：**

```
backend/
  db/
    database.py             # SQLite 连接池（初期本地，后期可换 PostgreSQL）
    models.py               # ORM 模型：User / WeeklyPlan / DailyLog / ChatSession / ChatMessage
    migrations/             # Alembic 迁移脚本
  api/
    profile.py              # GET/POST /api/profile
    weekly_plan.py          # GET/PUT /api/weekly-plan
    daily_log.py            # GET/POST /api/daily-log/{date}
    chat.py                 # GET/POST /api/chat/sessions · /messages
```

**技术选型建议：**
- ORM：**SQLAlchemy** 2.x（async 模式）
- 数据库：**SQLite**（本地应用，无需安装额外服务）
- 迁移：**Alembic**

---

### 🟠 P1 — 上下文管理与 Token 优化

**当前文件：** `src/utils/chatHistory.js` · `src/utils/coachChat.js` · `src/utils/prompt.js`

**核心问题：**

当前「上下文管理」仅仅是 `.slice(-20)` 截断，V2/V3 修改意见要求：
- 上下文压缩（summarization）
- 多工具调用下的 token 消耗优化
- 参考 Claude Code / OpenCode 的长对话设计

**Python 重构目标：**

```
backend/
  agent/
    context_manager.py
      ├── ContextWindow         # 滑动窗口，精确计数 token（tiktoken / deepseek tokenizer）
      ├── SummaryCompressor     # 超出模型上下文阈值时调用 AI 自动摘要历史
      └── PromptBuilder         # 将 profile / weekly_plan / daily_log 序列化注入 system prompt
```

**实现策略（参考 Claude Code 设计）：**
1. 超过 token 阈值（1M）时，将最早的若干轮对话压缩为一段摘要 message
2. 工具调用结果只保留必要字段，去除冗余 JSON
3. System prompt 按「静态档案」+「动态今日日志」分层，仅在数据变化时重建

---

### 🟠 P1 — 文件上传与解析模块

**当前状态：** 完全未实现（V1/V2 修改意见均提到此需求）

**需求：**
- 图片上传（喂给 AI 视觉分析，如训练截图、食物照片）
- Excel 解析（训练记录表格）
- DOCX / MD 文件解析
- 文件缓存到软件所在文件夹（非 C 盘）

**Python 重构目标：**

```
backend/
  files/
    uploader.py             # 文件接收 + 存储到 data/uploads/
    parsers/
      image_parser.py       # base64 编码，准备喂给 DeepSeek vision
      excel_parser.py       # pandas / openpyxl → 结构化 JSON
      docx_parser.py        # python-docx → markdown 文本
      md_parser.py          # 直接透传或 markdown-it 解析
```

**技术选型：**
- Excel：`pandas` + `openpyxl`
- DOCX：`python-docx`
- 图片：`Pillow` + base64
- 存储路径：`./data/uploads/`（相对于 backend 目录，不写 C 盘）

---

### 🟠 P1 — 模型选择与调用配置

**当前文件：** `src/api/deepseek.js`（`DEFAULT_MODEL = 'deepseek-v4-flash'`，硬编码）

**需求（V2 修改意见）：**
> 我需要能选择模型，从接入的 API 中列出可用模型，在提示词输入框旁有可展开的选项

**Python 重构目标：**

```
backend/
  api/
    models.py               # GET /api/models → 返回可用模型列表
  config.py                 # 读取 .env，管理 API Key、base URL、可用模型白名单
```

前端只需请求 `/api/models` 动态渲染下拉选项，不再硬编码 model string。

---

### 🟡 P2 — 复杂指标计算服务

**当前文件：** `src/utils/dailyMetrics.js` · `src/utils/dailyMetricsPanel.js` · `src/utils/promptMetricsSection.js`

**现状评估：** 当前纯前端计算是可用的，但存在以下问题：

1. 当 AI 需要动态修正 TDEE / 体脂率（V1 修改意见 #2 要求 AI 结合历史数据修正），前端无法持久化 AI 的修正结果。
2. 随着周期计划（V3 意见）引入，指标计算复杂度会大幅上升，JS 难以维护。

**Python 重构目标（初期可选，后期必须）：**

```
backend/
  metrics/
    bmr.py                  # Mifflin-St Jeor 公式
    tdee.py                 # TDEE 估算 + AI 修正结果持久化
    body_composition.py     # BMI / 体脂率估算
    prompt_metrics.py       # 生成注入 AI 的 structured_metrics JSON
```

---

### 🟡 P2 — 周期计划引擎（未来功能，提前设计）

**当前状态：** 无（V3 修改意见提出）

**需求：**
- 可配置周期长度（1/2/6 周等）
- 周期间自动递增训练负荷（progressive overload step）
- 预制计划库（5x5 / 德州计划 / 疯牛 5x5 等）

**Python 重构目标（预留接口）：**

```
backend/
  plans/
    cycle_engine.py         # 周期状态机：当前第几周、下一周如何递增
    preset_library.py       # 预制计划 JSON 配置 + 按 1RM 自动填充重量
    plan_generator.py       # 根据周期配置生成 weeklyPlan 结构
```

---

## 三、可以保留在前端（JS/React）的部分

| 模块                                           | 原因              |
| -------------------------------------------- | --------------- |
| 所有 UI 组件（`PlanDayCard` 等）                    | 纯展示逻辑，React 胜任  |
| 表单草稿管理（`exerciseForm.js`）                    | 即时交互，无需服务端      |
| 简单格式化函数（`calc.js` 的 `formatWeightDisplay` 等） | 无状态、无副作用        |
| 训练计划编辑器状态（`planEditorState.js`）              | 本地 UI 状态，不涉及持久化 |
| 路由 / Tab 切换                                  | 纯前端导航           |

---

## 四、重构后整体架构

```
RepMind/
├── frontend/                   # 原 React 项目（保留）
│   ├── src/
│   │   ├── api/                # 改为调用 backend REST API 和 SSE
│   │   ├── components/         # 保留（UI 不动）
│   │   ├── utils/              # 保留纯 UI 工具函数，删除 AI/存储相关
│   │   └── ...
│   └── vite.config.js
│
└── backend/                    # 新增 Python 服务
    ├── main.py                 # FastAPI app 入口
    ├── config.py               # 环境变量、DeepSeek Key、模型配置
    ├── db/
    │   ├── database.py
    │   ├── models.py
    │   └── migrations/
    ├── api/
    │   ├── profile.py
    │   ├── weekly_plan.py
    │   ├── daily_log.py
    │   ├── chat.py             # SSE 流式接口
    │   └── models.py           # GET /api/models
    ├── agent/
    │   ├── deepseek_client.py
    │   ├── chat_session.py
    │   ├── context_manager.py
    │   ├── tool_calling.py
    │   └── background_worker.py
    ├── metrics/
    │   ├── daily_metrics.py
    │   └── prompt_metrics.py
    ├── files/
    │   ├── uploader.py
    │   └── parsers/
    ├── plans/
    │   ├── cycle_engine.py
    │   └── preset_library.py
    ├── data/                   # 本地数据目录（gitignore）
    │   ├── repMind.db
    │   └── uploads/
    └── requirements.txt
```

**前后端通信：**
- 普通 CRUD：REST API（JSON）
- AI 流式输出：`GET /api/chat/stream` → Server-Sent Events
- 文件上传：`POST /api/files/upload` → multipart/form-data

---

## 五、迁移优先级建议（实施顺序）

| 阶段 | 工作内容 | 收益 |
|------|----------|------|
| **Phase 1** | FastAPI 骨架 + SQLite 数据层 + 基础 CRUD API | 解除 localStorage 限制，聊天记录全量保存 |
| **Phase 2** | Python AI Agent（SSE 流式 + 后台任务） | API Key 安全、离页继续思考 |
| **Phase 3** | 上下文管理 + Token 优化 | 长对话稳定，成本可控 |
| **Phase 4** | 文件上传解析 + 模型选择 | 完成 V2 需求 |
| **Phase 5** | 周期计划引擎 + 预制库 | 完成 V3 需求 |

---

## 六、不建议用 Python 重写的部分

- **React UI**：重写成本极高，收益为零。保留原有组件，只把数据源从 `localStorage` 改为 API 调用即可。
- **Tailwind / CSS**：纯前端关注点，不涉及。
- **简单数值格式化**：`formatWeightDisplay`、`formatCountDisplay` 等无状态函数，留在前端减少 API 调用。

---

*本文档基于当前代码库全量分析生成，后续每完成一个 Phase 建议更新一次。*
