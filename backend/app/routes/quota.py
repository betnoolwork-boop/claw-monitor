from fastapi import APIRouter, Response
from pathlib import Path
import subprocess
import json

router = APIRouter(prefix='/api/quota', tags=['quota'])

SCRIPT = Path(__file__).resolve().parents[5] / 'scripts' / 'quota_monitor.py'

@router.get('/status')
def get_quota_status():
    try:
        result = subprocess.run(
            ['python3', str(SCRIPT), 'json'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {'error': result.stderr}
    except Exception as e:
        return {'error': str(e)}

@router.get('/alert')
def get_quota_alert():
    try:
        result = subprocess.run(
            ['python3', str(SCRIPT), 'alert'],
            capture_output=True, text=True, timeout=15
        )
        return {
            'alert': result.returncode != 0,
            'output': result.stdout.strip(),
            'exit_code': result.returncode
        }
    except Exception as e:
        return {'error': str(e)}
