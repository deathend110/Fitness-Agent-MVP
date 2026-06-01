from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.chat import initialize_background_worker, router as chat_router
from backend.api.daily_log import router as daily_log_router
from backend.api.drafts import router as drafts_router
from backend.api.files import router as files_router
from backend.api.memory import router as memory_router
from backend.api.metrics import router as metrics_router
from backend.api.models import router as models_router
from backend.api.migrate import router as migrate_router
from backend.api.profile import router as profile_router
from backend.api.tools import router as tools_router
from backend.api.weekly_plan import router as weekly_plan_router
from backend.config import get_settings
from backend.db.database import create_all_tables, session_factory
from backend.db.seed import seed_if_empty
from backend.model_config.runtime import (
    ProviderRuntimeCache,
    get_provider_runtime,
    set_provider_runtime,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await create_all_tables()
    await seed_if_empty(session_factory)
    # 先把模型配置缓存挂到 app.state，后续接口可直接热刷新而不用重启进程。
    runtime = ProviderRuntimeCache.from_path(settings.model_provider_config_path)
    _app.state.provider_runtime = runtime
    set_provider_runtime(runtime)
    initialize_background_worker(
        session_factory=session_factory,
        runtime_provider=get_provider_runtime,
    )
    yield
    set_provider_runtime(None)


app = FastAPI(title="FitLoop Backend", lifespan=lifespan)

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
app.include_router(drafts_router)
app.include_router(chat_router)
app.include_router(files_router)
app.include_router(memory_router)
app.include_router(models_router)
app.include_router(metrics_router)
app.include_router(tools_router)
app.include_router(migrate_router)
