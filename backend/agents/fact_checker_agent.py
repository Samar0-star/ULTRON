from __future__ import annotations

# backend/agents/fact_checker_agent.py
"""
Production-ready Fact Checker Agent.
Verifies claims against known facts or external sources (via context).
"""

import os
import json
import logging
import asyncio
import hashlib
from typing import Any, Dict, List, Optional
from backend.core.skill_injector import get_expert_system

# Logging
logger = logging.getLogger("avon.fact_checker")
logger.setLevel(os.getenv("AVON_LOG_LEVEL", "INFO"))
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)

# Config
TEMPERATURE = 0.0
try:
    from backend.config import settings
    MAX_CONTEXT_CHARS = settings.get_limit("prompt_truncation_limit", 400000)
except Exception:
    MAX_CONTEXT_CHARS = 400000

_PROMPT_TXT = """
# SYSTEM ROLE
You are the PHD-Grade Verification Node in an automated AI Scientist pipeline. Your sole function is strict, objective fact-checking of a provided `target_claim` against the provided `reference_context`. You are a logical evaluator, not a conversational assistant.

# OPERATIONAL DIRECTIVES
1. ZERO HALLUCINATION: You must evaluate the claim *strictly* based on the provided `reference_context`. Do not use outside training data. If the context does not contain enough explicit data to verify the claim, it must be flagged as unsupported.
2. STRICT LOGICAL MATCHING: Treat the claim as a proposition. Identify if the evidence fully entails, contradicts, or is orthogonal to the claim.
3. MACHINE OUTPUT ONLY: Return strictly a valid JSON object. Do not wrap the JSON in markdown formatting (no ```json). Do not output any preamble or conversational text.

# VERDICT TAXONOMY
You must classify the claim using ONLY one of the following strict states:
- VERIFIED: The claim is explicitly and fully supported by the context.
- CONTRADICTED: The claim is explicitly refuted by data in the context.
- UNSUPPORTED: The context lacks sufficient information to either verify or refute the claim.
- PARTIAL: The claim contains a mix of supported facts and unsupported extrapolations/errors.

# REQUIRED JSON SCHEMA
{
  "verdict": "VERIFIED" | "CONTRADICTED" | "UNSUPPORTED" | "PARTIAL",
  "confidence": float (0.0 to 1.0, representing the directness of the evidence),
  "logical_analysis": "A concise, 1-2 sentence mechanical explanation of why the evidence entails or contradicts the claim.",
  "evidence_extracted": [
    "Exact substring quote(s) from the reference_context that justify the verdict. Array must be empty if UNSUPPORTED."
  ],
  "corrected_claim": "If the verdict is CONTRADICTED or PARTIAL, provide the corrected factual statement. If VERIFIED or UNSUPPORTED, output null."
}

Return only the JSON object.
"""

class Agent:
    name = "fact_checker"
    capabilities = ["fact_checking", "verification", "critical_reasoning", "general"]

    def __init__(self):
        self.expert_system = get_expert_system()

    async def run(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async entrypoint.
        task payload: {"claim": "...", "context": "..."}
        """
        payload = task.get("payload") or {}
        claim = payload.get("claim") or task.get("query") or ""
        evidence = payload.get("context") or payload.get("evidence") or ""

        if not claim:
            return {"status": "failed", "error": "No claim provided"}

        # Import llm_manager
        try:
            from backend.llm_manager import run_llm, get_model
            _fc_cfg = get_model("fact_checking")
        except ImportError:
            try:
                from llm_manager import run_llm, get_model
                _fc_cfg = get_model("fact_checking")
            except ImportError:
                raise RuntimeError("LLM Manager not available")

        FACT_CHECKING_MODEL = _fc_cfg[0] if isinstance(_fc_cfg, tuple) else str(_fc_cfg)
        fc_temp = float(_fc_cfg[1]) if isinstance(_fc_cfg, tuple) and len(_fc_cfg) > 1 else TEMPERATURE

        prompt_text = _PROMPT_TXT + f"\n\nClaim:\n{claim}\n\nEvidence/Context:\n{str(evidence)[:MAX_CONTEXT_CHARS]}"
        
        # [GODZILLA ALIGNMENT] Inject specialist fact-checking skills
        prompt_text = await self.expert_system.inject_bundle(prompt_text, "fact_checker")

        logger.info(f"Fact checking claim: {claim[:50]}...")
        
        try:
            resp = await asyncio.to_thread(run_llm, prompt_text, model=FACT_CHECKING_MODEL, temperature=fc_temp)
            
            # [HARDENING] Extract text safely from dict or str
            if isinstance(resp, dict):
                resp_text = resp.get("text", resp.get("content", ""))
            else:
                resp_text = str(resp)

            # Parse JSON with repair_json fallback
            try:
                from backend.utils.json_repair import repair_json
                data = repair_json(resp_text)
                if not isinstance(data, dict):
                    start = resp_text.find("{")
                    end = resp_text.rfind("}")
                    data = json.loads(resp_text[start:end+1]) if (start != -1 and end != -1) else None
                if isinstance(data, dict):
                    
                    # [TITAN V240.0] EPISTEMIC BINDING
                    # Physically save the verified fact to the World Model.
                    wm = context.get("world_model")
                    verdict = data.get("verdict")
                    corrected = data.get("corrected_claim")
                    logical_analysis = data.get("logical_analysis") or data.get("analysis") or ""
                    if wm and (verdict == "VERIFIED" or (verdict == "PARTIAL" and corrected)):
                        committed_claim = corrected if verdict == "PARTIAL" else (corrected or claim)
                        logger.info(f" [FACT_CHECKER] Committing verified claim to World Model: {committed_claim[:30]}...")
                        try:
                            fact_id = hashlib.sha256(committed_claim.encode()).hexdigest()[:16]
                            wm.commit_verified_fact(
                                key=f"verified_claim_{fact_id}",
                                value=committed_claim,
                                source="fact_checker_agent",
                                confidence=data.get("confidence", 0.8),
                                metadata={
                                    "fact_id": fact_id,
                                    "analysis": logical_analysis,
                                    "logical_analysis": logical_analysis,
                                    "verdict": verdict,
                                    "evidence_extracted": data.get("evidence_extracted", []),
                                    "reasoning_trace": resp_text
                                }
                            )
                        except Exception as wm_err:
                            logger.error(f" [FACT_CHECKER] Failed to commit to World Model: {wm_err}")
                            
                    return {"result": data, "meta": {"raw": resp_text}}
                else:
                    return {"result": {"verdict": "error", "analysis": resp_text}, "meta": {"raw": resp_text}}
            except Exception:
                return {"result": {"verdict": "error", "analysis": resp_text}, "meta": {"raw": resp_text}}
                
        except Exception as e:
            logger.error(f"Fact check failed: {e}")
            return {"error": str(e)}

# Backward compatibility
FactCheckerAgent = Agent
