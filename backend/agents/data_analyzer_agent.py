"""
Autonomous Data Auditor (V41.0)
==========================================================
Advanced autonomous scientific data analysis and interpretation module.
Integrates statistical validation with neural-symbolic reasoning.
"""

import os
import logging
import json
import numpy as np
import pandas as pd
import scipy.stats as stats
import math
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict

from backend.execution.sandbox import GodModeSandbox
from backend.core.skill_injector import get_expert_system
from backend.llm_manager import CODE_GENERATION_MODEL

logger = logging.getLogger("agents.data_analyzer")

# =============================================================================
# SCIENTIFIC MANDATE: THE ANALYTICAL CORE
# =============================================================================

_SCIENTIST_SYSTEM_PROMPT = """
ROLE: LEAD SCIENTIFIC AUDITOR & PRINCIPAL INVESTIGATOR (PhD, 30+ Years Exp.)
IDENTITY: You are a rigorous, evidence-based scientist. You have zero tolerance for shallow analysis.

CORE OPERATIONAL PROTOCOLS:
1. QUANTITATIVE DEPTH: Beyond basic EDA, you must look for structural signals in data distributions.
2. ADVANCED MODELING: Utilize Multivariate Regression, PCA, or non-parametric rank analysis where appropriate.
3. HYPOTHESIS FALSIFICATION: Actively seek data patterns that contradict the proposed hypothesis.
4. VISUALIZATION STANDARDS: Recommend dashboards that include residual analysis and confidence intervals.
5. DATA PROVENANCE: Strictly adhere to the physical data paths provided.

TASK:
Provide a rigorous scientific interpretation of the provided statistical results.
"""

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class StatisticalTestResult:
    """Represents a specific statistical outcome with full metadata."""
    test_name: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_type: str = "Cohen's d"
    sample_size: int = 0
    significance_label: str = "N/A"
    degrees_of_freedom: Optional[int] = None

@dataclass
class VariableAnalysis:
    """Detailed profile of a scientific variable including distribution metrics."""
    name: str
    dtype: str
    n_samples: int = 0
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    missing_pct: float = 0.0
    outliers_detected: int = 0
    coefficient_of_variation: float = 0.0

@dataclass
class ResultInterpretation:
    """The Final Scientific Verdict - Cognitive synthesis of analytical outputs."""
    experiment_id: str
    hypothesis_supported: Optional[bool]
    confidence: float
    summary: str
    key_findings: List[str]
    statistical_significance: str
    practical_significance: str
    biological_relevance: Optional[str]
    physical_implications: Optional[str]
    potential_confounds: List[str]
    follow_up_experiments: List[str]
    anomalies_detected: List[str]
    patterns_detected: List[str]
    overall_assessment: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class DataAnalyzerAgent:
    """
    Expert system for high-rigor data auditing and interpretation.
    """

    name = "data_analyzer_agent"
    capabilities = [
        "statistical-analysis", "scientific-visualization", "statsmodels", 
        "exploratory-data-analysis", "pandas", "scipy", "numpy", 
        "matplotlib", "seaborn", "polars", "vaex", "dask", 
        "pingouin", "umap-learn", "adversarial_audit"
    ]

    def __init__(self, llm_manager: Any = None):
        self.llm_manager = llm_manager
        self.interpretation_history: List[ResultInterpretation] = []
        # [TITAN V211.0] STATISTICAL SOVEREIGNTY
        # Physically abolished hardcoded p-values.
        from backend.discovery.constants import ScientificDefaults
        self.SIG_THRESHOLD = ScientificDefaults.ALPHA_SIGNIFICANCE
        self.EFFECT_THRESHOLD = float(os.getenv("SVEL_MIN_EFFECT", "0.3"))
        self.sandbox = GodModeSandbox()
        self.expert_system = get_expert_system()
        
        logger.info(" DataAnalyzerAgent (Professional Edition) Initialized.")

    async def run(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Primary analytical discovery loop.
        """
        context = context or {}
        payload = task.get("payload", {})
        data_path = payload.get("data_path") or task.get("query")
        
        if not data_path or not os.path.exists(data_path):
            alt_path = os.path.join(os.getcwd(), data_path) if data_path else ""
            if not os.path.exists(alt_path):
                return {"status": "error", "error": f"DATA_NOT_FOUND: Path {data_path} is unreachable."}
            data_path = alt_path

        try:
            # PROACTIVE CODE EXECUTION
            sandbox_stdout = ""
            sandbox_stderr = ""
            base_prompt = f"Write a rigorous Python script to analyze the dataset at {data_path}. Target Hypothesis: {payload.get('hypothesis', 'N/A')}. Use pandas and scipy.stats. Print key results."
            if self.llm_manager:
                logger.info(f" [ANALYSIS] Brainstorming analysis code for {data_path}...")
                analysis_prompt = await self.expert_system.inject_bundle(base_prompt, "data_analyst")
                
                code_resp = self.llm_manager.run(
                    analysis_prompt, 
                    source="data_analyzer_agent_codegen", 
                    model=CODE_GENERATION_MODEL
                )
                
                # Extract response text
                if isinstance(code_resp, dict):
                    analysis_code = code_resp.get("text", "")
                else:
                    analysis_code = str(code_resp)
                
                if "```python" in analysis_code:
                    analysis_code = analysis_code.split("```python")[1].split("```")[0].strip()
                elif "```" in analysis_code:
                    analysis_code = analysis_code.split("```")[1].split("```")[0].strip()

                logger.debug(f" Executing analysis code:\n{analysis_code}")
                exec_res = self.sandbox.run(analysis_code, profile="scientific")
                sandbox_stdout = getattr(exec_res, "stdout", "") or ""
                sandbox_stderr = getattr(exec_res, "stderr", "") or ""
                logger.info(f" Execution Status: {exec_res.exit_code}")
            
            # 1. DATA AUDIT (with delimiter sniffing)
            if str(data_path).endswith('.tsv'):
                df = pd.read_csv(data_path, sep='\t')
            else:
                df = pd.read_csv(data_path)
                if df.shape[1] == 1 and len(df.columns) == 1:
                    col0 = str(df.columns[0])
                    if ';' in col0:
                        df = pd.read_csv(data_path, sep=';')
                    elif '\t' in col0:
                        df = pd.read_csv(data_path, sep='\t')
            audit = self._audit_data_integrity(df)
            if sandbox_stdout:
                audit["sandbox_stdout"] = sandbox_stdout[:4000]
            if sandbox_stderr:
                audit["sandbox_stderr"] = sandbox_stderr[:1000]
            if audit["integrity_score"] < 0.3:
                return {"status": "failed", "error": "DATA_INTEGRITY_FAILURE", "details": audit}

            # 2. STATISTICAL ANALYSIS
            target = payload.get("target_col") or self._infer_target(df)
            tests = self._execute_rigorous_tests(df, target)
            variables = self._profile_variables(df)

            # 3. ANOMALY DETECTION
            anomalies = self._detect_statistical_anomalies(tests, variables)

            # 4. MULTIMODAL VERIFICATION
            fusion = self._bridge_to_images(df, context.get("image_folders", []))
            if sandbox_stdout:
                fusion["sandbox_stdout"] = sandbox_stdout[:4000]

            # 5. SCIENTIFIC INTERPRETATION
            hypothesis = payload.get("hypothesis") or context.get("active_hypothesis", "N/A")
            interpretation = await self._generate_phd_interpretation(
                audit=audit,
                tests=tests,
                variables=variables,
                anomalies=anomalies,
                fusion=fusion,
                hypothesis=hypothesis,
                domain=context.get("DOMAIN", "ml")
            )

            # Record to memory
            self.interpretation_history.append(interpretation)

            logger.info(f" Analysis complete: Verdict generated for {data_path}")
            return {
                "status": "success",
                "verdict": interpretation.to_dict(),
                "multimodal_status": fusion,
                "context": interpretation.summary
            }

        except Exception as e:
            logger.exception(f" Analytical loop failure: {e}")
            return {"status": "error", "error": str(e)}

    def _audit_data_integrity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check for data quality, sparsity, and potential leakage."""
        sparsity = df.isnull().mean().mean()
        dupes = df.duplicated().mean()
        
        # Identify columns with no variance
        constant_cols = [col for col in df.columns if df[col].nunique() <= 1]
        
        score = 1.0 - (sparsity * 0.4) - (dupes * 0.4) - (len(constant_cols)/max(1, len(df.columns)) * 0.2)
        
        return {
            "integrity_score": float(score),
            "n_samples": len(df),
            "n_features": len(df.columns),
            "sparsity": float(sparsity),
            "constant_features": constant_cols
        }

    def _execute_rigorous_tests(self, df: pd.DataFrame, target: str) -> List[StatisticalTestResult]:
        """Perform statistical tests based on distribution characteristics."""
        results = []
        if target not in df.columns: return results
        
        numeric_df = df.select_dtypes(include=[np.number])
        for col in numeric_df.columns:
            if col == target: continue
            
            try:
                data_x = df[col].dropna()
                data_y = df[target].dropna()
                common_idx = data_x.index.intersection(data_y.index)
                x, y = data_x[common_idx], data_y[common_idx]
                
                if len(x) < 5: continue

                # Check for normality
                if len(x) >= 8:
                    _, p_norm = stats.normaltest(x)
                    is_normal = p_norm > 0.05
                else:
                    is_normal = False

                if is_normal:
                    r, p = stats.pearsonr(x, y)
                    test_name = "Pearson Correlation"
                    eff_size = (2 * r) / math.sqrt(1 - r**2 + 1e-10)
                else:
                    rho, p = stats.spearmanr(x, y)
                    test_name = "Spearman Rank"
                    eff_size = rho

                results.append(StatisticalTestResult(
                    test_name=f"{test_name} ({col})",
                    statistic=float(r if is_normal else rho),
                    p_value=float(p),
                    effect_size=float(eff_size),
                    sample_size=len(x),
                    significance_label="Significant" if p < self.SIG_THRESHOLD else "Insignificant"
                ))
            except Exception: continue

        # Apply Benjamini-Hochberg FDR adjustment across all tested features to prevent multi-column p-hacking
        if len(results) > 1:
            m = len(results)
            order = np.argsort([res.p_value for res in results])
            adj_p = [1.0] * m
            prev_bh = 1.0
            for rank_rev in range(m - 1, -1, -1):
                idx = int(order[rank_rev])
                rank = rank_rev + 1
                bh_val = min(prev_bh, results[idx].p_value * m / rank)
                prev_bh = bh_val
                adj_p[idx] = float(min(1.0, bh_val))
            for idx, res in enumerate(results):
                res.p_value = adj_p[idx]
                res.significance_label = "Significant" if adj_p[idx] < self.SIG_THRESHOLD else "Insignificant"
            
        return results

    def _profile_variables(self, df: pd.DataFrame) -> List[VariableAnalysis]:
        """Deep profiling of variable distributions."""
        profiles = []
        for col in df.columns[:15]:
            series = df[col]
            analysis = VariableAnalysis(name=col, dtype=str(series.dtype), n_samples=len(series))
            
            if pd.api.types.is_numeric_dtype(series):
                clean = series.dropna()
                if not clean.empty:
                    analysis.mean = float(clean.mean())
                    analysis.std = float(clean.std())
                    analysis.min = float(clean.min())
                    analysis.max = float(clean.max())
                    analysis.missing_pct = float(series.isnull().mean() * 100)
                    if abs(analysis.mean) > 1e-9:
                        analysis.coefficient_of_variation = analysis.std / abs(analysis.mean)
            
            profiles.append(analysis)
        return profiles

    def _detect_statistical_anomalies(self, tests: List[StatisticalTestResult], 
                                     variables: List[VariableAnalysis]) -> List[str]:
        """Identify potential statistical traps or data instabilities."""
        anomalies = []
        
        for test in tests:
            if test.p_value < 0.001 and abs(test.effect_size) < 0.1:
                anomalies.append(f"OVERPOWERED: '{test.test_name}' is significant only due to sample size (N={test.sample_size}).")
            
            if test.p_value > 0.1 and abs(test.effect_size) > 0.6:
                anomalies.append(f"UNDERPOWERED: '{test.test_name}' shows a large effect ({test.effect_size:.2f}) but failed significance.")

        for var in variables:
            if var.coefficient_of_variation > 5.0:
                anomalies.append(f"EXTREME_VARIANCE: Variable '{var.name}' has noise-to-signal ratio > 5.0.")

        return anomalies

    def _bridge_to_images(self, df: pd.DataFrame, folders: List[str]) -> Dict[str, Any]:
        """Verify physical availability of auxiliary imaging data."""
        status = {"ready": False, "found_folders": [], "mapping": "none"}
        
        # Check input folders dynamically
        for folder in folders:
            if folder and os.path.exists(folder):
                status["found_folders"].append(folder)
                status["ready"] = True
                
        # Also check dynamic targets based on session environment
        session_id = os.environ.get("SVEL_SESSION_ID", "").lower()
        if "cifar" in session_id:
            for d in ["cifar-100-python", "cifar100", "data/cifar100"]:
                if os.path.exists(d):
                    status["found_folders"].append(d)
                    status["ready"] = True
        elif "sars" in session_id or "covid" in session_id:
            targets = ["SARS-CoV-2_data", "COVID-19_Lung_CT_Scans"]
            for t in targets:
                if os.path.exists(t):
                    status["found_folders"].append(t)
                    status["ready"] = True
        
        if any(c in df.columns for col in df.columns for c in ["id", "accession", "sequence"]):
            status["mapping"] = "ID_MATCH_PROBABLE"
            
        return status

    async def _generate_phd_interpretation(self, audit: Dict, tests: List[StatisticalTestResult], 
                                          variables: List[VariableAnalysis], anomalies: List[str],
                                          fusion: Dict, hypothesis: str, domain: str) -> ResultInterpretation:
        """Synthesize analytical outputs into a peer-review ready interpretation."""
        if not self.llm_manager:
            return self._create_fallback(audit, tests)

        evidence = "\n".join([f"- {t.test_name}: p={t.p_value:.4f}, effect={t.effect_size:.2f}" for t in tests[:10]])
        distribution = "\n".join([f"- {v.name}: CV={v.coefficient_of_variation:.2f}, missing={v.missing_pct:.1f}%" for v in variables[:5]])

        import re
        session_id = os.environ.get("SVEL_SESSION_ID", "").lower()
        domain = (domain or os.environ.get("SVEL_DOMAIN", "")).lower()
        hyp_low = hypothesis.lower()
        
        # Explicitly protect natural sciences from being flagged as ML
        is_natural_science = any(d in domain or d in hyp_low for d in ["biology", "biomedical", "biophysics", "chemistry", "physics", "medicine", "protein", "sars", "spike", "rbd", "ace2"])
        
        ml_pattern = r'\b(neural network|deep learning|transformer architecture|vision transformer|cifar|imagenet|pruning|flops|backprop|autoencoder)\b'
        is_ml = not is_natural_science and (
            domain in ["cs", "ml", "machine_learning", "deep_learning"] or
            bool(re.search(ml_pattern, hyp_low)) or
            bool(re.search(ml_pattern, session_id))
        )
        
        relevance_field = '"model_implications": "Explain what these results imply for neural network architecture, performance, or capacity"' if is_ml else '"domain_relevance": "Explain domain-specific physical/biological relevance or causal mechanism"'

        prompt = f"""
        {_SCIENTIST_SYSTEM_PROMPT}

        HYPOTHESIS TO AUDIT:
        {hypothesis}

        PHYSICAL EVIDENCE (STATISTICAL TESTS):
        {evidence}

        DATA ENVIRONMENT (VARIABLES):
        {distribution}

        ANOMALIES DETECTED BY HEURISTIC AUDIT:
        {anomalies}

        REPORT REQUIREMENTS:
        1. STATISTICAL SIGNIFICANCE: Interpret p-values in context of effect size.
        2. SCIENTIFIC RELEVANCE: Prioritize practical meaning over raw statistics.
        3. CONFOUNDS: Identify potential data biases.
        4. FOLLOW-UP: Recommend 3-5 specific validation experiments.

        OUTPUT THE VERDICT IN VALID JSON FORMAT ONLY.
        {{
            "hypothesis_supported": true/false/null,
            "confidence": 0.0-1.0,
            "summary": "Professional overview",
            "key_findings": [],
            "significance_interpretation": "",
            "practical_significance": "",
            {relevance_field},
            "potential_confounds": [],
            "follow_up_experiments": [],
            "overall_assessment": ""
        }}
        """
        try:
            resp = self.llm_manager.run(prompt=prompt, model=CODE_GENERATION_MODEL)
            
            if isinstance(resp, dict):
                raw = resp.get("text", "{}")
            else:
                raw = str(resp)
                
            if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
            from backend.utils.json_repair import repair_json
            data = repair_json(raw)
            if not isinstance(data, dict):
                data = json.loads(raw)
            
            # Generate Unique ID for the experiment
            exp_id = f"audit_{uuid.uuid4().hex[:8]}"
            
            return ResultInterpretation(
                experiment_id=exp_id,
                hypothesis_supported=data.get("hypothesis_supported"),
                confidence=data.get("confidence", 0.0),
                summary=data.get("summary", ""),
                key_findings=data.get("key_findings", []),
                statistical_significance=data.get("significance_interpretation", ""),
                practical_significance=data.get("practical_significance", ""),
                biological_relevance=None if is_ml else (data.get("domain_relevance") or data.get("biological_relevance")),
                physical_implications=data.get("model_implications") if is_ml else data.get("physical_implications"),
                potential_confounds=data.get("potential_confounds", []),
                follow_up_experiments=data.get("follow_up_experiments", []),
                anomalies_detected=anomalies + data.get("anomalies_detected", []),
                patterns_detected=self._detect_cross_history_patterns(),
                overall_assessment=data.get("overall_assessment", "")
            )
        except Exception as e:
            logger.error(f" Interpretation Synthesis Failed: {e}")
            return self._create_fallback(audit, tests)

    def _detect_cross_history_patterns(self) -> List[str]:
        """Search the agent's memory for longitudinal trends."""
        patterns = []
        if len(self.interpretation_history) < 2: return patterns
        
        supports = [h.hypothesis_supported for h in self.interpretation_history if h.hypothesis_supported is not None]
        if len(supports) >= 3 and all(supports):
            patterns.append("CONVERGENCE: Strong cross-modal confirmation across multiple datasets.")
            
        return patterns

    def _create_fallback(self, audit: Dict, tests: List[StatisticalTestResult]) -> ResultInterpretation:
        """Safety fallback for system failures."""
        return ResultInterpretation(
            experiment_id=f"fallback_{uuid.uuid4().hex[:8]}",
            hypothesis_supported=None,
            confidence=0.0,
            summary="Automated audit completed. Basic statistical correlations detected. Neural synthesis unavailable.",
            key_findings=[f"Audited {audit['n_samples']} samples."],
            statistical_significance="Unverified.",
            practical_significance="Requires manual peer-review.",
            biological_relevance=None,
            physical_implications=None,
            potential_confounds=["Neural layer failure"],
            follow_up_experiments=["Verify data pipeline integrity"],
            anomalies_detected=[],
            patterns_detected=[],
            overall_assessment="DEGRADED: Running on physical heuristics only."
        )

    def _infer_target(self, df: pd.DataFrame) -> str:
        """Identify primary dependent variable from common scientific identifiers."""
        for c in ["yield", "target", "label", "outcome", "severity", "mortality"]:
            if c in df.columns: return c
        return df.columns[-1]
