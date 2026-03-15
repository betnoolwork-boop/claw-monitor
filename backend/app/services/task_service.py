from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.runtime_service import get_runtime_agent_statuses, get_runtime_sessions

CRON_LABELS = {
    'openclaws-russia-daily-post-preview': 'Предпросмотр поста OpenClaws Russia',
    'tszh-claims-monitor': 'Мониторинг заявок ТСЖ',
    'morning-digest': 'Утренний дайджест',
    'morning-digest:boss': 'Утренний дайджест',
    'evening-digest': 'Вечерний дайджест',
    'backup:daily': 'Ежедневный бэкап',
    'finance-daily-report': 'Ежедневный финансовый отчёт',
    'finance-limit-alert': 'Проверка лимитов финансов',
    'finance-topic-import': 'Импорт финансового топика',
    'knowledge-save': 'Сохранение базы знаний',
    'thoughts-monitor': 'Мониторинг мыслей',
    'news-hot': 'Горячие новости',
    'news-daily': 'Ежедневные новости',
    'subagents-healthcheck': 'Проверка здоровья субагентов',
    'growth-review': 'Growth review',
    'doomsday-bot-daily-review': 'Ежедневный review Doomsday Bot',
    'finance:payment-reminder': 'Напоминание об оплатах',
}

CRON_ID_LABELS = {
    'a4f3378e-8d33-47da-b091-35931fd23d67': 'Проверка здоровья субагентов',
    '93b345d2-8fb8-4f6d-b23c-baa7f08b426b': 'Импорт финансового топика',
    'c1a6c4a4-cfd2-4a64-8703-2915a21e2df9': 'Сохранение базы знаний',
    '98ba8946-d66f-48c3-9ea4-7e9fd37a4dc9': 'Проверка лимитов финансов',
    '90605c87-a2a4-4422-99c1-3f42757b7a16': 'Вечерний дайджест',
    'a960ce09-b8c7-4d9f-89f8-7014f400c2d2': 'Мониторинг мыслей',
    'a35cc8b5-12fb-43e8-97f7-1ca03fff763e': 'Ежедневный финансовый отчёт',
    '0f0d208a-636d-475b-a333-2353056a11f7': 'Ежедневный бэкап',
    '1b440a81-8a80-43c0-b203-53b057bd71e5': 'Growth review',
    '9b20289c-6534-4402-a120-2abd06e3d32b': 'Утренний дайджест',
    '4288b39c-f2aa-4de2-bb79-c9582dab2a95': 'Ежедневный review Doomsday Bot',
    'a13090d7-0d17-4904-af45-6b0ad90b3621': 'Напоминание об оплатах',
    'e96df4bd-b327-4b23-aceb-818e0f272126': 'Мониторинг заявок ТСЖ',
    'e1d3ebf5-f462-4005-8020-c7f55f2b8dca': 'Предпросмотр поста OpenClaws Russia',
    '3ec65a5e-5c84-426d-9cac-168ab3641a5f': 'Напоминание: review Doomsday Bot',
}


def _to_seconds_ago(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        ts = float(raw) / 1000.0 if raw > 10_000_000_000 else float(raw)
        return int(datetime.now(timezone.utc).timestamp() - ts)
    return None


def _humanize_label(label: str) -> str:
    raw = str(label or '').strip()
    if not raw:
        return 'Task'
    for key, title in CRON_LABELS.items():
        if key in raw:
            return title
    if raw.startswith('Cron: '):
        raw = raw.replace('Cron: ', '', 1)
    raw = raw.replace('-', ' ').replace('_', ' ')
    return raw[:1].upper() + raw[1:]


def _extract_task_title(session: Dict[str, Any]) -> str:
    label = session.get('label') or session.get('displayName') or session.get('key')
    key = str(session.get('key', '') or '')

    if ':subagent:' in key:
        tail = key.split(':subagent:', 1)[-1]
        return f'Подагентная задача ({tail[:8]})'

    if ':cron:' in key:
        cron_id = key.split(':cron:', 1)[-1].split(':', 1)[0]
        if cron_id in CRON_ID_LABELS:
            return CRON_ID_LABELS[cron_id]
        return _humanize_label(str(label or key))

    messages = session.get('messages') or []
    if messages:
        first = messages[0]
        content = first.get('content') or []
        if isinstance(content, list):
            for part in content:
                text = part.get('text') if isinstance(part, dict) else None
                if text:
                    return str(text).split('\n')[0][:120]
    return _humanize_label(str(label or 'Task'))


def _priority_for(session: Dict[str, Any], source: str) -> str:
    label = str(session.get('label') or session.get('displayName') or '').lower()
    if 'backup' in label:
        return 'low'
    if 'digest' in label or 'news' in label:
        return 'medium'
    if source == 'subagent':
        return 'high'
    return 'medium'


def get_live_task_queue() -> Dict[str, Any]:
    sessions = get_runtime_sessions()
    runtime_agents = {a['id']: a for a in get_runtime_agent_statuses()}
    items: List[Dict[str, Any]] = []

    for session in sessions:
        key = str(session.get('key', '') or session.get('sessionKey', '') or '')
        agent_id = str(session.get('agentId', '') or '')
        title = _extract_task_title(session)
        updated = session.get('updatedAt') or session.get('lastMessageAt') or session.get('createdAt')
        seconds_ago = _to_seconds_ago(updated)

        if ':cron:' in key:
            status = 'scheduled'
            if seconds_ago is not None and seconds_ago < 900:
                status = 'recent'
            items.append({
                'id': key,
                'title': title,
                'status': status,
                'priority': _priority_for(session, 'cron'),
                'assignedAgent': agent_id or 'main',
                'source': 'cron',
                'secondsAgo': seconds_ago,
            })
        elif ':subagent:' in key:
            rt = runtime_agents.get(agent_id, {})
            status = 'running' if rt.get('runtimeState') in {'active', 'warm'} else 'done'
            items.append({
                'id': key,
                'title': title,
                'status': status,
                'priority': _priority_for(session, 'subagent'),
                'assignedAgent': agent_id or 'subagent',
                'source': 'subagent',
                'secondsAgo': seconds_ago,
            })

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (item.get('title'), item.get('source'), item.get('assignedAgent'))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda x: (x.get('secondsAgo') is None, x.get('secondsAgo', 10**9)))
    return {
        'items': deduped[:20],
        'count': len(deduped),
    }
