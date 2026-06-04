# Cycle Plan Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在训练计划页落地手动可控的“周期计划模式”，新增计划设置入口、周期/非周期来源切换、预制力量周期计划创建与当前周投影，同时保持今日日志与 AI 教练统一读取当前激活计划来源。

**Architecture:** 保留现有 `weekly_plan_day` 作为手动周计划来源，新建独立的周期计划状态与周快照模型；前端通过 `计划设置` 入口管理来源切换和周期配置；下游模块不直接理解周期模板，只消费“当前激活来源的有效周计划”。首版只做手动控制，不给模型写权限，但后端接口与服务按后续 AI 复用方式设计。

**Tech Stack:** React 19 + Vite + Tailwind CSS、FastAPI、SQLAlchemy + SQLite、node:test、pytest + httpx AsyncClient

---

## File Structure

### New backend files
- `backend/api/cycle_plans.py`
  - 周期计划 REST 接口：来源切换、模板列表、创建活动周期、读取当前周期、生成下一周、确认推进、保存单周覆盖、停止周期。
- `backend/agent/active_plan.py`
  - 提供“当前激活来源有效周计划”读取函数，供 API、metrics、AI 上下文、工具调用统一复用。
- `backend/plans/preset_library.py`
  - 内置预制模板注册表：`candito_6week`、`madcow_5x5`、`texas_method`。
- `backend/plans/cycle_engine.py`
  - 周期模板周生成器：把模板定义 + `1RM/TM` + 当前周次 + 轻量配置转换成现有 `WeeklyPlanSchema` 兼容结构。
- `backend/plans/cycle_service.py`
  - 封装活动周期创建、当前周读取、待推进周生成、确认推进、覆盖层合并等服务逻辑。
- `backend/tests/test_cycle_engine.py`
  - 周期模板生成与覆盖层合并单测。
- `backend/tests/test_cycle_api.py`
  - 周期接口与来源切换 API 测试。

### Modified backend files
- `backend/db/models.py`
  - 新增计划来源状态、活动周期、周期周快照表。
- `backend/db/seed.py`
  - 初始化默认计划来源为 `manual`。
- `backend/db/migrations/versions/<timestamp>_add_cycle_plan_mode.py`
  - Alembic 迁移。
- `backend/schemas/__init__.py`
  - 新增周期计划相关 schema。
- `backend/main.py`
  - 注册 `cycle_plans` 路由。
- `backend/api/metrics.py`
  - 改成读取当前激活来源的有效周计划，而不是直接读 `weekly_plan_day`。
- `backend/api/tools.py`
  - 计划工具链与 proposal 提交改成读取当前激活来源的有效周计划；若当前来源是周期计划且当前周存在覆盖层，则提交写回覆盖层。
- `backend/agent/tool_calling.py`
  - `get_weekly_plan` 读取当前激活来源的有效周计划。
- `backend/agent/chat_session.py`
  - AI 上下文注入改成读取当前激活来源的有效周计划，并附带周期状态摘要（只读）。

### New frontend files
- `src/utils/cyclePlanView.js`
  - 周期计划设置页/弹层需要的展示模型：来源说明、模板摘要、状态标签、空态文案。
- `src/utils/cyclePlanForm.js`
  - 周期计划创建与设置表单草稿转换、默认值与 payload 构建。
- `tests/cyclePlanView.test.js`
  - 周期计划展示模型测试。
- `tests/cyclePlanForm.test.js`
  - 周期计划表单映射测试。

### Modified frontend files
- `src/api/backendClient.js`
  - 增加周期计划与计划来源接口客户端。
- `src/api/appData.js`
  - 增加当前计划来源、有效周计划与活动周期加载函数。
- `src/App.jsx`
  - 增加 `planSource`、`effectiveWeeklyPlan`、`activeCyclePlan` 状态；下游 tab 改读有效周计划。
- `src/tabs/PlanTab.jsx`
  - 接入 `计划设置` 入口、周期模式主状态和来源切换后的主视图。
- `src/components/plan-header/PlanHeaderToolbar.jsx`
  - `计划设置` 按钮接入真实点击事件。
- `src/utils/planHeader.js`
  - 头部模型加入当前来源标签和按钮真实文案，不再标记为 placeholder。
- `src/tabs/TodayTab.jsx`
  - 改为读取 `effectiveWeeklyPlan`。
- `src/tabs/CoachTab.jsx`
  - 改为读取 `effectiveWeeklyPlan`，并保留手动周计划写入逻辑隔离。
- `src/utils/todayPlan.js`
  - 无协议变更，但补充测试覆盖“周期计划投影仍兼容 today plan 摘要”。
- `tests/backendClient.test.js`
  - 新增周期接口请求测试。
- `tests/planHeader.test.js`
  - 新增真实计划设置入口和来源标签断言。
- `tests/todayTab.test.js`
  - 新增今日日志读取有效周计划的源码契约断言。
- `README.md`
  - 增加周期计划模式首版能力说明。
- `ARCHITECTURE.md`
  - 增加计划来源系统、周期计划数据流、当前激活来源的读取规则。

## Task 1: Add cycle plan persistence and schemas

**Files:**
- Create: `backend/db/migrations/versions/<timestamp>_add_cycle_plan_mode.py`
- Modify: `backend/db/models.py`
- Modify: `backend/db/seed.py`
- Modify: `backend/schemas/__init__.py`
- Test: `backend/tests/test_models.py`
- Test: `backend/tests/test_phase3_models.py`

- [ ] **Step 1: Write the failing model round-trip test**

```python
@pytest.mark.asyncio
async def test_cycle_plan_models_round_trip_preserves_source_active_cycle_and_snapshot(tmp_path: Path):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'cycle-models.db'}"
    engine, session_factory = create_engine_and_session_factory(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(PlanSourceState(active_source="cycle"))
        session.add(
            ActiveCyclePlan(
                id=1,
                preset_key="candito_6week",
                status="active",
                start_date="2026-06-01",
                current_week_index=1,
                pending_week_index=2,
                goal="力量提升",
                base_lifts={"squat": {"oneRm": 160, "tm": 144}},
                config={"trainingDays": ["Monday", "Wednesday", "Friday"]},
            )
        )
        session.add(
            CycleWeekSnapshot(
                cycle_id=1,
                week_index=1,
                generated_plan={
                    "Monday": {"type": "strength", "exercises": [{"name": "深蹲", "pct": 0.8}]}
                },
                override_plan={
                    "Monday": {"type": "strength", "exercises": [{"name": "深蹲", "pct": 0.78}]}
                },
                is_confirmed=True,
                week_start="2026-06-01",
                week_end="2026-06-07",
            )
        )
        await session.commit()

    async with session_factory() as session:
        source = await session.get(PlanSourceState, 1)
        cycle = await session.get(ActiveCyclePlan, 1)
        snapshot = await session.get(CycleWeekSnapshot, {"cycle_id": 1, "week_index": 1})

    assert source is not None
    assert source.active_source == "cycle"
    assert cycle is not None
    assert cycle.base_lifts["squat"]["tm"] == 144
    assert snapshot is not None
    assert snapshot.override_plan["Monday"]["exercises"][0]["pct"] == 0.78

    await engine.dispose()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_models.py::test_cycle_plan_models_round_trip_preserves_source_active_cycle_and_snapshot -v`

Expected: FAIL with `NameError` / missing `PlanSourceState`, `ActiveCyclePlan`, or `CycleWeekSnapshot`.

- [ ] **Step 3: Add SQLAlchemy models**

```python
class PlanSourceState(Base):
    __tablename__ = "plan_source_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active_source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class ActiveCyclePlan(Base):
    __tablename__ = "active_cycle_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preset_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    current_week_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    pending_week_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_lifts: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class CycleWeekSnapshot(Base):
    __tablename__ = "cycle_week_snapshot"

    cycle_id: Mapped[int] = mapped_column(
        ForeignKey("active_cycle_plan.id", ondelete="CASCADE"),
        primary_key=True,
    )
    week_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    generated_plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    override_plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(nullable=False, default=False)
    week_start: Mapped[str] = mapped_column(String(10), nullable=False)
    week_end: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
```

- [ ] **Step 4: Add seed and Pydantic schemas**

```python
class PlanSourceSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    activeSource: Literal["manual", "cycle"]


class CyclePresetSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    summary: str
    supportedWeeks: int
    supportsTm: bool


class ActiveCyclePlanSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    presetKey: str
    status: str
    startDate: str
    currentWeekIndex: int
    pendingWeekIndex: int | None = None
    goal: str = ""
    baseLifts: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 5: Add Alembic migration**

```python
def upgrade() -> None:
    op.create_table(
        "plan_source_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active_source", sa.String(length=16), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "active_cycle_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("preset_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.String(length=10), nullable=False),
        sa.Column("current_week_index", sa.Integer(), nullable=False),
        sa.Column("pending_week_index", sa.Integer(), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("base_lifts", sqlite.JSON(), nullable=False),
        sa.Column("config", sqlite.JSON(), nullable=False),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("last_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "cycle_week_snapshot",
        sa.Column("cycle_id", sa.Integer(), nullable=False),
        sa.Column("week_index", sa.Integer(), nullable=False),
        sa.Column("generated_plan", sqlite.JSON(), nullable=False),
        sa.Column("override_plan", sqlite.JSON(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False),
        sa.Column("week_start", sa.String(length=10), nullable=False),
        sa.Column("week_end", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cycle_id"], ["active_cycle_plan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cycle_id", "week_index"),
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_models.py::test_cycle_plan_models_round_trip_preserves_source_active_cycle_and_snapshot backend/tests/test_phase3_models.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/db/models.py backend/db/seed.py backend/db/migrations/versions backend/schemas/__init__.py backend/tests/test_models.py backend/tests/test_phase3_models.py
git commit -m "feat: 增加周期计划基础数据模型"
```

## Task 2: Build preset registry and deterministic cycle engine

**Files:**
- Create: `backend/plans/preset_library.py`
- Create: `backend/plans/cycle_engine.py`
- Test: `backend/tests/test_cycle_engine.py`

- [ ] **Step 1: Write failing engine tests for the three preset families**

```python
def test_build_candito_week_one_plan_projects_to_weekly_plan_shape() -> None:
    plan = build_cycle_week_plan(
        preset_key="candito_6week",
        week_index=1,
        base_lifts={
            "squat": {"oneRm": 160, "tm": 144},
            "bench": {"oneRm": 110, "tm": 99},
            "deadlift": {"oneRm": 190, "tm": 171},
        },
        config={"trainingDays": ["Monday", "Wednesday", "Friday"]},
    )

    assert plan["Monday"]["type"] == "strength"
    assert plan["Monday"]["exercises"][0]["name"] == "深蹲"
    assert plan["Monday"]["exercises"][0]["ref1RM"] == "squat"
    assert plan["Sunday"] == {"type": "rest", "exercises": []}


def test_build_madcow_week_two_plan_uses_tm_when_present() -> None:
    plan = build_cycle_week_plan(
        preset_key="madcow_5x5",
        week_index=2,
        base_lifts={"squat": {"oneRm": 160, "tm": 150}},
        config={},
    )

    assert plan["Monday"]["exercises"][0]["pct"] is not None
    assert plan["Monday"]["exercises"][0]["template"]["loadMode"] == "percentage"


def test_apply_cycle_week_override_replaces_only_target_day() -> None:
    generated = {
        "Monday": {"type": "strength", "exercises": [{"name": "深蹲", "pct": 0.8}]},
        "Tuesday": {"type": "rest", "exercises": []},
    }
    override = {
        "Monday": {"type": "strength", "exercises": [{"name": "暂停深蹲", "pct": 0.75}]}
    }

    effective = merge_cycle_week_override(generated, override)

    assert effective["Monday"]["exercises"][0]["name"] == "暂停深蹲"
    assert effective["Tuesday"] == {"type": "rest", "exercises": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_cycle_engine.py -q`

Expected: FAIL with missing module or missing `build_cycle_week_plan`.

- [ ] **Step 3: Add preset registry**

```python
PRESET_LIBRARY = {
    "candito_6week": {
        "key": "candito_6week",
        "label": "Candito 6 周",
        "summary": "固定 6 周力量周期，按周切换强度与容量重点。",
        "supported_weeks": 6,
        "supports_tm": True,
        "week_blocks": {
            1: [
                {"day": "Monday", "type": "strength", "lift": "squat", "sets": 6, "reps": 6, "pct": 0.72},
                {"day": "Wednesday", "type": "strength", "lift": "bench", "sets": 6, "reps": 6, "pct": 0.72},
                {"day": "Friday", "type": "strength", "lift": "deadlift", "sets": 4, "reps": 6, "pct": 0.72},
            ],
        },
    },
    "madcow_5x5": {
        "key": "madcow_5x5",
        "label": "Madcow 5x5",
        "summary": "每周递进的 5x5 线性进展结构。",
        "supported_weeks": 12,
        "supports_tm": True,
        "week_blocks": {
            1: [
                {"day": "Monday", "type": "strength", "lift": "squat", "sets": 5, "reps": 5, "pct": 0.75},
                {"day": "Wednesday", "type": "strength", "lift": "bench", "sets": 5, "reps": 5, "pct": 0.72},
                {"day": "Friday", "type": "strength", "lift": "deadlift", "sets": 5, "reps": 5, "pct": 0.78},
            ],
        },
    },
    "texas_method": {
        "key": "texas_method",
        "label": "德州计划",
        "summary": "HLM 周结构：容量日、恢复日、强度日。",
        "supported_weeks": 12,
        "supports_tm": True,
        "week_blocks": {
            1: [
                {"day": "Monday", "type": "strength", "lift": "squat", "sets": 5, "reps": 5, "pct": 0.82},
                {"day": "Wednesday", "type": "recovery", "lift": "bench", "sets": 3, "reps": 5, "pct": 0.7},
                {"day": "Friday", "type": "intensity", "lift": "deadlift", "sets": 1, "reps": 5, "pct": 0.87},
            ],
        },
    },
}
```

- [ ] **Step 4: Implement deterministic plan projection**

```python
def build_cycle_week_plan(
    *,
    preset_key: str,
    week_index: int,
    base_lifts: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preset = get_cycle_preset_or_raise(preset_key)
    normalized_plan = {day_key: {"type": "rest", "exercises": []} for day_key in WEEKDAY_ORDER}
    week_block = resolve_week_block(preset, week_index)

    for item in week_block:
        lift_key = item["lift"]
        normalized_plan[item["day"]] = {
            "type": item["type"],
            "exercises": [
                build_percentage_exercise(
                    name=LIFT_LABELS[lift_key],
                    ref_1rm=lift_key,
                    pct=item["pct"],
                    sets=item["sets"],
                    reps=item["reps"],
                    tm=read_tm_or_one_rm(base_lifts, lift_key),
                )
            ],
        }

    return normalized_plan


def merge_cycle_week_override(
    generated_plan: dict[str, Any],
    override_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    if not override_plan:
        return generated_plan

    merged = deepcopy(generated_plan)
    for day_key, day_plan in override_plan.items():
        merged[day_key] = day_plan
    return merged
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_cycle_engine.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/plans/preset_library.py backend/plans/cycle_engine.py backend/tests/test_cycle_engine.py
git commit -m "feat: 增加周期计划预制模板与周生成引擎"
```

## Task 3: Add cycle service and backend API surface

**Files:**
- Create: `backend/plans/cycle_service.py`
- Create: `backend/agent/active_plan.py`
- Create: `backend/api/cycle_plans.py`
- Modify: `backend/main.py`
- Modify: `backend/api/metrics.py`
- Modify: `backend/schemas/__init__.py`
- Test: `backend/tests/test_cycle_api.py`

- [ ] **Step 1: Write failing API tests for source switch and active cycle lifecycle**

```python
@pytest.mark.asyncio
async def test_plan_source_defaults_to_manual_and_can_switch_to_cycle(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/plan-source")
    assert response.status_code == 200
    assert response.json() == {"activeSource": "manual"}

    switch_response = await api_client.put("/api/plan-source", json={"activeSource": "cycle"})
    assert switch_response.status_code == 200
    assert switch_response.json() == {"activeSource": "cycle"}


@pytest.mark.asyncio
async def test_create_active_cycle_generates_week_one_snapshot(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/cycles",
        json={
            "presetKey": "candito_6week",
            "startDate": "2026-06-01",
            "goal": "力量提升",
            "baseLifts": {
                "squat": {"oneRm": 160, "tm": 144},
                "bench": {"oneRm": 110, "tm": 99},
                "deadlift": {"oneRm": 190, "tm": 171},
            },
            "config": {"trainingDays": ["Monday", "Wednesday", "Friday"]},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cycle"]["presetKey"] == "candito_6week"
    assert payload["currentWeek"]["weekIndex"] == 1
    assert payload["currentWeek"]["effectivePlan"]["Monday"]["type"] == "strength"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_cycle_api.py -q`

Expected: FAIL with `404 Not Found` for `/api/plan-source` or `/api/cycles`.

- [ ] **Step 3: Implement cycle service**

```python
class CyclePlanService:
    async def get_plan_source(self, session: AsyncSession) -> PlanSourceState:
        source = await session.get(PlanSourceState, 1)
        if source is None:
            source = PlanSourceState(id=1, active_source="manual")
            session.add(source)
            await session.flush()
        return source

    async def create_active_cycle(self, session: AsyncSession, payload: CreateCyclePlanSchema) -> ActiveCyclePlan:
        cycle = ActiveCyclePlan(
            preset_key=payload.preset_key,
            status="active",
            start_date=payload.start_date,
            current_week_index=1,
            goal=payload.goal,
            base_lifts=payload.base_lifts,
            config=payload.config,
            last_generated_at=utc_now(),
            last_confirmed_at=utc_now(),
        )
        session.add(cycle)
        await session.flush()

        generated_plan = build_cycle_week_plan(
            preset_key=payload.preset_key,
            week_index=1,
            base_lifts=payload.base_lifts,
            config=payload.config,
        )
        session.add(
            CycleWeekSnapshot(
                cycle_id=cycle.id,
                week_index=1,
                generated_plan=generated_plan,
                override_plan=None,
                is_confirmed=True,
                week_start=payload.start_date,
                week_end=compute_week_end(payload.start_date),
            )
        )
        return cycle
```

- [ ] **Step 4: Implement API routes**

```python
router = APIRouter(prefix="/api", tags=["cycle-plans"])


@router.get("/plan-source", response_model=PlanSourceSchema, response_model_by_alias=True)
async def get_plan_source(session: AsyncSession = Depends(get_db_session)) -> PlanSourceSchema:
    source = await CyclePlanService().get_plan_source(session)
    return PlanSourceSchema(activeSource=source.active_source)


@router.put("/plan-source", response_model=PlanSourceSchema, response_model_by_alias=True)
async def put_plan_source(
    payload: PlanSourceSchema,
    session: AsyncSession = Depends(get_db_session),
) -> PlanSourceSchema:
    source = await CyclePlanService().set_plan_source(session, payload.activeSource)
    await session.commit()
    return PlanSourceSchema(activeSource=source.active_source)


@router.get("/cycles/presets", response_model=list[CyclePresetSchema], response_model_by_alias=True)
async def list_cycle_presets() -> list[CyclePresetSchema]:
    return [CyclePresetSchema(**item) for item in list_cycle_presets_view()]
```

- [ ] **Step 5: Add active effective plan resolver**

```python
async def load_effective_weekly_plan(session: AsyncSession) -> dict[str, Any]:
    source = await CyclePlanService().get_plan_source(session)
    if source.active_source == "cycle":
        cycle_payload = await CyclePlanService().get_active_cycle_payload(session)
        if cycle_payload and cycle_payload["currentWeek"]:
            return cycle_payload["currentWeek"]["effectivePlan"]
    return await load_manual_weekly_plan(session)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_cycle_api.py backend/tests/test_crud_api.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/api/cycle_plans.py backend/agent/active_plan.py backend/plans/cycle_service.py backend/main.py backend/api/metrics.py backend/schemas/__init__.py backend/tests/test_cycle_api.py
git commit -m "feat: 增加周期计划后端接口与当前来源读取"
```

## Task 4: Route AI, metrics, and plan tools through the active plan source

**Files:**
- Modify: `backend/agent/chat_session.py`
- Modify: `backend/agent/tool_calling.py`
- Modify: `backend/api/tools.py`
- Modify: `backend/api/metrics.py`
- Test: `backend/tests/test_chat_session_context.py`
- Test: `backend/tests/test_tool_calling.py`
- Test: `backend/tests/test_plan_tools.py`

- [ ] **Step 1: Write failing tests for active source consumption**

```python
@pytest.mark.asyncio
async def test_get_weekly_plan_tool_returns_cycle_effective_plan_when_cycle_source_is_active(db_session: AsyncSession) -> None:
    await seed_cycle_source_with_snapshot(db_session)

    weekly_plan = await registry.execute(db_session, "get_weekly_plan", {})

    assert weekly_plan["Monday"]["exercises"][0]["name"] == "暂停深蹲"


@pytest.mark.asyncio
async def test_chat_context_includes_cycle_summary_when_cycle_source_is_active(db_session: AsyncSession) -> None:
    await seed_cycle_source_with_snapshot(db_session)

    request = await build_agent_request(
        session=db_session,
        session_id=1,
        user_input="这周深蹲要不要轻一点？",
    )

    joined = "\n".join(item["content"] for item in request.messages if isinstance(item.get("content"), str))
    assert "当前计划来源：周期计划" in joined
    assert "当前周期：Candito 6 周" in joined
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_tool_calling.py::test_get_weekly_plan_tool_returns_cycle_effective_plan_when_cycle_source_is_active backend/tests/test_chat_session_context.py::test_chat_context_includes_cycle_summary_when_cycle_source_is_active -v`

Expected: FAIL because tool/context still read `weekly_plan_day`.

- [ ] **Step 3: Switch loaders to active plan service**

```python
async def _load_weekly_plan(session: AsyncSession) -> dict[str, Any]:
    return await load_effective_weekly_plan(session)


async def _load_cycle_summary(session: AsyncSession) -> dict[str, Any] | None:
    return await CyclePlanService().get_active_cycle_summary(session)
```

- [ ] **Step 4: Add read-only cycle summary to context blocks**

```python
if cycle_summary:
    sections.append(
        "当前计划来源：周期计划\n"
        f"当前周期：{cycle_summary['presetLabel']}\n"
        f"当前周次：第 {cycle_summary['currentWeekIndex']} 周\n"
        f"状态：{cycle_summary['statusLabel']}"
    )
```

- [ ] **Step 5: Ensure proposal writes to override layer when source is cycle**

```python
if active_source == "cycle":
    next_override = adopt_plan_change(current_effective_plan, payload.day, payload.changes).next_plan
    await CyclePlanService().save_week_override(
        session=session,
        cycle_id=active_cycle.id,
        week_index=active_cycle.current_week_index,
        override_plan=next_override,
    )
else:
    # existing weekly_plan_day write path
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_chat_session_context.py backend/tests/test_tool_calling.py backend/tests/test_plan_tools.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/agent/chat_session.py backend/agent/tool_calling.py backend/api/tools.py backend/api/metrics.py backend/tests/test_chat_session_context.py backend/tests/test_tool_calling.py backend/tests/test_plan_tools.py
git commit -m "feat: 让AI与工具链读取当前激活计划来源"
```

## Task 5: Add frontend cycle plan client state and settings entry

**Files:**
- Modify: `src/api/backendClient.js`
- Modify: `src/api/appData.js`
- Modify: `src/App.jsx`
- Modify: `src/utils/planHeader.js`
- Modify: `src/components/plan-header/PlanHeaderToolbar.jsx`
- Modify: `tests/backendClient.test.js`
- Modify: `tests/planHeader.test.js`

- [ ] **Step 1: Write failing frontend contract tests**

```javascript
test('createBackendClient 暴露周期计划与计划来源接口', async () => {
  const requests = []
  const client = createBackendClient({
    baseUrl: 'http://127.0.0.1:8000/api',
    fetchImpl: async (url, options) => {
      requests.push({ url, options })
      return { ok: true, json: async () => ({ ok: true }) }
    },
  })

  await client.getPlanSource()
  await client.updatePlanSource({ activeSource: 'cycle' })
  await client.getCyclePresets()
  await client.createCyclePlan({ presetKey: 'candito_6week' })

  assert.equal(requests[0].url, 'http://127.0.0.1:8000/api/plan-source')
  assert.equal(requests[1].options.method, 'PUT')
  assert.equal(requests[2].url, 'http://127.0.0.1:8000/api/cycles/presets')
  assert.equal(requests[3].url, 'http://127.0.0.1:8000/api/cycles')
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- --test-name-pattern="周期计划与计划来源接口|计划设置入口"`

Expected: FAIL because client methods and header model fields do not exist.

- [ ] **Step 3: Add backend client methods**

```javascript
getPlanSource({ signal } = {}) {
  return request('/plan-source', { signal })
},
updatePlanSource(payload, { signal } = {}) {
  return request('/plan-source', { method: 'PUT', body: payload, signal })
},
getCyclePresets({ signal } = {}) {
  return request('/cycles/presets', { signal })
},
createCyclePlan(payload, { signal } = {}) {
  return request('/cycles', { method: 'POST', body: payload, signal })
},
getActiveCyclePlan({ signal } = {}) {
  return request('/cycles/active', { signal })
},
generateNextCycleWeek(cycleId, { signal } = {}) {
  return request(`/cycles/${cycleId}/generate-next-week`, { method: 'POST', signal })
},
confirmNextCycleWeek(cycleId, { signal } = {}) {
  return request(`/cycles/${cycleId}/confirm-next-week`, { method: 'POST', signal })
},
updateCycleWeekOverride(cycleId, weekIndex, payload, { signal } = {}) {
  return request(`/cycles/${cycleId}/weeks/${weekIndex}/override`, {
    method: 'PUT',
    body: payload,
    signal,
  })
},
stopCyclePlan(cycleId, { signal } = {}) {
  return request(`/cycles/${cycleId}/stop`, { method: 'POST', signal })
},
```

- [ ] **Step 4: Add app-level state loading for active source and effective plan**

```javascript
const [planSource, setPlanSource] = useState({ activeSource: 'manual' })
const [effectiveWeeklyPlan, setEffectiveWeeklyPlan] = useState(() => normalizeWeeklyPlan(defaultWeeklyPlan))
const [activeCyclePlan, setActiveCyclePlan] = useState(null)

const nextData = await loadAppData({ signal: abortController.signal })
setWeeklyPlan(normalizeWeeklyPlan(nextData.weeklyPlan))
setPlanSource(nextData.planSource)
setEffectiveWeeklyPlan(normalizeWeeklyPlan(nextData.effectiveWeeklyPlan))
setActiveCyclePlan(nextData.activeCyclePlan)
```

- [ ] **Step 5: Make settings button real in header model**

```javascript
const PLAN_SETTINGS_BUTTON = {
  label: '计划设置',
  hint: '切换非周期计划或周期计划，并管理当前周期配置。',
  title: '计划设置',
  description: '在这里选择手动周计划或周期计划，并管理当前激活计划。',
  confirmLabel: '打开设置',
  isPlaceholder: false,
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npm test -- --test-name-pattern="周期计划与计划来源接口|训练计划头部展示模型"`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/api/backendClient.js src/api/appData.js src/App.jsx src/utils/planHeader.js src/components/plan-header/PlanHeaderToolbar.jsx tests/backendClient.test.js tests/planHeader.test.js
git commit -m "feat: 增加周期计划前端基础状态与计划设置入口"
```

## Task 6: Build manual plan settings flow in Plan tab

**Files:**
- Create: `src/utils/cyclePlanForm.js`
- Create: `src/utils/cyclePlanView.js`
- Modify: `src/tabs/PlanTab.jsx`
- Modify: `tests/profileTab.test.js`
- Create: `tests/cyclePlanForm.test.js`
- Create: `tests/cyclePlanView.test.js`

- [ ] **Step 1: Write failing tests for cycle plan form mapping and settings UI contract**

```javascript
test('buildCreateCyclePlanPayload 会把表单草稿映射成后端 payload', () => {
  const payload = buildCreateCyclePlanPayload({
    presetKey: 'candito_6week',
    startDate: '2026-06-01',
    goal: '力量提升',
    squatOneRm: '160',
    squatTm: '144',
    trainingDays: ['Monday', 'Wednesday', 'Friday'],
  })

  assert.deepEqual(payload, {
    presetKey: 'candito_6week',
    startDate: '2026-06-01',
    goal: '力量提升',
    baseLifts: {
      squat: { oneRm: 160, tm: 144 },
    },
    config: {
      trainingDays: ['Monday', 'Wednesday', 'Friday'],
    },
  })
})

test('PlanTab 源码包含计划设置入口、来源选择和周期设置表单块', () => {
  const source = readFileSync('src/tabs/PlanTab.jsx', 'utf-8')

  assert.match(source, /isPlanSettingsOpen/)
  assert.match(source, /planSource\.activeSource/)
  assert.match(source, /非周期计划/)
  assert.match(source, /周期计划/)
  assert.match(source, /getCyclePresets|createCyclePlan/)
  assert.match(source, /生成下一周|确认进入下一周|停止周期/)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- --test-name-pattern="buildCreateCyclePlanPayload|计划设置入口"`

Expected: FAIL because helpers and UI blocks do not exist.

- [ ] **Step 3: Add cycle form helper**

```javascript
export function buildCreateCyclePlanPayload(draft = {}) {
  return {
    presetKey: draft.presetKey,
    startDate: draft.startDate,
    goal: draft.goal?.trim() ?? '',
    baseLifts: {
      squat: {
        oneRm: Number(draft.squatOneRm) || null,
        tm: Number(draft.squatTm) || null,
      },
      bench: {
        oneRm: Number(draft.benchOneRm) || null,
        tm: Number(draft.benchTm) || null,
      },
      deadlift: {
        oneRm: Number(draft.deadliftOneRm) || null,
        tm: Number(draft.deadliftTm) || null,
      },
    },
    config: {
      trainingDays: Array.isArray(draft.trainingDays) ? draft.trainingDays : [],
      accessoryMode: draft.accessoryMode || 'default',
    },
  }
}
```

- [ ] **Step 4: Add plan settings flow in `PlanTab`**

```javascript
const [isPlanSettingsOpen, setIsPlanSettingsOpen] = useState(false)
const [cycleDraft, setCycleDraft] = useState(() => createCyclePlanDraft(profile, activeCyclePlan))

async function handleSwitchPlanSource(nextSource) {
  const saved = await updatePlanSource(nextSource)
  onPlanSourceChange(saved)
}

async function handleCreateCycle() {
  const payload = buildCreateCyclePlanPayload(cycleDraft)
  const created = await createCyclePlan(payload)
  onActiveCyclePlanChange(created.cycle)
  onEffectiveWeeklyPlanChange(normalizeWeeklyPlan(created.currentWeek.effectivePlan))
  onPlanSourceChange({ activeSource: 'cycle' })
}
```

- [ ] **Step 5: Keep cycle operations manual and explicit**

```javascript
<button type="button" onClick={() => handleGenerateNextWeek(activeCyclePlan.id)}>
  生成下一周
</button>
<button type="button" onClick={() => handleConfirmNextWeek(activeCyclePlan.id)}>
  确认进入下一周
</button>
<button type="button" onClick={() => handleStopCycle(activeCyclePlan.id)}>
  停止周期
</button>
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npm test -- --test-name-pattern="buildCreateCyclePlanPayload|计划设置入口|cycle plan"`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/utils/cyclePlanForm.js src/utils/cyclePlanView.js src/tabs/PlanTab.jsx tests/cyclePlanForm.test.js tests/cyclePlanView.test.js tests/profileTab.test.js
git commit -m "feat: 增加训练计划页手动周期设置流程"
```

## Task 7: Switch downstream consumers to effective weekly plan

**Files:**
- Modify: `src/App.jsx`
- Modify: `src/tabs/TodayTab.jsx`
- Modify: `src/tabs/CoachTab.jsx`
- Modify: `src/utils/todayPlan.js`
- Modify: `tests/todayTab.test.js`
- Modify: `tests/coachChat.test.js`

- [ ] **Step 1: Write failing downstream contract tests**

```javascript
test('TodayTab 源码读取 effectiveWeeklyPlan 而不是直接依赖 manual weeklyPlan', () => {
  const source = readFileSync('src/tabs/TodayTab.jsx', 'utf-8')

  assert.match(source, /effectiveWeeklyPlan/)
})

test('CoachTab 会把当前激活来源的有效周计划传给教练链路', () => {
  const source = readFileSync('src/tabs/CoachTab.jsx', 'utf-8')

  assert.match(source, /effectiveWeeklyPlan/)
  assert.doesNotMatch(source, /weeklyPlan=\{weeklyPlan\}/)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- --test-name-pattern="effectiveWeeklyPlan"`

Expected: FAIL because tabs still read `weeklyPlan`.

- [ ] **Step 3: Thread effective plan through App and tabs**

```javascript
<PlanTab
  weeklyPlan={weeklyPlan}
  effectiveWeeklyPlan={effectiveWeeklyPlan}
  planSource={planSource}
  activeCyclePlan={activeCyclePlan}
  onEffectiveWeeklyPlanChange={setEffectiveWeeklyPlan}
/>

<TodayTab
  dailyLog={dailyLog}
  profile={profile}
  weeklyPlan={effectiveWeeklyPlan}
/>

<CoachTab
  chatHistory={chatHistory}
  dailyLog={dailyLog}
  profile={profile}
  weeklyPlan={effectiveWeeklyPlan}
/>
```

- [ ] **Step 4: Preserve manual weekly plan editing path**

```javascript
function handleWeeklyPlanChange(nextPlanUpdater) {
  setWeeklyPlan((currentPlan) => {
    const nextPlan = typeof nextPlanUpdater === 'function' ? nextPlanUpdater(currentPlan) : nextPlanUpdater
    if (planSource.activeSource === 'manual') {
      setEffectiveWeeklyPlan(normalizeWeeklyPlan(nextPlan))
    }
    return nextPlan
  })
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npm test -- --test-name-pattern="effectiveWeeklyPlan|TodayTab|CoachTab"`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/App.jsx src/tabs/TodayTab.jsx src/tabs/CoachTab.jsx src/utils/todayPlan.js tests/todayTab.test.js tests/coachChat.test.js
git commit -m "feat: 下游统一读取当前激活训练计划来源"
```

## Task 8: Verify end-to-end behavior and update docs

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Test: `backend/tests/test_cycle_api.py`
- Test: `tests/backendClient.test.js`
- Test: `tests/planHeader.test.js`
- Test: `tests/todayTab.test.js`

- [ ] **Step 1: Add documentation updates**

```md
## 周期计划模式

- 训练计划页支持通过 `计划设置` 在 `非周期计划` 与 `周期计划` 之间切换
- 周期计划首版提供 `Candito 6 周`、`Madcow 5x5`、`德州计划`
- 当前版本只支持手动创建、手动推进、手动停止周期；AI 教练只读取周期状态，不直接修改周期
```

- [ ] **Step 2: Run frontend unit tests**

Run: `npm test`

Expected: PASS with new cycle plan related tests included.

- [ ] **Step 3: Run backend unit tests**

Run: `uv run pytest backend/tests/test_models.py backend/tests/test_cycle_engine.py backend/tests/test_cycle_api.py backend/tests/test_chat_session_context.py backend/tests/test_tool_calling.py backend/tests/test_plan_tools.py -q`

Expected: PASS.

- [ ] **Step 4: Run manual backend + frontend smoke flow**

Run: `npm run dev:all`

Expected:
- frontend at `http://127.0.0.1:5173`
- backend at `http://127.0.0.1:8000`
- app loads without fallback banner

Manual checklist:
- 打开训练计划页，点击 `计划设置`
- 切到 `周期计划`
- 选择 `Candito 6 周` 并填写 `1RM/TM`
- 启动周期后本周训练计划切到生成周
- 打开今日日志，今日计划摘要与周期本周一致
- 打开 AI 教练，请求体重/训练建议时上下文没有报错
- 在周期模式下采纳一条计划修改建议，刷新后当前周覆盖仍在

- [ ] **Step 5: Commit**

```bash
git add README.md ARCHITECTURE.md
git commit -m "docs: 补充周期计划模式架构与使用说明"
```

## Self-Review

- 本计划覆盖了以下已确认范围：
  - `计划设置` 入口真实化
  - `非周期计划 / 周期计划` 来源选择
  - 周期模式首版只做手动控制
  - 周期计划首版只做力量计划模板
  - 预制模板优先，轻量参数覆盖
  - 到周后用户确认推进
  - 今日日志 / AI 教练 / 指标统一读取当前激活来源
- 本计划刻意不做：
  - 模型直接创建/推进/停止周期
  - 完整自定义周期 DSL
  - 增肌类泛化模板系统
  - 自动根据日志表现自适应修改下周负重
- 需要实现时坚持：
  - 新接口和服务优先复用，不在前端硬编码周期规则
  - 周期周改动写覆盖层，不反写模板
  - 手动周计划保留且独立，不与周期状态混写
