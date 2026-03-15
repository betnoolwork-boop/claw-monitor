from fastapi import APIRouter, Depends, Request

from app.services.auth_service import require_auth
from app.services.runtime_service import get_runtime_agent_statuses, get_runtime_summary

router = APIRouter(prefix='/api/runtime', tags=['runtime'])


@router.get('/summary')
def runtime_summary(_: Request, __=Depends(require_auth)):
    return get_runtime_summary()


@router.get('/agents')
def runtime_agents(_: Request, __=Depends(require_auth)):
    return get_runtime_agent_statuses()
