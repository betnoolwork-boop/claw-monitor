from __future__ import annotations

import subprocess
from typing import Any, Dict

from app.services.analytics_snapshot_service import prewarm_analytics_snapshot
from app.services.annotations_service import annotate_incident, annotate_session, clear_annotation
from app.services.details_service import get_agent_details
from app.services.incidents_service import get_incident_detail

ALLOWED_ACTIONS = {
    'refresh_runtime',
    'refresh_queue',
    'subagents_healthcheck',
    'dashboard_backend_restart',
    'dashboard_frontend_restart',
    'prewarm_snapshot',
    'annotate_watch',
    'annotate_mute',
    'annotate_note',
    'annotation_clear',
    'agent_details_refresh',
    'agent_runtime_probe',
    'incident_details_refresh',
}


def run_action(action: str, target: str | None = None, kind: str | None = None, note: str | None = None) -> Dict[str, Any]:
    if action not in ALLOWED_ACTIONS:
        return {'ok': False, 'message': 'Action not allowed'}

    if action == 'refresh_runtime':
        return {'ok': True, 'message': 'Runtime refresh requested. Просто обнови блоки дашборда.'}

    if action == 'refresh_queue':
        return {'ok': True, 'message': 'Queue refresh requested. Просто обнови блоки дашборда.'}

    if action == 'subagents_healthcheck':
        try:
            out = subprocess.check_output([
                'openclaw', 'agents', 'list'
            ], text=True, stderr=subprocess.STDOUT)
            return {'ok': True, 'message': 'Subagents healthcheck выполнен.', 'output': out[:1200]}
        except Exception as e:
            return {'ok': False, 'message': f'Healthcheck failed: {e}'}

    if action == 'dashboard_backend_restart':
        try:
            subprocess.check_call(['systemctl', 'restart', 'claw-monitor-backend.service'])
            return {'ok': True, 'message': 'Backend restarted'}
        except Exception as e:
            return {'ok': False, 'message': f'Backend restart failed: {e}'}

    if action == 'dashboard_frontend_restart':
        try:
            subprocess.check_call(['systemctl', 'restart', 'claw-monitor-frontend.service'])
            return {'ok': True, 'message': 'Frontend restarted'}
        except Exception as e:
            return {'ok': False, 'message': f'Frontend restart failed: {e}'}

    if action == 'prewarm_snapshot':
        try:
            result = prewarm_analytics_snapshot(force=True)
            meta = result.get('meta', {})
            return {'ok': True, 'message': f"Snapshot prewarmed. age={meta.get('ageSeconds')}s ttl={meta.get('ttlRemainingSeconds')}s", 'details': result}
        except Exception as e:
            return {'ok': False, 'message': f'Snapshot prewarm failed: {e}'}

    if action in {'annotate_watch', 'annotate_mute', 'annotate_note'}:
        if not target or kind not in {'session', 'incident'}:
            return {'ok': False, 'message': 'Annotation target/kind required'}
        mode = action.replace('annotate_', '')
        result = annotate_session(target, mode, note) if kind == 'session' else annotate_incident(target, mode, note)
        return {'ok': True, 'message': f'{kind} annotated as {mode}', 'details': result}

    if action == 'annotation_clear':
        if not target or kind not in {'session', 'incident'}:
            return {'ok': False, 'message': 'Annotation target/kind required'}
        result = clear_annotation(kind, target)
        return {'ok': bool(result.get('ok')), 'message': 'Annotation cleared' if result.get('ok') else result.get('message', 'Clear failed')}

    if action == 'agent_details_refresh':
        if not target:
            return {'ok': False, 'message': 'Agent target required'}
        details = get_agent_details(target)
        if not details.get('found'):
            return {'ok': False, 'message': f'Agent {target} not found'}
        agent = details.get('agent', {})
        return {
            'ok': True,
            'message': f'Agent {target}: runtime={agent.get("runtimeState")}, seen={agent.get("lastSeenSecondsAgo")}, sessions={agent.get("sessionCount")}',
            'details': details,
        }

    if action == 'agent_runtime_probe':
        if not target:
            return {'ok': False, 'message': 'Agent target required'}
        try:
            out = subprocess.check_output(['openclaw', 'sessions', '--json', '--all-agents'], text=True, stderr=subprocess.DEVNULL)
            snippet = out[:1200]
            return {'ok': True, 'message': f'Runtime probe выполнен для {target}.', 'output': snippet}
        except Exception as e:
            return {'ok': False, 'message': f'Agent runtime probe failed: {e}'}

    if action == 'incident_details_refresh':
        if not target:
            return {'ok': False, 'message': 'Incident target required'}
        details = get_incident_detail(target)
        if not details.get('found'):
            return {'ok': False, 'message': f'Incident {target} not found'}
        event = details.get('event', {})
        return {
            'ok': True,
            'message': f'Incident {event.get("kind")}: {event.get("provider")}/{event.get("model")} · session={event.get("sessionKey")}',
            'details': details,
        }

    return {'ok': False, 'message': 'Unhandled action'}
