from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from app.services.runtime_service import get_runtime_sessions


SNAPSHOT_TTL_SECONDS = 60.0

_PROVIDER_COST_HINTS = {
    'openai-codex': 3.0,
    'openrouter': 1.4,
    'bailian': 1.8,
    'unknown': 1.0,
}

_SEVERITY_RANK = {
    'critical': 4,
    'warning': 3,
    'info': 2,
    'ok': 1,
}

_TIMELINE_BUCKETS = [
    ('lt1h', 3600),
    ('lt6h', 6 * 3600),
    ('lt24h', 24 * 3600),
    ('gte24h', None),
]

_CACHE: Dict[str, Any] = {
    'expiresAt': 0.0,
    'value': None,
}


def get_cached_snapshot_meta() -> Dict[str, Any]:
    value = _CACHE.get('value') or {}
    built_at = value.get('builtAt')
    expires_at = _CACHE.get('expiresAt', 0.0)
    now = time.time()
    return {
        'hasValue': bool(value),
        'builtAt': built_at,
        'expiresAt': expires_at,
        'ageSeconds': round(now - built_at, 3) if isinstance(built_at, (int, float)) else None,
        'ttlRemainingSeconds': round(max(0.0, expires_at - now), 3),
    }


def prewarm_analytics_snapshot(force: bool = False) -> Dict[str, Any]:
    if force:
        _CACHE['expiresAt'] = 0.0
    snap = build_analytics_snapshot()
    return {
        'ok': True,
        'meta': get_cached_snapshot_meta(),
        'sessionsTracked': len(snap.get('sessions', [])),
    }


def _session_age_seconds(session: Dict[str, Any]) -> int | None:
    updated = session.get('updatedAt')
    if isinstance(updated, (int, float)):
        ts = float(updated) / 1000.0 if updated > 10_000_000_000 else float(updated)
        return int(time.time() - ts)
    age_ms = session.get('ageMs')
    if isinstance(age_ms, (int, float)):
        return int(float(age_ms) / 1000.0)
    return None


def _base_key(key: str) -> str:
    raw = str(key or '')
    if ':run:' in raw:
        return raw.split(':run:', 1)[0]
    return raw


def _short_title(session: Dict[str, Any]) -> str:
    key = str(session.get('key', '') or '')
    base = _base_key(key)
    if ':telegram:direct:' in base:
        return 'Telegram direct'
    if ':telegram:group:' in base:
        return 'Telegram group'
    if ':cron:' in base:
        return f'Cron task {base.rsplit(":cron:", 1)[-1][:8]}'
    if ':subagent:' in base:
        return f'Subagent {base.rsplit(":subagent:", 1)[-1][:8]}'
    return base or 'session'


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    try:
        n = float(numerator)
        d = float(denominator)
        if d <= 0:
            return None
        return n / d
    except Exception:
        return None


def _session_total_tokens(session: Dict[str, Any]) -> int:
    total = session.get('totalTokens')
    if isinstance(total, (int, float)):
        return int(total)
    input_tokens = session.get('inputTokens') or 0
    output_tokens = session.get('outputTokens') or 0
    if isinstance(input_tokens, (int, float)) or isinstance(output_tokens, (int, float)):
        return int((input_tokens or 0) + (output_tokens or 0))
    return 0


def _estimated_cost(provider: str, total_tokens: int) -> float:
    weight = _PROVIDER_COST_HINTS.get(provider or 'unknown', 1.0)
    return round((total_tokens / 1000.0) * weight, 3)


def _health_label(score: int) -> str:
    if score >= 85:
        return 'healthy'
    if score >= 65:
        return 'watch'
    return 'unstable'


def _incident_remediation(kind: str, event: Dict[str, Any]) -> Dict[str, Any]:
    ratio = event.get('ratio')
    provider = event.get('provider') or 'unknown'
    model = event.get('model') or 'unknown'
    if kind == 'context_overflow_risk':
        return {
            'summary': 'Контекст уже вышел за безопасный предел.',
            'confidence': 'high',
            'hints': [
                'Сжать prompt/context перед следующим прогоном.',
                'Разбить задачу на 2+ шага вместо одного длинного прохода.',
                'Для этого cron/session выбрать модель с большим или более устойчивым контекстным окном.',
                'Проверить, не тянется ли лишний исторический хвост в session memory.',
            ],
            'safeActions': [
                {'action': 'incident_details_refresh', 'label': 'Refresh incident'},
                {'action': 'refresh_runtime', 'label': 'Refresh runtime'},
                {'action': 'refresh_queue', 'label': 'Refresh queue'},
            ],
        }
    if kind == 'context_saturation':
        return {
            'summary': 'Контекст близок к перегрузке, но ещё не критичен.',
            'confidence': 'high' if isinstance(ratio, (int, float)) and ratio >= 0.9 else 'medium',
            'hints': [
                'Сократить system/context payload до следующего запуска.',
                'Вынести справочный блок в краткую summary-форму.',
                'Для повторяющихся cron-задач ограничить накопление длинной истории.',
            ],
            'safeActions': [
                {'action': 'incident_details_refresh', 'label': 'Refresh incident'},
                {'action': 'refresh_runtime', 'label': 'Refresh runtime'},
            ],
        }
    if kind == 'fallback_chain':
        return {
            'summary': 'Один и тот же поток ходил через несколько model/provider variants.',
            'confidence': 'medium',
            'hints': [
                f'Проверить, intentional ли fallback с {provider}/{model} на альтернативы или наоборот.',
                'Разделить штатный routing и аварийный fallback, чтобы в UI это не выглядело как шум.',
                'Если fallback полезный — сохранить policy/причину явно.',
            ],
            'safeActions': [
                {'action': 'incident_details_refresh', 'label': 'Refresh incident'},
                {'action': 'refresh_runtime', 'label': 'Refresh runtime'},
            ],
        }
    if kind == 'generation_aborted':
        return {
            'summary': 'Последний запуск завершился abort-сигналом.',
            'confidence': 'medium',
            'hints': [
                'Проверить, был ли это ручной stop или системный abort.',
                'Сверить runtime state и queue state для этой же session/task.',
                'Если abort повторяется — выделить отдельный alert pattern.',
            ],
            'safeActions': [
                {'action': 'incident_details_refresh', 'label': 'Refresh incident'},
                {'action': 'refresh_runtime', 'label': 'Refresh runtime'},
                {'action': 'refresh_queue', 'label': 'Refresh queue'},
            ],
        }
    if kind == 'visibility_gap':
        return {
            'summary': 'По session не хватает свежих token/usage метрик.',
            'confidence': 'medium',
            'hints': [
                'Проверить, это старая сессия, subagent-run или реальная telemetry gap.',
                'Отделить archival sessions от live sessions в summary/UI.',
                'Не считать такой поток надёжным источником для spend/usage аналитики.',
            ],
            'safeActions': [
                {'action': 'incident_details_refresh', 'label': 'Refresh incident'},
                {'action': 'refresh_runtime', 'label': 'Refresh runtime'},
            ],
        }
    return {
        'summary': 'Нужен ручной разбор паттерна.',
        'confidence': 'low',
        'hints': [
            'Посмотреть related sessions и related events.',
            'Сверить incident c runtime/queue/alerts слоями.',
        ],
        'safeActions': [{'action': 'incident_details_refresh', 'label': 'Refresh incident'}],
    }


def _classify_session(session: Dict[str, Any]) -> Dict[str, Any]:
    ratio = _safe_ratio(session.get('inputTokens'), session.get('contextTokens'))
    return {
        'sessionKey': session.get('key'),
        'baseKey': _base_key(str(session.get('key', '') or '')),
        'sessionTitle': _short_title(session),
        'agentId': session.get('agentId'),
        'sessionKind': session.get('kind'),
        'provider': session.get('modelProvider') or 'unknown',
        'model': session.get('model') or 'unknown',
        'ageSeconds': _session_age_seconds(session),
        'inputTokens': session.get('inputTokens'),
        'outputTokens': session.get('outputTokens'),
        'totalTokens': session.get('totalTokens'),
        'totalTokensFresh': session.get('totalTokensFresh'),
        'contextTokens': session.get('contextTokens'),
        'ratio': ratio,
        'abortedLastRun': bool(session.get('abortedLastRun')),
        'systemSent': bool(session.get('systemSent')),
    }


def _make_event(level: str, kind: str, title: str, message: str, session: Dict[str, Any], extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    item = {'level': level, 'kind': kind, 'title': title, 'message': message}
    item.update(_classify_session(session))
    if extra:
        item.update(extra)
    item['remediation'] = _incident_remediation(kind, item)
    item['id'] = f"{item['kind']}::{item['sessionKey']}"
    return item


def build_analytics_snapshot() -> Dict[str, Any]:
    now = time.time()
    if _CACHE['value'] is not None and now < _CACHE['expiresAt']:
        return _CACHE['value']

    sessions = get_runtime_sessions()
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    events: List[Dict[str, Any]] = []

    llm_provider_rows = defaultdict(lambda: {'provider': None, 'sessions': 0, 'tokens': 0, 'estimatedCostIndex': 0.0, 'models': set(), 'freshSessions': 0})
    llm_model_rows = defaultdict(lambda: {'model': None, 'provider': None, 'sessions': 0, 'tokens': 0, 'estimatedCostIndex': 0.0, 'freshSessions': 0})
    incident_provider_rows = defaultdict(lambda: {'provider': None, 'sessions': 0, 'models': set(), 'highContext': 0, 'aborted': 0, 'visibilityGaps': 0})

    tokens_total = 0
    estimated_cost_total = 0.0
    fresh_sessions = 0
    provider_counts = defaultdict(int)
    model_counts = defaultdict(int)

    for session in sessions:
        key = str(session.get('key', '') or '')
        grouped[_base_key(key)].append(session)

        provider = str(session.get('modelProvider') or 'unknown')
        model = str(session.get('model') or 'unknown')
        total_tokens = _session_total_tokens(session)
        estimated_cost = _estimated_cost(provider, total_tokens)
        ratio = _safe_ratio(session.get('inputTokens'), session.get('contextTokens'))

        tokens_total += total_tokens
        estimated_cost_total += estimated_cost
        provider_counts[provider] += 1
        model_counts[model] += 1
        if session.get('totalTokensFresh') is True:
            fresh_sessions += 1

        prow = llm_provider_rows[provider]
        prow['provider'] = provider
        prow['sessions'] += 1
        prow['tokens'] += total_tokens
        prow['estimatedCostIndex'] += estimated_cost
        prow['models'].add(model)
        if session.get('totalTokensFresh') is True:
            prow['freshSessions'] += 1

        mkey = f'{provider}::{model}'
        mrow = llm_model_rows[mkey]
        mrow['provider'] = provider
        mrow['model'] = model
        mrow['sessions'] += 1
        mrow['tokens'] += total_tokens
        mrow['estimatedCostIndex'] += estimated_cost
        if session.get('totalTokensFresh') is True:
            mrow['freshSessions'] += 1

        iprow = incident_provider_rows[provider]
        iprow['provider'] = provider
        iprow['sessions'] += 1
        iprow['models'].add(model)
        if ratio is not None and ratio >= 0.8:
            iprow['highContext'] += 1
        if session.get('abortedLastRun') is True:
            iprow['aborted'] += 1
        if session.get('totalTokens') is None or session.get('totalTokensFresh') is False:
            iprow['visibilityGaps'] += 1

        if ratio is not None and ratio >= 1.0:
            events.append(_make_event('critical', 'context_overflow_risk', 'Контекст переполнен или почти переполнен', f'{_short_title(session)} использовал {session.get("inputTokens")} input tokens при лимите {session.get("contextTokens")}.', session, {'ratio': ratio}))
        elif ratio is not None and ratio >= 0.8:
            events.append(_make_event('warning', 'context_saturation', 'Высокая загрузка контекста', f'{_short_title(session)} уже занял {int(ratio * 100)}% окна контекста.', session, {'ratio': ratio}))
        if session.get('abortedLastRun') is True:
            events.append(_make_event('warning', 'generation_aborted', 'Есть aborted run', f'Последний прогон {_short_title(session)} завершился с abortedLastRun=true.', session))
        if session.get('totalTokens') is None or session.get('totalTokensFresh') is False:
            events.append(_make_event('info', 'visibility_gap', 'Неполная token visibility', f'По {_short_title(session)} нет свежей totalTokens-метрики.', session))

    for base, related in grouped.items():
        variants: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        for item in related:
            variants[(str(item.get('modelProvider') or 'unknown'), str(item.get('model') or 'unknown'))].append(item)
        if len(variants) >= 2:
            ordered = sorted(variants.items(), key=lambda pair: min((_session_age_seconds(s) or 10**9) for s in pair[1]))
            newest = min(related, key=lambda s: _session_age_seconds(s) or 10**9)
            chain = ' → '.join(f'{provider}/{model}' for (provider, model), _ in ordered)
            events.append(_make_event('info', 'fallback_chain', 'Замечена смена модели/провайдера', f'{_short_title(newest)} проходил через несколько model/provider variants: {chain}.', newest, {
                'variants': [{'provider': provider, 'model': model, 'count': len(items)} for (provider, model), items in ordered]
            }))

    events.sort(key=lambda item: (-_SEVERITY_RANK.get(str(item.get('level')), 0), item.get('ageSeconds') if item.get('ageSeconds') is not None else 10**9))
    incident_map = defaultdict(list)
    for event in events:
        if event.get('sessionKey'):
            incident_map[event['sessionKey']].append(event)

    expensive_sessions = []
    hot_sessions = []
    provider_health_rows = defaultdict(lambda: {'critical': 0, 'warning': 0, 'info': 0})
    for event in events:
        provider_health_rows[str(event.get('provider') or 'unknown')][str(event.get('level') or 'info')] += 1

    for session in sessions:
        provider = str(session.get('modelProvider') or 'unknown')
        model = str(session.get('model') or 'unknown')
        total_tokens = _session_total_tokens(session)
        estimated_cost = _estimated_cost(provider, total_tokens)
        age = _session_age_seconds(session)
        session_incidents = incident_map.get(session.get('key'), [])
        critical = len([e for e in session_incidents if e.get('level') == 'critical'])
        warning = len([e for e in session_incidents if e.get('level') == 'warning'])
        info = len([e for e in session_incidents if e.get('level') == 'info'])
        expensive_sessions.append({
            'sessionKey': session.get('key'), 'agentId': session.get('agentId'), 'kind': session.get('kind'), 'provider': provider, 'model': model,
            'totalTokens': total_tokens, 'estimatedCostIndex': estimated_cost, 'fresh': bool(session.get('totalTokensFresh')), 'incidentCount': len(session_incidents),
            'topIncidentKind': session_incidents[0].get('kind') if session_incidents else None, 'ageSeconds': age,
        })
        hotness = min(total_tokens / 5000.0, 40) + critical * 25 + warning * 10 + info * 2
        if age is not None:
            hotness += 25 if age < 3600 else 15 if age < 21600 else 5 if age < 86400 else 0
        if session.get('totalTokensFresh') is True:
            hotness += 5
        hot_sessions.append({
            'sessionKey': session.get('key'), 'agentId': session.get('agentId'), 'kind': session.get('kind'), 'provider': provider, 'model': model,
            'totalTokens': total_tokens, 'estimatedCostIndex': estimated_cost, 'fresh': bool(session.get('totalTokensFresh')), 'incidentCount': len(session_incidents),
            'critical': critical, 'warning': warning, 'info': info, 'ageSeconds': age, 'hotScore': round(hotness, 1),
            'topIncidentKind': session_incidents[0].get('kind') if session_incidents else None,
        })

    expensive_sessions.sort(key=lambda item: (-item['estimatedCostIndex'], -item['totalTokens']))
    hot_sessions.sort(key=lambda item: (-item['hotScore'], -item['incidentCount'], -item['totalTokens']))

    provider_health = []
    for provider, row in llm_provider_rows.items():
        irow = provider_health_rows[provider]
        visibility_gaps = incident_provider_rows[provider]['visibilityGaps']
        score = 100 - irow['critical'] * 25 - irow['warning'] * 10 - irow['info'] * 2 - visibility_gaps * 2
        if row['freshSessions'] == 0 and row['sessions'] > 0:
            score -= 10
        score = max(0, min(100, score))
        provider_health.append({
            'provider': provider, 'score': score, 'health': _health_label(score), 'sessions': row['sessions'], 'tokens': row['tokens'],
            'freshSessions': row['freshSessions'], 'critical': irow['critical'], 'warning': irow['warning'], 'info': irow['info'], 'visibilityGaps': visibility_gaps,
        })
    provider_health.sort(key=lambda item: (-item['score'], item['provider']))

    incident_by_level = {
        'critical': len([e for e in events if e.get('level') == 'critical']),
        'warning': len([e for e in events if e.get('level') == 'warning']),
        'info': len([e for e in events if e.get('level') == 'info']),
    }
    by_kind = defaultdict(int)
    timeline_buckets = {bucket: {'critical': 0, 'warning': 0, 'info': 0} for bucket, _ in _TIMELINE_BUCKETS}
    for event in events:
        by_kind[str(event.get('kind') or 'unknown')] += 1
        age = event.get('ageSeconds')
        bucket_name = 'gte24h'
        if isinstance(age, int):
            for bucket, limit in _TIMELINE_BUCKETS:
                if limit is None or age < limit:
                    bucket_name = bucket
                    break
        timeline_buckets[bucket_name][str(event.get('level') or 'info')] += 1

    snapshot = {
        'sessions': sessions,
        'incidentEvents': events[:100],
        'incidentSummary': {
            'status': 'attention' if (incident_by_level['critical'] or incident_by_level['warning']) else 'ok',
            'sessionsTracked': len(sessions), 'events': len(events),
            'critical': incident_by_level['critical'], 'warning': incident_by_level['warning'], 'info': incident_by_level['info'],
            'topIssue': events[0] if events else None,
            'byKind': dict(sorted(by_kind.items(), key=lambda kv: kv[1], reverse=True)),
            'providers': [
                {'provider': value['provider'], 'sessions': value['sessions'], 'models': sorted(value['models']), 'modelCount': len(value['models']), 'highContext': value['highContext'], 'aborted': value['aborted'], 'visibilityGaps': value['visibilityGaps']}
                for value in sorted(incident_provider_rows.values(), key=lambda row: (-row['sessions'], row['provider'] or ''))
            ],
        },
        'incidentTimeline': {
            'buckets': [{'id': bucket, 'critical': counts['critical'], 'warning': counts['warning'], 'info': counts['info'], 'total': counts['critical'] + counts['warning'] + counts['info']} for bucket, counts in timeline_buckets.items()],
            'topKinds': [{'kind': kind, 'count': count} for kind, count in sorted(by_kind.items(), key=lambda kv: kv[1], reverse=True)[:8]],
        },
        'llmSummary': {
            'sessionsTracked': len(sessions), 'tokensTotal': tokens_total, 'estimatedCostIndex': round(estimated_cost_total, 3), 'freshSessions': fresh_sessions,
            'providerCount': len(provider_counts), 'modelCount': len(model_counts), 'incidentLinkedSessions': len({e.get('sessionKey') for e in events if e.get('sessionKey')}),
            'topExpensiveSession': expensive_sessions[0] if expensive_sessions else None,
            'topHotSession': hot_sessions[0] if hot_sessions else None,
            'lowestProviderHealth': provider_health[-1] if provider_health else None,
        },
        'llmProviders': {'count': len(llm_provider_rows), 'items': [
            {'provider': row['provider'], 'sessions': row['sessions'], 'tokens': row['tokens'], 'estimatedCostIndex': round(row['estimatedCostIndex'], 3), 'models': sorted(row['models']), 'modelCount': len(row['models']), 'freshSessions': row['freshSessions']}
            for row in sorted(llm_provider_rows.values(), key=lambda item: (-item['tokens'], item['provider']))
        ]},
        'llmModels': {'count': len(llm_model_rows), 'items': [
            {'model': row['model'], 'provider': row['provider'], 'sessions': row['sessions'], 'tokens': row['tokens'], 'estimatedCostIndex': round(row['estimatedCostIndex'], 3), 'freshSessions': row['freshSessions']}
            for row in sorted(llm_model_rows.values(), key=lambda item: (-item['tokens'], item['model']))
        ]},
        'expensiveSessions': {'count': len(sessions), 'items': expensive_sessions[:20]},
        'providerHealth': {'count': len(provider_health), 'items': provider_health},
        'hotSessions': {'count': len(sessions), 'items': hot_sessions[:20]},
        'builtAt': now,
    }
    _CACHE['value'] = snapshot
    _CACHE['expiresAt'] = now + SNAPSHOT_TTL_SECONDS
    return snapshot
