# FitLoop MVP 架构说明

## 当前项目结构

```text
Fitness Agent MVP/
├── docs/                  # SDD 文档、课程要求和规格说明
├── task/                  # 按 Sprint 拆分的开发任务
├── src/
│   ├── App.jsx            # 主入口，统一读取 localStorage 并向 4 个 Tab 注入数据
│   ├── main.jsx           # React 挂载入口
│   ├── index.css          # Tailwind CSS 入口与全局样式
│   ├── tabs/
│   │   ├── ProfileTab.jsx # 档案摘要展示
│   │   ├── PlanTab.jsx    # 周训练计划展示
│   │   ├── TodayTab.jsx   # 今日日志摘要展示
│   │   └── CoachTab.jsx   # AI 对话与后续采纳入口
│   └── utils/
│       ├── storage.js     # localStorage 读写工具
│       ├── defaultData.js # 默认 profile / weeklyPlan / dailyLog / chatHistory
│       └── calc.js        # 日期、重量、BMR、训练消耗、TDEE 计算工具
├── index.html
├── package.json
├── README.md
└── ARCHITECTURE.md
```

## 核心模块职责

- `App.jsx`
  - 统一读取 `profile / weeklyPlan / dailyLog / chatHistory`
  - 当 localStorage 为空时回退到默认数据
  - 将数据注入四个 Tab
  - 用 `useEffect` 写回 localStorage

- `src/utils/storage.js`
  - 提供 `loadStorage(key, fallback)`
  - 提供 `saveStorage(key, value)`
  - 处理空值、非法 JSON 和非浏览器环境

- `src/utils/defaultData.js`
  - 集中维护 `fitloop_profile`
  - 集中维护 `fitloop_weeklyPlan`
  - 集中维护 `fitloop_dailyLog`
  - 集中维护 `fitloop_chatHistory`
  - 字段严格对齐 `docs/plan.md` 与 `docs/fitness_coach_mvp_spec.md`

- `src/utils/calc.js`
  - `getTodayKey()`：统一返回 `weeklyPlan` 使用的星期键
  - `getTodayStr()`：统一返回 `dailyLog` 使用的日期键
  - `getExerciseKg()`：统一计算动作实际重量
  - `calcBMR()`：计算基础代谢
  - `calcTrainingKcal()`：估算训练消耗
  - `calcTDEE()`：汇总今日训练和热量上下文

- `tabs/PlanTab.jsx`
  - 展示一周训练计划
  - 通过 `getExerciseKg()` 共享重量换算逻辑

- `tabs/TodayTab.jsx`
  - 展示今日日志摘要
  - 通过 `getTodayKey()`、`getTodayStr()` 和 `getExerciseKg()` 共享日期与重量逻辑

- `tabs/CoachTab.jsx`
  - 展示默认聊天历史
  - 为后续 AI 上下文注入、建议解析和采纳写回预留入口

## 数据流说明

```text
App 启动
  -> loadStorage(key, fallback)
  -> localStorage 有值则直接读取
  -> localStorage 为空或 JSON 非法则回退默认数据
  -> calc.js 提供今日日期/星期、动作重量、训练消耗与 TDEE 计算能力
  -> App 将数据注入 Profile / Plan / Today / Coach 四个 Tab
  -> useEffect 将当前状态持久化回 localStorage
```

## localStorage 数据结构

### `fitloop_profile`

```json
{
  "basic": { "name": "用户昵称", "sex": "male", "age": 23, "height": 178, "weight": 82.1 },
  "oneRM": { "squat": 120, "bench": 90, "deadlift": 150 },
  "goal": "增肌减脂",
  "targetWeight": 78,
  "notes": "用户的训练和恢复备注"
}
```

### `fitloop_weeklyPlan`

```json
{
  "Monday": {
    "type": "腿日",
    "exercises": [
      {
        "id": "uuid",
        "name": "深蹲",
        "ref1RM": "squat",
        "pct": 0.75,
        "kg": null,
        "sets": 4,
        "reps": 6,
        "rpe": null,
        "note": "主项"
      }
    ]
  },
  "Tuesday": { "type": "rest", "exercises": [] }
}
```

### `fitloop_dailyLog`

```json
{
  "2026-05-29": {
    "weight": 82.1,
    "kcal": 2150,
    "protein": 165,
    "trainingDone": true,
    "trainingNotes": "深蹲第三组未完成",
    "fatigue": 4,
    "sleep": 6.8
  }
}
```

### `fitloop_chatHistory`

```json
[
  { "role": "user", "content": "最近疲劳有点高，要不要调整计划？" },
  { "role": "assistant", "content": "可以先从主项强度和睡眠恢复一起看。" }
]
```

## AI 调用链路

后续 AI 教练功能的链路保持如下：

```text
CoachTab
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
  -> 其中调用 calcTDEE() / getExerciseKg() 等工具拼装上下文
  -> callDeepSeek(userMessage, chatHistory, systemPrompt)
  -> parseAiResponse(content)
  -> 纯文本回复 或 结构化建议卡片
  -> 用户采纳后写回 fitloop_weeklyPlan
```

## 计算工具规则

- `getTodayKey()` 返回 `Sunday` ~ `Saturday`，严格对齐 `weeklyPlan` key
- `getTodayStr()` 返回 `YYYY-MM-DD`，严格对齐 `dailyLog` key
- `getExerciseKg()` 支持两种模式：
  - `ref1RM + pct`：`oneRM[ref1RM] * pct` 后取整
  - 固定 `kg`：直接返回填写重量
- `calcTrainingKcal()` 使用 `kg * sets * reps * 0.1`
- `calcTDEE()` 当前返回：
  - `todayKey`
  - `todayStr`
  - `todayPlan`
  - `isTrainingDay`
  - `bmr`
  - `trainingKcal`
  - `tdee`
  - `todayKcal`
  - `delta`

## 后续扩展方向

- 为四个 Tab 接入表单编辑与实时保存
- 新增 `utils/prompt.js`，将 `calcTDEE()` 结果注入 AI system prompt
- 接入 DeepSeek `/chat/completions`
- 支持 AI 结构化 JSON 建议解析与一键采纳
- 补充最小验证记录、截图和课程演示材料
