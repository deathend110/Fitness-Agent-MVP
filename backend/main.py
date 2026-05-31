from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.daily_log import router as daily_log_router
from backend.api.profile import router as profile_router
from backend.api.weekly_plan import router as weekly_plan_router
from backend.config import get_settings

settings = get_settings()

app = FastAPI(title="FitLoop Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def get_health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(profile_router)
app.include_router(weekly_plan_router)
app.include_router(daily_log_router)
