# RepMind MVP

RepMind MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。项目当前聚焦一条最小但完整的核心闭环：

用户档案 -> 训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 一键采纳并写回训练计划

## 项目简介

- 前端：Vite + React + Tailwind CSS
- 后端：FastAPI + SQLite
- AI 接口：当前正式聊天主链路以运行时 `modelRef` 驱动的 OpenAI-compatible 为中心；Gemini 继续保留原生运行时接入，DeepSeek 默认也按 OpenAI-compatible `/v1` 链路接入，并会根据 provider 的 `wireApi + apiPathMode` 在 `chat_completions` 与 `responses` 两条 wire 之间选择正确客户端，不再错误回退到旧 DeepSeek 直连链路
- 模型适配：当前已完成独立模型配置、双 Provider 基础层、统一工具调用内核与聊天运行时接线
- 运行形态：本地前后端联调，可直接用于课程演示

当前 MVP 主要能力：

- 维护用户档案、训练目标和三大项 1RM
- 维护一周训练计划与今日日志
- AI 教练在发送前自动注入最新档案、计划、日志和相关上下文
- AI 回复支持结构化建议卡片，用户确认后写回训练计划
- AI 教练支持“单日训练计划卡”采纳：确认后可直接把该日训练类型与动作写回训练计划
- 支持真实会话历史、文件上传摘要注入、附件回显和安全 Markdown 渲染
- 最近对话支持删除；未命名会话在首条用户提问成功落库后会自动改用该 prompt 作为标题
- AI 教练最近对话时间戳会兼容后端返回的“无时区 UTC ISO 字符串”，避免本地时区下显示偏移
- 后台思考任务会继续显示“思考中”状态，但不再锁定输入框；采纳计划卡后仍可继续输入下一条提示词
- “思考中”占位气泡已改成三个逐次呼吸的圆点动效，替代原来的方块光标，视觉提示更接近主流聊天产品
- AI 教练顶部已接入模型设置入口，可在页面内编辑多供应商 Provider 配置、可用模型与默认模型
- OpenAI-compatible Provider 设置页已支持显式配置 `wireApi`（`chat_completions` / `responses`）和 `apiPathMode`（`raw_root` / `append_v1`）
- OpenAI-compatible provider 后端现已按真实 `wireApi + apiPathMode` 构造 `/models` 与聊天 endpoint；`append_v1` 会自动避免 `.../v1/v1/...` 重复拼接
- OpenAI-compatible provider 的网络/HTTP 错误会优先显示真实 provider 名称，例如“聪明AI 网络请求失败…”，方便区分是 DeepSeek、本地代理还是中转站波动

当前 AI 教练主链路口径：

- 前端聊天主入口：`CoachTab -> src/utils/coachChat.js -> src/api/coachBackend.js`
- 前端普通 CRUD / 会话 / 草稿 / 文件 / 计划卡接口：`src/api/backendClient.js`
- 后端聊天主入口：`backend/api/chat.py -> backend/agent/chat_session.py -> run_tool_calling_chat()`
- provider runtime 主路径：OpenAI-compatible runtime / Gemini-native runtime
- legacy 兼容壳：`src/api/deepseek.js`、`POST /api/weekly-plan/adopt`、聊天 `messages` 旧契约、`DeepSeekClient` fallback

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
Copy-Item .env.example .env
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

关闭当前项目相关前后端进程：

```powershell
npm run stop:all
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
- 前端 dev server 端口统一由根目录 `.env` 中的 `VITE_DEV_PORT` 控制，未配置时默认回退到 `5173`
- 浏览器端统一通过 `VITE_API_BASE_URL` 访问本地后端；未配置时会回退到 `http://127.0.0.1:8000/api`
- `npm run dev:backend` 现在会通过 `backend/run_dev_server.py` 读取 `backend/.env` 中的 `BACKEND_HOST / BACKEND_PORT` 后再启动 uvicorn
- `npm run stop:all` 会调用 `scripts/kill-repmind.ps1`；同时保留 `scripts/kill-fitloop.ps1` 作为旧入口兼容脚本，二者都会只停止命令行中包含当前仓库路径的 `node/python/uv` 相关进程

## API Key 配置

前端 `.env` 示例：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_DEV_PORT=5173
```

后端 `backend/.env` 至少需要配置：

```bash
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
DEEPSEEK_API_KEY=your_deepseek_api_key
LLM_TIMEOUT_SECONDS=30
DATABASE_URL=sqlite+aiosqlite:///./data/repmind.db
MODEL_PROVIDER_CONFIG_PATH=./config/model_providers.json
HTTP_PROXY=
HTTPS_PROXY=
```

配置说明：

- 根目录 `.env` 只负责前端开发期配置；推荐把前端访问地址和前端 dev 端口都收口到这里
- `VITE_API_BASE_URL` 需要与后端实际地址保持一致，例如后端改到 `127.0.0.1:9000` 时应同步改成 `http://127.0.0.1:9000/api`
- `VITE_DEV_PORT` 改动后，若后端 `CORS_ORIGINS` 仍保留默认值，请一并在 `backend/.env` 中同步允许新的前端地址
- `BACKEND_HOST / BACKEND_PORT` 由后端启动脚本统一读取，避免 `package.json`、uvicorn CLI 和配置层三处各写一份端口
- 前端不再直接读取或暴露 DeepSeek API Key
- AI 教练相关能力仍会从 `backend/.env` 读取 `DEEPSEEK_API_KEY` 作为旧版兼容与首份配置 bootstrap 来源；`DeepSeekClient` 当前仅保留为短期 fallback，当运行时 provider 配置缺失、无效或尚未初始化时才会兜底
- `LLM_TIMEOUT_SECONDS` 是统一的模型请求超时入口；旧环境变量 `DEEPSEEK_TIMEOUT_SECONDS` 仍兼容，老 `.env` 不改也可以继续运行
- 当前仓库默认口径已经固化为：DeepSeek 使用 `https://api.deepseek.com/v1`，并在 provider 配置里配合 `wireApi=chat_completions`、`apiPathMode=append_v1`；如果你本地 `backend/config/model_providers.json` 是更早生成的旧文件，里面仍可能保留根路径写法，但运行时不会因此回退到旧主链路
- 模型提供方配置已经开始迁移到独立 JSON 文件，默认落在 `backend/config/model_providers.json`
- `MODEL_PROVIDER_CONFIG_PATH` 用来覆盖模型配置 JSON 的路径，缺失文件时会自动根据当前后端设置生成首份文件
- `GET /api/models` 现在返回带 `provider::remoteModel` 形式的 `modelRef`，聊天、草稿和后台任务会统一按这个引用解析真实模型
- 选择 Gemini 模型后，`/api/chat/reply` 与 `/api/chat/stream` 会直接实例化 Gemini 运行时客户端；如果仍看到 DeepSeek 模型名相关报错，通常说明当前进程还没有加载到最新代码
- 前端流式聊天现在统一使用 `POST /api/chat/stream` 发送 JSON body，不再把 `userInput / messages / thinking / fileIds` 拼进 query string，避免长输入和附件上下文把 URL 拉得过长
- AI 教练工具调用现在分为两条运行时链路：OpenAI-compatible `chat_completions` 会按 `assistant(tool_calls) -> tool` 顺序补齐消息，OpenAI-compatible `responses` 会按 `function_call -> function_call_output` 回环，Gemini-native 会按官方 `functionCall -> functionResponse` 结构继续下一轮请求
- 当前正式的 OpenAI-compatible 流式计划卡链路固定为：先在工具回环里拿到 proposal，再开始流式输出 assistant 正文；正文结束后才发 proposal 卡数据，随后补发 suggestion，最后再发 done
- `POST /api/chat/stream` 的稳定正常顺序当前只有两种：普通回复为 `delta* -> suggestion -> done`；计划卡回复为 `delta* -> proposal -> suggestion -> done`。约束是“先工具、再流式正文、正文后出卡、done 必须最后”，当前不要把 `tool_status` 当成正式主链路保证
- 当 AI 生成的是待确认 proposal 卡时，后端会拦截“已采纳 / 已写入计划 / 已更新计划”这类误导性正文表述，统一保留“待确认、尚未写回”的真实语义；真正写回仍只会发生在 `/api/tools/plan/commit`
- `/api/tools/plan/commit` 成功后，后端会同步把对应 assistant 历史消息里的 proposal 状态更新为 `committed`；后续同一会话继续追问或切换模型时，新的上下文也会显式带上该状态，避免模型把旧卡误判为仍待确认
- AI 教练页面当前采纳建议统一优先走 `commit / ignore` 标准 proposal 协议；只有历史 suggestion 缺少 `proposalId` 时，前端兼容层才会回退到 `/api/weekly-plan/adopt`
- Gemini-native 工具调用现在会把内部 `tool_choice` 映射到官方 `toolConfig.functionCallingConfig`，并兼容 Gemini 风格的单日计划字段（如 `exerciseName / time / unit`），避免计划卡存在但名称或时长信息写回丢失
- 当用户这一轮明确要求“待确认计划卡 / proposal / 不要直接写回”时，Gemini-native 首轮会被强制切到 required function calling，避免它只输出正文却不返回结构化 proposal，导致计划卡无法渲染或采纳
- 当用户本轮明确要求“生成计划修改卡 / 计划卡 / 修改卡”时，后端会把该轮视为必须产出结构化 proposal；如果模型首轮只返回文字卡片，后端会追加一次系统纠偏重试，要求它改用 proposal 工具返回可采纳卡片
- DeepSeek `/v1` 兼容链路现在统一不会主动发送 `tool_choice` 给 DeepSeek 家族模型；这是为了兼容 DeepSeek 对 `thinking + tool_choice` 以及部分 `auto/required` 组合的协议限制，改由“proposal 工具按轮暴露 + 结果校验 + 纠偏重试”来保证计划卡场景稳定可用
- 计划 proposal 工具现在只会在用户本轮明确要求“计划卡 / 修改卡 / 调整卡 / 生成新计划 / 改计划”等场景下暴露；普通解释性聊天会回到只读工具与自然回复，避免连续不停生成新卡
- `POST /api/tools/plan/ignore` 已可用；前端点击“忽略”会同步把该 proposal 标记为 `ignored`，后续同会话会回到正常聊天，直到用户再次明确唤起下一张计划卡
- 对于 Gemini 偶尔把“休息日新增整天训练安排”误生成为 `propose_plan_change` 的情况，后端会在空训练日上把这类 `add/replace` proposal 自动升级成 `day_plan_replace`，尽量保证仍能产出可采纳的计划卡
- `GET/PUT /api/model-config` 会读取和保存脱敏后的多供应商模型配置；保存后后端会立即刷新运行时缓存，前台聊天、流式输出和后台任务都会直接使用新配置，不需要重启服务
- `POST /api/model-config/providers/test` 与 `POST /api/model-config/providers/discover-models` 支持在页面内测试连接并拉取远端模型列表
- OpenAI-compatible Provider 的测试连接、模型发现、配置保存与回显都会携带 `wireApi` / `apiPathMode`；新版 DeepSeek bootstrap 默认补成 `https://api.deepseek.com/v1 + chat_completions + append_v1`，而显式把 `base_url` 配到 `/v1` 时，endpoint builder 也会自动避免出现 `/v1/v1/chat/completions`
- OpenAI-compatible 聊天后端同时支持 `chat_completions` 与 `responses` 两种 wire；工具回环会按各自协议补齐 follow-up 消息
- OpenAI-compatible `responses` 模式下，后端现在会发送 Responses API 需要的扁平 `function` tools schema，而不是 `chat_completions` 的嵌套 `function` 结构；这已经过真实中转站的普通工具对话、proposal 卡生成、计划 commit 和后台任务验证
- 如果 OpenAI-compatible 中转站在 `responses` 下返回 SSE 上游异常，或在工具 follow-up 阶段拒绝 `function_call_output` 的 HTTP 续传，运行时会自动把该轮请求降级到 `chat_completions`，避免普通对话可用但 proposal / 后台任务失效；流式场景也会直接切到真正的 `chat_completions` 流式请求，避免先发一轮非流式 fallback 造成重复请求
- `POST /api/model-config/providers/test` 与 `POST /api/model-config/providers/discover-models` 在 OpenAI-compatible provider 下会对瞬时 `502/503/504` 与网络抖动做轻量重试，减少“测试连接失败但聊天其实可用”的假阴性
- 如果本机访问 Gemini 依赖代理，请把 `HTTP_PROXY` / `HTTPS_PROXY` 写入 `backend/.env`；后端启动时会自动同步到运行进程，避免只在某个终端窗口里临时设代理导致 Gemini 连不上
- 保存模型配置时会保留真实 `apiKey`，但返回给前端的是脱敏预览值
- 未配置 API Key 时，除 AI 教练外的大部分本地功能仍可使用
- 不要提交真实 API Key
- `backend/config/model_providers.proxy-e2e.json` 只应保存占位示例，真实中转站 key 请放在本地私有配置中，不要写回仓库工作区

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

OpenAI-compatible 流式 proposal 时序回归：

```powershell
node --test tests/coachBackend.test.js tests/coachComposer.test.js
uv run pytest backend\tests\test_chat_stream.py backend\tests\test_chat_tool_loop.py backend\tests\test_tool_calling.py -q
```

浏览器自动化冒烟：

```powershell
uv run python -m playwright install chromium
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_browser_smoke.py
```

浏览器自动化深度回归：

```powershell
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_commit_full_flow.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_ignore_flow.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_attachment_flow.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_provider_switch.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_stream_fallback.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev -- --host 127.0.0.1" --port 5173 -- uv run python tests\e2e\coach_model_config_flow.py
```

更细的验证记录见 [docs/verification.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification.md)。

这次流式改造的回归重点：

- OpenAI-compatible 主链路在计划卡场景下必须保持“先工具、再流式正文、正文后出卡”
- `responses` 降级到 `chat_completions` 时不能先额外打一轮假的非流式请求，也不能造成重复 assistant 正文
- 前端只在收到 `proposal` 事件后挂出采纳卡，`done` 之前不应把 proposal 误判成已写回计划

## Demo 操作路径

1. 启动 `npm run dev:all`，确认前后端都已启动。
2. 进入“我的档案”，填写基础信息、训练目标和三大项 1RM。
3. 进入“训练计划”，配置一周计划，至少为某一天添加一个动作。
4. 进入“今日日志”，填写体重、热量、睡眠、疲劳度和备注。
5. 进入“AI 教练”，发送训练调整问题，确认后端自动注入当前上下文。
6. 如果 AI 返回结构化建议卡，点击“采纳并更新计划”；新版也支持直接采纳整张“单日训练计划卡”。
7. 返回“训练计划”，确认对应动作或整日训练安排已被更新并持久化。
8. 如需展示扩展能力，可额外演示文件上传、附件回显、历史会话恢复、Markdown 表格渲染与模型设置弹窗。

## 相关文档

- 架构与数据流：[ARCHITECTURE.md](/g:/VSCODE-G/Fitness Agent MVP/ARCHITECTURE.md)
- 后端启动、迁移与接口：[backend/README.md](/g:/VSCODE-G/Fitness Agent MVP/backend/README.md)
- 迭代进度与历史记录：[docs/progress.md](/g:/VSCODE-G/Fitness Agent MVP/docs/progress.md)
- 验证记录：[docs/verification.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification.md)
- 发布前验证计划：[docs/verification_release_plan.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification_release_plan.md)
