# Discovery Module - The Ultron Killer
# With 5 Upgrades: Temporal Survival, Orthogonal Attacks, Failure Patterns, 
# Survivor Amplification, Discovery Rate Governance

from backend.discovery.assumption_graph import (
    AssumptionGraph,
    AssumptionNode,
    Verdict,
    DiscrepancyType,
    DiscrepancyReport,
    get_assumption_graph,
    reset_assumption_graph
)

from backend.discovery.reality_constraints import (
    check_reality_constraints,
    validate_necessity,
    DerivationGate,
    ConstraintType,
    REALITY_CONSTRAINTS
)
from backend.discovery.discovery_orchestrator import (
    DiscoverySession,
    get_discovery_session,
    reset_discovery_session,
    DISCOVERY_HARD_CAPS,
    # UPGRADE 1: Temporal Survival
    SurvivorTier,
    # UPGRADE 2: Orthogonal Attacks
    AttackAxis
)
from backend.discovery.failure_patterns import (
    # UPGRADE 3: Failure Pattern Memory
    FailurePatternIndex,
    FailureCategory,
    FailureRecord,
    get_failure_index,
    reset_failure_index
)

__all__ = [
    # Assumption Graph
    "AssumptionGraph",
    "AssumptionNode",
    "Verdict",
    "DiscrepancyType",
    "DiscrepancyReport",
    "get_assumption_graph",

    "reset_assumption_graph",
    # Reality Constraints
    "check_reality_constraints",
    "validate_necessity",
    "DerivationGate",
    "ConstraintType",
    "REALITY_CONSTRAINTS",
    # Discovery Session
    "DiscoverySession",
    "get_discovery_session",
    "reset_discovery_session",
    "DISCOVERY_HARD_CAPS",
    # UPGRADE 1: Temporal Survival
    "SurvivorTier",
    # UPGRADE 2: Orthogonal Attacks
    "AttackAxis",
    # UPGRADE 3: Failure Patterns
    "FailurePatternIndex",
    "FailureCategory",
    "FailureRecord",
    "get_failure_index",
    "reset_failure_index"
]

