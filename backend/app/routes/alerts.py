from fastapi import APIRouter, Depends, Request

from app.services.alerts_service import get_alerts
from app.services.auth_service import require_auth

router = APIRouter(prefix='/api/alerts', tags=['alerts'])


@router.get('')
def alerts(_: Request, __=Depends(require_auth)):
    return get_alerts()
