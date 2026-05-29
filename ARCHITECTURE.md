# FitLoop MVP 架构说明

## 当前项目结构

```text
Fitness Agent MVP/
├── docs/                  # SDD 文档、课程要求和参考资料
├── task/                  # 按 Sprint 拆分的开发任务
├── src/
│   ├── App.jsx            # 当前 React 主入口和 Sprint 0 初始界面
│   ├── main.jsx           # React 挂载入口
│   ├── index.css          # Tailwind CSS 入口和全局样式
│   ├── tabs/              # 四个主 Tab 页面
│   │   ├── ProfileTab.jsx # 我的档案入口
│   │   ├── PlanTab.jsx    # 训练计划入口
│   │   ├── TodayTab.jsx   # 今日日志入口
│   │   └── CoachTab.jsx   # AI 教练入口
│   ├── components/        # 后续放置可复用 UI 组件
│   ├── utils/             # 后续放置存储、计算、Prompt 构建工具
│   └── api/               # 后续放置 DeepSeek API 调用封装
├── index.html             # Vite HTML 入口
├── package.json           # npm 脚本和依赖
├── tailwind.config.js     # Tailwind 配置
├── postcss.config.cjs     # PostCSS 配置
├── vite.config.js         # Vite 配置
└── README.md              # 运行说明和 demo 路径
```

## 核心模块职责

- `App.jsx`：当前负责顶部导航、Tab 状态切换和页面容器协调。
- `tabs/ProfileTab.jsx`：当前是我的档案占位页，后续负责用户档案、三大项 1RM、训练目标和备注录入。
- `tabs/PlanTab.jsx`：当前是训练计划占位页，后续负责一周训练计划展示和动作增删改。
- `tabs/TodayTab.jsx`：当前是今日日志占位页，后续负责今日日志录入和今日计划只读摘要。
- `tabs/CoachTab.jsx`：当前是 AI 教练占位页，后续负责 AI 对话、上下文预览、采纳卡片接入。
- `components/ExerciseEditor.jsx`：后续负责单个训练动作编辑。
- `components/AdoptCard.jsx`：后续负责 AI 结构化建议展示和采纳交互。
- `utils/storage.js`：后续统一封装 localStorage 读写。
- `utils/calc.js`：后续封装 1RM 重量、BMR、TDEE 和日期计算。
- `utils/prompt.js`：后续将档案、计划、日志格式化为 AI system prompt。
- `api/deepseek.js`：后续封装 DeepSeek `/chat/completions` 调用。

## 数据流说明

MVP 数据流设计为本地闭环：

```text
用户输入档案/计划/日志
        ↓
localStorage
        ↓
buildSystemPrompt()
        ↓
DeepSeek API
        ↓
AI 回复文本 + 可选 JSON 建议
        ↓
采纳卡片
        ↓
写回 fitloop_weeklyPlan
```

## localStorage 数据结构

后续实现会使用以下 key：

- `fitloop_profile`：用户基本信息、三大项 1RM、训练目标和备注。
- `fitloop_weeklyPlan`：一周训练计划，按 Monday 到 Sunday 存储。
- `fitloop_dailyLog`：按日期存储体重、热量、蛋白质、睡眠、疲劳度和训练备注。
- `fitloop_chatHistory`：AI 对话历史，最多保留最近 20 条。

## AI 调用链路

后续 AI 教练功能使用 DeepSeek 原生 OpenAI 格式：

```text
CoachTab
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
  -> callDeepSeek(userMessage, chatHistory, systemPrompt)
  -> parseAiResponse(content)
  -> AdoptCard 或纯文本回复
```

## 扩展方向

- Sprint 1-4：完成核心闭环。
- Sprint 5：补齐验证记录和课堂 demo 脚本。
- Sprint 6：加入体重趋势图、数据导入导出和流式输出。

当前项目是最简 MVP，后续模块超过 200 行时需要拆分，保持高内聚、低耦合。
