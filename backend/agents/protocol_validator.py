"""
Protocol Validator Agent
========================
High-rigor validation of research protocols before execution.
[TITAN V185.0] Physically asynchronous and event-loop-safe.
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from backend.llm_manager import run_llm, HYPOTHESIS_VALIDATION_MODEL
from backend.core.hypothesis.models import Hypothesis

logger = logging.getLogger(__name__)

@dataclass
class PlanReview:
    plan_id: str
    is_approved: bool
    overall_score: float
    summary: str
    feedback: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "is_approved": self.is_approved,
            "overall_score": self.overall_score,
            "summary": self.summary,
            "feedback": self.feedback or []
        }

class ProtocolValidator:
    """
    Sovereign gatekeeper for research protocols.
    Uses Ph.D. level reasoning to identify flaws, safety risks, and data holes.
    """
    
    def __init__(self, llm_manager=None):
        self.llm_manager = llm_manager
        logger.info(" ProtocolValidator: Sovereign Gate ONLINE.")

    async def validate(self, plan: Any, context: Dict[str, Any]) -> PlanReview:
        """
        Validate a research plan using adversarial LLM reasoning.
        """
        plan_id = plan.get("id", "unknown") if isinstance(plan, dict) else getattr(plan, "id", "unknown")
        tasks = plan.get("tasks", []) if isinstance(plan, dict) else getattr(plan, "tasks", [])

        if not self.llm_manager:
            logger.critical(" [SECURITY] No LLM manager provided. ProtocolValidator failing CLOSED to protect system.")
            return PlanReview(plan_id, False, 0.0, "Auto-rejection (No LLM for validation)")

        # Prepare prompt
        task_descriptions = "\n".join([
            f"- {t.get('description', str(t)) if isinstance(t, dict) else getattr(t, 'description', str(t))}"
            for t in tasks
        ])
        prompt = f"""You are a Lead Ph.D. Research Auditor. 
CRITICAL MISSION: Audit the following research plan for mathematical rigor, feasibility, and scientific novelty.

RESEARCH QUESTION: {context.get('research_question', 'N/A')}
DOMAIN: {context.get('domain', 'general')}

PLAN TASKS:
{task_descriptions}

AUDIT RULES:
1. Reject if the plan uses vague "placeholders" instead of technical steps.
2. Reject if the statistical methods are inappropriate for the domain.
3. Reject if the plan lacks empirical grounding or falsification metrics.

REQUIRED OUTPUT (JSON):
{{
  "is_approved": bool,
  "overall_score": 0.0-1.0,
  "summary": "Forensic audit summary",
  "feedback": ["Flaw 1", "Flaw 2"]
}}
"""
        
        # [TITAN V185.0] ASYNC RETRY MANIFOLD
        for attempt in range(2):
            try:
                model_string = HYPOTHESIS_VALIDATION_MODEL[0] if isinstance(HYPOTHESIS_VALIDATION_MODEL, (list, tuple)) else HYPOTHESIS_VALIDATION_MODEL
                result = await self.llm_manager.run_async(
                    prompt, 
                    model=model_string,
                    temperature=0.1,
                    source="protocol_validator"
                )
                
                # Parse JSON robustly
                text = result.get("text", "") if isinstance(result, dict) else str(result)
                from backend.utils.json_repair import repair_json
                data = repair_json(text)
                if isinstance(data, dict):
                    return PlanReview(
                        plan_id=plan_id,
                        is_approved=bool(data.get("is_approved", False)),
                        overall_score=float(data.get("overall_score", 0.0)),
                        summary=str(data.get("summary", "Audit complete")),
                        feedback=data.get("feedback", []) if isinstance(data.get("feedback"), list) else []
                    )
                else:
                    if attempt == 0:
                        logger.warning("No valid JSON dict found in validator response, retrying...")
                        await asyncio.sleep(0.5)
                        continue
                    
                    # [TITAN V162.1] ABSOLUTE RIGOR
                    logger.critical("[PROTOCOL-REJECT] LLM-Critic synthesis failure. Plan BLOCKED.")
                    return PlanReview(plan_id, False, 0.0, "Validator failed to produce structured JSON.")
                    
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Protocol validation attempt 1 failed: {e}. Retrying in 0.5s...")
                    await asyncio.sleep(0.5)
                    continue
                
                logger.error(f"Protocol validation failed after retries: {e}")
                return PlanReview(
                    plan_id=plan_id,
                    is_approved=False,
                    overall_score=0.0,
                    summary=f"Validation error: {str(e)}. Plan BLOCKED for safety."
                )
        
        return PlanReview(plan_id, False, 0.0, "Critical validation failure: Loop exited unexpectedly.")
