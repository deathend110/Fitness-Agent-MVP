# Plan Card Drag Sort Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为训练计划页实现“同一天内动作卡片整卡拖拽排序，放手即保存”，且不影响现有动作卡片编辑、删除、菜单和周期 override 流程。

**Architecture:** 在 `weeklyPlan` 工具层新增同日动作重排纯函数，作为唯一排序业务入口；页面层继续通过 `PlanTab -> applyPlanMutation()` 复用现有手动计划与周期 override 写回链路；拖拽交互只落在 `PlanDayCard / PlanExerciseItem` 层，并通过显式禁用条件和不可拖区域标记隔离现有编辑与菜单行为。

**Tech Stack:** React 19、Vite、Node built-in test runner、Tailwind CSS、Playwright（通过 `uv run python ...` 执行）

---

### Task 1: 补齐同日动作重排纯函数

**Files:**
- Modify: `src/utils/weeklyPlan.js`
- Modify: `tests/weeklyPlan.test.js`

- [ ] **Step 1: Write the failing tests**

```js
test('reorderExercisesInDay 会在同一天内调整动作顺序并保留动作内容', () => {
  const nextPlan = reorderExercisesInDay(demoWeeklyPlan, 'Monday', 'monday-rdl', 'monday-squat')

  assert.deepEqual(
    nextPlan.Monday.exercises.map((exercise) => exercise.id),
    ['monday-rdl', 'monday-squat'],
  )
  assert.equal(nextPlan.Monday.exercises[0].name, demoWeeklyPlan.Monday.exercises[1].name)
  assert.equal(nextPlan.Tuesday.exercises.length, demoWeeklyPlan.Tuesday.exercises.length)
})

test('reorderExercisesInDay 会保留 weekMeta 并在非法输入时返回原计划', () => {
  const weeklyPlan = {
    ...demoWeeklyPlan,
    weekMeta: {
      weekNumber: 23,
      weekStart: '2026-06-01',
      weekEnd: '2026-06-07',
    },
  }

  const samePlan = reorderExercisesInDay(weeklyPlan, 'Monday', 'monday-squat', 'monday-squat')
  const missingTargetPlan = reorderExercisesInDay(weeklyPlan, 'Monday', 'missing', 'monday-rdl')

  assert.deepEqual(samePlan, weeklyPlan)
  assert.deepEqual(missingTargetPlan, weeklyPlan)
  assert.deepEqual(
    reorderExercisesInDay(weeklyPlan, 'Monday', 'monday-rdl', 'monday-squat').weekMeta,
    weeklyPlan.weekMeta,
  )
})

test('reorderExercisesInDay 遇到单动作日时不做变更', () => {
  const weeklyPlan = {
    ...demoWeeklyPlan,
    Tuesday: {
      ...demoWeeklyPlan.Tuesday,
      exercises: [demoWeeklyPlan.Tuesday.exercises[0]],
    },
  }

  assert.deepEqual(
    reorderExercisesInDay(weeklyPlan, 'Tuesday', weeklyPlan.Tuesday.exercises[0].id, weeklyPlan.Tuesday.exercises[0].id),
    weeklyPlan,
  )
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- tests/weeklyPlan.test.js`

Expected: FAIL with `reorderExercisesInDay is not exported` or equivalent missing symbol failure.

- [ ] **Step 3: Write minimal implementation**

```js
export function reorderExercisesInDay(weeklyPlan, dayKey, fromExerciseId, toExerciseId) {
  if (!fromExerciseId || !toExerciseId || fromExerciseId === toExerciseId) {
    return weeklyPlan
  }

  return updateDayPlan(weeklyPlan, dayKey, (dayPlan) => {
    if (!Array.isArray(dayPlan.exercises) || dayPlan.exercises.length < 2) {
      return dayPlan
    }

    const currentIndex = dayPlan.exercises.findIndex((exercise) => exercise.id === fromExerciseId)
    const targetIndex = dayPlan.exercises.findIndex((exercise) => exercise.id === toExerciseId)

    if (currentIndex < 0 || targetIndex < 0 || currentIndex === targetIndex) {
      return dayPlan
    }

    const nextExercises = [...dayPlan.exercises]
    const [movedExercise] = nextExercises.splice(currentIndex, 1)
    nextExercises.splice(targetIndex, 0, movedExercise)

    return {
      ...dayPlan,
      exercises: nextExercises,
    }
  })
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- tests/weeklyPlan.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/weeklyPlan.js tests/weeklyPlan.test.js
git commit -m "新增训练计划动作同日重排工具"
```

### Task 2: 补齐拖拽启用判定和页面状态约束

**Files:**
- Modify: `src/utils/planEditorState.js`
- Modify: `tests/planEditorState.test.js`

- [ ] **Step 1: Write the failing tests**

```js
test('canReorderPlanDayExercises 仅在无编辑态且动作数大于 1 时允许拖拽', () => {
  assert.equal(
    canReorderPlanDayExercises({
      editingState: clearPlanEditorState(),
      dayKey: 'Monday',
      exerciseCount: 2,
    }),
    true,
  )

  assert.equal(
    canReorderPlanDayExercises({
      editingState: startEditingExercise('Monday', { id: 'monday-squat', name: '深蹲' }, []),
      dayKey: 'Monday',
      exerciseCount: 2,
    }),
    false,
  )

  assert.equal(
    canReorderPlanDayExercises({
      editingState: startAddingExercise('Monday', []),
      dayKey: 'Monday',
      exerciseCount: 2,
    }),
    false,
  )

  assert.equal(
    canReorderPlanDayExercises({
      editingState: clearPlanEditorState(),
      dayKey: 'Monday',
      exerciseCount: 1,
    }),
    false,
  )
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- tests/planEditorState.test.js`

Expected: FAIL because `canReorderPlanDayExercises` does not exist.

- [ ] **Step 3: Write minimal implementation**

```js
export function canReorderPlanDayExercises({ editingState, dayKey, exerciseCount }) {
  if (!Number.isInteger(exerciseCount) || exerciseCount < 2) {
    return false
  }

  if (editingState?.dayKey !== dayKey) {
    return true
  }

  return false
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- tests/planEditorState.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/planEditorState.js tests/planEditorState.test.js
git commit -m "补齐训练计划拖拽启用判定"
```

### Task 3: 在 PlanTab 接通排序写回入口

**Files:**
- Modify: `src/tabs/PlanTab.jsx`
- Modify: `tests/profileTab.test.js`

- [ ] **Step 1: Write the failing test**

```js
test('PlanTab 源码会通过 applyPlanMutation 接通动作拖拽排序写回', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /reorderExercisesInDay/)
  assert.match(source, /handleReorderExercise/)
  assert.match(source, /applyPlanMutation\(\(currentPlan\)\s*=>\s*reorderExercisesInDay/)
  assert.match(source, /onMoveExercise/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/profileTab.test.js`

Expected: FAIL because `PlanTab.jsx` does not yet include reorder wiring.

- [ ] **Step 3: Write minimal implementation**

```jsx
import {
  addExerciseToDay,
  removeExerciseFromDay,
  reorderExercisesInDay,
  updateDayType,
  updateExerciseInDay,
} from '../utils/weeklyPlan.js'
```

```jsx
async function handleReorderExercise(dayKey, fromExerciseId, toExerciseId) {
  try {
    await applyPlanMutation((currentPlan) =>
      reorderExercisesInDay(currentPlan, dayKey, fromExerciseId, toExerciseId),
    )
  } catch (error) {
    setCycleActionMessage(error.message)
  }
}
```

```jsx
onMoveExercise={(fromId, toId) => handleReorderExercise(column.dayKey, fromId, toId)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/profileTab.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tabs/PlanTab.jsx tests/profileTab.test.js
git commit -m "接通训练计划动作拖拽排序写回入口"
```

### Task 4: 在 PlanDayCard 传递拖拽能力并隔离编辑态

**Files:**
- Modify: `src/components/PlanDayCard.jsx`
- Modify: `tests/planLayout.test.js`

- [ ] **Step 1: Write the failing test**

```js
test('PlanDayCard 源码会按动作数和编辑态决定是否允许动作拖拽', () => {
  const cardSource = readWorkspaceFile('src/components/PlanDayCard.jsx')

  assert.match(cardSource, /canReorderPlanDayExercises|dragEnabled/)
  assert.match(cardSource, /onMoveExercise/)
  assert.match(cardSource, /plan\.exercises\.length/)
  assert.match(cardSource, /editingExerciseId/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/planLayout.test.js`

Expected: FAIL because `PlanDayCard.jsx` does not yet calculate drag availability or pass reorder props.

- [ ] **Step 3: Write minimal implementation**

```jsx
import { NEW_PLAN_EXERCISE_ID, canReorderPlanDayExercises } from '../utils/planEditorState.js'
```

```jsx
const dragEnabled = canReorderPlanDayExercises({
  editingState: {
    dayKey,
    exerciseId: editingExerciseId,
  },
  dayKey,
  exerciseCount: plan.exercises.length,
}) && editingExerciseId !== NEW_PLAN_EXERCISE_ID
```

```jsx
<PlanExerciseItem
  dragEnabled={dragEnabled}
  onMoveExercise={onMoveExercise}
  ...
/>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/planLayout.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/PlanDayCard.jsx tests/planLayout.test.js
git commit -m "接通训练计划日卡片拖拽开关"
```

### Task 5: 在动作卡片实现整卡拖拽并隔离操作区域

**Files:**
- Modify: `src/components/PlanExerciseItem.jsx`
- Modify: `tests/planExerciseCard.test.js`

- [ ] **Step 1: Write the failing test**

```js
test('PlanExerciseItem 会保留菜单入口并为整卡拖拽添加隔离操作区', () => {
  const source = fs.readFileSync(new URL('../src/components/PlanExerciseItem.jsx', import.meta.url), 'utf8')

  assert.match(source, /draggable=\{dragEnabled\}/)
  assert.match(source, /onDragStart=/)
  assert.match(source, /onDragOver=/)
  assert.match(source, /onDrop=/)
  assert.match(source, /data-no-drag/)
  assert.match(source, /aria-label="更多操作"/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/planExerciseCard.test.js`

Expected: FAIL because drag props and `data-no-drag` markers are missing.

- [ ] **Step 3: Write minimal implementation**

```jsx
const [dropActive, setDropActive] = useState(false)

function isNoDragTarget(target) {
  return target instanceof HTMLElement && Boolean(target.closest('[data-no-drag="true"]'))
}

function handleDragStart(event) {
  if (!dragEnabled || isNoDragTarget(event.target)) {
    event.preventDefault()
    return
  }

  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', exercise.id)
}

function handleDrop(event) {
  event.preventDefault()
  setDropActive(false)
  const fromExerciseId = event.dataTransfer.getData('text/plain')
  onMoveExercise?.(fromExerciseId, exercise.id)
}
```

```jsx
<li
  className={`rounded-xl border px-3 py-3 shadow-sm shadow-black/20 ${cardModel.cardClassName} ${
    dropActive ? 'ring-2 ring-fitloop-orange/70' : ''
  }`}
  draggable={dragEnabled}
  onDragEnd={() => setDropActive(false)}
  onDragOver={(event) => {
    if (!dragEnabled) {
      return
    }
    event.preventDefault()
    setDropActive(true)
  }}
  onDragStart={handleDragStart}
  onDrop={handleDrop}
>
```

```jsx
<div className="relative shrink-0" data-no-drag="true" ref={menuRef}>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/planExerciseCard.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/PlanExerciseItem.jsx tests/planExerciseCard.test.js
git commit -m "实现训练计划动作卡片整卡拖拽交互"
```

### Task 6: 补齐拖拽回归测试并同步文档

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Create or Modify: `tests/e2e/plan_drag_sort.py`

- [ ] **Step 1: Write the failing browser validation script**

```python
from tests.e2e.coach_e2e_helpers import run_app_with_mock_state

def test_plan_drag_sort_persists():
    with run_app_with_mock_state() as app:
        page = app.page
        page.goto(app.url)
        page.get_by_role("tab", name="训练计划").click()

        monday_cards = page.locator('[data-day-key="Monday"] [data-exercise-id]')
        before_first = monday_cards.nth(0).text_content()
        before_second = monday_cards.nth(1).text_content()

        page.drag_and_drop(
            '[data-day-key="Monday"] [data-exercise-id="monday-rdl"]',
            '[data-day-key="Monday"] [data-exercise-id="monday-squat"]',
        )

        after_first = monday_cards.nth(0).text_content()
        assert after_first == before_second

        page.reload()
        reloaded_first = page.locator('[data-day-key="Monday"] [data-exercise-id]').nth(0).text_content()
        assert reloaded_first == before_second
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `npm test -- tests/weeklyPlan.test.js tests/planEditorState.test.js tests/profileTab.test.js tests/planLayout.test.js tests/planExerciseCard.test.js`

Expected: PASS only after previous tasks; before browser script wiring, the Playwright script should fail because test hooks/attributes are not complete.

Run: `uv run python tests/e2e/plan_drag_sort.py`

Expected: FAIL because drag test selectors or behavior are not yet fully wired.

- [ ] **Step 3: Finalize selectors, docs, and verification support**

```jsx
<li data-exercise-id={exercise.id} ...>
```

```jsx
<div data-day-key={dayKey} className="flex h-full min-w-0 flex-col">
```

```md
## 当前能力

- 训练计划页支持同一天内动作卡片拖拽排序，放手即保存
```

```md
### 训练计划页

- 动作列表顺序由 `weeklyPlan[dayKey].exercises` 数组驱动
- 同日拖拽排序通过 `reorderExercisesInDay()` 和 `applyPlanMutation()` 统一写回
```

- [ ] **Step 4: Run full verification**

Run: `npm test`

Expected: PASS with 0 failures

Run: `npm run build`

Expected: build succeeds with exit code 0

Run: `uv run python tests/e2e/plan_drag_sort.py`

Expected: PASS with drag sort order persisting after reload

- [ ] **Step 5: Commit**

```bash
git add README.md ARCHITECTURE.md src/components/PlanDayCard.jsx src/components/PlanExerciseItem.jsx tests/e2e/plan_drag_sort.py
git commit -m "补充训练计划动作拖拽排序文档与验证"
```
