from fastapi import APIRouter, Depends, Request

from app.services.auth_service import require_auth
from app.services.growth_service import (
    get_growth_proposals,
    get_growth_report,
    get_growth_summary,
    get_growth_timeline,
)

router = APIRouter(prefix='/api/growth', tags=['growth'])


@router.get('/summary')
def growth_summary(_: Request, __=Depends(require_auth)):
    return get_growth_summary()


@router.get('/proposals')
def growth_proposals(_: Request, __=Depends(require_auth)):
    return get_growth_proposals()


@router.get('/timeline')
def growth_timeline(_: Request, __=Depends(require_auth)):
    return get_growth_timeline()


@router.get('/report')
def growth_report(_: Request, __=Depends(require_auth)):
    return get_growth_report()
