from __future__ import annotations

from typing import Any, Dict, List

from app.services.analytics_snapshot_service import build_analytics_snapshot


def get_incident_events() -> List[Dict[str, Any]]:
    return build_analytics_snapshot().get('incidentEvents', [])


def get_incident_summary() -> Dict[str, Any]:
    return build_analytics_snapshot().get('incidentSummary', {})


def get_provider_incidents() -> Dict[str, Any]:
    summary = get_incident_summary()
    return {
        'count': len(summary.get('providers', [])),
        'items': summary.get('providers', []),
    }


def get_incident_timeline() -> Dict[str, Any]:
    return build_analytics_snapshot().get('incidentTimeline', {'buckets': [], 'topKinds': []})


def get_incident_detail(event_id: str) -> Dict[str, Any]:
    snapshot = build_analytics_snapshot()
    events = snapshot.get('incidentEvents', [])
    event = next((item for item in events if item.get('id') == event_id), None)
    if not event:
        return {'found': False, 'message': 'Incident not found'}

    base_key = event.get('baseKey')
    related_sessions = [
        {
            'sessionKey': s.get('key'),
            'baseKey': base_key,
            'sessionTitle': event.get('sessionTitle'),
            'agentId': s.get('agentId'),
            'sessionKind': s.get('kind'),
            'provider': s.get('modelProvider') or 'unknown',
            'model': s.get('model') or 'unknown',
            'ageSeconds': event.get('ageSeconds') if str(s.get('key')) == str(event.get('sessionKey')) else None,
            'inputTokens': s.get('inputTokens'),
            'outputTokens': s.get('outputTokens'),
            'totalTokens': s.get('totalTokens'),
            'totalTokensFresh': s.get('totalTokensFresh'),
            'contextTokens': s.get('contextTokens'),
            'ratio': event.get('ratio') if str(s.get('key')) == str(event.get('sessionKey')) else None,
            'abortedLastRun': bool(s.get('abortedLastRun')),
            'systemSent': bool(s.get('systemSent')),
        }
        for s in snapshot.get('sessions', [])
        if str(s.get('key', '')).split(':run:', 1)[0] == base_key
    ][:10]
    related_events = [item for item in events if item.get('baseKey') == base_key][:10]

    return {
        'found': True,
        'event': event,
        'relatedSessions': related_sessions,
        'relatedEvents': related_events,
        'remediation': event.get('remediation', {}),
    }
