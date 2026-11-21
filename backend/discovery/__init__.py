# SVEL Discovery & Reality Gates

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

from backend.discovery.adversarial_executor import (
    AdversarialExecutor
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
    # Adversarial Testing
    "AdversarialExecutor",
]


