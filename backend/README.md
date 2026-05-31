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

当前仍未落地到后端的内容：

- DeepSeek 代理与 SSE 流式
- 后台思考
- 计划采纳后端化
- AI 教练页前端切换到后端 chat 接口

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
- 后端 Agent 模块只从 `backend/.env` 读取 DeepSeek API Key；前端旧直连路径将在 Task 9 移除

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

### 今日日志

- `GET /api/daily-log?from=YYYY-MM-DD&to=YYYY-MM-DD`
- `PUT /api/daily-log/{date}`

### 聊天存储

- `GET /api/chat/sessions`
- `POST /api/chat/sessions`
- `GET /api/chat/sessions/default`
- `GET /api/chat/sessions/{id}/messages`
- `POST /api/chat/sessions/{id}/messages`

说明：

- `GET /api/chat/sessions/default` 会获取或创建“默认对话”，用于承接旧版单条 `chatHistory`
- `POST /api/chat/sessions` 未传标题时会创建“新对话”，不会占用默认会话语义
- 消息读取全量返回，不做 20 条裁剪
- 追加消息仅负责存储 `role / content / suggestion`，不触发 DeepSeek 请求
- `suggestion` 为可空 JSON，用于后续保存 AI 结构化建议

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
