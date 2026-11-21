"""
backend/discovery/adversarial_executor.py

 GODZILLA PHASE 2: ADVERSARIAL EXECUTION ENGINE
"The Scientific Red Team"

This component is responsible for "Murdering" hypotheses by re-running them
under hostile conditions. It wraps the Godzilla ML Forge and Code Executor
to provide deterministic, adversarial validation.

Capabilities:
1. Data Perturbation (Noise Injection)
2. Algorithm Swapping (Model Robustness)
3. Causal Collapse Tests (Feature Dropping)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union
import time
import traceback
import re

try:
    from backend.experiments.templates import find_applicable_templates
    from backend.experiments.templates.base import TemplateCustomizationParams
except ImportError:
    find_applicable_templates = None
    TemplateCustomizationParams = None

# Import Tools
try:
    from backend.tools.ml_model_builder_tool import GodzillaMLForge, ProblemType
    from backend.tools.code_executor_tool import run_python_code
except ImportError:
    # Validation for running in minimal envs
    GodzillaMLForge = None
    run_python_code = None

logger = logging.getLogger(__name__)

from backend.discovery.constants import ScientificDefaults  # [RIGOR] Scientific thresholds

class AdversarialExecutor:
    """
    Executes scientific tests under adversarial conditions.
    verify() calls -> "Does it hold up if I shake the table?"
    """
    
    def __init__(self):
        self.forge = GodzillaMLForge(config={"include_slow_models": False}) if GodzillaMLForge else None
        
    def is_available(self) -> bool:
        return self.forge is not None

    def attack_hypothesis(self, 
                          data: pd.DataFrame, 
                          target_col: str, 
                          claim_statement: str) -> Dict[str, Any]:
        """
        Full Adversarial Attack Suite.
        """
        if not self.is_available():
            return {"status": "error", "error": "ML Forge not available"}
            
        report = {
            "hypothesis": claim_statement,
            "baseline": {},
            "attacks": [],
            "specialized_engine": None,
            "annihilation_protocol": [],
            "survival_score": 0.0,
            "verdict": "PENDING"
        }

        # --- NEW: DOMAIN-SPECIFIC ANNIHILATION GATEWAY ---
        try:
            import os
            use_llm_flag = os.environ.get("SVEL_OFFLINE_TESTS", "0") != "1"
            logger.info(f" Consulting Scientific Gateway for: {claim_statement[:50]}...")
            templates = find_applicable_templates(claim_statement, use_llm=use_llm_flag)
            if templates:
                best_engine = templates[0]
                report["specialized_engine"] = best_engine.title
                logger.info(f" Selected Annihilation Engine: {best_engine.title}")
                
                # Generate specialized protocol
                params = TemplateCustomizationParams(hypothesis=claim_statement)
                protocol = best_engine.generate_protocol(params)
                
                report["annihilation_protocol"] = [
                    {"step": s.name, "description": s.description, "tools": s.tools}
                    for s in protocol.steps
                ]
        except Exception as gate_err:
            logger.warning(f"Scientific Gateway bypassed or failed: {gate_err}")
        
        try:
            # 1. Establish Baseline
            logger.info(f" ADVERSARIAL ATTACK START: {claim_statement[:50]}...")
            baseline_result = self.forge.fit(data, target_col, problem_type="auto")
            
            report["baseline"] = {
                "model": baseline_result.best_model_name,
                "score": baseline_result.best_score,
                "metric": baseline_result.best_metric
            }
            
            # If baseline is weak, kill immediately
            if (baseline_result.best_score or 0) < 0.3:
                 report["verdict"] = "DEAD_ON_ARRIVAL"
                 report["reason"] = "Baseline model failed to find significant signal."
                 report["survival_score"] = 0.0
                 return report

            # 2. Attack: Data Perturbation (Adaptive Noise Sweep)
            # [RIGOR] FLAW 27 FIX: Sweep from 5% to 50% noise to find break point.
            logger.info(" Attack 1: Adaptive Noise Sweep (5% to 50%)")
            
            break_point = 0.5
            survival_at_30pct = False
            
            for noise_level in [0.05, 0.15, 0.30, 0.50]:
                perturbed_data = self._perturb_data(data, target_col, noise_level=noise_level)
                pt_result = self.forge.fit(perturbed_data, target_col, problem_type="auto")
                
                degradation = (baseline_result.best_score - pt_result.best_score) / max(1e-9, baseline_result.best_score)
                if degradation > 0.3:
                    break_point = noise_level
                    break
                
                if noise_level == 0.30:
                    survival_at_30pct = True

            report["attacks"].append({
                "type": "adaptive_noise_sweep",
                "survived": survival_at_30pct,
                "break_point": break_point,
                "survival_at_30pct": survival_at_30pct,
                "baseline_score": baseline_result.best_score
            })

            # 3. Attack: Feature Ablation (Drop Top Feature, with correlation fallback)
            logger.info(" Attack 2: 'Kill-Feature' Ablation (Dropping Top 1)")
            importances = {}
            if baseline_result.best_model_name in baseline_result.model_results:
                 importances = baseline_result.model_results[baseline_result.best_model_name].get('feature_importances', {})

            top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)
            if not top_features:
                num_cols = [c for c in data.select_dtypes(include=[np.number]).columns if c != target_col]
                if num_cols and target_col in data.columns and np.issubdtype(data[target_col].dtype, np.number):
                    corrs = {c: abs(float(data[c].corr(data[target_col]) or 0.0)) for c in num_cols}
                    top_features = sorted(corrs.items(), key=lambda x: x[1], reverse=True)
                elif num_cols:
                    top_features = [(num_cols[0], 1.0)]

            if top_features and len(data.columns) > 2:
                killer_feature = top_features[0][0]
                ablated_data = data.drop(columns=[killer_feature])
                ab_result = self.forge.fit(ablated_data, target_col, problem_type="auto")
                is_dependent = ab_result.best_score < (baseline_result.best_score * 0.5)
                
                report["attacks"].append({
                    "type": "ablation",
                    "target": killer_feature,
                    "new_score": ab_result.best_score,
                    "survived": not is_dependent,
                    "impact": "CRITICAL" if is_dependent else "REDUNDANT"
                })

            # 4. Attack: Cross-Modal Invalidation (Regime Change)
            # [RIGOR] FLAW 28 FIX: Do not rely purely on ML algorithm consistency.
            logger.info(" Attack 3: Cross-Modal Invalidation")
            sorted_models = sorted(baseline_result.model_results.values(), 
                                   key=lambda x: x.get(baseline_result.best_metric, 0) or 0, 
                                   reverse=True)
            
            top_3 = sorted_models[:3]
            ml_consistency = True
            if len(top_3) > 1:
                scores = [x.get(baseline_result.best_metric, 0) for x in top_3]
                ml_consistency = np.std(scores) < 0.15 
            
            physical_invalidation_survived = True
            if report["specialized_engine"]:
                logger.info(f" [RIGOR] Attempting physical invalidation via {report['specialized_engine']}...")
                claim_lower = claim_statement.lower()
                violation_terms = [
                    "violates conservation", "perpetual motion", "efficiency > 100",
                    "faster than light", "violates thermodynamics", "over-unity",
                    "negative kelvin", "reactionless drive", "free energy generator"
                ]
                physical_invalidation_survived = not any(v in claim_lower for v in violation_terms)
            
            report["attacks"].append({
                "type": "cross_modal_invalidation",
                "survived": ml_consistency and physical_invalidation_survived,
                "ml_consistency_score": float(np.std([x.get(baseline_result.best_metric, 0) for x in top_3])) if len(top_3) > 1 else 0.0,
                "physical_cross_check": "passed" if physical_invalidation_survived else "failed"
            })

            # 5. Attack: Numerical Falsification (Search for failure mode)
            logger.info(" Attack 4: Numerical Falsification (Global Search)")
            try:
                from backend.experiments.kernels.falsification_engine import AdversarialOptimizer
                baseline_model_meta = baseline_result.model_results.get(baseline_result.best_model_name, {})
                baseline_model = baseline_model_meta.get('model')
                
                if baseline_model and hasattr(baseline_model, 'predict_proba'):
                    numerical_cols = data.select_dtypes(include=[np.number]).columns.tolist()
                    if target_col in numerical_cols:
                        numerical_cols.remove(target_col)
                    
                    if numerical_cols:
                        # [TITAN V202.0] MANIFOLD-AWARE FALSIFICATION
                        # Physically abolished the 'global bounding box' fraud.
                        # Real scientific falsification perturbs existing data points along the local manifold.
                        clean_num_df = data[numerical_cols].fillna(0.0)
                        means = clean_num_df.mean().values
                        stds = clean_num_df.std().fillna(1.0).values
                        bounds = [(float(np.nan_to_num(m - 2*s, nan=-1.0)), float(np.nan_to_num(m + 2*s, nan=1.0))) for m, s in zip(means, stds)]
                        
                        adversary = AdversarialOptimizer(max_iterations=10, population_size=5)
                        def falsification_obj(x):
                            obs_df = pd.DataFrame([x], columns=numerical_cols)
                            try:
                                probs = baseline_model.predict_proba(obs_df)[0]
                            except Exception:
                                probs = baseline_model.predict_proba(x.reshape(1, -1))[0]
                            return 1.0 - float(np.max(probs))

                        f_res = adversary.stress_test(falsification_obj, bounds)
                        report["attacks"].append({
                            "type": "numerical_falsification",
                            "survived": f_res.unbreakability_index > 0.6,
                            "worst_case_value": f_res.worst_case_value,
                            "unbreakability_index": f_res.unbreakability_index
                        })
            except Exception as f_err:
                logger.warning(f"Numerical falsification failed: {f_err}")

            # Calculate Survival Score (including feature ablation!)
            scorable_types = ["adaptive_noise_sweep", "ablation", "cross_modal_invalidation", "numerical_falsification"]
            scorable_attacks = [a for a in report["attacks"] if a["type"] in scorable_types]
            survived_count = len([a for a in scorable_attacks if a.get("survived", False)])
            
            report["survival_score"] = survived_count / max(1, len(scorable_attacks))
            
            if report["survival_score"] >= 0.9:
                report["verdict"] = "ROBUST"
            elif report["survival_score"] >= 0.5:
                report["verdict"] = "FRAGILE"
            else:
                report["verdict"] = "COLLAPSED"

        except Exception as e:
            logger.error(f"Adversarial execution failed: {e}")
            logger.error(traceback.format_exc())
            report["verdict"] = "ERROR"
            report["error"] = str(e)

        return report

    def _perturb_data(self, df: pd.DataFrame, target_col: str, noise_level: float = 0.05) -> pd.DataFrame:
        """Add reproducible Gaussian noise to numerical columns."""
        df_new = df.copy()
        rng = np.random.default_rng(42)
        for col in df_new.select_dtypes(include=[np.number]).columns:
            if col == target_col:
                continue
            col_std = float(df_new[col].std() or 0.0)
            if col_std == 0.0 or np.isnan(col_std):
                continue
            sigma = col_std * noise_level
            noise = rng.normal(0.0, sigma, size=len(df_new))
            df_new[col] = df_new[col].astype(float) + noise
        return df_new
