from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.registry_service import get_registry_agents

_SESSIONS_CACHE: Dict[str, Any] = {
    'expiresAt': 0.0,
    'value': None,
}
_SESSION_TTL_SECONDS = 30.0


def _run_sessions_list() -> Dict[str, Any]:
    cmd = [
        'openclaw', 'sessions',
        '--json',
        '--all-agents',
    ]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except Exception:
        return {'sessions': []}


def _parse_iso(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
    except Exception:
        return None


def get_runtime_sessions() -> List[Dict[str, Any]]:
    now = time.time()
    if _SESSIONS_CACHE['value'] is not None and now < _SESSIONS_CACHE['expiresAt']:
        return _SESSIONS_CACHE['value']

    data = _run_sessions_list()
    sessions = data.get('sessions', data if isinstance(data, list) else [])
    recent = data.get('recent', []) if isinstance(data, dict) else []
    if isinstance(sessions, list) and sessions:
        result = sessions
    elif isinstance(recent, list):
        result = recent
    else:
        result = []

    _SESSIONS_CACHE['value'] = result
    _SESSIONS_CACHE['expiresAt'] = now + _SESSION_TTL_SECONDS
    return result


def get_runtime_agent_statuses() -> List[Dict[str, Any]]:
    registry_agents = get_registry_agents()
    sessions = get_runtime_sessions()
    now = datetime.now(timezone.utc).timestamp()

    mapped: List[Dict[str, Any]] = []
    for agent in registry_agents:
        agent_id = agent.get('id')
        related = []
        for session in sessions:
            key = str(session.get('key', '') or session.get('sessionKey', '') or '')
            session_agent = str(session.get('agentId', '') or '')
            if session_agent == agent_id or f'agent:{agent_id}:' in key or key == f'agent:{agent_id}:main':
                related.append(session)

        latest_seen = None
        latest_session = None
        for session in related:
            raw_updated = session.get('updatedAt') or session.get('lastMessageAt') or session.get('createdAt')
            if isinstance(raw_updated, (int, float)):
                ts = float(raw_updated) / 1000.0 if raw_updated > 10_000_000_000 else float(raw_updated)
            else:
                ts = _parse_iso(raw_updated)
            if ts and (latest_seen is None or ts > latest_seen):
                latest_seen = ts
                latest_session = session

        seconds_ago = int(now - latest_seen) if latest_seen else None
        runtime_state = 'idle'
        if seconds_ago is None:
            runtime_state = 'unknown'
        elif seconds_ago < 300:
            runtime_state = 'active'
        elif seconds_ago < 3600:
            runtime_state = 'warm'
        else:
            runtime_state = 'idle'

        latest_message = None
        if latest_session:
            messages = latest_session.get('messages') or []
            if messages:
                content = messages[-1].get('content') or []
                if isinstance(content, list):
                    for part in content:
                        text = part.get('text') if isinstance(part, dict) else None
                        if text:
                            latest_message = str(text).split('\n')[0][:160]
                            break

        mapped.append({
            'id': agent_id,
            'name': agent.get('name', agent_id),
            'tier': agent.get('tier'),
            'priority': agent.get('priority'),
            'registryStatus': agent.get('status'),
            'runtimeState': runtime_state,
            'lastSeenSecondsAgo': seconds_ago,
            'sessionCount': len(related),
            'latestSessionKey': (latest_session or {}).get('key') or (latest_session or {}).get('sessionKey'),
            'latestMessage': latest_message,
        })

    return mapped


def get_runtime_summary() -> Dict[str, Any]:
    agents = get_runtime_agent_statuses()
    return {
        'active': len([a for a in agents if a.get('runtimeState') == 'active']),
        'warm': len([a for a in agents if a.get('runtimeState') == 'warm']),
        'idle': len([a for a in agents if a.get('runtimeState') == 'idle']),
        'unknown': len([a for a in agents if a.get('runtimeState') == 'unknown']),
        'total': len(agents),
    }
