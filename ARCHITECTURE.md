# RepMind MVP 架构说明

本文档只描述当前工作区中的真实实现。目标读者是开发者，因此重点放在模块边界、数据流、接口关系、存储结构和兼容层职责。

## 系统总览

RepMind MVP 由前端 React 应用和本地 FastAPI 后端组成。

- 前端负责页面渲染、交互编排、局部缓存和与后端通信
- 后端负责结构化数据持久化、AI 教练上下文组装、工具回环、Provider 适配和文件摘要处理
- SQLite 是主数据源
- `localStorage` 仍然存在，但主要承担缓存、迁移兼容和少量前端恢复状态

当前核心业务闭环如下：

1. 用户在前端维护档案、训练计划和今日日志
2. 前端将结构化数据写入本地后端
3. 用户在 AI 教练页发起对话
4. 后端读取当前状态、会话历史、摘要、记忆和附件摘要，拼装模型请求
5. Provider runtime 请求模型，必要时执行工具调用
6. 后端以 SSE 或普通 JSON 返回正文、建议卡和完成事件
7. 用户确认计划卡后，后端将变更写回 `weekly_plan_day`

## 前端结构

### 应用入口

- [src/App.jsx](/g:/VSCODE-G/Fitness Agent MVP/src/App.jsx)
  - 管理四个主页面：`Profile`、`Plan`、`Today`、`Coach`
  - 应用启动时调用 `loadAppData()` 从后端读取 `profile / weeklyPlan / dailyLog`
  - 同时保留 `localStorage` 缓存，后端不可用时页面仍能展示本地数据
  - 负责把 `profile / weeklyPlan / dailyLog` 的改动异步回写后端
  - 负责 localStorage 首次迁移提示与导入后端入口

### 前端 API 层

- [src/api/backendClient.js](/g:/VSCODE-G/Fitness Agent MVP/src/api/backendClient.js)
  - 普通 REST 接口客户端
  - 负责档案、周计划、今日日志、会话、消息、草稿、文件、模型配置、指标和计划卡提交
  - 是前端非聊天场景的统一后端访问层

- [src/api/coachBackend.js](/g:/VSCODE-G/Fitness Agent MVP/src/api/coachBackend.js)
  - AI 教练聊天专用访问层
  - 负责 `/api/chat/stream` 的 SSE 解析
  - 负责 `/api/chat/reply` 的非流式调用
  - 负责读取 `delta / proposal / suggestion / done / error` 事件并交给页面状态机

- [src/api/appData.js](/g:/VSCODE-G/Fitness Agent MVP/src/api/appData.js)
  - 把前端数据结构映射到后端字段结构
  - 负责 `oneRM <-> oneRm`、`tdee <-> tdeeManual` 等字段转换

- [src/api/deepseek.js](/g:/VSCODE-G/Fitness Agent MVP/src/api/deepseek.js)
  - 历史兼容壳
  - 当前仍存在，但主聊天入口已经不直接依赖它组织业务逻辑

### 主页面职责

- [src/tabs/ProfileTab.jsx](/g:/VSCODE-G/Fitness Agent MVP/src/tabs/ProfileTab.jsx)
  - 负责“我的档案”页的结构化摘要卡、分组表单和折叠式数据管理区
  - 编辑基础档案、训练目标、目标体重和三大项 1RM
  - 通过页面层局部 UI 状态控制数据导入导出面板的展开与收起

- [src/tabs/PlanTab.jsx](/g:/VSCODE-G/Fitness Agent MVP/src/tabs/PlanTab.jsx)
  - 编辑一周训练计划
  - 管理按日训练类型、动作增删改和动作表单状态

- [src/tabs/TodayTab.jsx](/g:/VSCODE-G/Fitness Agent MVP/src/tabs/TodayTab.jsx)
  - 编辑今日日志
  - 展示每日摘要、今日计划和体重趋势图

- [src/tabs/CoachTab.jsx](/g:/VSCODE-G/Fitness Agent MVP/src/tabs/CoachTab.jsx)
  - AI 教练页的页面编排中心
  - 管理会话列表、当前会话、消息列表、流式状态、后台思考状态、草稿、附件和模型选择
  - 通过 `requestCoachReply / requestCoachReplyStream / startBackgroundCoachReply` 驱动聊天链路
  - 负责 proposal 卡确认、忽略、消息元数据合并和会话恢复

### 前端状态与本地缓存

当前浏览器端仍保存以下内容：

- `profile`
- `weeklyPlan`
- `dailyLog`
- `chatHistory`
- 本地迁移完成标记
- 当前活动会话 id
- 后台任务恢复锚点
- 我的档案页“数据管理”折叠状态这类纯展示 UI 状态

这些数据的角色不同：

- `profile / weeklyPlan / dailyLog` 的主数据源是后端 SQLite，本地只做缓存和降级展示
- `chatHistory` 仍保留为前端兼容缓存，但真实会话与消息已由后端 `chat_session / chat_message` 承担
- 活动会话 id、后台任务信息属于纯前端恢复状态，不写入后端业务表

## 后端结构

### 应用入口

- [backend/main.py](/g:/VSCODE-G/Fitness Agent MVP/backend/main.py)
  - 创建 FastAPI 应用
  - 启动时建表、播种默认数据、加载 provider runtime、初始化后台任务 worker
  - 注册以下路由模块：
    - `profile`
    - `weekly_plan`
    - `daily_log`
    - `drafts`
    - `chat`
    - `files`
    - `memory`
    - `models`
    - `model_config`
    - `metrics`
    - `tools`
    - `migrate`

### API 层

- `backend/api/profile.py`
  - `GET /api/profile`
  - `PUT /api/profile`

- `backend/api/weekly_plan.py`
  - `GET /api/weekly-plan`
  - `PUT /api/weekly-plan`
  - `POST /api/weekly-plan/adopt` 兼容旧采纳协议

- `backend/api/daily_log.py`
  - `GET /api/daily-log`
  - `PUT /api/daily-log/{date}`

- `backend/api/chat.py`
  - 聊天主入口
  - 负责请求归一、会话解析、聊天流式/非流式返回、后台任务提交、消息落库、usage 记录和上下文调试

- `backend/api/drafts.py`
  - 管理会话级草稿、模型、thinking 和附件 id

- `backend/api/files.py`
  - 负责上传文件保存、去重、摘要解析、文件列表查询和删除

- `backend/api/memory.py`
  - 提供 memory item 检索和候选确认/忽略接口

- `backend/api/models.py`
  - 返回当前启用模型列表和旧 UI 兼容的顶层 thinking 信息

- `backend/api/model_config.py`
  - 读取、保存、测试和发现 provider 配置

- `backend/api/metrics.py`
  - 返回每日指标摘要

- `backend/api/tools.py`
  - 负责 proposal 生成、commit 和 ignore

- `backend/api/migrate.py`
  - 负责把浏览器 localStorage 快照导入后端

### Agent 层

- `backend/agent/context_manager.py`
  - 定义 token 预算
  - 负责 prompt 拼装
  - 负责会话摘要压缩与消息预算裁剪

- `backend/agent/chat_session.py`
  - AI 教练主编排层
  - 负责从数据库读取 profile、weekly plan、daily logs、summary、memory、knowledge、recent messages、file summary
  - 负责构建 Agent request
  - 负责 provider 绑定、运行时协议转换、OpenAI-compatible / Gemini / fallback 客户端接线
  - 负责统一工具回环入口

- `backend/agent/tool_calling.py`
  - 定义工具注册表、工具参数模型和工具处理函数

- `backend/agent/tool_loop.py`
  - 负责多轮工具回环执行
  - 记录工具调用日志
  - 控制 proposal 工具停止点

- `backend/agent/adopt_plan.py`
  - 负责构建 proposal、commit proposal、ignore proposal

- `backend/agent/response_parser.py`
  - 负责从模型回复中解析纯文本与 suggestion

- `backend/agent/memory.py`
  - 负责 memory 检索逻辑

- `backend/agent/usage_ledger.py`
  - 负责 usage 记录标准化与汇总

- `backend/agent/background_worker.py`
  - 负责离页后台思考任务

### Provider 运行时

- `backend/model_config/*`
  - 管理 provider 配置文件、运行时缓存和 `provider::remoteModel` 解析

- `backend/providers/openai_compatible.py`
  - OpenAI-compatible 协议适配层

- `backend/providers/openai_compatible_client.py`
  - OpenAI-compatible HTTP 细节封装

- `backend/providers/gemini_native.py`
  - Gemini-native 协议适配层

- `backend/providers/gemini_client.py`
  - Gemini-native HTTP 客户端

### 存储与文件层

- `backend/db/models.py`
  - 定义所有 SQLite 表结构

- `backend/db/database.py`
  - 管理数据库连接、session 和建表

- `backend/db/seed.py`
  - 初始化空白档案与默认周计划

- `backend/files/uploader.py`
  - 上传文件的命名、路径和哈希处理

- `backend/files/parsers/*`
  - 负责 Markdown、DOCX、Excel、图片摘要解析

## 数据流

### 档案、周计划、今日日志

1. 前端页面编辑结构化数据
2. `src/api/appData.js` 做字段映射
3. `src/api/backendClient.js` 调用后端 CRUD 接口
4. 后端写入 SQLite
5. 前端同时保留 localStorage 缓存

### AI 教练对话

1. `CoachTab` 收集 `userInput / model / thinking / fileIds / sessionId`
2. `src/api/coachBackend.js` 发起 `/api/chat/stream` 或 `/api/chat/reply`
3. `backend/api/chat.py` 归一新旧请求体
4. `backend/agent/chat_session.py` 读取当前会话相关数据
5. `PromptAssembler` 拼装消息列表
6. 运行时根据 `modelRef` 绑定具体 provider client
7. 如果模型请求工具，`ToolLoopOrchestrator` 执行工具回环
8. 后端输出：
   - 流式：`delta -> proposal? -> suggestion? -> done`
   - 非流式：`{ text, suggestion, proposal }`
9. 成功完成后写入 `chat_message`，必要时写入 `usage_record` 和 `tool_call_log`

### 计划卡写回

1. 模型返回待确认 proposal 卡
2. 前端点击采纳
3. `backendClient.commitPlanChange()` 调用 `POST /api/tools/plan/commit`
4. 后端校验 proposal 并写回 `weekly_plan_day`
5. 同步把相关 assistant 消息中的 suggestion 状态更新为 `committed`

## 存储结构

当前主数据源是 SQLite。关键表如下：

- `profile`
  - 用户档案、三大项 1RM、训练目标、目标体重、备注

- `weekly_plan_day`
  - 一周七天的训练类型与动作数组

- `daily_log`
  - 某日体重、热量、蛋白质、睡眠、疲劳、步数、训练完成情况、备注和手动 TDEE

- `chat_session`
  - 会话元数据，如标题、创建时间、更新时间

- `chat_message`
  - 会话消息，包含 `role`、`content`、`suggestion`、`attachments`

- `chat_session_summary`
  - 长对话摘要

- `memory_item`
  - 长期记忆

- `knowledge_item`
  - 外部资料或上传文件提炼出的知识文本

- `uploaded_file`
  - 上传文件元数据与摘要

- `coach_draft`
  - 会话草稿、选中模型、thinking 和附件 id

- `tool_call_log`
  - 工具调用审计日志

- `usage_record`
  - 模型使用量记录

## AI 教练链路

当前 AI 教练是后端编排，而不是前端直接拼 prompt 调模型。

### 输入

前端发送：

- `sessionId`
- `userInput`
- `model`
- `thinking`
- `fileIds`

兼容路径仍支持直接传 `messages`，但当前主入口优先使用 `userInput` 契约。

### 上下文组装

后端会按当前实现读取：

- `profile`
- `weekly_plan`
- `daily_logs`
- `memory_item`
- `knowledge_item`
- `chat_session_summary`
- `chat_message`
- `uploaded_file` 摘要

然后拼成模型请求消息。这个过程在后端完成，前端不再负责 system prompt 编排。

### Provider 选路

后端通过 `provider::remoteModel` 解析具体 provider 和 remote model id。

当前支持：

- OpenAI-compatible runtime
- Gemini-native runtime

当 provider runtime 缺失或不可用时，可以回退到 `DeepSeekClient`。

### 工具回环

当前工具包括：

- 读取档案
- 读取周计划
- 读取指定日期日志
- 计算轻量指标
- 搜索记忆
- 读取上传文件摘要
- 生成计划修改 proposal
- 生成单日计划替换 proposal

模型需要工具时，后端会执行工具并将结果继续回灌给模型，而不是把工具逻辑留给前端。

### 输出

流式接口使用 SSE，前端消费以下事件：

- `delta`
- `proposal`
- `suggestion`
- `tool_status`
- `done`
- `error`

非流式接口返回：

- `text`
- `suggestion`
- `proposal`

### 落库

只有一轮对话完整成功后，后端才会统一落库：

- `chat_message`
- `tool_call_log`
- `usage_record`

这样可以避免半截 assistant 消息污染会话历史。

## 当前兼容层

以下内容属于当前代码的一部分，但它们的角色是兼容壳或兜底，不是新的主设计：

- `src/api/deepseek.js`
  - 前端旧聊天适配壳

- `POST /api/weekly-plan/adopt`
  - 旧版按 `day + changes` 直接采纳的接口
  - 当前标准写回入口是 `POST /api/tools/plan/commit`

- 聊天 `messages` 旧契约
  - 当前主契约是 `userInput + sessionId + model + thinking + fileIds`
  - 旧 `messages` 结构仍被后端接受，用于兼容测试或旧调用点

- `backend/agent/deepseek_client.py`
  - 当前仍保留为 fallback 客户端
  - 正常情况下，主链路优先走 provider runtime

这些兼容层仍需在架构认知里保留，因为它们会影响当前运行行为和测试路径。
