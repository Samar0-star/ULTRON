"""
The Overmind (Strategic Auditor)
================================
**THE SUPEREGO.**

Use Cases:
1.  **Metric-Driven Auditing**: Mathematically measures semantic drift from the original goal.
2.  **Historical Tracking**: Remembers past directives to prevent strategic flip-flopping.
3.  **Direct Context Injection**: Surgically modifies the shared context for downstream agents.
4.  **Emergency Pivot**: Can completely redirect the swarm if it detects failure patterns.

GODZILLA-TIER UPGRADES:
- Upgrade 1: DriftMeter (Semantic Distance vs. Vibes)
- Upgrade 2: AuditLog (Assessment Memory)
- Upgrade 3: Deterministic Gating (Short-circuit if drift is low)

It watches the watcher.
"""
import os
import logging
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

from backend.core.events.event_bus import events
from backend.core.hypothesis.models import Hypothesis, HypothesisState
from backend.llm_manager import run_llm, META_REASONING_MODEL
try:
    from backend.core.skill_injector import get_expert_system
except ImportError:
    get_expert_system = None

logger = logging.getLogger("backend.orchestration.overmind")

# Conditional import for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL_AVAILABLE = True
except (ImportError, Exception) as e:
    logger.warning(f"Overmind: Embedding model unavailable ({e}). Running in vibe-check mode.")
    EMBEDDING_MODEL_AVAILABLE = False


@dataclass
class AuditRecord:
    """Memory of a strategic decision."""
    cycle: int
    timestamp: float
    drift_score: float
    action: str
    rationale: str
    directive: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DriftMeter:
    """
    Mathematical conscience.
    Measures semantic distance between Original Goal and Current Reality.
    """
    def __init__(self):
        self.model = None
        if EMBEDDING_MODEL_AVAILABLE:
            try:
                from backend.core.world_model import get_shared_embedding_model
                self.model = get_shared_embedding_model()
                if self.model:
                    logger.info("Overmind: DriftMeter connected to shared embedding model.")
                else:
                    logger.info("Overmind: Shared embedding model offline; using lexical-overlap drift calculation.")
            except Exception as e:
                logger.warning(f"Overmind: DriftMeter failed to load model: {e}")

    def compute_drift(self, goal: str, current_state: str) -> float:
        """
        Calculate drift score (0.0 = aligned, 1.0 = lost).
        """
        if not goal or not current_state or not current_state.strip():
            return 0.3
        if not self.model:
            g_tokens = {w for w in goal.lower().split() if len(w) > 3}
            s_tokens = {w for w in current_state.lower().split() if len(w) > 3}
            if not g_tokens or not s_tokens:
                return 0.3
            overlap = len(g_tokens & s_tokens) / float(len(g_tokens))
            return float(max(0.0, min(0.5, 0.5 * (1.0 - overlap))))

        try:
            embeddings = self.model.encode([goal, current_state])
            n0 = float(np.linalg.norm(embeddings[0]))
            n1 = float(np.linalg.norm(embeddings[1]))
            if n0 <= 1e-12 or n1 <= 1e-12 or np.isnan(n0) or np.isnan(n1):
                return 0.3
            sim = float(np.dot(embeddings[0], embeddings[1]) / (n0 * n1))
            if np.isnan(sim):
                return 0.3
            return float(max(0.0, min(1.0, 1.0 - sim)))
        except Exception as e:
            logger.error(f"Drift calc failed: {e}")
            return 0.3


class Overmind:
    """
    The "Godzilla" of supervisors. 
    It doesn't execute tasks; it judges the direction of the hive.
    
    Now equipped with:
    - DriftMeter (Math)
    - AuditLog (Memory)
    """
    def __init__(self, llm_manager: Any = None, drift_meter: Any = None):
        self.llm_manager = llm_manager
        self.drift_meter = drift_meter or DriftMeter()
        
        self.audit_log: List[AuditRecord] = []
        
        # EPISTEMIC LAW: Hard termination flag (wired into orchestrator._can_proceed)
        self.termination_requested: bool = False
        self.termination_reason: str = ""
        
        # Thresholds
        self.drift_tolerance = 0.25  # Below this, short-circuit (trust the swarm)
        self.max_drift = 0.6         # Above this, force emergency pivot

    async def audit_trajectory(
        self, 
        research_question: str, 
        hypotheses: List[Hypothesis], 
        findings: List[Dict[str, Any]],
        cycle: int
    ) -> Dict[str, Any]:
        """
        Perform a strategic audit of the current research session.
        Returns a 'Directive' for the orchestrator.
        """
        logger.info(f"[OVERMIND] Auditing cycle {cycle}...")

        # 1. METRIC-DRIVEN CHECK (The "Vibes" Killer)
        # Construct current trajectory string from active/proposed/confirmed hypotheses and findings
        active_hyps = []
        for h in (hypotheses or []):
            if isinstance(h, dict):
                st = str(h.get("state", "")).lower()
                if st not in ("refuted", "falsified", "archived"):
                    active_hyps.append(str(h.get("statement", "")))
            else:
                st = getattr(h, "state", None)
                if st not in (HypothesisState.REFUTED, HypothesisState.ARCHIVED):
                    active_hyps.append(str(getattr(h, "statement", "")))
        if not active_hyps and hypotheses:
            active_hyps = [
                str(h.get("statement", "") if isinstance(h, dict) else getattr(h, "statement", ""))
                for h in hypotheses[:5]
            ]

        recent_findings = []
        for f in (findings or [])[-5:]:
            if isinstance(f, dict):
                txt = (
                    f.get("content")
                    or f.get("summary")
                    or (f.get("result", {}).get("summary") if isinstance(f.get("result"), dict) else None)
                    or f.get("task_description")
                    or ""
                )
                if txt:
                    recent_findings.append(str(txt))
            elif isinstance(f, str):
                recent_findings.append(f)

        current_state_text = f"Hypotheses: {' '.join(active_hyps)}. Findings: {' '.join(recent_findings)}"
        drift_score = self.drift_meter.compute_drift(research_question, current_state_text)
        
        # [GODZILLA FIX] Prevent Cycle 1 "Lost" State and Panic Pivoting
        if cycle <= 1:
            drift_score = min(drift_score, 0.2) # Force ultra-low drift for startup
            logger.info(f"Overmind: Capping startup drift to {drift_score:.3f} to ensure pipeline flow.")
        elif cycle <= 3:
            drift_score = min(drift_score, 0.4)
            logger.info(f"Overmind: Capping early cycle drift to {drift_score:.3f}")
        
        logger.info(f"Overmind Metric: Drift Score = {drift_score:.3f}")

        # 2. DETERMINISTIC GATING (The Token Saver)
        # If drift is low and we haven't pivoted recently, trust the process.
        # [GODZILLA] Force Cycle 1 to continue to establish a baseline
        if cycle <= 1:
            logger.info("Overmind: Startup Cycle 1. Forcing 'continue' to establish research baseline.")
            self._log_audit(cycle, drift_score, "continue", "Startup baseline")
            return {"action": "continue", "rationale": "Forced baseline for Cycle 1.", "drift_score": drift_score}

        if drift_score < self.drift_tolerance and cycle % 5 != 0:
            logger.info("Overmind: Drift acceptable. Standing down.")
            self._log_audit(cycle, drift_score, "continue", "Drift within tolerance")
            return {"action": "continue", "rationale": "Strategic alignment confirmed by metrics.", "drift_score": drift_score}

        # 3. CONTEXT PREPARATION (If we must intervene)
        if not self.llm_manager:
            return {"action": "continue", "rationale": "No LLM for meta-reasoning", "drift_score": drift_score}

        # Prepare a high-density summary (safely handling both Hypothesis objects and dicts)
        hyp_lines = []
        for h in (hypotheses or [])[:15]:
            if isinstance(h, dict):
                st_raw = h.get("state", "proposed")
                st_val = st_raw.value if hasattr(st_raw, "value") else str(st_raw)
                stmt_val = h.get("statement", str(h))
            else:
                st_raw = getattr(h, "state", "proposed")
                st_val = st_raw.value if hasattr(st_raw, "value") else str(st_raw)
                stmt_val = getattr(h, "statement", str(h))
            hyp_lines.append(f"- [{st_val}] {stmt_val}")
        hyp_summary = "\n".join(hyp_lines)

        finding_lines = []
        for f in (findings or [])[-10:]:
            if isinstance(f, dict):
                f_txt = (
                    f.get("task_description")
                    or f.get("content")
                    or f.get("summary")
                    or (f.get("result", {}).get("summary") if isinstance(f.get("result"), dict) else None)
                    or str(f)
                )
            else:
                f_txt = str(f)
            finding_lines.append(f"- {str(f_txt)[:150]}")
        finding_summary = "\n".join(finding_lines)
        
        # Injection: Historical Context
        last_audit = self.audit_log[-1] if self.audit_log else None
        last_directive = f"Last directive ({last_audit.action}): {last_audit.directive}" if last_audit else "None"

        # MIND/BODY LOCK
        meta_prompt = ""
        if get_expert_system:
            try:
                expert = get_expert_system()
                if hasattr(expert, "_check_keyword_overrides"):
                    t1_skills = (
                        expert._check_keyword_overrides("critique", "T1")
                        or expert._check_keyword_overrides("critical", "T1")
                        or expert._check_keyword_overrides("adversarial", "T1")
                    )
                    if t1_skills:
                        meta_prompt = "\n# [COG] - CRITICAL REASONING PROTOCOLS\n"
                        for s in t1_skills:
                            if hasattr(s, "to_prompt_block"):
                                meta_prompt += s.to_prompt_block(include_examples=False)
            except Exception as e:
                logger.warning(f"Failed to inject Overmind skills: {e}")

        prompt = f"""
# RESEARCH TRAJECTORY SUPERVISOR & STRATEGIC AUDITOR

{meta_prompt}

You are the strategic supervisor evaluating research swarm trajectory against the target objective.
Your mandate: Evaluate empirical progress, detect goal drift or hallucination, and command course corrections.

===============================================================================
MISSION CONTEXT
===============================================================================

ORIGINAL GOAL: {research_question}
CURRENT CYCLE: {cycle}
CALCULATED DRIFT: {drift_score:.3f} (0=Perfect, 1=Lost)
PREVIOUS DIRECTIVE: {last_directive}

ACTIVE HYPOTHESES:
{hyp_summary}

RECENT FINDINGS:
{finding_summary}

===============================================================================
AUDIT PROTOCOL
===============================================================================

1. [DRIFT] DRIFT ANALYSIS: Drift is {drift_score:.3f}. If > {self.max_drift}, this is CRITICAL.
   - Are we answering the WRONG question?
   - Are we obsessing over a minor detail?

2. [TRUTH] HALLUCINATION CHECK:
   - Are hypotheses grounded in findings?

3. [SPEED] MOMENTUM CHECK:
   - Are we going in circles? (Check previous directive)

===============================================================================
VERDICT OPTIONS
===============================================================================

- CONTINUE: All is well. Proceed.
- PRUNE: Archive specified hypotheses.
- PIVOT: Complete direction change.
- INTENSIFY: Double down on current promising direction.
- TERMINATE: EMERGENCY STOP. Research direction is fundamentally flawed or question is unanswerable. Use ONLY when continued research would waste resources.

Return ONLY valid JSON:
{{
    "action": "continue" | "prune" | "pivot" | "intensify" | "terminate",
    "rationale": "Strategic reasoning...",
    "prune_ids": ["id1"],
    "new_directive": "Guidance for swarm...",
    "context_patch": "Text to inject into shared context (optional)",
    "confidence": 0.0-1.0
}}"""

        try:
            result = await self.llm_manager.run_async(prompt=prompt, model=META_REASONING_MODEL)

            text = ""
            if isinstance(result, dict):
                text = result.get("text", "")
            elif hasattr(result, 'content'):
                # Anthropic Message Object handle
                if isinstance(result.content, list) and len(result.content) > 0:
                    text = getattr(result.content[0], 'text', str(result.content[0]))
                else:
                    text = str(result.content)
            else:
                text = str(result)

            # Lazy import
            from backend.utils.json_repair import repair_json
            directive = repair_json(text)

            
            if not directive:
                 logger.warning(f"Overmind audit failed to parse JSON. Raw: {text[:100]}...")
                 directive = {"action": "continue", "rationale": "JSON Parsing Failure"}
            
            # Allow list output (rare but possible)
            if isinstance(directive, list):
                directive = directive[0] if (len(directive) > 0 and isinstance(directive[0], dict)) else {"action": "continue", "rationale": "List fallback"}
            if not isinstance(directive, dict):
                directive = {"action": "continue", "rationale": "Invalid directive format"}
            directive["drift_score"] = drift_score
            
            # Log decision
            self._log_audit(
                cycle, drift_score, 
                directive.get("action", "unknown"), 
                directive.get("rationale", ""), 
                directive.get("new_directive")
            )
            
            # EPISTEMIC LAW: Set termination flag if Overmind issues TERMINATE with high confidence (>= 0.8)
            if directive.get("action") == "terminate":
                try:
                    conf = float(directive.get("confidence", 0.8))
                except (ValueError, TypeError):
                    conf = 0.8
                if conf < 0.8:
                    logger.warning(f"OVERMIND: Termination directive rejected due to low confidence ({conf:.2f} < 0.80). Defaulting action to 'continue'.")
                    directive["action"] = "continue"
                elif os.environ.get("ULTRON_ALLOW_OVERMIND_TERMINATE", "false").lower() == "true":
                    self.termination_requested = True
                    self.termination_reason = directive.get("rationale", "Overmind strategic termination")
                    logger.critical(f"OVERMIND TERMINATION REQUESTED: {self.termination_reason}")
                else:
                    logger.warning("OVERMIND requested terminate; converting to strategic PIVOT to preserve autonomous campaign runtime.")
                    directive["action"] = "pivot"
                    if not directive.get("new_directive"):
                        directive["new_directive"] = "Explore orthogonal physical mechanisms and untested variable interactions." 
            
            # Broadcast event
            await events.emit(
                event_type="OVERMIND_DIRECTIVE_ISSUED",
                payload={"session_id": "global", "directive": directive},
                source="Overmind"
            )
            
            return directive
        except Exception as e:
            logger.error(f"Overmind audit failed: {e}")
            return {"action": "pause", "rationale": f"Overmind exception: {e}. Pausing for safety.", "drift_score": drift_score}

    def _log_audit(self, cycle: int, drift: float, action: str, rationale: str, directive: str = None):
        """Record the judgment."""
        self.audit_log.append(AuditRecord(
            cycle=cycle,
            timestamp=time.time(),
            drift_score=drift,
            action=action,
            rationale=rationale,
            directive=directive
        ))

# Shared DriftMeter (Heavy Resource - Singleton)
_SHARED_DRIFT_METER: Optional[DriftMeter] = None

def get_overmind(llm_manager: Any = None) -> Overmind:
    """
    Get a fresh Overmind instance for the session (with shared heavy resources).
    Fixes state leakage by ensuring fresh audit logs per call.
    """
    global _SHARED_DRIFT_METER
    if _SHARED_DRIFT_METER is None:
        _SHARED_DRIFT_METER = DriftMeter()
    
    return Overmind(llm_manager=llm_manager, drift_meter=_SHARED_DRIFT_METER)
