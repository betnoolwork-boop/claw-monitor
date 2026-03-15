from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter(prefix='/api/claims', tags=['claims'])

CLAIMS_PATH = Path(__file__).resolve().parents[5] / 'data' / 'claims_registry.json'

@router.get('/list')
def get_claims():
    try:
        if not CLAIMS_PATH.exists():
            return {'claims': [], 'count': 0}
        data = json.loads(CLAIMS_PATH.read_text(encoding='utf-8'))
        claims = data.get('claims', []) if isinstance(data, dict) else data
        
        # Сортировка: новые первые, по дедлайну
        now = __import__('datetime').datetime.now().isoformat()
        claims.sort(key=lambda c: (
            0 if c.get('status') == 'new' else 1,
            c.get('deadline', '9999'),
        ))
        
        return {
            'claims': claims,
            'count': len(claims),
            'new': len([c for c in claims if c.get('status') == 'new']),
            'in_progress': len([c for c in claims if c.get('status') == 'in_progress']),
            'done': len([c for c in claims if c.get('status') == 'done']),
        }
    except Exception as e:
        return {'error': str(e), 'claims': [], 'count': 0}

@router.get('/stats')
def get_claims_stats():
    try:
        if not CLAIMS_PATH.exists():
            return {'total': 0}
        data = json.loads(CLAIMS_PATH.read_text(encoding='utf-8'))
        claims = data.get('claims', []) if isinstance(data, dict) else data
        return {
            'total': len(claims),
            'new': len([c for c in claims if c.get('status') == 'new']),
            'in_progress': len([c for c in claims if c.get('status') == 'in_progress']),
            'done': len([c for c in claims if c.get('status') == 'done']),
        }
    except Exception as e:
        return {'error': str(e)}

@router.post('/{claim_id}/status')
def update_claim_status(claim_id: str, status: str):
    try:
        data = json.loads(CLAIMS_PATH.read_text(encoding='utf-8'))
        claims = data.get('claims', []) if isinstance(data, dict) else data
        for c in claims:
            if c.get('id') == claim_id:
                c['status'] = status
                CLAIMS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                return {'ok': True, 'id': claim_id, 'status': status}
        return {'ok': False, 'error': 'not found'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
