# FitLoop MVP 架构说明

## 当前项目结构

```text
Fitness Agent MVP/
├─ docs/                  # SDD 文档、课程要求和参考资料
├─ task/                  # 按 Sprint 拆分的开发任务
├─ src/
│  ├─ App.jsx             # 主入口，统一读取 localStorage 并向 4 个 Tab 注入数据
│  ├─ main.jsx            # React 挂载入口
│  ├─ index.css           # Tailwind CSS 入口和全局样式
│  ├─ tabs/
│  │  ├─ ProfileTab.jsx   # 档案摘要展示
│  │  ├─ PlanTab.jsx      # 周计划摘要展示
│  │  ├─ TodayTab.jsx     # 今日日志摘要展示
│  │  └─ CoachTab.jsx     # AI 对话与日志摘要展示
│  ├─ utils/
│  │  ├─ storage.js       # localStorage 读写工具
│  │  └─ defaultData.js   # 默认 profile / weeklyPlan / dailyLog / chatHistory
│  ├─ components/         # 后续可复用 UI 组件
│  └─ api/                # 后续 DeepSeek API 封装
├─ index.html
├─ package.json
├─ tailwind.config.js
├─ vite.config.js
├─ README.md
└─ ARCHITECTURE.md
```

## 核心模块职责

- `App.jsx`
  - 统一读取 `profile / weeklyPlan / dailyLog / chatHistory`
  - 当 localStorage 为空时回退到默认数据
  - 将读取结果传给四个 Tab 做只读摘要展示
  - 在首次渲染后把当前数据写回 localStorage

- `src/utils/storage.js`
  - 提供 `loadStorage(key, fallback)`
  - 提供 `saveStorage(key, value)`
  - 处理空值、非法 JSON、非浏览器环境这三类边界情况

- `src/utils/defaultData.js`
  - 集中维护 `fitloop_profile`
  - 集中维护 `fitloop_weeklyPlan`
  - 集中维护 `fitloop_dailyLog`
  - 集中维护 `fitloop_chatHistory`
  - 字段严格对齐 `docs/plan.md` 与 `docs/fitness_coach_mvp_spec.md`

- `tabs/ProfileTab.jsx`
  - 展示默认档案摘要
  - 展示基本信息、三大项 1RM、目标和备注

- `tabs/PlanTab.jsx`
  - 展示默认一周训练计划
  - 处理 `ref1RM + pct -> 实际重量` 的只读换算展示

- `tabs/TodayTab.jsx`
  - 展示当天默认日志摘要
  - 展示根据当天星期匹配出的只读计划摘要

- `tabs/CoachTab.jsx`
  - 展示默认聊天历史
  - 展示最近几天的日志摘要
  - 为后续 AI 上下文注入和建议采纳预留页面位置

## 数据流说明

当前 MVP 数据流保持本地闭环：

```text
App 启动
  -> loadStorage(key, fallback)
  -> localStorage 中已有数据则直接读取
  -> localStorage 为空或 JSON 非法则回退默认数据
  -> 将数据注入 Profile / Plan / Today / Coach 四个 Tab
  -> useEffect 持久化到 localStorage
  -> 后续任务继续接入表单编辑、AI 对话和采纳写回
```

## localStorage 数据结构

### `fitloop_profile`

```json
{
  "basic": { "name": "小林", "sex": "male", "age": 23, "height": 178, "weight": 82.1 },
  "oneRM": { "squat": 120, "bench": 90, "deadlift": 150 },
  "goal": "增肌减脂",
  "targetWeight": 78,
  "notes": "工作日容易睡眠不足，当前每周训练 3 次，希望先把恢复节奏稳定下来。"
}
```

### `fitloop_weeklyPlan`

```json
{
  "Monday": {
    "type": "腿日",
    "exercises": [
      {
        "id": "monday-squat",
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
  }
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
    "trainingNotes": "深蹲第三组没有按计划完成，膝盖有一点紧。",
    "fatigue": 4,
    "sleep": 6.8
  }
}
```

### `fitloop_chatHistory`

```json
[
  { "role": "user", "content": "最近训练后疲劳感有点高，需要调整计划吗？" },
  { "role": "assistant", "content": "可以先从下肢主项强度和睡眠恢复一起看，后续我会结合训练计划给你建议。" }
]
```

## AI 调用链路

后续 AI 教练功能的调用链路保持不变：

```text
CoachTab
  -> buildSystemPrompt(profile, weeklyPlan, dailyLog)
  -> callDeepSeek(userMessage, chatHistory, systemPrompt)
  -> parseAiResponse(content)
  -> 纯文本回复 或 结构化建议卡片
  -> 用户采纳后写回 fitloop_weeklyPlan
```

## 后续扩展方向

- 为四个 Tab 接入编辑表单与实时保存
- 增加 `utils/calc.js` 和 `utils/prompt.js`
- 接入 DeepSeek `/chat/completions`
- 支持 AI 结构化 JSON 建议解析与一键采纳
- 补充最小验证记录、截图和课程演示材料
