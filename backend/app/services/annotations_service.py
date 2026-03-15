from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parents[5]
ANNOTATIONS_PATH = BASE_DIR / 'projects' / 'claw-monitor' / 'data' / 'annotations.json'


def _load() -> Dict[str, Any]:
    if not ANNOTATIONS_PATH.exists():
        return {'sessions': {}, 'incidents': {}, 'updatedAt': None}
    try:
        return json.loads(ANNOTATIONS_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {'sessions': {}, 'incidents': {}, 'updatedAt': None}


def _save(data: Dict[str, Any]) -> None:
    data['updatedAt'] = time.time()
    ANNOTATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANNOTATIONS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def get_annotations() -> Dict[str, Any]:
    return _load()


def annotate_session(session_key: str, mode: str, note: str | None = None) -> Dict[str, Any]:
    data = _load()
    entry = {
        'mode': mode,
        'note': note or '',
        'updatedAt': time.time(),
    }
    data.setdefault('sessions', {})[session_key] = entry
    _save(data)
    return {'ok': True, 'entry': entry}


def annotate_incident(event_id: str, mode: str, note: str | None = None) -> Dict[str, Any]:
    data = _load()
    entry = {
        'mode': mode,
        'note': note or '',
        'updatedAt': time.time(),
    }
    data.setdefault('incidents', {})[event_id] = entry
    _save(data)
    return {'ok': True, 'entry': entry}


def clear_annotation(kind: str, target: str) -> Dict[str, Any]:
    data = _load()
    bucket = 'sessions' if kind == 'session' else 'incidents'
    if target in data.get(bucket, {}):
        del data[bucket][target]
        _save(data)
        return {'ok': True}
    return {'ok': False, 'message': 'Annotation not found'}


def summarize_annotations() -> Dict[str, Any]:
    data = _load()
    sessions = data.get('sessions', {})
    incidents = data.get('incidents', {})
    watch_sessions = [k for k, v in sessions.items() if v.get('mode') == 'watch']
    muted_sessions = [k for k, v in sessions.items() if v.get('mode') == 'mute']
    noted_sessions = [k for k, v in sessions.items() if v.get('mode') == 'note']
    muted_incidents = [k for k, v in incidents.items() if v.get('mode') == 'mute']
    watch_incidents = [k for k, v in incidents.items() if v.get('mode') == 'watch']
    return {
        'updatedAt': data.get('updatedAt'),
        'sessions': sessions,
        'incidents': incidents,
        'counts': {
            'watchSessions': len(watch_sessions),
            'mutedSessions': len(muted_sessions),
            'notedSessions': len(noted_sessions),
            'watchIncidents': len(watch_incidents),
            'mutedIncidents': len(muted_incidents),
        },
        'watchSessions': watch_sessions[:10],
        'mutedSessions': muted_sessions[:10],
    }
