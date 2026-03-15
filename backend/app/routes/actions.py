from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.services.actions_service import run_action
from app.services.auth_service import require_auth

router = APIRouter(prefix='/api/actions', tags=['actions'])


class ActionRequest(BaseModel):
    action: str
    target: str | None = None
    kind: str | None = None
    note: str | None = None


@router.post('')
def actions(request: ActionRequest, _: Request, __=Depends(require_auth)):
    return run_action(request.action, request.target, request.kind, request.note)
