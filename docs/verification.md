# RepMind MVP 最终验收记录

## 1. 验收范围

本文档记录 RepMind MVP 在 Sprint 6 完成后的最终验收结果，覆盖：

- 自动化单元测试与构建验证
- Task 7.1 核心成功路径验收
- Task 7.2 边界与失败场景验收

本轮结果分为两类证据：

- 代码级证据：`node --test`、`npm test`、`npm run build`
- 浏览器级证据：基于 Playwright 的页面验收

说明：

- 浏览器级验收使用本地 `vite preview` 页面进行。
- 为了稳定验证 AI 卡片、降级与错误提示，页面级 AI 返回采用浏览器 `fetch` mock。
- 真实 DeepSeek 路径已单独探测过，能够返回正常文本回复；但结构化 JSON 返回不稳定，因此最终验收对“采纳卡片是否出现”采用可重复的 mock 方案。

## 2. 本轮执行环境

- 日期：2026-05-30
- 预览地址：`http://127.0.0.1:4177`
- 浏览器验收工具：Playwright（Python 虚拟环境 `.venv-qa`）

## 3. 自动化验证结果

### 3.1 前置校验相关测试

- 命令：`node --test tests/coachGuard.test.js tests/coachChat.test.js`
- 结果：`5/5` 通过

覆盖点：

- 档案缺少关键字段时返回阻断提示
- 档案满足最小上下文要求时允许继续
- AI 请求构建与流式/普通回复路径未被回归破坏

### 3.2 全量测试

- 命令：`npm test`
- 结果：`44/44` 通过，`0` 失败

重点覆盖：

- 本地存储读写
- 今日日志写回
- Prompt 构建
- AI 响应解析
- 建议采纳写回
- 体重趋势图数据整理
- 数据导入导出
- AI 流式输出
- 档案未完善时的 AI 发送拦截

### 3.3 生产构建

- 命令：`npm run build`
- 结果：构建成功

## 4. Task 7.1 核心成功路径验收

### 4.1 验收路径

按任务要求构造并验证以下闭环：

1. 设定档案：当前体重 `75kg`、深蹲 `1RM 120kg`、目标为“增肌减脂”
2. 设定周一训练计划：深蹲 `75% x 4 x 6`
3. 写入今日日志：体重 `82kg`、热量 `2100kcal`、疲劳度 `3`、备注“深蹲第3组没完成”
4. 进入 AI 教练，发送“最近疲劳度有点高，要不要调整计划”
5. 页面出现 AI 回复与“采纳并更新计划”卡片
6. 点击采纳
7. 返回训练计划页确认周一深蹲计划已更新

### 4.2 实际结果

浏览器级结果如下：

- AI 请求先走流式，再自动降级到普通回复，实际 `fetch` 次数为 `2`
- 页面成功渲染“采纳并更新计划”按钮
- 点击采纳后，`fitloop_weeklyPlan` 中 `Monday -> 深蹲 -> pct` 从 `0.75` 更新为 `0.7`
- 返回训练计划页并展开 Monday 后，可见 `70% -> 84kg`
- 页面显示成功反馈文案，核心闭环跑通

### 4.3 结论

Task 7.1 通过。  
RepMind 已具备“日志 -> AI 建议 -> 采纳 -> 写回训练计划”的完整演示闭环。

## 5. Task 7.2 边界与失败场景验收

### 5.1 休息日 prompt 中训练消耗为 0，固定 kg 与 TDEE 正常

验收方式：

- 浏览器中打开 AI 教练页
- 展开“当前上下文预览”
- 使用“今日为 rest、周计划中含固定重量动作、dailyLog 为空”的状态验证

实际结果：

- 预览文本中出现 `训练容量估算消耗：0kcal`
- 固定重量动作正常显示 `80kg`
- `TDEE` 正常展示
- 空日志场景下显示“暂无记录 / 未记录”兜底文案
- AI 输入框正常可见，页面未崩溃

结论：通过。

### 5.2 新用户没有日志时，AI 教练不崩溃

验收方式：

- 与 5.1 共用空 `dailyLog` 状态
- 重点检查 AI 教练页是否仍能正常打开与展示上下文预览

实际结果：

- 页面正常渲染
- AI 输入区可用
- Prompt 预览存在空数据兜底文案

结论：通过。

### 5.3 Profile 未填写时，不发送 AI 请求

验收方式：

- 档案中清空姓名、当前体重、训练目标、深蹲 1RM
- 进入 AI 教练页输入问题并点击发送

实际结果：

- 页面显示“请先完善档案...”阻断提示
- 浏览器中捕获到的 AI 请求次数为 `0`
- `fitloop_chatHistory` 长度保持为 `0`

结论：通过。

### 5.4 API Key 错误时，页面显示错误提示

验收方式：

- 浏览器层 mock DeepSeek 返回 `401`

实际结果：

- 页面出现错误提示
- 提示内容包含 `401 / 无效 / 缺失` 语义
- 请求次数为 `2`，符合“先流式、后普通降级”的当前实现

补充说明：

- “缺失 API Key”场景已由 `tests/deepseek.test.js` 覆盖
- 页面级最终验收这里记录的是“错误 Key / 401”场景

结论：通过。

### 5.5 AI 返回纯文本时，不渲染采纳卡片

验收方式：

- 浏览器层 mock AI 普通文本回复，不返回 `---JSON---`

实际结果：

- 页面能正常显示 AI 文本回复
- 未出现“采纳并更新计划”按钮
- 请求次数为 `2`，符合流式失败后普通回复降级路径

结论：通过。

## 6. 最终结论

截至 2026-05-30，RepMind V0 已通过当前 MVP 范围内的最终验收：

- 核心成功路径可完整演示
- 关键边界与失败场景有明确证据
- 自动化测试 `44/44` 通过
- 生产构建成功

当前版本已经适合用于课程展示、课堂 demo 和验收说明。
## 7. Task 6.4 固定样本稳定性验收

### 7.1 验收目标

- 固定一组档案、周计划与今日日志，验证 `buildDailyMetricsSummary()` 关键数值稳定
- 验证 Today 页展示模型与 prompt 注入使用同一份核心指标口径
- 覆盖 `TDEE / 热量状态 / 蛋白质状态 / 恢复数据`

### 7.2 固定样本

- 参考日期：`2026-05-25`（Monday）
- 档案：男，29 岁，175cm，70kg
- 今日计划：深蹲 `140 x 80% x 5 x 5`，卧推 `100 x 70% x 4 x 6`
- 今日日志：`2500kcal`、蛋白质 `105g`、睡眠 `7.2h`、疲劳 `3`

### 7.3 自动化验收

- 命令：`node --test tests/task64MetricsStability.test.js`
- 结果：`1/1` 通过

关键断言：

- `tdee = 2433`
- `calorie_status = balanced`
- `protein_status = low`
- `sleep_hours = 7.2`
- `fatigue_level = 3`
- Today 页 `panelModel.source.summary` 与 prompt 中 `structured_metrics` 完整对齐

## 8. 2026-06-03 深度浏览器验证补充

### 8.1 验收目标

- 为开源发布前验证计划补齐 AI 教练深度浏览器回归脚本
- 覆盖 commit、ignore、附件上传、provider 切换、stream fallback、模型设置保存后即时生效
- 保持全部脚本都能通过浏览器端 route mock 稳定复现

### 8.2 新增脚本

- `tests/e2e/coach_commit_full_flow.py`
- `tests/e2e/coach_ignore_flow.py`
- `tests/e2e/coach_attachment_flow.py`
- `tests/e2e/coach_provider_switch.py`
- `tests/e2e/coach_stream_fallback.py`
- `tests/e2e/coach_model_config_flow.py`

### 8.3 自动化验收命令

- 命令：`uv run python -m py_compile tests/e2e/coach_commit_full_flow.py tests/e2e/coach_ignore_flow.py tests/e2e/coach_attachment_flow.py tests/e2e/coach_provider_switch.py tests/e2e/coach_stream_fallback.py tests/e2e/coach_model_config_flow.py`
- 结果：通过

- 命令：`uv run python tests/e2e/coach_commit_full_flow.py`
- 结果：通过

- 命令：`uv run python tests/e2e/coach_ignore_flow.py`
- 结果：通过

- 命令：`uv run python tests/e2e/coach_attachment_flow.py`
- 结果：通过

- 命令：`uv run python tests/e2e/coach_provider_switch.py`
- 结果：通过

- 命令：`uv run python tests/e2e/coach_stream_fallback.py`
- 结果：通过

- 命令：`uv run python tests/e2e/coach_model_config_flow.py`
- 结果：通过

### 8.4 本轮覆盖点

- proposal 卡生成后，commit 前计划页保持旧内容，commit 后才显示新计划
- ignore 会调用 `/api/tools/plan/ignore`，且忽略后旧卡片不会继续以待处理状态出现
- 附件上传后首轮消息会携带 `fileIds`，移除附件后下一轮不再携带旧附件
- DeepSeek / Responses / Gemini 三类 `modelRef` 切换后，真实发送请求会跟随切换
- `/api/chat/stream` 失败后会回退到 `/api/chat/reply`，且不会重复生成 assistant 消息
- 模型设置弹窗保存后，新的默认模型会立即体现在模型选择器和后续聊天请求里

### 8.5 结论

截至 2026-06-03，AI 教练浏览器级自动化验证已经从“冒烟”扩展到“深度流程回归”。  
当前脚本集已能稳定覆盖开源发布前验证计划中的 6 条高风险前端链路。
