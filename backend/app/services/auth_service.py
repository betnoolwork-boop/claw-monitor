from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException, Request, Response, status

BASE_DIR = Path(__file__).resolve().parents[5]
AUTH_PATH = BASE_DIR / 'projects' / 'clawmonitor-dashboard' / 'config' / 'auth.json'
COOKIE_NAME = 'clawmonitor_dashboard_session'


def load_auth_config() -> Dict[str, Any]:
    return json.loads(AUTH_PATH.read_text(encoding='utf-8'))


def validate_login(username: str, password: str) -> bool:
    cfg = load_auth_config()
    return username == cfg.get('username') and password == cfg.get('password')


def issue_session(response: Response) -> None:
    cfg = load_auth_config()
    response.set_cookie(
        COOKIE_NAME,
        cfg.get('sessionToken'),
        httponly=True,
        secure=False,
        samesite='Lax',
        max_age=60 * 60 * 24 * 14,
        path='/',
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path='/')


def require_auth(request: Request) -> None:
    cfg = load_auth_config()
    token = request.cookies.get(COOKIE_NAME)
    if token != cfg.get('sessionToken'):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
