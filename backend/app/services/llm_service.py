from __future__ import annotations

from typing import Any, Dict

from app.services.analytics_snapshot_service import build_analytics_snapshot


def get_llm_summary() -> Dict[str, Any]:
    return build_analytics_snapshot().get('llmSummary', {})


def get_llm_by_provider() -> Dict[str, Any]:
    return build_analytics_snapshot().get('llmProviders', {'count': 0, 'items': []})


def get_llm_by_model() -> Dict[str, Any]:
    return build_analytics_snapshot().get('llmModels', {'count': 0, 'items': []})


def get_expensive_sessions() -> Dict[str, Any]:
    return build_analytics_snapshot().get('expensiveSessions', {'count': 0, 'items': []})


def get_provider_health() -> Dict[str, Any]:
    return build_analytics_snapshot().get('providerHealth', {'count': 0, 'items': []})


def get_hot_sessions() -> Dict[str, Any]:
    return build_analytics_snapshot().get('hotSessions', {'count': 0, 'items': []})
