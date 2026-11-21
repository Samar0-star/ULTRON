"""
SVEL Terminal User Interface Package
"""
from backend.ui.terminal_dashboard import (
    SVELTerminalDashboard,
    SVELDashboardState,
    AgentRecord,
    HypothesisRecord,
    ExperimentRecord,
    GNNOracleRecord,
    TribunalRecord,
    EpistemicEventRecord,
    DashboardLogHandler
)

__all__ = [
    "SVELTerminalDashboard",
    "SVELDashboardState",
    "AgentRecord",
    "HypothesisRecord",
    "ExperimentRecord",
    "GNNOracleRecord",
    "TribunalRecord",
    "EpistemicEventRecord",
    "DashboardLogHandler"
]
