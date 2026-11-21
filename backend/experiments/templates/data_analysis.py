"""
SVEL DATA ANALYSIS TEMPLATES
==============================
Rigorous statistical frameworks for empirical validation.
All analyses require physical data loading and proper assumption testing.
"""

from typing import List, Dict, Any, Optional
import re
import logging

from backend.experiments.models import (
    ExperimentProtocol,
    ProtocolStep,
    Variable,
    ControlGroup,
    ResourceRequirements,
    StatisticalTestSpec,
    ExperimentType
)
from backend.experiments.templates.base import (
    TemplateBase,
    TemplateCustomizationParams
)
from backend.experiments.templates import register_template

logger = logging.getLogger(__name__)

@register_template
class TTestComparisonTemplate(TemplateBase):
    """
    Template for rigorous two-group comparison.
    """

    def __init__(self):
        super().__init__(
            name="t_test_comparison",
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="general",
            title="Rigorous Group Comparison (SVEL-APEX)",
            description="Compare means with mandatory assumption checking (Normality/Levene) and effect size calculation.",
            suitable_for=["Two-group comparisons", "Mean difference testing", "Treatment vs control"],
            requirements=["scipy", "pandas", "numpy", "statsmodels"],
            complexity_score=0.8,
            rigor_score=1.0
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        statement = str(hypothesis).lower()
        comparison_keywords = ["greater than", "less than", "higher than", "vs", "between", "compare"]
        return any(keyword in statement for keyword in comparison_keywords)

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"Rigorous Group Comparison: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="general",
            description=self.description,
            steps=[
                ProtocolStep(
                    name="assumption_testing",
                    description=(
                        "1. Load the actual dataset from the provided source.\n"
                        "2. Perform Shapiro-Wilk normality testing on each group.\n"
                        "3. Perform Levene's variance homogeneity test before selecting the final test.\n"
                        "4. Select Welch's t-test or Mann-Whitney U only after the prerequisite diagnostics are computed."
                    ),
                    code_template="""# ZERO-SHOT MANDATE: Write the full assumption-checking workflow from scratch.
# Requirements:
#   1. Load the actual data source specified in parameters.
#   2. Compute Shapiro-Wilk statistics and p-values for each group.
#   3. Compute Levene's statistic and p-value for variance equality.
#   4. Select and execute the correct downstream test only after diagnostics are available.
#   5. Return computed diagnostics and test results; do not fabricate outcomes.
# DO NOT use fabricated data generators or hardcoded p-values.
""",
                    expected_output="Test assumption diagnostics"
                ),
                ProtocolStep(
                    name="statistical_execution",
                    description="Execute the assumption-approved statistical test and compute the corresponding effect size.",
                    code_template="""
import numpy as np
from scipy import stats

def execute_ttest(group_a, group_b):
    # Grounded Execution: Actually perform the statistical test
    try:
        a = np.array(group_a)
        b = np.array(group_b)
        
        # Welch's t-test (assumes unequal variance by default, more robust)
        stat, p_val = stats.ttest_ind(a, b, equal_var=False)
        
        # Effect size: Cohen's d for Welch's t-test
        n1, n2 = len(a), len(b)
        s1, s2 = np.var(a, ddof=1), np.var(b, ddof=1)
        s_pooled = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
        cohens_d = (np.mean(a) - np.mean(b)) / s_pooled if s_pooled > 0 else 0.0
        
        # Confidence interval for difference of means
        diff = np.mean(a) - np.mean(b)
        se = np.sqrt(s1/n1 + s2/n2)
        df = (s1/n1 + s2/n2)**2 / ((s1/n1)**2 / (n1-1) + (s2/n2)**2 / (n2-1)) if (s1/n1 + s2/n2) > 0 else 1
        ci = stats.t.interval(0.95, df, loc=diff, scale=se)
        
        return {
            "test_name": "Welch t-test",
            "statistic": float(stat),
            "p_value": float(p_val),
            "cohens_d": float(cohens_d),
            "ci_95": [float(ci[0]), float(ci[1])],
            "significant_05": bool(p_val < 0.05),
            "significant_01": bool(p_val < 0.01),
            "sample_sizes": [n1, n2]
        }
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}

# Example invocation (Agent will provide data)
# result = execute_ttest(data['group1'], data['group2'])
""",
                    expected_output="p-value and effect size"
                )
            ],
            resource_requirements=ResourceRequirements(cpu_cores=4, memory_gb=8),
            expected_duration_hours=1.0
        )

@register_template
class CorrelationAnalysisTemplate(TemplateBase):
    """
    Template for rigorous correlation analysis.
    """

    def __init__(self):
        super().__init__(
            name="correlation_analysis",
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="general",
            title="Robust Correlation Analysis (SVEL-APEX)",
            description="Analyze relationship strength using Pearson, Spearman, or Kendall based on data distribution.",
            suitable_for=["Relationship testing", "Predictive relationships"],
            requirements=["scipy", "pandas", "numpy"],
            complexity_score=0.7,
            rigor_score=1.0
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        statement = str(hypothesis).lower()
        correlation_keywords = ["correlat", "associat", "relationship", "related", "dependency"]
        return any(keyword in statement for keyword in correlation_keywords)

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"Robust Correlation Analysis: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="general",
            description=self.description,
            steps=[
                ProtocolStep(
                    name="distribution_check",
                    description="Load the actual paired data, test normality for both variables, and choose the correlation method from the observed diagnostics.",
                    code_template="""# ZERO-SHOT MANDATE: Implement the normality-gated correlation selection workflow.
# Requirements:
#   1. Load the real paired dataset from the specified source.
#   2. Apply Shapiro-Wilk testing to both variables before choosing a correlation method.
#   3. Select Pearson only when both variables satisfy the normality prerequisite.
#   4. Otherwise select Spearman or Kendall based on the observed data characteristics.
#   5. Return the computed diagnostics and method choice with no fabricated labels.
# DO NOT use generated data or hardcoded normality labels.
""",
                    expected_output="Selected correlation method"
                ),
                ProtocolStep(
                    name="correlation_execution",
                    description="Compute the observed correlation, bootstrap confidence interval, and exact p-value from the real paired data.",
                    code_template="""# ZERO-SHOT MANDATE: Implement the correlation and bootstrap inference workflow.
# Requirements:
#   1. Load the actual paired data from the specified source.
#   2. Compute the correlation statistic chosen from the diagnostic stage.
#   3. Use bootstrap resampling on the observed data to estimate the confidence interval.
#   4. Compute the exact p-value from the observed sample statistics.
#   5. Return the computed coefficient, interval bounds, and p-value only.
# DO NOT use generated data or hardcoded correlation results.
""",
                    expected_output="Correlation metrics and CIs"
                )
            ],
            resource_requirements=ResourceRequirements(cpu_cores=4, memory_gb=8),
            expected_duration_hours=1.0
        )

@register_template
class RegressionAnalysisTemplate(TemplateBase):
    """
    Template for rigorous regression analysis.
    """

    def __init__(self):
        super().__init__(
            name="regression_analysis",
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="general",
            title="Diagnostic Regression Analysis (SVEL-APEX)",
            description="Predict outcome variable using OLS with mandatory diagnostic checks (VIF, Durbin-Watson, Breusch-Pagan).",
            suitable_for=["Prediction tasks", "Causal modeling", "Multivariate analysis"],
            requirements=["statsmodels", "pandas", "numpy", "scipy"],
            complexity_score=0.9,
            rigor_score=1.0
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        statement = str(hypothesis).lower()
        regression_keywords = ["predict", "explain", "effect of", "impact of", "regress", "caus"]
        return any(keyword in statement for keyword in regression_keywords)

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"Diagnostic Regression Analysis: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,

            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="general",
            description=self.description,
            steps=[
                ProtocolStep(
                    name="regression_fitting",
                    description="Fit the OLS model from the actual dataset and compute the required regression diagnostics.",
                    code_template="""# ZERO-SHOT MANDATE: Implement the full regression workflow from raw data.
# Requirements:
#   1. Load the actual data from CSV, database, or API into a DataFrame.
#   2. Define the dependent variable y and the predictor matrix X from the observed data.
#   3. Fit OLS with statsmodels and extract the fitted model summary.
#   4. Compute VIF, Durbin-Watson, Breusch-Pagan, and Shapiro-Wilk residual diagnostics.
#   5. Return the computed model and diagnostics only; do not fabricate summaries.
# DO NOT use generated data or fabricated regression outputs.
""",
                    expected_output="Fitted model summary"
                )
            ],
            resource_requirements=ResourceRequirements(cpu_cores=4, memory_gb=8),
            expected_duration_hours=1.0
        )

def register_all_data_analysis_templates():
    """Register the data analysis templates in the global registry."""
    import sys
    import inspect
    # The decorator handles registration; this is a safety handshake
    pass
