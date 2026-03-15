from __future__ import annotations

import subprocess
from typing import Any, Dict, List

GATEWAY_PID_CMD = "pgrep -f 'openclaw-gateway' | head -1"


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
        {'id': 'backend', 'name': 'Dashboard Backend', 'lines': _wc('./logs/backend.log')},
        {'id': 'backend-error', 'name': 'Dashboard Errors', 'lines': _wc('./logs/backend-error.log')},
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
            cmd = ['journalctl', '_PID=' + pid, f'-n', str(lines), '--no-pager']
            if source == 'gateway-errors':
                cmd.extend(['--priority=err'])
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            return out if out.strip() else 'No entries'
        except Exception as e:
            return f'Error: {e}'
    
    path_map = {
        'backend': './logs/backend.log',
        'backend-error': './logs/backend-error.log',
    }
    path = path_map.get(source)
    if not path:
        return f'Unknown source: {source}'
    try:
        out = subprocess.check_output(['tail', f'-{lines}', path], text=True, stderr=subprocess.DEVNULL)
        return out if out.strip() else 'No entries'
    except Exception as e:
        return f'Error: {e}'
