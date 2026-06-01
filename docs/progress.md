# RepMind MVP 迭代与进度记录

本文档承接 README 中迁出的阶段性更新、历史任务说明和进度索引。README 现在只保留项目概览与使用说明；如果你想了解项目是如何一步步演进到当前状态的，从这里开始看。

## 当前进度概览

当前仓库已经完成以下主线能力：

- 基础训练记录闭环：用户档案、周计划、今日日志
- AI 教练闭环：上下文注入、建议生成、结构化建议卡、用户确认后写回训练计划
- 本地后端化：SQLite 持久化、聊天会话落库、SSE 流式代理、离页后台思考
- Agent 能力增强：上下文编排、摘要压缩、memory、tool calls、usage 观测
- 文件体验增强：本地上传、摘要注入、草稿持久化、消息附件回显
- 展示体验增强：真实会话历史、安全 Markdown、表格与分割线渲染

## 当前已实现能力

- 维护用户档案、训练目标与三大项 1RM
- 维护一周训练计划
- 录入今日日志：体重、热量、蛋白质、睡眠、疲劳度、训练备注
- AI 发送前由后端自动读取并注入最新档案、计划、日志、摘要、长期记忆和必要工具结果
- AI 教练可上传并附加图片、Excel、DOCX、Markdown/TXT 文件，后端只注入摘要与 `fileId`
- AI 教练支持模型与 thinking 配置
- AI 回复支持安全 Markdown 展示，标题、列表、代码块、表格和分割线可正常渲染
- AI 输入草稿、模型、thinking 和附件 id 可保存到后端草稿
- 已发送的用户消息支持附件卡片回显，刷新和切换历史会话后仍可恢复
- AI 教练历史侧栏来自后端真实会话，支持切换、恢复和新建对话
- 离页后台思考可在回页后补齐结果
- 结构化建议卡支持采纳与忽略，采纳后通过后端写回训练计划

## 详细阶段文档索引

### V0 / V1 基础版本

- [task/V0/长期推进表.md](/g:/VSCODE-G/Fitness Agent MVP/task/V0/长期推进表.md)
- [task/V0/RepMind V0 开发完成记录.md](/g:/VSCODE-G/Fitness Agent MVP/task/V0/RepMind V0 开发完成记录.md)
- [task/V1/RepMind 修改规划表V1.md](/g:/VSCODE-G/Fitness Agent MVP/task/V1/RepMind 修改规划表V1.md)

### V1.5 / V1.6 训练计划与应用壳层重构

- [task/V1.5/Task 1 - 应用壳层与侧边栏导航重构.md](/g:/VSCODE-G/Fitness Agent MVP/task/V1.5/Task 1 - 应用壳层与侧边栏导航重构.md)
- [task/V1.5/Task 2 - 训练计划页头部工具栏重构.md](/g:/VSCODE-G/Fitness Agent MVP/task/V1.5/Task 2 - 训练计划页头部工具栏重构.md)
- [task/V1.5/Task 3 - 周视图比例网格与列容器重构.md](/g:/VSCODE-G/Fitness Agent MVP/task/V1.5/Task 3 - 周视图比例网格与列容器重构.md)
- [task/V1.5/Task 4 - 训练日动作卡片信息密度重构.md](/g:/VSCODE-G/Fitness Agent MVP/task/V1.5/Task 4 - 训练日动作卡片信息密度重构.md)
- [task/V1.5/Task 5 - 休息日列与空状态交互适配.md](/g:/VSCODE-G/Fitness Agent MVP/task/V1.5/Task 5 - 休息日列与空状态交互适配.md)
- [task/V1.6/V1.6 开发完成总结.md](/g:/VSCODE-G/Fitness Agent MVP/task/V1.6/V1.6 开发完成总结.md)

### V2 / V2.1 AI 教练页 UI 重构

- [task/V2/V2 开发完成总结.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2/V2 开发完成总结.md)
- [task/V2.1/V2.1 AI教练页重写设计文档.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.1/V2.1 AI教练页重写设计文档.md)
- [task/V2.1/V2.1 AI教练页重写实施计划.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.1/V2.1 AI教练页重写实施计划.md)
- [task/V2.1/V2.1 开发完成总结.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.1/V2.1 开发完成总结.md)

### V2.3 后端化与 Agent 编排

- [task/V2.3/V2.3 Python 后端基建长期规划表.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Python 后端基建长期规划表.md)
- [task/V2.3/V2.3 Phase 1 后端骨架与数据迁移实施计划.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 1 后端骨架与数据迁移实施计划.md)
- [task/V2.3/V2.3 Phase 1 验收记录.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 1 验收记录.md)
- [task/V2.3/V2.3 Phase 2 Python Agent 与密钥后移实施计划.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 2 Python Agent 与密钥后移实施计划.md)
- [task/V2.3/V2.3 Phase 3 上下文管理与工具调用实施计划.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 3 上下文管理与工具调用实施计划.md)
- [task/V2.3/V2.3 Phase 3 验收记录.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 3 验收记录.md)
- [task/V2.3/V2.3 Phase 3 开发完成报告.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 3 开发完成报告.md)
- [task/V2.3/V2.3 Phase 4 文件体验与模型配置实施计划.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 4 文件体验与模型配置实施计划.md)
- [task/V2.3/V2.3 Phase 4 验收记录.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 4 验收记录.md)
- [task/V2.3/V2.3 Phase 4 开发完成报告.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 Phase 4 开发完成报告.md)
- [task/V2.3/V2.3 开发完成总结.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.3/V2.3 开发完成总结.md)

### V2.4 消息附件回显

- [task/V2.4/V2.4 AI 教练消息附件回显设计.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.4/V2.4 AI 教练消息附件回显设计.md)
- [task/V2.4/V2.4 AI 教练消息附件回显实施计划.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.4/V2.4 AI 教练消息附件回显实施计划.md)
- [task/V2.4/V2.4 验收记录.md](/g:/VSCODE-G/Fitness Agent MVP/task/V2.4/V2.4 验收记录.md)

## 补充说明

原 README 中这些偏“开发记录 / 技术备忘”的内容已经迁出：

- 阶段性功能更新日志
- 历史任务补充记录
- 后端接口长清单
- `localStorage` 键说明
- 历史迁移路径与旧版本收口说明

这些信息现在分别归位到更合适的文档：

- 架构、数据流、模块职责：[ARCHITECTURE.md](/g:/VSCODE-G/Fitness Agent MVP/ARCHITECTURE.md)
- 后端启动、迁移、接口速查：[backend/README.md](/g:/VSCODE-G/Fitness Agent MVP/backend/README.md)
- 验证与验收证据：[docs/verification.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification.md)
