from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.actions import router as actions_router
from app.routes.alerts import router as alerts_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.details import router as details_router
from app.routes.growth import router as growth_router
from app.routes.incidents import router as incidents_router
from app.routes.llm import router as llm_router
from app.routes.logs import router as logs_router
from app.routes.presets import router as presets_router
from app.routes.registry import router as registry_router
from app.routes.runtime import router as runtime_router
from app.routes.system import router as system_router
# tasks route not yet implemented
# from app.routes.tasks import router as tasks_router
from app.services.analytics_snapshot_service import prewarm_analytics_snapshot


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        prewarm_analytics_snapshot(force=True)
    except Exception:
        pass
    yield


app = FastAPI(title="Claw Monitor API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["", "http://127.0.0.1:3000", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(actions_router)
app.include_router(details_router)
app.include_router(registry_router)
app.include_router(growth_router)
app.include_router(system_router)
app.include_router(runtime_router)
app.include_router(incidents_router)
app.include_router(llm_router)
app.include_router(chat_router)
app.include_router(presets_router)
app.include_router(logs_router)


@app.get('/health')
def health():
    return {'ok': True, 'service': 'claw-monitor-api'}