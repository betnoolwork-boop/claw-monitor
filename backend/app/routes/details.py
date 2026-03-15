from fastapi import APIRouter, Depends, Request

from app.services.auth_service import require_auth
from app.services.details_service import get_agent_details, get_dashboard_insights, get_dashboard_snapshot, get_session_details

router = APIRouter(prefix='/api/details', tags=['details'])


@router.get('/agent/{agent_id}')
def agent_details(agent_id: str, _: Request, __=Depends(require_auth)):
    return get_agent_details(agent_id)


@router.get('/insights')
def dashboard_insights(_: Request, __=Depends(require_auth)):
    return get_dashboard_insights()


@router.get('/snapshot')
def dashboard_snapshot(_: Request, __=Depends(require_auth)):
    return get_dashboard_snapshot()


@router.get('/session/{session_key:path}')
def session_details(session_key: str, _: Request, __=Depends(require_auth)):
    return get_session_details(session_key)
