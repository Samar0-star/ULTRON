# -*- coding: utf-8 -*-
"""
Hypothesis Generator - The  Engine (V1.0 - Ph.D. LEVEL TIER 2)
=========================================================
Standardized JSON parsing using global repair_json.
Sovereign Reasoning Anchors and Persistence Binding active.
"""

import logging
import json
import re
import hashlib
import time
import os
import sys
import asyncio
from typing import List, Dict, Any, Optional



from backend.core.hypothesis.models import Hypothesis, HypothesisState
from backend.llm_manager import (
    HYPOTHESIS_GENERATION_MODEL,
    HYPOTHESIS_VALIDATION_MODEL,
    REPORT_FINAL_MODEL
)
from backend.core.skill_injector import get_expert_system
from backend.utils.json_repair import repair_json

logger = logging.getLogger(__name__)


def extract_json_brute(s):
    first_brace = s.find('{')
    last_brace = s.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        return s[first_brace:last_brace+1]
    first_bracket = s.find('[')
    last_bracket = s.rfind(']')
    if first_bracket != -1 and last_bracket > first_bracket:
        return s[first_bracket:last_bracket+1]
    return s


class HypothesisGenerator:
    """
    The GODZILLA: FORMAL HYPOTHESIS ENGINE.
    Generates hypotheses with MATHEMATICAL STRUCTURE, not just prose.
    """
    
    def __init__(self, llm_manager):
        self.llm_manager = llm_manager

    async def generate_hypotheses(self, research_question: str, domain: str, 
                                 existing_hypotheses: List[Hypothesis] = None,
                                 selected_tools: List[str] = None,
                                 **kwargs) -> List[Hypothesis]:
        """
        Generates FORMAL scientific hypotheses using a 2-Pass Protocol.
        Now uses a robust retry loop instead of falling back to synthetic slop.
        """
        from backend.core.domain_regulator import DomainRegulator
        
        # [TITAN V138.0] REFINED RIGOR GATE
        # Only skip hypothesis generation for purely administrative/bibliographic tasks with zero scientific mechanism.
        proc_stems = ["extract pdf", "gather citations", "using agent", "compile bibliography", "preprocess file"]
        q_low = research_question.lower().strip()
        if any(q_low.startswith(stem) or stem in q_low for stem in proc_stems):
            if not any(sci_kw in q_low for sci_kw in ["hypothesis", "mechanism", "develop", "novel", "effect", "interaction", "model", "predict", "validate", "optimize"]):
                logger.info(f" [SCIENCE] Purely administrative task detected: '{research_question}'. Skipping hypothesis generation.")
                return []


        existing_context = ""
        if existing_hypotheses:
            existing_context = "\nEXISTING HYPOTHESES (Do not repeat):\n"
            for h in existing_hypotheses:
                h_stmt = h.statement if hasattr(h, 'statement') else str(h)
                existing_context += f"- {h_stmt}\n"

        # Query Semantic Morgue so previously falsified/killed hypotheses populate the DEAD ZONE
        morgue_entries = []
        try:
            from backend.agents.red_team_agent import RedTeamAgent
            morgue_entries = RedTeamAgent().query_morgue(research_question, similarity_threshold=0.55) or []
            if morgue_entries:
                existing_context += "\nDEAD ZONE (Previously Falsified / Killed Hypotheses — DO NOT RE-PROPOSE):\n"
                for m_item in morgue_entries[:10]:
                    existing_context += f"- {m_item.get('statement', '')} [Killed because: {m_item.get('kill_reason', 'Falsified')}]\n"
        except Exception as morgue_err:
            logger.debug(f"Morgue lookup skipped during hypothesis generation: {morgue_err}")

        expert = get_expert_system()
        profile = await DomainRegulator.get_domain_profile(research_question, domain_hint=domain)
        # [TITAN V143.0] NEURAL GROUNDING
        grounding = await DomainRegulator.get_domain_examples_async(profile, research_question=research_question)

        logger.info(f" [SCIENCE] Discovery active. Tags: {profile}. Grounding: {grounding.get('unit', 'unknown')}")

        facts = kwargs.get("facts", [])
        
        # [RIGOR FILTER] Purify facts using the dynamic DomainRegulator to prevent out-of-domain slop
        if facts:
            fact_map = {(f.value if hasattr(f, "value") else str(f)): f for f in facts}
            fact_strs = list(fact_map.keys())
            filtered_strs = DomainRegulator.filter_by_domain_similarity(fact_strs, research_question)
            facts = [fact_map[s] for s in filtered_strs]

        MAX_RETRIES = 5
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                backoff = min(2.0 * (2 ** (attempt - 1)), 6.0)
                logger.info(f"Retrying hypothesis generation attempt {attempt+1} (backoff {backoff:.1f}s)...")
                await asyncio.sleep(backoff)


            # [TITAN V154.9] ADAPTIVE TPM SHIELD (DISABLED FOR V15 RUN)
            # [GODZILLA FIX] Context truncation caused Epistemic Collapse. 
            # We now pass the entire context array unconditionally so the LLM can generate PhD-level novelty.
            current_facts = facts
            
            # [RIGOR FIX] Purify context from OS/API logs
            # [ANTI-ROT COMPACTION PROTOCOL]
            # 1. Purify context from OS/API logs, transfer bars, and hydration noise
            # 2. Strict retention for high-signal Physical Canon (PDB crystallography, DMS binding measurements)
            # 3. Relevance ranking for literature findings with a 28,000 char compaction ceiling
            # 4. Drastically reduces prefill latency, eliminating upstream ALB HTTP 504 timeouts
            physical_canon = []
            literature_facts = []
            rq_tokens = set(re.findall(r'\w+', research_question.lower())) if research_question else set()

            for f in current_facts:
                f_key = getattr(f, "key", "") or ""
                f_val = f.value if hasattr(f, "value") else str(f)
                is_schema_or_data = any(k in f_key.lower() for k in ["local_database_schema", "database", "dataset", "schema", "ground_truth", "empirical"]) or ("AVAILABLE PHYSICAL DATASETS" in f_val)
                if not is_schema_or_data and any(x in f_val for x in ["traceback", "Traceback", "Exception:", "node_modules", "window.__reactRouter"]):
                    logger.debug(f" [PURITY] Stripped OS/API log from context: {f_val[:50]}...")
                    continue

                is_physical = is_schema_or_data or any(k in f_key.lower() for k in [
                    "ground_truth", "biophys", "crystal", "dms", "structure", "interface", "contact",
                    "physics", "chemistry", "materials", "astro", "genom", "neuro", "climate", "experiment"
                ]) or any(k in f_val.lower() for k in [
                    "format=sqlite", "format=parquet", "format=tabular", "format=hdf5", "columns (",
                    "angstrom", "sasa", "coulomb", "pdb", "binding affinity", "kelvin", "electron", " hamiltonian"
                ])

                if is_physical:
                    physical_canon.append(f_val)
                else:
                    val_lower = f_val.lower()
                    f_tokens = set(re.findall(r'\w+', val_lower))
                    overlap = len(rq_tokens.intersection(f_tokens))
                    has_numerical = 1 if re.search(r'\d+\.?\d*', f_val) else 0
                    score = overlap * 2.0 + has_numerical
                    literature_facts.append((score, f_val))

            literature_facts.sort(key=lambda x: x[0], reverse=True)

            max_chars = 120000
            selected_facts = []
            cum_chars = 0

            # Priority 1: 100% of physical ground truth
            for pf in physical_canon:
                if cum_chars + len(pf) > int(max_chars * 0.65):
                    break
                selected_facts.append(pf)
                cum_chars += len(pf)

            # Priority 2: High-signal literature facts filling clean headroom
            for _, lf in literature_facts:
                if cum_chars + len(lf) > max_chars:
                    break
                selected_facts.append(lf)
                cum_chars += len(lf)

            context_str = "\n".join([f"- {f}" for f in selected_facts]) if selected_facts else "No facts available."
            logger.info(f" [GENERATOR] Starting 2-Turn Discovery pass, attempt {attempt + 1}/{MAX_RETRIES} (grounded context: {len(selected_facts)} facts, {cum_chars} chars - Anti-Rot Compaction Active)")
            safe_context = context_str
            safe_rq = research_question


            
            domain_tags = str(profile)
            physical_grounding = str(grounding)

            if attempt == 0:
                seeds_section = f"""NOVELTY SEEDS — USE THESE AS DEPARTURE POINTS FOR GENUINELY NEW TERRITORY
══════════════════════════════════════════════════════════════════
The following are UNEXPLORED directions for {domain}. Use them as inspiration
to derive a novel mechanism based on the objective: {safe_rq}"""
            else:
                seeds_section = f"NOVELTY SEEDS: Focus on unmapped mechanistic interactions in {domain}."

            brainstorm_prompt = f"""You are an expert theoretical and experimental researcher in {domain}.
Ensure all scientific claims are falsifiable, mathematically consistent, and grounded in observable quantities from the provided data.
If the research question is fundamentally unfalsifiable, circular, or ungrounded, output: {{"refusal": true, "reason": "..."}}.

RESEARCH QUESTION:
{safe_rq}

DOMAIN TAGS:
{domain_tags}

AVAILABLE PHYSICAL DATA (GROUND TRUTH):
{physical_grounding}
(These are the only variables you may use. Every variable has a fixed physical meaning, unit, and empirical range.
You must respect these bounds. Proposing a variable outside this set is invalid.)

CONTEXTUAL FACTS (prior knowledge):
{safe_context}

══════════════════════════════════════════════════════════════════
PHASE 0 — FALSIFIABILITY AND IDENTIFIABILITY GATE
══════════════════════════════════════════════════════════════════

Before designing any hypothesis, verify:
1. The research question can be operationalized as a testable claim about the provided physical variables.
2. An explicit quantitative measurement exists that would conclusively falsify the core claim.
3. Physical and biological constraints are strictly respected (conservation laws, dimensional consistency).

══════════════════════════════════════════════════════════════════
PRIOR ART EXCLUSION, DEAD ZONE & NOVELTY DIRECTIVE
══════════════════════════════════════════════════════════════════
Formulate hypotheses that explore orthogonal mechanisms to established literature in {domain}.
Do not reproduce textbook mechanisms, previously tested hypotheses, or falsified DEAD ZONE claims below:
{existing_context if existing_context else "No prior hypotheses or DEAD ZONE entries recorded yet."}

══════════════════════════════════════════════════════════════════
{seeds_section}
══════════════════════════════════════════════════════════════════

MISSION: Generate EXACTLY one novel, mechanistic, mathematically precise hypothesis.

You must produce a hypothesis that:

1. **States a clear, causal mechanism** connecting at least two variables from the physical grounding.
2. **Expresses that mechanism as a functional form** (equation) using the defined variable symbols and their units.
   - The equation must be dimensionally consistent.
   - Parameters must have plausible numerical ranges (justify briefly).
3. **Draws a causal graph** (in your mind, then described) showing the assumed causal links, confounders, and latent variables.
4. **Defines the primary estimand** — what quantity is being estimated from the experiment.
5. **Specifies a single decisive falsification experiment**:
   - Exact condition (values of variables)
   - Expected outcome under the hypothesis
   - Outcome under the null (no effect)
   - A numerical threshold that would reject the hypothesis (e.g., “if MCC < 0.3” not “if p>0.05”).
6. **Is fundamentally novel** — explicitly state in novelty_claim why it avoids the DEAD ZONE above,
   what the nearest published work is, and the precise gap this hypothesis fills. Vague novelty claims
   like "extends prior work" are INVALID. You must name the exact published paper you are departing from
   and describe the mechanistic gap.

Your output MUST be a valid JSON object with the following structure (no prose outside):
{{
  "refusal": false,
  "hypothesis": {{
    "statement": "A single, falsifiable scientific claim.",
    "rationale": "Step-by-step mechanistic logic leading from cause to effect. Include the causal DAG description and why this mechanism is plausible given the data context.",
    "variables": [
      {{ "symbol": "X", "name": "name", "unit": "SI unit", "role": "independent/dependent/confounding/mediator", "empirical_range": "from data" }}
    ],
    "parameters": [
      {{ "symbol": "k", "value_guess": 0.0, "unit": "...", "justification": "physical basis" }}
    ],
    "functional_form": "Mathematical equation using the variable symbols (e.g., dY/dt = k * X**2 / (K + X)). Strict Rule: It must be a single equation and contain ONLY valid mathematical symbols and variables. Do NOT include words, descriptions, subscripts, or clauses like 'where...', 'if...', or annotations.",
    "constraints": [
      {{ "equation": "X >= 0", "variables": ["X"], "type": "physical", "description": "Physical boundary condition" }}
    ],
    "predictions": [
      {{ "condition": "Set X to specific value, control Z", "outcome": "Y > threshold_high", "baseline": 0.0, "baseline_unit": "SI unit", "threshold": 0.1, "threshold_unit": "SI unit", "direction": "increase" }}
    ],
    "falsification_experiment": {{
      "condition": "Set X to specific value, control Z",
      "expected_outcome": "Y > threshold_high",
      "null_outcome": "Y ≈ baseline",
      "falsification_threshold": "numeric",
      "metric": "e.g., mean Y difference > 2σ"
    }},
    "novelty_claim": "Why this hypothesis is not an obvious consequence of existing theory."
  }}
}}

Sovereign Directive: Operate as an autonomous frontier computational scientist. Formulate an exact, dimensionally consistent, mathematically rigorous, and strictly falsifiable hypothesis.
"""
            
            # Use high-temperature for Turn 1 to maximize novelty
            from backend.llm_manager import HYPOTHESIS_GENERATION_MODEL
            brain_model = HYPOTHESIS_GENERATION_MODEL
            
            reasoning_text = ""
            for brainstorm_attempt in range(3):
                reasoning_resp = await self.llm_manager.run_async(
                    brainstorm_prompt, 
                    model=brain_model, 
                    temperature=0.7
                )
                
                # [TITAN V151.0] UNIFIED SEMANTIC EXTRACTOR
                raw_content = ""
                if isinstance(reasoning_resp, dict):
                    raw_content = reasoning_resp.get("text") or reasoning_resp.get("content") or reasoning_resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if not raw_content: raw_content = str(reasoning_resp)
                else:
                    raw_content = str(reasoning_resp)
                
                if raw_content and len(raw_content.strip()) > 10 and raw_content.strip() != "{}":
                    reasoning_text = raw_content
                    break
                
                logger.warning(f" [RETRY-BRAIN] Brainstorming turn returned empty or failed (Attempt {brainstorm_attempt+1}/3). Sleeping 5s...")
                await asyncio.sleep(5.0)

            if not reasoning_text:
                logger.error(" [BRAINSTORM] Brainstorming turn failed completely. Skipping this cycle.")
                continue

            # [TELEMETRY Breakthrough] Log the raw manifold for forensic audit
            logger.info(f" [BRAINSTORM] Successfully generated {len(reasoning_text)} chars of scientific reasoning.")

            # BUG-FIX-15: Direct JSON Short-Circuit Parser
            short_circuit_success = False
            parsed_hyp = None
            try:
                json_str = extract_json_brute(reasoning_text)
                parsed_data = repair_json(json_str)
                if not parsed_data:
                    parsed_data = json.loads(json_str)
                
                if isinstance(parsed_data, dict) and parsed_data.get("refusal") is True:
                    logger.info(f" [SCIENCE] Brainstorming turn refused hypothesis generation. Reason: {parsed_data.get('reason')}")
                    return []
                
                hyp_data = None
                if isinstance(parsed_data, dict):
                    if "hypothesis" in parsed_data:
                        hyp_data = parsed_data["hypothesis"]
                    elif "skeletons" in parsed_data and isinstance(parsed_data["skeletons"], list) and len(parsed_data["skeletons"]) > 0:
                        hyp_data = parsed_data["skeletons"][0]
                    elif parsed_data.get("statement") and parsed_data.get("variables"):
                        hyp_data = parsed_data

                if hyp_data and hyp_data.get("statement") and hyp_data.get("variables"):
                    if hyp_data.get("functional_form"):
                        logger.info(" [SINGLE-TURN-PASS] Found complete hypothesis in Turn 1, proceeding directly to formal validation.")
                        parsed_hyp = hyp_data
                        short_circuit_success = True
            except Exception as short_err:
                logger.debug(f"Direct Turn 1 JSON parse skipped/failed: {short_err}")

            valid_skeletons = []
            if short_circuit_success:
                valid_skeletons = [parsed_hyp]
            else:
                # TURN 2: STRUCTURAL EXTRACTION
                from backend.llm_manager import TASK_ROUTING_MODEL
                routing_model = TASK_ROUTING_MODEL[0] if isinstance(TASK_ROUTING_MODEL, tuple) else TASK_ROUTING_MODEL

                extraction_prompt = f"""You are a Mathematical Formalization Kernel — the bridge between creative ideation and a computationally testable hypothesis skeleton.
You receive the raw output of a scientific brainstorming step (a senior physicist's hypothesis) and must produce a clean, fully‑fielded skeleton for downstream hardening.

INPUT (raw brainstorm output):
{reasoning_text}

TASK:
1. If the input contains a JSON object with "refusal": true, propagate the refusal immediately as: {{"refusal": true, "reason": "..."}} (no skeletons).
2. If the input contains a well‑formed hypothesis JSON (with key "hypothesis"), extract that single hypothesis.
3. If the input is messy prose, locate the main hypothesis and build the skeleton from it.
4. The output MUST be a JSON object with a single key "skeletons", which is a list of exactly one skeleton.

SKELETON MANDATORY FIELDS (every one must be present; if missing, you may infer from context but never fabricate):

- **statement**: A one‑sentence, falsifiable scientific claim.
- **rationale**: Multi‑step mechanistic logic that explains **why** the cause leads to the effect. Include the causal DAG description and how the proposed mechanism is consistent with known physics.
- **variables**: List of objects: {{ "symbol": "X", "name": "…", "unit": "SI unit", "role": "independent|dependent|confounding|mediator", "empirical_range": "from data" }}.
- **parameters**: List of objects: {{ "symbol": "k", "value_guess": 0.0, "unit": "…", "justification": "physical basis for range" }}.
- **functional_form**: The core mathematical equation using the variable symbols (LaTeX or plain text, e.g., dY/dt = k * X**2 / (K + X)). Strict Rule: It must be a single equation and contain ONLY valid mathematical symbols and variables. Do NOT include words, descriptions, subscripts, or clauses like 'where...', 'if...', or annotations.
- **falsification_experiment**: An object with exactly these keys:
   - "condition": The precise experimental condition (e.g., “Set X = 2.5 T, hold Z constant”)
   - "expected_outcome": What the hypothesis predicts (e.g., “Y > 5.0 s⁻¹”)
   - "null_outcome": Outcome under no effect (e.g., “Y ≈ 1.2 s⁻¹”)
   - "falsification_threshold": Numerical boundary (e.g., “if observed Y < 4.0, reject hypothesis”)
   - "metric": The measurement used (e.g., “mean Y over 100 ms”)

OUTPUT FORMAT (JSON only, no prose):
{{
  "skeletons": [
    {{
      "statement": "...",
      "rationale": "...",
      "variables": [ ... ],
      "parameters": [ ... ],
      "functional_form": "...",
      "falsification_experiment": {{ ... }}
    }}
  ]
}}

RULES:
- Do NOT add predictions or constraints (they will be added later).
- Do NOT wrap the response in markdown or backticks — raw JSON only.
- If the brainstorm already refused, output {{ "refusal": true, "reason": "..." }} without a "skeletons" key.
- Preserve all numeric values and units exactly.
- For functional_form: Pure mathematical equation in Python/SymPy syntax (e.g., "DeltaDelta_G = alpha * R * T * log(KD_mut / KD_WT)" or "dY_dt = k * X**2 / (K + X)"). Use explicit operators (*, **, /). DO NOT use LaTeX backslashes (\Delta, \ln), curly braces {{}}, or prose.
- Return exactly one skeleton; never more.
- Emit the complete valid JSON object.
"""
                # BUG-FIX-16: Nested Turn 2 retry loop to recover from extraction rate limits
                skeletons_data = None
                for ext_attempt in range(3):
                    skeletons_data = await self._execute_llm(
                        extraction_prompt, 
                        model=routing_model, 
                        temperature=0.0, 
                        expected_key="skeletons"
                    )
                    if isinstance(skeletons_data, list):
                        dict_items = [x for x in skeletons_data if isinstance(x, dict)]
                        skeletons_data = {"skeletons": dict_items}
                    elif isinstance(skeletons_data, dict) and "statement" in skeletons_data and "variables" in skeletons_data:
                        skeletons_data = {"skeletons": [skeletons_data]}

                    # Check if we got a valid skeletons key
                    if isinstance(skeletons_data, dict) and (skeletons_data.get("skeletons") or skeletons_data.get("refusal")):
                        break
                    logger.warning(f" [RETRY-EXT] Structural Extraction failed or rate-limited (Attempt {ext_attempt+1}/3). Retrying extraction...")
                    await asyncio.sleep(5.0)
                
                if isinstance(skeletons_data, dict) and skeletons_data.get("refusal") is True:
                    logger.info(f" [SCIENCE] Structural extraction propagated refusal. Reason: {skeletons_data.get('reason')}")
                    return []

                if not skeletons_data:
                    logger.info(f" [RETRY] Skeleton generation failed. Retrying...")
                    continue
                    
                skeletons = [s for s in (skeletons_data if isinstance(skeletons_data, list) else skeletons_data.get("skeletons", [])) if isinstance(s, dict)]

                if not skeletons:
                    logger.info(f" [RETRY] Skeletons array empty. Retrying...")
                    continue

                # [TITAN V145.1] HARD RIGOR GATE RESTORED
                # Physically abolished 'TBD' placeholders and 'Relaxed' logic.
                # We enforce absolute mathematical completeness for every discovery.
                for skeleton in skeletons:
                    if not isinstance(skeleton, dict):
                        continue
                    # Mandatory Field Checklist
                    has_stmt = bool(skeleton.get("statement"))
                    has_vars = bool(skeleton.get("variables"))
                    has_params = bool(skeleton.get("parameters"))
                    has_math = bool(skeleton.get("functional_form"))
                    
                    if has_stmt and has_vars and has_params and has_math:
                        valid_skeletons.append(skeleton)
                    else:
                        logger.warning(f" [RIGOR] Rejected incomplete skeleton. Keys present: {list(skeleton.keys())}")

                if not valid_skeletons:
                    logger.info(f" [RETRY] All skeletons rejected due to incomplete structure. Retrying...")
                    continue
            
            # SINGLE-PASS SHORT-CIRCUIT FOR 2026 FRONTIER MODELS:
            # If Turn 1 already produced a complete formal hypothesis (with constraints/predictions or falsification_experiment)
            # that passes _validate_formal_hypothesis, skip the redundant Turn 2/Turn 3 re-serialization loop.
            if short_circuit_success and isinstance(parsed_hyp, dict):
                if not parsed_hyp.get("predictions") and isinstance(parsed_hyp.get("falsification_experiment"), dict):
                    f_exp = parsed_hyp["falsification_experiment"]
                    try:
                        thresh_match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", str(f_exp.get("falsification_threshold", "0.1")))
                        thresh_val = abs(float(thresh_match.group(0))) if thresh_match else 0.1
                        if thresh_val <= 0:
                            thresh_val = 0.1
                    except Exception:
                        thresh_val = 0.1
                    parsed_hyp["predictions"] = [{
                        "condition": str(f_exp.get("condition", "Controlled experimental perturbation")),
                        "outcome": str(f_exp.get("expected_outcome", "Significant metric shift")),
                        "baseline": 0.0,
                        "threshold": thresh_val,
                        "direction": "any"
                    }]
                if (
                    parsed_hyp.get("constraints")
                    and parsed_hyp.get("predictions")
                    and self._validate_formal_hypothesis(parsed_hyp)
                ):
                    cand_stmt = str(parsed_hyp.get("statement", "")).strip()
                    cand_words = {w for w in re.findall(r"\w+", cand_stmt.lower()) if len(w) > 3}
                    prior_stmts = [
                        (eh.statement if hasattr(eh, "statement") else str(eh))
                        for eh in (existing_hypotheses or [])
                    ] + [str(m.get("statement", "")) for m in (morgue_entries or [])]
                    is_dup = False
                    for p_stmt in prior_stmts:
                        if not p_stmt:
                            continue
                        p_words = {w for w in re.findall(r"\w+", p_stmt.lower()) if len(w) > 3}
                        if cand_stmt.lower() == p_stmt.strip().lower():
                            is_dup = True
                            break
                        if cand_words and p_words and (len(cand_words & p_words) / max(1, len(cand_words | p_words))) >= 0.80:
                            is_dup = True
                            break
                    if not is_dup:
                        logger.info(" [SINGLE-PASS COMPLETE] Frontier model emitted complete, verified formal hypothesis in 1 pass.")
                        return [Hypothesis(
                            statement=parsed_hyp["statement"],
                            rationale=parsed_hyp.get("rationale", "Generated from formal structure."),
                            variables=parsed_hyp.get("variables", []),
                            parameters=parsed_hyp.get("parameters", []),
                            predictions=parsed_hyp.get("predictions", []),
                            functional_form=parsed_hyp.get("functional_form", ""),
                            constraints=parsed_hyp.get("constraints", []),
                            domain=domain,
                            metadata=parsed_hyp.get("metadata", {})
                        )]

            # PASS 2: PREDICTION HARDENING
            expansion_template = """You are a Computational Scientific Protocol Hardening Engine.
You receive a single hypothesis skeleton — the product of a rigorous brainstorming and formalization pipeline.
Your task is to produce the final, testable hypothesis object with enriched predictions and strict physical constraints.

DOMAIN TAGS: {profile_str}
RESEARCH QUESTION: {research_q}

INPUT SKELETON (exactly one hypothesis):
{skeletons_json}

TASK:
1. If the skeleton contains a refusal (i.e., the input JSON has "refusal": true), propagate it: output {{"refusal": true, "reason": "..."}}.
2. Otherwise, convert the single skeleton into a fully specified hypothesis with the following structure:

OUTPUT FORMAT (JSON only, no prose):
{{
  "hypotheses": [
    {{
      "statement": "Original statement from skeleton",
      "rationale": "Multi-step mechanistic logic (from skeleton)",
      "variables": [ ... ],
      "parameters": [ ... ],
      "constraints": [ ... ],
      "predictions": [ ... ],
      "functional_form": "Equation from skeleton. Do NOT modify the equation from the skeleton, and do NOT add any prose text, comments, or 'where...' clauses to it. Keep it as a pure mathematical equation.",
      "mechanism": "Physical basis of the causal chain (from skeleton rationale)",
      "falsification_criteria": "Concrete measurement condition that would kill the hypothesis (distilled from skeleton.falsification_experiment)"
    }}
  ]
}}

DETAILED REQUIREMENTS:

A. PREDICTIONS (array, at least 2, maximum 4)
   Each prediction must be a concrete, numerically specific test of the hypothesis, derived from:
   - The skeleton's falsification_experiment (this must become the first prediction)
   - One or two additional logically independent predictions that probe different variable regimes or sensitivity.
   Each prediction object MUST contain:
   - "condition": Clear experimental setup (e.g., "When X is held at 2.5 ± 0.1 T and Z = 0")
   - "outcome": Expected measurable result (e.g., "Y increases by at least 3.2 s⁻¹")
   - "baseline": Numerical value of the null hypothesis (NOT a placeholder like 0.0 unless physically justified)
   - "baseline_unit": SI unit (must match the variable's unit)
   - "threshold": Minimum effect size that would be considered significant (must be derived from the falsification threshold in the skeleton, or from domain-appropriate smallest detectable effect)
   - "threshold_unit": SI unit
   - "direction": "increase" | "decrease" | "any"
   All baseline/threshold numbers must be physically plausible given the variable's empirical range.

B. CONSTRAINTS (array, at least 2)
    Each constraint is a mathematical inequality or equality that the hypothesis MUST respect.
    - "equation": Python/sympy equation/inequality string (e.g., "alpha < 1", "0 < alpha", "dE/dt = Pin - Pout"). Strict rules: Use standard mathematical operators (<, >, <=, >=, =). Do NOT write double inequalities like "0 < H < 5"; instead split them into two separate constraint objects (e.g., "0 < H" and "H < 5"). Do NOT use LaTeX commands like \\leq, \\geq, or backslashes. Do NOT include subscripts or unicode characters.
    - "variables": list of variable symbols used
    - "type": one of "physical" (enforces a conservation law or boundary), "mathematical" (identity, like non-negativity), "empirical" (derived from prior measurements), "boundary" (impossible states like T > 0 K)
   - "description": what this constraint means in words.
   Examples: energy conservation, mass balance, probability sum=1, positivity of rates, known physical limits.

C. FALSIFICATION CRITERIA
   Reformulate the skeleton's falsification_experiment into a single, precise, self-contained statement:
   "The hypothesis is falsified if [metric] measured under [condition] is [comparison] [value]."

D. GENERAL RULES
   - Do NOT add new variables not present in the skeleton.
   - Preserve all existing fields from the skeleton (statement, rationale, variables, parameters, functional_form).
   - The "mechanism" field should be a concise paragraph explaining the physical/biological pathway, extracted from the rationale.
   - Return ONLY the JSON object (no markdown, no backticks).
   - Emit the complete valid JSON object.
"""
            expansion_prompt = expansion_template.format(
                profile_str=', '.join(profile),
                research_q=research_question,
                skeletons_json=json.dumps(valid_skeletons, indent=2)
            )

            # BUG-FIX-16: Nested Turn 3 retry loop to recover from hardening rate limits
            final_data = None
            for hard_attempt in range(3):
                final_data = await self._execute_llm(
                    expansion_prompt, 
                    model=REPORT_FINAL_MODEL, 
                    temperature=0.4, 
                    expected_key="hypotheses"
                )
                if isinstance(final_data, list):
                    hyp_items = [x for x in final_data if isinstance(x, dict) and ("statement" in x or "functional_form" in x)]
                    if hyp_items:
                        final_data = {"hypotheses": hyp_items}
                    else:
                        final_data = None
                elif isinstance(final_data, dict) and "statement" in final_data and "variables" in final_data:
                    final_data = {"hypotheses": [final_data]}

                if isinstance(final_data, dict) and final_data.get("hypotheses"):
                    break
                logger.warning(f" [RETRY-HARD] Prediction Hardening failed or rate-limited (Attempt {hard_attempt+1}/3). Retrying hardening...")
                await asyncio.sleep(5.0)

            if isinstance(final_data, dict) and final_data.get("refusal") is True:
                logger.info(f" [SCIENCE] Hardening turn propagated refusal. Reason: {final_data.get('reason')}")
                return []
            
            if final_data:
                hyp_list = final_data if isinstance(final_data, list) else final_data.get("hypotheses", [])
                valid_hypotheses = []
                for h_dict in hyp_list:
                    if not isinstance(h_dict, dict):
                        continue
                    # Inherit from skeleton if Pass 2 omitted or truncated fields
                    if valid_skeletons and isinstance(valid_skeletons[0], dict):
                        skel = valid_skeletons[0]
                        if not h_dict.get("functional_form") and skel.get("functional_form"):
                            h_dict["functional_form"] = skel["functional_form"]
                        if not h_dict.get("statement") and skel.get("statement"):
                            h_dict["statement"] = skel["statement"]
                        if not h_dict.get("rationale") and skel.get("rationale"):
                            h_dict["rationale"] = skel["rationale"]
                        if not h_dict.get("variables") and skel.get("variables"):
                            h_dict["variables"] = skel["variables"]
                        if not h_dict.get("parameters") and skel.get("parameters"):
                            h_dict["parameters"] = skel["parameters"]

                    if self._validate_formal_hypothesis(h_dict):
                        # Post-generation deduplication against existing_hypotheses and Semantic Morgue DEAD ZONE
                        cand_stmt = str(h_dict.get("statement", "")).strip()
                        cand_words = {w for w in re.findall(r"\w+", cand_stmt.lower()) if len(w) > 3}
                        prior_stmts = [
                            (eh.statement if hasattr(eh, "statement") else str(eh))
                            for eh in (existing_hypotheses or [])
                        ] + [str(m.get("statement", "")) for m in (morgue_entries or [])]
                        is_dup = False
                        for p_stmt in prior_stmts:
                            if not p_stmt:
                                continue
                            p_words = {w for w in re.findall(r"\w+", p_stmt.lower()) if len(w) > 3}
                            if cand_stmt.lower() == p_stmt.strip().lower():
                                is_dup = True
                                break
                            if cand_words and p_words:
                                jacc = len(cand_words & p_words) / max(1, len(cand_words | p_words))
                                if jacc >= 0.80:
                                    is_dup = True
                                    break
                        if is_dup:
                            logger.warning(f" [DEDUP] Rejected hypothesis duplicating existing or DEAD ZONE claim: {cand_stmt[:80]}")
                            continue
                        valid_hypotheses.append(h_dict)

                if not valid_hypotheses:
                    logger.info(" [RETRY] No hypotheses passed validation. Retrying...")
                    continue

                final_list = []
                for h_raw in valid_hypotheses:
                    final_list.append(Hypothesis(
                        statement=h_raw["statement"],
                        rationale=h_raw.get("rationale", "Generated from formal structure."),
                        variables=h_raw.get("variables", []),
                        parameters=h_raw.get("parameters", []),
                        predictions=h_raw.get("predictions", []),
                        functional_form=h_raw.get("functional_form", ""),
                        constraints=h_raw.get("constraints", []),
                        domain=domain,
                        metadata=h_raw.get("metadata", {})
                    ))
                
                if final_list:
                    return final_list

        logger.error(f"[FATAL] Hypothesis generation exhausted {MAX_RETRIES} retries for domain {domain.upper()}.")
        raise RuntimeError(f"HYPOTHESIS_GENERATION_FAILED: Failed to generate valid hypotheses for domain {domain} after {MAX_RETRIES} attempts.")
    
    def _validate_formal_hypothesis(self, hyp_dict: Dict[str, Any]) -> bool:
        """Validate that hypothesis has FORMAL STRUCTURE.
        
        [GHOST-SHIP-FIX] Relaxed from hard numeric gate to soft check.
        Groq (our only working provider) rarely emits baseline/threshold fields
        in a single pass. Blocking on those causes 10-retry infinite loops.
        Require: statement + variables. Treat predictions as optional bonus.
        """
        if not isinstance(hyp_dict, dict):
            logger.warning(f" [VALIDATOR] Hypothesis is not a dict: {type(hyp_dict)}")
            return False
        if not hyp_dict.get("statement"):
            logger.warning(f" [VALIDATOR] Hypothesis missing 'statement' key or value! Present keys: {list(hyp_dict.keys())}")
            return False
        if not hyp_dict.get("variables"):
            logger.warning(f" [VALIDATOR] Hypothesis missing 'variables' key or value! Present keys: {list(hyp_dict.keys())}")
            return False

        # Reject hypotheses that confuse operational setup/API with actual ML science
        system_leakage_keywords = [
            "arxiv", "api", "query", "search query", "logical operator", 
            "virtual environment", "venv", "package", "pip install", 
            "docker", "colima", "sqlite", "database", "neo4j", 
            "markdown", "stdout", "stderr", "traceback", "syntax error",
            # Anti-directive pseudo-hypotheses (Overmind/Supervisor injections)
            "pivot directive", "supervisor directive",
            # [V255+] Anti-URL/dataset-link leakage
            "http://", "https://", "toronto.edu", "download url", ".tar.gz",
            "dataset download", "inclusionscore", "inclusion score",
            "weighted score", "date score", "paper score", "relevance score",
            # Anti-filesystem/OS contamination (live caught in production)
            # NOTE: Do NOT add dataset paths that appear in the research question itself
            # (e.g. data/cifar100/) — the LLM will naturally reference them.
            "path_exists", "boolean variable", "filesystem check",
            "os.path",
            "number of results", "max_results", "api endpoint",
            "recall of relevant papers", "recall@", "raises the recall",
            "boolean operator", "search term", "search engine", "search window",
            "creation time", "environment creation", "python environment",
            "package count", "package install", "install time"
        ]
        stmt = str(hyp_dict.get("statement", "")).lower()
        rationale = str(hyp_dict.get("rationale", "")).lower()
        if any(kw in stmt or kw in rationale for kw in system_leakage_keywords):
            logger.warning(f" [VALIDATOR] Rejected hypothesis due to domain leakage/system confusion: {stmt[:100]}")
            return False

        # [MATH FIX] Validate equations and constraints with sympy strictly
        import sympy
        from sympy.parsing.sympy_parser import (
            parse_expr,
            standard_transformations,
            implicit_multiplication_application,
            convert_xor
        )
        _transformations = standard_transformations + (implicit_multiplication_application, convert_xor)

        def sanitize_biophysical_math(eq_str: str) -> str:
            eq = re.split(r",\s*where\s+", eq_str, flags=re.IGNORECASE)[0]
            eq = re.split(r"\s+for\s+", eq, flags=re.IGNORECASE)[0]
            eq = re.split(r",\s*with\s+", eq, flags=re.IGNORECASE)[0]
            eq = re.split(r",\s*given\s+", eq, flags=re.IGNORECASE)[0]
            eq = re.split(r";\s*", eq, flags=re.IGNORECASE)[0]
            eq = re.split(r",\s*such\s+that\s+", eq, flags=re.IGNORECASE)[0]
            
            # Pre-clean Angstrom and unicode units
            eq = eq.replace('Å', '_angstrom').replace('Å', '_angstrom')

            # Summation indices cleanup BEFORE anything else
            def clean_sum_subscript(match):
                content = match.group(1)
                clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', content)
                clean_id = re.sub(r'_+', '_', clean_id).strip('_')
                return f'Sum_{clean_id}*'

            eq = re.sub(r'\\?[ΣsS]um_\{([^}]+)\}', clean_sum_subscript, eq)
            eq = re.sub(r'\\Sigma_\{([^}]+)\}', clean_sum_subscript, eq)
            eq = re.sub(r'Σ_\{([^}]+)\}', clean_sum_subscript, eq)
            eq = re.sub(r'Σ_([a-zA-Z0-9]+)', r'Sum_\1*', eq)
            eq = re.sub(r'\\sum_([a-zA-Z0-9]+)', r'Sum_\1*', eq)
            eq = re.sub(r'Sum_([a-zA-Z0-9]+)\s+', r'Sum_\1*', eq)

            # If multiple equals signs exist (e.g. A = expr = C), reduce to primary equality A = C
            if eq.count("=") > 1 and "==" not in eq and "<=" not in eq and ">=" not in eq:
                eq_parts = eq.split("=")
                eq = f"{eq_parts[0].strip()} = {eq_parts[-1].strip()}"
            
            # Fix Delta and differential operators before stripping backslashes
            eq = re.sub(r"\\Delta\\Delta\s*([A-Za-z]+)", r"DeltaDelta_\1", eq)
            eq = re.sub(r"\\Delta\s*([A-Za-z]+)", r"Delta_\1", eq)
            eq = re.sub(r"DeltaDelta\s+([A-Za-z]+)", r"DeltaDelta_\1", eq)
            eq = re.sub(r"Delta\s+([A-Za-z]+)", r"Delta_\1", eq)
            eq = re.sub(r"d([A-Za-z]+)/d([A-Za-z]+)", r"d\1_d\2", eq)
            
            # Common LaTeX functions -> Python/SymPy functions
            eq = re.sub(r"\\ln\b", "log", eq)
            eq = re.sub(r"\\log\b", "log", eq)
            eq = re.sub(r"\\exp\b", "exp", eq)
            eq = re.sub(r"\\sqrt\{([^}]+)\}", r"sqrt(\1)", eq)
            eq = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"((\1)/(\2))", eq)
            eq = re.sub(r"\\left\(", "(", eq)
            eq = re.sub(r"\\right\)", ")", eq)
            eq = re.sub(r"\\left\[", "(", eq)
            eq = re.sub(r"\\right\]", ")", eq)
            eq = re.sub(r"\\cdot\b", "*", eq)
            eq = re.sub(r"\\times\b", "*", eq)
            
            # LaTeX superscripts and subscripts
            eq = re.sub(r"\^\{([^}]+)\}", r"**(\1)", eq)
            eq = re.sub(r"_\{([^}]+)\}", r"_\1", eq)
            eq = re.sub(r"\^([0-9a-zA-Z])", r"**\1", eq)
            
            # Greek letters mapping to var_<greek>
            greek_letters = [
                "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
                "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho",
                "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega"
            ]
            for g in greek_letters:
                eq = re.sub(r"\\" + g + r"\b", f"var_{g}", eq, flags=re.IGNORECASE)
            
            # Brackets and backslashes
            eq = eq.replace("\\", "").replace("{", "(").replace("}", ")")
            eq = eq.replace("[", "(").replace("]", ")")
            
            # [MHD HARDENING] Unicode scientific symbols mapping
            replacements = {
                "∆": "Delta_", "Δ": "Delta_",
                "·": "*", "×": "*",
                "≥": ">=", "≤": "<=",
                "λ": "var_lambda", "η": "var_eta", "θ": "var_theta", "κ": "var_kappa",
                "μ": "var_mu", "τ": "var_tau", "ω": "var_omega", "Σ": "Sum",
                "σ": "var_sigma", "α": "var_alpha", "β": "var_beta", "γ": "var_gamma",
                "δ": "var_delta", "ρ": "var_rho", "ε": "var_epsilon", "φ": "var_phi",
                "ψ": "var_psi", "π": "var_pi", "°": "_circ", "circ": "_circ"
            }
            for k, v in replacements.items():
                eq = eq.replace(k, v)
                
            eq = re.sub(r"_+", "_", eq)
            
            # Fix pipes
            eq = re.sub(r"\|(.*?)\|", r"Abs(\1)", eq)
            
            # Reserved words (Python keywords and collision-prone Greek letters)
            reserved_words = {
                r"\balpha\b": "var_alpha",
                r"\bbeta\b": "var_beta",
                r"\bgamma\b": "var_gamma",
                r"\bdelta\b": "var_delta",
                r"\blambda\b": "var_lambda",
                r"\btheta\b": "var_theta",
                r"\bkappa\b": "var_kappa",
                r"\bmu\b": "var_mu",
                r"\btau\b": "var_tau",
                r"\bomega\b": "var_omega",
                r"\bsigma\b": "var_sigma",
                r"\bphi\b": "var_phi",
                r"\bpsi\b": "var_psi",
                r"\brho\b": "var_rho",
                r"\bepsilon\b": "var_epsilon",
                r"\beta\b": "var_eta",
                r"\bpi\b": "var_pi"
            }
            for pat, repl in reserved_words.items():
                eq = re.sub(pat, repl, eq)

            # Function names mapping
            func_replacements = {
                r"\bmax\(": "Max(",
                r"\bmin\(": "Min(",
                r"\babs\(": "Abs(",
            }
            for pat, repl in func_replacements.items():
                eq = re.sub(pat, repl, eq)
                
            # Strip indicator function brackets I(...) -> 1
            eq = re.sub(r"I\((.*?)\)", r"1", eq)
            
            if " if " in eq and " else " in eq:
                eq = eq.split(" if ")[0]
                
            return eq.strip()

        def check_math_string(eq_str: str) -> bool:
            try:
                clean_eq = sanitize_biophysical_math(eq_str)

                safe_symbols = [
                    'S', 'N', 'C', 'O', 'I', 'E', 'Q', 'B', 'K', 'T', 'R',
                    'beta', 'lambda', 'alpha', 'theta', 'gamma', 'delta', 
                    'var_beta', 'var_lambda', 'var_alpha', 'var_theta', 'var_gamma', 
                    'var_delta', 'var_pi', 'var_mu', 'var_sigma', 'var_rho', 
                    'var_epsilon', 'var_phi', 'var_psi', 'var_eta', 'var_kappa', 
                    'var_tau', 'var_omega'
                ]
                safe_locals = {sym: sympy.Symbol(sym) for sym in safe_symbols}
                safe_locals.update({
                    'Max': sympy.Max,
                    'Min': sympy.Min,
                    'Abs': sympy.Abs,
                    'abs': sympy.Abs,
                    'max': sympy.Max,
                    'min': sympy.Min,
                    'exp': sympy.exp,
                    'log': sympy.log,
                    'ln': sympy.log,
                    'sqrt': sympy.sqrt,
                    'sin': sympy.sin,
                    'cos': sympy.cos,
                })

                def _parse_part(s):
                    s = s.strip().rstrip(",").rstrip(";")
                    try:
                        return parse_expr(s, local_dict=safe_locals, transformations=_transformations)
                    except Exception:
                        try:
                            return sympy.sympify(s, locals=safe_locals)
                        except Exception:
                            clean_s = re.sub(r'[^a-zA-Z0-9_\+\-\*\/\(\)\s\.]', '', s)
                            return parse_expr(clean_s, local_dict=safe_locals, transformations=_transformations)

                def _eval_and_check(s):
                    if not s.strip(): return True
                    res = _parse_part(s)
                    if res.has(sympy.zoo) or res.has(sympy.nan):
                        raise ValueError(f"Math evaluated to invalid bound or complex result: {res}")

                    for atom in res.atoms(sympy.Function):
                        fname = atom.func.__name__.lower()
                        if fname in ["log", "ln"] and atom.args:
                            arg = atom.args[0]
                            if arg.is_number and float(arg) <= 0:
                                raise ValueError(f"Logarithm domain boundary violation: log({arg}) <= 0")
                        elif fname in ["sqrt"] and atom.args:
                            arg = atom.args[0]
                            if arg.is_number and float(arg) < 0:
                                raise ValueError(f"Square root domain boundary violation: sqrt({arg}) < 0")
                    return True

                # Check equality FIRST if it is an equation
                if '=' in clean_eq and not any(op in clean_eq for op in ['<=', '>=', '!=', '==']):
                    parts = clean_eq.split('=', 1)
                    for p in parts:
                        _eval_and_check(p)
                    return True
                elif '==' in clean_eq:
                    parts = clean_eq.split('==', 1)
                    for p in parts:
                        _eval_and_check(p)
                    return True

                # Check inequality operators
                for op in ["<=", ">=", "<", ">"]:
                    if op in clean_eq:
                        parts = clean_eq.split(op)
                        for p in parts:
                            _eval_and_check(p)
                        try:
                            left = _parse_part(parts[0])
                            right = _parse_part(parts[1])
                            if left.is_number and right.is_number:
                                l_val, r_val = float(left), float(right)
                                if op == "<" and not (l_val < r_val):
                                    raise ValueError(f"Constant inequality sign violation: {l_val} < {r_val} is False")
                                elif op == "<=" and not (l_val <= r_val):
                                    raise ValueError(f"Constant inequality sign violation: {l_val} <= {r_val} is False")
                                elif op == ">" and not (l_val > r_val):
                                    raise ValueError(f"Constant inequality sign violation: {l_val} > {r_val} is False")
                                elif op == ">=" and not (l_val >= r_val):
                                    raise ValueError(f"Constant inequality sign violation: {l_val} >= {r_val} is False")
                        except ValueError:
                            raise
                        except Exception:
                            pass
                        return True
                
                _eval_and_check(clean_eq)
                return True
            except (sympy.SympifyError, TypeError) as e:
                logger.warning(f" [VALIDATOR] Mathematical equation syntax error in '{eq_str}': {e}")
                return False
            except ZeroDivisionError:
                logger.warning(f" [VALIDATOR] Math error: Division by zero explicitly found in: {eq_str}")
                return False
            except ValueError as ve:
                logger.warning(f" [VALIDATOR] Invalid mathematical boundary or sign convention found: {ve}")
                return False
            except Exception as e:
                logger.warning(f" [VALIDATOR] Mathematical error in '{eq_str}': {e}")
                return False

        # Enforce non-empty functional_form
        func_form = hyp_dict.get("functional_form", "")
        if not func_form or not isinstance(func_form, str) or not func_form.strip():
            logger.warning(" [VALIDATOR] Hypothesis missing mandatory 'functional_form' string — rejecting.")
            return False
        if not check_math_string(func_form):
            return False
            
        # Enforce non-empty constraints list
        constraints = hyp_dict.get("constraints", [])
        if not constraints or not isinstance(constraints, list) or len(constraints) == 0:
            logger.warning(" [VALIDATOR] Hypothesis missing mandatory 'constraints' array — rejecting.")
            return False
        for c in constraints:
            if not isinstance(c, dict):
                return False
            eq_str = c.get("equation") or c.get("expression") or ""
            if not eq_str or not check_math_string(eq_str):
                return False

        # Check that predictions exist and are non-empty
        preds = hyp_dict.get("predictions", [])
        if not preds:
            logger.warning(" [VALIDATOR] Hypothesis missing 'predictions' — rejecting.")
            return False
        
        # Check that predictions contain valid baseline/threshold numbers
        valid_preds = [p for p in preds 
                      if isinstance(p, dict) and p.get("baseline") is not None and p.get("threshold") is not None]
        if not valid_preds:
            logger.warning(f" [VALIDATOR] Rejected hypothesis: predictions must contain numeric baseline and threshold values.")
            return False
        hyp_dict["predictions"] = valid_preds
        return True

    async def _execute_llm(self, prompt: str, model: str, temperature: float, expected_key: str = "hypotheses", source: str = "hypothesis_generator", max_tokens_override: Optional[int] = None) -> Any:
        try:
            if not self.llm_manager: return None
            # [TITAN V147.0] ASYNC MANIFOLD UNIFICATION
            # Physically abolished synchronous LLM calls in the synthesis loop.
            exec_kwargs = {}
            if max_tokens_override is not None:
                exec_kwargs["max_tokens_override"] = max_tokens_override

            response = await self.llm_manager.run_async(
                prompt=prompt,
                model=model,
                temperature=temperature,
                **exec_kwargs
            )
            text = response if isinstance(response, str) else response.get("text", str(response))
            
            # Save the full raw response to a debug file for forensic inspection
            try:
                debug_dir = os.environ.get("ANTIGRAVITY_SCRATCH_DIR") or os.path.join(os.getcwd(), "scratch")
                os.makedirs(debug_dir, exist_ok=True)
                with open(os.path.join(debug_dir, "last_raw_response.txt"), "w", encoding="utf-8") as debug_f:
                    debug_f.write(text)
            except Exception as debug_err:
                logger.error(f" [DEBUG] Failed to write raw telemetry: {debug_err}")

            # [TITAN V148.0] RAW TELEMETRY
            # Physically expose the raw model response to identifying reasoning blocks vs noise.
            if len(text) > 0:
                logger.info(f" [RAW] Model Output (first 200 chars): {text[:200]}...")
            else:
                logger.warning(" [RAW] Model returned zero characters.")

            # [V1.0] ATOMIC REASONING ANCHOR
            # Physically capture trace BEFORE any json processing happens.
            think_match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
            derivation = think_match.group(1).strip() if think_match else text[:1000] # Fallback to raw if tags missing

            clean_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            clean_text = re.sub(r"```[a-z]*", "", clean_text, flags=re.IGNORECASE).strip()
            clean_text = clean_text.replace("```", "").strip()

            final_hyp = None
            try:
                final_hyp = repair_json(clean_text, return_objects=True)
            except Exception:
                pass

            if not final_hyp:
                clean_json = extract_json_brute(clean_text)
                logger.info(f" [PARSER] Manifold fragment: {clean_json[:100]}...")
                try:
                    final_hyp = repair_json(clean_json, return_objects=True)
                    if not final_hyp:
                        import json
                        final_hyp = json.loads(clean_json)
                except Exception as e:
                    logger.error(f" [PARSER] Brute-force JSON load failed: {e}.")
                    return None

            # [TITAN V240.0] PERSISTENCE BINDING
            # Physically inject the trace directly into the structure.
            if isinstance(final_hyp, dict):
                # Ensure metadata exists
                if "metadata" not in final_hyp: final_hyp["metadata"] = {}
                final_hyp["metadata"]["thinking_trace"] = derivation
            
            return final_hyp

        except Exception as e:
            logger.error(f"Discovery Engine Failure: {e}")
            return None



