# Task 1 数值显示优化

- **估时**：15 分钟
- **依赖**：无
- **目标**：让训练重量、次数、组数等数值显示更简洁，避免出现冗长小数。
- **主要文件**：
  - `src/utils/calc.js`
  - `src/components/PlanDayCard.jsx`
  - `src/components/ExerciseEditor.jsx`
  - `src/tabs/TodayTab.jsx`
  - `src/utils/adoptCard.js`
- **主要操作**：
  - 统一数值格式化规则。
  - 重量展示保留合适的小数位。
  - 组数、次数、RPE 等展示保持统一风格。
- **完成信号**：
  - 页面中不会出现过长的小数展示。
  - 同一数值在不同页面展示一致。
- **验证方式**：
  - 输入 `97.25kg`、`75%` 等数据，刷新后检查展示是否符合预期。

