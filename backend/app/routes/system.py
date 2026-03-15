from fastapi import APIRouter, Depends, Request

from app.services.auth_service import require_auth
from app.services.system_service import get_system_status
from app.services.task_service import get_live_task_queue

router = APIRouter(prefix='/api', tags=['system'])


@router.get('/system/status')
def system_status(_: Request, __=Depends(require_auth)):
    return get_system_status()


@router.get('/tasks/queue')
def task_queue(_: Request, __=Depends(require_auth)):
    return get_live_task_queue()
