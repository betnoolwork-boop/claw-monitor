from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parents[5]
PRESETS_DIR = BASE_DIR / 'projects' / 'claw-monitor' / 'data' / 'presets'
PRESETS_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULT_PRESETS = [
    {
        'name': 'Только критичные',
        'description': 'Показывать только критичные инциденты и горячие сессии',
        'filters': {
            'incidents': {'levels': ['critical']},
            'hot_sessions': {'min_hot_score': 30},
            'hide_muted': True,
        },
        'is_default': True,
    },
    {
        'name': 'Только watchlist',
        'description': 'Показывать только watch-объекты',
        'filters': {
            'show_watchlist_only': True,
            'hide_muted': True,
        },
        'is_default': False,
    },
    {
        'name': 'Активные + горячие',
        'description': 'Показывать активные сессии и горячие задачи',
        'filters': {
            'incidents': {'levels': ['warning', 'info', 'critical']},
            'hot_sessions': {'min_hot_score': 10},
            'tasks': {'status': 'active'},
            'hide_muted': True,
        },
        'is_default': False,
    },
    {
        'name': 'Утренний обзор',
        'description': 'Полный обзор с устаревшими фильтрами',
        'filters': {
            'incidents': {'max_age_hours': 24},
            'hot_sessions': {'max_age_hours': 6},
            'tasks': {'max_age_hours': 24},
            'hide_muted': False,
        },
        'is_default': False,
    },
]

def _load_preset(preset_id: str) -> Optional[Dict[str, Any]]:
    preset_path = PRESETS_DIR / f'{preset_id}.json'
    if not preset_path.exists():
        return None
    try:
        return json.loads(preset_path.read_text(encoding='utf-8'))
    except Exception:
        return None

def _save_preset(preset_id: str, data: Dict[str, Any]) -> None:
    preset_path = PRESETS_DIR / f'{preset_id}.json'
    data['updated_at'] = time.time()
    preset_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def _preset_to_response(preset: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': preset['id'],
        'name': preset['name'],
        'description': preset.get('description'),
        'filters': preset['filters'],
        'is_default': preset['is_default'],
        'created_at': preset['created_at'],
        'updated_at': preset['updated_at'],
        'owner': preset['owner'],
    }

def get_presets(owner: str) -> List[Dict[str, Any]]:
    presets = []
    for preset_path in PRESETS_DIR.glob('*.json'):
        preset = _load_preset(preset_path.stem)
        if preset and preset.get('owner') == owner:
            presets.append(_preset_to_response(preset))
    presets.sort(key=lambda p: (not p['is_default'], p['name'].lower()))
    return presets

def create_preset(data: Dict[str, Any], owner: str) -> Dict[str, Any]:
    preset_id = str(uuid.uuid4())
    created_at = time.time()
    preset = {
        'id': preset_id,
        'name': data['name'],
        'description': data.get('description'),
        'filters': data['filters'],
        'is_default': data.get('is_default', False),
        'created_at': created_at,
        'updated_at': created_at,
        'owner': owner,
    }
    _save_preset(preset_id, preset)
    return _preset_to_response(preset)

def update_preset(preset_id: str, data: Dict[str, Any], owner: str) -> Dict[str, Any]:
    preset = _load_preset(preset_id)
    if not preset or preset.get('owner') != owner:
        raise ValueError('Preset not found or access denied')
    preset.update({
        'name': data.get('name', preset['name']),
        'description': data.get('description', preset.get('description')),
        'filters': data.get('filters', preset['filters']),
        'is_default': data.get('is_default', preset['is_default']),
    })
    _save_preset(preset_id, preset)
    return _preset_to_response(preset)

def delete_preset(preset_id: str, owner: str) -> Dict[str, Any]:
    preset = _load_preset(preset_id)
    if not preset or preset.get('owner') != owner:
        raise ValueError('Preset not found or access denied')
    preset_path = PRESETS_DIR / f'{preset_id}.json'
    if preset_path.exists():
        preset_path.unlink()
    return {'ok': True, 'id': preset_id}

def apply_preset(preset_id: str, owner: str) -> Dict[str, Any]:
    preset = _load_preset(preset_id)
    if not preset or preset.get('owner') != owner:
        raise ValueError('Preset not found or access denied')
    return {
        'ok': True,
        'preset': _preset_to_response(preset),
        'filters': preset['filters'],
    }

def get_default_presets() -> List[Dict[str, Any]]:
    defaults = []
    for preset_data in _DEFAULT_PRESETS:
        preset_id = f'default-{preset_data["name"].lower().replace(' ', '-').replace('ё', 'е')}'
        preset = {
            'id': preset_id,
            'name': preset_data['name'],
            'description': preset_data['description'],
            'filters': preset_data['filters'],
            'is_default': preset_data['is_default'],
            'created_at': 0.0,
            'updated_at': 0.0,
            'owner': 'system',
        }
        defaults.append(preset)
    return defaults

def initialize_default_presets(owner: str) -> List[Dict[str, Any]]:
    created = []
    for preset_data in _DEFAULT_PRESETS:
        preset_id = f'default-{preset_data["name"].lower().replace(' ', '-').replace('ё', 'е')}'
        if not _load_preset(preset_id):
            created_at = time.time()
            preset = {
                'id': preset_id,
                'name': preset_data['name'],
                'description': preset_data['description'],
                'filters': preset_data['filters'],
                'is_default': preset_data['is_default'],
                'created_at': created_at,
                'updated_at': created_at,
                'owner': owner,
            }
            _save_preset(preset_id, preset)
            created.append(_preset_to_response(preset))
    return created