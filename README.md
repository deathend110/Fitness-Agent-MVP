# RepMind MVP

RepMind MVP 是一个本地运行的 AI 健身教练与训练记录应用。当前版本采用前端 React + 本地 FastAPI + SQLite 的结构，围绕一条可演示、可验证的核心闭环工作：

用户档案 -> 一周训练计划 -> 今日日志 -> AI 教练读取上下文 -> 返回建议或计划卡 -> 用户确认后写回训练计划

## 当前能力

- 维护用户档案、训练目标和三大项 1RM
- 我的档案页提供结构化摘要卡、分组表单和折叠式数据管理区，适合日常记录与演示展示
- 维护一周训练计划，并支持按日编辑训练类型与动作
- 维护今日日志，记录体重、热量、蛋白质、睡眠、疲劳、步数、训练备注和手动 TDEE
- 根据今日计划和日志生成每日摘要与体重趋势视图
- 提供 AI 教练对话页，支持多会话、流式回复、草稿恢复、附件上传和 Markdown 消息渲染
- AI 教练会在后端自动读取档案、周计划、今日日志、近期对话、会话摘要、记忆和文件摘要
- 当模型返回结构化计划建议时，前端会展示待确认的计划卡，用户可确认写回或忽略
- 支持模型配置管理，可切换和测试 OpenAI-compatible 与 Gemini-native provider

## 技术栈

- 前端：Vite、React 19、Tailwind CSS
- 后端：FastAPI、SQLAlchemy Async、SQLite
- AI 运行时：OpenAI-compatible provider runtime、Gemini-native provider runtime
- 测试：Node 内置测试、pytest、Playwright

## 环境要求

- Node.js 24 或兼容版本
- npm 11 或兼容版本
- Python 3.11+
- `uv`

## 安装

安装前端依赖：

```bash
npm install
```

安装 Python 依赖：

```powershell
uv sync
```

准备环境文件：

```powershell
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env
```

## 启动

只启动前端：

```bash
npm run dev
```

只启动后端：

```powershell
npm run dev:backend
```

同时启动前后端：

```powershell
npm run dev:all
```

停止当前项目相关本地进程：

```powershell
npm run stop:all
```

默认地址：

- 前端：`http://localhost:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`

## 环境变量

根目录 `.env` 主要用于前端开发期配置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_DEV_PORT=5173
```

`backend/.env` 主要用于后端运行：

```bash
DATABASE_URL=sqlite+aiosqlite:///./data/repmind.db
DATA_DIR=./data
UPLOADS_DIR=./data/uploads
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEFAULT_MODEL=deepseek-v4-flash
LLM_TIMEOUT_SECONDS=30
MODEL_PROVIDER_CONFIG_PATH=./config/model_providers.json
```

说明：

- 前端统一通过 `VITE_API_BASE_URL` 访问后端
- 后端启动地址由 `BACKEND_HOST` 和 `BACKEND_PORT` 控制
- SQLite 默认文件是 `backend/data/repmind.db`
- 上传文件默认存放在 `backend/data/uploads`
- Provider 配置默认从 `backend/config/model_providers.json` 读取
- 如需演示 AI 教练，至少需要在本地配置一个可用的模型 provider 和对应 API Key
- 不要提交真实 API Key

## AI Provider 说明

当前聊天能力支持两类 provider：

- OpenAI-compatible provider
- Gemini-native provider

你可以在应用内的模型设置中测试连接、发现模型，并切换默认模型。

## 测试

前端单测：

```bash
npm test
```

前端构建：

```bash
npm run build
```

后端测试：

```powershell
uv run pytest backend\tests -q
```

浏览器自动化前，先安装 Chromium：

```powershell
uv run python -m playwright install chromium
```

示例 E2E：

```powershell
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\coach_browser_smoke.py
```

## Demo 路径

1. 启动 `npm run dev:all`
2. 在“我的档案”填写基础信息、训练目标和三大项 1RM
3. 在“训练计划”配置至少一天的训练内容
4. 在“今日日志”填写体重、热量、睡眠、疲劳和备注
5. 进入“AI 教练”发送问题，观察流式回复和上下文驱动的建议
6. 如果出现计划建议卡，点击确认写回
7. 返回“训练计划”确认对应日程已经更新

## 相关文档

- [ARCHITECTURE.md](/g:/VSCODE-G/Fitness Agent MVP/ARCHITECTURE.md)
- [backend/README.md](/g:/VSCODE-G/Fitness Agent MVP/backend/README.md)
