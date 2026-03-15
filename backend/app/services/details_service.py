from __future__ import annotations

from typing import Any, Dict, List

from app.services.analytics_snapshot_service import build_analytics_snapshot, get_cached_snapshot_meta
from app.services.annotations_service import summarize_annotations
from app.services.runtime_service import get_runtime_agent_statuses, get_runtime_summary
from app.services.task_service import get_live_task_queue
from app.services.alerts_service import get_alerts
from app.services.incidents_service import get_incident_events, get_incident_summary, get_incident_timeline, get_provider_incidents
from app.services.llm_service import get_expensive_sessions, get_hot_sessions, get_llm_by_model, get_llm_by_provider, get_llm_summary, get_provider_health
from app.services.registry_service import get_registry_agents, get_registry_summary, get_registry_topology
from app.services.growth_service import get_growth_proposals, get_growth_summary
from app.services.system_service import get_system_status


def get_agent_details(agent_id: str) -> Dict[str, Any]:
    agents = get_runtime_agent_statuses()
    agent = next((a for a in agents if a.get('id') == agent_id), None)
    if not agent:
        return {'found': False, 'message': 'Agent not found'}

    related_tasks = [
        t for t in get_live_task_queue().get('items', [])
        if t.get('assignedAgent') == agent_id
    ]

    return {
        'found': True,
        'agent': agent,
        'tasks': related_tasks[:10],
    }


def get_dashboard_insights() -> Dict[str, Any]:
    alerts = get_alerts().get('items', [])
    queue = get_live_task_queue().get('items', [])
    running = [q for q in queue if q.get('status') == 'running'][:5]
    recent = sorted(queue, key=lambda x: x.get('secondsAgo') if x.get('secondsAgo') is not None else 10**9)[:5]
    incident_summary = get_incident_summary()
    incident_events = get_incident_events()[:5]
    return {
        'alerts': alerts[:5],
        'runningTasks': running,
        'recentTasks': recent,
        'incidentSummary': incident_summary,
        'incidents': incident_events,
    }


def get_session_details(session_key: str) -> Dict[str, Any]:
    snapshot = build_analytics_snapshot()
    sessions = snapshot.get('sessions', [])
    incidents = snapshot.get('incidentEvents', [])
    queue_items = (get_live_task_queue() or {}).get('items', [])
    runtime_agents = {a.get('id'): a for a in get_runtime_agent_statuses()}

    session = next((s for s in sessions if str(s.get('key')) == str(session_key)), None)
    if not session:
        return {'found': False, 'message': 'Session not found'}

    base_key = str(session.get('key', '')).split(':run:', 1)[0]
    related_sessions = [s for s in sessions if str(s.get('key', '')).split(':run:', 1)[0] == base_key]
    related_incidents = [e for e in incidents if e.get('baseKey') == base_key or str(e.get('sessionKey', '')).split(':run:', 1)[0] == base_key]
    related_queue = [q for q in queue_items if str(q.get('id', '')).split(':run:', 1)[0] == base_key or q.get('assignedAgent') == session.get('agentId')]
    agent = runtime_agents.get(session.get('agentId'))

    annotations = summarize_annotations()
    return {
        'found': True,
        'session': {
            'key': session.get('key'),
            'agentId': session.get('agentId'),
            'kind': session.get('kind'),
            'provider': session.get('modelProvider') or 'unknown',
            'model': session.get('model') or 'unknown',
            'inputTokens': session.get('inputTokens'),
            'outputTokens': session.get('outputTokens'),
            'totalTokens': session.get('totalTokens'),
            'totalTokensFresh': session.get('totalTokensFresh'),
            'contextTokens': session.get('contextTokens'),
            'abortedLastRun': bool(session.get('abortedLastRun')),
            'label': session.get('label') or session.get('displayName'),
        },
        'agent': agent,
        'annotation': (annotations.get('sessions') or {}).get(session_key),
        'relatedSessions': [
            {
                'key': s.get('key'),
                'provider': s.get('modelProvider') or 'unknown',
                'model': s.get('model') or 'unknown',
                'totalTokens': s.get('totalTokens'),
                'kind': s.get('kind'),
            }
            for s in related_sessions[:10]
        ],
        'incidents': related_incidents[:10],
        'queue': related_queue[:10],
    }


def get_dashboard_snapshot() -> Dict[str, Any]:
    registry_summary = get_registry_summary()
    registry_agents = get_registry_agents()
    registry_topology = get_registry_topology()
    runtime_summary = get_runtime_summary()
    runtime_agents = get_runtime_agent_statuses()
    system_status = get_system_status()
    alerts = get_alerts()
    queue = get_live_task_queue()
    growth_summary = get_growth_summary()
    growth_proposals = get_growth_proposals()
    incident_summary = get_incident_summary()
    incident_events = get_incident_events()
    incident_timeline = get_incident_timeline()
    incident_providers = get_provider_incidents()
    llm_summary = get_llm_summary()
    llm_providers = get_llm_by_provider()
    llm_models = get_llm_by_model()
    llm_expensive = get_expensive_sessions()
    llm_health = get_provider_health()
    llm_hot = get_hot_sessions()
    insights = get_dashboard_insights()
    annotations = summarize_annotations()

    session_annotations = annotations.get('sessions', {})
    incident_annotations = annotations.get('incidents', {})
    for item in incident_events:
        item['annotation'] = incident_annotations.get(item.get('id'))
    for item in llm_expensive.get('items', []):
        item['annotation'] = session_annotations.get(item.get('sessionKey'))
    for item in llm_hot.get('items', []):
        item['annotation'] = session_annotations.get(item.get('sessionKey'))
    for item in queue.get('items', []):
        item['annotation'] = session_annotations.get(item.get('id'))

    return {
        'overview': {
            'registry': registry_summary,
            'runtime': runtime_summary,
            'growth': growth_summary,
        },
        'alerts': alerts,
        'system': system_status,
        'runtime': {
            'summary': runtime_summary,
            'agents': runtime_agents,
        },
        'registry': {
            'summary': registry_summary,
            'agents': registry_agents,
            'topology': registry_topology,
        },
        'tasks': queue,
        'growth': {
            'summary': growth_summary,
            'proposals': growth_proposals,
        },
        'incidents': {
            'summary': incident_summary,
            'events': {'items': incident_events},
            'providers': incident_providers,
            'timeline': incident_timeline,
        },
        'llm': {
            'summary': llm_summary,
            'providers': llm_providers,
            'models': llm_models,
            'expensiveSessions': llm_expensive,
            'providerHealth': llm_health,
            'hotSessions': llm_hot,
        },
        'insights': insights,
        'annotations': annotations,
        'snapshotMeta': get_cached_snapshot_meta(),
    }
