# backend/core/schemas/__init__.py
from .research_plan import PlannedTask, ResearchPlanSchema
from .hypothesis import ScientificHypothesisSchema, Prediction
from .experiment import ExperimentProtocolSchema, ExperimentProtocolStep, ExperimentResultSchema, ExperimentMetrics
from .verdict import RedTeamVerdict, ConsensusVerdictSchema
from .orchestration import (
    HypothesisUpdate,
    AnalysisResult,
    StrategicAudit,
    ConsensusVerdict,
    TaskDecomposition,
    RoutingDecision,
)
from .agents import (
    FactCheckResult,
    DocumentExtraction,
    MLCodeResult,
    SummaryResult,
    AnalysisOutput,
)
from .meta import (
    CognitiveModeDecision,
    NoveltyAssessment,
    TestabilityAssessment,
    StructuralImpactAssessment,
)

__all__ = [
    # Research & Planning
    "PlannedTask",
    "ResearchPlanSchema",
    "ScientificHypothesisSchema",
    "Prediction",
    "ExperimentProtocolSchema",
    "ExperimentProtocolStep",
    "ExperimentResultSchema",
    "ExperimentMetrics",
    "RedTeamVerdict",
    "ConsensusVerdictSchema",
    # Orchestration
    "HypothesisUpdate",
    "AnalysisResult",
    "StrategicAudit",
    "ConsensusVerdict",
    "TaskDecomposition",
    "RoutingDecision",
    # Specialist Agents
    "FactCheckResult",
    "DocumentExtraction",
    "MLCodeResult",
    "SummaryResult",
    "AnalysisOutput",
    # Meta-Reasoning & Discovery
    "CognitiveModeDecision",
    "NoveltyAssessment",
    "TestabilityAssessment",
    "StructuralImpactAssessment",
]
