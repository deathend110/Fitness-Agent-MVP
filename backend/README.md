# FitLoop Backend

## 简介

`backend/` 是 V2.3 新增的本地 Python 后端，负责承接 FitLoop MVP 的数据持久化、迁移能力，并逐步承接 AI Agent 相关后端能力。

当前已落地范围：

- `profile` 后端 CRUD
- `weeklyPlan` 后端 CRUD
- `dailyLog` 后端 CRUD
- `localStorage -> SQLite` 一次性迁移接口
- `chat` 会话与消息后端 CRUD
- DeepSeek 客户端与 `---JSON---` 响应解析基础模块
- DeepSeek 后端代理、SSE 流式事件和非流式回退接口
- 离页后台思考任务提交、查询和成功回复落库
- 计划采纳后端校验与写回接口
- Phase 3 数据模型：会话摘要、长期记忆、知识条目、工具调用日志和 usage 记录
- Phase 3 后端上下文拼装：`userInput/sessionId` 可由后端读取 SQLite 状态并构建 DeepSeek messages
- Phase 3 usage 观测：非流式与支持 usage 的流式响应完成后写入 `UsageRecord`，可查看 prompt cache hit/miss 汇总
- Phase 3 长对话摘要压缩：`SummaryCompressor` 生成 `ChatSessionSummary`，`StateReinjector` 回注当前状态
- Phase 3 memory：长期记忆候选提取、检索、确认和忽略接口
- Phase 3 Tool Calls：只读工具、工具循环、工具结果瘦身、工具审计日志
- Phase 3 计划修改安全闸门：`propose` 只生成建议卡，`commit` 必须来自用户确认路径

后续阶段仍未落地的内容：

- AI 教练页真实多会话 UI
- 文件上传解析、模型选择、前端 Markdown 渲染、后端草稿持久化、完整知识库、周期计划与预制计划库

V2.3 Phase 2 已完成密钥后移、SSE 流式代理、离页后台思考和计划采纳后端化；Phase 3 已把 prompt、上下文管理、memory、usage 观测和工具调用迁入后端 Agent Orchestrator。

## 技术栈

- FastAPI
- SQLAlchemy 2.x Async
- SQLite
- Alembic
- pytest + pytest-asyncio

## 安装依赖

在仓库根目录执行：

```powershell
uv sync
```

说明：

- `backend/requirements.txt` 是兼容导出文件，不是主依赖入口
- 如需刷新该文件，可执行 `uv export --format requirements-txt -o backend\requirements.txt`

## 环境变量

复制样例文件：

```powershell
Copy-Item backend\.env.example backend\.env
```

当前重点字段：

- `DATABASE_URL`
- `CORS_ORIGINS`
- `DATA_DIR`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEFAULT_MODEL`
- `DEEPSEEK_TIMEOUT_SECONDS`

说明：

- 数据库存放在 `backend/data/`
- `DATABASE_URL=sqlite+aiosqlite:///./data/repmind.db` 会按 `backend/` 目录解析，仓库根目录启动也不会写到根目录 `data/`
- `backend/.env` 不应提交到仓库
- 后端 Agent 模块只从 `backend/.env` 读取 DeepSeek API Key；前端不再读取或打包 DeepSeek Key

## 启动方式

只启动后端：

```powershell
npm run dev:backend
```

前后端双进程联调：

```powershell
npm run dev:all
```

健康检查：

```text
GET http://127.0.0.1:8000/api/health
```

## 数据库迁移

开发启动时会自动创建本地 SQLite 表并写入空白档案与一周休息日默认计划，首次演示不需要手动迁移。

如需显式执行 Alembic 迁移，在仓库根目录执行：

```powershell
uv run alembic -c backend\alembic.ini upgrade head
```

## 接口速查

### 健康检查

- `GET /api/health`

### 档案

- `GET /api/profile`
- `PUT /api/profile`

### 周计划

- `GET /api/weekly-plan`
- `PUT /api/weekly-plan`
- `POST /api/weekly-plan/adopt`

`POST /api/weekly-plan/adopt` 请求体：

```json
{
  "day": "Monday",
  "changes": [
    {
      "action": "update",
      "exerciseName": "深蹲",
      "field": "pct",
      "newValue": 0.7
    }
  ]
}
```

响应体为 `{ok, message, plan}`。当前只支持 `action: "update"` 更新已有动作字段；目标 day、动作名、字段名、action、数值字段或 RPE 边界不合法时返回 `ok: false` 并保留原计划，不写入脏数据。`pct / kg / sets / reps / rpe` 支持安全数字字符串转换，但会拒绝 `NaN / Infinity` 等非有限数值。

### 今日日志

- `GET /api/daily-log?from=YYYY-MM-DD&to=YYYY-MM-DD`
- `PUT /api/daily-log/{date}`

### 聊天存储

- `GET /api/chat/sessions`
- `POST /api/chat/sessions`
- `GET /api/chat/sessions/default`
- `GET /api/chat/sessions/{id}/messages`
- `POST /api/chat/sessions/{id}/messages`
- `GET /api/chat/stream`
- `POST /api/chat/reply`
- `POST /api/chat/{session_id}/background`
- `GET /api/chat/background/{task_id}`
- `GET /api/chat/sessions/{id}/context/debug`
- `GET /api/memory/items?kind&query`
- `GET /api/memory/candidates`
- `POST /api/memory/candidates/{id}/confirm`
- `POST /api/memory/candidates/{id}/ignore`
- `POST /api/tools/plan/propose`
- `POST /api/tools/plan/commit`

说明：

- `GET /api/chat/sessions/default` 会获取或创建“默认对话”，用于承接旧版单条 `chatHistory`
- `POST /api/chat/sessions` 未传标题时会创建“新对话”，不会占用默认会话语义
- 消息读取全量返回，不做 20 条裁剪
- `GET /api/chat/stream` 接收 `messages=<JSON>`、可选 `session_id / model`，返回 `text/event-stream`
- `GET /api/chat/stream` 也可接收 `userInput + session_id + model + thinking`，由后端统一拼装上下文
- SSE 事件格式为 `event: delta / suggestion / proposal / tool_status / done / error`，`data` 始终是 JSON
- `POST /api/chat/reply` 接收 `{sessionId?, messages, model?}` 或 Phase 3 新契约 `{sessionId?, userInput, model?}`，用于前端流式失败后的非流式回退
- 新契约会调用 `backend.agent.chat_session.build_agent_request()`，按稳定 system prompt、当前用户状态、安全记忆、相关记忆、会话摘要、最近消息和当前输入构建 DeepSeek messages
- DeepSeek Tool Calls 由 `run_tool_calling_chat()` 执行；每轮最多 4 次工具调用，工具参数非法或循环超限会返回可解释错误并记录 `ToolCallLog`
- 流式和非流式请求都只在完整成功后一起写入本轮 user + assistant，错误时不写半截 assistant
- `suggestion` 为可空 JSON，用于后续保存 AI 结构化建议
- `POST /api/chat/{session_id}/background` 接收 `{messages, model?}`，返回 `{task_id}`，用于前端离页时提交后台思考兜底
- `GET /api/chat/background/{task_id}` 返回 `pending / running / succeeded / failed / not_found`；成功时 `result` 包含 `{text, suggestion}`，且本轮 user + assistant 已写入 `chat_message`
- 前端触发后台思考前会中止当前前台 SSE / 普通请求，且只有后台任务成功拿到 `task_id` 后才抑制前台错误，避免后台任务和前台请求双写同一轮对话
- 前端本地 `fitloop:coach-background-task` 会记录 `taskId / sessionId / sourceUserIndex / userContent / createdAt`，回页合并前用源 user 下标和内容确认仍是原始轮次
- 后台任务失败或返回空内容时只记录 `failed` 状态和友好 message，不写入脏 assistant
- 后台任务表当前存放在后端进程内存中，服务重启后旧 task_id 会返回 `not_found`
- `/context/debug` 当前返回会话 usage 汇总和 token budget；`prompt_cache_hit_tokens / prompt_cache_miss_tokens` 直接来自 DeepSeek `usage`，不会伪造流式缺失字段

### Phase 3 memory

- `GET /api/memory/items?kind&query` 查询已确认长期记忆，支持按类型和关键词过滤
- `GET /api/memory/candidates` 查询待确认候选
- `POST /api/memory/candidates/{id}/confirm` 将候选晋升为长期记忆
- `POST /api/memory/candidates/{id}/ignore` 忽略候选，后续不再注入

memory 保存用户长期事实、偏好、目标、约束、器械条件和安全限制；knowledge 保存外部资料或上传文件知识。单日疲劳、临时状态和 AI 自己的建议不会直接晋升为 memory。

### Phase 3 工具与计划 proposal

- `POST /api/tools/plan/propose` 接收计划修改建议，返回 `{proposalId, card, validation}`，不写 `weekly_plan_day`
- `POST /api/tools/plan/commit` 接收 `{proposalId}`，仅在 proposal 未过期、未重复提交且校验通过时写回计划

工具 schema 约束：

- 使用 DeepSeek OpenAI 兼容 `tools` 结构
- 参数 schema 使用 `additionalProperties: false`
- 后端必须用 Pydantic 二次校验 day、日期、动作名、字段名、非有限数字和 RPE 边界
- 模型只能提出计划修改 proposal，不能在 tool loop 中直接 commit 写库

### DeepSeek cache / token 调试

`GET /api/chat/sessions/{id}/context/debug` 会返回：

- 最近一次上下文选择与估算 token
- token budget 配置和裁剪原因
- `UsageRecord` 汇总的 `prompt_tokens / completion_tokens / total_tokens`
- DeepSeek `prompt_cache_hit_tokens / prompt_cache_miss_tokens`

如果 cache hit 很低，优先检查 stable system prompt 和 tools schema 是否被动态时间戳、随机 id 或实时状态污染。

### localStorage 迁移

- `POST /api/migrate/import`

请求体使用前端 `buildBackupPayload()` 形状：

```json
{
  "app": "fitloop-mvp",
  "version": 1,
  "exportedAt": "2026-05-31T11:30:00.000Z",
  "profile": {},
  "weeklyPlan": {},
  "dailyLog": {},
  "chatHistory": []
}
```

迁移行为说明：

- `profile / weeklyPlan / dailyLog` 会幂等写入 SQLite
- 旧版导入接口中的 `chatHistory` 当前仍只接收不入库，后续会单独接入 chat 表迁移
- 响应中的 `skipped.chatHistory` 会明确说明这一点

## 数据目录

后端运行期数据统一放在：

```text
backend/data/
```

当前主要包含：

- `repmind.db`

## 测试命令

以下命令默认在仓库根目录执行：

定向测试：

```powershell
uv run python -m pytest backend\tests\test_health.py
uv run python -m pytest backend\tests\test_models.py
uv run python -m pytest backend\tests\test_crud_api.py
uv run python -m pytest backend\tests\test_migrate.py
```

Phase 1 汇总测试：

```powershell
uv run python -m pytest backend\tests\test_health.py backend\tests\test_models.py backend\tests\test_crud_api.py backend\tests\test_migrate.py
```

聊天存储定向测试：

```powershell
uv run pytest backend\tests\test_chat_store.py
```

聊天 SSE 定向测试：

```powershell
uv run pytest backend\tests\test_chat_stream.py
```

后台思考定向测试：

```powershell
uv run pytest backend\tests\test_background_worker.py
```

计划采纳定向测试：

```powershell
uv run pytest backend\tests\test_adopt_plan.py
```

Phase 3 数据模型与上下文拼装定向测试：

```powershell
uv run pytest backend\tests\test_phase3_models.py backend\tests\test_context_manager.py backend\tests\test_chat_session_context.py
uv run pytest backend\tests\test_usage_ledger.py backend\tests\test_deepseek_client.py backend\tests\test_chat_stream.py
uv run pytest backend\tests\test_summary_compressor.py backend\tests\test_memory.py backend\tests\test_memory_api.py
uv run pytest backend\tests\test_tool_calling.py backend\tests\test_chat_tool_loop.py backend\tests\test_plan_tools.py
```

Phase 3 全量后端验证：

```powershell
uv run pytest backend\tests
```
