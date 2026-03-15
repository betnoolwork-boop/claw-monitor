from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.services.auth_service import require_auth
from app.services.chat_service import handle_chat

router = APIRouter(prefix='/api/chat', tags=['chat'])


class ChatRequest(BaseModel):
    message: str
    mode: str | None = 'query'


@router.post('')
def chat(request: ChatRequest, _: Request, __=Depends(require_auth)):
    return handle_chat(request.message)
