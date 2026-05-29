# FitLoop MVP — AI 健身顾问项目规划文档

> 本文档用于指导 AI Agent 完成代码实现。请严格按照数据结构、功能描述和优先级顺序开发。

---

## 一、项目背景与目标

### 痛点

用户目前使用三个工具管理健身：
- **Excel**：维护训练计划
- **薄荷健康 App**：记录体重和饮食热量
- **AI 对话**：定期把上述数据手动粘贴给 AI，获取建议

三个工具之间**没有数据流通**，每次找 AI 咨询都要重新介绍自己，导致使用频率很低，建议缺乏连续性。

### 核心目标

构建一个**数据闭环**：

```
用户录入体重/饮食
        ↓
      数据层
     ↙      ↖
训练计划    AI教练（自动读取最新数据）
     ↖      ↙
   用户采纳建议 → 直接修改计划
```

**AI 教练始终拥有用户的完整上下文，用户随时可以咨询，建议可一键写回计划。**

### 核心价值主张

1. AI 教练每次对话都自动注入最新的训练计划、体重趋势、饮食数据
2. AI 给出的计划调整建议可以一键采纳，直接更新训练计划
3. 替代 Excel + 碎片化 AI 对话的工作流，真正形成闭环

### MVP 边界（不做的内容）

- ❌ TDEE 独立看板：TDEE 作为 system prompt 的一行上下文数据由 AI 解读，不做前端计算展示
- ❌ 体重趋势图：Sprint 2 时间够再加
- ❌ 热力图、流式输出：加分项，不影响核心链路

---

## 二、技术栈

```
框架：      React (functional components + hooks)
样式：      Tailwind CSS
图表：      Recharts（Sprint 2）
数据存储：  localStorage（无需后端，全部本地）
AI 接口：   DeepSeek API（原生 OpenAI 格式）
            POST https://api.deepseek.com/chat/completions
            模型：deepseek-v4-pro
            API Key：从 .env 文件读取 VITE_DEEPSEEK_API_KEY
```

**交付形式：单个可运行的 React 应用（.jsx 文件或标准 CRA/Vite 项目均可）**

---

## 三、数据结构（localStorage）

所有数据存储在 localStorage，key 如下：

### 3.1 用户档案 `fitloop_profile`

```json
{
  "basic": {
    "name": "用户昵称",
    "sex": "male",
    "age": 23,
    "height": 178,
    "weight": 82.1
  },
  "oneRM": {
    "squat": 120,
    "bench": 90,
    "deadlift": 150
  },
  "goal": "增肌减脂",
  "targetWeight": 78,
  "notes": "容易睡眠不足，工作日压力大，每周训练3天"
}
```

### 3.2 训练计划 `fitloop_weeklyPlan`

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
      },
      {
        "id": "uuid",
        "name": "罗马尼亚硬拉",
        "ref1RM": null,
        "pct": null,
        "kg": 80,
        "sets": 3,
        "reps": 10,
        "rpe": null,
        "note": ""
      }
    ]
  },
  "Tuesday":   { "type": "rest", "exercises": [] },
  "Wednesday": { "type": "推日", "exercises": [] },
  "Thursday":  { "type": "rest", "exercises": [] },
  "Friday":    { "type": "拉日", "exercises": [] },
  "Saturday":  { "type": "rest", "exercises": [] },
  "Sunday":    { "type": "rest", "exercises": [] }
}
```

**重量计算规则：**
- 若 `ref1RM` 不为 null，实际重量 = `profile.oneRM[ref1RM] × pct`，保留整数
- 若 `ref1RM` 为 null，使用 `kg` 字段直接显示

### 3.3 每日日志 `fitloop_dailyLog`

```json
{
  "2026-05-27": {
    "weight": 82.1,
    "kcal": 2150,
    "protein": 165,
    "trainingDone": true,
    "trainingNotes": "深蹲第三组没完成，感觉膝盖有点不舒服",
    "fatigue": 3,
    "sleep": 7
  },
  "2026-05-26": { "..." : "..." }
}
```

**说明：** `trainingNotes` 替代原有的 `completedExercises` 精确字段。自然语言备注对 AI 教练的参考价值远高于结构化数据，且录入成本极低。

### 3.4 AI 对话历史 `fitloop_chatHistory`

```json
[
  { "role": "user", "content": "..." },
  { "role": "assistant", "content": "..." }
]
```

保留最近 20 条，超出则从头部截断。

---

## 四、TDEE 计算逻辑

### 4.1 BMR（Mifflin-St Jeor）

```js
// 男性
BMR = 10 × weight + 6.25 × height - 5 × age + 5
// 女性
BMR = 10 × weight + 6.25 × height - 5 × age - 161
```

### 4.2 当日训练热量消耗

```js
// 计算今日训练计划的总容量
const todayKey = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][new Date().getDay()]
const todayPlan = weeklyPlan[todayKey]

let totalVolume = 0 // kg·次
todayPlan.exercises.forEach(ex => {
  const actualKg = ex.ref1RM ? Math.round(profile.oneRM[ex.ref1RM] * ex.pct) : ex.kg
  totalVolume += actualKg × ex.sets × ex.reps
})

// 经验系数：力量训练每 kg·次 约消耗 0.1 kcal
const trainingKcal = totalVolume × 0.1
```

### 4.3 当日 TDEE

```js
// 休息日：基础活动系数 1.2
// 训练日：BMR × 1.2 + 训练消耗
const isTrainingDay = todayPlan.type !== 'rest'
const TDEE = isTrainingDay
  ? Math.round(BMR × 1.2 + trainingKcal)
  : Math.round(BMR × 1.2)
```

### 4.4 热量缺口

```js
const todayKcal = dailyLog[today]?.kcal ?? 0
const delta = todayKcal - TDEE
// delta < 0: 热量缺口（减脂有利）
// delta > 0: 热量盈余（增肌有利）
```

---

## 五、页面结构（4个 Tab）

```
┌────────────────────────────────────────────────────┐
│  FitLoop                          [我的档案][训练计划][今日日志][AI教练]  │
└────────────────────────────────────────────────────┘
```

### Tab 1：我的档案 (`ProfileTab`)

**功能：**
- 表单录入/编辑基本信息（姓名、性别、年龄、身高、体重）
- 录入/编辑三大项 1RM（深蹲、卧推、硬拉）
- 选择训练目标（增肌 / 减脂 / 增肌减脂）
- 设置目标体重
- 备注文本框（自由填写训练情况、生活习惯等，这些内容会注入 AI 上下文）

**交互：**
- 实时保存到 localStorage
- 修改 1RM 后，训练计划页的实际重量自动重新计算

---

### Tab 2：训练计划 (`PlanTab`)

**功能：**
- 周视图：7天横向排列，显示每天类型标签（腿日/推日/拉日/休息）
- 点击某天展开该天的动作列表
- 每个动作显示：动作名 / 实际重量（kg） / 组数 × 次数 / RPE（可选）/ 备注
- 可以新增、删除、编辑动作
- 动作编辑表单字段：
  - 动作名称（文本）
  - 重量来源：选择"挂钩1RM百分比"或"直接填写kg"
  - 若挂钩1RM：选择参考哪个1RM（深蹲/卧推/硬拉）+ 百分比滑块（50%~95%）
  - 若直接填写：数字输入框（kg）
  - 组数（数字）
  - 次数（数字）
  - 备注（文本，可选）
- 修改某天类型（腿日/推日/拉日/有氧/休息）
- **AI 建议采纳区域**（见第七节）

**实际重量展示逻辑：**
- 挂钩1RM的动作：显示"75% → 90kg"
- 直接填写的动作：显示"80kg"

---

### Tab 3：今日日志 (`TodayTab`)

**功能：今日数据录入（全部保存到 `dailyLog[today]`）**

- 今日体重（kg，小数点后1位）
- 今日热量摄入（kcal，从薄荷健康抄过来）
- 今日蛋白质（g，可选）
- 今日睡眠时长（小时）
- 主观疲劳度（1-5 滑块，1=精力充沛，5=极度疲劳）
- 是否完成训练（开关）
- 训练备注（文本框，记录实际与计划的差异，如"深蹲第3组没完成"、"膝盖不舒服跳过腿举"）

**今日计划展示（只读）：**

从 `weeklyPlan[todayKey]` 读取，展示今天计划的动作列表，提醒用户对照填写备注。

```
今日计划：腿日
深蹲 90kg × 4×6 | 罗马尼亚硬拉 80kg × 3×10 | 腿举 160kg × 3×12
```

> TDEE 计算数据传入 system prompt 供 AI 解读，不在此页面做看板展示。

**体重趋势图（Sprint 2，Recharts LineChart）：**
- 展示最近 14 天体重折线图
- X 轴：日期，Y 轴：体重（kg）

---

### Tab 4：AI 教练 (`CoachTab`)

**这是核心 Tab，也是演示的重点。**

**布局：**
- 上方：对话气泡区域（可滚动）
- 下方：输入框 + 发送按钮
- 右上角：一个"当前上下文预览"折叠按钮，点击可查看本次对话注入的完整 context

**System Prompt 自动构建（每次发送前重新生成）：**

```
你是一位专业的力量训练与饮食管理顾问，风格直接、专业、有据可依。
以下是用户的完整当前状态，每次对话开始前自动更新：

【基本信息】
姓名：{name}，性别：{sex}，年龄：{age}岁，身高：{height}cm，当前体重：{weight}kg
训练目标：{goal}，目标体重：{targetWeight}kg
用户备注：{notes}

【三大项 1RM】
深蹲：{squat}kg | 卧推：{bench}kg | 硬拉：{deadlift}kg

【本周训练计划】
{weeklyPlan 格式化，每天一行，列出类型和动作摘要}

【近14天体重记录】
{日期: 体重kg，逐行列出，末尾注明14日变化量和趋势}

【近7天饮食摘要】
{日期: 摄入kcal / 蛋白质g，末尾注明7日均值}

【近7天训练完成情况】
{日期: 完成/休息/缺训，疲劳度X/5，睡眠Xh，训练备注（原文呈现）}

【当前 TDEE 估算（今日）】
基础代谢(BMR)：{bmr}kcal
今日训练类型：{todayType}
训练容量估算消耗：{trainingKcal}kcal
当日 TDEE：{tdee}kcal
今日摄入：{todayKcal}kcal
热量缺口/盈余：{delta}kcal

请基于以上数据回答用户问题，给出具体、可执行的建议。
如果你的建议涉及修改训练计划，请在回复末尾额外输出以下 JSON（紧跟在正文之后，用 ---JSON--- 分隔）：

---JSON---
{
  "suggest_plan_update": true,
  "day": "Monday",
  "summary": "建议降低深蹲强度，增加次数",
  "changes": [
    {
      "action": "update",
      "exerciseName": "深蹲",
      "field": "pct",
      "oldValue": 0.75,
      "newValue": 0.70
    },
    {
      "action": "update",
      "exerciseName": "深蹲",
      "field": "reps",
      "oldValue": 6,
      "newValue": 82
    }
  ]
}

如果不涉及计划修改，不要输出 JSON 部分。
```

**AI 返回内容的解析：**
- 检测返回内容是否包含 `---JSON---` 分隔符
- 若包含，将 JSON 部分解析，在对话气泡下方渲染"采纳建议卡片"
- 若不包含，正常渲染文本回复

---

## 六、AI 调用实现

DeepSeek 使用原生 OpenAI 格式（`/chat/completions`），比 Anthropic 兼容模式更稳定，字段支持更完整。

```js
// src/api/deepseek.js
const callAI = async (userMessage, chatHistory, systemPrompt) => {
  const apiKey = import.meta.env.VITE_DEEPSEEK_API_KEY

  const response = await fetch("https://api.deepseek.com/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${apiKey}`   // 注意：Bearer，不是 x-api-key
    },
    body: JSON.stringify({
      model: "deepseek-v4-pro",
      max_tokens: 1000,
      messages: [
        { role: "system", content: systemPrompt },  // system 作为 messages[0]
        ...chatHistory,                              // 历史对话（最近20条）
        { role: "user", content: userMessage }
      ]
    })
  })

  if (!response.ok) {
    const err = await response.json()
    throw new Error(err.error?.message ?? `HTTP ${response.status}`)
  }

  const data = await response.json()
  return data.choices[0].message.content   // 注意：OpenAI 格式，不是 data.content[0].text
}

export default callAI
```

**与 Anthropic 格式的关键差异：**

| 项目 | Anthropic 格式 | DeepSeek 原生（本项目使用）|
|------|--------------|--------------------------|
| Endpoint | `/anthropic/v1/messages` | `/chat/completions` |
| Auth Header | `x-api-key: xxx` | `Authorization: Bearer xxx` |
| System 字段 | 顶层 `system` 参数 | `messages[0]` 的 `role: "system"` |
| 返回值 | `data.content[0].text` | `data.choices[0].message.content` |

**.env 文件配置（项目根目录新建 `.env`）：**
```
VITE_DEEPSEEK_API_KEY=你的DeepSeek API Key
```
注意：`.env` 不要提交到 git，`.gitignore` 中加入 `.env`。

**流式输出（Sprint 3 加分项）：**
请求体加 `stream: true`，使用 SSE 逐 token 渲染，实现打字机效果。DeepSeek 原生格式完整支持此特性。

---

## 七、一键采纳计划修改（闭环核心）

当 AI 返回包含 JSON 建议时，在 AI 回复气泡下方渲染采纳卡片：

```
┌─────────────────────────────────────────────────┐
│ 📋 AI 建议修改训练计划 · 周一（腿日）             │
│                                                 │
│ 建议降低深蹲强度，增加次数以优化疲劳管理           │
│                                                 │
│  深蹲  75% → 70%  (90kg → 84kg)                │
│  深蹲  6次/组 → 8次/组                          │
│                                                 │
│  [✓ 采纳并更新计划]        [✗ 忽略]             │
└─────────────────────────────────────────────────┘
```

**采纳逻辑：**
```js
const adoptPlanChange = (day, changes) => {
  const plan = loadFromStorage('fitloop_weeklyPlan')
  changes.forEach(change => {
    const ex = plan[day].exercises.find(e => e.name === change.exerciseName)
    if (ex) ex[change.field] = change.newValue
  })
  saveToStorage('fitloop_weeklyPlan', plan)
  // 更新成功后，下次打开训练计划 Tab 即可看到变更
}
```

---

## 八、开发任务拆分（按优先级）

### Sprint 1 — 核心骨架（必须完成）

| #   | 任务                                      | 估时    |
| --- | --------------------------------------- | ----- |
| 1   | 项目初始化，Tab 路由框架，localStorage 工具函数        | 30min |
| 2   | 档案 Tab：表单 + 保存                          | 45min |
| 3   | 训练计划 Tab：周视图 + 动作列表展示                   | 45min |
| 4   | 训练计划 Tab：动作增删改（含1RM百分比逻辑）               | 60min |
| 5   | AI 教练 Tab：System Prompt 构建（含 TDEE 计算注入） | 45min |
| 6   | AI 教练 Tab：对话 UI + DeepSeek API 调用       | 45min |
| 7   | AI 返回 JSON 解析 + 采纳卡片渲染 + 写回计划           | 45min |

### Sprint 2 — 闭环完整（建议完成）

| # | 任务 | 估时 |
|---|------|------|
| 8 | 今日日志 Tab：录入表单（含训练备注）+ 保存 | 45min |
| 9 | 今日日志 Tab：今日计划只读展示 | 20min |
| 10 | 体重趋势折线图（Recharts） | 45min |
| 11 | AI 教练 Tab：上下文预览折叠面板 | 20min |

### Sprint 3 — 演示加分（时间够再做）

| # | 任务 | 估时 |
|---|------|------|
| 12 | AI 流式输出（打字机效果） | 45min |
| 13 | 训练完成热力图（类 GitHub contribution） | 60min |
| 14 | 数据导入导出（JSON 文件） | 30min |

---

## 九、验收标准（TDD 最小测试集）

### 核心成功路径

1. 填写 Profile（体重75kg，深蹲1RM 120kg，目标增肌减脂）
2. 训练计划周一设置深蹲 75% × 4×6
3. 今日日志录入：体重82kg，热量2100kcal，疲劳度3，训练备注"深蹲第3组没完成"
4. 打开 AI 教练，问"最近疲劳度有点高，要不要调整计划"
5. AI 回复包含建议且带 `---JSON---` 结构，采纳卡片正常渲染
6. 点击采纳，切换到训练计划页，对应动作已更新

### 边界情况

- 边界1：今天是休息日，system prompt 里训练消耗为 0，AI 能正确理解今天不训练
- 边界2：某动作直接填 kg 而非百分比，TDEE 计算和 prompt 格式化均正确
- 边界3：日志完全为空（新用户），AI 教练提示数据不足，不报错崩溃

### 失败场景

- 失败1：Profile 未填写，进入 AI 教练 Tab，显示"请先完善档案"，不发送 API 请求
- 失败2：API 调用失败（网络/key错误），显示错误提示，界面不崩溃
- 失败3：AI 返回纯文本（不含 `---JSON---`），正常渲染文字，不出现采纳卡片

---

## 十、工具函数参考

```js
// src/utils/storage.js
export const save = (key, data) => localStorage.setItem(key, JSON.stringify(data))
export const load = (key) => {
  try { return JSON.parse(localStorage.getItem(key)) }
  catch { return null }
}

// src/utils/calc.js
export const getTodayKey = () =>
  ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][new Date().getDay()]

export const getTodayStr = () => new Date().toISOString().split('T')[0]

export const getRecentLogs = (dailyLog, n = 14) =>
  Object.entries(dailyLog ?? {})
    .sort(([a], [b]) => b.localeCompare(a))
    .slice(0, n)

export const calcBMR = ({ weight, height, age, sex }) =>
  sex === 'male'
    ? 10 * weight + 6.25 * height - 5 * age + 5
    : 10 * weight + 6.25 * height - 5 * age - 161

export const calcTrainingKcal = (exercises = [], oneRM = {}) =>
  exercises.reduce((sum, ex) => {
    const kg = ex.ref1RM ? Math.round(oneRM[ex.ref1RM] * ex.pct) : ex.kg
    return sum + (kg ?? 0) * ex.sets * ex.reps * 0.1
  }, 0)

// src/utils/prompt.js
export const buildSystemPrompt = (profile, weeklyPlan, dailyLog) => {
  const bmr = calcBMR(profile.basic)
  const todayKey = getTodayKey()
  const todayPlan = weeklyPlan?.[todayKey] ?? { type: 'rest', exercises: [] }
  const isTrainingDay = todayPlan.type !== 'rest'
  const trainingKcal = isTrainingDay ? calcTrainingKcal(todayPlan.exercises, profile.oneRM) : 0
  const tdee = Math.round(bmr * 1.2 + trainingKcal)

  const recentLogs = getRecentLogs(dailyLog, 14)
  const todayStr = getTodayStr()
  const todayLog = dailyLog?.[todayStr]

  const weightHistory = recentLogs
    .map(([date, log]) => `${date}: ${log.weight ?? '未记录'}kg`)
    .join('\n')

  const dietHistory = recentLogs.slice(0, 7)
    .map(([date, log]) => `${date}: ${log.kcal ?? '未记录'}kcal / 蛋白质${log.protein ?? '未记录'}g`)
    .join('\n')

  const trainingHistory = recentLogs.slice(0, 7)
    .map(([date, log]) => {
      const status = log.trainingDone ? '完成' : '未完成/休息'
      return `${date}: ${status}，疲劳度${log.fatigue ?? '-'}/5，睡眠${log.sleep ?? '-'}h，备注：${log.trainingNotes || '无'}`
    })
    .join('\n')

  const planSummary = Object.entries(weeklyPlan ?? {})
    .map(([day, p]) => {
      if (p.type === 'rest') return `${day}: 休息日`
      const exList = p.exercises.map(ex => {
        const kg = ex.ref1RM ? Math.round(profile.oneRM[ex.ref1RM] * ex.pct) : ex.kg
        return `${ex.name} ${kg}kg×${ex.sets}×${ex.reps}`
      }).join(' | ')
      return `${day}（${p.type}）: ${exList}`
    }).join('\n')

  return `你是一位专业的力量训练与饮食管理顾问，风格直接、专业、有据可依。
以下是用户的完整当前状态，每次对话开始前自动更新：

【基本信息】
姓名：${profile.basic.name}，性别：${profile.basic.sex === 'male' ? '男' : '女'}，年龄：${profile.basic.age}岁，身高：${profile.basic.height}cm，当前体重：${profile.basic.weight}kg
训练目标：${profile.goal}，目标体重：${profile.targetWeight}kg
用户备注：${profile.notes || '无'}

【三大项 1RM】
深蹲：${profile.oneRM.squat}kg | 卧推：${profile.oneRM.bench}kg | 硬拉：${profile.oneRM.deadlift}kg

【本周训练计划】
${planSummary}

【近14天体重记录】
${weightHistory || '暂无记录'}

【近7天饮食摘要】
${dietHistory || '暂无记录'}

【近7天训练完成情况】
${trainingHistory || '暂无记录'}

【今日 TDEE 估算】
基础代谢(BMR)：${bmr}kcal
今日训练类型：${todayPlan.type}（${isTrainingDay ? '训练日' : '休息日'}）
训练容量估算消耗：${Math.round(trainingKcal)}kcal
当日 TDEE：${tdee}kcal
今日实际摄入：${todayLog?.kcal ?? '未记录'}kcal
热量缺口/盈余：${todayLog?.kcal ? todayLog.kcal - tdee : '未记录'}kcal

请基于以上数据回答用户问题，给出具体、可执行的建议。
如果你的建议涉及修改训练计划，请在回复正文末尾另起一行输出以下 JSON，用 ---JSON--- 标记分隔：

---JSON---
{
  "suggest_plan_update": true,
  "day": "Monday",
  "summary": "建议降低深蹲强度，增加次数",
  "changes": [
    { "action": "update", "exerciseName": "深蹲", "field": "pct", "oldValue": 0.75, "newValue": 0.70 },
    { "action": "update", "exerciseName": "深蹲", "field": "reps", "oldValue": 6, "newValue": 8 }
  ]
}

如果不涉及计划修改，不要输出 JSON 部分。`
}

```
---
## 十一、文件结构建议
fitloop/
├── src/
│   ├── App.jsx                  # 主入口，Tab 路由
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
│   │   ├── storage.js           # localStorage 工具
│   │   ├── calc.js              # BMR/TDEE 计算 + 日期工具
│   │   └── prompt.js            # System Prompt 构建（完整实现见第十节）
│   └── api/
│       └── deepseek.js          # DeepSeek API 调用（原生 OpenAI 格式）
├── .env                         # VITE_DEEPSEEK_API_KEY=xxx（不提交 git）
├── .gitignore                   # ignore  .env
├── docs/                  # 参考文档
├── package.json
└── README.md

---

## 十二、README 要求（提交必须包含）

```
README.md 至少包含：

1. **项目简介**：一句话说明这是什么
2. **环境要求**：Node.js 版本
3. **安装命令**：`npm install`
4. **运行命令**：`npm run dev` 或 `npm start`
5. **首次使用步骤**：填写档案 → 设置训练计划 → 录入今日日志 → 打开 AI 教练
6. **API Key 配置**：项目根目录新建 `.env` 文件，写入 `VITE_DEEPSEEK_API_KEY=你的Key`，从 [DeepSeek 控制台](https://platform.deepseek.com) 申请
7. **测试命令**：`npm test`（如有）
8. **Demo 步骤**：演示时的操作路径
```
---

## 十三、给 Agent 的开发指令

> 以下为给 AI Agent 的直接指令，请按顺序执行：

1. 使用 **Vite + React + Tailwind CSS** 初始化项目
2. 按照第十一节的文件结构组织代码
3. 按照**第八节 Sprint 1 → Sprint 2** 的顺序逐任务实现，Sprint 1 全部完成后再开始 Sprint 2
4. 数据结构严格按照第三节定义，不要自行修改字段名，特别注意 `trainingNotes` 而非 `notes`
5. API 调用严格按照第六节实现，使用原生 OpenAI 格式，endpoint 为 `/chat/completions`，返回值取 `data.choices[0].message.content`
6. System Prompt 构建函数在 `utils/prompt.js` 中完整实现，参考第十节的代码
7. AI 返回解析：检测 `---JSON---` 分隔符，正文和 JSON 分别处理；JSON 解析失败时降级为纯文本展示，不报错
8. 所有 localStorage 操作统一通过 `utils/storage.js` 的 `save/load` 函数
9. 样式使用 Tailwind，整体风格：深色运动 App，深灰背景 `#1a1a2e`，强调色橙色 `#f97316`
10. 完成后生成完整 README.md，包含安装、运行、API Key 配置和 demo 操作路径

---

*文档版本：v1.2 | 项目代号：FitLoop | 更新记录：修正 API 为 DeepSeek 原生格式；收敛 MVP 边界（去除 TDEE 看板，trainingNotes 替代 completedExercises）*
