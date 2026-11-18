"""
ULTRON Ph.D. EXPERIMENT IMPLEMENTER (TITAN V71.0)
=================================================
The "Computational Scientist" of the discovery pipeline.
Translates structured JSON protocols into high-fidelity Python code.
"""

import logging
import re
import json
import inspect
from typing import Dict, Any, Optional

from backend.llm_manager import LLMManager, CODE_GENERATION_MODEL

logger = logging.getLogger("agents.experiment_implementer")

class ExperimentImplementer:
    """Translates a JSON scientific protocol into high-performance Python code."""
    
    SYSTEM_PROMPT = """
You are a senior PHD LEAD scientist, methodologist, and code architect with zero tolerance
for pseudo-science, statistical theatre, or reproducibility theatre.

Your task: produce a falsifiable, identifiable, numerically stable, and
mechanistically grounded Python implementation of the supplied experimental
protocol. If the protocol, hypothesis, or estimand is scientifically invalid,
you will refuse with a precise, structured explanation—no code, no apologies.

All output must survive adversarial peer review at a top-tier journal.
No placeholder logic. No decorative mathematics. No hidden assumptions.

══════════════════════════════════════════════════════════════════════════
PHASE 0 — GATEKEEPER: FALSIFIABILITY & IDENTIFIABILITY
══════════════════════════════════════════════════════════════════════════

Before any code, determine:

1. What is the exact scientific question? State it in one operational sentence.
2. What is the primary estimand? Define it mathematically.
3. Is the estimand identifiable from the data that can realistically be collected?
   – If no: refuse implementation. Explain why, state what additional
     assumptions or data would be necessary, and stop.
4. What observations would falsify the primary claim?
   – If none, the hypothesis is unscientific; refuse and stop.
5. What are the untestable assumptions? List them. If they are implausible given
   domain knowledge, refuse and explain.

Pass this gate before writing a single line of code.

══════════════════════════════════════════════════════════════════════════
PHASE 1 — COMPREHENSIVE DGP AUDIT
══════════════════════════════════════════════════════════════════════════

Characterize the data-generating process exhaustively:

| Question                                      | Must Answer? |
|-----------------------------------------------|--------------|
| What produces the observations?               | Yes          |
| Dependence structure (i.i.d., temporal, …)    | Yes          |
| Latent variables and their plausible impact   | Yes          |
| Support of every observable variable          | Yes          |
| Missingness mechanism (MCAR, MAR, MNAR)       | Yes          |
| Selection bias sources                        | Yes          |
| Confounding structure (draw a DAG mentally)   | Yes          |
| Instrument / sensor noise model               | Yes          |
| Known physical/biological constraints         | Yes          |
| Which assumptions are testable?               | Yes          |
| Which are fundamentally untestable?           | Yes          |

This audit determines all downstream choices. Copy-pasting a t-test is fraud
until this audit is complete.

══════════════════════════════════════════════════════════════════════════
PHASE 2 — ESTIMATOR AND INFERENCE PROTOCOL
══════════════════════════════════════════════════════════════════════════

The estimator must align with the DGP, not with convenience.

Binary / categorical outcomes:
  – Rare events or separation → Firth logistic regression (statsmodels or
    PyMC), or Bayesian with weakly-informative priors.
  – Imbalanced classes → Matthews Correlation Coefficient (MCC) primary,
    PR-AUC secondary. Never report ROC-AUC alone.
  – No SMOTE before train/test splitting. Data leakage invalidates everything.

Count data:
  – Test overdispersion (AER::dispersiontest equivalent).
  – If Var ≈ Mean → Poisson acceptable.
  – Otherwise → Negative Binomial or Conway-Maxwell-Poisson.

Temporal data:
  – No random shuffling. Use block bootstrap, HAC covariance, GEE, or
    state-space models. Block length chosen adaptively (Politis–Romano
    algorithm or similar).

Hierarchical/clustered data:
  – Mixed-effects models (statsmodels MixedLM or lme4-like via rpy2),
    cluster bootstrap, or robust clustered covariance. Pseudoreplication
    is a fatal error.

Heavy-tailed / bounded support:
  – M-estimators (scipy.optimize or statsmodels RLM), quantile regression,
    Beta regression for proportions, log-skew-normal for positive continuous.

Causal estimands:
  – Use backdoor criterion, do-calculus, or instrumental variables.
  – Doubly-robust estimators, g-computation, or targeted maximum likelihood.
  – Explicitly state untestable assumptions (no unmeasured confounders, etc.).
  – Sensitivity analysis for unmeasured confounding is mandatory.

All estimators must:
  – Be fully implemented (no black-box calls to packages without exposing
    the likelihood or loss function in readable code).
  – Provide effect sizes with confidence intervals, not just p-values.
  – Use a resampling scheme strictly matched to the dependence structure:
    • i.i.d. → BCa bootstrap (B ≥ 10 000 for confirmatory)
    • Temporal → stationary/circular block bootstrap, block length adaptive
    • Clustered → cluster bootstrap preserving group membership
    • Small n → BCa, never percentile
  – Optionally, profile likelihood CIs or conformal prediction when appropriate.

Multiple comparisons:
  – >1 hypothesis → Benjamini-Hochberg (exploratory) or Holm-Bonferroni
    (confirmatory). Distinguish the two. Never present uncorrected p-values
    as confirmatory.

══════════════════════════════════════════════════════════════════════════
PHASE 2.5 — BIOPHYSICAL AND STRUCTURAL MODELING MANDATE (CRITICAL)
══════════════════════════════════════════════════════════════════════════

When the environment contains a macromolecular 3D structure (DATA_PDB / STRUCTURE_PRIMARY):
1. ZERO SPREADSHEET FILTERING AS "DISCOVERY":
   Merely filtering an existing CSV (e.g. `df[df['bind_avg'] > 0.1]`) and labeling the top row an "autonomous discovery" is FRAUD. 
   A computational structural biologist models the physical 3D structure.

2. 3D ATOMIC INTERFACE COMPUTATION:
   You MUST parse 3D coordinates using `Bio.PDB` (`PDBParser`) and execute actual physical modeling:
   - Compute pairwise atomic Euclidean distances across the complex interface (across distinct interacting chains) with contact cutoff d < 4.5 Å for heavy atoms.
   - Compute residue-level solvent-accessible surface area (SASA) burial:
     Delta_SASA = SASA_unbound - SASA_bound (via Bio.PDB.ShrakeRupley or pre-injected `calculate_buried_sasa`).
   - Compute electrostatic interface potential and salt bridges (Coulomb energy with distance-dependent dielectric eps(r) = 4r via `calculate_coulomb_energies`).

3. PHYSICAL PREDICTION OF UNMEASURED PHENOTYPES:
   For mutational or epistatic hypotheses:
   - Calculate the 3D atomic displacement, steric volume delta (Delta_V in A^3), and charge delta (Delta_q) between wildtype and mutant side-chains.
   - For double mutants or candidate design, calculate whether physical steric clash score (sum of overlap distances < 2.0 A) or electrostatic repulsion explains non-linear binding affinity.
   - Connect the computed 3D physical property (buried SASA, Coulomb energy, contact count) to experimental phenotypes via inferential regression or non-parametric correlation (Spearman rho, p < 0.01).

4. GROUNDED CANDIDATE DISCOVERY FORMAT:
   If a novel candidate is identified, print:
   CANDIDATE_DISCOVERY: {"candidate_id": "CAND-<MUTATION>", "target": "<PROTEIN_LOCUS>", "mutation": "<SUBSTITUTION>", "predicted_affinity_effect": "<VALUE>", "mechanism": "<PHYSICAL_3D_MECHANISM>", "validation_evidence": "<STATISTICAL_TEST_RESULT>"}
   NEVER output generic synthetic candidate IDs (e.g. "var_0022" or "sim_01"). All candidate IDs must be physically or biochemically grounded (e.g. "CAND-<VARIANT_NAME>").

══════════════════════════════════════════════════════════════════════════
PHASE 3 — MECHANISTIC AND NUMERICAL HARDENING
══════════════════════════════════════════════════════════════════════════

Mechanistic validation:
  – Enforce all physical/biological constraints: probabilities in [0,1],
    concentrations non-negative, conservation laws, dimensional consistency.
  – Detect impossible states (e.g., negative distances, energy creation)
    and reject or flag them.
  – A model with perfect metrics that violates physics is WRONG and must
    be reported as invalid.

Numerical stability:
  – Probabilities in log-space, exponentiate only for final output.
  – Kahan summation for long accumulations.
  – Check matrix condition numbers before inversion; use pseudoinverse
    (np.linalg.lstsq) if κ > 1e10.
  – Epsilon guards on all division operators.
  – Stable softmax / log-sum-exp everywhere.

Reproducibility infrastructure:
  – Seed all PRNGs (numpy, torch, etc.) and log the seed state before any
    stochastic operation.
  – At runtime, emit a JSON artifact containing:
    • Exact package versions (pip freeze relevant subset)
    • Hardware fingerprint (CPU, RAM, GPU if used)
    • Input data SHA-256 hash (to detect silent corruption)
    • Wall-clock timestamps and elapsed time per phase
    • Full configuration snapshot (all hyperparameters, thresholds, random seeds)
  – No proprietary/opaque telemetry hooks.

══════════════════════════════════════════════════════════════════════════
PHASE 4 — IMPLEMENTATION STRUCTURE
══════════════════════════════════════════════════════════════════════════

Every implementation must produce a single, self-contained Python script
with the following internal sections, in order:

1. MODULE DOCSTRING
   – Scientific objective, DGP summary, estimand definition, untestable
     assumptions, falsification criteria, expected output.

2. CONFIGURATION
   – A frozen dataclass or dictionary that holds every tunable parameter,
     threshold, and seed. Comment each with its justification and units.
     No magic numbers in function bodies.

3. DATA VALIDATION & PREPROCESSING
   – Schema and range checks, missingness audit, impossible-state detection.
   – Preprocessing choices justified by DGP: log-transform only if lognormal
     DGP assumed; z-score only if Gaussian reasonably justified; min-max
     only if bounded support is authentic.

4. PRIMARY ANALYSIS
   – Explicit estimator class/function, loss/likelihood fully written.
   – Dependence-appropriate bootstrap or CI construction.
   – Diagnostics: residuals (deviance, Pearson), influence measures,
     VIF for collinearity, calibration plots, etc.

5. ASSUMPTION & SENSITIVITY ANALYSES
   – Test the testable assumptions: homoskedasticity (Breusch-Pagan),
     autocorrelation (Durbin-Watson), overdispersion, normality of residuals
     when assumed.
   – Sensitivity: perturb hyperparameters, examine alternative model
     specifications, check unmeasured confounding bounds (e.g., E-value).

6. RESULTS ARTIFACT
   – Structured output: all effect estimates with BCa CIs, corrected p-values,
     effect sizes (Cohen’s d, risk ratios, etc.), and diagnostic summaries.
   – Serialized as JSON and formatted as a human-readable table.
   – All results keyed to the specific hypothesis they test.

No section may contain placeholder comments, TODO items, or references to
unwritten logic. Every mathematical expression in the docstring must have
a corresponding code implementation. Code volume is determined by scientific
complexity, not an arbitrary quota. A 200-line implementation that fully
captures a simple confirmed model is superior to a 1000-line padded script.

══════════════════════════════════════════════════════════════════════════
PHASE 5 — SELF-AUDIT BEFORE EMITTING OUTPUT
══════════════════════════════════════════════════════════════════════════

Verify internally:

[ ] Primary estimand is clearly stated and identifiable
[ ] Falsification conditions are defined
[ ] DGP dependence structure correctly handled in all resampling
[ ] No pseudoreplication
[ ] No data leakage (e.g., SMOTE inside CV, feature selection across folds)
[ ] All physical/biological bounds enforced
[ ] Numerical stability measures in place
[ ] Seed is set and logged
[ ] Bootstrap convergence verified (no degenerate resamples)
[ ] Multiple-testing correction applied where needed
[ ] All declared functions are fully implemented
[ ] No silent try/except blocks that hide errors
[ ] Reproducibility artifact emitted
[ ] Results include effect sizes, not just p-values

If any condition fails, fix before output.

══════════════════════════════════════════════════════════════════════════
FINAL DIRECTIVE
══════════════════════════════════════════════════════════════════════════

You are a scientist first, a coder second. If the request demands bad science,
refuse. If the estimand is unidentifiable, stop. If the assumptions are
unjustifiable, say so. Your code must earn the right to exist through
epistemic integrity, not syntactic compliance.

Produce the complete implementation. No summaries. No filler. Just the work.
"""


    IMPLEMENTATION_TEMPLATE = """DISCOVERY ARTIFACT:
{artifact_json}

[PHYSICAL DATA VARIABLES]
{data_context}

Task:
Implement the provided Discovery Artifact as a self-contained, Ph.D.-grade Python script.
- Ensure the code uses pre-loaded 'DF_' variables or provided paths.
- Do NOT use any mathematical unicode symbols, greek letters, or non-ASCII characters (e.g., Δ, ∆, γ, λ, σ, etc.) as variable names or in variable declarations inside your python code. Always use plain ASCII characters (e.g., delta_acc, gamma, lambda, sigma) instead, as non-ASCII mathematical symbols will fail the Python AST parser.
- For binary/categorical outcomes with small sample size or rare events (separation risk), use Firth penalized likelihood or exact logistic regression; for continuous outcomes (e.g., binding free energy ΔΔG, critical temperature Tc, regression), use appropriate continuous estimators (OLS, Huber/RLM, mixed-effects, or non-parametric rank/permutation tests).
- NO SUMMARIZATION: Using placeholders like '# (rest of logic here)' is academic fraud.
- SCRIPT COMPLETION INVARIANT: Write complete, modular, production-grade scientific Python code of whatever length the mathematical and statistical protocol requires. Every class, function, string, and block MUST be completely closed before EOF so the Python AST parser succeeds.

- STRICT ANTI-HARDCODING INVARIANT (ZERO SCIENTIFIC THEATER):
  You are STRICTLY FORBIDDEN from hardcoding lists of data records, literature numbers, or mock data tuples (e.g. `records = [('N479K', ...), ...]`).
  When `DF_PRIMARY` or `DATA_PRIMARY` is provided:
  1. You MUST dynamically load, inspect, filter, and extract your features from the real dataset (`DF_PRIMARY` or `pd.read_csv(DATA_PRIMARY)`).
  2. For biological mutation datasets like SKEMPI (`skempi_v2.csv`), filter the `#Pdb` or protein columns directly, extract `Affinity_mut_parsed` and `Affinity_wt_parsed`, and compute ΔΔG = RT * ln(Kd_mut / Kd_wt).
  3. If structural PDB files (`DATA_PDB` / `6lzg.pdb`) are present, parse the atomic coordinates or residue contacts dynamically.
  4. Hardcoding static literature numbers in arrays while ignoring the real dataset is classified as academic fraud and will be rejected by the AST Cleanroom.

- STRICT COLUMN SCHEMA GROUNDING (ZERO HALLUCINATED COLUMNS):
  Examine the exact columns listed in [PHYSICAL DATA VARIABLES] for your dataset.
  You MUST use ONLY the exact column names present in the dataset schema.
  NEVER invent, guess, or write assertions that assert non-existent column names exist (e.g. `assert col_nv and col_thd and col_sigm`).
  If a theoretical quantity (e.g. Debye temperature, electron density, variance, entropy) does not have a 1-to-1 matching column name in the dataset, map it to the closest physical proxy in the dataset (or use substring search on `df.columns` with a safe fallback). NEVER assert on a guessed column name!

- STRUCTURAL BIOPHYSICS & MOLECULAR CANDIDATE PROTOCOL:
  When testing macromolecular interfaces or mutational libraries (e.g., `STRUCTURE_PRIMARY` / `DATA_PDB` and `DF_PRIMARY`):
  1. Dynamically compute the physical atomic interface contacts across interacting chains using `calculate_atomic_contacts(STRUCTURE_PRIMARY, cutoff=5.0)` or Biopython NeighborSearch.
  2. Cross-reference the 3D contact residue positions with empirical mutational or functional screening data (`DF_PRIMARY`).
  3. Identify candidate mutations or functional residues based on measured experimental binding, expression, or activity at the structural interface.
  4. Perform a permutation test (2,000 resamples) comparing interface vs non-interface distributions to establish statistical significance.
  5. In stdout, emit the concrete candidate specification for downstream wet-lab validation:
     print("CANDIDATE_DISCOVERY:" + json.dumps({{"candidate_id": "...", "mutation": "...", "predicted_affinity_effect": float(...), "contact_residues": [...], "mechanism": "..."}}))

- The sandbox executes your code in an isolated environment and rigorously verifies empirical outcomes through:
  (1) Output telemetry: emit GROUNDING_DATA:<json_metrics> with valid numerical p-values, effect sizes, and confidence intervals.
  (2) Downstream 3-layer statistical grounding validation (1000-iteration permutation tests, BCa bootstrap resampling, subset stress).
  (3) 4-layer adversarial stress-testing (parameter noise injection, feature ablation, numerical stability checks).
- Use the most appropriate scientific library for your data structure: scipy.stats, statsmodels, sklearn, lifelines, PyMC, or PyTorch. Ensure all statistical models converge and all estimates have quantified uncertainty.
{data_instruction}
- SCRIPT OUTPUT REQUIREMENTS: The script you generate MUST:
  (1) Save summary results to `summary.csv` in the current directory (`pd.DataFrame([...]).to_csv("summary.csv", index=False)`).
  (2) Output `GROUNDING_DATA:<json_metrics>` on its own line in stdout containing at minimum: `{{"p_value": float(p_val), "effect_size": float(effect_size), "t_statistic": float(t_stat), "sample_size": int(n), "confidence_interval": [float(ci_lo), float(ci_hi)], "control_raw": list(control_arr[:2000]), "treatment_raw": list(treatment_arr[:2000])}}` AND print a final JSON summary line `print(json.dumps({{"supported": bool(is_supported), "confidence": float(conf), "report": {{"p_value": float(p_val), "effect_size": float(effect_size), "t_statistic": float(t_stat), "sample_size": int(n), "statistical_test": str(test_name), "confidence_interval": [float(ci_lo), float(ci_hi)]}}}}))`.
  (3) Declare `FALSIFICATION_BOUNDS = {{...}}` as a dict variable containing parameter boundaries.
  (4) Wrap dataset logs or evaluation results with `CSV_DATA_START` and `CSV_DATA_END` tags in stdout.

[STRUCTURAL ANCHOR]:
# CRITICAL: You MUST explicitly import ALL libraries and modules you use here (e.g. import pandas as pd, import numpy as np, import scipy, etc.)
# The sandbox environment will NOT auto-import them. If you fail to include the imports, your code will crash.
# ... (rest of Ph.D. logic)
"""

    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager

    def _get_integrity_shield(self) -> str:
        """Injects industrial-strength utility functions directly into the sandbox context."""
        return """
import pandas as pd
import numpy as np
import os
import json
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#  Physical Context Bonding
DATA_ARTIFACT_PATH = os.environ.get('DATA_ARTIFACT_PATH', 'results.csv')
IMAGE_ARTIFACT_PATH = os.environ.get('IMAGE_ARTIFACT_PATH', 'plot.png')
DATA_SEP = os.environ.get('DATA_SEP', ';')

#  Zero-Division & Robustness Guards
def safe_mean(arr): return np.mean(arr) if len(arr) > 0 else 0.0
def safe_std(arr): return np.std(arr) if len(arr) > 1 else 0.0

# Temporal Block Bootstrap
def block_bootstrap(df, block_size=5, n_iterations=10000):
    \"\"\"Preserves time-series correlation during resampling.\"\"\"
    n = len(df)
    if n == 0:
        return []
    indices = np.arange(n)
    eff_block = max(1, min(int(block_size), n))
    n_blocks = max(1, int(np.ceil(n / eff_block)))
    max_start = max(1, n - eff_block + 1)
    bootstrap_results = []
    for i in range(n_iterations):
        starts = np.random.randint(0, max_start, n_blocks)
        resampled_indices = np.concatenate([indices[s:s+eff_block] for s in starts])[:n]
        bootstrap_results.append(resampled_indices)
    return bootstrap_results
"""

    async def implement_protocol(self, artifact_json: Dict[str, Any], data_context: str, protocol_skeleton: str = "", domain: str = "general", has_bound_data: Optional[bool] = None) -> str:
        """
        [PHASE 2] Translate Artifact into high-fidelity Ph.D. Code.
        """
        logger.info(f" [IMPLEMENTER] Implementing Ph.D. Logic for: {artifact_json.get('title', 'Discovery Mission')}")
        
        hypothesis_stmt = (
            artifact_json.get("hypothesis") or 
            artifact_json.get("hypothesis_statement") or 
            artifact_json.get("statement") or 
            artifact_json.get("title") or 
            "UNDEFINED RESEARCH MISSION"
        )

        if has_bound_data is True:
            is_simulation = False
        elif has_bound_data is False:
            is_simulation = True
        else:
            is_simulation = "No relevant physical datasets found in vault" in data_context or not data_context.strip()
        if is_simulation:
            data_instruction = (
                "- NUMERICAL SIMULATION / THEORETICAL MODELING MODE: No physical tabular dataset is bound for this hypothesis.\n"
                "  You MUST implement a rigorous, deterministic numerical simulation or mathematical Data Generating Process (DGP) using numpy, scipy, statsmodels, or torch.\n"
                "  Do NOT require or check for DF_PRIMARY or DATA_PRIMARY. Do NOT exit with an error. Generate your control and treatment distributions programmatically via your DGP with realistic physical and statistical properties."
            )
        else:
            data_instruction = (
                "- THE DATA IS ALREADY LOADED: You MUST use the pre-injected global variables: `DATA_PRIMARY` (the absolute path string) and `DF_PRIMARY` (the pre-loaded Pandas DataFrame or resolved data object). Do NOT guess filenames, invent synthetic data, or access unlisted files. Use `DATA_PRIMARY` / `DF_PRIMARY` directly."
            )

        prompt = self.IMPLEMENTATION_TEMPLATE.format(
            artifact_json=json.dumps(artifact_json, indent=2),
            data_context=data_context,
            data_instruction=data_instruction
        )

        # [AGENTIC EXPLORATION] Sovereign Skill Injection
        try:
            from backend.core.skill_injector import get_expert_system
            expert = get_expert_system()
            prompt = await expert.agentic_inject(
                base_prompt=prompt, 
                query=hypothesis_stmt, 
                llm_manager=self.llm_manager,
                max_skills=3,
                domain=domain
            )
        except Exception as e:
            logger.error(f" [IMPLEMENTER] Skill injection failed: {e}")

        shield = self._get_integrity_shield()
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}\n\n[MANDATORY NUMERICAL SHIELD - USE THESE FUNCTIONS]:\n{shield}"
        
        response = await self.llm_manager.run_async(
            full_prompt,
            temperature=0.1, 
            source="implementer.py",
            task_hint="code_generation",
            is_json=False
        )

        raw_text = response if isinstance(response, str) else response.get("text", "")
        code = self._extract_code(raw_text)
        
        # [GODZILLA V68.34] Structural Integrity Gate
        if code.strip().startswith("{") and code.strip().endswith("}"):
            logger.error(" [IMPLEMENTER] CRITICAL: LLM returned JSON instead of Python code.")
            raise ValueError("Structural Failure: Model returned JSON protocol instead of Python implementation.")
        
        return shield + "\n\n" + code

    def _extract_code(self, text: str) -> str:
        """Surgically extract Python code from the response."""
        import textwrap
        import json
        code = ""
        
        # Priority 1: Markdown blocks
        match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
        if match: 
            code = match.group(1)
        else:
            match = re.search(r"```\n?(.*?)```", text, re.DOTALL)
            if match: 
                code = match.group(1)
            else:
                code = text
        
        code = textwrap.dedent(code).strip()
        
        # Priority 2: JSON-wrapped code handling (LLM failure mode)
        if code.startswith("{") and code.endswith("}"):
            try:
                # Try to parse it and look for code fields
                data = json.loads(code)
                for key in ["python_code", "implementation", "code", "script", "executable_code", "experiment_code", "source_code", "python", "run"]:
                    if key in data and isinstance(data[key], str) and len(data[key]) > 50:
                        logger.info(f" [IMPLEMENTER] Extracted Python code from JSON field: {key}")
                        return data[key].strip()
                
                # Recursive search for any string field containing Python code
                def find_code(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            res = find_code(v)
                            if res: return res
                    elif isinstance(obj, list):
                        for item in obj:
                            res = find_code(item)
                            if res: return res
                    elif isinstance(obj, str) and ("import " in obj or "def " in obj) and len(obj) > 50:
                        return obj.strip()
                    return None
                
                nested = find_code(data)
                if nested:
                    logger.info(" [IMPLEMENTER] Recursively extracted Python code from nested JSON")
                    return nested

                raise ValueError("LLM returned a JSON dictionary with no recognizable code fields.")
            except json.JSONDecodeError:
                pass # Not real JSON, just code starting/ending with braces (rare)

        return code
