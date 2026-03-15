from fastapi import APIRouter, Depends, Request

from app.services.auth_service import require_auth
from app.services.registry_service import (
    get_registry_agents,
    get_registry_core,
    get_registry_experimental,
    get_registry_summary,
    get_registry_topology,
)

router = APIRouter(prefix='/api/registry', tags=['registry'])


@router.get('/summary')
def registry_summary(_: Request, __=Depends(require_auth)):
    return get_registry_summary()


@router.get('/agents')
def registry_agents(_: Request, __=Depends(require_auth)):
    return get_registry_agents()


@router.get('/topology')
def registry_topology(_: Request, __=Depends(require_auth)):
    return get_registry_topology()


@router.get('/core')
def registry_core(_: Request, __=Depends(require_auth)):
    return get_registry_core()


@router.get('/experimental')
def registry_experimental(_: Request, __=Depends(require_auth)):
    return get_registry_experimental()
