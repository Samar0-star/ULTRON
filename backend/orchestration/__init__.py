# ULTRON Autonomous Orchestration & Swarm Governance
from .circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerError

def _try_get(name, module_name):
    try:
        import importlib
        mod = importlib.import_module(module_name, package=__package__)
        return getattr(mod, name, None)
    except Exception:
        return None

SingularityEngine = _try_get('SingularityEngine', '.singularity')
get_singularity = _try_get('get_singularity', '.singularity')
SwarmManager = _try_get('SwarmManager', '.swarm_manager')
get_swarm_manager = _try_get('get_swarm_manager', '.swarm_manager')
DeepResearchOrchestrator = _try_get('DeepResearchOrchestrator', '.deep_research_orchestrator')

__all__ = [
    'CircuitBreaker',
    'CircuitState',
    'CircuitBreakerError',
    'SingularityEngine',
    'get_singularity',
    'SwarmManager',
    'get_swarm_manager',
    'DeepResearchOrchestrator'
]
