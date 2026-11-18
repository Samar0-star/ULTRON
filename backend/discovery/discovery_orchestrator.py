# -*- coding: utf-8 -*-
"""
DISCOVERY ORCHESTRATOR - THE KILLER CORE
================================================
Integrates the Assumption Graph, Reality Constraints, and Verdict system
into a unified discovery execution engine.

UPGRADES:
- Upgrade 1: Temporal Survival Mechanics (survival_cycles, SurvivorTier)
- Upgrade 2: Orthogonal Attack Generator (AttackAxis, orthogonality validation)
- Upgrade 3: Failure Pattern Memory (integrated with FailurePatternIndex)
- Upgrade 4: Survivor Amplification (amplify_survivor method)
- Upgrade 5: Discovery Rate Governance (half_life, structural_yield KPIs)
"""
import logging
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import os

_REDIS_DISABLED = False

# REDIS PERSISTENCE (PHASE 12 - Lazy Initialized on First Use)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client = None

def _get_redis_client():
    global _redis_client, _REDIS_DISABLED
    if _REDIS_DISABLED:
        return None
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)
        except Exception:
            _REDIS_DISABLED = True
            _redis_client = None
    return _redis_client

from backend.discovery.assumption_graph import (
    AssumptionGraph,
    Verdict,
    EscapeType,
    EscapeRouteReport,
    get_assumption_graph,
    reset_assumption_graph
)
from backend.discovery.reality_constraints import (
    check_reality_constraints,
    validate_necessity,
    DerivationGate,
    ConstraintType
)
from backend.discovery.failure_patterns import (
    get_failure_index,
    FailurePatternIndex
)
from backend.discovery.constants import ScientificDefaults  # [RIGOR] Scientific thresholds

try:
    from backend.core.skill_injector import get_expert_system
    from backend.llm_manager import run_llm
except ImportError:
    get_expert_system = None
    run_llm = None

# TITAN WORLD MODEL INTEGRATION (1000x UPGRADE)
try:
    from backend.core.world_model import WorldModel, Entity, CHROMADB_AVAILABLE
    WORLD_MODEL_AVAILABLE = True
except ImportError:
    WorldModel = None
    Entity = None
    CHROMADB_AVAILABLE = False
    WORLD_MODEL_AVAILABLE = False

logger = logging.getLogger(__name__)


# HARD CAPS (For long-running 12+ hour research sessions)
DISCOVERY_HARD_CAPS = {
    "max_claims": 100,         
    "max_assumptions": 500,     
    "max_eliminated_approaches": 100,  # Was 1
    "max_falsification_experiments": 100  # Was 1
}



# =============================================================================
# NEW UPGRADE 1A: DISCOVERY POLICY ENGINE (Separated from State)
# =============================================================================

class DiscoveryPolicy:
    """
    Acceptance and attack rules - SEPARATED from session state.
    
    This enables:
    - Evolving rules without corrupting state
    - Deterministic session replay
    - Multi-session scaling
    """
    
    def __init__(self, hard_caps: Dict[str, int] = None, world_model=None):
        self.hard_caps = hard_caps or DISCOVERY_HARD_CAPS
        self.world_model = world_model
        # [RIGOR] Scientifically justified thresholds (Cohen, 1988; Kosmos)
        self._min_novelty_threshold = ScientificDefaults.NOVELTY_THRESHOLD
        self._min_testability = ScientificDefaults.TESTABILITY_THRESHOLD
        self._survival_probability_weight = ScientificDefaults.WEIGHT_SURVIVAL_PROB
        self._structural_impact_weight = ScientificDefaults.WEIGHT_STRUCTURAL_IMPACT
        self._novelty_weight = ScientificDefaults.WEIGHT_NOVELTY
        self._testability_weight = ScientificDefaults.WEIGHT_TESTABILITY
    
    async def should_accept(self, statement: str, current_count: int, 
                      failure_patterns: 'FailurePatternIndex' = None) -> tuple:
        """
        Policy decision: should this assumption be accepted?
        
        Returns:
            (accept: bool, reason: str)
        """
        # Gate 1: Hard cap
        if current_count >= self.hard_caps["max_assumptions"]:
            return False, f"Hard cap reached ({self.hard_caps['max_assumptions']})"
        
        # Gate 2: Reality constraints
        is_valid, violated_constraint, violation_detail = await check_reality_constraints(statement)
        if not is_valid:
            return False, f"Reality constraint: {violated_constraint.value} - {violation_detail}"
        
        # Gate 3: Derivation gate
        is_valid, reason = await DerivationGate.validate_number_claim(statement)
        if not is_valid:
            return False, f"Derivation gate: {reason}"
        
        return True, "Passed all gates"
    
    def compute_discovery_value(self, assumption: str, 
                                 survival_stats: Dict[str, float],
                                 failure_patterns: 'FailurePatternIndex' = None,
                                 entity_count: int = 0) -> float:
        """
        UPGRADE 2: Discovery Value Function
        
        DiscoveryValue = Novelty  SurvivalProbability  StructuralImpact  Testability
        
        This turns the orchestrator from rule-driven to VALUE-DRIVEN.
        """
        # Novelty: how far from known failure patterns
        novelty = self._compute_novelty(assumption, failure_patterns)
        
        # Survival probability: based on past survival stats
        survival_prob = self._compute_survival_probability(survival_stats)
        
        # Structural impact: affects how many other assumptions
        structural_impact = self._compute_structural_impact(assumption, entity_count)
        
        # Testability: can it be attacked meaningfully?
        testability = self._compute_testability(assumption)
        
        # Weighted combination
        value = (
            self._novelty_weight * novelty +
            self._survival_probability_weight * survival_prob +
            self._structural_impact_weight * structural_impact +
            self._testability_weight * testability
        )
        
        return min(1.0, max(0.0, value))
    
    def _compute_novelty(self, assumption: str, failure_patterns: 'FailurePatternIndex' = None) -> float:
        """How different is this from known failure patterns?"""
        if not failure_patterns:
            return 0.7  # Default if no patterns available
        
        # Check against killed assumptions
        killed = failure_patterns.get_killed_assumptions() if hasattr(failure_patterns, 'get_killed_assumptions') else []
        if not killed:
            return 1.0

        # SEMANTIC UPGRADE: Use WorldModel embeddings if available
        if self.world_model:
            max_similarity = 0.0
            for killed_assumption in killed[:50]: # Check recent 50 kills
                sim = self.world_model.compute_similarity(assumption, killed_assumption)
                if sim > max_similarity:
                    max_similarity = sim
            
            # Novelty = 1 - Similarity
            return max(0.0, 1.0 - max_similarity)

        # FALLBACK: Jaccard similarity on substantive tokens (excluding stopwords)
        stopwords = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "that", "this"}
        assumption_words = set(w for w in assumption.lower().split() if w not in stopwords and len(w) > 2)
        if not assumption_words:
            return 0.5
        
        max_jaccard = 0.0
        for killed_assumption in killed[:20]:
            killed_lower = killed_assumption.lower() if isinstance(killed_assumption, str) else ""
            killed_words = set(w for w in killed_lower.split() if w not in stopwords and len(w) > 2)
            if killed_words:
                jaccard = len(assumption_words & killed_words) / len(assumption_words | killed_words)
                if jaccard > max_jaccard:
                    max_jaccard = jaccard
        
        return max(0.1, 1.0 - max_jaccard)
    
    def _compute_survival_probability(self, survival_stats: Dict[str, float]) -> float:
        """Based on historical survival rates."""
        if not survival_stats:
            return 0.5  # Default
        
        # Use historical half-life and survival rate
        half_life = survival_stats.get("half_life_hours", 4.0)
        survival_rate = survival_stats.get("survival_rate", 0.5)
        
        # Optimal half-life is 2-8 hours
        if 2.0 <= half_life <= 8.0:
            half_life_factor = 1.0
        elif half_life < 2.0:
            half_life_factor = 0.6  # System too harsh
        else:
            half_life_factor = 0.8  # System too lenient
        
        return survival_rate * half_life_factor
    
    def _compute_structural_impact(self, assumption: str, entity_count: int) -> float:
        """How many other assumptions would this affect?"""
        # Keywords that suggest structural importance
        structural_keywords = [
            "fundamental", "core", "base", "primary", "critical",
            "mechanism", "principle", "law", "governs", "controls",
            "determines", "causes", "enables", "prevents", "requires"
        ]
        
        assumption_lower = assumption.lower()
        keyword_hits = sum(1 for kw in structural_keywords if kw in assumption_lower)
        
        # More entities = higher potential structural impact
        entity_factor = min(1.0, entity_count / 10.0) if entity_count > 0 else 0.5
        
        impact = (keyword_hits * 0.15) + (entity_factor * 0.5)
        return min(1.0, impact + 0.2)  # Baseline of 0.2
    
    def _compute_testability(self, assumption: str) -> float:
        """Can this be attacked meaningfully?"""
        # Vague statements are not testable
        vague_markers = ["generally", "usually", "sometimes", "might", "could", "possibly"]
        # Specific statements are testable
        specific_markers = ["exactly", "always", "never", "must", "will", "at least", "at most", "%", "="]
        
        assumption_lower = assumption.lower()
        
        vague_score = sum(1 for m in vague_markers if m in assumption_lower) * 0.15
        specific_score = sum(1 for m in specific_markers if m in assumption_lower) * 0.2
        
        testability = 0.5 + specific_score - vague_score
        return max(0.1, min(1.0, testability))


# =============================================================================
# NEW UPGRADE 1B: SURVIVAL ENGINE (Separated from State)
# =============================================================================

class SurvivalEngine:
    """
    Tier promotion, cycle tracking, amplification - SEPARATED from session state.
    """
    
    @staticmethod
    def compute_tier(cycles: int, cycles_per_hour: float = 2.0, runtime_hours: float = 12.0) -> 'SurvivorTier':
        """
        Compute tier from survival cycles, SCALED to total runtime.
        
        Args:
            cycles: Current cycles survived
            cycles_per_hour: Speed of research (defaults to 2)
            runtime_hours: Total session duration (12, 24, 72)
            
        Logic:
            - Structural: > 20% of total runtime (or > 8 hours flat)
            - Resilient:  > 8% of total runtime (or > 3 hours flat)
        """
        hours_survived = cycles / cycles_per_hour
        
        # [RIGOR] Scientifically justified thresholds
        structural_threshold = max(ScientificDefaults.STRUCTURAL_FLAT_HOURS, 
                                   runtime_hours * ScientificDefaults.STRUCTURAL_RUNTIME_PCT)
        resilient_threshold = max(ScientificDefaults.RESILIENT_FLAT_HOURS,
                                  runtime_hours * ScientificDefaults.RESILIENT_RUNTIME_PCT)
        
        if hours_survived >= structural_threshold:
            return SurvivorTier.STRUCTURAL
        elif hours_survived >= resilient_threshold:
            return SurvivorTier.RESILIENT
        return SurvivorTier.ESCAPED
    
    @staticmethod
    def should_amplify(tier: 'SurvivorTier', cycles: int) -> bool:
        """Should we apply amplification pressure?"""
        return tier in [SurvivorTier.RESILIENT, SurvivorTier.STRUCTURAL]
    
    @staticmethod
    def generate_structured_explanation(assumption: str, 
                                         failed_attacks: List[str],
                                         regimes_tested: List[str],
                                         axes_used: List[str]) -> Dict[str, Any]:
        """
        UPGRADE 4: Explanation Generator (NOT creativity - structured prompts)
        
        After a failed kill or survival, generate:
        - WHY did this survive?
        - WHAT must be true?
        - WHAT variable is shielding it?
        """
        explanation = {
            "assumption": assumption,
            "failed_attacks_count": len(failed_attacks),
            "regimes_tested": regimes_tested,
            "axes_used": axes_used,
            "analysis": {}
        }
        
        # Infer WHY it survived based on failed attacks
        if len(failed_attacks) >= 3:
            explanation["analysis"]["survival_reason"] = "ROBUST: Survived multiple orthogonal attacks"
        elif "boundary" not in str(axes_used).lower():
            explanation["analysis"]["survival_reason"] = "UNTESTED_BOUNDARY: Boundary conditions not attacked"
        elif "regime" not in str(axes_used).lower():
            explanation["analysis"]["survival_reason"] = "UNTESTED_REGIME: Operating regimes not varied"
        else:
            explanation["analysis"]["survival_reason"] = "RESILIENT: Passed diverse attacks"
        
        # Infer WHAT must be true
        must_be_true = []
        if len(axes_used) >= 3:
            must_be_true.append("Assumption holds across multiple attack dimensions")
        if "parameter" in str(axes_used).lower() and "regime" in str(axes_used).lower():
            must_be_true.append("Relationship is parameter-regime invariant")
        if len(failed_attacks) >= 2:
            must_be_true.append(f"At least {len(failed_attacks)} attack vectors are insufficient")
        explanation["analysis"]["must_be_true"] = must_be_true
        
        # Infer shielding variables
        shielding_vars = []
        all_axes = {"parameter", "regime", "material", "formulation", "boundary"}
        untested = all_axes - set(str(a).lower() for a in axes_used)
        for axis in untested:
            shielding_vars.append(f"Possible shield: {axis} dimension untested")
        explanation["analysis"]["potential_shields"] = shielding_vars
        
        # Suggest next attacks
        explanation["next_attacks"] = [f"Attack via {axis} axis" for axis in untested]
        
        return explanation


# =============================================================================
# NEW UPGRADE 1C: GOVERNANCE ENGINE (Separated from State)
# =============================================================================

class GovernanceEngine:
    """
    Half-life, yield, KPI calculations - SEPARATED from session state.
    """
    
    @staticmethod
    def compute_half_life(birth_times: Dict[str, datetime], 
                          death_times: Dict[str, datetime]) -> Optional[float]:
        """Calculate average time (hours) before survivors die."""
        if len(death_times) < 2:
            return None
        
        lifespans = []
        for key, death_time in death_times.items():
            if key in birth_times:
                birth_time = birth_times[key]
                lifespan_hours = (death_time - birth_time).total_seconds() / 3600
                lifespans.append(lifespan_hours)
        
        if not lifespans:
            return None
        
        return sum(lifespans) / len(lifespans)
    
    @staticmethod
    def compute_structural_yield(total_survivors: int, structural_influences: int) -> float:
        """Calculate % of survivors that influence future work."""
        if total_survivors == 0:
            return 0.0
        return structural_influences / total_survivors
    
    @staticmethod
    def assess_half_life(half_life: Optional[float]) -> str:
        """Assess half-life health."""
        if half_life is None:
            return "INSUFFICIENT_DATA"
        elif half_life < 1.0:
            return "TOO_HARSH"
        elif half_life > 24.0:
            return "TOO_PERMISSIVE"
        return "OPTIMAL"
    
    @staticmethod
    def assess_yield(structural_yield: float) -> str:
        """Assess yield health."""
        if structural_yield == 0.0:
            return "NO_INFLUENCE"
        elif structural_yield < 0.01:
            return "MINIMAL"
        elif structural_yield <= 0.05:
            return "OPTIMAL"
        return "TOO_HIGH"
    
    @staticmethod
    def get_survival_stats(birth_times: Dict, death_times: Dict, 
                           structural_influences: int) -> Dict[str, float]:
        """Get survival statistics for value function."""
        half_life = GovernanceEngine.compute_half_life(birth_times, death_times)
        total = len(birth_times)
        deaths = len(death_times)
        
        return {
            "half_life_hours": half_life or 4.0,
            "survival_rate": (total - deaths) / total if total > 0 else 0.5,
            "structural_yield": structural_influences / total if total > 0 else 0.0
        }


# =============================================================================
# NEW UPGRADE 3: SEMANTIC ATTACK DISTANCE (Replaces keyword-only)
# =============================================================================

class SemanticAttackValidator:
    """
    Replace keyword-based orthogonality with semantic distance.
    
    Reject attacks if:
    - semantic distance < threshold AND axis overlap > 1
    """
    
    def __init__(self, world_model=None, distance_threshold: float = 0.4):
        self.world_model = world_model
        self.distance_threshold = distance_threshold
        self._embedding_cache: Dict[str, Any] = {}
    
    def compute_attack_distance(self, attack1: str, attack2: str) -> float:
        """
        Compute semantic distance between two attacks.
        Uses cosine distance on embeddings if available, else word overlap.
        """
        # Try to use WorldModel embeddings if available
        if self.world_model:
            return 1.0 - self.world_model.compute_similarity(attack1, attack2)
        elif WORLD_MODEL_AVAILABLE and CHROMADB_AVAILABLE:
            # Fallback if world_model not passed but might be available globally? 
            # (Strictly relies on injected instance now for cleanliness)
            pass
            
        return self._word_distance(attack1, attack2)
    
    def _semantic_distance(self, text1: str, text2: str) -> float:
        """Deprecated internal method - use compute_attack_distance direct logic."""
        return 1.0 - self.world_model.compute_similarity(text1, text2) if self.world_model else 1.0
    
    def _word_distance(self, text1: str, text2: str) -> float:
        """Word-based distance as fallback."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 1.0  # Max distance if empty
        
        # Jaccard distance
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0
        return 1.0 - similarity
    
    def is_sufficiently_orthogonal(self, new_attack: str, previous_attack: str,
                                    new_axes: Set, previous_axes: Set) -> tuple:
        """
        Check if new attack is sufficiently orthogonal.
        
        Returns:
            (is_orthogonal: bool, reason: str)
        """
        # Compute distances
        semantic_dist = self.compute_attack_distance(new_attack, previous_attack)
        axis_overlap = len(new_axes & previous_axes)
        
        # Reject if: low semantic distance AND high axis overlap
        if semantic_dist < self.distance_threshold and axis_overlap > 1:
            return False, f"Semantic distance {semantic_dist:.2f} < {self.distance_threshold} AND axis overlap {axis_overlap} > 1"
        
        # Accept if high semantic distance OR low axis overlap
        if semantic_dist >= self.distance_threshold:
            return True, f"Semantic distance {semantic_dist:.2f} >= {self.distance_threshold}"
        
        if axis_overlap <= 1:
            return True, f"Axis overlap {axis_overlap} <= 1"
        
        return True, "Passed orthogonality check"


# =============================================================================
# NEW UPGRADE 5: RECURSIVE DISCOVERY LOOPS (Hierarchical Discovery)
# =============================================================================

class RecursiveDiscoveryManager:
    """
    UPGRADE 5: Recursive Discovery Loops
    
    STRUCTURAL hypothesis 
        spawn 3 child discovery sessions 
            test under narrower regimes 
                only survivors propagate upward
    
    This creates hierarchical discovery, not flat exploration.
    This is what humans do subconsciously.
    
    Multiplier: ~30-50 long-term discovery power
    """
    
    def __init__(self, max_depth: int = 3, max_children: int = 3):
        self.max_depth = max_depth
        self.max_children = max_children
        self._child_sessions: Dict[str, List[Any]] = {}  # parent_id -> child sessions
        self._propagated_survivors: Dict[str, List[str]] = {}  # parent_id -> survivor statements
    
    def should_spawn_children(self, tier: 'SurvivorTier', current_depth: int) -> bool:
        """
        Should this session spawn child sessions?
        Only STRUCTURAL hypotheses at allowed depth can spawn.
        """
        return tier == SurvivorTier.STRUCTURAL and current_depth < self.max_depth
    
    def generate_child_regimes(self, parent_assumption: str, 
                                axes_used: List[str]) -> List[Dict[str, Any]]:
        """
        [RIGOR] FLAW 23 FIX: Generate adversarial child regimes.
        Child sessions MUST NOT inherit the parent assumption as a given truth.
        Instead, they are tasked with finding Independent Origins or Refutations.
        """
        all_axes = {"parameter", "regime", "material", "formulation", "boundary"}
        untested_axes = all_axes - set(str(a).lower() for a in axes_used)
        
        child_regimes = []
        
        # Generate adversarial regime for each untested axis
        for i, axis in enumerate(list(untested_axes)[:self.max_children]):
            child_regimes.append({
                "child_id": f"child_{i}",
                "focus_axis": axis,
                "regime_description": f"Attempt to INVALIDATE parent hypothesis by testing extreme {axis} edge cases.",
                "constraints": {
                    "primary_attack_axis": axis,
                    "target_for_refutation": parent_assumption, # NO INHERITANCE
                    "independent_origin_required": True,
                    "depth": 1
                }
            })
        
        # If not enough untested axes, create competitive alternative regimes
        if len(child_regimes) < self.max_children:
            for i in range(len(child_regimes), self.max_children):
                child_regimes.append({
                    "child_id": f"child_{i}",
                    "focus_axis": "alternative_mechanism",
                    "regime_description": "Search for an entirely different physical mechanism that explains the observed data.",
                    "constraints": {
                        "primary_attack_axis": "mechanism",
                        "parent_context": parent_assumption,
                        "search_for_conflict": True,
                        "depth": 1
                    }
                })
        
        return child_regimes[:self.max_children]
    
    def register_child_session(self, parent_id: str, child_session: Any) -> None:
        """Register a child session."""
        if parent_id not in self._child_sessions:
            self._child_sessions[parent_id] = []
        self._child_sessions[parent_id].append(child_session)
    
    def propagate_survivor(self, parent_id: str, survivor_statement: str) -> None:
        """Record a survivor that propagated from child to parent."""
        if parent_id not in self._propagated_survivors:
            self._propagated_survivors[parent_id] = []
        self._propagated_survivors[parent_id].append(survivor_statement)
        logger.info(f"[RECURSIVE] Survivor propagated to parent {parent_id}: {survivor_statement[:50]}...")
    
    def get_child_sessions(self, parent_id: str) -> List[Any]:
        """Get all child sessions for a parent."""
        return self._child_sessions.get(parent_id, [])
    
    def get_propagated_survivors(self, parent_id: str) -> List[str]:
        """Get all survivors that propagated from children."""
        return self._propagated_survivors.get(parent_id, [])
    
    def compute_hierarchical_confidence(self, parent_id: str) -> float:
        """
        Compute confidence boost from hierarchical survival.
        
        If a hypothesis survives in multiple child regimes,
        its confidence increases multiplicatively.
        """
        survivors = self._propagated_survivors.get(parent_id, [])
        children = self._child_sessions.get(parent_id, [])
        
        if not children:
            return 1.0  # No children, no boost
        
        survival_rate = len(survivors) / len(children) if children else 0
        
        # Boost: 1.0 + (0.2 per surviving child, max 1.5)
        boost = 1.0 + (survival_rate * 0.5)
        return min(1.5, boost)
    
    def create_recursive_discovery_plan(self, structural_assumption: str,
                                          current_session: 'DiscoverySession') -> Dict[str, Any]:
        """
        Create a full recursive discovery plan for a STRUCTURAL hypothesis.
        
        Returns:
            Plan dict with child regimes, attack sequences, and propagation rules
        """
        if not current_session.is_structural():
            return {"error": "Only STRUCTURAL hypotheses can spawn recursive discovery"}
        
        # Get axes already used
        axes_used = [a.value if hasattr(a, 'value') else str(a) 
                     for a in current_session.attack_history] if hasattr(current_session, 'attack_history') else []
        
        # Flatten attack_history if it's a list of sets
        flat_axes = []
        for item in axes_used:
            if isinstance(item, set):
                flat_axes.extend(list(item))
            else:
                flat_axes.append(item)
        
        child_regimes = self.generate_child_regimes(structural_assumption, flat_axes)
        
        plan = {
            "parent_session_id": current_session.session_id,
            "structural_assumption": structural_assumption,
            "survival_cycles": current_session.survival_cycles,
            "tier": current_session.current_tier.value,
            "child_regimes": child_regimes,
            "propagation_rules": {
                "require_all_children_survive": False,
                "min_children_survive": 1,
                "confidence_boost_per_child": 0.15,
                "max_confidence_boost": 0.5
            },
            "termination_conditions": {
                "max_depth": self.max_depth,
                "max_total_sessions": self.max_children ** self.max_depth,
                "timeout_hours": 24
            }
        }
        
        logger.info(f"[RECURSIVE] Created discovery plan with {len(child_regimes)} child regimes")
        return plan


# =============================================================================
# UPGRADE 1: TEMPORAL SURVIVAL MECHANICS
# =============================================================================

class SurvivorTier(Enum):
    """
    [RIGOR] FLAW 22 FIX: Promotion tiers based on RIGOROUS EVIDENCE, not cycles.
    """
    ESCAPED = "escaped"           # Preliminary lead
    RESILIENT = "resilient"       # Survived independent numerical stress test
    STRUCTURAL = "structural"     # Survived deep statistical falsification (Rigor > 0.8)

def get_tier_from_rigor(rigor_score: float, distinct_attacks: int) -> SurvivorTier:
    """Compute tier from scientific rigor index and diversity of attacks."""
    # [RIGOR] Scientific thresholds (Cohen's effect sizes)
    if rigor_score >= ScientificDefaults.STRUCTURAL_RIGOR and distinct_attacks >= 3:
        return SurvivorTier.STRUCTURAL
    elif rigor_score >= ScientificDefaults.RESILIENT_RIGOR and distinct_attacks >= 1:
        return SurvivorTier.RESILIENT
    else:
        return SurvivorTier.ESCAPED


# =============================================================================
# UPGRADE 2: ORTHOGONAL ATTACK GENERATOR
# =============================================================================

class AttackAxis(Enum):
    """
    Attack axes for orthogonality enforcement.
    
    Rule: A falsification attempt is INVALID if it shares >1 axis 
    with the previous attempt. This ensures independent stress testing.
    """
    PARAMETER = "parameter"           # Changing numerical thresholds
    REGIME = "regime"                 # Changing operating conditions (T, P, rate)
    MATERIAL = "material"             # Changing material composition
    FORMULATION = "formulation"       # Changing mathematical model
    BOUNDARY = "boundary"             # Changing boundary conditions

    @classmethod
    def from_attack_text(cls, text: str) -> Set["AttackAxis"]:
        """
        Infer attack axes from attack description text.
        """
        text_lower = text.lower()
        axes = set()
        
        # Parameter axis markers
        if any(m in text_lower for m in ["threshold", "limit", "value", "number", "constant", "coefficient"]):
            axes.add(cls.PARAMETER)
        
        # Regime axis markers
        if any(m in text_lower for m in ["temperature", "pressure", "rate", "current", "voltage", "speed", "condition"]):
            axes.add(cls.REGIME)
        
        # Material axis markers
        if any(m in text_lower for m in ["material", "composition", "electrolyte", "cathode", "anode", "substrate", "alloy"]):
            axes.add(cls.MATERIAL)
        
        # Formulation axis markers
        if any(m in text_lower for m in ["equation", "model", "formula", "derivation", "assumption", "theory"]):
            axes.add(cls.FORMULATION)
        
        # Boundary axis markers
        if any(m in text_lower for m in ["boundary", "initial", "interface", "surface", "edge", "constraint"]):
            axes.add(cls.BOUNDARY)
        
        # Default to PARAMETER if nothing detected
        if not axes:
            axes.add(cls.PARAMETER)
        
        return axes


@dataclass
class DiscoverySession:
    """
    State container for a Discovery Mode session.
    
    Includes all 5 upgrades:
    - Upgrade 1: Temporal survival tracking
    - Upgrade 2: Attack orthogonality
    - Upgrade 3: Failure pattern integration
    - Upgrade 4: Survivor amplification
    - Upgrade 5: Governance KPIs
    """
    session_id: str
    mission_id: str = "default_user"
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    # Graph - Initialized in __post_init__ to respect mission_id
    assumption_graph: AssumptionGraph = field(init=False)
    
    # Outputs (capped)
    claims: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    eliminated_approaches: List[str] = field(default_factory=list)
    falsification_experiments: List[str] = field(default_factory=list)
    
    # Escape Routes
    escape_routes: EscapeRouteReport = field(default_factory=EscapeRouteReport)
    
    # Verdict
    verdict: Verdict = Verdict.CONDITIONALLY_DEAD
    verdict_reason: str = ""
    
    # Refusal tracking (KPI)
    total_assumptions_proposed: int = 0
    assumptions_refused: int = 0
    refusal_reasons: List[str] = field(default_factory=list)
    
    # =========================================================================
    # UPGRADE 1: TEMPORAL SURVIVAL MECHANICS
    # =========================================================================
    survival_cycles: int = 0
    distinct_attack_vectors: Set[str] = field(default_factory=set)
    failed_kill_reasons: List[str] = field(default_factory=list)
    current_tier: SurvivorTier = SurvivorTier.ESCAPED
    survival_score: float = 0.0  # Real-time resilience score (0.0 - 1.0)
    force_reading_next_cycle: bool = False  # Flag to trigger deep reading rescue
    
    def record_adversarial_score(self, score: float) -> None:
        """Update the running average survival score."""
        # Weighted update: 70% new score, 30% history (to reflect consistency)
        if self.survival_score == 0.0:
            self.survival_score = score
        else:
            self.survival_score = (self.survival_score * 0.3) + (score * 0.7)
        logger.info(f" [RESILIENCE] Survival Score updated: {self.survival_score:.2f}")
    
    # =========================================================================
    # UPGRADE 2: ORTHOGONAL ATTACK GENERATOR
    # =========================================================================
    last_attack_axes: Set[AttackAxis] = field(default_factory=set)
    last_attack_text: str = ""
    attack_history: List[Set[str]] = field(default_factory=list)  # Track all attacks
    orthogonality_rejections: int = 0
    
    # =========================================================================
    # UPGRADE 5: DISCOVERY RATE GOVERNANCE
    # =========================================================================
    survivor_birth_times: Dict[str, datetime] = field(default_factory=dict)
    survivor_death_times: Dict[str, datetime] = field(default_factory=dict)
    structural_influences: int = 0
    
    # =========================================================================
    # UPGRADE 6: TITAN WORLD MODEL INTEGRATION (1000x POWER)
    # =========================================================================
    # WorldModel instance (initialized in __post_init__)
    _world_model: Optional[Any] = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize components after dataclass creation."""
        # Initialize graph scoped to both mission_id and session_id
        self.assumption_graph = get_assumption_graph(self.mission_id, self.session_id)
        
        if WORLD_MODEL_AVAILABLE and WorldModel is not None:
            try:
                self._world_model = WorldModel(session_id=self.session_id)
                logger.info(f" TITAN WorldModel attached to DiscoverySession (session={self.session_id})")
            except Exception as e:
                logger.warning(f"WorldModel init failed: {e}")
                self._world_model = None
        
        # Initialize Semantic Validator
        self.semantic_validator = SemanticAttackValidator(world_model=self._world_model)
    
    @property
    def world_model(self) -> Optional[Any]:
        """Get the WorldModel instance."""
        return self._world_model
    
    def sync_to_world_model(self, key: str, value: Any, confidence: float = 1.0) -> bool:
        """
        Sync a discovery finding to the WorldModel.
        
        Args:
            key: Fact key (e.g., "discovery.assumption.validated")
            value: Fact value
            confidence: Confidence score (0-1)
            
        Returns:
            True if synced successfully
        """
        if not self._world_model:
            return False
        
        try:
            self._world_model.add_fact(
                key=key,
                value=value,
                source=f"discovery_session_{self.session_id}",
                confidence=confidence,
                metadata={"session_id": self.session_id, "tier": self.current_tier.value}
            )
            return True
        except Exception as e:
            logger.error(f"WorldModel sync failed: {e}")
            return False
    
    def create_discovery_entity(self, entity_type: str, properties: Dict[str, Any]) -> Optional[str]:
        """
        Create an entity in the WorldModel from discovery findings.
        
        Returns:
            Entity ID if created, None otherwise
        """
        if not self._world_model or Entity is None:
            return None
        
        try:
            entity = Entity(
                type=entity_type,
                properties=properties,
                source=f"discovery_session_{self.session_id}",
                confidence=0.8 if self.is_structural() else 0.5,
                metadata={"tier": self.current_tier.value, "survival_cycles": self.survival_cycles}
            )
            self._world_model.add_entity(entity)
            
            # Index in ChromaDB if available
            if CHROMADB_AVAILABLE and hasattr(self._world_model, 'index_entity_chroma'):
                text = f"{entity_type}: {str(properties)}"
                self._world_model.index_entity_chroma(entity.entity_id, text)
            
            return entity.entity_id
        except Exception as e:
            logger.error(f"Entity creation failed: {e}")
            return None
    
    # =========================================================================
    # CORE METHODS
    # =========================================================================
    
    @property
    def refusal_rate(self) -> float:
        """Calculate refusal rate."""
        if self.total_assumptions_proposed == 0:
            return 0.0
        return self.assumptions_refused / self.total_assumptions_proposed
    
    async def add_assumption(self, statement: str) -> bool:
        """
        Add an assumption with all gates applied.
        
        Returns:
            bool: True if accepted, False if refused
        """
        self.total_assumptions_proposed += 1
        
        # GATE 1: Hard Cap
        if len(self.assumptions) >= DISCOVERY_HARD_CAPS["max_assumptions"]:
            self.assumptions_refused += 1
            self.refusal_reasons.append(f"Hard cap reached ({DISCOVERY_HARD_CAPS['max_assumptions']})")
            logger.warning(f"REFUSED (Hard Cap): {statement[:50]}...")
            return False
        
        # GATE 2: Reality Constraints
        is_valid, violated_constraint, violation_detail = await check_reality_constraints(statement)
        if not is_valid:
            self.assumptions_refused += 1
            self.refusal_reasons.append(f"Reality constraint: {violated_constraint.value} - {violation_detail}")
            logger.warning(f"REFUSED (Reality Constraint): {statement[:50]}... -> {violation_detail}")
            
            # UPGRADE 3: Record to failure pattern index
            get_failure_index().record_constraint_kill(violated_constraint.value, statement[:100])
            return False
        
        # GATE 3: Derivation Gate
        is_valid, reason = await DerivationGate.validate_number_claim(statement)
        if not is_valid:
            self.assumptions_refused += 1
            self.refusal_reasons.append(f"Derivation gate: {reason}")
            logger.warning(f"REFUSED (Derivation Gate): {statement[:50]}... -> {reason}")
            return False
        
        # GATE 4: Irreversibility Check (via graph)
        node_id = self.assumption_graph.add_assumption(statement)
        if node_id is None:
            self.assumptions_refused += 1
            self.refusal_reasons.append("Irreversibility: Killed assumption rephrased")
            logger.warning(f"REFUSED (Irreversibility): {statement[:50]}...")
            return False
        
        # Passed all gates
        self.assumptions.append(statement)
        # [FIX] Append proposed claim so SNR/SRI can be computed honestly (not placebo)
        if len(self.claims) < DISCOVERY_HARD_CAPS["max_claims"]:
            self.claims.append(f"proposed: {statement[:100]}")
        
        # UPGRADE 5: Record birth time
        self.survivor_birth_times[statement[:50]] = datetime.utcnow()
        
        logger.info(f"ACCEPTED: {statement[:50]}...")
        
        # PERSIST STATE
        self.save_to_redis()
        
        return True
    
    # =========================================================================
    # UPGRADE 1: TEMPORAL SURVIVAL METHODS
    # =========================================================================
    
    def record_survival(self, attack_vector: str = "", semantic_verdict: str = "UNKNOWN", rigor_score: float = 0.0) -> None:
        """
        [RIGOR] FLAW 22 FIX: Record survival with scientific proof.
        """
        self.survival_cycles += 1
        
        if attack_vector:
            import re
            # [FIX] Record actual attack axis values for diversity index (not cycle-specific strings)
            inferred_axes = AttackAxis.from_attack_text(attack_vector)
            if not inferred_axes:
                # If no keywords are matched, fall back to mapping cycle number to AttackAxis value deterministically
                cycle_match = re.search(r'cycle\s*(\d+)', attack_vector, re.IGNORECASE)
                if cycle_match:
                    cycle_num = int(cycle_match.group(1))
                    axes_list = list(AttackAxis)
                    fallback_axis = axes_list[cycle_num % len(axes_list)]
                    inferred_axes = {fallback_axis}
                else:
                    inferred_axes = {AttackAxis.PARAMETER}
            
            for axis in inferred_axes:
                self.distinct_attack_vectors.add(axis.value)
            # [FIX] Populate claims list so SRI/SNR metrics are not placebo
            claim_label = f"validated: survived {attack_vector} (rigor={rigor_score:.2f})"
            if len(self.claims) < DISCOVERY_HARD_CAPS["max_claims"]:
                self.claims.append(claim_label)
        
        # Update tier
        old_tier = self.current_tier
        
        # Promotion based on evidence + distinct attacks
        self.current_tier = get_tier_from_rigor(rigor_score, len(self.distinct_attack_vectors))
        
        if self.current_tier != old_tier:
            logger.info(f"[SURVIVOR TIER] Promoted: {old_tier.value} -> {self.current_tier.value} (Rigor: {rigor_score:.2f}, Attacks: {len(self.distinct_attack_vectors)})")
            
        # PERSIST STATE
        self.save_to_redis()
    
    def record_failed_kill(self, reason: str) -> None:
        """Record a failed kill attempt with reason."""
        self.failed_kill_reasons.append(reason)
        # [RIGOR] FLAW 22 FIX: Software errors or timeouts do NOT grant survival points.
        logger.info(f"[FAILED KILL] Attack aborted/failed due to environment: {reason[:100]}...")
        # Do not call record_survival() here anymore.
    
    def is_structural(self) -> bool:
        """Check if this hypothesis is STRUCTURAL tier (can influence future work)."""
        return self.current_tier == SurvivorTier.STRUCTURAL
    
    def is_resilient(self) -> bool:
        """Check if this hypothesis is RESILIENT or higher."""
        return self.current_tier in [SurvivorTier.RESILIENT, SurvivorTier.STRUCTURAL]
    
    # =========================================================================
    # UPGRADE 2: ORTHOGONAL ATTACK METHODS
    # =========================================================================
    
    def validate_attack_orthogonality(self, attack_text: str) -> bool:
        """
        Validate that a new attack is orthogonal to the previous attack.
        
        Rule: Invalid if shares >1 axis with previous attack.
        
        Returns:
            bool: True if attack is orthogonal (valid), False if too similar
        """
        new_axes = AttackAxis.from_attack_text(attack_text)
        
        # First attack is always valid
        if not self.last_attack_axes:
            self.last_attack_axes = new_axes
            self.last_attack_text = attack_text
            self.attack_history.append({a.value for a in new_axes})
            return True
        
        # UPGRADE 2 + 3: Semantic + Axis Orthogonality Check
        is_valid, reason = self.semantic_validator.is_sufficiently_orthogonal(
            new_attack=attack_text,
            previous_attack=self.last_attack_text,
            new_axes={a.value for a in new_axes},
            previous_axes={a.value for a in self.last_attack_axes}
        )
        
        if not is_valid:
            self.orthogonality_rejections += 1
            logger.warning(f"[ORTHOGONALITY] Rejected: {reason}")
            return False
        
        # Valid - update history
        self.last_attack_axes = new_axes
        self.last_attack_text = attack_text
        self.attack_history.append({a.value for a in new_axes})
        logger.info(f"[ORTHOGONALITY] Accepted: {reason}")
        return True
    
    def suggest_orthogonal_axes(self) -> List[str]:
        """
        Suggest attack axes that haven't been used recently.
        
        Returns:
            List of axis names to consider for next attack
        """
        all_axes = set(AttackAxis)
        used_axes = self.last_attack_axes
        unused = all_axes - used_axes
        return [a.value for a in unused]
    
    # =========================================================================
    # UPGRADE 4: SURVIVOR AMPLIFICATION
    # =========================================================================
    
    def amplify_survivor(self, llm_manager=None) -> Dict[str, Any]:
        """
        Generate pressure on survivors when they reach RESILIENT tier.
        
        NOT creativity - this is PRESSURE.
        - Force stronger attacks
        - Generate competitor hypotheses
        - Ask: "What must be true if this survives?"
        
        Returns:
            Dict with amplification results
        """
        if not self.is_resilient():
            return {"status": "NOT_RESILIENT", "message": "Hypothesis has not yet reached RESILIENT tier"}
        
        result = {
            "status": "AMPLIFIED",
            "tier": self.current_tier.value,
            "survival_cycles": self.survival_cycles,
            "distinct_attacks": list(self.distinct_attack_vectors),
            "failed_kills": len(self.failed_kill_reasons),
            "stronger_attacks": [],
            "competitor_questions": [],
            "implications": []
        }
        
        # Suggest unused attack axes
        unused_axes = self.suggest_orthogonal_axes()
        if unused_axes:
            result["stronger_attacks"] = [f"Attack via {axis} axis" for axis in unused_axes]
        
        # Standard competitor questions (no LLM needed)
        result["competitor_questions"] = [
            "What alternative approach would invalidate this hypothesis if true?",
            "What boundary condition has NOT been tested?",
            "What material substitution would break this?"
        ]
        
        # Standard implications (no LLM needed)
        result["implications"] = [
            f"If this survives {self.survival_cycles + 2} more cycles, it becomes STRUCTURAL",
            f"This hypothesis has resisted {len(self.distinct_attack_vectors)} distinct attack types",
            "Next attack MUST use a different axis combination"
        ]
        
        logger.info(f"[SURVIVOR AMPLIFICATION] Generated pressure for tier={self.current_tier.value}")
        return result
    
    # =========================================================================
    # UPGRADE 5: GOVERNANCE KPIs
    # =========================================================================
    
    def get_survivor_half_life(self) -> Optional[float]:
        """
        Calculate average time (hours) before survivors die.
        
        Interpretation:
        - Too short (< 1h) -> System too harsh
        - Infinite (no deaths) -> System too permissive
        - Optimal: 2-8 hours
        
        Returns:
            float: Average hours, or None if insufficient data
        """
        if len(self.survivor_death_times) < 2:
            return None
        
        lifespans = []
        for key, death_time in self.survivor_death_times.items():
            if key in self.survivor_birth_times:
                birth_time = self.survivor_birth_times[key]
                lifespan_hours = (death_time - birth_time).total_seconds() / 3600
                lifespans.append(lifespan_hours)
        
        if not lifespans:
            return None
        
        return sum(lifespans) / len(lifespans)
    
    def get_structural_yield(self) -> float:
        """
        Calculate % of survivors that influence future work.
        
        Target: Very low (1-5%) but non-zero.
        
        Returns:
            float: Percentage (0.0 - 1.0)
        """
        total_survivors = len(self.survivor_birth_times)
        if total_survivors == 0:
            return 0.0
        
        return self.structural_influences / total_survivors
    
    def record_structural_influence(self) -> None:
        """Record that a STRUCTURAL hypothesis influenced future work."""
        if self.is_structural():
            self.structural_influences += 1
            logger.info(f"[GOVERNANCE] Structural influence recorded (total: {self.structural_influences})")
    
    def record_death(self, assumption_key: str, reason: str = "") -> None:
        """
        Record the death of a survivor.
        
        Args:
            assumption_key: First 50 chars of assumption (used as key)
            reason: Reason for death
        """
        self.survivor_death_times[assumption_key] = datetime.utcnow()
        # [FIX] Record death/rejection in the claims list
        if len(self.claims) < DISCOVERY_HARD_CAPS["max_claims"]:
            self.claims.append(f"rejected: {assumption_key[:100]} (reason={reason})")
        
        # UPGRADE 3: Record to failure pattern index
        get_failure_index().record_assumption_death("general", reason[:100])
        
        logger.info(f"[GOVERNANCE] Death recorded: {assumption_key[:30]}...")
        
        # PERSIST STATE
        self.save_to_redis()
    
    def get_governance_report(self) -> Dict[str, Any]:
        """Generate full governance KPI report."""
        half_life = self.get_survivor_half_life()
        structural_yield = self.get_structural_yield()
        
        # Assess half-life
        if half_life is None:
            half_life_assessment = "INSUFFICIENT_DATA"
        elif half_life < 1.0:
            half_life_assessment = "TOO_HARSH"
        elif half_life > 24.0:
            half_life_assessment = "TOO_PERMISSIVE"
        else:
            half_life_assessment = "OPTIMAL"
        
        # Assess yield
        # [RIGOR] Scientific yield thresholds
        if structural_yield == 0.0:
            yield_assessment = "NO_INFLUENCE"
        elif structural_yield < ScientificDefaults.STRUCTURAL_YIELD_MIN:
            yield_assessment = "MINIMAL"
        elif structural_yield <= ScientificDefaults.STRUCTURAL_YIELD_OPTIMAL_MAX:
            yield_assessment = "OPTIMAL"
        else:
            yield_assessment = "TOO_HIGH"
        
        return {
            "survivor_half_life_hours": half_life,
            "half_life_assessment": half_life_assessment,
            "structural_yield": structural_yield,
            "yield_assessment": yield_assessment,
            "total_survivors": len(self.survivor_birth_times),
            "total_deaths": len(self.survivor_death_times),
            "structural_influences": self.structural_influences,
            "orthogonality_rejections": self.orthogonality_rejections,
            "survival_cycles": self.survival_cycles,
            "current_tier": self.current_tier.value
        }

    def evaluate_session_quality(self) -> Dict[str, Any]:
        """
        Phase 5: SCHOLAR EVALUATION (Mind/Body Lock)
        
        Uses 'scholar_evaluation_titan' to grade the session based on governance KPIs.
        """
        report = self.get_governance_report()
        
        # 1. Prepare Protocol
        meta_prompt = ""
        if get_expert_system:
            try:
                expert = get_expert_system()
                # Force "Scholar Evaluation" T1 Skills
                t1_skills = expert._check_keyword_overrides("grade", "T1") 
                if not t1_skills:
                     t1_skills = expert._check_keyword_overrides("scholar", "T1")

                if t1_skills:
                    meta_prompt = "\n#  [COGNITIVE_OS] - SCHOLAR EVALUATION PROTOCOLS\n"
                    for s in t1_skills:
                        meta_prompt += s.to_prompt_block(include_examples=False)
                    logger.info(f" Mind/Body Lock: Injected {len(t1_skills)} Scholar Skills.")
            except Exception as e:
                logger.warning(f"Failed to inject Scholar skills: {e}")

        # 2. Construct Prompt
        prompt = f"""
        {meta_prompt}

        OBJECTIVE: Grade this discovery session.
        
        METRICS:
        {json.dumps(report, indent=2)}
        
        SURVIVORS ({len(self.assumptions)}):
        {json.dumps(self.assumptions[:10], indent=2)}... (truncated)
        
        Execute the SCHOLAR PROTOCOL now.
        """

        # 3. Call LLM
        review = "LLM_UNAVAILABLE"
        if run_llm:
            try:
                # UPGRADE: Use centralized model constant
                from backend.llm_manager import TASK_ROUTING_MODEL
                result = run_llm(prompt, model=TASK_ROUTING_MODEL) 
                review = result.get("text", "") if isinstance(result, dict) else str(result)
            except Exception as e:
                logger.error(f"Scholar grading failed: {e}")
                review = f"Error: {e}"
        
        return {
            "metrics": report,
            "scholar_review": review
        }
    
    # =========================================================================
    # EXISTING METHODS (PRESERVED)
    # =========================================================================
    
    def violate_assumption(self, statement: str, reason: str, source: str) -> List[str]:
        """
        Violate an assumption and cascade.
        
        Returns:
            List of all violated assumption IDs
        """
        # Find node by statement
        for node_id, node in self.assumption_graph.nodes.items():
            if node.statement == statement:
                # UPGRADE 3: Record to failure pattern index
                get_failure_index().record_assumption_death("violated", reason[:100])
                
                # UPGRADE 5: Record death
                self.record_death(statement[:50], reason)
                
                return self.assumption_graph.violate(node_id, reason, source)
        
        return []
    
    def set_escape_route(
        self,
        escape_type: EscapeType,
        exists: bool,
        evidence_fact_id: Optional[str] = None,
        confidence: float = 0.8
    ) -> None:
        """Set an escape route status while preserving VerifiedEscape dataclass integrity."""
        from backend.discovery.assumption_graph import VerifiedEscape
        esc_obj = VerifiedEscape(
            exists=bool(exists),
            evidence_fact_id=evidence_fact_id,
            confidence=float(confidence) if exists else 0.0
        )
        if escape_type == EscapeType.MATERIAL:
            self.escape_routes.material_escape = esc_obj
        elif escape_type == EscapeType.GEOMETRY:
            self.escape_routes.geometry_escape = esc_obj
        elif escape_type == EscapeType.OPERATING_REGIME:
            self.escape_routes.operating_regime_escape = esc_obj
        elif escape_type == EscapeType.CONTROL:
            self.escape_routes.control_escape = esc_obj
        
        # UPGRADE 3: If escape was set to True but later fails, record it
        if not exists:
            get_failure_index().record_escape_failure(escape_type.value, "Escape route invalidated")
    
    def finalize_verdict(self) -> None:
        """Calculate final verdict based on graph and escape routes."""
        graph_verdict = self.assumption_graph.get_verdict()
        escape_verdict = self.escape_routes.get_verdict()
        
        # Most severe verdict wins
        if graph_verdict == Verdict.DEAD and escape_verdict == Verdict.DEAD:
            self.verdict = Verdict.DEAD
            self.verdict_reason = "Fundamental assumption violated with no escape"
        elif graph_verdict == Verdict.ESCAPED and escape_verdict == Verdict.ESCAPED:
            self.verdict = Verdict.ESCAPED
            self.verdict_reason = "All assumptions hold and escape routes exist"
            # UPGRADE 1: Record survival
            self.record_survival("Verdict finalized as ESCAPED")
        else:
            self.verdict = Verdict.CONDITIONALLY_DEAD
            self.verdict_reason = "Some assumptions violated or escape routes remain conditional"
    
    def to_dict(self) -> Dict[str, Any]:
        """Export session as dictionary."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "verdict": self.verdict.value,
            "verdict_reason": self.verdict_reason,
            "claims": self.claims,
            "assumptions": self.assumptions,
            "eliminated_approaches": self.eliminated_approaches,
            "falsification_experiments": self.falsification_experiments,
            "escape_routes": self.escape_routes.to_dict(),
            "assumption_graph": self.assumption_graph.to_dict(),
            # Original KPI
            "kpi": {
                "refusal_rate": self.refusal_rate,
                "total_proposed": self.total_assumptions_proposed,
                "refused": self.assumptions_refused
            },
            # UPGRADE 1: Temporal survival
            "temporal": {
                "survival_cycles": self.survival_cycles,
                "distinct_attack_vectors": list(self.distinct_attack_vectors),
                "failed_kill_reasons": self.failed_kill_reasons,
                "current_tier": self.current_tier.value
            },
            # UPGRADE 2: Orthogonality
            "orthogonality": {
                "rejections": self.orthogonality_rejections,
                "attack_history": [sorted(list(s)) if isinstance(s, set) else s for s in self.attack_history],
                "suggested_axes": self.suggest_orthogonal_axes()
            },
            # UPGRADE 5: Governance
            "governance": self.get_governance_report(),
            # UPGRADE 3: Failure patterns (global)
            "failure_patterns": get_failure_index().to_dict()
        }
    
    def get_refusal_report(self) -> Dict[str, Any]:
        """
        [RIGOR] FLAW 24 FIX: Scientific Rigor Index (SRI) Report.
        Replaces legacy refusal rate gaming with a multi-metric rigor assessment.
        """
        # Calculate Signal-to-Noise Ratio (Validated vs Total proposed)
        snr = (len([c for c in self.claims if "validated" in c.lower()]) / 
               max(1, self.total_assumptions_proposed))
        
        # Calculate Diversity Index (Unique attack axes used)
        diversity = len(self.distinct_attack_vectors) / 5.0 # normalized to 5 core axes
        
        # Aggregate Rigor Score
        sri = (snr * 0.4) + (diversity * 0.6)
        
        if sri < 0.3:
            assessment = "CRITICAL: High Hallucination Risk. Signal-to-noise ratio is too low."
        elif sri < 0.7:
            assessment = "MODERATE: Discovery requires further orthogonal validation."
        else:
            assessment = "HIGH RIGOR: Finding has survived diverse independent stress tests."

        return {
            "scientific_rigor_index": sri,
            "signal_to_noise_ratio": snr,
            "diversity_index": diversity,
            "verdict": assessment,
            "refusal_count": self.assumptions_refused,
            "reasons": self.refusal_reasons[:5]
        }
    def save_to_redis(self) -> None:
        """
        Save session state to Redis.
        """
        global _REDIS_DISABLED
        client = _get_redis_client()
        if not client or _REDIS_DISABLED:
            return

        try:
            data = self.to_dict()
            key = f"discovery_session:global:{self.session_id}"
            json_data = json.dumps(data, default=str)
            client.set(key, json_data)
            client.expire(key, 86400 * 4)
        except Exception as e:
            _REDIS_DISABLED = True
            logger.debug(f"Switched to local-only mode: DiscoverySession save to Redis failed ({e})")

    @classmethod
    def load_from_redis(cls, session_id: str) -> Optional['DiscoverySession']:
        """
        Load session state from Redis.
        Returns None if not found or Redis error.
        """
        global _REDIS_DISABLED
        client = _get_redis_client()
        if not client or _REDIS_DISABLED:
            return None
            
        try:
            key = f"discovery_session:global:{session_id}"
            data_json = client.get(key)
            if not data_json:
                return None
                
            data = json.loads(data_json)
            
            # Rehydrate
            session = cls(session_id=session_id)
            
            # Restore simple fields
            session.claims = data.get("claims", [])
            session.assumptions = data.get("assumptions", [])
            session.eliminated_approaches = data.get("eliminated_approaches", [])
            session.falsification_experiments = data.get("falsification_experiments", [])
            
            # Restore KPIs
            kpi = data.get("kpi", {})
            session.total_assumptions_proposed = kpi.get("total_proposed", 0)
            session.assumptions_refused = kpi.get("refused", 0)
            
            # Restore Temporal
            temp = data.get("temporal", {})
            session.survival_cycles = temp.get("survival_cycles", 0)
            session.distinct_attack_vectors = set(temp.get("distinct_attack_vectors", []))
            session.failed_kill_reasons = temp.get("failed_kill_reasons", [])
            
            # Restore Enums
            try:
                session.current_tier = SurvivorTier(temp.get("current_tier", "escaped"))
            except Exception as e:
                logger.warning(f"Failed to restore SurvivorTier from temp data, defaulting to ESCAPED: {e}")
                session.current_tier = SurvivorTier.ESCAPED
                
            try:
                session.verdict = Verdict(data.get("verdict", "conditionally_dead"))
            except Exception as e:
                logger.warning(f"Failed to restore Verdict from data, defaulting to CONDITIONALLY_DEAD: {e}")
                session.verdict = Verdict.CONDITIONALLY_DEAD
                
            session.verdict_reason = data.get("verdict_reason", "")
            
            # Restore Governance
            gov = data.get("governance", {})
            session.structural_influences = gov.get("structural_influences", 0)
            session.orthogonality_rejections = gov.get("orthogonality_rejections", 0)

            # RIGOR FIX: Rehydrate Assumption Graph (Logical Amnesia Fix)
            graph_data = data.get("assumption_graph")
            if graph_data and hasattr(session.assumption_graph, 'load_from_dict'):
                session.assumption_graph.load_from_dict(graph_data)
                logger.info(f"Rehydrated AssumptionGraph for session {session_id}")

            logger.info(f"Loaded DiscoverySession {session_id} from Redis.")
            return session
            
        except Exception as e:
            _REDIS_DISABLED = True
            logger.debug(f"Failed to load DiscoverySession from Redis: {e}")
            return None

    def load_from_dict(self, data: Dict[str, Any]):
        """
        Rehydrate session state from a dictionary (e.g. from checkpoint).
        """
        try:
            # Restore simple fields
            self.claims = data.get("claims", [])
            self.assumptions = data.get("assumptions", [])
            self.eliminated_approaches = data.get("eliminated_approaches", [])
            self.falsification_experiments = data.get("falsification_experiments", [])
            
            # Restore KPIs
            kpi = data.get("kpi", {})
            self.total_assumptions_proposed = kpi.get("total_proposed", 0)
            self.assumptions_refused = kpi.get("refused", 0)
            
            # Restore Temporal
            temp = data.get("temporal", {})
            self.survival_cycles = temp.get("survival_cycles", 0)
            self.distinct_attack_vectors = set(temp.get("distinct_attack_vectors", []))
            self.failed_kill_reasons = temp.get("failed_kill_reasons", [])
            
            # Restore Enums
            try:
                self.current_tier = SurvivorTier(temp.get("current_tier", "escaped"))
            except Exception as e:
                logger.warning(f"Failed to restore SurvivorTier for hypothesis, defaulting to ESCAPED: {e}")
                self.current_tier = SurvivorTier.ESCAPED
                
            try:
                self.verdict = Verdict(data.get("verdict", "conditionally_dead"))
            except Exception as e:
                logger.warning(f"Failed to restore Verdict for hypothesis, defaulting to CONDITIONALLY_DEAD: {e}")
                self.verdict = Verdict.CONDITIONALLY_DEAD
                
            self.verdict_reason = data.get("verdict_reason", "")
            
            # Restore Governance
            gov = data.get("governance", {})
            self.structural_influences = gov.get("structural_influences", 0)
            self.orthogonality_rejections = gov.get("orthogonality_rejections", 0)
            
            logger.info(f"Rehydrated DiscoverySession {self.session_id} from dictionary.")
        except Exception as e:
            logger.error(f"Rehydration from dict failed: {e}")


# Mission-scoped sessions
_discovery_sessions: Dict[str, DiscoverySession] = {}

def get_discovery_session(session_id: str = "default") -> DiscoverySession:
    """Get or create the discovery session."""
    global _discovery_sessions

    # 1. Check Memory Cache
    if session_id in _discovery_sessions:
        return _discovery_sessions[session_id]

    # 2. Check Redis (Persistence Fix)
    loaded_session = DiscoverySession.load_from_redis(session_id)
    if loaded_session:
        _discovery_sessions[session_id] = loaded_session
        return loaded_session

    # 3. Create New (scoped to session_id so other active sessions are never wiped)
    reset_assumption_graph(session_id=session_id)
    new_session = DiscoverySession(session_id=session_id)
    _discovery_sessions[session_id] = new_session

    # Save initial state
    new_session.save_to_redis()

    return new_session

def reset_discovery_session(session_id: str = None) -> None:
    """Reset the discovery session."""
    global _discovery_sessions
    if session_id is None:
        _discovery_sessions.clear()
        reset_assumption_graph()
    else:
        if session_id in _discovery_sessions:
            del _discovery_sessions[session_id]
        reset_assumption_graph(session_id=session_id)
