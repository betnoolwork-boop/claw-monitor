from __future__ import annotations

from typing import Any, Dict, List

from app.services.growth_service import get_growth_summary
from app.services.incidents_service import get_incident_summary
from app.services.runtime_service import get_runtime_agent_statuses
from app.services.task_service import get_live_task_queue


def get_alerts() -> Dict[str, Any]:
    alerts: List[Dict[str, Any]] = []

    runtime_agents = get_runtime_agent_statuses()
    unknown_agents = [a for a in runtime_agents if a.get('runtimeState') == 'unknown']
    active_agents = [a for a in runtime_agents if a.get('runtimeState') == 'active']

    if len(unknown_agents) >= 10:
        alerts.append({
            'level': 'warning',
            'title': 'Много агентов без runtime-сигнала',
            'message': f'Unknown runtime у {len(unknown_agents)} агентов. Нужна дальнейшая нормализация live layer.',
            'source': 'runtime',
        })

    if len(active_agents) == 0:
        alerts.append({
            'level': 'info',
            'title': 'Нет явно active-агентов',
            'message': 'Сейчас нет агентов с runtimeState=active. Возможно, система в тихом режиме или эвристика слишком грубая.',
            'source': 'runtime',
        })

    queue = get_live_task_queue()
    running_tasks = [x for x in queue.get('items', []) if x.get('status') == 'running']
    scheduled_tasks = [x for x in queue.get('items', []) if x.get('status') == 'scheduled']

    if len(running_tasks) >= 3:
        alerts.append({
            'level': 'info',
            'title': 'Есть активный task flow',
            'message': f'Сейчас видно {len(running_tasks)} running-задач.',
            'source': 'queue',
        })

    if len(scheduled_tasks) >= 10:
        alerts.append({
            'level': 'info',
            'title': 'Плотный cron-поток',
            'message': f'В operational feed видно {len(scheduled_tasks)} scheduled-задач.',
            'source': 'queue',
        })

    growth = get_growth_summary()
    if growth.get('signal') == 'high':
        alerts.append({
            'level': 'warning',
            'title': 'Высокий growth signal',
            'message': f'Открытых growth proposals: {growth.get("openProposals")}. Есть смысл выбрать следующий апгрейд.',
            'source': 'growth',
        })

    incidents = get_incident_summary()
    if incidents.get('critical', 0) > 0:
        alerts.append({
            'level': 'warning',
            'title': 'Есть критичные model/provider инциденты',
            'message': f'Критичных событий: {incidents.get("critical")}. Топ issue: {(incidents.get("topIssue") or {}).get("title", "—")}.',
            'source': 'incidents',
        })
    elif incidents.get('warning', 0) > 0:
        alerts.append({
            'level': 'info',
            'title': 'Есть предупреждения по model/provider layer',
            'message': f'Warning-событий: {incidents.get("warning")}, info-событий: {incidents.get("info")}.',
            'source': 'incidents',
        })

    return {
        'count': len(alerts),
        'items': alerts,
    }
