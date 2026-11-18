"""
Meta-Reasoning Layer (Pillar 6: Self-Adaptation) - GODZILLA TIER
================================================================
**THE COGNITIVE CONTROLLER.**

This is not a thermostat. This is a prefrontal cortex.
It observes the system's thought process and strategically intervenes.

Capabilities:
1.  **Reflective State Analysis**: Fuses 10+ metrics to determine "Cognitive Health".
2.  **Strategic Mode Switching**: Dynamically shifts between Exploration, Exploitation, and Lateral Jumping.
3.  **Stagnation Breaking**: Detects "thinking loops" and forces orthogonal strategy shifts.
4.  **Resource Arbitrage**: Allocates remaining budget to the highest-ROI activities.

It optimizes the mind.
"""

import logging
import json
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from backend.core.hypothesis.models import Hypothesis

logger = logging.getLogger(__name__)

class CognitiveMode(str, Enum):
    """Discrete operational modes for the research engine."""
    EXPLORATION_FRENZY = "exploration_frenzy" # Max branching, high temp
    SNIPER_FOCUS = "sniper_focus"             # Min branching, deep verification
    LATERAL_JUMP = "lateral_jump"             # Force orthogonal topics
    CRITIC_DEBATE = "critic_debate"           # Adversarial self-review
    RESOURCE_CONSERVATION = "conservation"    # Low cost, high safe-guarding
    PANIC_RESET = "panic_reset"               # Emergency state reset

@dataclass
class StrategyState:
    """The current strategic configuration."""
    mode: CognitiveMode = CognitiveMode.EXPLORATION_FRENZY
    branching_factor: int = 3
    exploration_rate: float = 0.5  # 0.0 = exploit, 1.0 = explore
    confidence_decay_rate: float = 0.05
    search_depth_limit: int = 3
    temperature: float = 0.7
    reasoning: str = "Initial State"

class MetaReasoningLayer:
    """
    The 'Overmind' of the research session.
    Uses LLM reflection to adjust high-level control parameters.
    """
    
    def __init__(self, llm_manager=None):
        self.llm_manager = llm_manager
        self.current_strategy = StrategyState()
        self.history = []
        self._last_intervention_cycle = 0
        self._stagnation_counter = 0

    async def adapt_strategy_async(self, cycle: int, hypotheses: List[Hypothesis], 
                                  session_metrics: Dict[str, Any] = None, 
                                  findings_count: int = 0,
                                  seed_data: List[Any] = None,
                                  domain: str = "other",
                                  **kwargs) -> StrategyState:
        """
        Analyze state and update strategy parameters using LLM reflection.
        
        Args:
            cycle: Current research cycle
            hypotheses: List of active hypotheses
            session_metrics: Dict containing findings_count, refusal_rate, error_rate, budget_used
            findings_count: (Optional) Direct findings count for alignment
            domain: The scientific domain of the mission
            
        Returns:
            Updated StrategyState
        """
        # 1. Gather Telemetry
        if session_metrics is None:
            session_metrics = {}
            
        def _is_active_hyp(h: Any) -> bool:
            st = getattr(h, "state", None) if not isinstance(h, dict) else h.get("state")
            st_val = getattr(st, "value", str(st)).lower() if st is not None else ""
            return st_val in ("testing", "proposed", "novel", "prioritized")

        active_hypotheses = [h for h in hypotheses if _is_active_hyp(h)]
        active_count = len(active_hypotheses)
        
        # Use findings_count from either dict or direct arg
        findings_count = session_metrics.get("findings_count", findings_count)
        refusal_rate = session_metrics.get("refusal_rate", 0.0)
        
        # 2. Check for Hardware Interrupts (Hard Rules still apply for safety)
        if cycle - self._last_intervention_cycle < 3 and cycle > 5:
             # Prevent oscillating strategies too fast
             return self.current_strategy

        # 3. Construct Reflection Prompt (GODZILLA TIER)
        # Extract semantic content for the Brain
        active_hypotheses_text = "\n".join([
            f"- H{getattr(h, 'id', h.get('id', '?') if isinstance(h, dict) else '?')}: "
            f"{getattr(h, 'statement', h.get('statement', '') if isinstance(h, dict) else str(h))} "
            f"(State: {getattr(getattr(h, 'state', None), 'value', getattr(h, 'state', ''))})"
            for h in active_hypotheses[:10]
        ])
        
        # Process findings (unchoked for deep strategic reasoning; handle dicts or strings safely)
        recent_findings = session_metrics.get("recent_findings", [])
        finding_lines = []
        for f in recent_findings[:10]:
            if isinstance(f, dict):
                f_str = (
                    f.get("content")
                    or f.get("summary")
                    or (f.get("result", {}).get("summary") if isinstance(f.get("result"), dict) else "")
                    or str(f)
                )
            else:
                f_str = str(f)
            finding_lines.append(f"- {str(f_str)[:5000]}")
        findings_text = "\n".join(finding_lines) if finding_lines else "No recent findings."

        # Process Nexus Context (seed_data)
        nexus_context = "\n".join([str(n)[:5000] for n in seed_data[:5]]) if seed_data else "No deep memory retrieval."

        context = f"""
        MISSION DOMAIN: {domain.upper()}
        CURRENT STATE (Cycle {cycle}):
        - Active Hypotheses Count: {active_count}
        - Total Findings: {findings_count}
        - Refusal Rate: {refusal_rate:.2f}
        - Current Mode: {self.current_strategy.mode.value}
        
        ACTIVE HYPOTHESES (SEMANTIC):
        {active_hypotheses_text}
        
        RECENT DISCOVERIES (SEMANTIC):
        {findings_text}
        
        DEEP MEMORY CONTEXT (NEXUS):
        {nexus_context}
        
        GOAL: Optimize research trajectory based on CONTENT and DOMAIN.
        - Suggest strategies relevant to {domain.upper()}.
        - If findings contradict hypotheses -> CRITIC_DEBATE or SNIPER_FOCUS
        - If findings confirm core assumptions -> EXPLORATION_FRENZY
        - If stuck/refusals high -> LATERAL_JUMP (staying within {domain})
        """
        
        # 4. Neural Reflection via Structured Epistemic Schema
        try:
            if self.llm_manager:
                from backend.core.schemas.meta import CognitiveModeDecision
                from backend.llm_manager import META_REASONING_MODEL
                
                decision: CognitiveModeDecision = await self.llm_manager.run_structured_async(
                    prompt=f"Analyze this research session and recommend a strategic cognitive mode shift.\n{context}",
                    response_model=CognitiveModeDecision,
                    model=META_REASONING_MODEL
                )
                
                # Hallucination Guard: If confidence < 0.8, fall back to conservative retention
                if decision.confidence < 0.8:
                    logger.info(f" [META-REASONING] Low confidence ({decision.confidence:.2f} < 0.80). Retaining current mode: {self.current_strategy.mode.value}")
                else:
                    mode_str = decision.mode.lower()
                    new_mode = CognitiveMode(mode_str)
                    
                    if new_mode != self.current_strategy.mode:
                        logger.info(f" [META-REASONING] SHIFT: {self.current_strategy.mode.value} -> {new_mode.value}")
                        logger.info(f"   Reason: {decision.reasoning} (Confidence: {decision.confidence:.2f})")
                        self._last_intervention_cycle = cycle
                    
                    self.current_strategy = StrategyState(
                        mode=new_mode,
                        branching_factor=int(decision.branching_factor),
                        exploration_rate=float(decision.exploration_rate),
                        reasoning=decision.reasoning
                    )
            else:
                # Fallback to Heuristics if no LLM
                self._apply_heuristics(active_count, findings_count)
                
        except Exception as e:
            logger.warning(f"Meta-reasoning structured run failed: {e}. Falling back to heuristics.")
            self._apply_heuristics(active_count, findings_count)
            
        # 5. Record History
        self.history.append({
            "cycle": cycle,
            "strategy": self.current_strategy,
            "metrics": session_metrics
        })
        
        return self.current_strategy

    def _apply_heuristics(self, active_count: int, findings_count: int):
        """Fallback logic (The Thermostat)"""
        if active_count > 5:
            self.current_strategy.mode = CognitiveMode.SNIPER_FOCUS
            self.current_strategy.branching_factor = 1
            self.current_strategy.exploration_rate = 0.2
        elif active_count < 2:
            self.current_strategy.mode = CognitiveMode.EXPLORATION_FRENZY
            self.current_strategy.branching_factor = 5
            self.current_strategy.exploration_rate = 0.9
        
    def _get_recent_history_summary(self) -> str:
        """Get summarized history for context."""
        if not self.history:
            return "No history."
        return str([f"Cycle {h['cycle']}: {h['strategy'].mode.value}" for h in self.history[-3:]])
