# plan.md — RepMind

> 把"准备怎么做"说清楚：技术方案 | 目录结构 | 数据/API 草图 | 风险

---

## 一、技术方案

### 1.1 整体架构

```
┌─────────────────────────────────────────────┐
│              浏览器（本地运行）               │
│                                             │
│  React 前端                                 │
│  ├── 档案 Tab                               │
│  ├── 训练计划 Tab                            │
│  ├── 今日日志 Tab                            │
│  └── AI 教练 Tab ──► DeepSeek API           │
│           │                                 │
│      localStorage                           │
│      (profile / weeklyPlan / dailyLog /     │
│       chatHistory)                          │
└─────────────────────────────────────────────┘
```

- **无后端**：所有数据存在浏览器 localStorage，不需要服务器
- **无数据库**：数据随用随取，清除浏览器缓存则数据丢失（MVP 阶段可接受）
- **唯一外部依赖**：DeepSeek API，需要网络连接和有效 API Key

### 1.2 技术栈选型理由

| 技术  | 选型                         | 理由                               |
| --- | -------------------------- | -------------------------------- |
| 框架  | React + Vite               | 组件化开发，热更新快，构建产物可直接部署静态页          |
| 样式  | Tailwind CSS               | 无需写 CSS 文件，utility class 快速出界面   |
| 图表  | Recharts                   | React 原生，API 简单，够用               |
| 存储  | localStorage               | 零配置，无需后端，MVP 阶段完全满足              |
| AI  | DeepSeek API（原生 OpenAI 格式） | 有 Anthropic 兼容接口但字段支持不完整，原生格式更稳定 |

### 1.3 AI 调用方式

使用 DeepSeek `/chat/completions` 接口，**无状态调用**，每次请求携带完整对话历史：

```
请求结构：
  messages[0]: { role: "system", content: 自动构建的完整上下文 }
  messages[1~N]: 历史对话（最近20条，防止 token 超限）
  messages[N+1]: { role: "user", content: 本次用户输入 }

返回解析：
  data.choices[0].message.content
  → 检测是否含 ---JSON--- 分隔符
  → 是：分离正文和 JSON，渲染采纳卡片
  → 否：纯文本展示
```

### 1.4 System Prompt 注入策略

每次发送前实时构建，包含以下数据块：

```
【基本信息】    ← profile.basic + oneRM + goal
【本周训练计划】 ← weeklyPlan 格式化（含实际重量计算）
【近14天体重】  ← dailyLog 最近14条 weight 字段
【近7天饮食】   ← dailyLog 最近7条 kcal + protein 字段
【近7天训练情况】← dailyLog 最近7条 trainingDone + fatigue + sleep + trainingNotes
【今日 TDEE 估算】← 基于 BMR + 今日训练容量计算，作为参考数据注入
```

TDEE 数据只注入 prompt 供 AI 解读，**不在前端独立展示**。

---

## 二、页面与模块结构

### 2.1 页面结构（4个 Tab）

```
App
├── Tab: 我的档案（ProfileTab）
│   └── 表单：基本信息 + 1RM + 目标 + 备注
│
├── Tab: 训练计划（PlanTab）
│   ├── 周视图：7天横向排列，点击展开
│   ├── 动作列表：名称 / 实际重量 / 组×次
│   └── 动作编辑弹窗（ExerciseEditor）
│       ├── 重量来源：挂钩1RM百分比 或 直接填kg
│       └── 组数 / 次数 / 备注
│
├── Tab: 今日日志（TodayTab）
│   ├── 录入区：体重 / 热量 / 蛋白质 / 睡眠 / 疲劳度 / 是否训练 / 训练备注
│   └── 今日计划只读展示（从 weeklyPlan 读取）
│
└── Tab: AI 教练（CoachTab）
    ├── 对话气泡区（可滚动）
    ├── 采纳卡片（AdoptCard，AI 返回 JSON 时出现）
    ├── 上下文预览（折叠面板，查看本次注入的完整 prompt）
    └── 输入框 + 发送按钮
```

### 2.2 核心组件

| 组件                   | 职责                                |
| -------------------- | --------------------------------- |
| `ExerciseEditor.jsx` | 动作增删改弹窗，处理1RM百分比和直接kg两种模式         |
| `AdoptCard.jsx`      | 解析 AI 返回的 JSON 建议，展示变更对比，处理采纳写回逻辑 |
| `WeightChart.jsx`    | 近14天体重折线图（Sprint 2）               |

### 2.3 工具模块

| 模块                 | 职责                               |
| ------------------ | -------------------------------- |
| `utils/storage.js` | 统一的 localStorage 读写封装            |
| `utils/calc.js`    | BMR / TDEE / 训练容量计算，日期工具函数       |
| `utils/prompt.js`  | System Prompt 构建，将所有数据格式化为自然语言注入 |
| `api/deepseek.js`  | DeepSeek API 调用封装，错误处理           |

---

## 三、数据/API 草图

### 3.1 localStorage 数据结构

**`fitloop_profile`**
```json
{
  "basic": { "name": "", "sex": "male", "age": 23, "height": 178, "weight": 82.1 },
  "oneRM": { "squat": 120, "bench": 90, "deadlift": 150 },
  "goal": "增肌减脂",
  "targetWeight": 78,
  "notes": "容易睡眠不足，工作日压力大，每周训练3天"
}
```

**`fitloop_weeklyPlan`**
```json
{
  "Monday": {
    "type": "腿日",
    "exercises": [
      {
        "id": "uuid",
        "name": "深蹲",
        "ref1RM": "squat", "pct": 0.75,
        "kg": null,
        "sets": 4, "reps": 6, "note": ""
      }
    ]
  },
  "Tuesday": { "type": "rest", "exercises": [] }
}
```

> 重量渲染规则：`ref1RM` 不为 null → 实际重量 = `oneRM[ref1RM] × pct`（取整）；否则直接用 `kg` 字段。训练计划为**手动维护的静态周计划**，不自动生成周期递增逻辑。

**`fitloop_dailyLog`**
```json
{
  "2026-05-27": {
    "weight": 82.1,
    "kcal": 2150, "protein": 165,
    "sleep": 7, "fatigue": 3,
    "trainingDone": true,
    "trainingNotes": "深蹲第3组没完成，感觉膝盖有点不舒服"
  }
}
```

**`fitloop_chatHistory`**
```json
[
  { "role": "user", "content": "最近疲劳度比较高" },
  { "role": "assistant", "content": "..." }
]
```
保留最近 20 条，超出从头部截断。

### 3.2 DeepSeek API 调用草图

```
POST https://api.deepseek.com/chat/completions
Authorization: Bearer {VITE_DEEPSEEK_API_KEY}
Content-Type: application/json

{
  "model": "deepseek-v4-pro",
  "max_tokens": 1000,
  "messages": [
    { "role": "system", "content": "{buildSystemPrompt()}" },
    ...chatHistory,
    { "role": "user", "content": "{userInput}" }
  ]
}

响应：data.choices[0].message.content
```

### 3.3 AI 建议写回协议

AI 若建议修改训练计划，在正文末尾附加：

```
---JSON---
{
  "suggest_plan_update": true,
  "day": "Monday",
  "summary": "建议降低深蹲强度",
  "changes": [
    { "action": "update", "exerciseName": "深蹲", "field": "pct", "oldValue": 0.75, "newValue": 0.70 },
    { "action": "update", "exerciseName": "深蹲", "field": "reps", "oldValue": 6, "newValue": 8 }
  ]
}
```

前端解析后渲染采纳卡片，用户点击"采纳"→ 更新 `fitloop_weeklyPlan` → 下次 AI 对话读取新计划。

---

## 四、目录结构

```
fitloop/
├── src/
│   ├── App.jsx                  # 主入口，Tab 路由，全局状态
│   ├── tabs/
│   │   ├── ProfileTab.jsx       # 档案页
│   │   ├── PlanTab.jsx          # 训练计划页
│   │   ├── TodayTab.jsx         # 今日日志页
│   │   └── CoachTab.jsx         # AI 教练页（核心）
│   ├── components/
│   │   ├── ExerciseEditor.jsx   # 动作编辑弹窗
│   │   ├── AdoptCard.jsx        # AI 建议采纳卡片
│   │   └── WeightChart.jsx      # 体重趋势图（Sprint 2）
│   ├── utils/
│   │   ├── storage.js           # localStorage 读写封装
│   │   ├── calc.js              # BMR/TDEE 计算 + 日期工具
│   │   └── prompt.js            # System Prompt 构建
│   └── api/
│       └── deepseek.js          # DeepSeek API 调用
├── .env                         # VITE_DEEPSEEK_API_KEY=xxx
├── .gitignore                   # 含 .env
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

---

## 五、风险与应对

| 风险 | 可能性 | 影响 | 应对方案 |
|------|--------|------|---------|
| AI 返回格式不稳定（JSON 解析失败） | 中 | 采纳卡片无法渲染 | 降级为纯文本展示，不崩溃；prompt 中强调格式要求 |
| localStorage 数据意外丢失 | 低 | 用户数据全失 | Sprint 3 加 JSON 导出功能；MVP 阶段告知用户风险 |
| DeepSeek API 限流或不可用 | 低 | AI 教练无法使用 | 显示友好错误提示，其余三个 Tab 不受影响 |
| System Prompt 过长导致 token 超限 | 中 | API 报错 | 日志只取最近14天，对话历史只保留20条；prompt 格式精简 |
| 训练计划手动维护成本高 | 高 | 用户懒得更新 | UI 设计尽量减少操作步骤；这是 MVP 已知局限，后续迭代周期计划生成 |

---

*文档版本：v1.0 | 对应 idea.md v1.0 / spec.md v1.2*
