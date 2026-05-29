# FitLoop MVP

FitLoop MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。当前阶段优先打通最小闭环：用户档案、周训练计划、今日日志，以及后续 AI 教练读取这些上下文的基础数据面。

## 项目简介

- 前端技术栈：Vite + React + Tailwind CSS
- 数据存储：localStorage
- AI 接口：DeepSeek 原生 OpenAI 格式
- 当前已完成的核心能力：
  - 用户档案录入与 1RM 维护
  - 一周训练计划编辑与持久化
  - 今日日志表单录入、保存与刷新后恢复
  - TodayTab 只读展示 `weeklyPlan[todayKey]` 的当日训练类型与动作摘要
  - CoachTab 临时展示 system prompt 上下文预览，可直接检查档案、计划、日志与 TDEE 是否注入

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

默认地址通常是 `http://localhost:5173/`。

## API Key 配置

在项目根目录创建 `.env`：

```bash
VITE_DEEPSEEK_API_KEY=你的DeepSeek_API_Key
```

不要提交真实 API Key。

## 测试命令

运行全部当前自动化测试：

```bash
npm test
```

仅运行今日日志相关测试：

```bash
node --test tests/dailyLog.test.js
```

仅运行 system prompt 相关测试：

```bash
node --test tests/prompt.test.js
```

前端构建验证：

```bash
npm run build
```

## Demo 操作路径

1. 打开首页。
2. 切换到“我的档案”，确认基础信息和三大项 1RM。
3. 切换到“训练计划”，查看或调整本周训练安排。
4. 切换到“今日日志”。
5. 输入当天的体重、热量、蛋白质、睡眠、疲劳度、是否完成训练和训练备注。
6. 点击“保存今日日志”。
7. 观察右侧“已保存摘要”是否同步显示最新数据。
8. 查看右侧“今日计划”是否按 `weeklyPlan[todayKey]` 只读展示训练类型与动作摘要；休息日应明确显示休息提示。
9. 切换到“AI 教练”，确认“临时上下文预览”里已经包含用户档案、本周计划、近 7/14 天日志摘要，以及“当日 TDEE”。
10. 重点检查预览中是否能看到训练备注，例如“深蹲第三组没有按计划完成”，以及 TDEE 数值。
11. 刷新页面，确认今日日志仍然保留。

## 本地数据键

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`

## Task 4.1 补充说明

- 新增 `src/api/deepseek.js`，统一封装 DeepSeek Chat Completions 调用。
- 默认接口地址为 `https://api.deepseek.com/chat/completions`。
- 默认模型为 `deepseek-v4-flash`，未再使用即将弃用的 `deepseek-chat` / `deepseek-reasoner`。
- `CoachTab` 现会显示 API Key 配置状态；如果未配置 `.env`，AI 教练页会直接提示缺少 `VITE_DEEPSEEK_API_KEY`。

## Task 4.1 测试命令

```bash
node --test tests/deepseek.test.js
```
