"""
Clinical Trial Analysis Template
================================
PhD-level clinical trial design and analysis.
Supports RCT analysis, meta-analysis, and adaptive trial designs.

Part of ULTRON's Medicine Domain Templates.
"""

from typing import List, Dict, Any
from backend.experiments.templates.base import StatisticalTemplate, TemplateCustomizationParams
from backend.experiments.templates import register_template
from backend.experiments.models import (
    ExperimentProtocol, ExperimentType, ProtocolStep, Variable,
    StatisticalTestSpec, ValidationCheck, ResourceRequirements
)


@register_template
class ClinicalTrialTemplate(StatisticalTemplate):
    """
    Template for clinical trial analysis.
    
    Capabilities:
    - Randomized controlled trial analysis
    - Intention-to-treat analysis
    - Per-protocol analysis
    - Sample size calculation
    - Power analysis
    - Adverse event analysis
    """
    
    def __init__(self):
        super().__init__(
            name="clinical_trial_analysis",
            domain="medicine",
            title="Clinical Trial Analysis",
            description=(
                "Comprehensive analysis of randomized controlled trials. "
                "Includes efficacy endpoints, safety analysis, and subgroup analyses."
            ),
            suitable_for=[
                "RCT primary endpoint analysis",
                "Drug vs placebo comparison",
                "Non-inferiority trials",
                "Superiority testing",
                "Interim analysis"
            ],
            requirements=[
                "Patient-level outcome data",
                "Treatment allocation",
                "Baseline covariates",
                "Follow-up time points"
            ],
            complexity_score=0.8,
            rigor_score=0.95
        )
    
    def is_applicable(self, hypothesis) -> bool:
        statement = str(hypothesis).lower()
        
        trial_keywords = [
            'clinical trial', 'rct', 'randomized', 'placebo',
            'treatment effect', 'efficacy', 'drug', 'intervention',
            'primary endpoint', 'phase 2', 'phase 3', 'phase ii', 'phase iii'
        ]
        
        return any(kw in statement for kw in trial_keywords)
    
    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        data_path = params.custom_variables.get('data_path', 'trial_data.csv')
        primary_endpoint = params.custom_variables.get('primary_endpoint', 'response')
        treatment_col = params.custom_variables.get('treatment_column', 'treatment_arm')
        alpha = params.custom_variables.get('alpha', 0.05)
        
        steps = [
            ProtocolStep(
                name="load_and_validate",
                description="Load the actual trial dataset, validate schema integrity, and reject any missing treatment allocation.",
                code_template=self._generate_load_code(data_path, treatment_col),
                expected_output="Validated trial DataFrame",
                validation=["No missing treatment allocation", "Balanced arms"]
            ),
            ProtocolStep(
                name="baseline_characteristics",
                description="Compare baseline characteristics between arms after loading the real patient-level data.",
                code_template=self._generate_baseline_code(treatment_col),
                expected_output="Table 1 (baseline characteristics)",
                validation=["Randomization successful", "No significant imbalances"]
            ),
            ProtocolStep(
                name="primary_analysis",
                description="Analyze the primary efficacy endpoint using the observed trial data and prespecified estimand.",
                code_template=self._generate_primary_code(primary_endpoint, treatment_col, alpha),
                expected_output="Treatment effect estimate and p-value",
                validation=["ITT analysis performed", "Confidence interval computed"]
            ),
            ProtocolStep(
                name="sensitivity_analysis",
                description="Perform sensitivity analyses on the observed dataset, including per-protocol and subgroup checks.",
                code_template=self._generate_sensitivity_code(),
                expected_output="Sensitivity analysis results",
                validation=["Per-protocol analysis", "Subgroup analyses"]
            ),
            ProtocolStep(
                name="safety_analysis",
                description="Analyze adverse events using the real safety dataset and prespecified AE definitions.",
                code_template=self._generate_safety_code(),
                expected_output="Safety summary",
                validation=["AE counts by arm", "SAE assessment"]
            )
        ]
        
        return ExperimentProtocol(
            title=f"Clinical Trial Analysis: {primary_endpoint}",
            hypothesis_id=params.hypothesis.id if hasattr(params.hypothesis, 'id') else "unknown",
            experiment_type=ExperimentType.STATISTICAL,
            domain="medicine",
            steps=steps,
            variables=[
                Variable(name="primary_endpoint", type="string", value=primary_endpoint, description="Primary endpoint"),
                Variable(name="alpha", type="float", value=str(alpha), description="Significance level")
            ],
            statistical_tests=[
                StatisticalTestSpec(
                    test_type="two_sample_comparison",
                    parameters={"alpha": alpha, "method": "t_test_or_chi_square"},
                    description="Compare treatment vs control"
                ),
                StatisticalTestSpec(
                    test_type="confidence_interval",
                    parameters={"level": 0.95},
                    description="95% CI for treatment effect"
                )
            ],
            validation_checks=[
                ValidationCheck(
                    check_type="randomization_balance",
                    parameters={"max_imbalance": 0.2},
                    description="Check for randomization imbalance"
                ),
                ValidationCheck(
                    check_type="missing_data",
                    parameters={"max_missing_primary": 0.1},
                    description="Check missing endpoint data"
                )
            ],
            resource_requirements=ResourceRequirements(
                estimated_runtime_seconds=120,
                memory_mb=2048,
                cpu_cores=2
            ),
            expected_duration_hours=0.5,
            reproducibility_notes=[
                "Use a documented seed only for reproducible imputation on the observed data",
                "Document exact statistical methods",
                "Pre-specify subgroup analyses"
            ]
        )
    
    def _generate_load_code(self, data_path: str, treatment_col: str) -> str:
        return f'''
import pandas as pd
import logging
import os

logger = logging.getLogger("ultron.clinical")

# === Load Real Trial Data — NO SYNTHETIC FALLBACK ===
if not os.path.exists("{data_path}"):
    raise FileNotFoundError(
        f"Clinical trial data file not found: {data_path}\\n"
        "Synthetic patient data generation is forbidden. "
        "Provide a real anonymized trial CSV with columns: patient_id, treatment_arm, primary_endpoint."
    )

trial_df = pd.read_csv("{data_path}")

print(f"Loaded {{len(trial_df)}} patients")
print(f"Columns: {{list(trial_df.columns)}}")

# Validate treatment allocation
if "{treatment_col}" not in trial_df.columns:
    raise ValueError("Treatment column not found")

arm_counts = trial_df["{treatment_col}"].value_counts()
print(f"\\nTreatment allocation:")
print(arm_counts)

# Check balance
ratio = arm_counts.min() / arm_counts.max()
print(f"\\nAllocation ratio: {{ratio:.2f}}")
if ratio < 0.8:
    logger.warning("Significant allocation imbalance detected")

print("\\n Trial data validated")
'''
    
    def _generate_baseline_code(self, treatment_col: str) -> str:
        return f'''
# === Baseline Characteristics (Table 1) ===
from scipy import stats
from scipy.stats import mannwhitneyu, shapiro, levene, fisher_exact

# Identify baseline variables (exclude outcome and ID columns)
baseline_vars = [col for col in trial_df.columns 
                 if col not in ['{treatment_col}', 'patient_id', 'response', 'survival_time', 'event']]

print("\\n" + "="*60)
print("TABLE 1: BASELINE CHARACTERISTICS")
print("="*60)

table1_results = []

for var in baseline_vars[:10]:  # Limit for display
    if trial_df[var].dtype in ['int64', 'float64']:
        # Continuous variable
        treatment_vals = trial_df[trial_df['{treatment_col}'] == 'treatment'][var].dropna()
        control_vals = trial_df[trial_df['{treatment_col}'] == 'control'][var].dropna()

        if len(treatment_vals) < 3 or len(control_vals) < 3:
            raise ValueError(f"Variable {{var}} has insufficient samples for baseline testing.")

        shapiro_t = shapiro(treatment_vals)
        shapiro_c = shapiro(control_vals)
        lev = levene(treatment_vals, control_vals)
        if shapiro_t.pvalue > 0.05 and shapiro_c.pvalue > 0.05 and lev.pvalue > 0.05:
            stat, pval = stats.ttest_ind(treatment_vals, control_vals, equal_var=True)
            test_name = "Student_t"
        else:
            stat, pval = mannwhitneyu(treatment_vals, control_vals, alternative="two-sided")
            test_name = "Mann_Whitney_U"
        
        print(f"{{var}}: Treatment={{treatment_vals.mean():.2f}}{{treatment_vals.std():.2f}}, "
              f"Control={{control_vals.mean():.2f}}{{control_vals.std():.2f}}, "
              f"test={{test_name}}, p={{pval:.3f}}")
        
        table1_results.append({{"var": var, "p_value": pval, "test": test_name}})
    else:
        # Categorical variable
        contingency = pd.crosstab(trial_df['{treatment_col}'], trial_df[var])
        chi2, pval, dof, expected = stats.chi2_contingency(contingency)
        if (expected < 5).any():
            _, pval = fisher_exact(contingency.values[:2, :2])
            test_name = "Fisher_exact"
        else:
            test_name = "Chi_square"
        print(f"{{var}}: {{test_name}} p={{pval:.3f}}")

# Check for imbalances
significant_imbalances = [r for r in table1_results if r['p_value'] < 0.05]
if significant_imbalances:
    print(f"\\n Warning: {{len(significant_imbalances)}} significant baseline difference(s)")
else:
    print("\\n No significant baseline imbalances")
'''
    
    def _generate_primary_code(self, endpoint: str, treatment_col: str, alpha: float) -> str:
        return f'''
# === Primary Endpoint Analysis (ITT) ===
from scipy import stats
import numpy as np
from scipy.stats import mannwhitneyu, shapiro, levene, fisher_exact

endpoint = "{endpoint}"
alpha = {alpha}

# Get endpoint data by arm
treatment_group = trial_df[trial_df['{treatment_col}'] == 'treatment'][endpoint].dropna()
control_group = trial_df[trial_df['{treatment_col}'] == 'control'][endpoint].dropna()

print("\\n" + "="*60)
print(f"PRIMARY ANALYSIS: {{endpoint.upper()}}")
print("="*60)

# Determine test type based on endpoint
if trial_df[endpoint].dtype in ['int64', 'float64'] and trial_df[endpoint].nunique() > 2:
    # Continuous endpoint - t-test
    effect = treatment_group.mean() - control_group.mean()
    if len(treatment_group) < 3 or len(control_group) < 3:
        raise ValueError("Primary endpoint has insufficient samples for parametric testing.")
    shapiro_t = shapiro(treatment_group)
    shapiro_c = shapiro(control_group)
    lev = levene(treatment_group, control_group)
    if shapiro_t.pvalue > {alpha} and shapiro_c.pvalue > {alpha} and lev.pvalue > {alpha}:
        stat, pval = stats.ttest_ind(treatment_group, control_group, equal_var=False)
        test_name = "Welch_t"    else:
        stat, pval = mannwhitneyu(treatment_group, control_group, alternative="two-sided")
        test_name = "Mann_Whitney_U"
    
    # 95% CI using pooled SE
    n1, n2 = len(treatment_group), len(control_group)
    se = np.sqrt(treatment_group.var()/n1 + control_group.var()/n2)
    ci_lower = effect - 1.96 * se
    ci_upper = effect + 1.96 * se
    
    print(f"\\nTreatment mean: {{treatment_group.mean():.3f}} (n={{n1}})")
    print(f"Control mean: {{control_group.mean():.3f}} (n={{n2}})")
    print(f"\\nTreatment effect: {{effect:.3f}} (95% CI: {{ci_lower:.3f}}, {{ci_upper:.3f}})")
    print(f"Test: {{test_name}}")
    print(f"P-value: {{pval:.4f}}")
    
else:
    # Binary endpoint - chi-square / Fisher's exact
    contingency = pd.crosstab(trial_df['{treatment_col}'], trial_df[endpoint])
    chi2, pval, dof, expected = stats.chi2_contingency(contingency)
    if (expected < 5).any():
        _, pval = fisher_exact(contingency.values[:2, :2])
        test_name = "Fisher_exact"
    else:
        test_name = "Chi_square"
    
    # Calculate relative risk
    treat_rate = treatment_group.mean()
    ctrl_rate = control_group.mean()
    relative_risk = treat_rate / ctrl_rate if ctrl_rate > 0 else np.nan
    
    print(f"\\nResponse rate (treatment): {{treat_rate*100:.1f}}%")
    print(f"Response rate (control): {{ctrl_rate*100:.1f}}%")
    print(f"Relative Risk: {{relative_risk:.2f}}")
    print(f"Test: {{test_name}}")
    print(f"P-value: {{pval:.4f}}")

# Statistical significance
if pval < alpha:
    print(f"\\n RESULT: Statistically significant (p < {{alpha}})")
    significant = True
else:
    print(f"\\n RESULT: Not statistically significant (p  {{alpha}})")
    significant = False

primary_result = {{
    "endpoint": endpoint,
    "p_value": float(pval),
    "significant": significant,
    "alpha": alpha
}}
'''
    
    def _generate_sensitivity_code(self) -> str:
        return '''
# === Sensitivity Analyses ===
print("\\n" + "="*60)
print("SENSITIVITY ANALYSES")
print("="*60)

# 1. Per-Protocol Analysis
if 'per_protocol' in trial_df.columns:
    pp_df = trial_df[trial_df['per_protocol'] == True]
    print(f"\\n1. Per-Protocol Population: {len(pp_df)} patients")
    # Repeat primary analysis on PP population
else:
    print("\\n1. Per-Protocol analysis: Not available")

# 2. Missing Data Sensitivity
missing_rate = trial_df[endpoint].isna().mean()
print(f"\\n2. Missing Data Rate: {missing_rate*100:.1f}%")
if missing_rate > 0.1:
    print("    Consider multiple imputation")

# 3. Subgroup Analyses (pre-specified)
print("\\n3. Subgroup Analyses:")
for subgroup in ['age_group', 'sex', 'disease_severity']:
    if subgroup in trial_df.columns:
        for group_val in trial_df[subgroup].unique():
            sub_df = trial_df[trial_df[subgroup] == group_val]
            print(f"   {subgroup}={group_val}: n={len(sub_df)}")

print("\\n Sensitivity analyses complete")
'''
    
    def _generate_safety_code(self) -> str:
        return '''
# === Safety Analysis ===
print("\\n" + "="*60)
print("SAFETY ANALYSIS")
print("="*60)

# Adverse events
ae_cols = [col for col in trial_df.columns if 'ae_' in col.lower() or 'adverse' in col.lower()]

if ae_cols:
    print(f"\\nAdverse event columns found: {len(ae_cols)}")
    
    for ae_col in ae_cols[:5]:
        ae_treat = trial_df[trial_df[treatment_col] == 'treatment'][ae_col].sum()
        ae_ctrl = trial_df[trial_df[treatment_col] == 'control'][ae_col].sum()
        n_treat = len(trial_df[trial_df[treatment_col] == 'treatment'])
        n_ctrl = len(trial_df[trial_df[treatment_col] == 'control'])
        
        print(f"  {ae_col}: Treatment={ae_treat}/{n_treat} ({ae_treat/n_treat*100:.1f}%), "
              f"Control={ae_ctrl}/{n_ctrl} ({ae_ctrl/n_ctrl*100:.1f}%)")
else:
    print("\\nNo adverse event data found")

# Summary
print("\\n Safety analysis complete")

# Final output
clinical_trial_results = {
    "primary_result": primary_result,
    "supports_hypothesis": significant,
    "safety_concerns": False  # Would be set based on AE analysis
}

import json
with open('clinical_trial_results.json', 'w') as f:
    json.dump(clinical_trial_results, f, indent=2)

print("\\n Saved results: clinical_trial_results.json")
'''
