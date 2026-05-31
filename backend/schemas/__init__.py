from __future__ import annotations

from typing import Any

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


class WeeklyPlanSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    Monday: WeeklyPlanDaySchema
    Tuesday: WeeklyPlanDaySchema
    Wednesday: WeeklyPlanDaySchema
    Thursday: WeeklyPlanDaySchema
    Friday: WeeklyPlanDaySchema
    Saturday: WeeklyPlanDaySchema
    Sunday: WeeklyPlanDaySchema


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
