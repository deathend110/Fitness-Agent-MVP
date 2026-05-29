# FitLoop MVP 架构说明

## 当前项目结构
```text
src/
  App.jsx
  components/
    ExerciseEditor.jsx
  tabs/
    ProfileTab.jsx
    PlanTab.jsx
    TodayTab.jsx
    CoachTab.jsx
  utils/
    storage.js
    defaultData.js
    calc.js
    profileForm.js
    exerciseForm.js
```

## 核心模块职责
- `App.jsx`：统一读取和写回本地状态，组织四个 Tab。
- `ProfileTab.jsx`：编辑用户档案和三大项 1RM。
- `PlanTab.jsx`：展示周计划，并提供单动作编辑演示。
- `ExerciseEditor.jsx`：编辑单个动作草稿。
- `exerciseForm.js`：处理动作草稿与正式对象的转换。
- `calc.js`：统一计算重量、BMR、TDEE 等结果。

## 数据流说明
```text
App 启动
  -> loadStorage()
  -> 读取 profile / weeklyPlan / dailyLog / chatHistory
  -> 传给各 Tab
  -> ProfileTab 编辑档案并回写 App
  -> App 保存到 localStorage
  -> PlanTab 根据 profile 计算动作实际重量
  -> ExerciseEditor 编辑单动作草稿
  -> exerciseForm.js 规范化成正式动作对象
```

## localStorage 数据结构
- `fitloop_profile`
- `fitloop_weeklyPlan`
- `fitloop_dailyLog`
- `fitloop_chatHistory`

其中 `weeklyPlan` 仍然按 `Monday` 到 `Sunday` 存储；动作对象包含：
- `name`
- `ref1RM`
- `pct`
- `kg`
- `sets`
- `reps`
- `rpe`
- `note`

## AI 调用链路
```text
CoachTab -> 拼装上下文 -> DeepSeek Chat Completions -> 解析建议 -> 回写对话显示
```

## 后续扩展方向
- 训练动作新增、编辑、删除的正式持久化
- 今日日志更完整的表单化录入
- AI 建议结构化解析与一键采纳
- 体重趋势、周训练热力图等轻量分析视图

