from fastapi import APIRouter, Depends, Request

from app.services.auth_service import require_auth
from app.services.llm_service import get_expensive_sessions, get_hot_sessions, get_llm_by_model, get_llm_by_provider, get_llm_summary, get_provider_health

router = APIRouter(prefix='/api/llm', tags=['llm'])


@router.get('/summary')
def llm_summary(_: Request, __=Depends(require_auth)):
    return get_llm_summary()


@router.get('/providers')
def llm_providers(_: Request, __=Depends(require_auth)):
    return get_llm_by_provider()


@router.get('/models')
def llm_models(_: Request, __=Depends(require_auth)):
    return get_llm_by_model()


@router.get('/expensive-sessions')
def llm_expensive_sessions(_: Request, __=Depends(require_auth)):
    return get_expensive_sessions()


@router.get('/provider-health')
def llm_provider_health(_: Request, __=Depends(require_auth)):
    return get_provider_health()


@router.get('/hot-sessions')
def llm_hot_sessions(_: Request, __=Depends(require_auth)):
    return get_hot_sessions()
