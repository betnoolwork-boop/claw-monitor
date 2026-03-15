from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parents[5]
REGISTRY_PATH = BASE_DIR / 'config' / 'agent-registry.json'


def load_registry() -> Dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))


def get_registry_summary() -> Dict[str, Any]:
    registry = load_registry()
    tiers = registry.get('tiers', {})
    counts = {
        'orchestrator': len(tiers.get('orchestrator', [])),
        'specialists': len(tiers.get('specialists', [])),
        'executionBackends': len(tiers.get('execution_backends', [])),
        'experimental': len(tiers.get('experimental', [])),
    }
    return {
        'root': registry.get('root'),
        'counts': counts,
        'canonicalCore': counts['orchestrator'] + counts['specialists'] + counts['executionBackends'],
        'updatedAt': registry.get('updatedAt'),
    }


def get_registry_agents() -> List[Dict[str, Any]]:
    registry = load_registry()
    agents = []
    for agent_id, data in registry.get('agents', {}).items():
        row = {'id': agent_id}
        row.update(data)
        agents.append(row)
    agents.sort(key=lambda x: (x.get('tier', ''), x.get('priority', 'P9'), x.get('id', '')))
    return agents


def get_registry_topology() -> Dict[str, Any]:
    registry = load_registry()
    nodes = []
    for agent_id, data in registry.get('agents', {}).items():
        nodes.append({
            'id': agent_id,
            'label': data.get('name', agent_id),
            'tier': data.get('tier'),
            'priority': data.get('priority'),
            'status': data.get('status'),
            'role': data.get('role'),
        })
    return {
        'root': registry.get('root'),
        'nodes': nodes,
        'edges': registry.get('links', []),
    }


def get_registry_core() -> Dict[str, Any]:
    registry = load_registry()
    tiers = registry.get('tiers', {})
    return {
        'orchestrator': tiers.get('orchestrator', []),
        'specialists': tiers.get('specialists', []),
        'executionBackends': tiers.get('execution_backends', []),
    }


def get_registry_experimental() -> List[Dict[str, Any]]:
    registry = load_registry()
    agents = registry.get('agents', {})
    experimental_ids = registry.get('tiers', {}).get('experimental', [])
    return [
        {
            'id': agent_id,
            **agents.get(agent_id, {}),
        }
        for agent_id in experimental_ids
    ]
