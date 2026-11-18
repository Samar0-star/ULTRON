# backend/core/schemas/orchestration.py
"""
Pydantic schemas for orchestration-level structured LLM outputs.
Provides native grammar-constrained decoding models to eliminate regex JSON scraping.
Includes mandatory confidence scores for hallucination-resistant epistemic governance.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

class HypothesisUpdate(BaseModel):
    """Structured decision on an active hypothesis based on empirical evidence."""
    hypothesis_id: str = Field(description="Unique identifier of the target hypothesis")
    action: Literal["confirm", "refute", "refine", "keep"] = Field(
        description="Epistemic action to take on this hypothesis"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Calibrated model confidence in this update (threshold < 0.8 defaults to conservative retention)"
    )
    reason: str = Field(description="Detailed mechanistic or empirical justification")

class AnalysisResult(BaseModel):
    """Aggregated analysis of cycle experimental findings and hypothesis mutations."""
    hypothesis_updates: List[HypothesisUpdate] = Field(
        default_factory=list,
        description="List of proposed updates to active hypotheses"
    )
    overall_assessment: str = Field(
        default="",
        description="High-level synthesis of experimental results and cycle momentum"
    )

class StrategicAudit(BaseModel):
    """Overmind supervisor strategic assessment and trajectory directive."""
    directive: Literal["CONTINUE", "PRUNE", "PIVOT", "INTENSIFY", "TERMINATE"] = Field(
        description="High-level swarm orchestration directive"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Confidence in trajectory assessment (< 0.8 triggers CONTINUE with human alert)"
    )
    reasoning: str = Field(description="Strategic justification grounded in goal distance and epistemic yield")
    prune_targets: List[str] = Field(
        default_factory=list,
        description="Hypothesis IDs or task IDs recommended for immediate cancellation"
    )
    pivot_suggestion: Optional[str] = Field(
        default=None,
        description="Alternative conceptual angle if PIVOT is commanded"
    )

class ConsensusVerdict(BaseModel):
    """Multi-agent tribunal consensus verdict."""
    verdict: Literal["YES", "NO"] = Field(description="Binary consensus decision")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Consensus strength (< 0.8 indicates contentious debate)"
    )
    dissenting_reasons: List[str] = Field(
        default_factory=list,
        description="Documented disagreements or adversarial critiques"
    )

class TaskDecomposition(BaseModel):
    """SingularityEngine task decomposition into parallel executable units."""
    subtasks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of discrete decomposed task dictionaries matching ResearchTask spec"
    )
    rationale: str = Field(default="", description="Decomposition strategy and dependency logic")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence in plan completeness")

class RoutingDecision(BaseModel):
    """Central router component dispatch decision."""
    component: str = Field(description="Selected agent or engine destination key")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Routing confidence (< 0.8 falls back to primary scientific coordinator)"
    )
    reasoning: str = Field(description="Rationale for selected component match")
