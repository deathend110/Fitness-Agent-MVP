# FitLoop MVP

FitLoop MVP 是一个本地运行的 AI 健身教练与训练记录应用，用于课程设计中的 Agent-based MVP 展示。当前重点是先跑通最小闭环：用户档案、每周训练计划、今日日志、AI 教练上下文注入与建议采纳。

## 项目简介

- 前端技术栈：Vite + React + Tailwind CSS
- 数据存储：localStorage
- AI 接口：DeepSeek 原生 OpenAI 格式
- 当前已完成的核心基础：档案录入、训练计划查看与维护、默认本地数据加载

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

训练计划 helper 的最小自动化验证：

```bash
node --test tests/weeklyPlan.test.js
```

前端构建验证：

```bash
npm run build
```

## Demo 操作路径

1. 打开首页。
2. 切换到“我的档案”，确认三大项 1RM 已存在或自行修改。
3. 切换到“训练计划”。
4. 展开 `Monday`。
5. 将训练类型改成“腿日”。
6. 点击“新增动作”，录入“深蹲 75% 4 组 6 次”并保存。
7. 刷新页面，确认刚才新增的动作仍然存在。
8. 再尝试编辑或删除某个动作，确认只影响当前日期，不会误改其他日期。

## 本地数据键

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`
