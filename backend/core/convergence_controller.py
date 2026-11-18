"""
Convergence Controller
======================
PCD Pillar 5: Autonomous Stop Logic.

Decides when to stop the research session based on epistemic state,
rather than arbitrary limits.
"""

import logging
from typing import List, Dict, Optional
from backend.core.hypothesis.models import Hypothesis, HypothesisState

logger = logging.getLogger(__name__)

class ConvergenceController:
    def __init__(
        self, 
        stagnation_threshold: int = 25, 
        confidence_threshold: float = 0.85,
        min_cycles_before_saturation: int = 15  # Guard rail: don't check saturation in early cycles
    ):
        self.stagnation_threshold = stagnation_threshold
        self.confidence_threshold = confidence_threshold
        self.min_cycles_before_saturation = min_cycles_before_saturation
        self.stagnation_counter = 0
        self.last_hypotheses_hash = ""

    async def check_convergence(self, cycle: int, hypotheses: List[Hypothesis]) -> Optional[str]:
        """
        Check if research should stop.
        Returns stopping reason string or None.
        """
        # 1. Check Stagnation (Information Gain Plateau)
        # Skip stagnation tracking on the very first cycle or when no hypotheses exist
        # to prevent premature termination during initial exploration.
        current_hash = self._compute_hypothesis_hash(hypotheses)
        if cycle == 0 or not hypotheses:
            # Initial exploration phase — never count as stagnation
            self.last_hypotheses_hash = current_hash
        elif current_hash == self.last_hypotheses_hash:
            self.stagnation_counter += 1
        else:
            self.stagnation_counter = 0
            self.last_hypotheses_hash = current_hash
            
        if self.stagnation_counter >= self.stagnation_threshold:
            return f"Exploration Plateau: No hypothesis updates for {self.stagnation_counter} cycles."

        # 2. Check Epistemic Saturation (Confidence Convergence)
        # PHASE 3 FIX: Re-enabled with guard rail (only after min_cycles_before_saturation)
        if cycle >= self.min_cycles_before_saturation:
            active_states = {
                HypothesisState.TESTING, HypothesisState.PROPOSED,
                HypothesisState.NOVEL, HypothesisState.PRIORITIZED,
                "testing", "proposed", "novel", "prioritized"
            }
            active = []
            for h in hypotheses:
                h_state = h.get("state") if isinstance(h, dict) else getattr(h, "state", None)
                h_state_val = h_state.value if hasattr(h_state, "value") else h_state
                if h_state in active_states or h_state_val in active_states:
                    active.append(h)
            
            if not active and len(hypotheses) > 0:
                 return "Epistemic Saturation: All hypotheses resolved."
             
            def _is_decisive(h):
                meta = h.get("metadata", {}) if isinstance(h, dict) else (getattr(h, "metadata", None) or {})
                conf = (h.get("confidence") if isinstance(h, dict) else getattr(h, "confidence", None)) or 0.0
                return bool(meta.get("experiment_run", False)) and (
                    conf >= self.confidence_threshold or conf <= (1.0 - self.confidence_threshold)
                )

            if active and all(_is_decisive(h) for h in active):
                return "Confidence Convergence: All active hypotheses have been experimentally tested with decisive confidence scores."

        return None


    def _compute_hypothesis_hash(self, hypotheses: List[Hypothesis]) -> str:
        # Simple string representation of state for change detection
        # Include confidence and state (supports both Hypothesis objects and dicts)
        parts = []
        for h in hypotheses:
            h_id = h.get("id", "?") if isinstance(h, dict) else getattr(h, "id", "?")
            h_state = h.get("state", "?") if isinstance(h, dict) else getattr(h, "state", "?")
            h_state_str = h_state.value if hasattr(h_state, "value") else str(h_state)
            h_conf = (h.get("confidence") if isinstance(h, dict) else getattr(h, "confidence", None)) or 0.0
            parts.append(f"{h_id}:{h_state_str}:{float(h_conf):.2f}")
        return "|".join(sorted(parts))
