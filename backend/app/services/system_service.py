from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parents[5]
QUEUE_PATH = BASE_DIR / 'projects' / 'claw-monitor' / 'data' / 'task-queue.json'


def _read_loadavg() -> str:
    try:
        return Path('/proc/loadavg').read_text(encoding='utf-8').split()[0]
    except Exception:
        return 'n/a'


def _read_meminfo() -> Dict[str, int]:
    try:
        info = {}
        for line in Path('/proc/meminfo').read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(':')
                if key in ('MemTotal', 'MemAvailable'):
                    info[key] = int(parts[1])  # kB
        total_mb = info.get('MemTotal', 0) // 1024
        avail_mb = info.get('MemAvailable', 0) // 1024
        return {'totalMb': total_mb, 'usedMb': total_mb - avail_mb}
    except Exception:
        return {'totalMb': 0, 'usedMb': 0}


def _read_uptime() -> int:
    try:
        return int(float(Path('/proc/uptime').read_text().split()[0]))
    except Exception:
        return 0


def get_system_status() -> Dict[str, Any]:
    total, used, free = shutil.disk_usage('/')
    return {
        'status': 'ok',
        'hostname': os.uname().nodename,
        'loadavg1': _read_loadavg(),
        'disk': {
            'totalGb': round(total / (1024**3), 2),
            'usedGb': round(used / (1024**3), 2),
            'freeGb': round(free / (1024**3), 2),
        },
        'memory': _read_meminfo(),
        'uptimeSeconds': _read_uptime(),
        'python': subprocess.getoutput('python3 --version'),
    }


def get_task_queue() -> Dict[str, Any]:
    if not QUEUE_PATH.exists():
        return {'items': [], 'count': 0}
    import json
    data = json.loads(QUEUE_PATH.read_text(encoding='utf-8'))
    return {
        'items': data.get('items', []),
        'count': len(data.get('items', [])),
    }
