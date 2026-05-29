# FitLoop MVP 架构说明

## 当前项目结构

```text
src/
  App.jsx
  components/
    ExerciseEditor.jsx
    PlanDayCard.jsx
  tabs/
    ProfileTab.jsx
    PlanTab.jsx
    TodayTab.jsx
    CoachTab.jsx
  utils/
    calc.js
    defaultData.js
    exerciseForm.js
    profileForm.js
    storage.js
    weeklyPlan.js
tests/
  weeklyPlan.test.js
```

## 核心模块职责

- `src/App.jsx`
  - 统一加载 `profile / weeklyPlan / dailyLog / chatHistory`
  - 维护顶层 React state
  - 通过 `useEffect` 将状态写回 localStorage
- `src/tabs/PlanTab.jsx`
  - 组织训练计划页面
  - 协调“展开哪一天”“当前编辑哪个动作”等页面状态
  - 把 `ExerciseEditor` 的草稿转换为正式动作对象后写回周计划
- `src/components/PlanDayCard.jsx`
  - 负责单日训练卡片展示
  - 渲染训练类型选择、动作列表、编辑入口和新增入口
- `src/components/ExerciseEditor.jsx`
  - 只负责单个动作草稿编辑
  - 不直接读写 localStorage
- `src/utils/exerciseForm.js`
  - 在动作草稿对象与正式动作对象之间做转换
  - 保证百分比模式与固定重量模式的数据字段形态一致
- `src/utils/weeklyPlan.js`
  - 封装周计划更新逻辑
  - 包含修改训练类型、新增动作、更新动作、删除动作
  - 生成稳定动作 `id`，优先使用 `crypto.randomUUID()`
- `tests/weeklyPlan.test.js`
  - 直接验证周计划 helper 的核心行为

## 数据流说明

```text
App 启动
  -> loadStorage()
  -> 读取 fitloop_weeklyPlan 等本地数据
  -> 将 weeklyPlan 与 setWeeklyPlan 传给 PlanTab

PlanTab 页面交互
  -> 用户修改训练类型 / 新增动作 / 编辑动作 / 删除动作
  -> ExerciseEditor 维护单动作草稿
  -> draftToExercise() 转成正式动作对象
  -> weeklyPlan.js 返回新的 weeklyPlan
  -> onWeeklyPlanChange(setWeeklyPlan) 更新顶层状态

App 状态变化
  -> useEffect(saveStorage)
  -> 写回 fitloop_weeklyPlan
  -> 刷新页面后再次 loadStorage() 仍能恢复
```

## localStorage 数据结构

### `fitloop_weeklyPlan`

按 `Monday` 到 `Sunday` 存储，每天结构如下：

```json
{
  "type": "腿日",
  "exercises": [
    {
      "id": "stable-id",
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
```

动作对象约束：

- 百分比模式：`ref1RM` 与 `pct` 有值，`kg === null`
- 固定重量模式：`kg` 有值，`ref1RM === null && pct === null`
- 每个动作都包含稳定 `id`

### 其他键

- `fitloop_profile`：用户基础信息、三大项 1RM、目标与备注
- `fitloop_dailyLog`：按日期存储体重、热量、疲劳、睡眠、训练备注
- `fitloop_chatHistory`：AI 对话历史

## AI 调用链路

当前项目保留 AI 页面骨架，正式链路仍按以下方向扩展：

```text
CoachTab
  -> 读取最新 profile / weeklyPlan / dailyLog
  -> 组装上下文 prompt
  -> 调用 DeepSeek Chat Completions
  -> 解析建议
  -> 回显到页面，并在后续 Sprint 支持采纳写回计划
```

## 后续扩展方向

- 训练计划动作顺序调整与批量复制
- 今日日志更完整的表单校验
- AI 返回结构化 JSON 建议并一键采纳
- 体重趋势图、训练热力图、数据导入导出
