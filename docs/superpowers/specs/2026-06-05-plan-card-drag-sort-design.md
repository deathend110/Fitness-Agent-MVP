# 训练计划页动作卡片同日拖拽排序设计

## 背景

当前训练计划页的动作顺序完全由 `weeklyPlan[dayKey].exercises` 数组顺序驱动：

- [src/tabs/PlanTab.jsx](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/tabs/PlanTab.jsx) 负责页面编排、编辑态管理和写回入口
- [src/components/PlanDayCard.jsx](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/components/PlanDayCard.jsx) 负责单日卡片内的动作列表渲染
- [src/components/PlanExerciseItem.jsx](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/components/PlanExerciseItem.jsx) 负责单个动作卡片、三点菜单和编辑态切换
- [src/utils/weeklyPlan.js](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/utils/weeklyPlan.js) 提供动作增删改和单日类型更新的纯函数

目前用户可以新增、编辑、删除动作，但不能调整同一天内动作顺序。随着动作数量增多，用户无法按训练流程、主辅项优先级或个人习惯重排列表，影响训练计划维护体验。

本设计目标是在不破坏现有动作卡片相关功能的前提下，为训练计划页增加“同一天内动作卡片整卡拖拽排序，放手即保存”的能力。

## 目标

- 支持训练计划页同一天内动作卡片的上下拖拽排序
- 拖拽放手后立即保存，不新增额外确认按钮
- 继续复用现有 `weeklyPlan` / 周期 override 写回链路
- 不修改动作数据结构，不引入额外排序字段
- 不影响动作编辑、删除、三点菜单、周期模式和周计划现有行为
- 保持实现边界清晰，可通过纯函数和组件契约测试覆盖

## 非目标

- 不支持跨天拖拽
- 不支持把动作从某一天拖到另一日
- 首版不支持移动端触摸拖拽排序
- 不引入新的后端专用排序接口
- 不重构现有动作编辑器或卡片视觉结构
- 不为排序单独增加“保存顺序”模式

## 用户确认的交互边界

用户已确认以下产品边界：

- 拖拽范围仅限同一天内
- 采用整张卡片可拖拽的交互方式
- 需要区分卡片上的操作区域，避免与三点菜单等点击行为冲突
- 放手即保存
- 如果当天存在编辑中的动作或新增动作表单，则禁用该天拖拽
- 首版桌面端优先；移动端先保持可浏览但不支持拖拽

## 方案比较

### 方案 A：原生 HTML5 拖拽 + 纯函数重排

优点：

- 不引入第三方依赖
- 当前范围只涉及同日列表重排，复杂度可控
- 可以把顺序变更收敛为 `weeklyPlan` 纯函数，便于测试
- 与现有 `PlanTab -> applyPlanMutation()` 数据链路兼容最好

缺点：

- 需要手动处理拖拽反馈和局部不可拖区域
- 移动端触摸扩展能力较弱

### 方案 B：引入轻量拖拽库

优点：

- 后续扩展移动端拖拽更顺
- 拖拽占位、碰撞判断等能力更完整

缺点：

- 当前需求过小，引入额外依赖和抽象层性价比低
- 需要适配现有卡片菜单、编辑态和周期模式写回，回归面更大

### 方案 C：上移 / 下移按钮替代拖拽

优点：

- 实现风险最低
- 易于键盘操作和无障碍支持

缺点：

- 不符合“动作卡片点击拖曳排序”的明确需求
- 用户心智与预期不一致

### 结论

采用方案 A。

## 现有代码与逻辑分析

### 1. 动作顺序的真实来源

[src/utils/weeklyPlan.js](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/utils/weeklyPlan.js) 中的 `normalizeDayPlan()` 会保留 `exercises` 数组顺序；[src/components/PlanDayCard.jsx](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/components/PlanDayCard.jsx) 直接按 `plan.exercises.map(...)` 渲染。因此：

- 只要重排某天 `exercises` 数组
- 所有展示层顺序会自然更新
- 不需要给动作增加 `sortOrder` 等字段

### 2. 现有保存链路已经满足排序写回需求

[src/tabs/PlanTab.jsx](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/tabs/PlanTab.jsx) 中的 `applyPlanMutation()` 已经统一处理两种模式：

- 手动计划模式：走 `onWeeklyPlanChange(...)`
- 周期 override 模式：走 `backendClient.updateCycleWeekOverride(...)`

因此拖拽排序不应新增单独保存链路，只应作为新的 `planUpdater` 进入 `applyPlanMutation()`。

### 3. 编辑态是现有最高风险状态

[src/utils/planEditorState.js](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/utils/planEditorState.js) 使用 `dayKey + exerciseId + draft` 维护当前唯一编辑态。当前假设是：

- 同一时刻只会有一个目标动作处于编辑态
- 新增动作使用 `NEW_PLAN_EXERCISE_ID`
- 删除当前编辑目标时需要清空编辑态

如果拖拽与编辑态同时开放，最容易引出：

- 编辑目标与列表位置变化不同步
- 新增表单和排序态争抢焦点
- 拖拽过程中误触菜单 / 编辑按钮

因此本设计将“有编辑态时禁用该天拖拽”作为强约束。

### 4. 动作卡片已有局部交互热点

[src/components/PlanExerciseItem.jsx](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/components/PlanExerciseItem.jsx) 中已有：

- 三点菜单按钮
- 编辑入口
- 删除入口
- 编辑态下整块表单

整卡可拖时，必须显式排除这些热点区域，避免点击菜单时触发拖拽起手。

## 架构设计

### 1. 数据模型保持不变

不新增任何排序字段，动作顺序继续由：

- `weeklyPlan[dayKey].exercises[index]`

表达。

这样可以保持：

- 现有动作编辑器输入输出结构不变
- AI 建议采纳与周计划写回结构不变
- 周期快照与手动计划的消费接口不变

### 2. 新增同日重排纯函数

在 [src/utils/weeklyPlan.js](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/utils/weeklyPlan.js) 新增纯函数，例如：

- `reorderExercisesInDay(weeklyPlan, dayKey, fromExerciseId, toExerciseId)`

职责：

- 仅重排指定 `dayKey` 的 `exercises`
- 根据 `fromExerciseId` 和 `toExerciseId` 计算新顺序
- 不修改动作内容本身
- 保留 `weekMeta`
- 不影响其他日期
- 非法 id、相同 id、缺失动作或长度小于 2 时直接返回原计划

这个函数会成为拖拽排序的唯一业务入口。

### 3. 页面层继续复用统一写回入口

在 [src/tabs/PlanTab.jsx](/g:/VSCODE-G/Fitness%20Agent%20MVP/src/tabs/PlanTab.jsx) 新增：

- `handleReorderExercise(dayKey, fromExerciseId, toExerciseId)`

内部逻辑：

- 调用 `applyPlanMutation((currentPlan) => reorderExercisesInDay(...))`
- 捕获周期 override 保存失败时的异常
- 继续复用 `cycleActionMessage` 展示错误

这样拖拽排序与现有：

- 改训练日类型
- 新增动作
- 编辑动作
- 删除动作

共用一套保存路径。

### 4. 组件交互边界

#### `PlanDayCard`

新增职责：

- 计算该天是否允许拖拽
- 给每个动作项透传 `dragEnabled`
- 给每个动作项透传 `onMoveExercise(fromId, toId)`

建议判定条件：

- 当天动作数大于 1
- 当前没有编辑中的已有动作
- 当前没有新增动作表单打开

这样拖拽开关逻辑集中在单日容器，不扩散到其他页面层。

#### `PlanExerciseItem`

新增职责：

- 非编辑态时承载原生拖拽事件
- 维护最小必要的局部视觉反馈
- 识别不可拖热点区域

交互规则：

- 非编辑态且 `dragEnabled=true` 时，整卡允许拖拽
- 编辑态时不允许拖拽
- 操作热点区域通过 `data-no-drag` 标记跳过拖拽起手
- 当前目标卡片仅在 `dragover` 时高亮，不引入复杂占位器

## 组件接口设计

### `weeklyPlan.js`

新增导出：

- `reorderExercisesInDay(weeklyPlan, dayKey, fromExerciseId, toExerciseId)`

输入输出约束：

- 输入保持与现有 `addExerciseToDay / updateExerciseInDay / removeExerciseFromDay` 同级
- 输出保持完整 `weeklyPlan`
- 复用现有 `updateDayPlan(...)` 保持顶层元数据一致

### `PlanTab`

新增内部方法：

- `handleReorderExercise(dayKey, fromExerciseId, toExerciseId)`

新增传参给 `PlanDayCard`：

- `onMoveExercise={(fromId, toId) => handleReorderExercise(column.dayKey, fromId, toId)}`

不新增顶层 React state 来持久存拖拽排序结果，避免页面级状态扩散。

### `PlanDayCard`

新增 props：

- `canReorderExercises`
- `onMoveExercise`

或者仅新增：

- `onMoveExercise`

并在组件内部基于现有 `editingExerciseId`、`plan.exercises.length` 推导是否允许拖拽。二者都可行，但推荐显式传入 `canReorderExercises`，让判定归属更清晰。

### `PlanExerciseItem`

新增 props：

- `dragEnabled`
- `onMoveExercise`

内部新增局部状态：

- `dropActive`：当前卡片是否处于可放置高亮态

不把拖拽中的 DOM 状态提升到 `PlanTab`，因为这不是业务状态，只是局部交互反馈。

## 交互细节

### 拖拽起手

- 用户按住卡片主体区域开始拖拽
- 若起手点落在 `data-no-drag` 区域，则不触发拖拽
- 三点菜单按钮所在容器必须打上 `data-no-drag`

### 拖拽经过

- 悬停目标卡片时，目标卡片显示高亮边框或背景
- 被拖动卡片降低透明度
- 不引入额外占位骨架，避免大幅改造列表结构

### 放手

- 若目标动作有效且与源动作不同，则立即触发 `onMoveExercise`
- 放手后立刻走当前计划写回链路
- 所有局部高亮状态清空

### 禁用情形

以下情况整天禁用拖拽：

- 当前天有编辑中的已有动作
- 当前天新增动作表单正在展开
- 当前天动作数量小于 2

### 移动端降级

首版不实现触摸拖拽，但页面应保持：

- 正常浏览
- 编辑 / 删除 / 菜单功能可用
- 不因为 `draggable` 逻辑影响点击

## 数据流

### 手动计划模式

1. 用户在同一天内拖动动作卡片
2. `PlanExerciseItem` 识别 `fromExerciseId / toExerciseId`
3. `PlanDayCard` 调用 `onMoveExercise`
4. `PlanTab.handleReorderExercise()` 调用 `applyPlanMutation(...)`
5. `reorderExercisesInDay()` 返回新的 `weeklyPlan`
6. `onWeeklyPlanChange(...)` 写回页面状态与后端同步链路

### 周期 override 模式

1. 用户在当前周期周快照中拖动动作卡片
2. `PlanTab.handleReorderExercise()` 仍调用 `applyPlanMutation(...)`
3. `applyPlanMutation()` 走 `backendClient.updateCycleWeekOverride(...)`
4. 后端返回新的 `effectivePlan`
5. 前端继续通过 `onEffectiveWeeklyPlanChange(...)` 刷新页面

## 失败处理

- `fromExerciseId` 不存在：返回原计划
- `toExerciseId` 不存在：返回原计划
- 两个 id 相同：返回原计划
- 当天动作少于 2 个：不触发写回
- 周期 override 保存失败：沿用现有 `cycleActionMessage` 报错

首版不做复杂乐观回滚，直接沿用当前异步保存语义，保持行为一致性。

## 测试设计

本次实现应继续遵守当前项目的 TDD 和最小验证策略。

### 纯函数测试

在 [tests/weeklyPlan.test.js](/g:/VSCODE-G/Fitness%20Agent%20MVP/tests/weeklyPlan.test.js) 新增：

- 同一天内动作顺序正确调整
- 其他天不受影响
- `weekMeta` 保留
- 非法 id 时返回原计划
- 相同源目标 id 时返回原计划
- 单动作日返回原计划

### 页面状态 / 交互判定测试

可在 [tests/planEditorState.test.js](/g:/VSCODE-G/Fitness%20Agent%20MVP/tests/planEditorState.test.js) 或新增专门测试中覆盖：

- 编辑态存在时禁用拖拽
- 新增表单展开时禁用拖拽
- 重排后动作内容不变，仅顺序变化

### 源码契约测试

新增或扩展测试验证：

- `PlanTab` 的排序仍走 `applyPlanMutation(...)`
- `PlanExerciseItem` 同时保留菜单入口和拖拽属性
- 菜单按钮或操作区域带有不可拖拽隔离标记

### 浏览器自动化验证

由于本功能涉及真实拖拽交互、局部热点和放手即保存，建议补一条 Playwright 验证：

- 打开训练计划页
- 在同一天拖动两张动作卡片
- 放手后顺序立刻变化
- 刷新后顺序保持

## 风险与处理

### 风险 1：整卡可拖与局部按钮冲突

处理：

- 对菜单按钮和未来操作区统一打 `data-no-drag`
- 在拖拽起手处优先判断事件源是否位于不可拖区域

### 风险 2：编辑态与拖拽态缠绕

处理：

- 只要当天存在编辑态，就整体禁用拖拽
- 不允许“编辑中卡片也能被拖动”

### 风险 3：周期 override 写回出现分叉逻辑

处理：

- 排序必须走 `applyPlanMutation(...)`
- 禁止直接在拖拽组件中调用单独 API

### 风险 4：为了拖拽引入额外持久化字段

处理：

- 不新增 `sortOrder`
- 只使用数组顺序表达排序

### 风险 5：移动端误触行为不稳定

处理：

- 首版明确不承诺触摸拖拽
- 桌面端实现完成后再单独评估移动端扩展

## 影响范围

### 前端页面与组件

- `src/tabs/PlanTab.jsx`
- `src/components/PlanDayCard.jsx`
- `src/components/PlanExerciseItem.jsx`

### 前端工具层

- `src/utils/weeklyPlan.js`
- 如需要，新增小型拖拽判定 helper，但不应把 DOM 行为塞进业务工具层

### 测试

- `tests/weeklyPlan.test.js`
- `tests/planEditorState.test.js`
- 视实现情况新增训练计划拖拽相关测试文件
- 补充一条 Playwright 拖拽验证

### 文档

- `README.md`
- `ARCHITECTURE.md`

## 验收标准

- 用户可以在训练计划页同一天内通过拖拽重排动作卡片
- 放手后顺序立即保存并稳定显示
- 编辑、删除、三点菜单和新增动作流程不受影响
- 周期 override 模式下的当前周动作顺序也能正常写回
- 非法拖放、编辑中拖放、单动作日拖放都不会破坏现有计划数据
- 相关测试覆盖纯函数、交互边界和至少一条真实浏览器拖拽路径
