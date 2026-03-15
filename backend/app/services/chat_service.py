from __future__ import annotations

from typing import Any, Dict, List

from app.services.growth_service import get_growth_proposals, get_growth_summary
from app.services.incidents_service import get_incident_events, get_incident_summary
from app.services.llm_service import get_expensive_sessions, get_hot_sessions, get_llm_by_provider, get_llm_summary, get_provider_health
from app.services.registry_service import get_registry_agents, get_registry_summary, get_registry_topology
from app.services.runtime_service import get_runtime_agent_statuses, get_runtime_summary
from app.services.system_service import get_system_status
from app.services.task_service import get_live_task_queue


def _busy_agents(agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [a for a in agents if a.get('status') in {'canonical', 'draft', 'experimental', 'transitional'}][:5]


def _find_agent(agents: List[Dict[str, Any]], text: str) -> Dict[str, Any] | None:
    lowered = text.lower()
    for agent in agents:
        agent_id = str(agent.get('id', '')).lower()
        agent_name = str(agent.get('name', '')).lower()
        if agent_id and agent_id in lowered:
            return agent
        if agent_name and agent_name in lowered:
            return agent
    return None


def handle_chat(message: str) -> Dict[str, Any]:
    text = (message or '').strip().lower()
    agents = get_registry_agents()
    runtime_agents = get_runtime_agent_statuses()
    registry = get_registry_summary()
    runtime = get_runtime_summary()
    growth = get_growth_summary()
    system = get_system_status()
    queue = get_live_task_queue()
    incidents = get_incident_summary()
    llm = get_llm_summary()

    if not text:
        return {
            'reply': 'Напиши запрос. Например: кто сейчас занят, покажи очередь, статус системы, рост Люси.',
            'cards': [],
            'actions': [],
        }

    if 'кто занят' in text or 'agents' in text or 'агенты' in text:
        selected = [a for a in runtime_agents if a.get('runtimeState') in {'active', 'warm'}][:6]
        if not selected:
            selected = runtime_agents[:6]
        return {
            'reply': f'По runtime сейчас: active={runtime.get("active")}, warm={runtime.get("warm")}, idle={runtime.get("idle")}, unknown={runtime.get("unknown")}.',
            'cards': [
                {
                    'title': a.get('name', a.get('id')),
                    'meta': f'{a.get("tier", "unknown")} · runtime={a.get("runtimeState", "—")} · seen={a.get("lastSeenSecondsAgo", "n/a")}s'
                }
                for a in selected
            ],
            'actions': [{'type': 'open_agents', 'label': 'Открыть Agents'}],
        }

    if 'очеред' in text or 'queue' in text or 'задач' in text:
        items = queue.get('items', [])[:5]
        return {
            'reply': f'Сейчас в живой очереди/потоке видно {queue.get("count", 0)} задач.',
            'cards': [
                {
                    'title': item.get('title'),
                    'meta': f'{item.get("status")} · {item.get("priority")} · {item.get("assignedAgent")} · {item.get("source")}'
                }
                for item in items
            ],
            'actions': [{'type': 'open_tasks', 'label': 'Открыть Queue'}],
        }

    if 'статус системы' in text or 'system' in text or 'нагруз' in text:
        return {
            'reply': f'Система в статусе {system.get("status")}. Host: {system.get("hostname")}, load: {system.get("loadavg1")}.',
            'cards': [
                {'title': 'Hostname', 'meta': system.get('hostname')},
                {'title': 'Load avg', 'meta': str(system.get('loadavg1'))},
                {'title': 'Disk', 'meta': f'{system["disk"]["usedGb"]}/{system["disk"]["totalGb"]} GB'},
            ],
            'actions': [{'type': 'open_system', 'label': 'Открыть System'}],
        }

    if 'рост' in text or 'growth' in text or 'улучш' in text:
        best = growth.get('bestNextMove') or {}
        proposals = get_growth_proposals()[:3]
        return {
            'reply': f'Сигнал роста сейчас: {growth.get("signal")}. Открытых предложений: {growth.get("openProposals")}.',
            'cards': [
                {
                    'title': best.get('title', 'Нет следующего шага'),
                    'meta': f'{best.get("type", "—")} · {best.get("complexity", "—")}'
                },
                *[
                    {'title': item.get('title'), 'meta': f'{item.get("status")} · {item.get("type")}'}
                    for item in proposals
                ]
            ],
            'actions': [{'type': 'open_growth', 'label': 'Открыть Growth'}],
        }

    if 'llm' in text or 'расход' in text or 'spend' in text or 'tokens' in text or 'токен' in text or 'стоим' in text:
        expensive = get_expensive_sessions().get('items', [])[:5]
        providers = get_llm_by_provider().get('items', [])[:3]
        health = get_provider_health().get('items', [])
        hot = get_hot_sessions().get('items', [])[:2]
        worst = health[-1] if health else {}
        return {
            'reply': f'LLM layer: sessions={llm.get("sessionsTracked")}, tokens={llm.get("tokensTotal")}, estimated cost index={llm.get("estimatedCostIndex")}. Самый слабый provider health: {worst.get("provider", "—")}={worst.get("score", "—")}.',
            'cards': [
                *[
                    {
                        'title': item.get('provider'),
                        'meta': f'sessions={item.get("sessions")} · tokens={item.get("tokens")} · cost~{item.get("estimatedCostIndex")}'
                    }
                    for item in providers
                ],
                *[
                    {
                        'title': f'hot {item.get("sessionKey")}',
                        'meta': f'score={item.get("hotScore")} · incidents={item.get("incidentCount")} · {item.get("provider")}'
                    }
                    for item in hot
                ]
            ],
            'actions': [{'type': 'open_llm', 'label': 'Открыть LLM'}],
        }

    if 'инцид' in text or 'fallback' in text or 'лимит' in text or 'overflow' in text or 'provider' in text or 'модел' in text:
        items = get_incident_events()[:5]
        top_issue = incidents.get('topIssue') or {}
        return {
            'reply': f'По model/provider layer сейчас: critical={incidents.get("critical")}, warning={incidents.get("warning")}, info={incidents.get("info")}. Топ issue: {top_issue.get("kind", "—")}.',
            'cards': [
                {
                    'title': item.get('title'),
                    'meta': ' · '.join(filter(None, [item.get('level'), item.get('provider'), item.get('model'), item.get('sessionKey')]))
                }
                for item in items
            ],
            'actions': [{'type': 'open_incidents', 'label': 'Открыть Incidents'}],
        }

    if 'тополог' in text or 'схем' in text or 'связ' in text:
        topology = get_registry_topology()
        return {
            'reply': f'В канонической топологии {len(topology.get("nodes", []))} узлов и {len(topology.get("edges", []))} связей.',
            'cards': [
                {'title': edge.get('from'), 'meta': f'{edge.get("type")} → {edge.get("to")}'}
                for edge in topology.get('edges', [])[:6]
            ],
            'actions': [{'type': 'open_topology', 'label': 'Открыть Topology'}],
        }

    if 'лучший следующий шаг' in text or 'best next move' in text or 'что дальше' in text:
        best = growth.get('bestNextMove') or {}
        return {
            'reply': f'Лучший следующий шаг сейчас: {best.get("title", "не определён")}.' ,
            'cards': [
                {'title': best.get('title', '—'), 'meta': f'{best.get("type", "—")} · {best.get("complexity", "—")}'}
            ],
            'actions': [{'type': 'open_growth', 'label': 'Открыть Growth'}],
        }

    if 'агент ' in text or 'про агента' in text or 'agent ' in text:
        agent = _find_agent(agents, text)
        if agent:
            return {
                'reply': f'Нашла агента {agent.get("name", agent.get("id"))}.',
                'cards': [
                    {
                        'title': agent.get('name', agent.get('id')),
                        'meta': ' · '.join(filter(None, [agent.get('tier'), agent.get('priority'), agent.get('status')]))
                    },
                    {'title': 'Role', 'meta': agent.get('role', 'n/a')},
                    {'title': 'Backing', 'meta': agent.get('backingModule', '—')},
                ],
                'actions': [{'type': 'open_agents', 'label': 'Открыть Agents'}],
            }

    return {
        'reply': 'Пока понимаю такие запросы: статус системы, кто занят, покажи очередь, рост Люси, LLM расход/токены, инциденты моделей/провайдеров, топология, лучший следующий шаг, агент <имя>.',
        'cards': [],
        'actions': [
            {'type': 'hint', 'label': 'кто занят'},
            {'type': 'hint', 'label': 'покажи очередь'},
            {'type': 'hint', 'label': 'статус системы'},
            {'type': 'hint', 'label': 'рост Люси'},
            {'type': 'hint', 'label': 'LLM расход'},
            {'type': 'hint', 'label': 'инциденты моделей'},
            {'type': 'hint', 'label': 'топология'},
            {'type': 'hint', 'label': 'лучший следующий шаг'},
            {'type': 'hint', 'label': 'агент main'},
        ],
    }
