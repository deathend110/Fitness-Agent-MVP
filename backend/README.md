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

当前仍未落地到后端的内容：

- AI 教练页真实多会话 UI

这些内容属于 V2.3 Phase 2。

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

在 `backend/` 目录执行：

```powershell
uv run python -m alembic upgrade head
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

响应体为 `{ok, message, plan}`。当前只支持更新已有动作字段；目标 day、动作名、字段名、action 或 RPE 边界不合法时返回 `ok: false` 并保留原计划，不写入脏数据。

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

说明：

- `GET /api/chat/sessions/default` 会获取或创建“默认对话”，用于承接旧版单条 `chatHistory`
- `POST /api/chat/sessions` 未传标题时会创建“新对话”，不会占用默认会话语义
- 消息读取全量返回，不做 20 条裁剪
- `GET /api/chat/stream` 接收 `messages=<JSON>`、可选 `session_id / model`，返回 `text/event-stream`
- SSE 事件格式为 `event: delta / suggestion / done / error`，`data` 始终是 JSON
- `POST /api/chat/reply` 接收 `{sessionId?, messages, model?}`，用于前端流式失败后的非流式回退
- 流式和非流式请求都只在完整成功后一起写入本轮 user + assistant，错误时不写半截 assistant
- `suggestion` 为可空 JSON，用于后续保存 AI 结构化建议
- `POST /api/chat/{session_id}/background` 接收 `{messages, model?}`，返回 `{task_id}`，用于前端离页时提交后台思考兜底
- `GET /api/chat/background/{task_id}` 返回 `pending / running / succeeded / failed / not_found`；成功时 `result` 包含 `{text, suggestion}`，且本轮 user + assistant 已写入 `chat_message`
- 前端触发后台思考前会中止当前前台 SSE / 普通请求，且只有后台任务成功拿到 `task_id` 后才抑制前台错误，避免后台任务和前台请求双写同一轮对话
- 后台任务失败或返回空内容时只记录 `failed` 状态和友好 message，不写入脏 assistant
- 后台任务表当前存放在后端进程内存中，服务重启后旧 task_id 会返回 `not_found`

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
