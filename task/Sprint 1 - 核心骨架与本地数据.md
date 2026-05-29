### Task 1.1 搭建 App Tab 框架

- **估时**：45 分钟
- **依赖**：Task 0.1
- **目标**：形成 4 个主页面入口。
- **主要操作**：
  - 在 `src/App.jsx` 中实现顶部导航。
  - 创建 `ProfileTab.jsx`、`PlanTab.jsx`、`TodayTab.jsx`、`CoachTab.jsx` 空页面。
  - 点击导航可切换 Tab。
  - 使用 Tailwind 做基础深色运动风格。
- **完成信号**：
  - 页面有“我的档案、训练计划、今日日志、AI 教练”4 个 Tab。
  - 切换 Tab 不刷新页面。
- **验证方式**：
  - 手动点击 4 个 Tab，确认对应页面标题正常显示。

### Task 1.2 实现 localStorage 工具与默认数据

- **估时**：45 分钟
- **依赖**：Task 1.1
- **目标**：统一管理本地数据读写。
- **主要操作**：
  - 创建 `src/utils/storage.js`。
  - 实现 `loadStorage(key, fallback)` 和 `saveStorage(key, value)`。
  - 创建 `src/utils/defaultData.js`，定义默认 profile、weeklyPlan、dailyLog、chatHistory。
  - 所有默认字段对齐 `docs/plan.md` 和 `docs/fitness_coach_mvp_spec.md`。
- **完成信号**：
  - localStorage 没有数据时，页面能读取默认数据。
  - 写入非法 JSON 时，读取函数能回退到 fallback。
- **验证方式**：
  - 手动清空浏览器 localStorage 后刷新页面，确认页面不崩溃。

### Task 1.3 实现计算工具

- **估时**：45 分钟
- **依赖**：Task 1.2
- **目标**：封装重量、日期、BMR/TDEE 计算。
- **主要操作**：
  - 创建 `src/utils/calc.js`。
  - 实现 `getTodayKey()`、`getTodayStr()`。
  - 实现 `getExerciseKg(exercise, oneRM)`。
  - 实现 `calcBMR(profileBasic)`。
  - 实现 `calcTrainingKcal(exercises, oneRM)`。
  - 实现 `calcTDEE(profile, weeklyPlan, dailyLog)`。
- **完成信号**：
  - 1RM 百分比动作能计算实际重量。
  - 固定 kg 动作能直接返回 kg。
  - 休息日训练消耗为 0。
- **验证方式**：
  - 在页面临时展示或控制台检查：深蹲 120kg 的 75% 显示 90kg。