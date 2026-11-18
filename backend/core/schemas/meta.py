# backend/core/schemas/meta.py
"""
Pydantic schemas for meta-reasoning, discovery scoring, and epistemic governance.
Provides structured contracts replacing heuristic word-overlap and keyword counters.
Enforces calibrated confidence thresholds to prevent agent hallucination amplification.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CognitiveModeDecision(BaseModel):
    """MetaReasoningLayer dynamic search strategy steering."""
    mode: Literal[
        "EXPLORATION_FRENZY", "SNIPER_FOCUS", "LATERAL_JUMP",
        "CRITIC_DEBATE", "RESOURCE_CONSERVATION", "PANIC_RESET"
    ] = Field(description="Selected swarm cognitive operating mode")
    branching_factor: int = Field(
        default=3, ge=1, le=10,
        description="Number of parallel hypothesis variants or subtasks to spawn"
    )
    exploration_rate: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Exploration vs exploitation budget allocation (epsilon parameter)"
    )
    confidence: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description="Confidence in strategic adjustment (< 0.8 defaults to retaining current mode)"
    )
    reasoning: str = Field(description="Strategic justification based on findings trajectory")
    search_depth_limit: Optional[int] = Field(
        default=5, ge=1, le=20,
        description="Max recursive branch depth for task decomposition"
    )

class NoveltyAssessment(BaseModel):
    """Semantic novelty evaluation replacing crude 3-word overlap checks."""
    is_novel: bool = Field(description="Whether the claim diverges meaningfully from existing literature")
    novelty_score: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Continuous novelty score (0.0 = verbatim duplicate, 1.0 = paradigm shift)"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Confidence in novelty assessment (< 0.8 defaults to conservative re-evaluation)"
    )
    closest_prior_work: Optional[str] = Field(
        default=None,
        description="Closest known publication or prior art claim"
    )
    divergence_description: str = Field(
        description="Mechanistic explanation of how this hypothesis differs from prior art"
    )

class TestabilityAssessment(BaseModel):
    """Popperian testability evaluation replacing regex adverb counters."""
    __test__ = False
    is_testable: bool = Field(description="Whether the hypothesis makes empirical falsifiable predictions")
    testability_score: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Degree of empirical operationalizability (0.0 = unfalsifiable, 1.0 = exact measurement)"
    )
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence in assessment")
    falsification_criteria: Optional[str] = Field(
        default=None,
        description="Explicit quantitative condition that would conclusively disprove the claim"
    )
    required_data: List[str] = Field(
        default_factory=list,
        description="Observable physical or computational variables needed for testing"
    )

class StructuralImpactAssessment(BaseModel):
    """Graph centrality and domain impact assessment replacing keyword counters."""
    impact_score: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Estimated transformative impact on target scientific domain"
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Certainty score")
    central_mechanisms: List[str] = Field(
        default_factory=list,
        description="Core physical or causal pathways affected by this discovery"
    )
    reasoning: str = Field(description="Explanation of why this finding shifts domain assumptions")
