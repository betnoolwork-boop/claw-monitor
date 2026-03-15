# Services package - auto-import with graceful fallback
import importlib

_exports = {}

_modules = {
    '.actions_service': ['run_action'],
    '.analytics_snapshot_service': ['build_analytics_snapshot', 'prewarm_analytics_snapshot'],
    '.annotations_service': ['annotate_session', 'annotate_incident', 'clear_annotation', 'get_annotations', 'summarize_annotations'],
    '.auth_service': ['require_auth'],
    '.details_service': ['get_agent_details', 'get_session_details'],
    '.incidents_service': ['get_incident_detail', 'get_incident_summary', 'get_incident_events', 'get_incident_timeline', 'get_provider_incidents'],
    '.growth_service': ['get_growth_summary', 'get_growth_proposals'],
    '.llm_service': ['get_llm_summary', 'get_llm_providers', 'get_llm_models', 'get_llm_sessions', 'get_llm_health'],
    '.presets_service': ['get_presets', 'create_preset', 'update_preset', 'delete_preset', 'apply_preset', 'get_default_presets', 'initialize_default_presets'],
    '.registry_service': ['get_registry_summary', 'get_registry_agents', 'get_registry_topology'],
    '.runtime_service': ['get_runtime_summary', 'get_runtime_sessions'],
    '.system_service': ['get_system_info'],
    '.tasks_service': ['get_tasks_summary', 'get_task_queue'],
    '.alerts_service': ['get_alerts'],
}

for mod_name, names in _modules.items():
    try:
        mod = importlib.import_module(mod_name, package=__package__)
        for name in names:
            if hasattr(mod, name):
                _exports[name] = getattr(mod, name)
    except ImportError:
        pass

globals().update(_exports)
