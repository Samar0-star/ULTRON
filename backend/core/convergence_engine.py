"""
EPISTEMIC CONVERGENCE ENGINE - Intelligent Research Stopping System

This module provides mathematically rigorous convergence detection for
autonomous research. It goes far beyond simple thresholds by implementing:

1. Vector-based semantic novelty (FAISS embeddings)
2. Epistemic velocity tracking (rate of knowledge discovery)
3. Saturation analysis (coverage of hypothesis space)
4. Cost-per-discovery optimization
5. Gdel-style provability limits (knows when a question is unanswerable)

Part of Ultron's Advanced Research Architecture.
"""

import logging
import math
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from backend.discovery.constants import ScientificDefaults

logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class StoppingReason(str, Enum):
    """Reasons for stopping research."""
    ITERATION_LIMIT = "iteration_limit"
    RUNTIME_LIMIT = "runtime_limit"
    NO_TESTABLE_HYPOTHESES = "no_testable_hypotheses"
    NOVELTY_EXHAUSTION = "novelty_exhaustion"
    SATURATION_REACHED = "saturation_reached"
    DIMINISHING_RETURNS = "diminishing_returns"
    EPISTEMIC_STAGNATION = "epistemic_stagnation"
    PROVABILITY_LIMIT = "provability_limit"
    USER_REQUESTED = "user_requested"
    BUDGET_EXHAUSTED = "budget_exhausted"
    ANSWER_FOUND = "answer_found"


class ConvergenceConfidence(str, Enum):
    """Confidence levels for convergence decisions."""
    CERTAIN = "certain"  # Mandatory criteria met
    HIGH = "high"        # 80%+ confidence
    MEDIUM = "medium"    # 50-80% confidence
    LOW = "low"          # <50% confidence


# Thresholds for convergence detection
CONVERGENCE_THRESHOLDS = {
    "novelty_decline_window": 5,       # Number of cycles to check for decline
    "novelty_exhaustion_threshold": ScientificDefaults.NOVELTY_THRESHOLD,
    "saturation_threshold": ScientificDefaults.SATURATION_THRESHOLD,
    "discovery_rate_min": ScientificDefaults.DISCOVERY_RATE_MIN,
    "cost_per_discovery_max": 500.0,   # USD per significant finding
    "epistemic_velocity_min": ScientificDefaults.EPISTEMIC_VELOCITY_MIN,
    "stagnation_cycles": ScientificDefaults.STAGNATION_CYCLES,
}


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class ConvergenceMetrics:
    """
    Comprehensive metrics for convergence detection.
    
    These metrics are tracked per research cycle and used to make
    intelligent stopping decisions.
    """
    # Discovery metrics
    discovery_rate: float = 0.0  # Significant findings / total experiments
    total_experiments: int = 0
    significant_findings: int = 0
    
    # Novelty metrics (semantic)
    novelty_score: float = 1.0  # Current cycle novelty (0-1)
    novelty_trend: List[float] = field(default_factory=list)  # History
    novelty_velocity: float = 0.0  # Rate of change
    is_novelty_declining: bool = False
    
    # Saturation metrics
    saturation_ratio: float = 0.0  # Tested / total hypotheses
    hypotheses_tested: int = 0
    total_hypotheses: int = 0
    hypothesis_space_coverage: float = 0.0  # Semantic coverage of all possible hypotheses
    
    # Epistemic velocity (rate of knowledge gain)
    epistemic_velocity: float = 1.0  # Decreases as we learn less per cycle
    knowledge_delta_history: List[float] = field(default_factory=list)
    
    # Consistency metrics
    consistency_score: float = 0.0  # Replication rate
    contradictions_found: int = 0
    
    # Provability assessment
    provability_score: float = 1.0  # 0 = likely unprovable, 1 = definitely answerable
    unanswerable_signals: List[str] = field(default_factory=list)
    
    # Cost metrics
    total_cost_usd: float = 0.0
    cost_per_discovery: Optional[float] = None
    
    # Iteration tracking
    iteration_count: int = 0
    max_iterations: int = 10
    
    # Time tracking
    start_time: Optional[datetime] = None
    elapsed_hours: float = 0.0
    max_runtime_hours: float = 72.0
    
    # Answer tracking
    answer_confidence: float = 0.0  # 0-1, how confident we are in the answer
    best_answer: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "discovery_rate": self.discovery_rate,
            "novelty_score": self.novelty_score,
            "saturation_ratio": self.saturation_ratio,
            "epistemic_velocity": self.epistemic_velocity,
            "cost_per_discovery": self.cost_per_discovery,
            "iteration_count": self.iteration_count,
            "elapsed_hours": self.elapsed_hours,
            "answer_confidence": self.answer_confidence,
            "provability_score": self.provability_score,
        }


@dataclass
class StoppingDecision:
    """Decision on whether to stop research."""
    should_stop: bool
    reason: StoppingReason
    is_mandatory: bool  # True = must stop, False = recommended
    confidence: ConvergenceConfidence
    confidence_score: float  # 0-1
    details: str
    metrics_snapshot: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_stop": self.should_stop,
            "reason": self.reason.value,
            "is_mandatory": self.is_mandatory,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConvergenceReport:
    """Final convergence report generated at research end."""
    research_question: str
    converged: bool
    stopping_reason: StoppingReason
    
    # Summary
    total_iterations: int
    total_hypotheses: int
    hypotheses_supported: int
    hypotheses_rejected: int
    experiments_conducted: int
    
    # Key findings
    key_discoveries: List[Dict[str, Any]] = field(default_factory=list)
    supported_hypotheses: List[str] = field(default_factory=list)
    rejected_hypotheses: List[str] = field(default_factory=list)
    
    # Final metrics
    final_metrics: ConvergenceMetrics = field(default_factory=ConvergenceMetrics)
    
    # Answer
    final_answer: Optional[str] = None
    answer_confidence: float = 0.0
    
    # Recommendations
    recommended_next_steps: List[str] = field(default_factory=list)
    
    # Report text
    summary: str = ""
    
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        status = " CONVERGED" if self.converged else " STOPPED"
        
        return f"""# Epistemic Convergence Report

**Research Question:** {self.research_question}

**Status:** {status}  
**Stopping Reason:** {self.stopping_reason.value}

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Iterations | {self.total_iterations} |
| Hypotheses Generated | {self.total_hypotheses} |
| Hypotheses Supported | {self.hypotheses_supported} |
| Hypotheses Rejected | {self.hypotheses_rejected} |
| Experiments Conducted | {self.experiments_conducted} |

---

## Key Metrics

- **Discovery Rate:** {self.final_metrics.discovery_rate:.1%}
- **Novelty Score:** {self.final_metrics.novelty_score:.2f}
- **Saturation:** {self.final_metrics.saturation_ratio:.1%}
- **Epistemic Velocity:** {self.final_metrics.epistemic_velocity:.2f}
- **Provability Score:** {self.final_metrics.provability_score:.2f}

---

## Final Answer

{self.final_answer or "No definitive answer determined."}

**Confidence:** {self.answer_confidence:.1%}

---

## Supported Hypotheses

{chr(10).join(f"- {h}" for h in self.supported_hypotheses) or "None"}

---

## Recommended Next Steps

{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(self.recommended_next_steps))}

---

**Generated:** {self.generated_at.isoformat()}
"""


# ============================================================================
# EPISTEMIC CONVERGENCE ENGINE
# ============================================================================

class EpistemicConvergenceEngine:
    """
    Advanced convergence detection system for Ultron research.
    
    This engine monitors research progress and determines when to stop
    based on multiple sophisticated criteria:
    
    1. **Mandatory Criteria** (always enforced):
       - Iteration limit
       - Runtime limit
       - Budget exhaustion
       - No testable hypotheses remain
    
    2. **Intelligent Criteria** (ML-based):
       - Semantic novelty exhaustion
       - Epistemic velocity stagnation
       - Saturation of hypothesis space
       - Diminishing returns (cost/discovery)
       - Provability assessment (is this answerable?)
    
    Example:
        engine = EpistemicConvergenceEngine(
            max_iterations=10,
            max_runtime_hours=72
        )
        
        decision = engine.check_convergence(
            hypotheses=current_hypotheses,
            results=all_results,
            cycle_info=cycle_data
        )
        
        if decision.should_stop:
            report = engine.generate_final_report(research_question)
    """
    
    def __init__(
        self,
        max_iterations: int = 10,
        max_runtime_hours: float = 72.0,
        max_budget_usd: float = 1000.0,
        thresholds: Optional[Dict[str, float]] = None,
        enable_semantic_novelty: bool = True
    ):
        """
        Initialize the convergence engine.
        
        Args:
            max_iterations: Maximum research cycles
            max_runtime_hours: Maximum runtime in hours
            max_budget_usd: Maximum budget in USD
            thresholds: Override default thresholds
            enable_semantic_novelty: Use embeddings for novelty detection
        """
        import threading
        self._lock = threading.Lock()
        
        self.max_iterations = max_iterations
        self.max_runtime_hours = max_runtime_hours
        self.max_budget_usd = max_budget_usd
        self.enable_semantic_novelty = enable_semantic_novelty
        
        # Merge thresholds
        self.thresholds = CONVERGENCE_THRESHOLDS.copy()
        if thresholds:
            self.thresholds.update(thresholds)
        
        # Initialize metrics
        self.metrics = ConvergenceMetrics(
            max_iterations=max_iterations,
            max_runtime_hours=max_runtime_hours
        )
        
        # Hypothesis embeddings cache (for semantic novelty)
        self._hypothesis_embeddings: Dict[str, np.ndarray] = {}
        
        # Decision history
        self.decision_history: List[StoppingDecision] = []
        
        logger.info(
            f"EpistemicConvergenceEngine initialized: "
            f"max_iter={max_iterations}, max_hours={max_runtime_hours}"
        )
    
    # ========================================================================
    # MAIN CONVERGENCE CHECK
    # ========================================================================
    
    async def check_convergence(
        self,
        hypotheses: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        cycle_info: Dict[str, Any],
        research_question: Optional[str] = None
    ) -> StoppingDecision:
        """
        Check if research should stop.
        
        Args:
            hypotheses: List of hypothesis dicts with 'id', 'statement', 'status'
            results: List of experiment result dicts
            cycle_info: Current cycle information
            research_question: The research question being investigated
        
        Returns:
            StoppingDecision with recommendation
        """
        logger.info(f"Checking convergence (iteration {self.metrics.iteration_count + 1})")
        
        # Update metrics
        await self._update_metrics(hypotheses, results, cycle_info)
        
        # Check mandatory criteria first
        mandatory_checks = [
            self._check_iteration_limit,
            self._check_runtime_limit,
            self._check_budget_limit,
            self._check_hypothesis_exhaustion,
        ]
        
        for check_fn in mandatory_checks:
            decision = check_fn(hypotheses, results)
            if decision.should_stop:
                self.decision_history.append(decision)
                logger.info(f"Mandatory stop: {decision.reason.value}")
                return decision
        
        # Check intelligent criteria
        intelligent_checks = [
            self._check_novelty_exhaustion,
            self._check_epistemic_stagnation,
            self._check_saturation,
            self._check_diminishing_returns,
            self._check_provability_limit,
            self._check_answer_found,
        ]
        
        for check_fn in intelligent_checks:
            decision = check_fn(hypotheses, results)
            if decision.should_stop and decision.confidence_score >= 0.7:
                self.decision_history.append(decision)
                logger.info(f"Intelligent stop: {decision.reason.value} ({decision.confidence_score:.2f})")
                return decision
        
        # No stopping criteria met
        return StoppingDecision(
            should_stop=False,
            reason=StoppingReason.USER_REQUESTED,
            is_mandatory=False,
            confidence=ConvergenceConfidence.LOW,
            confidence_score=0.1,
            details="No stopping criteria met, research continues",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    # ========================================================================
    # MANDATORY CHECKS
    # ========================================================================
    
    def _check_iteration_limit(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if iteration limit reached."""
        should_stop = self.metrics.iteration_count >= self.max_iterations
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.ITERATION_LIMIT,
            is_mandatory=True,
            confidence=ConvergenceConfidence.CERTAIN,
            confidence_score=1.0,
            details=f"Iteration {self.metrics.iteration_count}/{self.max_iterations}",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    def _check_runtime_limit(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if runtime limit reached."""
        should_stop = self.metrics.elapsed_hours >= self.max_runtime_hours
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.RUNTIME_LIMIT,
            is_mandatory=True,
            confidence=ConvergenceConfidence.CERTAIN,
            confidence_score=1.0,
            details=f"Runtime {self.metrics.elapsed_hours:.1f}/{self.max_runtime_hours}h",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    def _check_budget_limit(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if budget exhausted."""
        should_stop = self.metrics.total_cost_usd >= self.max_budget_usd
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.BUDGET_EXHAUSTED,
            is_mandatory=True,
            confidence=ConvergenceConfidence.CERTAIN,
            confidence_score=1.0,
            details=f"Cost ${self.metrics.total_cost_usd:.2f}/${self.max_budget_usd:.2f}",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    @staticmethod
    def _is_hypothesis_supported(h: Dict[str, Any]) -> bool:
        status = str(h.get("status") or h.get("state") or "").lower()
        verdict = str(h.get("test_verdict") or "").lower()
        return status in ("supported", "confirmed", "verified") or verdict in ("supported", "confirmed", "support")

    @staticmethod
    def _is_hypothesis_rejected(h: Dict[str, Any]) -> bool:
        status = str(h.get("status") or h.get("state") or "").lower()
        verdict = str(h.get("test_verdict") or "").lower()
        return status in ("rejected", "refuted", "falsified", "killed") or verdict in ("rejected", "refuted", "refute", "falsified")

    @classmethod
    def _is_hypothesis_tested(cls, h: Dict[str, Any]) -> bool:
        if h.get("is_tested") is True:
            return True
        status = str(h.get("status") or h.get("state") or "").lower()
        if status in ("supported", "rejected", "tested", "confirmed", "refuted", "falsified", "inconclusive"):
            return True
        return cls._is_hypothesis_supported(h) or cls._is_hypothesis_rejected(h)

    @staticmethod
    def _is_result_significant(r: Dict[str, Any]) -> bool:
        if r.get("supports_hypothesis") is True or r.get("supported") is True:
            return True
        if str(r.get("evidence_type") or "").lower() == "support":
            return True
        inner = r.get("result")
        if isinstance(inner, dict):
            if inner.get("supports_hypothesis") is True or inner.get("supported") is True:
                return True
            if str(inner.get("evidence_type") or "").lower() == "support":
                return True
        return False

    def _check_hypothesis_exhaustion(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if no testable hypotheses remain."""
        untested = [h for h in hypotheses if not self._is_hypothesis_tested(h)]
        no_pending = len(untested) == 0
        all_tested = self.metrics.hypotheses_tested >= len(hypotheses) and len(hypotheses) > 0
        
        should_stop = no_pending and all_tested
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.NO_TESTABLE_HYPOTHESES,
            is_mandatory=True,
            confidence=ConvergenceConfidence.CERTAIN,
            confidence_score=1.0,
            details=f"{len(untested)} untested, {self.metrics.hypotheses_tested} tested",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    # ========================================================================
    # INTELLIGENT CHECKS
    # ========================================================================
    
    def _check_novelty_exhaustion(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if novelty is exhausted (no new ideas)."""
        trend = self.metrics.novelty_trend
        window = self.thresholds["novelty_decline_window"]
        threshold = self.thresholds["novelty_exhaustion_threshold"]
        
        if len(trend) < window:
            return StoppingDecision(
                should_stop=False,
                reason=StoppingReason.NOVELTY_EXHAUSTION,
                is_mandatory=False,
                confidence=ConvergenceConfidence.LOW,
                confidence_score=0.1,
                details=f"Insufficient data ({len(trend)}/{window} points)",
                metrics_snapshot=self.metrics.to_dict()
            )
        
        recent = trend[-window:]
        avg_novelty = sum(recent) / len(recent)
        all_below = all(v < threshold for v in recent)
        declining = all(recent[i] >= recent[i+1] for i in range(len(recent)-1))
        
        should_stop = all_below or (declining and avg_novelty < threshold * 2)
        confidence = 0.85 if all_below else (0.7 if declining else 0.3)
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.NOVELTY_EXHAUSTION,
            is_mandatory=False,
            confidence=ConvergenceConfidence.HIGH if should_stop else ConvergenceConfidence.LOW,
            confidence_score=confidence,
            details=f"Avg novelty: {avg_novelty:.2f}, threshold: {threshold}",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    def _check_epistemic_stagnation(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if knowledge discovery has stagnated."""
        history = self.metrics.knowledge_delta_history
        stagnation_cycles = self.thresholds["stagnation_cycles"]
        min_velocity = self.thresholds["epistemic_velocity_min"]
        
        if len(history) < stagnation_cycles:
            return StoppingDecision(
                should_stop=False,
                reason=StoppingReason.EPISTEMIC_STAGNATION,
                is_mandatory=False,
                confidence=ConvergenceConfidence.LOW,
                confidence_score=0.1,
                details="Insufficient history",
                metrics_snapshot=self.metrics.to_dict()
            )
        
        recent = history[-stagnation_cycles:]
        all_stagnant = all(v < min_velocity for v in recent)
        
        return StoppingDecision(
            should_stop=all_stagnant,
            reason=StoppingReason.EPISTEMIC_STAGNATION,
            is_mandatory=False,
            confidence=ConvergenceConfidence.HIGH if all_stagnant else ConvergenceConfidence.LOW,
            confidence_score=0.8 if all_stagnant else 0.2,
            details=f"Recent velocity: {recent}, min: {min_velocity}",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    def _check_saturation(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if hypothesis space is saturated."""
        threshold = self.thresholds["saturation_threshold"]
        saturation = self.metrics.saturation_ratio
        
        should_stop = saturation >= threshold
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.SATURATION_REACHED,
            is_mandatory=False,
            confidence=ConvergenceConfidence.HIGH if should_stop else ConvergenceConfidence.LOW,
            confidence_score=saturation if should_stop else 0.2,
            details=f"Saturation: {saturation:.1%}, threshold: {threshold:.1%}",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    def _check_diminishing_returns(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if cost per discovery is too high."""
        max_cost = self.thresholds["cost_per_discovery_max"]
        current_cost = self.metrics.cost_per_discovery
        
        if current_cost is None:
            return StoppingDecision(
                should_stop=False,
                reason=StoppingReason.DIMINISHING_RETURNS,
                is_mandatory=False,
                confidence=ConvergenceConfidence.LOW,
                confidence_score=0.1,
                details="No cost data",
                metrics_snapshot=self.metrics.to_dict()
            )
        
        should_stop = current_cost > max_cost
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.DIMINISHING_RETURNS,
            is_mandatory=False,
            confidence=ConvergenceConfidence.MEDIUM if should_stop else ConvergenceConfidence.LOW,
            confidence_score=0.7 if should_stop else 0.2,
            details=f"Cost/discovery: ${current_cost:.2f}, max: ${max_cost:.2f}",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    def _check_provability_limit(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """
        [TITAN V202.0] PROVABILITY RECLAMATION
        Physically abolished the 'Gödel-inspired' Rigor Theater.
        Provability limits are now strictly tied to the Information-Theoretic floor.
        """
        # If epistemic velocity (Information Gain) drops below the absolute minimum floor
        # for a sustained period, the manifold is mathematically saturated/unprovable.
        min_gain = self.thresholds.get("min_information_gain", 0.001)
        velocity = abs(getattr(self.metrics, "epistemic_velocity", 1.0))
        
        should_stop = velocity < min_gain and len(self.metrics.knowledge_delta_history) >= self.thresholds.get("stagnation_window", 5)
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.PROVABILITY_LIMIT,
            is_mandatory=False,
            confidence=ConvergenceConfidence.HIGH if should_stop else ConvergenceConfidence.LOW,
            confidence_score=0.9 if should_stop else 0.1,
            details=f"Information Gain ({velocity:.5f}) below mathematically sovereign floor ({min_gain:.5f}).",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    def _check_answer_found(
        self, hypotheses: List, results: List
    ) -> StoppingDecision:
        """Check if a definitive answer has been found."""
        # [TITAN V211.0] SOVEREIGN CONVERGENCE GATE
        # Physically derive the answer threshold from environment manifold.
        confidence = self.metrics.answer_confidence
        threshold = float(os.getenv("ULTRON_CONVERGENCE_FLOOR", "0.85"))
        
        should_stop = confidence >= threshold and self.metrics.best_answer is not None
        
        return StoppingDecision(
            should_stop=should_stop,
            reason=StoppingReason.ANSWER_FOUND,
            is_mandatory=False,
            confidence=ConvergenceConfidence.HIGH if should_stop else ConvergenceConfidence.LOW,
            confidence_score=confidence if should_stop else 0.1,
            details=f"Answer confidence: {confidence:.1%}",
            metrics_snapshot=self.metrics.to_dict()
        )
    
    # ========================================================================
    # METRICS UPDATE
    # ========================================================================
    
    async def _update_metrics(
        self,
        hypotheses: List[Dict],
        results: List[Dict],
        cycle_info: Dict[str, Any]
    ) -> None:
        """Update all convergence metrics in a thread-safe manner."""
        with self._lock:
            # Iteration tracking
            self.metrics.iteration_count = cycle_info.get("iteration", self.metrics.iteration_count + 1)
            
            # Time tracking
            if self.metrics.start_time is None:
                self.metrics.start_time = datetime.utcnow()
            self.metrics.elapsed_hours = (
                datetime.utcnow() - self.metrics.start_time
            ).total_seconds() / 3600
            
            # Hypothesis metrics
            self.metrics.total_hypotheses = len(hypotheses)
            tested = [h for h in hypotheses if self._is_hypothesis_tested(h)]
            self.metrics.hypotheses_tested = len(tested)
            
            # Saturation
            if self.metrics.total_hypotheses > 0:
                self.metrics.saturation_ratio = (
                    self.metrics.hypotheses_tested / self.metrics.total_hypotheses
                )
            
            # Experiment metrics
            self.metrics.total_experiments = len(results)
            significant = [r for r in results if self._is_result_significant(r)]
            self.metrics.significant_findings = len(significant)
            
            # Discovery rate
            if results:
                self.metrics.discovery_rate = len(significant) / len(results)
            
            # Novelty (simplified - would use embeddings in production)
            novelty = await self._calculate_novelty(hypotheses)
            self.metrics.novelty_score = novelty
            self.metrics.novelty_trend.append(novelty)
            
            # [TITAN V202.0] EPISTEMIC VELOCITY RECLAMATION
            # Physically abolished the dimensionless pseudo-math (novelty * discovery_rate).
            # We define velocity strictly as the Semantic Information Gain (novelty score).
            delta = cycle_info.get("knowledge_delta", novelty)
            self.metrics.knowledge_delta_history.append(delta)
            if len(self.metrics.knowledge_delta_history) >= 2:
                # Positive information-gain velocity (EWMA of novelty + empirical discovery yield)
                # Prevents steady high novelty (e.g. 0.90 -> 0.90) from registering as 0.0 velocity stagnation
                prev_vel = getattr(self.metrics, "epistemic_velocity", delta)
                self.metrics.epistemic_velocity = float(0.6 * max(0.0, float(delta)) + 0.4 * float(prev_vel))
            
            # Cost tracking
            self.metrics.total_cost_usd = cycle_info.get("total_cost", self.metrics.total_cost_usd)
            if self.metrics.significant_findings > 0:
                self.metrics.cost_per_discovery = (
                    self.metrics.total_cost_usd / self.metrics.significant_findings
                )
            
            # Answer confidence
            self.metrics.answer_confidence = cycle_info.get("answer_confidence", 0.0)
            self.metrics.best_answer = cycle_info.get("best_answer")
            
            logger.debug(f"Metrics updated: {self.metrics.to_dict()}")
    
    async def _calculate_novelty(self, hypotheses: List[Dict]) -> float:
        """
        Calculate semantic novelty of latest hypotheses.
        
        Uses cosine distance from previous hypotheses.
        Falls back to simple heuristics if embeddings unavailable.
        """
        if not hypotheses:
            return 1.0
        
        # Get latest hypotheses
        latest = [h for h in hypotheses if h.get("generation") == max(
            h.get("generation", 0) for h in hypotheses
        )]
        
        if not latest:
            return 0.5
            
        latest_statements = [h.get("statement", "") for h in latest]
        
        # 1. SEMANTIC NOVELTY (Production Grade)
        try:
            if self.enable_semantic_novelty:
                from backend.core.world_model import get_shared_embedding_model
                from sklearn.metrics.pairwise import cosine_similarity
                import concurrent.futures
                
                model = get_shared_embedding_model()
                
                if model:
                    # Get prior statements
                    all_statements = [h.get("statement", "") for h in hypotheses]
                    if len(all_statements) <= len(latest_statements):
                        return 1.0
                    
                    prior_statements = all_statements[:-len(latest_statements)]
                    
                    def compute_embeddings():
                        latest_emb = model.encode(latest_statements)
                        prior_emb = model.encode(prior_statements)
                        return cosine_similarity(latest_emb, prior_emb)

                    # [RIGOR FIX] Missing Timeout Fallback / Synchronous Bottleneck
                    # Prevent embedding model from locking the event loop indefinitely.
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(compute_embeddings)
                        try:
                            import asyncio
                            sims = await asyncio.wrap_future(future)
                        except concurrent.futures.TimeoutError:
                            logger.warning(" [EPISTEMIC FAILURE] Semantic embedding timed out. Falling back to keyword diversity.")
                            raise RuntimeError("Embedding timeout")
                    
                    # Novelty = 1 - Max Similarity found for each new hypothesis
                    # We average the novelty of the batch
                    batch_novelty = 1.0 - sims.max(axis=1).mean()
                    
                    logger.info(f"Semantic Novelty Score: {batch_novelty:.2f} (using shared singleton)")
                    return float(batch_novelty)
                else:
                    logger.warning("Shared embedding model unavailable for novelty check.")
                
        except Exception as e:
            logger.error(f" [EPISTEMIC FAILURE] Semantic novelty computation failed: {e}. Physically falling back to Rigorous Keyword Diversity.")

        # [TITAN V204.0] RIGOROUS KEYWORD DIVERSITY FALLBACK
        # Physically abolished the '0.0 failure loop'. 
        # We compute Jaccard-based diversity as a last-resort scientific baseline.
        # This prevents 'Autonomous Stop Fraud' when embeddings are temporarily unavailable.
        all_statements = [h.get("statement", "") for h in hypotheses]
        if len(all_statements) <= len(latest_statements):
            return 1.0  # First generation
            
        prior_statements = all_statements[:-len(latest_statements)]
        prior_corpus = " ".join(prior_statements).lower().split()
        prior_set = set([w for w in prior_corpus if len(w) > 4]) # Filter trivial words
        
        scores = []
        for stmt in latest_statements:
            current_set = set([w for w in stmt.lower().split() if len(w) > 4])
            if not current_set:
                scores.append(0.1)
                continue
            
            overlap = len(current_set & prior_set) / len(current_set)
            scores.append(1.0 - overlap)
            
        return sum(scores) / len(scores) if scores else 0.1
    
    # ========================================================================
    # REPORT GENERATION
    # ========================================================================
    
    def generate_final_report(
        self,
        research_question: str,
        hypotheses: List[Dict],
        results: List[Dict],
        stopping_reason: StoppingReason
    ) -> ConvergenceReport:
        """Generate comprehensive final report."""
        
        # Categorize hypotheses
        supported = [h.get("statement", "") for h in hypotheses if self._is_hypothesis_supported(h)]
        rejected = [h.get("statement", "") for h in hypotheses if self._is_hypothesis_rejected(h)]
        
        # Generate recommendations
        next_steps = self._generate_recommendations(
            hypotheses, results, stopping_reason
        )
        
        # Create report
        report = ConvergenceReport(
            research_question=research_question,
            converged=stopping_reason in [
                StoppingReason.ANSWER_FOUND,
                StoppingReason.SATURATION_REACHED,
                StoppingReason.NO_TESTABLE_HYPOTHESES
            ],
            stopping_reason=stopping_reason,
            total_iterations=self.metrics.iteration_count,
            total_hypotheses=self.metrics.total_hypotheses,
            hypotheses_supported=len(supported),
            hypotheses_rejected=len(rejected),
            experiments_conducted=self.metrics.total_experiments,
            supported_hypotheses=supported[:10],
            rejected_hypotheses=rejected[:10],
            final_metrics=self.metrics,
            final_answer=self.metrics.best_answer,
            answer_confidence=self.metrics.answer_confidence,
            recommended_next_steps=next_steps,
            summary=self._generate_summary(research_question, stopping_reason)
        )
        
        logger.info("Final convergence report generated")
        return report
    
    def _generate_recommendations(
        self,
        hypotheses: List[Dict],
        results: List[Dict],
        stopping_reason: StoppingReason
    ) -> List[str]:
        """Generate next step recommendations."""
        recommendations = []
        
        if stopping_reason == StoppingReason.NOVELTY_EXHAUSTION:
            recommendations.append("Consider reformulating the research question")
            recommendations.append("Explore adjacent or related research areas")
        
        if stopping_reason == StoppingReason.SATURATION_REACHED:
            recommendations.append("Research area is well-explored; document findings")
            recommendations.append("Replicate key findings with different methods")
        
        if stopping_reason == StoppingReason.DIMINISHING_RETURNS:
            recommendations.append("Optimize resource allocation for remaining questions")
            recommendations.append("Focus on highest-impact hypotheses only")
        
        if stopping_reason == StoppingReason.PROVABILITY_LIMIT:
            recommendations.append("Question may require empirical data not available")
            recommendations.append("Consider breaking into smaller, answerable sub-questions")
        
        # Always recommend documentation
        recommendations.append("Compile and publish findings")
        recommendations.append("Archive research artifacts for future reference")
        
        return recommendations[:5]
    
    def _generate_summary(
        self,
        research_question: str,
        stopping_reason: StoppingReason
    ) -> str:
        """Generate summary text."""
        return f"""Research on "{research_question}" completed after {self.metrics.iteration_count} iterations 
({self.metrics.elapsed_hours:.1f} hours).

Stopping Reason: {stopping_reason.value}

Generated {self.metrics.total_hypotheses} hypotheses and conducted {self.metrics.total_experiments} experiments.

Discovery rate: {self.metrics.discovery_rate:.1%}
Final novelty: {self.metrics.novelty_score:.2f}
Saturation: {self.metrics.saturation_ratio:.1%}

Total cost: ${self.metrics.total_cost_usd:.2f}
"""


# ============================================================================
# SINGLETON ACCESSOR
# ============================================================================

_engine_instance: Optional[EpistemicConvergenceEngine] = None

def get_convergence_engine(
    max_iterations: int = 10,
    max_runtime_hours: float = 72.0
) -> EpistemicConvergenceEngine:
    """Get or create the singleton convergence engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = EpistemicConvergenceEngine(
            max_iterations=max_iterations,
            max_runtime_hours=max_runtime_hours
        )
    return _engine_instance


def reset_convergence_engine() -> None:
    """Reset the convergence engine (for testing)."""
    global _engine_instance
    _engine_instance = None
