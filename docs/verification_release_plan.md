# RepMind 开源发布前全量测试验证计划

## 1. 目标

本文档定义 RepMind 在“课程 MVP 可演示”之外，进一步达到“可稳定开源给社区试用”的发布前验证标准。

按本文档执行并全部通过后，当前版本应满足以下目标：

- 核心闭环稳定可用：档案 -> 训练计划 -> 今日日志 -> AI 教练 -> 结构化建议卡 -> 用户确认 -> 写回计划
- AI 教练对话、工具调用、proposal 生成、commit/ignore、历史恢复与后台任务具备稳定表现
- 多 provider 路径具备一致的可用性与错误恢复能力
- 真实用户可在本地完成安装、启动、配置与使用，不依赖隐性开发环境知识
- 关键失败场景有明确提示、可恢复路径和自动化证据

## 2. 适用范围

本计划覆盖以下模块：

- 前端应用壳层与四个主页面
- 本地数据与 SQLite 持久化
- 训练计划编辑、展示与写回
- AI 教练会话、流式输出、非流式回退、后台任务
- Agent 上下文拼装、工具调用与 proposal 闭环
- 文件上传与摘要注入
- 模型配置、provider 路由、多协议聊天运行时
- 浏览器自动化验收、稳定性验证与发布前人工验收

不在本轮开源准入目标内的内容：

- 云同步、多账号系统、后端高并发压测
- 远端向量知识库与复杂 OCR
- 移动端原生适配
- 社区运营、CI/CD 平台化发布流程

## 3. 发布准入标准

只有同时满足以下条件，版本才可对外开源试用：

1. 前端全量自动化测试通过
2. 后端全量自动化测试通过
3. 生产构建通过
4. 浏览器自动化核心链路通过
5. AI 教练三条主路径通过专项验证
6. 至少完成一轮完整人工长流程验收
7. 无 `P0`、无 `P1` 缺陷
8. README、ARCHITECTURE、验证文档与实际行为一致

缺陷等级定义：

- `P0`：数据写错、计划误改、消息丢失、会话错乱、无法启动
- `P1`：AI 主链路不稳定、proposal 不可采纳、模型配置不可用、严重 UI 假死
- `P2`：局部体验不佳、提示不清、边界场景不优雅但有替代路径
- `P3`：样式细节、文案小问题、非关键易用性问题

发布前必须满足：

- `P0 = 0`
- `P1 = 0`
- `P2` 仅允许少量已知问题，且有文档记录

## 4. 测试环境矩阵

至少覆盖以下环境矩阵：

### 4.1 Provider 与协议矩阵

- DeepSeek 主路径：`openai_compatible + chat_completions`
- OpenAI-compatible Responses 路径：`openai_compatible + responses`
- Gemini Native 路径：`gemini_native`
- Fallback 路径：provider 缺失、provider 凭据无效、运行时未初始化

### 4.2 数据状态矩阵

- 首次启动空数据库
- 已有完整档案、周计划、今日日志与历史会话
- 只有基础资料，无日志、无计划卡历史
- 存在旧 localStorage 与新 SQLite 并存状态

### 4.3 网络与运行状态矩阵

- 正常网络
- 慢网或 provider 响应较慢
- `stream` 失败后 `reply` 回退
- provider 瞬时 `401/403/5xx`
- 页面切换、失焦、后台 pending 恢复

## 5. 执行顺序

建议严格按以下顺序执行：

1. 环境与安装验证
2. 前端全量自动化测试
3. 后端全量自动化测试
4. AI 教练与工具调用专项测试
5. 浏览器自动化冒烟测试
6. 浏览器自动化深度流程测试
7. 稳定性与故障恢复测试
8. 人工长流程验收
9. 缺陷修复回归
10. 发布前文档一致性核对

## 6. 分层测试计划

### 6.1 环境与工程可用性

目标：确认仓库可安装、可启动、可构建、可最小配置运行。

必须验证：

- `npm install` 正常
- `uv sync` 正常
- `npm run dev:all` 能同时启动前后端
- `GET /api/health` 正常
- `npm run build` 成功
- `.env.example` 与 `backend/.env.example` 可直接作为首次配置参考
- 不配置 AI Key 时，非 AI 页面仍可使用，AI 页面给出明确错误而不是崩溃
- 空数据库首次启动可自动建表、生成默认数据并正常打开页面

建议命令：

```powershell
npm install
uv sync
npm run dev:all
npm run build
```

通过标准：

- 无启动阻塞
- 无构建失败
- 无必须依赖本地隐性配置的步骤

### 6.2 前端单元与状态层

目标：验证视图模型、页面状态、卡片行为、编辑逻辑与输入保护稳定。

必须执行：

```powershell
npm test
```

重点关注：

- `tests/coach*.test.js`
- `tests/adopt*.test.js`
- `tests/chat*.test.js`
- `tests/weeklyPlan*.test.js`
- `tests/dailyLog.test.js`
- `tests/prompt*.test.js`
- `tests/modelConfigView.test.js`
- `tests/messageAttachmentCard.test.js`
- `tests/markdownMessage.test.js`

必须覆盖的能力：

- 档案不完整时阻断发送
- 流式输出与非流式回退展示正确
- proposal 卡片渲染、采纳、忽略、隐藏逻辑正确
- 历史会话切换不串消息
- 模型切换、draft 恢复、附件展示稳定
- 今日指标展示与 prompt 注入口径一致
- 训练计划编辑器在空值、非法值、模式切换时不崩溃

通过标准：

- 前端全量测试通过
- 无明显 flaky case
- 失败可以定位到明确模块

### 6.3 后端 API 与数据层

目标：验证 CRUD、迁移、proposal 写回、配置保存、文件处理、错误返回与事务安全。

建议执行：

```powershell
uv run pytest backend\tests -q
```

重点关注：

- `test_crud_api.py`
- `test_migrate.py`
- `test_models_api.py`
- `test_model_config_api.py`
- `test_file_upload.py`
- `test_metrics_api.py`
- `test_drafts_api.py`
- `test_chat_store.py`
- `test_adopt_plan.py`

必须覆盖：

- `profile / weekly-plan / daily-log` CRUD
- localStorage 迁移
- draft 保存与恢复
- 文件上传、读取、删除
- 指标接口在空日志、休息日、训练日下都正常
- `commit` 成功写库、失败不写脏数据
- legacy `/api/weekly-plan/adopt` 与 proposal commit 结果一致
- 会话创建、默认会话、新建会话、删除会话正常
- provider 配置读取、保存、测试连接、discover models 正常

通过标准：

- 后端全量测试通过
- 失败场景不污染数据库
- 错误返回格式一致且可读

### 6.4 Agent、上下文与工具调用专项

目标：验证 AI 教练最关键的编排稳定性，尤其是上下文、tool loop、proposal 安全性与 provider fallback。

建议执行的重点测试：

```powershell
uv run pytest backend\tests\test_chat_stream.py backend\tests\test_background_worker.py backend\tests\test_chat_tool_loop.py backend\tests\test_tool_loop_orchestrator.py backend\tests\test_tool_calling.py backend\tests\test_chat_session_context.py backend\tests\test_chat_files_context.py backend\tests\test_context_manager.py backend\tests\test_summary_compressor.py backend\tests\test_gemini_client.py backend\tests\test_openai_compatible_provider.py backend\tests\test_provider_runtime.py backend\tests\test_deepseek_client.py -q
```

必须覆盖：

- `profile / weeklyPlan / dailyLog / memory / summary / recent messages / file summaries` 注入正确
- 普通问答与计划卡请求的工具暴露策略正确
- proposal 生成不写库，只有 commit 才写库
- `pending / committed / ignored` 状态在消息历史与上下文中一致
- `chat_completions`、`responses`、Gemini `functionCall -> functionResponse` 回环正确
- `responses -> chat_completions` 自动降级正确，且不重复执行工具或重复落库
- Gemini 在必须产出结构化 proposal 时能正确返回卡片
- 背景任务 pending/running/succeeded/failed 行为正确
- provider-aware 错误文案准确，不把所有异常都错误归因到 DeepSeek

通过标准：

- 工具调用相关测试全部通过
- 无“未确认 proposal 提前写回计划”风险
- 无“卡片展示状态与真实状态不一致”风险

### 6.5 浏览器自动化冒烟

目标：验证真实页面主交互未被回归破坏。

现有脚本：

- `tests/e2e/coach_browser_smoke.py`
- `tests/e2e/coach_session_history.py`
- `tests/e2e/coach_pending_restore.py`

建议执行：

```powershell
uv run python -m playwright install chromium
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\coach_browser_smoke.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\coach_session_history.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\coach_pending_restore.py
```

必须确认：

- AI 教练页可以打开
- 会话列表渲染正常
- 新建对话可用
- 历史会话切换正常
- pending 恢复正确渲染“思考中”
- proposal 卡片可见、可采纳

通过标准：

- 所有冒烟脚本通过
- 无明显 flaky

### 6.6 浏览器自动化深度流程

目标：从真实使用路径验证端到端稳定性。

建议新增并执行以下场景：

1. `coach_commit_full_flow`
- 填写档案
- 配置训练计划
- 录入今日日志
- 发送训练调整问题
- 生成 proposal
- 采纳并确认计划页已写回

2. `coach_ignore_flow`
- 生成卡片
- 点击忽略
- 同会话内 proposal 状态更新为 ignored
- 后续聊天恢复正常

3. `coach_provider_switch`
- DeepSeek / OpenAI-compatible responses / Gemini 之间切换
- 切换后继续发送消息
- 不串模型、不串 draft

4. `coach_attachment_flow`
- 上传 md/docx/xlsx/image 至少各一类
- 附件卡片显示正常
- AI 上下文能读取摘要
- 删除附件后状态同步

5. `coach_stream_fallback`
- 模拟 stream 失败
- 自动回退 reply
- 不重复生成 assistant，不重复落库

6. `coach_model_config_flow`
- 打开模型设置
- 测试连接
- discover models
- 保存配置
- 不重启直接生效

通过标准：

- 全部深度脚本通过
- 失败可复现、可定位
- 无重复写消息、重复写计划、UI 锁死等问题

### 6.7 稳定性与故障恢复测试

目标：验证异常情况下系统仍然可恢复、可解释、可继续使用。

必须专项验证：

- provider `401/403/5xx` 时 UI 有明确错误提示
- `responses` 路径 SSE 上游失败时自动回退
- 后台任务失败时不写脏 assistant
- 页面失焦后 background task 恢复正常
- 文件解析失败时不影响聊天页正常打开
- 空日志、空计划、空 memory、空文件时 AI 教练仍可工作
- 长会话压缩后 proposal 状态仍能被上下文识别

通过标准：

- 所有错误都具备用户可理解提示
- 用户无需刷新数据库或重置状态即可继续使用

## 7. AI 教练重点高风险场景清单

以下场景必须单独打勾确认：

- 未确认 proposal 绝不能写回计划
- 已 commit proposal 在历史与上下文中必须显示为已处理
- ignored proposal 不能在后续轮次继续被当作 pending
- OpenAI responses fallback 不能重复执行工具或重复落库
- Gemini 不能只返回正文而不返回结构化 proposal
- DeepSeek 特殊协议限制下 proposal 仍能稳定产出
- pending 背景任务恢复时不能丢当前 user 消息
- 流式失败回退后不能多生成一条 assistant
- 切换 provider/model 后旧 draft 不能错绑到新模型
- 文件上传或解析失败不能拖垮会话页
- proposal 卡采纳后计划页显示必须立即与后端结果一致

## 8. 人工验收清单

自动化通过后，必须再做一轮人工长流程验收。

### 8.1 新用户首次使用

- 从空状态进入应用
- 完成档案填写
- 新建周计划
- 录入今日日志
- 进入 AI 教练发问
- 采纳建议卡并返回计划页确认

关注点：

- 是否需要猜测下一步做什么
- 是否存在明显术语门槛
- 是否能在 5 分钟内完成闭环

### 8.2 老用户连续使用

- 打开已有数据
- 切换历史会话
- 追问同一训练日计划
- 查看旧 proposal 状态
- 再次发起新的计划卡请求

关注点：

- 是否串消息
- 是否误解旧 proposal 状态
- 是否在切换模型后失去当前上下文

### 8.3 AI 教练使用体验

重点关注：

- 发送动作是否明确
- “思考中”反馈是否合理
- 错误提示是否人能理解
- proposal 卡是否易懂
- 采纳与忽略是否给人足够信心
- 采纳后用户是否能明确知道“已经真实写回”

### 8.4 训练计划体验

重点关注：

- 新增、编辑、删除动作是否顺手
- 空状态与 rest day 展示是否清楚
- 百分比重量与实际公斤数是否可信
- 整日替换卡与字段 patch 卡是否都能被理解

### 8.5 模型配置体验

重点关注：

- 新增 provider 是否容易
- 测试连接、discover models 是否清楚
- 保存后是否即时生效
- 失败信息能否指导用户修正

人工验收通过标准：

- 非开发者也能完成核心流程
- 不需要理解内部实现即可做出正确操作
- 没有“我一点击就可能写坏计划”的心理负担

## 9. 建议执行命令基线

```powershell
npm test
npm run build
uv run pytest backend\tests -q
uv run python -m playwright install chromium
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\coach_browser_smoke.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\coach_session_history.py
uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\coach_pending_restore.py
```

如需达到发布前标准，建议补齐 6.6 中定义的新浏览器深度脚本后再执行完整回归。

## 10. 验收输出物要求

每轮正式验证建议保留以下证据：

- 测试命令与结果摘要
- 失败用例截图或日志
- 浏览器自动化截图或 HTML 报告
- 关键 proposal/commit 成功路径记录
- 手工验收 checklist
- 已知问题列表与优先级

建议把每轮正式验证结论追加记录到：

- `docs/verification.md`

若是发布前总验收，可额外输出一份独立报告，例如：

- `docs/verification_release_report.md`

## 11. 当前阶段建议

结合当前仓库现状，RepMind 已具备较好的单测、后端测试与基础浏览器冒烟能力，但距离“稳定开源试用”还需补齐以下两类内容：

1. 浏览器自动化深度流程
- commit 全流程
- ignore 流程
- provider 切换
- 附件上传
- stream fallback
- 模型配置保存与即时生效

2. AI 教练系统级稳定性验证
- proposal 状态一致性
- tool loop 多协议一致性
- fallback 不重复执行
- 背景任务恢复与消息去重

完成这两部分后，再做一轮全量回归，才更接近真正可对外开源的稳定标准。
