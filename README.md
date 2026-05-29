# FitLoop MVP

FitLoop 是一个本地运行的 AI 健身教练 + 训练记录软件 MVP，用于课程设计中的 Agent-based MVP 展示。项目目标是跑通“用户档案 -> 训练计划 -> 今日日志 -> AI 教练 -> 采纳建议写回计划”的最小闭环。

## 环境要求

- Node.js 24.13.1 或兼容版本
- npm 11.8.0 或兼容版本
- DeepSeek API Key（后续 AI 教练功能需要）

## 安装命令

```bash
npm install
```

## 运行命令

```bash
npm run dev
```

启动后访问终端输出的本地地址，通常是 `http://localhost:5173/`。

## 构建命令

```bash
npm run build
```

## API Key 配置

在项目根目录创建 `.env` 文件，并写入：

```bash
VITE_DEEPSEEK_API_KEY=你的DeepSeek_API_Key
```

`.env` 已在 `.gitignore` 中忽略，不应提交真实 API Key。

## 首次使用路径

当前已完成 Sprint 1 Task 1.1，应用具备 4 个主 Tab 入口。后续 MVP 的目标使用路径是：

1. 填写我的档案和三大项 1RM。
2. 设置一周训练计划。
3. 录入今日日志，包括体重、热量、睡眠、疲劳度和训练备注。
4. 打开 AI 教练，发送训练咨询。
5. 查看 AI 返回建议。
6. 如果出现采纳卡片，点击采纳并写回训练计划。

## Demo 路径

课程展示时按以下顺序演示：

1. 说明当前问题：训练计划、饮食记录和 AI 对话彼此割裂。
2. 展示 FitLoop 将档案、计划、日志集中在一个本地应用。
3. 展示 AI 教练读取上下文并返回建议。
4. 展示结构化建议一键写回训练计划。
5. 展示验证记录和后续迭代方向。

## 当前状态

- 已完成 Vite + React + Tailwind CSS 基础骨架。
- 已创建 `src/tabs`、`src/components`、`src/utils`、`src/api` 目录。
- 已完成 4 个主 Tab 页面入口：我的档案、训练计划、今日日志、AI 教练。
- 已实现顶部导航点击切换 Tab，切换过程不会刷新页面。
- 后续开发按 `task/Sprint 0 - 项目准备.md` 和 `docs/tasks.md` 推进。
