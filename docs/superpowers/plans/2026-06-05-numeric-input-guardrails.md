# Numeric Input Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为“我的档案”“今日日志”“训练计划”页建立统一的数值范围约束，做到输入阶段限制、字段级错误提示、保存前复核和文档同步。

**Architecture:** 先新增一个前端共享数值规则模块，集中定义范围、输入约束和错误文案；再分两层接线，一层接到表单输入组件，一层接到 `profile / today log / exercise / cycle payload` 的保存前工具函数，保证 UI 和数据层共用同一份规则来源。

**Tech Stack:** React 19、Vite、Node built-in test runner、Tailwind CSS

---

### Task 1: 建立共享数值规则层

**Files:**
- Create: `src/utils/numericFieldGuardrails.js`
- Create: `tests/numericFieldGuardrails.test.js`

- [ ] **Step 1: Write the failing test**

```js
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  NUMERIC_FIELD_GUARDRAILS,
  getNumericFieldGuardrail,
  validateNumericFieldValue,
  clampNumericInputDraft,
} from '../src/utils/numericFieldGuardrails.js'

test('共享规则层会返回档案体重和动作 RPE 的范围配置', () => {
  assert.equal(getNumericFieldGuardrail('profile.basic.weight').min, 25)
  assert.equal(getNumericFieldGuardrail('profile.basic.weight').max, 300)
  assert.equal(getNumericFieldGuardrail('plan.exercise.rpe').min, 0)
  assert.equal(getNumericFieldGuardrail('plan.exercise.rpe').max, 10)
})

test('validateNumericFieldValue 对空值放行，对越界值返回稳定错误文案', () => {
  assert.equal(validateNumericFieldValue('today.weight', ''), null)
  assert.equal(validateNumericFieldValue('today.weight', '82.5'), null)
  assert.match(validateNumericFieldValue('today.weight', '9999'), /体重/)
  assert.match(validateNumericFieldValue('profile.oneRM.bench', '-1'), /卧推 1RM/)
})

test('clampNumericInputDraft 会保留空串，并拒绝越界输入进入下一草稿值', () => {
  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '100',
      nextValue: '',
    }),
    { nextValue: '', error: null },
  )

  assert.deepEqual(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '100',
      nextValue: '120',
    }),
    { nextValue: '120', error: null },
  )

  assert.equal(
    clampNumericInputDraft({
      fieldKey: 'plan.exercise.kg',
      previousValue: '100',
      nextValue: '100000',
    }).nextValue,
    '100',
  )
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/numericFieldGuardrails.test.js`

Expected: FAIL with `Cannot find module '../src/utils/numericFieldGuardrails.js'`

- [ ] **Step 3: Write minimal implementation**

```js
const NUMERIC_FIELD_GUARDRAILS = {
  'profile.basic.age': { label: '年龄', min: 12, max: 100, step: 1 },
  'profile.basic.height': { label: '身高', min: 120, max: 250, step: 0.1, unit: 'cm' },
  'profile.basic.weight': { label: '当前体重', min: 25, max: 300, step: 0.1, unit: 'kg' },
  'profile.basic.waist': { label: '腰围', min: 40, max: 200, step: 0.1, unit: 'cm' },
  'profile.targetWeight': { label: '目标体重', min: 25, max: 300, step: 0.1, unit: 'kg' },
  'profile.oneRM.squat': { label: '深蹲 1RM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'profile.oneRM.bench': { label: '卧推 1RM', min: 5, max: 400, step: 0.1, unit: 'kg' },
  'profile.oneRM.deadlift': { label: '硬拉 1RM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'today.weight': { label: '体重', min: 25, max: 300, step: 0.1, unit: 'kg' },
  'today.kcal': { label: '热量', min: 0, max: 10000, step: 1, unit: 'kcal' },
  'today.protein': { label: '蛋白质', min: 0, max: 400, step: 1, unit: 'g' },
  'today.sleep': { label: '睡眠', min: 0, max: 24, step: 0.1, unit: 'h' },
  'today.steps': { label: '步数', min: 0, max: 100000, step: 1, unit: '步' },
  'today.tdee': { label: 'TDEE', min: 800, max: 7000, step: 1, unit: 'kcal' },
  'today.fatigue': { label: '疲劳度', min: 1, max: 5, step: 1, unit: '/5' },
  'plan.weekMeta.weekNumber': { label: '周数', min: 1, max: 999, step: 1, unit: '周' },
  'plan.exercise.pct': { label: '百分比负重', min: 0.2, max: 1.5, step: 0.01, unit: '倍' },
  'plan.exercise.kg': { label: '固定重量', min: 0.5, max: 500, step: 0.5, unit: 'kg' },
  'plan.exercise.sets': { label: '组数', min: 1, max: 20, step: 1, unit: '组' },
  'plan.exercise.reps': { label: '次数', min: 1, max: 100, step: 1, unit: '次' },
  'plan.exercise.rpe': { label: 'RPE', min: 0, max: 10, step: 0.5, unit: '/10' },
  'plan.cycle.squat.oneRm': { label: '深蹲 1RM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.cycle.squat.tm': { label: '深蹲 TM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.cycle.bench.oneRm': { label: '卧推 1RM', min: 5, max: 400, step: 0.1, unit: 'kg' },
  'plan.cycle.bench.tm': { label: '卧推 TM', min: 5, max: 400, step: 0.1, unit: 'kg' },
  'plan.cycle.deadlift.oneRm': { label: '硬拉 1RM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.cycle.deadlift.tm': { label: '硬拉 TM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.custom.totalWeeks': { label: '周数', min: 1, max: 24, step: 1, unit: '周' },
  'plan.custom.squat.tm': { label: '深蹲 TM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.custom.bench.tm': { label: '卧推 TM', min: 5, max: 400, step: 0.1, unit: 'kg' },
  'plan.custom.deadlift.tm': { label: '硬拉 TM', min: 10, max: 500, step: 0.1, unit: 'kg' },
  'plan.custom.ohp.tm': { label: '推举 TM', min: 5, max: 250, step: 0.1, unit: 'kg' },
}

function parseNumericDraft(value) {
  if (value === null || value === undefined) {
    return null
  }

  const normalized = `${value}`.trim()
  if (!normalized) {
    return null
  }

  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : Number.NaN
}

export function getNumericFieldGuardrail(fieldKey) {
  return NUMERIC_FIELD_GUARDRAILS[fieldKey] ?? null
}

export function validateNumericFieldValue(fieldKey, value) {
  const guardrail = getNumericFieldGuardrail(fieldKey)
  if (!guardrail) {
    return null
  }

  const parsed = parseNumericDraft(value)
  if (parsed === null) {
    return null
  }
  if (!Number.isFinite(parsed) || parsed < guardrail.min || parsed > guardrail.max) {
    return `${guardrail.label} 必须在 ${guardrail.min}-${guardrail.max}${guardrail.unit ?? ''} 之间`
  }

  return null
}

export function clampNumericInputDraft({ fieldKey, previousValue, nextValue }) {
  const error = validateNumericFieldValue(fieldKey, nextValue)
  if (error) {
    return { nextValue: previousValue, error }
  }

  return { nextValue, error: null }
}

export { NUMERIC_FIELD_GUARDRAILS }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/numericFieldGuardrails.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/numericFieldGuardrails.js tests/numericFieldGuardrails.test.js
git commit -m "新增共享数值范围规则层"
```

### Task 2: 为档案页和今日日志工具层补上保存前复核

**Files:**
- Modify: `src/utils/profileForm.js`
- Modify: `src/utils/dailyLog.js`
- Modify: `src/utils/todayLogView.js`
- Create: `tests/profileForm.test.js`
- Create: `tests/dailyLog.test.js`

- [ ] **Step 1: Write the failing tests**

```js
import test from 'node:test'
import assert from 'node:assert/strict'

import { draftToProfile } from '../src/utils/profileForm.js'
import { normalizeTodayLogEntry } from '../src/utils/dailyLog.js'

test('draftToProfile 会把越界档案数值转成 null，避免非法业务值落库', () => {
  const profile = draftToProfile({
    basic: {
      name: 'A',
      sex: 'male',
      age: '999',
      height: '9999',
      weight: '-1',
      waist: '300',
    },
    oneRM: {
      squat: '100000',
      bench: '-1',
      deadlift: '600',
    },
    goal: '',
    targetWeight: '9999',
    notes: '',
  })

  assert.equal(profile.basic.age, null)
  assert.equal(profile.basic.height, null)
  assert.equal(profile.basic.weight, null)
  assert.equal(profile.oneRM.bench, null)
  assert.equal(profile.targetWeight, null)
})

test('normalizeTodayLogEntry 会保留合法值并清洗越界值', () => {
  const entry = normalizeTodayLogEntry({
    weight: '82.5',
    kcal: '10001',
    protein: '180',
    sleep: '25',
    steps: '-1',
    fatigue: '6',
    tdee: '2500',
    trainingDone: true,
    trainingNotes: 'ok',
  })

  assert.equal(entry.weight, 82.5)
  assert.equal(entry.kcal, null)
  assert.equal(entry.protein, 180)
  assert.equal(entry.sleep, null)
  assert.equal(entry.steps, null)
  assert.equal(entry.fatigue, null)
  assert.equal(entry.tdee, 2500)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- tests/profileForm.test.js tests/dailyLog.test.js`

Expected: FAIL because越界值当前仍会被直接转成数字

- [ ] **Step 3: Write minimal implementation**

```js
import { validateNumericFieldValue } from './numericFieldGuardrails.js'

function toGuardedNumberOrNull(fieldKey, value) {
  if (value === '') {
    return null
  }

  if (validateNumericFieldValue(fieldKey, value)) {
    return null
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}
```

```js
export function draftToProfile(draft) {
  return {
    basic: {
      name: draft.basic.name,
      sex: draft.basic.sex,
      age: toGuardedNumberOrNull('profile.basic.age', draft.basic.age),
      height: toGuardedNumberOrNull('profile.basic.height', draft.basic.height),
      weight: toGuardedNumberOrNull('profile.basic.weight', draft.basic.weight),
      waist: toGuardedNumberOrNull('profile.basic.waist', draft.basic.waist),
    },
    oneRM: {
      squat: toGuardedNumberOrNull('profile.oneRM.squat', draft.oneRM.squat),
      bench: toGuardedNumberOrNull('profile.oneRM.bench', draft.oneRM.bench),
      deadlift: toGuardedNumberOrNull('profile.oneRM.deadlift', draft.oneRM.deadlift),
    },
    goal: draft.goal,
    targetWeight: toGuardedNumberOrNull('profile.targetWeight', draft.targetWeight),
    notes: draft.notes,
  }
}
```

```js
export function normalizeTodayLogEntry(form = {}) {
  return {
    weight: toGuardedNumberOrNull('today.weight', form.weight),
    kcal: toGuardedNumberOrNull('today.kcal', form.kcal),
    protein: toGuardedNumberOrNull('today.protein', form.protein),
    sleep: toGuardedNumberOrNull('today.sleep', form.sleep),
    steps: toGuardedNumberOrNull('today.steps', form.steps),
    fatigue: toGuardedNumberOrNull('today.fatigue', form.fatigue),
    tdee: toGuardedNumberOrNull('today.tdee', form.tdee),
    trainingDone: Boolean(form.trainingDone),
    trainingNotes: `${form.trainingNotes ?? ''}`.trim(),
  }
}
```

```js
const TODAY_LOG_FIELDS = {
  weight: {
    key: 'weight',
    guardrailKey: 'today.weight',
  },
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- tests/profileForm.test.js tests/dailyLog.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/profileForm.js src/utils/dailyLog.js src/utils/todayLogView.js tests/profileForm.test.js tests/dailyLog.test.js
git commit -m "补齐档案与今日日志数值保存前校验"
```

### Task 3: 接通档案页和今日日志页的输入阶段限制与提示

**Files:**
- Modify: `src/tabs/ProfileTab.jsx`
- Modify: `src/tabs/TodayTab.jsx`
- Modify: `tests/profileTab.test.js`
- Modify: `tests/todayTab.test.js`

- [ ] **Step 1: Write the failing tests**

```js
test('ProfileTab 源码会为档案数值输入挂接共享 guardrail 约束与错误提示', () => {
  const source = readFileSync('src/tabs/ProfileTab.jsx', 'utf-8')

  assert.match(source, /getNumericFieldGuardrail/)
  assert.match(source, /validateNumericFieldValue/)
  assert.match(source, /profile\.basic\.weight|profile\.basic\.age/)
  assert.match(source, /aria-invalid=/)
})

test('TodayTab 源码会为日志数值输入挂接共享 guardrail 约束与错误提示', () => {
  const source = readFileSync('src/tabs/TodayTab.jsx', 'utf-8')

  assert.match(source, /getNumericFieldGuardrail/)
  assert.match(source, /validateNumericFieldValue/)
  assert.match(source, /today\.\$\{field\.key\}|today\.weight/)
  assert.match(source, /aria-invalid=/)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- tests/profileTab.test.js tests/todayTab.test.js`

Expected: FAIL because页面源码当前没有共享 guardrail 接线

- [ ] **Step 3: Write minimal implementation**

```jsx
const [fieldErrors, setFieldErrors] = useState({})

function updateGuardedDraft(group, key, fieldKey, value) {
  const error = validateNumericFieldValue(fieldKey, value)

  setFieldErrors((current) => ({
    ...current,
    [fieldKey]: error,
  }))

  if (error && value !== '') {
    return
  }

  updateNestedField(group, key, value)
}
```

```jsx
const guardrail = getNumericFieldGuardrail(`today.${field.key}`)

<input
  aria-invalid={Boolean(fieldErrors[`today.${field.key}`])}
  max={guardrail?.max}
  min={guardrail?.min}
  step={guardrail?.step ?? field.step}
/>
<span>{fieldErrors[`today.${field.key}`] ?? field.hint}</span>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- tests/profileTab.test.js tests/todayTab.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tabs/ProfileTab.jsx src/tabs/TodayTab.jsx tests/profileTab.test.js tests/todayTab.test.js
git commit -m "接通档案页和今日日志页输入边界提示"
```

### Task 4: 为动作编辑、周数编辑和周期 payload 建立统一校验

**Files:**
- Modify: `src/utils/exerciseForm.js`
- Modify: `src/utils/cyclePlanForm.js`
- Modify: `src/utils/customStrengthPlanForm.js`
- Modify: `tests/exerciseForm.test.js`
- Modify: `tests/cyclePlanForm.test.js`
- Modify: `tests/customStrengthPlanForm.test.js`
- Modify: `tests/planHeader.test.js`

- [ ] **Step 1: Write the failing tests**

```js
test('buildExerciseSavePayload 会阻止非法固定重量、组数、次数和百分比进入保存结果', () => {
  assert.equal(
    exerciseForm.buildExerciseSavePayload({
      name: '深蹲',
      weightMode: 'fixed',
      kg: '100000',
      sets: '0',
      reps: '101',
      rpe: '8',
      note: '',
    }),
    null,
  )

  assert.equal(
    exerciseForm.buildExerciseSavePayload({
      name: '卧推',
      weightMode: 'percentage',
      ref1RM: 'bench',
      pct: '2',
      sets: '4',
      reps: '6',
      rpe: '8',
      note: '',
    }),
    null,
  )
})

test('buildCreateCyclePlanPayload 会把越界 1RM 和 TM 清洗为 null', () => {
  const payload = buildCreateCyclePlanPayload({
    presetKey: 'madcow_5x5',
    startDate: '2026-06-08',
    goal: 'strength',
    baseLifts: {
      squat: { oneRm: '100000', tm: '-1' },
      bench: { oneRm: '120', tm: '110' },
      deadlift: { oneRm: '220', tm: '9999' },
    },
    config: { trainingDays: ['Monday'] },
  })

  assert.equal(payload.baseLifts.squat.oneRm, null)
  assert.equal(payload.baseLifts.squat.tm, null)
  assert.equal(payload.baseLifts.deadlift.tm, null)
  assert.equal(payload.baseLifts.bench.oneRm, 120)
})

test('buildCreateCustomStrengthCyclePayload 会限制总周数和主项 TM 边界', () => {
  const payload = buildCreateCustomStrengthCyclePayload({
    name: 'test',
    startDate: '2026-06-09',
    totalWeeks: 99,
    mainLifts: {
      squat: { tm: '9999' },
      bench: { tm: '120' },
      deadlift: { tm: '-1' },
      ohp: { tm: '80' },
    },
    weeks: [{ weekIndex: 1, days: [] }],
  })

  assert.equal(payload.baseLifts.squat, undefined)
  assert.equal(payload.baseLifts.deadlift, undefined)
  assert.equal(payload.baseLifts.bench.tm, 120)
  assert.equal(payload.config.totalWeeks, 1)
})

test('PlanHeaderToolbar 源码会限制编辑周数输入范围', () => {
  const source = readWorkspaceFile('src/components/plan-header/PlanHeaderToolbar.jsx')

  assert.match(source, /getNumericFieldGuardrail/)
  assert.match(source, /plan\.weekMeta\.weekNumber/)
  assert.match(source, /max=/)
  assert.match(source, /min=/)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- tests/exerciseForm.test.js tests/cyclePlanForm.test.js tests/customStrengthPlanForm.test.js tests/planHeader.test.js`

Expected: FAIL because这些字段当前仍可直接进入 payload 或源码还未接 guardrail

- [ ] **Step 3: Write minimal implementation**

```js
function getExerciseFieldError(draft = {}) {
  return (
    validateNumericFieldValue('plan.exercise.kg', draft.kg) ??
    validateNumericFieldValue('plan.exercise.pct', draft.pct) ??
    validateNumericFieldValue('plan.exercise.sets', draft.sets) ??
    validateNumericFieldValue('plan.exercise.reps', draft.reps) ??
    validateNumericFieldValue('plan.exercise.rpe', draft.rpe)
  )
}

export function buildExerciseSavePayload(draft = {}) {
  if (getExerciseFieldError(draft)) {
    return null
  }

  return draftToExercise(draft)
}
```

```js
function normalizeGuardedNumber(fieldKey, value) {
  if (validateNumericFieldValue(fieldKey, value)) {
    return null
  }

  const parsedValue = Number(value)
  return Number.isFinite(parsedValue) ? parsedValue : null
}
```

```jsx
const weekNumberGuardrail = getNumericFieldGuardrail('plan.weekMeta.weekNumber')

<input
  max={weekNumberGuardrail?.max}
  min={weekNumberGuardrail?.min}
  step={weekNumberGuardrail?.step}
/>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- tests/exerciseForm.test.js tests/cyclePlanForm.test.js tests/customStrengthPlanForm.test.js tests/planHeader.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/exerciseForm.js src/utils/cyclePlanForm.js src/utils/customStrengthPlanForm.js src/components/plan-header/PlanHeaderToolbar.jsx tests/exerciseForm.test.js tests/cyclePlanForm.test.js tests/customStrengthPlanForm.test.js tests/planHeader.test.js
git commit -m "补齐训练计划与周期计划数值边界校验"
```

### Task 5: 接通动作编辑器、周期设置和自定义力量周期输入限制

**Files:**
- Modify: `src/components/ExerciseEditor.jsx`
- Modify: `src/components/plan-settings/PlanSettingsPanel.jsx`
- Modify: `src/components/plan-settings/CustomStrengthPlanEditor.jsx`
- Modify: `src/components/plan-settings/CustomStrengthMainLiftEditor.jsx`
- Modify: `tests/profileTab.test.js`

- [ ] **Step 1: Write the failing test**

```js
test('训练计划相关源码会为动作编辑器和周期设置挂接共享数值 guardrail', () => {
  const exerciseEditorSource = readFileSync('src/components/ExerciseEditor.jsx', 'utf-8')
  const planSettingsSource = readFileSync('src/components/plan-settings/PlanSettingsPanel.jsx', 'utf-8')
  const customPlanSource = readFileSync('src/components/plan-settings/CustomStrengthPlanEditor.jsx', 'utf-8')
  const customLiftSource = readFileSync('src/components/plan-settings/CustomStrengthMainLiftEditor.jsx', 'utf-8')

  assert.match(exerciseEditorSource, /getNumericFieldGuardrail/)
  assert.match(exerciseEditorSource, /aria-invalid=/)
  assert.match(planSettingsSource, /getNumericFieldGuardrail/)
  assert.match(customPlanSource, /getNumericFieldGuardrail/)
  assert.match(customLiftSource, /getNumericFieldGuardrail/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/profileTab.test.js`

Expected: FAIL because这些组件源码目前没有共享 guardrail 接线

- [ ] **Step 3: Write minimal implementation**

```jsx
const kgGuardrail = getNumericFieldGuardrail('plan.exercise.kg')
const pctGuardrail = getNumericFieldGuardrail('plan.exercise.pct')
const setsGuardrail = getNumericFieldGuardrail('plan.exercise.sets')
const repsGuardrail = getNumericFieldGuardrail('plan.exercise.reps')
const rpeGuardrail = getNumericFieldGuardrail('plan.exercise.rpe')
```

```jsx
<input
  aria-invalid={Boolean(fieldErrors.kg)}
  max={kgGuardrail?.max}
  min={kgGuardrail?.min}
  step={kgGuardrail?.step}
/>
```

```jsx
const totalWeeksGuardrail = getNumericFieldGuardrail('plan.custom.totalWeeks')
<input
  max={totalWeeksGuardrail?.max}
  min={totalWeeksGuardrail?.min}
  type="number"
/>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/profileTab.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/ExerciseEditor.jsx src/components/plan-settings/PlanSettingsPanel.jsx src/components/plan-settings/CustomStrengthPlanEditor.jsx src/components/plan-settings/CustomStrengthMainLiftEditor.jsx tests/profileTab.test.js
git commit -m "接通训练计划表单数值输入边界提示"
```

### Task 6: 同步文档并做整体验证

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`

- [ ] **Step 1: Write the failing documentation assertions**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('README 和 ARCHITECTURE 会说明数值输入边界约束层', () => {
  const readme = readFileSync('README.md', 'utf-8')
  const architecture = readFileSync('ARCHITECTURE.md', 'utf-8')

  assert.match(readme, /数值范围|输入边界|异常数值/)
  assert.match(architecture, /共享数值规则|输入阶段限制|保存前复核/)
})
```

- [ ] **Step 2: Run documentation assertion to verify it fails**

Run: `npm test -- tests/profileTab.test.js`

Expected: FAIL after将断言加入现有测试文件或新增文档测试文件

- [ ] **Step 3: Update documentation**

```md
## 当前能力

- 关键数值字段具备输入边界约束，避免出现明显不合理的体重、1RM、动作重量和周期 TM
```

```md
### 前端状态与输入约束

- 数值字段统一通过共享 guardrail 规则层定义 `min / max / step`
- 页面输入阶段即时提示越界值
- `profile / dailyLog / exercise / cycle payload` 在保存前再次复核
```

- [ ] **Step 4: Run full verification**

Run: `npm test`

Expected: PASS with 0 failures

Run: `npm run build`

Expected: build succeeds with exit code 0

- [ ] **Step 5: Commit**

```bash
git add README.md ARCHITECTURE.md tests/profileTab.test.js
git commit -m "同步数值输入边界约束文档与验证记录"
```
