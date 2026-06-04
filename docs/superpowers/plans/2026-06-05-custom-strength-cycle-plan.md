# Custom Strength Cycle Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有周期计划模式上落地第一版自定义力量周期计划，支持手动定义主项 `%TM` 周递进、静态辅助动作，并一次性生成全部周快照接入当前 `effectiveWeeklyPlan` 消费链路。

**Architecture:** 复用现有 `active_cycle_plan / cycle_week_snapshot / effectiveWeeklyPlan` 运行时骨架，把“自定义力量计划定义层”和“自定义力量生成层”拆成独立模块。后端通过 `custom_strength_definition.py` 校验归一化用户定义，通过 `custom_strength_engine.py` 编译出多周 `weeklyPlan`；前端通过独立 editor 组件维护草稿与 payload 映射，`PlanTab` 只负责入口与状态编排。

**Tech Stack:** FastAPI, SQLAlchemy Async, Pydantic, React 19, Vite, Node test runner, pytest, Playwright

---

## File Map

### Create

- `backend/plans/custom_strength_definition.py`
- `backend/plans/custom_strength_engine.py`
- `backend/tests/test_custom_strength_definition.py`
- `backend/tests/test_custom_strength_engine.py`
- `src/utils/customStrengthPlanForm.js`
- `src/components/plan-settings/CustomStrengthPlanEditor.jsx`
- `src/components/plan-settings/CustomStrengthWeekEditor.jsx`
- `src/components/plan-settings/CustomStrengthMainLiftEditor.jsx`
- `tests/customStrengthPlanForm.test.js`
- `tests/customStrengthPlanEditor.test.js`

### Modify

- `backend/schemas/__init__.py`
- `backend/plans/cycle_service.py`
- `backend/api/cycle_plans.py`
- `backend/tests/test_cycle_api.py`
- `src/api/backendClient.js`
- `src/components/plan-settings/PlanSettingsPanel.jsx`
- `src/tabs/PlanTab.jsx`
- `tests/backendClient.test.js`
- `tests/profileTab.test.js`
- `README.md`
- `ARCHITECTURE.md`

### Do Not Expand With New Logic

- `backend/plans/cycle_engine.py`
- `backend/plans/preset_library.py`
- `src/tabs/PlanTab.jsx` beyond orchestration

---

### Task 1: Add custom strength definition schema and validation

**Files:**
- Create: `backend/tests/test_custom_strength_definition.py`
- Create: `backend/plans/custom_strength_definition.py`
- Modify: `backend/schemas/__init__.py`

- [ ] **Step 1: Write the failing tests for definition normalization and validation**

```python
from __future__ import annotations

import pytest

from backend.plans.custom_strength_definition import normalize_custom_strength_definition


def build_valid_definition() -> dict:
    return {
        "planType": "custom_strength",
        "name": "四周力量周期",
        "startDate": "2026-06-09",
        "totalWeeks": 4,
        "mainLifts": {
            "squat": {"tm": 180},
            "bench": {"tm": 125},
        },
        "weeks": [
            {
                "weekIndex": 1,
                "days": [
                    {
                        "dayIndex": 1,
                        "label": "周一",
                        "type": "lower_strength",
                        "exercises": [
                            {
                                "id": "w1d1-squat",
                                "name": "Back Squat",
                                "category": "main",
                                "progression": {
                                    "mode": "percent_tm",
                                    "liftKey": "squat",
                                    "percentTm": 0.75,
                                },
                                "prescription": {"sets": 5, "reps": 5},
                                "notes": "",
                            }
                        ],
                    }
                ],
            }
        ],
    }


def test_normalize_custom_strength_definition_accepts_minimum_valid_definition() -> None:
    normalized = normalize_custom_strength_definition(build_valid_definition())

    assert normalized["planType"] == "custom_strength"
    assert normalized["totalWeeks"] == 4
    assert normalized["mainLifts"]["squat"]["tm"] == 180.0
    assert normalized["weeks"][0]["days"][0]["exercises"][0]["category"] == "main"


def test_normalize_custom_strength_definition_rejects_missing_tm_for_referenced_main_lift() -> None:
    payload = build_valid_definition()
    payload["mainLifts"].pop("squat")

    with pytest.raises(ValueError, match="squat.*TM"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_percent_tm_on_variation() -> None:
    payload = build_valid_definition()
    payload["weeks"][0]["days"][0]["exercises"][0]["category"] = "variation"

    with pytest.raises(ValueError, match="variation.*percent_tm"):
        normalize_custom_strength_definition(payload)


def test_normalize_custom_strength_definition_rejects_total_weeks_mismatch() -> None:
    payload = build_valid_definition()
    payload["totalWeeks"] = 6

    with pytest.raises(ValueError, match="totalWeeks"):
        normalize_custom_strength_definition(payload)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_custom_strength_definition.py -q`  
Expected: FAIL with `ModuleNotFoundError` for `backend.plans.custom_strength_definition` or missing `normalize_custom_strength_definition`.

- [ ] **Step 3: Add schema models for custom strength payloads**

```python
class CustomStrengthMainLiftSchema(BaseModel):
    tm: float = Field(..., gt=0)


class CustomStrengthExerciseSchema(BaseModel):
    id: str
    name: str
    category: Literal["main", "variation", "accessory"]
    progression: dict[str, Any] = Field(default_factory=dict)
    prescription: dict[str, Any] = Field(default_factory=dict)
    referenceLift: str | None = None
    loadText: str = ""
    notes: str = ""


class CustomStrengthDaySchema(BaseModel):
    dayIndex: int = Field(..., ge=1, le=7)
    label: str
    type: str
    exercises: list[CustomStrengthExerciseSchema] = Field(default_factory=list)


class CustomStrengthWeekSchema(BaseModel):
    weekIndex: int = Field(..., ge=1)
    days: list[CustomStrengthDaySchema] = Field(default_factory=list)


class CustomStrengthDefinitionSchema(BaseModel):
    planType: Literal["custom_strength"]
    name: str
    startDate: str
    totalWeeks: int = Field(..., ge=1)
    mainLifts: dict[str, CustomStrengthMainLiftSchema] = Field(default_factory=dict)
    weeks: list[CustomStrengthWeekSchema] = Field(default_factory=list)
```

- [ ] **Step 4: Implement definition normalization and validation**

```python
from __future__ import annotations

from copy import deepcopy
from typing import Any


VALID_CATEGORIES = {"main", "variation", "accessory"}
VALID_MAIN_LIFTS = {"squat", "bench", "deadlift", "ohp"}


def normalize_custom_strength_definition(payload: dict[str, Any]) -> dict[str, Any]:
    definition = deepcopy(payload) if isinstance(payload, dict) else {}
    if definition.get("planType") != "custom_strength":
        raise ValueError("planType 必须为 custom_strength。")
    total_weeks = int(definition.get("totalWeeks") or 0)
    weeks = definition.get("weeks") if isinstance(definition.get("weeks"), list) else []
    if total_weeks <= 0 or len(weeks) != total_weeks:
        raise ValueError("totalWeeks 与 weeks 定义数量必须一致。")

    main_lifts = definition.get("mainLifts") if isinstance(definition.get("mainLifts"), dict) else {}
    normalized_main_lifts = {}
    for lift_key, lift_value in main_lifts.items():
        if lift_key not in VALID_MAIN_LIFTS:
            continue
        tm_value = float(lift_value.get("tm"))
        if tm_value <= 0:
            raise ValueError(f"{lift_key} 的 TM 必须大于 0。")
        normalized_main_lifts[lift_key] = {"tm": tm_value}

    for week in weeks:
        for day in week.get("days", []):
            for exercise in day.get("exercises", []):
                _validate_custom_strength_exercise(exercise, normalized_main_lifts)

    definition["mainLifts"] = normalized_main_lifts
    return definition


def _validate_custom_strength_exercise(
    exercise: dict[str, Any],
    main_lifts: dict[str, dict[str, float]],
) -> None:
    category = exercise.get("category")
    if category not in VALID_CATEGORIES:
        raise ValueError("动作 category 非法。")
    progression = exercise.get("progression") if isinstance(exercise.get("progression"), dict) else {}
    progression_mode = progression.get("mode")

    if category == "main":
        if progression_mode != "percent_tm":
            raise ValueError("主项动作必须使用 percent_tm。")
        lift_key = progression.get("liftKey")
        if lift_key not in main_lifts:
            raise ValueError(f"{lift_key} 缺少对应 TM。")
        percent_tm = float(progression.get("percentTm"))
        if percent_tm <= 0:
            raise ValueError("主项动作的 percentTm 必须大于 0。")
        return

    if progression_mode == "percent_tm":
        raise ValueError(f"{category} 动作第一版不能使用 percent_tm。")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_custom_strength_definition.py -q`  
Expected: PASS with `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_custom_strength_definition.py backend/plans/custom_strength_definition.py backend/schemas/__init__.py
git commit -m "增加自定义力量计划定义校验"
```

---

### Task 2: Build custom strength multi-week engine

**Files:**
- Create: `backend/tests/test_custom_strength_engine.py`
- Create: `backend/plans/custom_strength_engine.py`

- [ ] **Step 1: Write the failing tests for week compilation**

```python
from __future__ import annotations

from backend.plans.custom_strength_definition import normalize_custom_strength_definition
from backend.plans.custom_strength_engine import build_custom_strength_cycle_weeks


def build_definition() -> dict:
    return normalize_custom_strength_definition(
        {
            "planType": "custom_strength",
            "name": "四周力量周期",
            "startDate": "2026-06-09",
            "totalWeeks": 2,
            "mainLifts": {
                "squat": {"tm": 180},
                "bench": {"tm": 120},
            },
            "weeks": [
                {
                    "weekIndex": 1,
                    "days": [
                        {
                            "dayIndex": 1,
                            "label": "周一",
                            "type": "lower_strength",
                            "exercises": [
                                {
                                    "id": "w1d1-squat",
                                    "name": "Back Squat",
                                    "category": "main",
                                    "progression": {"mode": "percent_tm", "liftKey": "squat", "percentTm": 0.75},
                                    "prescription": {"sets": 5, "reps": 5},
                                    "notes": "",
                                },
                                {
                                    "id": "w1d1-rows",
                                    "name": "Barbell Row",
                                    "category": "accessory",
                                    "progression": {"mode": "static"},
                                    "prescription": {"sets": 4, "reps": 8},
                                    "loadText": "RPE 8",
                                    "notes": "",
                                },
                            ],
                        }
                    ],
                },
                {
                    "weekIndex": 2,
                    "days": [
                        {
                            "dayIndex": 1,
                            "label": "周一",
                            "type": "lower_intensity",
                            "exercises": [
                                {
                                    "id": "w2d1-squat",
                                    "name": "Back Squat",
                                    "category": "main",
                                    "progression": {"mode": "percent_tm", "liftKey": "squat", "percentTm": 0.8},
                                    "prescription": {"sets": 4, "reps": 4},
                                    "notes": "",
                                }
                            ],
                        }
                    ],
                },
            ],
        }
    )


def test_build_custom_strength_cycle_weeks_generates_multiple_weeks() -> None:
    weeks = build_custom_strength_cycle_weeks(build_definition())

    assert len(weeks) == 2
    assert weeks[0]["Monday"]["type"] == "lower_strength"
    assert weeks[1]["Monday"]["type"] == "lower_intensity"


def test_build_custom_strength_cycle_weeks_materializes_main_lift_load_ref_from_tm() -> None:
    weeks = build_custom_strength_cycle_weeks(build_definition())

    squat = weeks[0]["Monday"]["exercises"][0]
    assert squat["ref1RM"] == "squat"
    assert squat["pct"] == 0.75
    assert squat["loadRef"] == {"lift": "squat", "value": 180.0, "source": "tm"}


def test_build_custom_strength_cycle_weeks_keeps_static_accessory_without_percent_fields() -> None:
    weeks = build_custom_strength_cycle_weeks(build_definition())

    row = weeks[0]["Monday"]["exercises"][1]
    assert row["name"] == "Barbell Row"
    assert row["kg"] is None
    assert row["pct"] is None
    assert row["note"] == "RPE 8"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_custom_strength_engine.py -q`  
Expected: FAIL with `ModuleNotFoundError` for `backend.plans.custom_strength_engine` or missing `build_custom_strength_cycle_weeks`.

- [ ] **Step 3: Implement custom strength weekly plan engine**

```python
from __future__ import annotations

from typing import Any


WEEKDAY_ORDER = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DAY_INDEX_TO_KEY = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}


def build_custom_strength_cycle_weeks(definition: dict[str, Any]) -> list[dict[str, dict[str, Any]]]:
    weeks = []
    for week in definition.get("weeks", []):
        week_plan = {day_key: {"type": "rest", "exercises": []} for day_key in WEEKDAY_ORDER}
        for day in week.get("days", []):
            day_key = DAY_INDEX_TO_KEY[day["dayIndex"]]
            week_plan[day_key] = {
                "type": day["type"],
                "exercises": [
                    _build_exercise_payload(exercise, definition["mainLifts"])
                    for exercise in day.get("exercises", [])
                ],
            }
        weeks.append(week_plan)
    return weeks


def _build_exercise_payload(exercise: dict[str, Any], main_lifts: dict[str, dict[str, float]]) -> dict[str, Any]:
    category = exercise["category"]
    sets = int(exercise["prescription"]["sets"])
    reps = int(exercise["prescription"]["reps"])
    if category == "main":
        lift_key = exercise["progression"]["liftKey"]
        percent_tm = float(exercise["progression"]["percentTm"])
        tm_value = float(main_lifts[lift_key]["tm"])
        return {
            "id": exercise["id"],
            "name": exercise["name"],
            "tier": "main",
            "template": {"loadMode": "percentage", "ref1RM": lift_key, "setType": "straight", "sets": sets, "repsText": str(reps)},
            "instance": {"pct": percent_tm, "kg": None, "note": exercise.get("notes", "")},
            "ref1RM": lift_key,
            "pct": percent_tm,
            "sets": sets,
            "reps": reps,
            "kg": None,
            "note": exercise.get("notes", ""),
            "loadRef": {"lift": lift_key, "value": tm_value, "source": "tm"},
        }
    return {
        "id": exercise["id"],
        "name": exercise["name"],
        "tier": "accessory",
        "template": {"loadMode": "fixed", "ref1RM": None, "setType": "straight", "sets": sets, "repsText": str(reps)},
        "instance": {"pct": None, "kg": None, "note": exercise.get("loadText") or exercise.get("notes", "")},
        "ref1RM": None,
        "pct": None,
        "sets": sets,
        "reps": reps,
        "kg": None,
        "note": exercise.get("loadText") or exercise.get("notes", ""),
        "loadRef": None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_custom_strength_engine.py -q`  
Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_custom_strength_engine.py backend/plans/custom_strength_engine.py
git commit -m "增加自定义力量计划周生成引擎"
```

---

### Task 3: Integrate custom strength with cycle service and API

**Files:**
- Modify: `backend/plans/cycle_service.py`
- Modify: `backend/api/cycle_plans.py`
- Modify: `backend/schemas/__init__.py`
- Modify: `backend/tests/test_cycle_api.py`

- [ ] **Step 1: Write the failing API tests for custom strength cycle creation**

```python
@pytest.mark.asyncio
async def test_create_custom_strength_cycle_generates_all_week_snapshots(
    api_client: tuple[AsyncClient, Any],
) -> None:
    client, session_factory = api_client
    await _seed_manual_state(session_factory)

    response = await client.post(
        "/api/cycles",
        json={
            "presetKey": "custom_strength",
            "startDate": "2026-06-09",
            "goal": "strength",
            "baseLifts": {"squat": {"tm": 180}, "bench": {"tm": 120}},
            "config": {
                "planType": "custom_strength",
                "name": "四周力量周期",
                "startDate": "2026-06-09",
                "totalWeeks": 2,
                "mainLifts": {"squat": {"tm": 180}, "bench": {"tm": 120}},
                "weeks": [
                    {
                        "weekIndex": 1,
                        "days": [
                            {
                                "dayIndex": 1,
                                "label": "周一",
                                "type": "lower_strength",
                                "exercises": [
                                    {
                                        "id": "w1d1-squat",
                                        "name": "Back Squat",
                                        "category": "main",
                                        "progression": {"mode": "percent_tm", "liftKey": "squat", "percentTm": 0.75},
                                        "prescription": {"sets": 5, "reps": 5},
                                        "notes": "",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "weekIndex": 2,
                        "days": [
                            {
                                "dayIndex": 1,
                                "label": "周一",
                                "type": "lower_intensity",
                                "exercises": [
                                    {
                                        "id": "w2d1-squat",
                                        "name": "Back Squat",
                                        "category": "main",
                                        "progression": {"mode": "percent_tm", "liftKey": "squat", "percentTm": 0.8},
                                        "prescription": {"sets": 4, "reps": 4},
                                        "notes": "",
                                    }
                                ],
                            }
                        ],
                    },
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cycle"]["presetKey"] == "custom_strength"
    assert payload["effectivePlan"]["Monday"]["exercises"][0]["pct"] == 0.75

    async with session_factory() as session:
        snapshots = (
            await session.execute(
                select(CycleWeekSnapshot).where(CycleWeekSnapshot.cycle_id == payload["cycle"]["id"])
            )
        ).scalars().all()
    assert len(snapshots) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_cycle_api.py -k "custom_strength_cycle" -q`  
Expected: FAIL because `custom_strength` is not supported or only one snapshot exists.

- [ ] **Step 3: Extend service to compile and persist all custom strength weeks**

```python
from backend.plans.custom_strength_definition import normalize_custom_strength_definition
from backend.plans.custom_strength_engine import build_custom_strength_cycle_weeks


def _compile_cycle_weeks(payload: CycleCreateRequestSchema) -> list[dict[str, Any]]:
    if payload.presetKey == "custom_strength":
        definition = normalize_custom_strength_definition(payload.config)
        return build_custom_strength_cycle_weeks(definition)
    week_one_plan = build_cycle_week_plan(
        preset_key=payload.presetKey,
        week_index=1,
        base_lifts=payload.baseLifts,
        config=payload.config,
    )
    return [week_one_plan]


async def create_active_cycle(session: AsyncSession, payload: CycleCreateRequestSchema) -> ActiveCycleDetailSchema:
    compiled_weeks = _compile_cycle_weeks(payload)
    cycle = ActiveCyclePlan(
        preset_key=payload.presetKey,
        status="active",
        start_date=payload.startDate,
        current_week_index=1,
        pending_week_index=None,
        goal=payload.goal,
        base_lifts=payload.baseLifts,
        config=payload.config,
    )
    session.add(cycle)
    await session.flush()

    for index, generated_plan in enumerate(compiled_weeks, start=1):
        week_start, week_end = _build_week_bounds(payload.startDate, index)
        session.add(
            CycleWeekSnapshot(
                cycle_id=cycle.id,
                week_index=index,
                generated_plan=generated_plan,
                override_plan=None,
                is_confirmed=index == 1,
                week_start=week_start,
                week_end=week_end,
            )
        )
```

- [ ] **Step 4: Keep API contract explicit for custom strength payloads**

```python
@router.post("/api/cycles", response_model=ActiveCycleDetailSchema, response_model_by_alias=True)
async def post_cycle(
    payload: CycleCreateRequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> ActiveCycleDetailSchema:
    try:
        return await create_active_cycle(session, payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_cycle_api.py -q`  
Expected: PASS with custom strength case included and no regression.

- [ ] **Step 6: Commit**

```bash
git add backend/plans/cycle_service.py backend/api/cycle_plans.py backend/schemas/__init__.py backend/tests/test_cycle_api.py
git commit -m "接通自定义力量计划后端创建链路"
```

---

### Task 4: Add frontend custom strength form mapping and API wiring

**Files:**
- Create: `tests/customStrengthPlanForm.test.js`
- Create: `src/utils/customStrengthPlanForm.js`
- Modify: `src/api/backendClient.js`
- Modify: `tests/backendClient.test.js`

- [ ] **Step 1: Write the failing tests for custom strength draft mapping**

```javascript
import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildCreateCustomStrengthCyclePayload,
  createCustomStrengthDraft,
} from '../src/utils/customStrengthPlanForm.js'

test('createCustomStrengthDraft creates a 4-week empty draft by default', () => {
  const draft = createCustomStrengthDraft()

  assert.equal(draft.totalWeeks, 4)
  assert.equal(draft.weeks.length, 4)
  assert.equal(draft.weeks[0].days.length, 7)
})

test('buildCreateCustomStrengthCyclePayload maps draft to cycle create payload', () => {
  const payload = buildCreateCustomStrengthCyclePayload({
    name: '四周力量周期',
    startDate: '2026-06-09',
    totalWeeks: 2,
    mainLifts: {
      squat: { tm: '180' },
      bench: { tm: '120' },
      deadlift: { tm: '' },
      ohp: { tm: '' },
    },
    weeks: [],
  })

  assert.equal(payload.presetKey, 'custom_strength')
  assert.equal(payload.goal, 'strength')
  assert.equal(payload.baseLifts.squat.tm, 180)
  assert.equal(payload.config.planType, 'custom_strength')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/customStrengthPlanForm.test.js`  
Expected: FAIL with missing module or missing exported helpers.

- [ ] **Step 3: Implement draft builders and payload mapping**

```javascript
const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

export function createCustomStrengthDraft() {
  return {
    name: '',
    startDate: '',
    totalWeeks: 4,
    mainLifts: {
      squat: { tm: '' },
      bench: { tm: '' },
      deadlift: { tm: '' },
      ohp: { tm: '' },
    },
    weeks: Array.from({ length: 4 }, (_, weekOffset) => ({
      weekIndex: weekOffset + 1,
      days: Array.from({ length: 7 }, (_, dayOffset) => ({
        dayIndex: dayOffset + 1,
        label: DAY_LABELS[dayOffset],
        type: 'rest',
        exercises: [],
      })),
    })),
  }
}

export function buildCreateCustomStrengthCyclePayload(draft) {
  return {
    presetKey: 'custom_strength',
    startDate: draft.startDate,
    goal: 'strength',
    baseLifts: {
      squat: { tm: toNumberOrNull(draft.mainLifts.squat.tm) },
      bench: { tm: toNumberOrNull(draft.mainLifts.bench.tm) },
      deadlift: { tm: toNumberOrNull(draft.mainLifts.deadlift.tm) },
      ohp: { tm: toNumberOrNull(draft.mainLifts.ohp.tm) },
    },
    config: {
      planType: 'custom_strength',
      name: draft.name,
      startDate: draft.startDate,
      totalWeeks: draft.totalWeeks,
      mainLifts: compactMainLifts(draft.mainLifts),
      weeks: draft.weeks,
    },
  }
}
```

- [ ] **Step 4: Add client coverage for createCyclePlan with custom strength payload**

```javascript
await client.createCyclePlan({
  presetKey: 'custom_strength',
  startDate: '2026-06-09',
  goal: 'strength',
  baseLifts: { squat: { tm: 180 } },
  config: { planType: 'custom_strength', totalWeeks: 2, weeks: [] },
})

assert.equal(requests[3].url, 'http://127.0.0.1:8000/api/cycles')
assert.equal(JSON.parse(requests[3].options.body).presetKey, 'custom_strength')
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `node --test tests/customStrengthPlanForm.test.js tests/backendClient.test.js`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/utils/customStrengthPlanForm.js tests/customStrengthPlanForm.test.js src/api/backendClient.js tests/backendClient.test.js
git commit -m "增加自定义力量计划前端草稿映射"
```

---

### Task 5: Add custom strength editor UI and plan settings integration

**Files:**
- Create: `src/components/plan-settings/CustomStrengthMainLiftEditor.jsx`
- Create: `src/components/plan-settings/CustomStrengthWeekEditor.jsx`
- Create: `src/components/plan-settings/CustomStrengthPlanEditor.jsx`
- Create: `tests/customStrengthPlanEditor.test.js`
- Modify: `src/components/plan-settings/PlanSettingsPanel.jsx`
- Modify: `src/tabs/PlanTab.jsx`
- Modify: `tests/profileTab.test.js`

- [ ] **Step 1: Write the failing source-contract tests for custom strength editor integration**

```javascript
import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

test('PlanSettingsPanel mounts custom strength editor entry and create action', () => {
  const source = readFileSync('src/components/plan-settings/PlanSettingsPanel.jsx', 'utf-8')

  assert.match(source, /自定义力量周期计划/)
  assert.match(source, /CustomStrengthPlanEditor/)
  assert.match(source, /创建自定义力量周期计划/)
})

test('PlanTab orchestrates custom strength draft separately from preset cycle draft', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /customStrengthDraft/)
  assert.match(source, /buildCreateCustomStrengthCyclePayload/)
  assert.match(source, /function handleCreateCustomStrengthCyclePlan/)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/customStrengthPlanEditor.test.js tests/profileTab.test.js`  
Expected: FAIL because editor files and symbols do not exist.

- [ ] **Step 3: Build minimal custom strength editor component tree**

```jsx
export default function CustomStrengthPlanEditor({
  draft,
  isSubmitting,
  onChange,
  onSubmit,
}) {
  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="grid gap-3 md:grid-cols-3">
        <input value={draft.name} onChange={(event) => onChange({ ...draft, name: event.target.value })} />
        <input type="date" value={draft.startDate} onChange={(event) => onChange({ ...draft, startDate: event.target.value })} />
        <input type="number" value={draft.totalWeeks} onChange={(event) => onChange(resizeWeeks(draft, Number(event.target.value)))} />
      </div>
      <CustomStrengthMainLiftEditor draft={draft} onChange={onChange} />
      {draft.weeks.map((week) => (
        <CustomStrengthWeekEditor key={week.weekIndex} week={week} draft={draft} onChange={onChange} />
      ))}
      <button disabled={isSubmitting} onClick={onSubmit} type="button">
        创建自定义力量周期计划
      </button>
    </div>
  )
}
```

- [ ] **Step 4: Integrate custom strength mode into plan settings orchestration**

```jsx
const [customStrengthDraft, setCustomStrengthDraft] = useState(() => createCustomStrengthDraft())

async function handleCreateCustomStrengthCyclePlan() {
  setIsCycleSubmitting(true)
  setCycleActionMessage('')
  try {
    const response = await backendClient.createCyclePlan(
      buildCreateCustomStrengthCyclePayload(customStrengthDraft),
    )
    const nextActiveCyclePlan = buildNextActiveCyclePayload(response)
    const nextEffectivePlan = readNextEffectivePlan(response)
    onPlanSourceChange?.({ activeSource: 'cycle' })
    onActiveCyclePlanChange?.(nextActiveCyclePlan)
    if (nextEffectivePlan) {
      onEffectiveWeeklyPlanChange?.(nextEffectivePlan)
    }
    setPlanSettingsMode('cycle')
    setCycleActionMessage('自定义力量周期计划已创建。')
  } catch (error) {
    setCycleActionMessage(error.message)
  } finally {
    setIsCycleSubmitting(false)
  }
}
```

- [ ] **Step 5: Keep PlanSettingsPanel as a mount point, not a logic bucket**

```jsx
{planSettingsMode === 'cycle' ? (
  <>
    <PresetCycleEditor ... />
    <CustomStrengthPlanEditor
      draft={customStrengthDraft}
      isSubmitting={isCycleSubmitting}
      onChange={setCustomStrengthDraft}
      onSubmit={handleCreateCustomStrengthCyclePlan}
    />
  </>
) : null}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `node --test tests/customStrengthPlanEditor.test.js tests/profileTab.test.js tests/customStrengthPlanForm.test.js`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/components/plan-settings/CustomStrengthMainLiftEditor.jsx src/components/plan-settings/CustomStrengthWeekEditor.jsx src/components/plan-settings/CustomStrengthPlanEditor.jsx src/components/plan-settings/PlanSettingsPanel.jsx src/tabs/PlanTab.jsx tests/customStrengthPlanEditor.test.js tests/profileTab.test.js
git commit -m "增加自定义力量计划创建编辑器"
```

---

### Task 6: Update docs and run full targeted verification

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`

- [x] **Step 1: Update README cycle plan capability text**

```md
- 周期计划模式支持预制模板与第一版自定义力量周期计划
- 自定义力量周期计划支持主项 TM 快照、按周手填 `%TM / sets / reps` 和静态辅助动作
```

- [x] **Step 2: Update architecture module and data-flow notes**

```md
- `backend/plans/custom_strength_definition.py`：自定义力量周期计划定义层
- `backend/plans/custom_strength_engine.py`：自定义力量周期计划周编译层
- `src/components/plan-settings/CustomStrengthPlanEditor.jsx`：自定义力量周期计划创建编辑器
```

- [x] **Step 3: Run focused verification suite**

Run: `node --test tests/customStrengthPlanForm.test.js tests/customStrengthPlanEditor.test.js tests/backendClient.test.js tests/profileTab.test.js`  
Expected: PASS.

Run: `uv run pytest backend/tests/test_custom_strength_definition.py backend/tests/test_custom_strength_engine.py backend/tests/test_cycle_api.py -q`  
Expected: PASS.

- [x] **Step 4: Run build and browser verification**

Run: `npm run build`  
Expected: PASS.

Run: `uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\cycle_plan_mode_switch_preview.py`  
Expected: PASS without regression in manual / cycle source switching.

Verification record:

- `node --test tests/customStrengthPlanForm.test.js tests/customStrengthPlanEditor.test.js tests/backendClient.test.js tests/profileTab.test.js` - PASS
- `uv run pytest backend/tests/test_custom_strength_definition.py backend/tests/test_custom_strength_engine.py backend/tests/test_cycle_api.py -q` - PASS
- `npm run build` - PASS
- `uv run python "G:\AI Tools\codex-skills\webapp-testing\scripts\with_server.py" --server "npm run dev:all" --port 5173 -- uv run python tests\e2e\cycle_plan_mode_switch_preview.py` - PASS

- [x] **Step 5: Commit**

```bash
git add README.md ARCHITECTURE.md docs/superpowers/plans/2026-06-05-custom-strength-cycle-plan.md tests/e2e/cycle_plan_mode_switch_preview.py
git commit -m "同步自定义力量周期计划文档与验证"
```

---

## Self-Review

- Spec coverage:
  - `custom_strength` 计划类型：Task 1, 3, 4, 5
  - 定义层与生成层分离：Task 1, 2
  - 一次性生成全部周快照：Task 3
  - 前端克制 editor：Task 5
  - 当前系统统一消费 `effectiveWeeklyPlan`：Task 3, 5
  - 文档同步：Task 6
- Placeholder scan:
  - 已避免 `TODO / TBD / implement later`
  - 每个任务都包含明确文件、测试和命令
- Type consistency:
  - `planType = custom_strength`
  - 生成入口统一为 `build_custom_strength_cycle_weeks`
  - 前端 payload 统一为 `buildCreateCustomStrengthCyclePayload`
