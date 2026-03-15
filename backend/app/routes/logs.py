from __future__ import annotations

import asyncio
import subprocess
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.services.auth_service import require_auth

router = APIRouter(prefix='/api/logs', tags=['logs'])

GATEWAY_PID_CMD = "pgrep -f 'openclaw-gateway' | head -1"

PATH_MAP = {
    'backend': './logs/backend.log',
    'backend-error': './logs/backend-error.log',
}


def _get_gateway_pid() -> str:
    try:
        return subprocess.check_output(GATEWAY_PID_CMD, shell=True, text=True).strip()
    except Exception:
        return ''


def get_log_sources() -> List[Dict[str, Any]]:
    pid = _get_gateway_pid()
    return [
        {'id': 'gateway', 'name': 'Gateway (openclaw)', 'lines': None, 'pid': pid},
        {'id': 'gateway-errors', 'name': 'Gateway Errors', 'lines': None, 'pid': pid},
        {'id': 'backend', 'name': 'Dashboard Backend', 'lines': _wc(PATH_MAP['backend'])},
        {'id': 'backend-error', 'name': 'Dashboard Errors', 'lines': _wc(PATH_MAP['backend-error'])},
    ]


def _wc(path: str) -> int:
    try:
        out = subprocess.check_output(['wc', '-l', path], text=True).strip()
        return int(out.split()[0])
    except Exception:
        return -1


def get_log_tail(source: str, lines: int = 100) -> str:
    lines = min(lines, 500)
    if source in ('gateway', 'gateway-errors'):
        pid = _get_gateway_pid()
        if not pid:
            return 'Gateway process not found'
        try:
            cmd = ['journalctl', '_PID=' + pid, '-n', str(lines), '--no-pager']
            if source == 'gateway-errors':
                cmd.extend(['--priority=err'])
            return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL) or 'No entries'
        except Exception as e:
            return f'Error: {e}'
    path = PATH_MAP.get(source)
    if not path:
        return f'Unknown source: {source}'
    try:
        return subprocess.check_output(['tail', f'-{lines}', path], text=True, stderr=subprocess.DEVNULL) or 'No entries'
    except Exception as e:
        return f'Error: {e}'


@router.get('/sources')
def log_sources(_: Request, __=Depends(require_auth)):
    return {'items': get_log_sources()}


@router.get('/tail/{source}')
def log_tail(source: str, lines: int = 100, _: Request = None, __=Depends(require_auth)):
    return {'source': source, 'content': get_log_tail(source, lines)}


@router.get('/stream/{source}')
async def log_stream(source: str, _: Request = None, __=Depends(require_auth)):
    """SSE stream: отдаёт новые строки в реальном времени."""
    
    async def event_generator():
        if source in ('gateway', 'gateway-errors'):
            pid = _get_gateway_pid()
            if not pid:
                yield f"data: Gateway process not found\n\n"
                return
            cmd = ['journalctl', '_PID=' + pid, '-f', '-n', '0', '--no-pager', '-o', 'cat']
            if source == 'gateway-errors':
                cmd.extend(['--priority=err'])
        else:
            path = PATH_MAP.get(source)
            if not path:
                yield f"data: Unknown source\n\n"
                return
            cmd = ['tail', '-f', '-n', '0', path]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                decoded = line.decode('utf-8', errors='replace').rstrip('\n')
                if decoded:
                    yield f"data: {decoded}\n\n"
        finally:
            proc.terminate()
            await proc.wait()

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
