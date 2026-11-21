"""
Epistemic Regulator (Pillar 1: Discipline)
==========================================
**THE CONSCIENCE.**

THE DETERMINISTIC EPISTEMIC GOVERNOR
- Enforces discipline WITHOUT spending tokens
- Does NOT judge truth or decide verdictse
- Only SUGGESTS actions to orchestrator

Use Cases:
1.  **Stagnation Breaking**: "If we are stuck for 3 cycles, force a split into Pro/Con hypotheses."
2.  **Entropy Pruning**: "If a hypothesis has no new confirmed evidence for 5 cycles, decay its confidence."
3.  **Redundancy Merging**: "If two hypotheses are >85% similar (via embeddings), merge them to save resources."
4.  **Zero-Token Logic**: Does all of this without expensive LLM calls, using pure Python rules.

GODZILLA-TIER UPGRADES:
- Upgrade 1: HypothesisTrajectory awareness (confidence slope, evidence rate)
- Upgrade 2: Causal-safe merge check (don't merge hypotheses that refute each other)
- Upgrade 3: Structured mutation operators (boundary, regime, latent variable)
- Upgrade 4: Formalized action contract (strict action_type enum)
- Upgrade 5: Meta-regulation (throttle if system unstable)

It keeps the system honest.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from enum import Enum
import numpy as np
from dataclasses import dataclass, field

from backend.core.hypothesis.models import Hypothesis, HypothesisState
from backend.discovery.constants import ScientificDefaults

logger = logging.getLogger(__name__)


# =============================================================================
# THE EPISTEMIC REAPER (Consolidated into Regulator Beast)
# =============================================================================

class ReaperUpdateType(str, Enum):
    """Refined categories for belief updates."""
    CONFIRMATION = "confirmation"  # Data supports existing model
    CONFLICT = "conflict"          # Data contradicts existing model
    PRUNING = "pruning"            # Hypothesis refuted/removed
    NEUTRAL = "neutral"            # No significant change


@dataclass
class ReaperResult:
    """The outcome of an epistemic audit."""
    success: bool
    update_type: ReaperUpdateType
    reasoning: str = ""
    affected_keys: List[str] = field(default_factory=list)
    confidence_delta: float = 0.0
    action_taken: str = "none"
    target_hypothesis_id: Optional[str] = None


class EpistemicReaper:
    """
    The Epistemic Reaper: Unifies SVEL's statistical rigor with SVEL's clash logic.
    Stalks the WorldModel for empirical contradictions.
    """
    
    def __init__(self, world_model: Any = None):
        self.world_model = world_model
        logger.info(" Epistemic Reaper attached and stalking.")

    def audit_statistical_clash(self, new_stats: Dict[str, Any], existing_stats: Dict[str, Any]) -> Optional[ReaperResult]:
        """
        Implements the high-precision port of SVEL's conflict math using Welch's t-test and Z-scores.
        """
        import scipy.stats as stats
        
        def _extract_eff(d: Dict[str, Any]) -> float:
            for k in ("effect_size", "cohens_d", "cohen_d", "observed_diff", "t_stat", "r_squared"):
                if d.get(k) is not None:
                    try:
                        return float(d[k])
                    except (ValueError, TypeError):
                        pass
            return 0.0

        new_effect = _extract_eff(new_stats)
        old_effect = _extract_eff(existing_stats)
        new_p = new_stats.get("p_value")
        old_p = existing_stats.get("p_value")
        new_se = new_stats.get("standard_error") or new_stats.get("se")
        old_se = existing_stats.get("standard_error") or existing_stats.get("se")

        def get_se(effect, p_val, se_val, stats_dict=None):
            if se_val is not None and float(se_val) > 0:
                return float(se_val)
            if stats_dict:
                sd = stats_dict.get("std") or stats_dict.get("sd")
                n_obs = stats_dict.get("n") or stats_dict.get("sample_size")
                if sd is not None and n_obs is not None and float(n_obs) > 1 and float(sd) > 0:
                    return float(sd) / np.sqrt(float(n_obs))
            if p_val is not None:
                p = float(p_val)
                p = max(1e-15, min(p, 1.0 - 1e-15))
                z = stats.norm.ppf(1.0 - p / 2.0)
                if z > 0:
                    return abs(float(effect)) / z
            # Conservative uncalibrated prior (CV=0.50) to avoid false Welch-Z refutations when SE and p are unknown
            return 0.5 * abs(float(effect)) if float(effect) != 0 else 0.10

        new_se = get_se(new_effect, new_p, new_se, new_stats)
        old_se = get_se(old_effect, old_p, old_se, existing_stats)

        # 1. Welch-Z test for difference between two independent estimates
        if new_se > 0 and old_se > 0:
            z_score = abs(new_effect - old_effect) / np.sqrt(new_se**2 + old_se**2)
            if z_score > 2.576: # p < 0.01 significance level
                return ReaperResult(
                    success=True,
                    update_type=ReaperUpdateType.CONFLICT,
                    reasoning=f"Statistical divergence: Welch-Z of difference is {z_score:.3f} (p < 0.01). New: {new_effect:.3f}±{new_se:.3f} vs Existing: {old_effect:.3f}±{old_se:.3f}",
                    action_taken="flag_key"
                )

        # 2. Directional Conflict as a secondary check
        if new_effect != 0 and old_effect != 0 and (new_effect * old_effect < 0):
            return ReaperResult(
                success=True,
                update_type=ReaperUpdateType.CONFLICT,
                reasoning=f"Directional Conflict: New effect ({new_effect:.3f}) opposes existing ({old_effect:.3f})",
                action_taken="flag_key"
            )

        # 3. Significance discrepancy check
        if new_p is not None and old_p is not None:
            new_p = float(new_p)
            old_p = float(old_p)
            alpha = ScientificDefaults.ALPHA_SIGNIFICANCE
            new_sig = new_p < alpha
            old_sig = old_p < alpha
            
            significant_discrepancy = (new_p < 0.01 and old_p > 0.10) or (old_p < 0.01 and new_p > 0.10)
            directional_discrepancy = (new_sig != old_sig) and (new_effect * old_effect < 0)
            
            if significant_discrepancy or directional_discrepancy:
                return ReaperResult(
                    success=True,
                    update_type=ReaperUpdateType.CONFLICT,
                    reasoning=f"Significance Clash: New p={new_p:.4f} vs Old p={old_p:.4f} with incompatible effect directions or extreme delta.",
                    action_taken="flag_key"
                )
        
        return None

    def assess_intuition(self, edge: Any) -> float:
        """
        GODZILLA UPGRADE: Judge a GNN 'Hunch'.
        Returns a score (0.0-1.0) indicating whether this intuition is worth pursuing.
        """
        # 1. Contradiction Check (Placeholder for V1)
        # Does this edge contradict known facts?
        # if self.world_model.contradicts(edge): return 0.0
        
        # 2. Confidence Calibration
        
        confidence = float(edge.confidence)
        
        # [TITAN V177.0] BAYESIAN DAMPING (NON-HEURISTIC)
        # Physically abolish the degree-based maturity fraud.
        # Utilize the GNN's stochastic uncertainty (sigma) to damp confidence.
        uncertainty = getattr(edge, "uncertainty", 0.0)
        
        # High uncertainty physically reduces trust in the hunch.
        # 1.0 / (1 + sigma) provides a mathematically grounded damping manifold.
        damping = 1.0 / (1.0 + uncertainty)
        return confidence * damping


        
    def reconcile_finding(self, finding: Dict[str, Any], context: List[Dict[str, Any]]) -> ReaperResult:
        """
        Audit a new finding against a list of related findings in the WorldModel.
        """
        new_stats = finding.get("statistics", {})
        metadata = finding.get("metadata", {})
        target_hyp_id = metadata.get("hypothesis_id") or finding.get("hypothesis_id")
        
        highest_clash: Optional[ReaperResult] = None
        
        for existing in context:
            # Context items from WorldModel are dicts converted from Fact objects
            # Fact.to_dict() puts statistics inside 'metadata' or 'statistics' field
            existing_stats = existing.get("statistics")
            if not existing_stats and "metadata" in existing:
                existing_stats = existing.get("metadata", {}).get("statistics")
            
            if not existing_stats:
                # Fallback to scanning for p_value directly in metadata
                meta = existing.get("metadata", {})
                if "p_value" in meta or "effect_size" in meta:
                    existing_stats = meta
            
            if not existing_stats:
                continue

            clash = self.audit_statistical_clash(new_stats, existing_stats)
            if clash:
                highest_clash = clash
                highest_clash.target_hypothesis_id = target_hyp_id
                
                # If a clash is detected AND we have a target hypothesis,
                # we should elevate this to PRUNING to ensure it gets killed.
                if target_hyp_id:
                    highest_clash.update_type = ReaperUpdateType.PRUNING
                    highest_clash.action_taken = "prune_hypothesis"
                    highest_clash.reasoning += f" (Refuting Hypothesis {target_hyp_id})"
                break
        
        if highest_clash:
            logger.warning(f" Reaper found a soul: {highest_clash.reasoning}")
            return highest_clash
            
        # Check for Pruning (direct refutation)
        if finding.get("refutes_hypothesis") or finding.get("metadata", {}).get("refutes_hypothesis"):
            return ReaperResult(
                success=True,
                update_type=ReaperUpdateType.PRUNING,
                reasoning="Hypothesis explicitly refuted by finding.",
                action_taken="prune_hypothesis",
                target_hypothesis_id=target_hyp_id
            )

        return ReaperResult(
            success=True,
            update_type=ReaperUpdateType.CONFIRMATION,
            reasoning="Finding is epistemically consistent.",
            action_taken="merge"
        )



# =============================================================================
# UPGRADE 4: FORMALIZED ACTION CONTRACT (Strict action_type enum)
# =============================================================================

class ActionType(Enum):
    """
    Strict contract between Regulator  Orchestrator.
    Prevents silent misinterpretation.
    """
    SPAWN_VARIANTS = "spawn_variants"      # Create hypothesis variants
    DECAY_CONFIDENCE = "decay_confidence"  # Reduce hypothesis confidence
    MERGE_HYPOTHESES = "merge_hypotheses"  # Combine similar hypotheses
    FORCE_ATTACK = "force_attack"          # Force falsification attempt
    ARCHIVE = "archive"                    # Move to archive (inactive)
    THROTTLE = "throttle"                  # Meta: slow down the system
    BOOST = "boost"                        # Increase confidence
    REFUTE = "refute"                      # ACTIVE PRUNING: Kill hypothesis via Reaper
    INVESTIGATE = "investigate"            # SYNTHESIS: Deep dive into contradiction instead of instant kill



@dataclass
class EpistemicAction:
    """
    Action suggested by regulator for orchestrator to execute.
    """
    action_type: ActionType  # UPGRADE 4: Now strict enum, not str
    target_ids: List[str]
    reason: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# =============================================================================
# UPGRADE 1: HYPOTHESIS TRAJECTORY AWARENESS
# =============================================================================

@dataclass
class HypothesisTrajectory:
    """
    Track hypothesis evolution over time for smarter regulation.
    
    Enables:
    - Decay only if confidence slope is flat
    - Split only if no structural movement
    
    Multiplier: ~3 better regulation
    """
    hypothesis_id: str
    confidence_history: List[float] = field(default_factory=list)
    evidence_count_history: List[int] = field(default_factory=list)
    cycle_history: List[int] = field(default_factory=list) # [TITAN V142.0] Track temporal dimension
    last_updated_cycle: int = 0
    created_cycle: int = 0
    attack_count: int = 0
    survival_count: int = 0
    
    def add_snapshot(self, confidence: float, evidence_count: int, cycle: int) -> None:
        """Record current state (upsert if called multiple times in the same cycle)."""
        if self.cycle_history and self.cycle_history[-1] == cycle:
            self.confidence_history[-1] = confidence
            self.evidence_count_history[-1] = evidence_count
        else:
            self.confidence_history.append(confidence)
            self.evidence_count_history.append(evidence_count)
            self.cycle_history.append(cycle)
        self.last_updated_cycle = cycle
    
    def get_confidence_slope(self, window: int = 5) -> float:
        """
        [TITAN V202.0] BOUNDED EPISTEMIC DERIVATIVE
        Physically abolished OLS on bounded probabilities.
        Uses Log-Odds (Logit) transformation for mathematically sovereign rate-of-change.
        """
        if len(self.confidence_history) < 2:
            return 0.0
        
        recent_conf = self.confidence_history[-window:]
        recent_cycles = self.cycle_history[-window:]
        
        if len(recent_conf) < 2:
            return 0.0
        
        import numpy as np
        x = np.array(recent_cycles)
        
        # Logit transform to project [0, 1] onto [-inf, inf]
        # Clip to prevent log(0)
        p = np.clip(recent_conf, 1e-5, 1.0 - 1e-5)
        y = np.log(p / (1.0 - p))
        
        x = x - x[0] # Shift
        
        n = len(x)
        denominator = (n * np.sum(x**2) - (np.sum(x))**2)
        if denominator == 0:
            return 0.0
        
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / denominator
        return float(slope)
    
    def get_evidence_rate(self, window: int = 5) -> float:
        """
        [TITAN V142.0] Evidence Velocity.
        d(Evidence)/d(Cycle).
        """
        if len(self.evidence_count_history) < 2:
            return 0.0
        
        recent_ev = self.evidence_count_history[-window:]
        recent_cycles = self.cycle_history[-window:]
        
        cycle_delta = recent_cycles[-1] - recent_cycles[0]
        if cycle_delta <= 0:
            return 0.0
        
        return (recent_ev[-1] - recent_ev[0]) / float(cycle_delta)

    
    def is_stagnant(self, slope_threshold: float = 0.01, cycles_threshold: int = 3) -> bool:
        """Check if hypothesis is stagnant (no structural movement)."""
        slope = abs(self.get_confidence_slope())
        evidence_rate = self.get_evidence_rate()
        
        return slope < slope_threshold and evidence_rate < 0.5
    
    def cycles_since_update(self, current_cycle: int) -> int:
        """How many cycles since last update?"""
        return current_cycle - self.last_updated_cycle


# =============================================================================
# UPGRADE 5: META-REGULATION (System Stability Tracking)
# =============================================================================

@dataclass
class MetaRegulationStats:
    """
    Second-order epistemic control.
    
    Track:
    - actions per cycle
    - merges per cycle
    - decays per cycle
    
    If too high  throttle mutation, raise merge threshold, pause spawning.
    
    Multiplier: ~10 long-run stability
    """
    actions_per_cycle: List[int] = field(default_factory=list)
    merges_per_cycle: List[int] = field(default_factory=list)
    decays_per_cycle: List[int] = field(default_factory=list)
    spawns_per_cycle: List[int] = field(default_factory=list)
    
    # Thresholds
    max_actions_per_cycle: int = 5
    max_merges_per_cycle: int = 2
    max_decays_per_cycle: int = 3
    
    def record_cycle(self, actions: int, merges: int, decays: int, spawns: int):
        """Record stats for this cycle."""
        self.actions_per_cycle.append(actions)
        self.merges_per_cycle.append(merges)
        self.decays_per_cycle.append(decays)
        self.spawns_per_cycle.append(spawns)
    
    def is_system_unstable(self, window: int = 3) -> bool:
        """Check if system is triggering too many actions (unstable)."""
        if len(self.actions_per_cycle) < window:
            return False
        
        recent_actions = self.actions_per_cycle[-window:]
        avg_actions = sum(recent_actions) / len(recent_actions)
        
        return avg_actions > self.max_actions_per_cycle
    
    def should_throttle_spawning(self, window: int = 3) -> bool:
        """Should we pause hypothesis spawning?"""
        if len(self.spawns_per_cycle) < window:
            return False
        
        recent = self.spawns_per_cycle[-window:]
        return sum(recent) > window * 2  # More than 2 spawns/cycle average
    
    def should_raise_merge_threshold(self, window: int = 3) -> bool:
        """Should we be more conservative about merging?"""
        if len(self.merges_per_cycle) < window:
            return False
        
        recent = self.merges_per_cycle[-window:]
        return sum(recent) > self.max_merges_per_cycle * window
    
    def get_throttle_factor(self) -> float:
        """
        Return throttle factor (0.0 = full throttle, 1.0 = no throttle).
        Used to reduce action frequency when system is unstable.
        """
        if not self.is_system_unstable():
            return 1.0
        
        # Calculate how unstable
        recent = self.actions_per_cycle[-3:] if len(self.actions_per_cycle) >= 3 else self.actions_per_cycle
        avg = sum(recent) / len(recent) if recent else 0
        
        # More actions = more throttle
        if avg > self.max_actions_per_cycle * 2:
            return 0.3  # Heavy throttle
        elif avg > self.max_actions_per_cycle:
            return 0.6  # Medium throttle
        return 1.0


# =============================================================================
# UPGRADE 3: STRUCTURED MUTATION OPERATORS (Zero-token, high-yield)
# =============================================================================

class Mutator:
    """
    Pillar 1 Helper: Deterministic Hypothesis Evolution.
    
    UPGRADED with structured mutations:
    - Boundary mutation: "only valid if X < threshold"
    - Regime isolation: "fails under condition A but holds under B"
    - Latent variable injection: "assuming hidden factor Z exists"
    
    Still zero-token, still deterministic, much higher yield.
    
    Multiplier: ~8-10
    """
    
    # === ORIGINAL MUTATIONS ===
    
    @staticmethod
    def invert(statement: str) -> str:
        """Naive negation injection"""
        if " not " in statement:
            return statement.replace(" not ", " ")
        return f"Refutation: {statement} is FALSE"

    @staticmethod
    def parameterize(statement: str, param: str) -> str:
        """Inject specific context"""
        return f"{statement} (specifically considering {param})"

    @staticmethod
    def intensify(statement: str) -> str:
        """Raise the stakes"""
        return f"CRITICAL: {statement}"
    
    # === UPGRADE 3: NEW STRUCTURED MUTATIONS ===
    
    @staticmethod
    def boundary_mutation(statement: str, variable: str = "X", threshold: str = "threshold") -> str:
        """
        Boundary mutation: "only valid if X < threshold"
        Tests edge cases where hypothesis might break.
        """
        return f"{statement} [BOUNDARY: only valid if {variable} < {threshold}]"
    
    @staticmethod
    def regime_isolation(statement: str, condition_a: str = "extreme conditions", 
                         condition_b: str = "normal conditions") -> str:
        """
        Regime isolation: "fails under condition A but holds under B"
        Separates regimes where hypothesis behaves differently.
        """
        return f"{statement} [REGIME: fails under {condition_a}, holds under {condition_b}]"
    
    @staticmethod
    def latent_variable_injection(statement: str, hidden_factor: str = "Z") -> str:
        """
        Latent variable injection: "assuming hidden factor Z exists"
        Introduces confounding variables that might explain observations.
        """
        return f"{statement} [LATENT: assuming hidden factor {hidden_factor} controls this]"
    
    @staticmethod
    def constraint_addition(statement: str, constraint: str = "energy conservation") -> str:
        """Add a physical/logical constraint."""
        return f"{statement} [CONSTRAINT: must satisfy {constraint}]"
    
    @staticmethod
    def temporal_restriction(statement: str, timeframe: str = "initial phase") -> str:
        """Restrict to specific time period."""
        return f"{statement} [TEMPORAL: applies only during {timeframe}]"
    
    @staticmethod
    def get_all_mutations(statement: str) -> List[str]:
        """Generate all mutation variants for a statement."""
        return [
            Mutator.invert(statement),
            Mutator.parameterize(statement, "unexpected edge cases"),
            Mutator.intensify(statement),
            Mutator.boundary_mutation(statement, "key_parameter", "critical_limit"),
            Mutator.regime_isolation(statement, "high stress", "normal operation"),
            Mutator.latent_variable_injection(statement, "confounding_factor"),
        ]


# =============================================================================
# MAIN: EPISTEMIC REGULATOR (Enhanced with all 5 upgrades)
# =============================================================================

class EpistemicRegulator:
    """
    THE DETERMINISTIC EPISTEMIC GOVERNOR.
    
    Does NOT:
    - Call LLMs
    - Judge truth
    - Decide verdicts
    - Hallucinate theory
    
    Only SUGGESTS actions.
    """
    
    def __init__(self, merge_threshold: float = 0.85):
        self.merge_threshold = merge_threshold
        
        self.model = None
        
        # UPGRADE 1: Trajectory tracking
        self.trajectories: Dict[str, HypothesisTrajectory] = {}
        
        # UPGRADE 5: Meta-regulation stats
        self.meta_stats = MetaRegulationStats()
        
        # Load embedding model via shared singleton (respects offline cache to avoid HF Hub hangs)
        try:
            from backend.core.world_model import get_shared_embedding_model
            self.model = get_shared_embedding_model()
            if self.model:
                logger.info("EpistemicRegulator: Connected to shared embedding model.")
            else:
                logger.info("EpistemicRegulator: Shared embedding model offline; using lexical-Jaccard merge fallback.")
        except Exception as e:
            logger.warning(f"EpistemicRegulator: Model load error: {e}")
    
    def regulate(self, hypotheses: List[Hypothesis], current_cycle: int) -> List[EpistemicAction]:
        """
        Apply deterministic rules to the hypothesis set.
        Returns a list of actions for the orchestrator to execute.
        
        UPGRADED with:
        - Trajectory awareness (don't decay if improving)
        - Meta-regulation (throttle if unstable)
        - Formalized action types
        """
        actions = []
        active_hypotheses = [h for h in hypotheses if h.state not in [HypothesisState.ARCHIVED, HypothesisState.REFUTED]]
        
        # WIRING FIX: Log hypotheses without formal structure
        for h in active_hypotheses:
            if not getattr(h, 'is_formally_complete', False):
                logger.debug(f"[FORMAL GUARD] Hypothesis {h.id} lacks formal structure (no variables/predictions)")
        
        # UPGRADE 1: Update trajectories
        for h in active_hypotheses:
            self._update_trajectory(h, current_cycle)
        
        # UPGRADE 5: Check system stability
        throttle_factor = self.meta_stats.get_throttle_factor()
        if throttle_factor < 1.0:
            logger.warning(f"[META-REGULATION] System unstable, throttle={throttle_factor:.2f}")
        
        # Rule 1: Zero-Token Spawning (Stagnation Breaker)
        spawned_ids = set()
        if not self.meta_stats.should_throttle_spawning():
            spawn_actions = self._check_stagnation_spawning(active_hypotheses, current_cycle)
            for a in spawn_actions:
                spawned_ids.update(a.target_ids)
            actions.extend(spawn_actions)
        
        # Rule 2: Confidence Decay (Entropy) - UPGRADED with trajectory awareness
        # PHASE 42: HARD EXECUTION GATES (Operation "Reality Check")
        # ACTION CONFLICT FIX: Don't decay if we JUST split/spawned variants (give them a chance)
        decay_candidates = [h for h in active_hypotheses if h.id not in spawned_ids]
        decay_actions = self._check_decay(decay_candidates, current_cycle)
        actions.extend(decay_actions)

        # Rule 2.5: Confidence Ceiling (Force Experimentation)
        ceiling_actions = self._check_confidence_ceiling(decay_candidates)
        actions.extend(ceiling_actions)
        
        # Rule 3: Merge Redundant (SentenceTransformer or deterministic token-similarity fallback) - UPGRADED with causal-safe check
        if len(active_hypotheses) > 1:
            if not self.meta_stats.should_raise_merge_threshold():
                merge_actions = self._check_merges(active_hypotheses)
            else:
                # Use higher threshold if system is merge-heavy
                merge_actions = self._check_merges(active_hypotheses, threshold_boost=0.05)
            actions.extend(merge_actions)
        
        # UPGRADE 5: Record meta-stats
        spawn_count = sum(1 for a in actions if a.action_type == ActionType.SPAWN_VARIANTS)
        merge_count = sum(1 for a in actions if a.action_type == ActionType.MERGE_HYPOTHESES)
        decay_count = sum(1 for a in actions if a.action_type == ActionType.DECAY_CONFIDENCE)
        self.meta_stats.record_cycle(len(actions), merge_count, decay_count, spawn_count)
        
        # UPGRADE 5: Add throttle action if unstable
        if self.meta_stats.is_system_unstable():
            actions.append(EpistemicAction(
                action_type=ActionType.THROTTLE,
                target_ids=[],
                reason="meta_regulation_instability",
                metadata={"throttle_factor": throttle_factor}
            ))
        
        return actions
    
    def _update_trajectory(self, h: Hypothesis, current_cycle: int) -> None:
        """UPGRADE 1: Update hypothesis trajectory."""
        if h.id not in self.trajectories:
            self.trajectories[h.id] = HypothesisTrajectory(
                hypothesis_id=h.id,
                created_cycle=current_cycle
            )
        
        trajectory = self.trajectories[h.id]
        evidence_count = len(h.evidence) if h.evidence else 0
        trajectory.add_snapshot(h.confidence, evidence_count, current_cycle)
    
    def _check_stagnation_spawning(self, hypotheses: List[Hypothesis], current_cycle: int) -> List[EpistemicAction]:
        """Rule 1: Stagnation breaking with trajectory awareness."""
        actions = []
        
        if len(hypotheses) == 1 and current_cycle >= 3:
            target = hypotheses[0]
            if target.state in [HypothesisState.PROPOSED, HypothesisState.TESTING]:
                # UPGRADE 1: Only split if trajectory is stagnant
                trajectory = self.trajectories.get(target.id)
                
                should_split = True
                if trajectory and not trajectory.is_stagnant():
                    # Hypothesis is still evolving, don't split yet
                    should_split = False
                    logger.info(f"[TRAJECTORY] {target.id} still evolving, skipping split")
                
                if should_split:
                    logger.info(f"Epistemic Rule Triggered: Stagnation Split on {target.id}")
                    
                    # UPGRADE 3: Enhanced mutations
                    mutants = Mutator.get_all_mutations(target.statement)
                    
                    actions.append(EpistemicAction(
                        action_type=ActionType.SPAWN_VARIANTS,
                        target_ids=[target.id],
                        reason="stagnation_single_hypothesis_mutation",
                        metadata={"variants": mutants}
                    ))
        
        return actions
    
    def _check_decay(self, hypotheses: List[Hypothesis], current_cycle: int) -> List[EpistemicAction]:
        """
        Rule 2: Confidence decay with trajectory awareness.
        
        UPGRADED: Only decay if confidence slope is FLAT, not if improving.
        WIRING FIX: Also consider formal prediction test status.
        """
        actions = []
        
        if current_cycle >= 5:
            for h in hypotheses:
                trajectory = self.trajectories.get(h.id)
                
                # WIRING FIX: Check both evidence and formal predictions
                has_evidence = bool(h.evidence)
                is_tested = getattr(h, 'is_tested', False)
                
                # Decay if: no evidence AND not formally tested AND still confident
                if not has_evidence and not is_tested and h.confidence > 0.3:
                    # UPGRADE 1: Check trajectory before decay
                    should_decay = True
                    
                    if trajectory:
                        slope = trajectory.get_confidence_slope()
                        if slope > 0.01:
                            # Confidence is improving, don't decay
                            should_decay = False
                            logger.info(f"[TRAJECTORY] {h.id} improving (slope={slope:.3f}), skipping decay")
                    
                    if should_decay:
                        # PHASE 42: Steeper decay for hypotheses lacking reality checks
                        has_experiment = h.metadata.get("experiment_run", False)
                        decay_amount = 0.25 if not has_experiment and h.confidence > 0.8 else 0.15
                        
                        actions.append(EpistemicAction(
                            action_type=ActionType.DECAY_CONFIDENCE,
                            target_ids=[h.id],
                            reason="stale_no_evidence" + ("_no_reality_check" if not has_experiment else ""),
                            metadata={"decay_amount": decay_amount}
                        ))
        
        return actions
    
    def _check_confidence_ceiling(self, hypotheses: List[Hypothesis]) -> List[EpistemicAction]:
        actions = []
        for h in hypotheses:
            if h.state == HypothesisState.CONFIRMED or (h.metadata and h.metadata.get("test_verdict") == "CONFIRMED"):
                continue
            ev_len = len(h.evidence) if h.evidence else 0
            sup_len = len(getattr(h, "supporting_evidence", []) or [])
            exp_bonus = 3 if (h.metadata and h.metadata.get("experiment_run")) else 0
            evidence_count = max(ev_len, sup_len) + exp_bonus
            max_conf = min(0.5 + 0.1 * evidence_count, 0.95)
            if h.confidence > max_conf:
                actions.append(EpistemicAction(
                    action_type=ActionType.DECAY_CONFIDENCE,
                    target_ids=[h.id],
                    reason="confidence_ceiling_exceeded",
                    metadata={"decay_amount": h.confidence - max_conf}
                ))
        return actions

    def _check_merges(self, hypotheses: List[Hypothesis], threshold_boost: float = 0.0) -> List[EpistemicAction]:
        """
        Rule 3: Merge redundant hypotheses.
        
        UPGRADED with causal-safe check:
        - Don't merge if hypotheses refute each other
        - Check evidence direction compatibility
        """
        actions = []
        
        # Dynamic threshold with meta-regulation boost
        effective_threshold = self.merge_threshold + threshold_boost
        
        # Compute embeddings (or fallback to deterministic token sets when offline)
        texts = [f"{h.statement} {getattr(h, 'rationale', '')}" for h in hypotheses]
        embeddings = None
        if self.model is not None:
            try:
                embeddings = self.model.encode(texts)
            except Exception as e:
                logger.debug(f"EpistemicRegulator encoding fallback triggered: {e}")
                embeddings = None
        
        # Pairwise check
        processed = set()
        for i in range(len(hypotheses)):
            for j in range(i + 1, len(hypotheses)):
                if i in processed or j in processed:
                    continue
                
                if embeddings is not None:
                    # Cosine similarity (with zero-norm guard)
                    norm_i = float(np.linalg.norm(embeddings[i]))
                    norm_j = float(np.linalg.norm(embeddings[j]))
                    if norm_i < 1e-12 or norm_j < 1e-12:
                        continue
                    sim = float(np.dot(embeddings[i], embeddings[j])) / (norm_i * norm_j)
                else:
                    t1 = {w for w in texts[i].lower().split() if len(w) > 2}
                    t2 = {w for w in texts[j].lower().split() if len(w) > 2}
                    if not t1 or not t2:
                        continue
                    sim = len(t1 & t2) / float(len(t1 | t2))
                
                if sim > effective_threshold:
                    h1 = hypotheses[i]
                    h2 = hypotheses[j]
                    
                    # UPGRADE 2: Causal-safe merge check
                    if self._hypotheses_refute_each_other(h1, h2):
                        logger.warning(f"[CAUSAL-SAFE] Blocking merge of {h1.id} & {h2.id} - they refute each other")
                        continue
                    
                    if not self._evidence_direction_compatible(h1, h2):
                        logger.warning(f"[CAUSAL-SAFE] Blocking merge of {h1.id} & {h2.id} - incompatible evidence")
                        continue
                    
                    logger.info(f"Epistemic Rule Triggered: Merge {h1.id} & {h2.id} (Sim: {sim:.2f})")
                    actions.append(EpistemicAction(
                        action_type=ActionType.MERGE_HYPOTHESES,
                        target_ids=[h1.id, h2.id],
                        reason=f"high_similarity_{sim:.2f}",
                        metadata={"dominant_id": h1.id if len(h1.evidence) >= len(h2.evidence) else h2.id}
                    ))
                    processed.add(j)
        
        return actions
    
    def _hypotheses_refute_each_other(self, h1: Hypothesis, h2: Hypothesis) -> bool:
        s1, s2 = h1.statement.lower(), h2.statement.lower()
        words1, words2 = set(s1.split()), set(s2.split())
        if not words1 or not words2:
            return False
        overlap = len(words1.intersection(words2)) / max(1, min(len(words1), len(words2)))
        if overlap > 0.5:
            if ("increases" in s1 and "decreases" in s2) or ("decreases" in s1 and "increases" in s2):
                return True
            has_neg1 = any(n in words1 for n in ["not", "never", "false", "fails"])
            has_neg2 = any(n in words2 for n in ["not", "never", "false", "fails"])
            if has_neg1 != has_neg2:
                return True
        return False
    def _evidence_direction_compatible(self, h1: Hypothesis, h2: Hypothesis) -> bool:
        """
        UPGRADE 2: Check if evidence directions are compatible.
        
        If h1 has supporting evidence and h2 has refuting evidence for same claim,
        they should not be merged.
        """
        # If neither has evidence, they're compatible
        if not h1.evidence and not h2.evidence:
            return True
        
        # If only one has evidence, they're compatible
        if not h1.evidence or not h2.evidence:
            return True
        
        # Check for opposing evidence types
        h1_types = set()
        h2_types = set()
        
        for e in h1.evidence:
            # Handle both Dict and Evidence object
            if isinstance(e, dict):
                 etype = e.get("type", "")
            else:
                 etype = getattr(e, "type", "")
            
            etype = str(etype).lower()
            
            if "support" in etype or "confirm" in etype:
                h1_types.add("support")
            elif "refute" in etype or "contradict" in etype:
                h1_types.add("refute")
        
        for e in h2.evidence:
            # Handle both Dict and Evidence object
            if isinstance(e, dict):
                 etype = e.get("type", "")
            else:
                 etype = getattr(e, "type", "")
            
            etype = str(etype).lower()

            if "support" in etype or "confirm" in etype:
                h2_types.add("support")
            elif "refute" in etype or "contradict" in etype:
                h2_types.add("refute")
        
        # If one has only support and other has only refute, incompatible
        if h1_types == {"support"} and h2_types == {"refute"}:
            return False
        if h1_types == {"refute"} and h2_types == {"support"}:
            return False
        
        return True
    
    def get_trajectory(self, hypothesis_id: str) -> Optional[HypothesisTrajectory]:
        """Get trajectory for a hypothesis."""
        return self.trajectories.get(hypothesis_id)
    
    def get_meta_stats(self) -> Dict[str, Any]:
        """Get meta-regulation statistics."""
        return {
            "total_cycles": len(self.meta_stats.actions_per_cycle),
            "avg_actions_per_cycle": (
                sum(self.meta_stats.actions_per_cycle) / len(self.meta_stats.actions_per_cycle)
                if self.meta_stats.actions_per_cycle else 0
            ),
            "is_unstable": self.meta_stats.is_system_unstable(),
            "throttle_factor": self.meta_stats.get_throttle_factor(),
            "should_raise_merge_threshold": self.meta_stats.should_raise_merge_threshold(),
            "should_throttle_spawning": self.meta_stats.should_throttle_spawning(),
        }

    def reset(self) -> None:
        """
        Clear all session-specific state.
        MUST be called when starting a new research session to prevent
        trajectories and meta-stats from a previous run contaminating the next.
        """
        self.trajectories.clear()
        self.meta_stats = MetaRegulationStats()
        logger.info(f"[EPISTEMIC_REGULATOR] Reset: trajectories and meta-stats cleared.")

