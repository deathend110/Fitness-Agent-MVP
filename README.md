# FitLoop MVP

FitLoop 是一个本地运行的 AI 健身教练 + 训练记录软件 MVP，用于课程设计中的 Agent-based MVP 展示。项目目标是跑通“用户档案 -> 训练计划 -> 今日日志 -> AI 教练 -> 采纳建议写回计划”的最小闭环。

当前已完成 Task 1.2：`localStorage` 工具和默认数据已接入页面，浏览器首次打开时也能展示默认档案、周计划、今日日志和聊天摘要。

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

`.env` 不应提交真实 API Key。

## 默认数据与 localStorage

- 页面启动时统一通过 `src/utils/storage.js` 读取四类数据：
  - `fitloop_profile`
  - `fitloop_weeklyPlan`
  - `fitloop_dailyLog`
  - `fitloop_chatHistory`
- 如果 localStorage 为空，会回退到 `src/utils/defaultData.js` 中的默认数据，并在首次渲染后写回浏览器存储。
- 如果某个 key 下保存了非法 JSON，`loadStorage(key, fallback)` 会自动回退到 fallback，页面不会崩溃。

## 测试命令

当前项目还没有正式测试框架，现阶段使用以下最小验证命令：

```bash
npm run build
node --input-type=module -e "import { loadStorage } from './src/utils/storage.js'; global.window = { localStorage: { getItem: () => '{bad json}', setItem: () => {} } }; console.log(JSON.stringify(loadStorage('fitloop_profile', { ok: true })));"
```

## Demo 操作路径

1. 打开首页，展示 4 个主 Tab。
2. 在“我的档案”查看默认用户档案摘要。
3. 在“训练计划”查看默认周计划，以及 1RM 百分比换算后的实际重量。
4. 在“今日日志”查看今日默认日志和今日只读训练安排。
5. 在“AI 教练”查看默认聊天记录和最近日志摘要。
6. 后续继续扩展为编辑、AI 对话和采纳写回闭环。

## 首次使用建议

如果你想验证“localStorage 为空时仍能展示默认数据”的行为，可以先清空浏览器中的以下 key，再刷新页面：

- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`

## 当前状态

- 已完成 Vite + React + Tailwind CSS 基础骨架。
- 已完成 4 个主 Tab 页面切换。
- 已新增 `src/utils/storage.js` 和 `src/utils/defaultData.js`。
- 已将默认数据接入 `App.jsx`，四个 Tab 会展示真实摘要而不是占位文案。
- 后续开发继续对齐 `docs/plan.md`、`docs/fitness_coach_mvp_spec.md` 和课程文档推进。
