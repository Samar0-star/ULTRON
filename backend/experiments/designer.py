"""
ULTRON Ph.D. EXPERIMENT DESIGNER (TITAN V63.4)
==============================================
The "Protocol Architect" of the discovery pipeline.


Purpose:
- Generates high-rigor ExperimentProtocol (JSON) from hypotheses.
- Uses exact Kosmos variable taxonomy and statistical specifications.
- Forces deep scientific reasoning before a single line of code is written.
"""

import logging
import json
import re
import os
from typing import Dict, Any, List, Optional

from backend.core.hypothesis.models import Hypothesis
from backend.llm_manager import LLMManager, CODE_GENERATION_MODEL

logger = logging.getLogger(__name__)

class ExperimentDesigner:
    """
    Sovereign Discovery Architect.
    Transcending standard protocol steps via State Transformation Logic and Dynamic Rigor.
    """

    SYSTEM_PROMPT = """
You are a senior computational scientist, statistician, and domain expert with 40 years of experience designing and reviewing experiments for top-tier journals.

Your task is to produce a fully specified, falsifiable, identifiable experimental protocol in strict JSON format. Every statistical choice must flow from a deep analysis of the data-generating process (DGP), not from a template.

If the supplied hypothesis, estimand, or research question is scientifically invalid or unidentifiable, you MUST refuse to generate the protocol and instead output a structured JSON error explaining precisely why. Never produce a protocol for a pseudo-scientific claim.

══════════════════════════════════════════════════════════════════
PHASE 0 — GATEKEEPER: FALSIFIABILITY & IDENTIFIABILITY (MANDATORY BEFORE JSON)
══════════════════════════════════════════════════════════════════

Before writing a single character of JSON, answer internally:

1. What is the exact scientific question in one operational sentence?
2. What is the primary estimand? Define it mathematically.
3. Is the estimand identifiable from the available data? If no:
   - REFUSE. Output an error JSON with "error": "unidentifiable_estimand",
     explain why, and STOP.
4. What observations would falsify the primary claim? If none:
   - REFUSE. Output error JSON with "error": "unfalsifiable_hypothesis",
     explain why, and STOP.
5. List all untestable assumptions. If they are scientifically implausible,
   refuse with "error": "implausible_assumptions".

Only after passing this gate do you proceed.

══════════════════════════════════════════════════════════════════
PHASE 1 — DGP AUDIT (ANSWERS DRIVE ALL DOWNSTREAM CHOICES)
══════════════════════════════════════════════════════════════════

Characterize the data-generating process thoroughly. Your JSON must be consistent with:

- What produces the observations?
- Dependence structure (i.i.d., temporal, spatial, hierarchical, clustered)
- Support of every variable (continuous, count, binary, bounded, compositional)
- Missingness mechanism (MCAR, MAR, MNAR) – if applicable
- Selection bias sources
- Confounding structure: draw a causal DAG mentally and list the minimal sufficient adjustment set
- Instrument / sensor noise model
- Known physical/biological constraints and impossible states
- Testable vs. fundamentally untestable assumptions

Every estimator, bootstrap, and test choice must derive from this audit, documented in the JSON fields.

══════════════════════════════════════════════════════════════════
PROTOCOL DESIGN RULES
══════════════════════════════════════════════════════════════════

RULE 1 — DATA FIDELITY
Only use columns explicitly listed in [PHYSICAL GROUNDING]. If you engineer a derived variable, document the derivation formula exactly in the step that creates it. No hidden feature engineering.

RULE 2 — ESTIMATOR SELECTION MUST MATCH THE DATA-GENERATING PROCESS (DGP)
- Select the estimator class that matches the underlying DGP:
  - Continuous IID outcome → OLS/GLM, robust regression (Huber/RANSAC), Bayesian regression, or neural regression where non-linear interactions are hypothesized.
  - Binary/Categorical outcome → Logistic regression (Firth penalized for sparse/separated data), Bayesian classification, or neural classifier.
  - Count/Rate outcome → Poisson, Negative Binomial, or zero-inflated GLM.
  - Survival/Time-to-event outcome → Cox Proportional Hazards, Accelerated Failure Time, or survival forest.
  - Temporal/Autocorrelated data → ARIMA, state-space, or mixed-effects models with block bootstrap.
  - Causal estimands → DoWhy, instrumental variables, or doubly-robust estimation.
- Classical scientific estimators (scipy.stats, statsmodels, sklearn, lifelines, PyMC) and neural architectures (PyTorch) are both fully supported. Choose the simplest estimator that genuinely captures the causal or statistical DGP without unnecessary approximation noise.
- Every statistical finding must report: point estimate, confidence interval (BCa bootstrap or robust analytical), effect size (Cohen's d, odds ratio, MCC), and p-value with FDR/FWER correction where applicable.

RULE 3 — UNCERTAINTY QUANTIFICATION IS MANDATORY
Every reported quantity must carry a confidence interval. Choose resampling to match dependence:
  - i.i.d. → standard bootstrap, B ≥ 2000 (≥ 10 000 for confirmatory).
  - Temporal → block bootstrap with adaptive block length (Politis–Romano optimal).
  - Clustered → cluster bootstrap preserving group membership.
  - Small n (<50) → BCa bootstrap, never percentile.
Implement bootstrap as a dedicated step that states block structure, CI method, and includes a stratification check to ensure both classes appear in each resample when the outcome is rare.

RULE 4 — EFFECT SIZE OVER P-VALUES
Report domain-appropriate effect sizes (Cohen’s d, risk ratios, MCC, etc.) with their own CIs. P-values are secondary. Multiple comparisons require explicit correction (Benjamini-Hochberg for discovery, Holm-Bonferroni for confirmatory).

RULE 5 — THRESHOLD JUSTIFICATION
Every numerical threshold must have a derivation:
- Youden’s J from ROC curve on this dataset,
- Physical / biological first principles with citation,
- Prior literature with explicit domain justification.
“Standard threshold” or “commonly used” are unacceptable.

RULE 6 — FALSIFIABILITY
The `falsification_plan` must state: “The hypothesis is falsified if [metric] [comparison] [value] based on [test], which would indicate [interpretation].” Vague criteria (“if results are not significant”) are rejected.

RULE 7 — MATHEMATICAL PARITY
Every equation in `mathematical_formalism` must appear exactly in the step that implements it. Variable names must match columns in [PHYSICAL GROUNDING].

RULE 8 — STEP COMPLETENESS
Every step must contain a concrete, executable action (no “analyze the data”), the specific function call or computation, a validation check that catches the most likely failure mode, and the expected output with numeric ranges where computable. No placeholders.

RULE 9 — SENSITIVITY ANALYSIS IS PART OF THE PROTOCOL
The protocol must include at least one step (or a dedicated sensitivity block) that:
- Perturbs key thresholds and assesses result stability,
- Tests alternative model specifications,
- Evaluates unmeasured confounding bounds (E-value if causal).
This step ensures that the conclusions are not brittle.

RULE 10 — NO CARGO-CULT FORCED STEPS
Do not force a specific number of steps, state transitions, or the word “Bootstrap” as a ritual. Steps arise naturally from the analysis plan. Bootstrap is used only when the DGP demands it, and its implementation details are described within the step where it is applied.

RULE 11 — SAMPLE SIZE & POWER REPORTING
- Distinguish between a planned experiment (power analysis for design) and a fixed observational dataset.
- For fixed datasets: do NOT report post-hoc power. Instead, report the observed precision of the primary effect size (half-width of the 95% CI). State whether the sample size is adequate for the planned analysis (e.g., EPV ≥ 10 for logistic regression). If underpowered, describe the corrections applied (Firth, bootstrap, Bayesian priors) and the resulting limitations.
- For planned experiments: provide a traditional power analysis with required N, effect size, alpha, and power.

RULE 12 — BIOPHYSICAL AND 3D STRUCTURAL RIGOR (MANDATORY WHEN PDB PRESENT)
When the experiment is in biophysics or contains a macromolecular structure (DATA_PDB / STRUCTURE_PRIMARY):
- Zero trivial spreadsheet filtering: Do not simply sort an existing CSV by binding affinity or p-value and label it a discovery.
- Mandatory 3D coordinate modeling: The protocol MUST include steps that parse 3D coordinates using Bio.PDB, calculate atomic Euclidean distances (d < 4.5 Å for heavy atoms across interacting interface chains), compute residue-level buried solvent accessible surface area (Delta_SASA via Bio.PDB.ShrakeRupley), or calculate Coulombic electrostatic energy.
- Predictive physical modeling: When testing mutations, the protocol must compute physical structural metrics (e.g. steric volume displacement, charge swap, atomic clash scores) and test whether 3D spatial properties correlate with or explain experimental mutational phenotypes.

══ OUTPUT JSON SCHEMA (MUST BE STRICTLY FOLLOWED) ══

{
  "name": "...",
  "description": "...",
  "objective": "...",
  "mathematical_formalism": "LaTeX equation",
  "falsification_plan": "...",
  "dgp_assumptions": {
    "independence_structure": "i.i.d. | temporal | clustered | hierarchical",
    "outcome_support": "Binary [0,1] | Continuous unbounded | ...",
    "known_confounders": ["..."],
    "testable_assumption_checks": ["Durbin-Watson", "Levene", "..."]
  },
  "steps": [
    {
      "step_number": 1,
      "title": "...",
      "description": "...",
      "action": "concrete function call or pseudocode",
      "expected_duration_minutes": ...,
      "requires_steps": [],
      "expected_output": "...",
      "validation_check": "...",
      "library_imports": ["module"]
    }
  ],
  "variables": {
    "var_name": {
      "name": "var_name",
      "type": "independent|dependent|control|confounding",
      "description": "...",
      "hypothesis_role": "...",
      "unit": "...",
      "values": "range or levels"
    }
  },
  "control_groups": [
    {
      "name": "...",
      "description": "...",
      "variables": {"col": "value"},
      "rationale": "...",
      "sample_size": 0
    }
  ],
  "statistical_tests": [
    {
      "test_type": "name",
      "dgp_justification": "why this test matches the DGP",
      "null_hypothesis": "H0: ...",
      "alternative": "one-sided-greater|less|two-sided",
      "alpha": 0.05,
      "alpha_correction": "None|Bonferroni|BH – state if FWER or FDR control",
      "primary_metric": "...",
      "effect_size_metric": "...",
      "variables": ["..."],
      "required_power": 0.80,
      "expected_effect_size": "..."
    }
  ],
  "sample_size": 0,
  "sample_size_rationale": "1. Fixed or expandable? 2. For logistic regression: EPV. 3. If fixed, report CI half-width for effect, not post-hoc power. 4. Corrections if underpowered.",
  "power_analysis_performed": true,
  "resource_estimates": {
    "compute_hours": 0.0,
    "memory_gb": 0,
    "gpu_required": false,
    "estimated_cost_usd": 0.0,
    "estimated_duration_days": 0.0,
    "required_libraries": ["pkg>=version"],
    "python_version": "3.10+",
    "can_parallelize": true,
    "parallelization_strategy": "..."
  },
  "random_seed": 42,
  "reproducibility_notes": "seed strategy, version pinning, data hashing, intermediate artifact naming.",
  "known_limitations": ["..."]
}

Ensure every field from the schema above is populated with concrete, executable values matching the target scientific domain.



══ SELF-AUDIT BEFORE EMITTING JSON ══

Before finalizing, verify:

[ ] Primary estimand clearly stated and identifiable.
[ ] Falsification conditions explicitly defined in the plan.
[ ] Estimator matches DGP and supports documented.
[ ] Bootstrap (if used) adapts to dependence structure; CI method stated.
[ ] All thresholds justified with a derivation method.
[ ] mathematical_formalism appears in the corresponding step.
[ ] No step uses vague verbs; every action is concrete.
[ ] EPV computed for logistic regressions; if EPV < 10, correction described.
[ ] Multiple testing correction applied when k>1 hypotheses.
[ ] Sensitivity analysis step present and addresses alternative specifications.
[ ] known_limitations describes what this design cannot conclude.
[ ] No forced boilerplate (state transitions, fixed bootstrap step number) – protocol evolved naturally from DGP.

If any condition fails, revise the JSON.

Output ONLY the JSON object. No prose before or after.

"""

    TEMPLATE = """Research Question: {research_id}
Hypothesis Statement: {statement}
Hypothesis Rationale: {rationale}
Domain: {domain}

[PHYSICAL GROUNDING - AVAILABLE DATA]
{data_context}

Task:
Design a detailed experimental protocol to test this hypothesis. Follow the system prompt's rules exactly.
The protocol must be structured as a JSON object with all required fields.

Requirements:
- The experiment name must be clear and descriptive.
- Description must state the system, intervention, statistical approach, and primary metric.
- Objective must specify what causal or associative claim can and cannot be established.
- Steps must be concrete, executable, and scientifically justified by the DGP. The number of steps is determined by the analysis, not a template.
- All variables must be defined from [PHYSICAL GROUNDING] only. Derived variables must be created in a step with their derivation formula.
- Control groups must be included with explicit rationales for what alternative explanations they rule out.
- Statistical tests must be matched to the DGP; provide null hypotheses, correction methods, and effect sizes.
- Sample size justification must distinguish fixed vs. expandable and report precision or power appropriately.
- All thresholds must be derived using one of the allowed methods (Youden, physical law, literature); none left unjustified.
- Sensitivity analysis must be included as a step.
- Reproducibility: specify random seed strategy, library versions, data hashing.
- Output formats: Protocol steps must instruct the code-generating LLM to: (1) Output GROUNDING_DATA:<json_metrics> in its final stdout. (2) Declare FALSIFICATION_BOUNDS = {{...}} as a dict variable in the generated Python script containing parameter boundaries. (3) Wrap dataset logs or evaluation results with CSV_DATA_START and CSV_DATA_END tags in stdout.
- No placeholders, no forced rituals like a fixed "Step 6 bootstrap" unless the DGP demands it. Bootstrap is a tool, not a mandatory step number.

Output ONLY the JSON object. No prose before or after.
"""

    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager

    async def design_protocol(self, hypothesis: Hypothesis, data_context: str, domain: str = "general", experiment_type: str = "computational") -> Dict[str, Any]:
        """
        [PHASE 1] Architect a high-fidelity Discovery Artifact (JSON).
        """
        logger.info(f" [DESIGNER] Architecting Supreme Artifact for: {hypothesis.id}")

        user_prompt = self.TEMPLATE.format(
            research_id=getattr(hypothesis, 'id', 'sci_id_unknown'),
            statement=hypothesis.statement,
            rationale=getattr(hypothesis, 'rationale', 'Discovery'),
            domain=domain,
            data_context=data_context
        )

        # Combine system + user prompt (LLMManager doesn't accept system param)
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{user_prompt}"

        # [GODZILLA V68.30] Agentic Skill Selection
        # Force the Designer to choose its own tools from the 122+ skills
        try:
            from backend.core.skill_injector import get_expert_system
            expert = get_expert_system()
            full_prompt = await expert.agentic_inject(
                base_prompt=full_prompt,
                query=hypothesis.statement, # USE THE REAL STATEMENT
                llm_manager=self.llm_manager,
                max_skills=3,
                domain=domain
            )
        except Exception as e:
            import traceback
            logger.error(f" [DESIGNER] Sovereign Skill Injection failed: {e}\n{traceback.format_exc()}")

        response = await self.llm_manager.run_async(
            full_prompt,
            temperature=0.2, # [ULTRON_CORE] Deterministic Ph.D. rigor
            model=CODE_GENERATION_MODEL
        )
        
        raw_text = response if isinstance(response, str) else response.get("text", "")
        artifact_json = self._extract_json(raw_text, hypothesis_id=hypothesis.id)
        
        if not artifact_json:
            logger.error(" [DESIGNER] Artifact architecture failed: Null response.")
            raise ValueError("LLM failed to return a valid Discovery Artifact JSON.")

        # Validation against Pydantic model
        try:
            from backend.core.models.scientific_protocol import DiscoveryArtifact
            artifact = DiscoveryArtifact(**artifact_json)
            
            # [GODZILLA RIGOR] Native Mathematical Power Analysis
            try:
                from backend.core.validation.power_analyzer import PowerAnalyzer
                power_analyzer = PowerAnalyzer()
                if "statistical_tests" in artifact_json and isinstance(artifact_json["statistical_tests"], list):
                    for test in artifact_json["statistical_tests"]:
                        if "test_type" in test and "expected_effect_size" in test:
                            import re
                            raw_effect = str(test.get("expected_effect_size", "0.5"))
                            eff_match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw_effect)
                            effect_size = max(0.05, abs(float(eff_match.group(0)))) if eff_match else 0.5
                            
                            raw_power = str(test.get("required_power", "0.8"))
                            pow_match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw_power)
                            power = float(pow_match.group(0)) if pow_match else 0.8
                            if power > 1.0 and power <= 100.0:
                                power /= 100.0
                            power = min(0.999, max(0.50, power))

                            raw_alpha = str(test.get("alpha", "0.05"))
                            alpha_match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw_alpha)
                            alpha = float(alpha_match.group(0)) if alpha_match else 0.05
                            if alpha > 1.0 and alpha <= 100.0:
                                alpha /= 100.0
                            alpha = min(0.20, max(0.0001, alpha))
                            
                            ttest_fn = getattr(power_analyzer, "ttest_sample_size", None) or getattr(power_analyzer, "t_test_sample_size", None)
                            if test.get("test_type") in ("t_test", "t-test", "ttest"):
                                n_req = ttest_fn(effect_size=effect_size, alpha=alpha, power=power) if ttest_fn else 30
                            elif test.get("test_type") == "anova":
                                raw_groups = test.get("groups", [1, 2])
                                groups = max(2, len(raw_groups) if isinstance(raw_groups, list) else int(raw_groups or 2))
                                n_req = power_analyzer.anova_sample_size(effect_size=effect_size, num_groups=groups, alpha=alpha, power=power)
                            elif test.get("test_type") in ("correlation", "pearson", "spearman", "regression", "linear_regression"):
                                corr_eff = min(0.99, max(0.01, effect_size))
                                n_req = power_analyzer.correlation_sample_size(effect_size=corr_eff, alpha=alpha, power=power)
                            else:
                                n_req = ttest_fn(effect_size=effect_size, alpha=alpha, power=power) if ttest_fn else 30

                            # Preserve larger fixed observational dataset sizes; only raise sample_size floor when unspecified or underpowered
                            existing_n = int(artifact_json.get("sample_size") or 0)
                            artifact_json["minimum_required_sample_size"] = n_req
                            if existing_n < n_req:
                                artifact_json["sample_size"] = n_req
                            artifact_json["sample_size_rationale"] = (
                                f"Ph.D. Power Analysis Floor: Minimum N={n_req} required for {round(power*100, 1)}% power "
                                f"to detect effect size {round(effect_size, 3)} at alpha={round(alpha, 4)} "
                                f"(Full available empirical dataset N={max(existing_n, n_req)} must be used without downsampling)."
                            )
                            break # Just use the first test for overall N
            except Exception as e:
                logger.warning(f" [DESIGNER] Power Analysis Override bypassed: {e}")

            logger.info(f" [DESIGNER] Artifact '{artifact.title}' successfully synthesized (Rigor: {artifact.calculate_rigor_score()}).")
            return artifact_json
        except Exception as e:
            logger.error(f" [DESIGNER] Artifact failed Pydantic validation: {e}")
            return artifact_json

    def _extract_json(self, text: str, hypothesis_id: str = "sci_unknown") -> Dict[str, Any]:
        """Robustly extract and HEAL the most significant JSON object from a string."""
        import json
        import re
        text = text.replace("```json", "").replace("```", "").strip()
        candidates = []
        start_indices = [m.start() for m in re.finditer('{', text)]
        for start in start_indices:
            count = 0
            for i in range(start, len(text)):
                if text[i] == '{': count += 1
                elif text[i] == '}': count -= 1
                if count == 0:
                    cand = text[start:i+1]
                    try:
                        data = json.loads(cand)
                        if isinstance(data, dict):
                            candidates.append((data, len(data.keys())))
                    except Exception as e:
                        try:
                            import ast
                            data = ast.literal_eval(cand)
                            if isinstance(data, dict):
                                candidates.append((data, len(data.keys())))
                        except Exception as e2:
                            import logging
                            logging.getLogger(__name__).warning(f" [DESIGNER] JSON extraction failed on candidate: {e2}")
                    break
        if not candidates: return {}
        
        # Pick the most complex object
        candidates.sort(key=lambda x: x[1], reverse=True)
        artifact_json = candidates[0][0]

        # [HEURISTIC HEALER V3] Recursive Deep-Search for Artifact Keys
        # Handle cases where the artifact is nested inside a 'discovery_artifact' or similar key
        for key in ["discovery_artifact", "artifact", "protocol", "experiment"]:
            if key in artifact_json and isinstance(artifact_json[key], dict):
                logger.info(f" [HEALER] Unpacking nested artifact from key: {key}")
                nested = artifact_json[key]
                # Merge top-level metadata if missing in nested
                for meta_key in ["title", "hypothesis", "abstract", "domain", "state_graph", "steps", "falsification_plan"]:
                    if meta_key not in nested and meta_key in artifact_json:
                        nested[meta_key] = artifact_json[meta_key]
                artifact_json = nested
                break

        # Map common LLM naming discrepancies
        if "hypothesis" not in artifact_json:
            artifact_json["hypothesis"] = artifact_json.get("hypothesis_statement", artifact_json.get("objective", hypothesis_id))
        
        # [GODZILLA HEALER] If hypothesis is still too short or missing, force the original
        if len(str(artifact_json.get("hypothesis", ""))) < 10:
             artifact_json["hypothesis"] = "Original Hypothesis: " + str(hypothesis_id)

        if "artifact_id" not in artifact_json:
            artifact_json["artifact_id"] = hypothesis_id
            
        # Unified mapping for bilingual support
        if "name" in artifact_json and "title" not in artifact_json:
            artifact_json["title"] = artifact_json["name"]
        if "description" in artifact_json and "abstract" not in artifact_json:
            artifact_json["abstract"] = artifact_json["description"]
            
        # Ensure 'mathematical_formalism' exists
        if "mathematical_hypothesis" in artifact_json and "mathematical_formalism" not in artifact_json:
            artifact_json["mathematical_formalism"] = artifact_json["mathematical_hypothesis"]
        if "mathematical_formalism" not in artifact_json:
            artifact_json["mathematical_formalism"] = "N/A"

        # Ensure list fields in DiscoveryArtifact are lists (Pydantic Auto-Healing)
        if "statistical_tests" in artifact_json:
            if isinstance(artifact_json["statistical_tests"], dict):
                artifact_json["statistical_tests"] = [artifact_json["statistical_tests"]]
            elif not isinstance(artifact_json["statistical_tests"], list):
                artifact_json["statistical_tests"] = []

        if "steps" in artifact_json:
            if isinstance(artifact_json["steps"], dict):
                artifact_json["steps"] = [artifact_json["steps"]]

        if "controls" in artifact_json:
            if isinstance(artifact_json["controls"], dict):
                artifact_json["controls"] = [artifact_json["controls"]]

        if "experimental_design" in artifact_json and isinstance(artifact_json["experimental_design"], dict):
            design = artifact_json["experimental_design"]
            if "steps" in design:
                if isinstance(design["steps"], dict):
                    design["steps"] = [design["steps"]]
                elif isinstance(design["steps"], str):
                    design["steps"] = [design["steps"]]
            if "controls" in design:
                if isinstance(design["controls"], dict):
                    design["controls"] = [design["controls"]]
                elif isinstance(design["controls"], str):
                    design["controls"] = [design["controls"]]
            if "datasets" in design:
                if isinstance(design["datasets"], dict):
                    design["datasets"] = [design["datasets"]]
                elif isinstance(design["datasets"], str):
                    design["datasets"] = [design["datasets"]]

        if "required_libraries" in artifact_json:
            if isinstance(artifact_json["required_libraries"], str):
                artifact_json["required_libraries"] = [artifact_json["required_libraries"]]
            elif isinstance(artifact_json["required_libraries"], dict):
                artifact_json["required_libraries"] = list(artifact_json["required_libraries"].keys())

        if "tags" in artifact_json:
            if isinstance(artifact_json["tags"], str):
                artifact_json["tags"] = [artifact_json["tags"]]

        # [GODZILLA V68.34] Autonomous Protocol Verification + AUTO-HEAL
        # Only auto-inject if no resampling or uncertainty quantification method is present
        protocol_str = json.dumps(artifact_json).lower()
        uq_terms = ("bootstrap", "permutation", "bca", "conformal", "credible_interval", "confidence_interval", "jackknife")
        missing_rigor = []
        if not any(t in protocol_str for t in uq_terms):
            missing_rigor.append("Bootstrap Resampling")
        
        if missing_rigor:
            logger.warning(f" [RIGOR FAIL] Protocol missing critical methods: {missing_rigor}. Auto-injecting...")
            existing_steps = artifact_json.get("steps") if isinstance(artifact_json.get("steps"), list) else []
            next_step_num = len(existing_steps) + 1
            bootstrap_step = {
                "step_number": next_step_num,
                "title": "Bootstrap Resampling Validation",
                "step": "Bootstrap Resampling Validation",
                "description": "Apply bootstrap resampling (n=1000 iterations) to compute 95% confidence intervals for all primary metrics. Use scipy.stats.bootstrap or manual numpy resampling. Report CI bounds alongside point estimates.",
                "action": "scipy.stats.bootstrap((data,), np.mean, n_resamples=1000, confidence_level=0.95)",
                "expected_output": "95% confidence interval [ci_low, ci_high] excluding null under H1",
                "validation_check": "Verify ci_low <= point_estimate <= ci_high and no NaN resamples",
                "type": "statistical_validation"
            }
            # Inject into the steps list if it exists
            if "steps" in artifact_json and isinstance(artifact_json["steps"], list):
                artifact_json["steps"].append(bootstrap_step)
            elif "methodology" in artifact_json and isinstance(artifact_json["methodology"], list):
                artifact_json["methodology"].append(bootstrap_step)
            elif "experimental_design" in artifact_json and isinstance(artifact_json["experimental_design"], dict):
                existing = artifact_json["experimental_design"].get("steps", [])
                if isinstance(existing, list):
                    existing.append(bootstrap_step)
                    artifact_json["experimental_design"]["steps"] = existing
            else:
                # Fallback: add a top-level bootstrap_validation key
                artifact_json["bootstrap_validation"] = bootstrap_step
            logger.info(f" [RIGOR HEAL] Bootstrap Resampling auto-injected into protocol.")

        return artifact_json


    async def refine_protocol(self, hypothesis: Hypothesis, code: str, error: str) -> Dict[str, Any]:
        """
        [STEP 1 - REFINEMENT] Analyze failure and refine the structured artifact.
        """
        logger.info(f" [DESIGNER] Refining Supreme Artifact for: {hypothesis.id}")

        prompt = f"""You are a Sovereign Lead Research Scientist.
A scientific discovery mission has FAILED. You must refine the artifact to fix the technical failure.

HYPOTHESIS: "{hypothesis.statement}"
ERROR MESSAGE: {error}

BROKEN CODE:
```python
{code}
```

[PH.D. DEBUGGING MANDATE]
Analyze the code for "Physics vs Logic" errors.
- Global variables like `DATA_PATH`, `DATA_PRIMARY`, and `DATA_PDB_6M0J` must NOT be wrapped in quotes.
- Ensure unit consistency (Dimensional Analysis).
- Verify mathematical logic.

Task:
Refine the Discovery Artifact. Identify if the failure was in Data Grounding, Physical Computation, or Falsification Logic.

Output ONLY the updated JSON object conforming to the DiscoveryArtifact schema.
"""
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
        response = await self.llm_manager.run_async(
            full_prompt, 
            temperature=0.5, 
            model=CODE_GENERATION_MODEL
        )
        return self._extract_json(response if isinstance(response, str) else response.get("text", ""))


