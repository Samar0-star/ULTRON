"""
Hypothesis Models for Avon-2 Deep Mode
========================================

Core data structures for hypothesis tracking.
Provides state management for hypotheses throughout the research lifecycle.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class HypothesisState(Enum):
    """Lifecycle states for a hypothesis"""
    PROPOSED = "proposed"       # Just generated
    NOVEL = "novel"             # Confirmed as novel (passed novelty check)
    NOVEL_CHECK = "novel_check" # Being checked for novelty
    PRIORITIZED = "prioritized" # Ranked and ready for testing
    TESTING = "testing"         # Experiment in progress
    CONFIRMED = "confirmed"     # Evidence supports hypothesis
    REFUTED = "refuted"         # Evidence contradicts hypothesis
    REFINED = "refined"         # Modified based on results
    ARCHIVED = "archived"       # No longer active


# Valid state transitions to prevent illegal lifecycle jumps
VALID_TRANSITIONS = {
    HypothesisState.PROPOSED: [HypothesisState.NOVEL_CHECK, HypothesisState.NOVEL, HypothesisState.PRIORITIZED, HypothesisState.TESTING, HypothesisState.REFUTED, HypothesisState.ARCHIVED],
    HypothesisState.NOVEL_CHECK: [HypothesisState.NOVEL, HypothesisState.PRIORITIZED, HypothesisState.REFUTED, HypothesisState.ARCHIVED],
    HypothesisState.NOVEL: [HypothesisState.PRIORITIZED, HypothesisState.TESTING, HypothesisState.REFUTED, HypothesisState.ARCHIVED],
    HypothesisState.PRIORITIZED: [HypothesisState.TESTING, HypothesisState.REFUTED, HypothesisState.ARCHIVED],
    HypothesisState.TESTING: [HypothesisState.CONFIRMED, HypothesisState.REFUTED, HypothesisState.REFINED, HypothesisState.ARCHIVED],
    HypothesisState.CONFIRMED: [HypothesisState.ARCHIVED],
    HypothesisState.REFUTED: [HypothesisState.ARCHIVED, HypothesisState.REFINED],
    HypothesisState.REFINED: [HypothesisState.NOVEL_CHECK, HypothesisState.NOVEL, HypothesisState.PRIORITIZED, HypothesisState.TESTING, HypothesisState.REFUTED, HypothesisState.ARCHIVED],
    HypothesisState.ARCHIVED: [],  # Terminal state - no transitions out
}


@dataclass
class Evidence:
    """
    Formal evidence supporting or refuting a hypothesis.
    Strictly typed to prevent 'Cosplay Science'.
    Supports dictionary access for legacy compatibility.
    """
    value: Any        # The core finding/data
    type: str         # 'experiment', 'citation', 'logic', 'simulation'
    source: str       # Agent or Tool ID
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 1.0  # Trust score of this evidence (0.0-1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        val = data["value"] if "value" in data and data["value"] is not None else data.get("content")
        return cls(
            value=val, # Handle generic content while preserving 0.0 / False
            type=data.get("type", "unknown"),
            source=data.get("source", "unknown"),
            timestamp=data.get("timestamp") or datetime.now().isoformat(),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {})
        )

    def __getitem__(self, key):
        """Legacy support for accessing evidence as a dictionary."""
        return getattr(self, key)
    
    def get(self, key, default=None):
        """Legacy support for .get()"""
        return getattr(self, key, default)


@dataclass
class Hypothesis:
    """
    A scientific hypothesis in the research pipeline.
    
    Attributes:
        id: Unique identifier
        statement: The hypothesis claim
        rationale: Why this hypothesis was proposed
        domain: Research domain (ml, nlp, physics, biology, etc.)
        state: Current lifecycle state
        confidence: System's confidence in this hypothesis (0.0-1.0)
        novelty_score: How novel this hypothesis is (0.0-1.0)
        testability_score: How testable this is (0.0-1.0)
        impact_score: Predicted impact if confirmed (0.0-1.0)
        priority_score: Combined ranking score (0.0-1.0)
    """
    statement: str
    rationale: str
    domain: str = "scientific_discovery"
    
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    research_question: str = ""
    
    # Lifecycle
    state: HypothesisState = HypothesisState.PROPOSED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Scores (0.01.0)
    confidence: float = 0.5
    uncertainty: float = 0.0 # [TITAN V157.0] GNN Epistemic Doubt (σ)
    novelty_score: Optional[float] = None

    testability_score: Optional[float] = None
    impact_score: Optional[float] = None
    feasibility_score: Optional[float] = None
    priority_score: Optional[float] = None
    survival_score: Optional[float] = None  # NEW: For Adversarial Leaderboard
    
    # Metadata
    source_agent: str = "unknown"
    parent_hypothesis_id: Optional[str] = None  # For refined hypotheses
    experiment_ids: List[str] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # =========================================================================
    # FORMAL SCIENTIFIC FIELDS (NEW - Wiring Fix)
    # These enable real scientific reasoning, not just prose
    # =========================================================================
    variables: List[Dict[str, Any]] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    functional_form: str = ""

    
    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================
    
    @property
    def is_active(self) -> bool:
        """Check if hypothesis is active (not archived/refuted)."""
        return self.state not in [HypothesisState.ARCHIVED, HypothesisState.REFUTED]
    
    @property
    def has_evidence(self) -> bool:
        """Check if any evidence exists."""
        return len(self.evidence) > 0
    
    @property
    def age_hours(self) -> float:
        """Hours since creation."""
        return (datetime.now() - self.created_at).total_seconds() / 3600
    
    @property
    def is_formally_complete(self) -> bool:
        """Check if hypothesis has formal scientific structure (not just prose)."""
        return bool(self.variables) and bool(self.predictions)
    
    @property
    def is_tested(self) -> bool:
        """Check if any prediction has been tested (measured value exists)."""
        if not self.predictions:
            return False
        return any(isinstance(p, dict) and p.get("measured") is not None for p in self.predictions)
    
    @property
    def test_verdict(self) -> str:
        """Get overall test verdict from predictions."""
        if not self.is_tested:
            return "UNTESTED"
        
        verdicts = [p.get("verdict") for p in self.predictions if isinstance(p, dict) and p.get("verdict")]
        if "REFUTED" in verdicts:
            return "REFUTED"
        elif all(v == "CONFIRMED" for v in verdicts) and verdicts:
            return "CONFIRMED"
        elif "CONFIRMED" in verdicts:
            return "PARTIALLY_CONFIRMED"
        return "INCONCLUSIVE"

    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "statement": self.statement,
            "rationale": self.rationale,
            "domain": self.domain,
            "research_question": self.research_question,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "confidence": self.confidence,
            "uncertainty": self.uncertainty, # [TITAN V157.0] Doubt Persistence
            "novelty_score": self.novelty_score,

            "testability_score": self.testability_score,
            "impact_score": self.impact_score,
            "feasibility_score": self.feasibility_score,
            "priority_score": self.priority_score,
            "survival_score": self.survival_score,
            "source_agent": self.source_agent,
            "parent_hypothesis_id": self.parent_hypothesis_id,
            "experiment_ids": self.experiment_ids,
            "evidence": [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.evidence],
            "tags": self.tags,
            "metadata": self.metadata,
            # FORMAL SCIENTIFIC FIELDS (NEW)
            "variables": self.variables,
            "parameters": self.parameters,
            "constraints": self.constraints,
            "predictions": self.predictions,
            "functional_form": self.functional_form,
            # Computed properties
            "is_active": self.is_active,
            "has_evidence": self.has_evidence,
            "age_hours": round(self.age_hours, 2),
            "is_formally_complete": self.is_formally_complete,
            "is_tested": self.is_tested,
            "test_verdict": self.test_verdict
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Hypothesis":
        """Deserialize from dictionary"""
        state_str = data.get("state", "proposed")
        state = HypothesisState(state_str) if isinstance(state_str, str) else state_str
        
        # PROPERLY DESERIALIZE EVIDENCE
        raw_evidence = data.get("evidence", [])
        evidence_objs = []
        for e in raw_evidence:
            if isinstance(e, dict):
                evidence_objs.append(Evidence.from_dict(e))
            else:
                 # Fallback if somehow already an object (shouldn't happen in JSON)
                 evidence_objs.append(e)

        
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            statement=data["statement"],
            rationale=data.get("rationale", ""),
            domain=data.get("domain", "general"),
            research_question=data.get("research_question", ""),
            state=state,
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            confidence=data.get("confidence", 0.5),
            uncertainty=data.get("uncertainty", 0.0), # [TITAN V157.0] Doubt Rehydration
            novelty_score=data.get("novelty_score"),

            testability_score=data.get("testability_score"),
            impact_score=data.get("impact_score"),
            feasibility_score=data.get("feasibility_score"),
            priority_score=data.get("priority_score"),
            survival_score=data.get("survival_score"),
            source_agent=data.get("source_agent", "unknown"),
            parent_hypothesis_id=data.get("parent_hypothesis_id"),
            experiment_ids=data.get("experiment_ids", []),
            evidence=evidence_objs,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            # FORMAL SCIENTIFIC FIELDS (NEW)
            variables=data.get("variables", []),
            parameters=data.get("parameters", []),
            constraints=data.get("constraints", []),
            predictions=data.get("predictions", []),
            functional_form=data.get("functional_form", "")
        )
    
    def update_state(self, new_state: HypothesisState, force: bool = False) -> None:
        """
        Update state with timestamp and transition validation.
        
        Args:
            new_state: Target state
            force: If True, bypass transition validation (use sparingly)
            
        Raises:
            ValueError: If transition is invalid and force=False
        """
        if not force:
            valid_next_states = VALID_TRANSITIONS.get(self.state, [])
            if new_state not in valid_next_states:
                raise ValueError(
                    f"Invalid state transition: {self.state.value}  {new_state.value}. "
                    f"Valid transitions: {[s.value for s in valid_next_states]}"
                )
        
        self.state = new_state
        self.updated_at = datetime.now()
    
    def add_evidence(
        self, 
        evidence_type: str, 
        value: Any, 
        source: str,
        confidence: float = 1.0,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Add evidence for/against this hypothesis.
        Uses Strict Evidence Schema.
        """
        ev = Evidence(
            type=evidence_type,
            value=value,
            source=source,
            timestamp=datetime.now().isoformat(),
            confidence=confidence,
            metadata=metadata or {}
        )
        self.evidence.append(ev)
        self.updated_at = datetime.now()



@dataclass
class NoveltyReport:
    """
    Report from novelty analysis.
    
    Contains detailed novelty assessment including similar work found.
    """
    hypothesis_id: str
    novelty_score: float  # 0.0 = duplicate, 1.0 = completely novel
    is_novel: bool
    prior_art_detected: bool
    max_similarity: float
    
    # Similar work found
    similar_papers: List[Dict[str, Any]] = field(default_factory=list)
    similar_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    
    # Analysis metadata
    novelty_threshold_used: float = 0.75
    summary: str = ""
    checked_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "hypothesis_id": self.hypothesis_id,
            "novelty_score": self.novelty_score,
            "is_novel": self.is_novel,
            "prior_art_detected": self.prior_art_detected,
            "max_similarity": self.max_similarity,
            "similar_papers": self.similar_papers,
            "similar_hypotheses": self.similar_hypotheses,
            "novelty_threshold_used": self.novelty_threshold_used,
            "summary": self.summary,
            "checked_at": self.checked_at.isoformat()
        }


@dataclass
class TestabilityReport:
    """
    Report from testability analysis.
    
    Assesses whether a hypothesis can be experimentally tested.
    """
    hypothesis_id: str
    testability_score: float  # 0.0 = untestable, 1.0 = easily testable
    is_testable: bool
    
    # Analysis breakdown
    data_availability: float  # 0.0-1.0
    methodology_clarity: float  # 0.0-1.0
    resource_requirements: float  # 0.0-1.0 (1.0 = low resources needed)
    time_estimate_hours: float
    
    # Suggested approach
    suggested_experiment_type: str = ""
    required_data_sources: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "hypothesis_id": self.hypothesis_id,
            "testability_score": self.testability_score,
            "is_testable": self.is_testable,
            "data_availability": self.data_availability,
            "methodology_clarity": self.methodology_clarity,
            "resource_requirements": self.resource_requirements,
            "time_estimate_hours": self.time_estimate_hours,
            "suggested_experiment_type": self.suggested_experiment_type,
            "required_data_sources": self.required_data_sources,
            "required_tools": self.required_tools,
            "summary": self.summary
        }


@dataclass
class PriorityRanking:
    """
    Priority ranking for a hypothesis.
    
    Combines multiple criteria into a single priority score.
    """
    hypothesis_id: str
    priority_score: float  # 0.0-1.0, higher = more priority
    rank: int  # 1 = highest priority
    
    # Score breakdown
    novelty_weight: float = 0.25
    feasibility_weight: float = 0.25
    impact_weight: float = 0.25
    testability_weight: float = 0.25
    
    # Individual weighted scores
    weighted_novelty: float = 0.0
    weighted_feasibility: float = 0.0
    weighted_impact: float = 0.0
    weighted_testability: float = 0.0
    
    rationale: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "hypothesis_id": self.hypothesis_id,
            "priority_score": self.priority_score,
            "rank": self.rank,
            "weights": {
                "novelty": self.novelty_weight,
                "feasibility": self.feasibility_weight,
                "impact": self.impact_weight,
                "testability": self.testability_weight
            },
            "weighted_scores": {
                "novelty": self.weighted_novelty,
                "feasibility": self.weighted_feasibility,
                "impact": self.weighted_impact,
                "testability": self.weighted_testability
            },
            "rationale": self.rationale
        }
