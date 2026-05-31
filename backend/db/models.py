from __future__ import annotations

from typing import Any

from sqlalchemy import CheckConstraint, Float, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


WEEKDAY_ORDER = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    basic: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    one_rm: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class WeeklyPlanDay(Base):
    __tablename__ = "weekly_plan_day"
    __table_args__ = (
        CheckConstraint(
            "day_key IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')",
            name="ck_weekly_plan_day_day_key",
        ),
    )

    day_key: Mapped[str] = mapped_column(String(16), primary_key=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, default="rest")
    # exercises 整存 JSON，保持 template + instance + 扁平兼容字段原样往返，避免采纳链路字段被提前规范化丢失。
    exercises: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)


class DailyLog(Base):
    __tablename__ = "daily_log"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep: Mapped[float | None] = mapped_column(Float, nullable=True)
    fatigue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    training_done: Mapped[bool | None] = mapped_column(nullable=True)
    training_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tdee_manual: Mapped[int | None] = mapped_column(Integer, nullable=True)
