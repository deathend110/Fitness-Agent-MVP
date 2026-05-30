# FitLoop MVP

FitLoop MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。当前阶段优先跑通一条最小但完整的核心闭环：

用户档案 -> 训练计划 -> 今日日志 -> AI 教练上下文注入 -> AI 建议 -> 一键采纳并写回训练计划

## 项目简介

- 前端：Vite + React + Tailwind CSS
- 存储：浏览器 `localStorage`
- AI：DeepSeek 原生 OpenAI 格式接口
- 目标：可运行、可演示、可验证

## 当前已实现能力

- 维护用户档案、训练目标与三大项 1RM
- 维护一周训练计划
- 使用 7 列课表式布局展示周计划
- 单日动作卡片支持主项 / 辅项层级展示
- 动作编辑器支持层级、组型、次数表达和两种负重模式
- 录入今日日志：体重、热量、蛋白质、睡眠、疲劳度、训练备注
- AI 发送前自动注入最新档案、计划和日志上下文
- 解析 AI 回复中的结构化 JSON 建议
- 渲染采纳卡片并将建议写回训练计划
- 本地 JSON 导入 / 导出

## Task 4 已完成的训练计划升级

- 周计划升级为 7 列课表布局，训练日与休息日宽度区分显示
- 动作卡片支持主项 `main` / 辅项 `accessory` 视觉层级
- 编辑器支持组型：
  - `straight`：常规直组
  - `custom`：自定义组型
- 编辑器支持次数表达：
  - 数值次数，如 `6`
  - 文本次数，如 `6/6/8`、`10-12`
- 动作数据结构升级为“模板 + 实例”双层，同时保留扁平兼容字段，便于当前 AI 采纳链路继续工作

## 环境要求

- Node.js 24.13.1 或兼容版本
- npm 11.8.0 或兼容版本

## 安装命令

```bash
npm install
```

## 运行命令

```bash
npm run dev
```

默认访问地址通常为：

```text
http://localhost:5173/
```

生产构建与本地预览：

```bash
npm run build
npm run preview
```

## API Key 配置

在项目根目录创建 `.env`：

```bash
VITE_DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
```

说明：

- 未配置 API Key 时，除 AI 教练外的本地功能仍可使用
- 修改 `.env` 后需要重启开发服务器
- 不要提交真实 API Key

## 测试命令

运行全部自动化测试：

```bash
npm test
```

按模块快速验证：

```bash
node --test tests/weeklyPlan.test.js tests/planExerciseCard.test.js
node --test tests/adoptPlan.test.js
node --test tests/coachChat.test.js tests/coachGuard.test.js
```

前端构建验证：

```bash
npm run build
```

最小验证记录见 [docs/verification.md](/g:/VSCODE-G/Fitness Agent MVP/docs/verification.md)。

## Demo 操作路径

1. 打开首页，确认可以进入四个主标签页。
2. 进入“我的档案”，填写基础信息、训练目标和三大项 1RM。
3. 进入“训练计划”，确认一周计划为 7 列课表布局。
4. 任选一天新增动作，尝试切换主项 / 辅项、直组 / 自定义组型，并填写次数表达。
5. 保存动作后，确认卡片呈现出主项 / 辅项分层。
6. 进入“今日日志”，填写当天体重、热量、蛋白质、睡眠、疲劳度和备注并保存。
7. 切换到“AI 教练”，展开上下文预览，确认包含档案、周计划与最近日志。
8. 输入训练调整问题并发送，观察聊天消息与错误提示。
9. 当 AI 回复包含 `---JSON---` 结构化建议时，确认页面渲染采纳卡片。
10. 点击“采纳并更新计划”，返回“训练计划”确认对应动作字段已更新。

## localStorage 键说明

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`
- `fitloop_storageVersion`

更多模块职责、数据流与数据结构说明见 [ARCHITECTURE.md](/g:/VSCODE-G/Fitness Agent MVP/ARCHITECTURE.md)。
