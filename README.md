# RepMind MVP

RepMind MVP 是一个本地运行的 AI 健身教练与训练记录应用。当前版本采用前端 React + 本地 FastAPI + SQLite 的结构，围绕一条可演示、可验证的核心闭环工作：

用户档案 -> 一周训练计划 -> 今日日志 -> AI 教练读取上下文 -> 返回建议或计划卡 -> 用户确认后写回训练计划

## 当前能力

- 维护用户档案、训练目标和三大项 1RM
- 我的档案页提供浅色渐变头图、单列信息流摘要区、结构化摘要卡、分组表单和折叠式数据管理区，避免顶部信息块在常见桌面宽度下互相挤压
- 维护一周训练计划，并支持按日编辑训练类型与动作；日期列头部会直接显示动作统计，减少重复标签和竖向空白
- 手动计划模式下可直接编辑头部周次；周期计划模式下周次由当前周期推进状态决定，保持只读展示
- 训练计划页支持同一天内动作卡片拖拽排序，放手即保存，并在刷新后保留最新顺序
- 支持通过“计划设置”分别管理非周期计划与周期计划，并显式切换当前生效来源
- 周期计划模式首版内置 `Candito 6 周`、`Madcow 5x5`、`德州计划`，并支持第一版自定义力量周期计划
- 自定义力量周期计划默认在计划设置页收起，通过弹窗填写主项 TM、开始日期、周数，以及按周维护基础 day type 结构
- 周期计划支持手动创建、启用当前周期、生成下一周、确认推进和停止周期
- 维护今日日志，使用记录优先的结构化工作台录入体重、热量、蛋白质、睡眠、疲劳、步数、训练备注和手动 TDEE
- 档案、今日日志、训练计划、周期设置和自定义力量周期计划中的关键数值字段统一接入共享数值范围约束，输入阶段会即时拦截明显异常值并显示字段级提示
- 档案、今日日志、动作保存、周期 payload 和自定义力量周期 payload 在写入前都会再次做同源数值复核，避免异常值绕过 UI 落库
- 今日日志和 AI 教练都会读取当前激活计划来源的有效周计划
- 根据今日计划和日志生成每日摘要与体重趋势视图
- 提供 AI 教练对话页，支持多会话、流式回复、草稿恢复、附件上传和 Markdown 消息渲染
- AI 教练会在后端自动读取档案、周计划、今日日志、近期对话、会话摘要、记忆和文件摘要
- 当模型返回结构化计划建议时，前端会展示待确认的计划卡，用户可确认写回或忽略
- 周期计划激活时，计划卡写回当前周期周快照的覆盖层；非周期计划时仍写回手动周计划
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

正常链路优先走 provider runtime；当运行时不可用时，后端仍保留 `DeepSeekClient` 作为 fallback。

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
3. 在“训练计划”中直接编辑手动周计划，或点击“计划设置”进入周期计划配置
4. 如果使用周期计划，可以选择预制模板并填写 `1RM / TM / 开始日期 / 训练日`，或切换到“自定义力量周期计划”填写名称、开始日期、周数、主项 TM 和周结构
5. 创建后再显式启用当前周期计划
6. 在“今日日志”填写体重、热量、睡眠、疲劳和备注，确认今日计划摘要与当前激活来源一致
7. 尝试输入越界数值，例如离谱体重、负数 TM 或非法 RPE，确认页面会即时拦截并给出字段级范围提示
8. 进入“AI 教练”发送问题，观察流式回复和上下文驱动的建议
9. 如果出现计划建议卡，点击确认写回
10. 返回“训练计划”确认对应日程已经更新；周期模式下可继续手动生成或确认下一周

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
