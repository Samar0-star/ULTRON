# ULTRON Reality & Falsification Discovery Core
from .reality_constraints import check_reality_constraints, RealityConstraints, ConstraintType
from .discovery_orchestrator import DiscoverySession, get_discovery_session
from .constants import ScientificDefaults
from .assumption_graph import AssumptionGraph, AssumptionNode, Verdict
from .failure_patterns import FailurePatternIndex

__all__ = [
    'check_reality_constraints', 'RealityConstraints', 'ConstraintType',
    'DiscoverySession', 'get_discovery_session',
    'ScientificDefaults', 'AssumptionGraph', 'AssumptionNode',
    'Verdict', 'FailurePatternIndex'
]
