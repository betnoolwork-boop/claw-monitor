from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.services.auth_service import clear_session, issue_session, validate_login

router = APIRouter(prefix='/api/auth', tags=['auth'])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post('/login')
def login(request: LoginRequest, response: Response):
    if not validate_login(request.username, request.password):
        response.status_code = 401
        return {'ok': False, 'message': 'Неверный логин или пароль'}
    issue_session(response)
    return {'ok': True}


@router.post('/logout')
def logout(response: Response):
    clear_session(response)
    return {'ok': True}
