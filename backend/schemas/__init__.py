from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ProfileBasicSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = ""
    sex: str = ""
    age: int | None = None
    height: float | None = None
    weight: float | None = None
    waist: float | None = None


class ProfileOneRmSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    squat: float | None = None
    bench: float | None = None
    deadlift: float | None = None


class ProfileSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    basic: ProfileBasicSchema = Field(default_factory=ProfileBasicSchema)
    oneRm: ProfileOneRmSchema = Field(default_factory=ProfileOneRmSchema)
    goal: str = ""
    targetWeight: float | None = None
    notes: str = ""


class WeeklyPlanDaySchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    exercises: list[dict[str, Any]]


class PlanProposalDayPlanSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    exercises: list[dict[str, Any]]


class WeeklyPlanSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    Monday: WeeklyPlanDaySchema
    Tuesday: WeeklyPlanDaySchema
    Wednesday: WeeklyPlanDaySchema
    Thursday: WeeklyPlanDaySchema
    Friday: WeeklyPlanDaySchema
    Saturday: WeeklyPlanDaySchema
    Sunday: WeeklyPlanDaySchema


class AdoptPlanChangeSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    action: str | None = None
    exerciseName: str | None = None
    field: str | None = None
    newValue: Any = None


class AdoptPlanRequestSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    day: str
    changes: list[AdoptPlanChangeSchema]


class AdoptPlanResponseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ok: bool
    message: str
    plan: WeeklyPlanSchema


class DailyLogEntrySchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    weight: float | None = None
    kcal: int | None = None
    protein: int | None = None
    sleep: float | None = None
    fatigue: int | None = None
    steps: int | None = None
    trainingDone: bool | None = None
    trainingNotes: str = ""
    tdeeManual: int | None = None


class DailyLogMapSchema(RootModel[dict[str, DailyLogEntrySchema]]):
    pass


class PlanSourceSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    activeSource: Literal["manual", "cycle"] = "manual"
    updatedAt: datetime | None = None


class CyclePresetSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    summary: str = ""
    supportedWeeks: list[int] = Field(default_factory=list)
    supportsTm: bool = False


class ActiveCyclePlanSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    presetKey: str
    status: Literal["draft", "active", "completed", "archived"]
    startDate: str
    currentWeekIndex: int = Field(..., ge=1)
    pendingWeekIndex: int | None = Field(default=None, ge=1)
    goal: str = ""
    baseLifts: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    lastGeneratedAt: datetime | None = None
    lastConfirmedAt: datetime | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class ChatSessionCreateSchema(BaseModel):
    title: str | None = None


class ChatSessionSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    title: str
    createdAt: datetime
    updatedAt: datetime


class ChatAttachmentSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fileId: int | None = None
    originalName: str = ""
    mimeType: str = ""
    extension: str = ""
    sizeBytes: int | None = None


class ChatMessageCreateSchema(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    suggestion: dict[str, Any] | None = None
    attachments: list[ChatAttachmentSchema] = Field(default_factory=list)


class ChatMessageSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    sessionId: int
    role: Literal["user", "assistant", "system"]
    content: str
    suggestion: dict[str, Any] | None = None
    attachments: list[ChatAttachmentSchema] = Field(default_factory=list)
    createdAt: datetime
