from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.models import Profile
from backend.db.seed import (
    DEFAULT_PROFILE_ID,
    EMPTY_PROFILE_BASIC,
    EMPTY_PROFILE_ONE_RM,
)
from backend.schemas import ProfileSchema

router = APIRouter(prefix="/api/profile", tags=["profile"])


def build_empty_profile_response() -> ProfileSchema:
    return ProfileSchema(
        basic=EMPTY_PROFILE_BASIC,
        oneRm=EMPTY_PROFILE_ONE_RM,
        goal="",
        targetWeight=None,
        notes="",
    )


def build_profile_response(profile: Profile) -> ProfileSchema:
    return ProfileSchema(
        basic=profile.basic,
        oneRm=profile.one_rm,
        goal=profile.goal,
        targetWeight=profile.target_weight,
        notes=profile.notes,
    )


@router.get("", response_model=ProfileSchema, response_model_by_alias=True)
async def get_profile(session: AsyncSession = Depends(get_db_session)) -> ProfileSchema:
    profile = await session.get(Profile, DEFAULT_PROFILE_ID)
    if profile is None:
        return build_empty_profile_response()
    return build_profile_response(profile)


@router.put("", response_model=ProfileSchema, response_model_by_alias=True)
async def put_profile(
    payload: ProfileSchema,
    session: AsyncSession = Depends(get_db_session),
) -> ProfileSchema:
    profile = await session.get(Profile, DEFAULT_PROFILE_ID)
    if profile is None:
        profile = Profile(
            id=DEFAULT_PROFILE_ID,
            basic=payload.basic.model_dump(mode="python"),
            one_rm=payload.oneRm.model_dump(mode="python"),
            goal=payload.goal,
            target_weight=payload.targetWeight,
            notes=payload.notes,
        )
        session.add(profile)
    else:
        profile.basic = payload.basic.model_dump(mode="python")
        profile.one_rm = payload.oneRm.model_dump(mode="python")
        profile.goal = payload.goal
        profile.target_weight = payload.targetWeight
        profile.notes = payload.notes

    await session.commit()
    await session.refresh(profile)
    return build_profile_response(profile)
