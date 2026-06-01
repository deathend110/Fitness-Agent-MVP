# FitLoop MVP

FitLoop MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。项目当前聚焦一条最小但完整的核心闭环：

用户档案 -> 训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 一键采纳并写回训练计划

## 项目简介

- 前端：Vite + React + Tailwind CSS
- 后端：FastAPI + SQLite
- AI 接口：OpenAI-compatible 与 Gemini-native 双协议适配正在落地，当前聊天主链路已接入运行时 `modelRef`
- 模型适配：当前已完成独立模型配置、双 Provider 基础层、统一工具调用内核与聊天运行时接线
- 运行形态：本地前后端联调，可直接用于课程演示

当前 MVP 主要能力：

- 维护用户档案、训练目标和三大项 1RM
- 维护一周训练计划与今日日志
- AI 教练在发送前自动注入最新档案、计划、日志和相关上下文
- AI 回复支持结构化建议卡片，用户确认后写回训练计划
- AI 教练支持“单日训练计划卡”采纳：确认后可直接把该日训练类型与动作写回训练计划
- 支持真实会话历史、文件上传摘要注入、附件回显和安全 Markdown 渲染

说明：

- README 只保留项目概览和使用说明
- 阶段性功能更新、历史任务记录与迭代说明已迁移到 [docs/progress.md](/g:/VSCODE-G/Fitness Agent MVP/docs/progress.md)

## 环境要求

- Node.js 24.13.1 或兼容版本
- npm 11.8.0 或兼容版本
- Python 3.11+
- `uv`（用于管理后端与自动化依赖）

## 安装命令

前端依赖：

```bash
npm install
```

后端与 Python 依赖：

```powershell
uv sync
```

首次配置时，建议准备环境文件：

```powershell
Copy-Item backend\.env.example backend\.env
```

## 运行命令

启动前端开发服务器：

```bash
npm run dev
```

前后端双进程联调：

```powershell
npm run dev:all
```

只启动后端：

```powershell
npm run dev:backend
```

生产构建与本地预览：

```bash
npm run build
npm run preview
```

默认前端地址通常为：

```text
http://localhost:5173/
```

说明：

- 后端首次启动会自动在 `backend/data/repmind.db` 创建 SQLite 表
- 浏览器端默认通过 `VITE_API_BASE_URL` 访问本地后端

## API Key 配置

前端 `.env` 示例：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

后端 `backend/.env` 至少需要配置：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key
DATABASE_URL=sqlite+aiosqlite:///./data/repmind.db
MODEL_PROVIDER_CONFIG_PATH=./config/model_providers.json
```

配置说明：

- 前端不再直接读取或暴露 DeepSeek API Key
- AI 教练相关能力仍会从 `backend/.env` 读取 `DEEPSEEK_API_KEY` 作为旧版兼容与首份配置 bootstrap 来源
- 模型提供方配置已经开始迁移到独立 JSON 文件，默认落在 `backend/config/model_providers.json`
- `MODEL_PROVIDER_CONFIG_PATH` 用来覆盖模型配置 JSON 的路径，缺失文件时会自动根据当前后端设置生成首份文件
- `GET /api/models` 现在返回带 `provider::remoteModel` 形式的 `modelRef`，聊天、草稿和后台任务会统一按这个引用解析真实模型
- 保存模型配置时会保留真实 `apiKey`，但返回给前端的是脱敏预览值
- 未配置 API Key 时，除 AI 教练外的大部分本地功能仍可使用
- 不要提交真实 API Key

环境变量样例见 [backend/.env.example](/g:/VSCODE-G/Fitness Agent MVP/backend/.env.example)。

## 测试命令

前端自动化测试：

```bash
npm test
```

前端构建验证：

```bash
npm run build
```

后端基础测试：

```powershell
uv run python -m pytest backend\tests\test_health.py backend\tests\test_models.py backend\tests\test_crud_api.py backend\tests\test_migrate.py
```

AI 教练关键链路回归：

```powershell
node --test tests/coachComposer.test.js tests/markdownMessage.test.js tests/chatHistory.test.js
uv run pytest backend\tests\test_chat_store.py backend\tests\test_chat_stream.py backend\tests\test_background_worker.py backend\tests\test_models_api.py backend\tests\test_drafts_api.py -q
```

浏览器自动化冒烟：

```powershell
uv run python -m playwright install chromium
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_browser_smoke.py
```

更细的验证记录见 [docs/verification.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification.md)。

## Demo 操作路径

1. 启动 `npm run dev:all`，确认前后端都已启动。
2. 进入“我的档案”，填写基础信息、训练目标和三大项 1RM。
3. 进入“训练计划”，配置一周计划，至少为某一天添加一个动作。
4. 进入“今日日志”，填写体重、热量、睡眠、疲劳度和备注。
5. 进入“AI 教练”，发送训练调整问题，确认后端自动注入当前上下文。
6. 如果 AI 返回结构化建议卡，点击“采纳并更新计划”；新版也支持直接采纳整张“单日训练计划卡”。
7. 返回“训练计划”，确认对应动作或整日训练安排已被更新并持久化。
8. 如需展示扩展能力，可额外演示文件上传、附件回显、历史会话恢复与 Markdown 表格渲染。

## 相关文档

- 架构与数据流：[ARCHITECTURE.md](/g:/VSCODE-G/Fitness Agent MVP/ARCHITECTURE.md)
- 后端启动、迁移与接口：[backend/README.md](/g:/VSCODE-G/Fitness Agent MVP/backend/README.md)
- 迭代进度与历史记录：[docs/progress.md](/g:/VSCODE-G/Fitness Agent MVP/docs/progress.md)
- 验证记录：[docs/verification.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification.md)
