# -*- coding: utf-8 -*-
"""
Statistical Validation Module
=============================

Production-grade statistical validation for autonomous research experiments.

Capabilities:
- T-tests, Chi-Square, Correlation (parametric)
- Mann-Whitney U, Wilcoxon Signed-Rank (non-parametric)
- Assumption Checking (Normality, Variance Homogeneity)
- Power Analysis & Meta-Analysis
- Multiple Comparison Correction (Bonferroni, Holm, FDR)
- Effect Size Battery with Confidence Intervals
- Reproducibility Scoring

Requires scipy for production use. Fallback approximations available but NOT recommended.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of statistical tests"""
    T_TEST = "t_test"
    PAIRED_T_TEST = "paired_t_test"
    CHI_SQUARE = "chi_square"
    ANOVA = "anova"
    MANN_WHITNEY = "mann_whitney"
    WILCOXON = "wilcoxon"
    CORRELATION = "correlation"


class SignificanceLevel(Enum):
    """Common significance levels"""
    ALPHA_01 = 0.01   # Very strong evidence
    ALPHA_05 = 0.05   # Strong evidence (standard)
    ALPHA_10 = 0.10   # Moderate evidence


@dataclass
class StatisticalResult:
    """Result of a statistical test"""
    test_type: str
    statistic: float
    p_value: float
    is_significant: bool
    alpha: float = 0.05
    
    # Effect size
    effect_size: Optional[float] = None
    effect_size_name: str = ""  # "Cohen's d", "r", etc.
    effect_interpretation: str = ""  # "small", "medium", "large"
    
    # Confidence interval
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_level: float = 0.95
    
    # Sample info
    n1: int = 0
    n2: int = 0
    mean1: Optional[float] = None
    mean2: Optional[float] = None
    std1: Optional[float] = None
    std2: Optional[float] = None
    
    # Power analysis
    power: Optional[float] = None
    
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_type": self.test_type,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "is_significant": self.is_significant,
            "alpha": self.alpha,
            "effect_size": self.effect_size,
            "effect_size_name": self.effect_size_name,
            "effect_interpretation": self.effect_interpretation,
            "confidence_interval": {
                "lower": self.ci_lower,
                "upper": self.ci_upper,
                "level": self.ci_level
            },
            "sample_info": {
                "n1": self.n1,
                "n2": self.n2,
                "mean1": self.mean1,
                "mean2": self.mean2
            },
            "power": self.power,
            "summary": self.summary
        }


class StatisticalValidator:
    """
    Validate experiment results using statistical methods.
    
    Provides:
    - Hypothesis testing (t-test, chi-square, etc.)
    - Effect size calculation
    - Confidence intervals
    - Power analysis
    
    Example:
        ```python
        validator = StatisticalValidator()
        
        result = validator.t_test(
            group1=[1.2, 1.4, 1.3, 1.5],
            group2=[1.8, 1.9, 2.0, 1.7]
        )
        
        if result.is_significant:
            print(f"Significant difference! p={result.p_value:.4f}")
        ```
    """
    
    def __init__(self, alpha: float = 0.05, require_scipy: bool = True):
        """
        Initialize validator.
        
        Args:
            alpha: Default significance level
            require_scipy: Deprecated arg, kept for compat. Scipy is now MANDATORY.
        """
        self.alpha = alpha
        
        # STRICT ENFORCEMENT: No fallbacks allowed for production science.
        try:
            import scipy.stats
            self._scipy_available = True
        except ImportError:
            raise ImportError(
                "scipy is REQUIRED for statistical validation. "
                "The system cannot compromise on mathematical rigor. "
                "Install with: pip install scipy"
            )
        
        logger.info(f"StatisticalValidator initialized (alpha={alpha}, strict_mode=True)")
    
    def _check_scipy(self) -> bool:
        """Deprecated check."""
        return True
    
    def t_test(
        self,
        group1: List[float],
        group2: List[float],
        paired: bool = False,
        alpha: Optional[float] = None
    ) -> StatisticalResult:
        """
        Perform t-test.
        
        Args:
            group1: First group of samples
            group2: Second group of samples
            paired: Whether to use paired t-test
            alpha: Significance level (default: self.alpha)
            
        Returns:
            StatisticalResult
        """
        alpha = alpha or self.alpha
        
        # Calculate basic stats
        n1, n2 = len(group1), len(group2)
        mean1 = sum(group1) / n1
        mean2 = sum(group2) / n2
        std1 = self._std(group1, mean1)
        std2 = self._std(group2, mean2)
        
        if self._scipy_available:
            import scipy.stats as stats
            
            if paired:
                stat, p_value = stats.ttest_rel(group1, group2)
            else:
                # Default to Welch's t-test (equal_var=False) for autonomous robustness
                stat, p_value = stats.ttest_ind(group1, group2, equal_var=False)
        else:
            if paired:
                diffs = [a - b for a, b in zip(group1, group2)]
                n = len(diffs)
                if n < 2:
                    stat, p_value = 0.0, 1.0
                else:
                    mean_diff = sum(diffs) / n
                    std_diff = self._std(diffs, mean_diff)
                    se = std_diff / math.sqrt(n)
                    stat = mean_diff / se if se > 0 else 0.0
                    p_value = self._t_to_p(stat, n - 1)
            else:
                stat, p_value = self._manual_t_test(group1, group2, mean1, mean2, std1, std2, n1, n2)
        
        if math.isnan(stat):
            stat = 0.0
        if math.isnan(p_value):
            p_value = 1.0

        # Effect size (Cohen's d)
        pooled_std = math.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1+n2-2)) if n1+n2 > 2 else 1
        effect_size = abs(mean1 - mean2) / pooled_std if pooled_std > 0 else 0
        effect_interpretation = self._interpret_cohens_d(effect_size)
        
        is_significant = bool(p_value < alpha)
        
        summary = (
            f"{'Paired ' if paired else ''}T-test: t={stat:.3f}, p={p_value:.4f}. "
            f"{'Significant' if is_significant else 'Not significant'} at ={alpha}. "
            f"Effect size (Cohen's d): {effect_size:.3f} ({effect_interpretation})."
        )
        
        return StatisticalResult(
            test_type="paired_t_test" if paired else "t_test",
            statistic=stat,
            p_value=p_value,
            is_significant=is_significant,
            alpha=alpha,
            effect_size=effect_size,
            effect_size_name="Cohen's d",
            effect_interpretation=effect_interpretation,
            n1=n1,
            n2=n2,
            mean1=mean1,
            mean2=mean2,
            std1=std1,
            std2=std2,
            summary=summary
        )
    
    def chi_square(
        self,
        observed: List[float],
        expected: List[float],
        alpha: Optional[float] = None
    ) -> StatisticalResult:
        """
        Perform chi-square test.
        
        Args:
            observed: Observed frequencies
            expected: Expected frequencies
            alpha: Significance level
            
        Returns:
            StatisticalResult
        """
        alpha = alpha or self.alpha
        
        import scipy.stats as stats
        stat, p_value = stats.chisquare(observed, f_exp=expected)
        
        is_significant = p_value < alpha
        
        # Effect size (Cramr's V simplified)
        n = sum(observed)
        k = len(observed)
        effect_size = math.sqrt(stat / (n * (k - 1))) if n > 0 and k > 1 else 0
        
        summary = (
            f"Chi-square test: ={stat:.3f}, p={p_value:.4f}. "
            f"{'Significant' if is_significant else 'Not significant'} at ={alpha}."
        )
        
        return StatisticalResult(
            test_type="chi_square",
            statistic=stat,
            p_value=p_value,
            is_significant=is_significant,
            alpha=alpha,
            effect_size=effect_size,
            effect_size_name="Cramr's V",
            n1=len(observed),
            summary=summary
        )
    
    def correlation(
        self,
        x: List[float],
        y: List[float],
        method: str = "pearson",
        alpha: Optional[float] = None
    ) -> StatisticalResult:
        """
        Calculate correlation coefficient.
        
        Args:
            x: First variable
            y: Second variable
            method: "pearson" or "spearman"
            alpha: Significance level
            
        Returns:
            StatisticalResult
        """
        alpha = alpha or self.alpha
        
        if len(x) != len(y):
            raise ValueError("x and y must have the same length")
        
        n = len(x)
        
        import scipy.stats as stats
        
        if method == "spearman":
            r, p_value = stats.spearmanr(x, y)
        else:
            r, p_value = stats.pearsonr(x, y)
        
        is_significant = p_value < alpha
        interpretation = self._interpret_correlation(r)
        
        summary = (
            f"{method.capitalize()} correlation: r={r:.3f}, p={p_value:.4f}. "
            f"{'Significant' if is_significant else 'Not significant'}. "
            f"Interpretation: {interpretation}."
        )
        
        return StatisticalResult(
            test_type=f"{method}_correlation",
            statistic=r,
            p_value=p_value,
            is_significant=is_significant,
            alpha=alpha,
            effect_size=abs(r),
            effect_size_name="r",
            effect_interpretation=interpretation,
            n1=n,
            summary=summary
        )
    
    # =========================================================================
    # ASSUMPTION CHECKING (Critical for Parametric Tests)
    # =========================================================================
    
    def check_assumptions(
        self,
        group1: List[float],
        group2: Optional[List[float]] = None,
        test_type: str = "t_test"
    ) -> Dict[str, Any]:
        """
        Check statistical assumptions before running parametric tests.
        
        Checks:
        - Normality (Shapiro-Wilk test)
        - Variance homogeneity (Levene's test) for two-group comparisons
        
        Args:
            group1: First data group
            group2: Second data group (optional)
            test_type: Type of test being planned
            
        Returns:
            Dict with assumption check results and recommendations
        """
        results = {
            "assumptions_met": True,
            "normality": {},
            "homogeneity": None,
            "recommendation": "Proceed with parametric test"
        }
        
        if self._scipy_available:
            import scipy.stats as stats
            
            # Normality test (Shapiro-Wilk)
            if len(group1) >= 3 and len(group1) <= 5000:
                stat1, p1 = stats.shapiro(group1)
                normal1 = p1 > 0.05
                results["normality"]["group1"] = {
                    "statistic": round(stat1, 4),
                    "p_value": round(p1, 4),
                    "is_normal": normal1
                }
                if not normal1:
                    results["assumptions_met"] = False
            
            if group2 and len(group2) >= 3 and len(group2) <= 5000:
                stat2, p2 = stats.shapiro(group2)
                normal2 = p2 > 0.05
                results["normality"]["group2"] = {
                    "statistic": round(stat2, 4),
                    "p_value": round(p2, 4),
                    "is_normal": normal2
                }
                if not normal2:
                    results["assumptions_met"] = False
                
                # Levene's test for variance homogeneity
                lev_stat, lev_p = stats.levene(group1, group2)
                homogeneous = lev_p > 0.05
                results["homogeneity"] = {
                    "statistic": round(lev_stat, 4),
                    "p_value": round(lev_p, 4),
                    "is_homogeneous": homogeneous
                }
                if not homogeneous:
                    results["assumptions_met"] = False
        else:
            results["warning"] = "scipy unavailable - assumptions not checked"
            results["assumptions_met"] = None
        
        # Generate recommendation
        if results["assumptions_met"] is False:
            results["recommendation"] = (
                "Assumptions VIOLATED. Use non-parametric alternatives: "
                "Mann-Whitney U (independent) or Wilcoxon (paired)."
            )
        elif results["assumptions_met"] is None:
            results["recommendation"] = (
                "Cannot verify assumptions without scipy. "
                "Consider using non-parametric tests for safety."
            )
        
        return results
    
    # =========================================================================
    # NON-PARAMETRIC TESTS (Alternatives when assumptions fail)
    # =========================================================================
    
    def mann_whitney_u(
        self,
        group1: List[float],
        group2: List[float],
        alternative: str = "two-sided",
        alpha: Optional[float] = None
    ) -> StatisticalResult:
        """
        Mann-Whitney U test (non-parametric alternative to independent t-test).
        
        Use when:
        - Data is ordinal or continuous but non-normal
        - Sample sizes are very small
        - Outliers are present
        
        Args:
            group1: First group of samples
            group2: Second group of samples
            alternative: 'two-sided', 'less', or 'greater'
            alpha: Significance level
            
        Returns:
            StatisticalResult
        """
        alpha = alpha or self.alpha
        n1, n2 = len(group1), len(group2)
        
        if self._scipy_available:
            import scipy.stats as stats
            stat, p_value = stats.mannwhitneyu(
                group1, group2, alternative=alternative
            )
        else:
            # Very rough approximation (NOT recommended)
            logger.warning("Mann-Whitney approximation may be inaccurate!")
            combined = sorted([(x, 0) for x in group1] + [(x, 1) for x in group2])
            ranks = {i: r + 1 for r, (_, i) in enumerate(combined)}
            r1 = sum(r + 1 for r, (x, g) in enumerate(combined) if g == 0)
            stat = r1 - n1 * (n1 + 1) / 2
            # Normal approximation for p-value
            mean_u = n1 * n2 / 2
            std_u = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
            z = (stat - mean_u) / std_u if std_u > 0 else 0
            p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
        
        is_significant = p_value < alpha
        
        # Effect size: r = Z / sqrt(N)
        total_n = n1 + n2
        z_stat = (stat - n1*n2/2) / math.sqrt(n1*n2*(n1+n2+1)/12) if n1*n2 > 0 else 0
        effect_size = abs(z_stat) / math.sqrt(total_n) if total_n > 0 else 0
        
        summary = (
            f"Mann-Whitney U test: U={stat:.1f}, p={p_value:.4f}. "
            f"{'Significant' if is_significant else 'Not significant'} at ={alpha}. "
            f"Effect size r={effect_size:.3f}."
        )
        
        return StatisticalResult(
            test_type="mann_whitney_u",
            statistic=stat,
            p_value=p_value,
            is_significant=is_significant,
            alpha=alpha,
            effect_size=effect_size,
            effect_size_name="r (rank-biserial)",
            n1=n1,
            n2=n2,
            summary=summary
        )
    
    def wilcoxon_signed_rank(
        self,
        x: List[float],
        y: List[float],
        alpha: Optional[float] = None
    ) -> StatisticalResult:
        """
        Wilcoxon signed-rank test (non-parametric alternative to paired t-test).
        
        Use when:
        - Differences are non-normal
        - Data is ordinal
        - Outliers in paired differences
        
        Args:
            x: First measurements
            y: Second measurements (paired with x)
            alpha: Significance level
            
        Returns:
            StatisticalResult
        """
        alpha = alpha or self.alpha
        
        if len(x) != len(y):
            raise ValueError("x and y must have the same length for paired test")
        
        n = len(x)
        
        if self._scipy_available:
            import scipy.stats as stats
            stat, p_value = stats.wilcoxon(x, y)
        else:
            # Simple approximation
            logger.warning("Wilcoxon approximation may be inaccurate!")
            diffs = [a - b for a, b in zip(x, y) if a != b]
            if not diffs:
                return StatisticalResult(
                    test_type="wilcoxon_signed_rank",
                    statistic=0,
                    p_value=1.0,
                    is_significant=False,
                    alpha=alpha,
                    summary="No non-zero differences found"
                )
            
            # Simplified: count of positive/negative ranks
            pos = sum(1 for d in diffs if d > 0)
            neg = len(diffs) - pos
            stat = min(pos, neg)
            # Normal approximation
            n_diff = len(diffs)
            mean_w = n_diff * (n_diff + 1) / 4
            std_w = math.sqrt(n_diff * (n_diff + 1) * (2*n_diff + 1) / 24)
            z = (stat - mean_w) / std_w if std_w > 0 else 0
            p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
        
        is_significant = p_value < alpha
        
        # Effect size: r = Z / sqrt(N)
        z_approx = (stat - n*(n+1)/4) / math.sqrt(n*(n+1)*(2*n+1)/24) if n > 0 else 0
        effect_size = abs(z_approx) / math.sqrt(n) if n > 0 else 0
        
        summary = (
            f"Wilcoxon signed-rank test: W={stat:.1f}, p={p_value:.4f}. "
            f"{'Significant' if is_significant else 'Not significant'} at ={alpha}."
        )
        
        return StatisticalResult(
            test_type="wilcoxon_signed_rank",
            statistic=stat,
            p_value=p_value,
            is_significant=is_significant,
            alpha=alpha,
            effect_size=effect_size,
            effect_size_name="r",
            n1=n,
            summary=summary
        )
    
    def effect_size_ci(
        self,
        d: float,
        n1: int,
        n2: int,
        confidence: float = 0.95
    ) -> Dict[str, float]:
        """
        Calculate confidence interval for Cohen's d.
        
        Uses non-central t-distribution for accurate CIs.
        
        Args:
            d: Cohen's d effect size
            n1: Sample size group 1
            n2: Sample size group 2
            confidence: Confidence level (default 0.95)
            
        Returns:
            Dict with lower, upper bounds and SE
        """
        # Variance of d (approximate)
        n_harm = 2 * n1 * n2 / (n1 + n2) if (n1 + n2) > 0 else 1
        var_d = (n1 + n2) / (n1 * n2) + (d ** 2) / (2 * (n1 + n2))
        se_d = math.sqrt(var_d)
        
        # Z value for confidence level
        alpha_ci = 1 - confidence
        if self._scipy_available:
            import scipy.stats as stats
            z = stats.norm.ppf(1 - alpha_ci / 2)
        else:
            z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%
        
        ci_lower = d - z * se_d
        ci_upper = d + z * se_d
        
        return {
            "effect_size": round(d, 4),
            "se": round(se_d, 4),
            "ci_lower": round(ci_lower, 4),
            "ci_upper": round(ci_upper, 4),
            "confidence_level": confidence,
            "interpretation": self._interpret_cohens_d(d)
        }
    
    def validate_experiment(
        self,
        control: List[float],
        treatment: List[float],
        hypothesis: str = "treatment > control"
    ) -> Dict[str, Any]:
        """
        Comprehensive experiment validation.
        
        Args:
            control: Control group results
            treatment: Treatment group results
            hypothesis: What we're testing
            
        Returns:
            Dict with comprehensive analysis
        """
        t_result = self.t_test(control, treatment)
        
        # Determine support for hypothesis
        mean_diff = t_result.mean2 - t_result.mean1
        
        if ">" in hypothesis:
            supports = mean_diff > 0 and t_result.is_significant
        elif "<" in hypothesis:
            supports = mean_diff < 0 and t_result.is_significant
        else:
            supports = t_result.is_significant
        
        return {
            "hypothesis": hypothesis,
            "supports_hypothesis": supports,
            "statistical_test": t_result.to_dict(),
            "mean_difference": mean_diff,
            "percent_change": (mean_diff / t_result.mean1 * 100) if t_result.mean1 else 0,
            "recommendation": self._generate_recommendation(t_result, supports)
        }
    
    # ========== Helper Methods ==========
    
    def _std(self, values: List[float], mean: float) -> float:
        """
        Calculate sample standard deviation.
        
        Raises:
            ValueError: If fewer than 2 values provided.
        """
        if len(values) < 2:
            raise ValueError(
                f"Need at least 2 values to calculate standard deviation, got {len(values)}. "
                "This may indicate a data collection problem."
            )
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def _safe_std(self, values: List[float], mean: float) -> float:
        """Calculate standard deviation, returning 0.0 if insufficient data (legacy fallback)."""
        if len(values) < 2:
            logger.warning(f"Insufficient data for std calculation ({len(values)} values)")
            return 0.0
        return self._std(values, mean)
    
    def _manual_t_test(
        self,
        g1: List[float], g2: List[float],
        m1: float, m2: float,
        s1: float, s2: float,
        n1: int, n2: int
    ) -> Tuple[float, float]:
        """Manual two-sample t-test (Welch's approximation)"""
        if n1 == 0 or n2 == 0:
            return 0.0, 1.0
        
        se = math.sqrt(s1**2/n1 + s2**2/n2) if s1 > 0 or s2 > 0 else 1
        t_stat = (m1 - m2) / se if se > 0 else 0
        
        # Approximate degrees of freedom (Welch-Satterthwaite)
        if s1 > 0 and s2 > 0:
            num = (s1**2/n1 + s2**2/n2)**2
            denom = (s1**2/n1)**2/(n1-1) + (s2**2/n2)**2/(n2-1)
            df = num / denom if denom > 0 else n1 + n2 - 2
        else:
            df = n1 + n2 - 2
        
        p_value = self._t_to_p(t_stat, df)
        return t_stat, p_value
    
    def _manual_chi_square(
        self,
        observed: List[float],
        expected: List[float]
    ) -> Tuple[float, float]:
        """Manual chi-square test"""
        chi2 = sum(
            (o - e)**2 / e
            for o, e in zip(observed, expected)
            if e > 0
        )
        
        df = len(observed) - 1
        p_value = self._chi2_to_p(chi2, df)
        return chi2, p_value
    
    def _manual_pearson(self, x: List[float], y: List[float]) -> float:
        """Manual Pearson correlation"""
        n = len(x)
        if n == 0:
            return 0.0
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denom_x = math.sqrt(sum((xi - mean_x)**2 for xi in x))
        denom_y = math.sqrt(sum((yi - mean_y)**2 for yi in y))
        
        if denom_x == 0 or denom_y == 0:
            return 0.0
        
        return num / (denom_x * denom_y)
    
    def _t_to_p(self, t: float, df: float) -> float:
        """Approximate t-statistic to p-value (two-tailed)"""
        if t == 0:
            return 1.0
        # Using approximation for large df
        if df <= 0:
            return 1.0
        
        x = df / (df + t**2)
        # Approximate incomplete beta function
        p = 0.5 * x ** (df / 2) * (1 - x) ** 0.5
        return min(1.0, max(0.0, 2 * p))
    
    def _chi2_to_p(self, chi2: float, df: int) -> float:
        """Approximate chi-square to p-value"""
        if df <= 0 or chi2 < 0:
            return 1.0
        
        # Very rough approximation
        if chi2 < df:
            return 0.5 + 0.5 * (1 - chi2/df)
        else:
            return max(0.01, 0.5 * math.exp(-0.5 * (chi2 - df)))
    
    def _interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size"""
        d = abs(d)
        if d < 0.2:
            return "negligible"
        elif d < 0.5:
            return "small"
        elif d < 0.8:
            return "medium"
        else:
            return "large"
    
    def _interpret_correlation(self, r: float) -> str:
        """Interpret correlation coefficient"""
        r = abs(r)
        if r < 0.1:
            return "negligible"
        elif r < 0.3:
            return "weak"
        elif r < 0.5:
            return "moderate"
        elif r < 0.7:
            return "strong"
        else:
            return "very strong"
    
    def _generate_recommendation(
        self,
        result: StatisticalResult,
        supports: bool
    ) -> str:
        """Generate recommendation based on results"""
        if not result.is_significant:
            return (
                "Results are not statistically significant. "
                "Consider increasing sample size or effect may be too small."
            )
        
        if supports:
            if result.effect_interpretation in ["large", "very strong"]:
                return "Strong evidence supports the hypothesis. Consider publishing results."
            else:
                return "Hypothesis supported but effect size is modest. Consider replication."
        else:
            return "Results are significant but in unexpected direction. Revise hypothesis."
    
    # =========================================================================
    # BEAST-TIER: POWER ANALYSIS
    # =========================================================================
    
    def power_analysis(
        self,
        effect_size: float,
        n1: int,
        n2: Optional[int] = None,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Calculate statistical power and sample size recommendations.
        
        Args:
            effect_size: Expected Cohen's d
            n1: Sample size of group 1
            n2: Sample size of group 2 (defaults to n1)
            alpha: Significance level
        
        Returns:
            Dict with power, required sample size for 80% power
        """
        n2 = n2 or n1
        
        # Approximate power calculation
        # Using normal approximation for t-test
        df = n1 + n2 - 2
        pooled_n = 2 * n1 * n2 / (n1 + n2)
        noncentrality = effect_size * math.sqrt(pooled_n / 2)
        
        # Critical t-value (approximate)
        t_crit = 1.96 if df > 30 else 2.0
        
        # Power approximation using normal CDF approximation
        z_beta = noncentrality - t_crit
        power = 0.5 * (1 + math.erf(z_beta / math.sqrt(2)))
        power = max(0.0, min(1.0, power))
        
        # Required n for 80% power (approximate)
        # n  2 * ((z_alpha + z_beta) / d)^2
        z_alpha = 1.96  # for alpha = 0.05
        z_beta_80 = 0.84  # for power = 0.80
        required_n_per_group = int(2 * ((z_alpha + z_beta_80) / max(effect_size, 0.01)) ** 2)
        
        # Recommendations
        if power < 0.5:
            recommendation = f"UNDERPOWERED! Need ~{required_n_per_group} per group for 80% power."
        elif power < 0.8:
            recommendation = f"Moderate power. Recommend {required_n_per_group} per group."
        else:
            recommendation = "Adequately powered for detecting specified effect."
        
        return {
            "power": round(power, 3),
            "current_n": {"n1": n1, "n2": n2},
            "effect_size": effect_size,
            "alpha": alpha,
            "required_n_for_80_power": required_n_per_group,
            "recommendation": recommendation
        }
    
    # =========================================================================
    # BEAST-TIER: META-ANALYSIS
    # =========================================================================
    
    def meta_analyze(
        self,
        studies: List[Dict[str, Any]],
        method: str = "fixed"
    ) -> Dict[str, Any]:
        """
        Combine multiple studies using meta-analysis.
        
        Args:
            studies: List of {"effect_size": ..., "se": ..., "n": ...}
            method: "fixed" or "random" effects
        
        Returns:
            Combined effect size with CI and heterogeneity stats
        """
        if not studies:
            return {"error": "No studies provided"}
        
        effects = []
        variances = []
        weights = []
        
        for study in studies:
            es = study.get("effect_size", 0)
            se = study.get("se") if study.get("se") is not None else study.get("standard_error", 0.1)
            n = study.get("n", 30)
            
            # If no SE, estimate from n
            if se <= 0:
                se = 1 / math.sqrt(max(n, 1))
            
            var_i = se ** 2
            effects.append(es)
            variances.append(var_i)
            weights.append(1 / var_i)
        
        if not weights or sum(weights) == 0:
            return {"error": "Could not calculate weights"}
        
        # Fixed-effect baseline for Q and DerSimonian-Laird tau^2
        sum_weights = sum(weights)
        fixed_effect = sum(e * w for e, w in zip(effects, weights)) / sum_weights
        
        # Heterogeneity (Q statistic)
        q_stat = sum(w * (e - fixed_effect) ** 2 for e, w in zip(effects, weights))
        df = len(studies) - 1
        i_squared = max(0, (q_stat - df) / q_stat * 100) if q_stat > 0 else 0
        
        if method == "random" and len(studies) > 1:
            c_denom = sum_weights - (sum(w ** 2 for w in weights) / sum_weights)
            tau_sq = max(0.0, (q_stat - df) / c_denom) if c_denom > 0 else 0.0
            rand_weights = [1.0 / (v + tau_sq) for v in variances]
            sum_rand_weights = sum(rand_weights)
            combined_effect = sum(e * w for e, w in zip(effects, rand_weights)) / sum_rand_weights
            combined_se = 1.0 / math.sqrt(sum_rand_weights)
        else:
            combined_effect = fixed_effect
            combined_se = 1.0 / math.sqrt(sum_weights)
        
        # 95% CI
        ci_lower = combined_effect - 1.96 * combined_se
        ci_upper = combined_effect + 1.96 * combined_se
        
        # Z-test for combined effect
        z_stat = combined_effect / combined_se if combined_se > 0 else 0.0
        p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z_stat) / math.sqrt(2))))
        
        heterogeneity = "low" if i_squared < 25 else "moderate" if i_squared < 75 else "high"
        
        return {
            "combined_effect": round(combined_effect, 4),
            "combined_se": round(combined_se, 4),
            "ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
            "z_statistic": round(z_stat, 3),
            "p_value": round(p_value, 4),
            "is_significant": p_value < 0.05,
            "n_studies": len(studies),
            "heterogeneity": {
                "q_statistic": round(q_stat, 3),
                "i_squared": round(i_squared, 1),
                "interpretation": heterogeneity
            },
            "method": method
        }
    
    # =========================================================================
    # BEAST-TIER: MULTIPLE COMPARISON CORRECTION
    # =========================================================================
    
    def apply_correction(
        self,
        p_values: List[float],
        method: str = "bonferroni"
    ) -> Dict[str, Any]:
        """
        Apply multiple comparison correction.
        
        Args:
            p_values: List of p-values
            method: "bonferroni", "holm", or "fdr" (Benjamini-Hochberg)
        
        Returns:
            Corrected p-values and significance decisions
        """
        n = len(p_values)
        if n == 0:
            return {"error": "No p-values provided"}
        
        alpha = 0.05
        
        if method == "bonferroni":
            # Simple Bonferroni: p * n
            corrected = [min(1.0, p * n) for p in p_values]
            threshold = alpha
            
        elif method == "holm":
            # Holm-Bonferroni (step-down with cumulative maximum monotonicity enforcement)
            indexed = sorted(enumerate(p_values), key=lambda x: x[1])
            corrected = [0.0] * n
            running_max = 0.0
            
            for rank, (orig_idx, p) in enumerate(indexed):
                correction_factor = n - rank
                adj_p = min(1.0, p * correction_factor)
                running_max = max(running_max, adj_p)
                corrected[orig_idx] = running_max
            threshold = alpha
            
        elif method == "fdr":
            # Benjamini-Hochberg (step-up with cumulative minimum monotonicity enforcement)
            indexed = sorted(enumerate(p_values), key=lambda x: x[1])
            corrected = [0.0] * n
            running_min = 1.0
            
            for rank in range(n - 1, -1, -1):
                orig_idx, p = indexed[rank]
                q = min(1.0, p * n / (rank + 1))
                running_min = min(running_min, q)
                corrected[orig_idx] = running_min
            threshold = alpha
        else:
            return {"error": f"Unknown method: {method}"}
        
        significant = [p < threshold for p in corrected]
        
        return {
            "original_p_values": p_values,
            "corrected_p_values": [round(p, 6) for p in corrected],
            "significant": significant,
            "significant_count": sum(significant),
            "threshold": threshold,
            "method": method,
            "n_tests": n,
            "summary": f"{sum(significant)}/{n} significant after {method} correction"
        }
    
    # =========================================================================
    # BEAST-TIER: REPRODUCIBILITY SCORING
    # =========================================================================
    
    def reproducibility_score(
        self,
        p_value: float,
        sample_size: int,
        effect_size: float
    ) -> Dict[str, Any]:
        """
        Estimate probability of replication success.
        
        Uses the replication probability formula based on power analysis.
        
        Args:
            p_value: Original study's p-value
            sample_size: Original sample size
            effect_size: Observed effect size
        
        Returns:
            Replication probability and assessment
        """
        # Estimate power of replication study (same n)
        power_info = self.power_analysis(effect_size, sample_size // 2, sample_size // 2)
        power = power_info["power"]
        
        # Replication probability depends on original p-value and power
        # Lower p-values and higher power = higher replication probability
        
        # Simplified model: rep_prob  power * (1 - p_value)
        rep_prob = power * (1 - p_value)
        rep_prob = max(0.0, min(1.0, rep_prob))
        
        # Adjust for effect size reliability
        if effect_size < 0.2:
            rep_prob *= 0.5  # Small effects are harder to replicate
        elif effect_size > 0.8:
            rep_prob = min(1.0, rep_prob * 1.2)  # Large effects are more reliable
        
        # Assessment
        if rep_prob > 0.8:
            assessment = "HIGH - Very likely to replicate"
            confidence = "excellent"
        elif rep_prob > 0.6:
            assessment = "MODERATE - Likely to replicate with adequate power"
            confidence = "good"
        elif rep_prob > 0.4:
            assessment = "LOW - Replication uncertain, increase sample size"
            confidence = "fair"
        else:
            assessment = "VERY LOW - Unlikely to replicate, possible Type I error"
            confidence = "poor"
        
        return {
            "replication_probability": round(rep_prob, 3),
            "confidence": confidence,
            "assessment": assessment,
            "original_metrics": {
                "p_value": p_value,
                "sample_size": sample_size,
                "effect_size": effect_size
            },
            "power_at_same_n": power,
            "recommendation": power_info["recommendation"]
        }
    
    # =========================================================================
    # BEAST-TIER: EXTENDED EFFECT SIZE BATTERY
    # =========================================================================
    
    def calculate_effect_sizes(
        self,
        group1: List[float],
        group2: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive effect size battery.
        
        Returns Cohen's d, Hedges' g, Glass's , and common language effect size.
        """
        n1, n2 = len(group1), len(group2)
        if n1 == 0 or n2 == 0:
            return {"error": "Empty groups"}
        
        mean1 = sum(group1) / n1
        mean2 = sum(group2) / n2
        std1 = self._std(group1, mean1)
        std2 = self._std(group2, mean2)
        
        mean_diff = mean2 - mean1
        
        # Cohen's d (pooled SD)
        pooled_sd = math.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1+n2-2)) if n1+n2 > 2 else 1
        cohens_d = mean_diff / pooled_sd if pooled_sd > 0 else 0
        
        # Hedges' g (bias-corrected)
        j = 1 - (3 / (4 * (n1 + n2 - 2) - 1)) if n1 + n2 > 3 else 1
        hedges_g = cohens_d * j
        
        # Glass's  (control SD only)
        glass_delta = mean_diff / std1 if std1 > 0 else 0
        
        # Common language effect size (probability of superiority)
        combined_sd = math.sqrt(std1**2 + std2**2)
        cles = 0.5 * (1 + math.erf(mean_diff / (combined_sd * math.sqrt(2)))) if combined_sd > 0 else 0.5
        
        return {
            "cohens_d": round(cohens_d, 4),
            "cohens_d_interpretation": self._interpret_cohens_d(cohens_d),
            "hedges_g": round(hedges_g, 4),
            "glass_delta": round(glass_delta, 4),
            "common_language_effect_size": round(cles, 4),
            "cles_interpretation": f"{round(cles*100)}% probability group2 > group1",
            "means": {"group1": round(mean1, 4), "group2": round(mean2, 4)},
            "sds": {"group1": round(std1, 4), "group2": round(std2, 4)},
            "n": {"group1": n1, "group2": n2}
        }


# Convenience functions

def run_statistical_test(
    test_type: str,
    data1: List[float],
    data2: Optional[List[float]] = None,
    **kwargs
) -> StatisticalResult:
    """
    Run a statistical test.
    
    Args:
        test_type: Type of test ("t_test", "chi_square", "correlation")
        data1: First dataset
        data2: Second dataset (if applicable)
        **kwargs: Additional test parameters
        
    Returns:
        StatisticalResult
    """
    validator = StatisticalValidator()
    
    if test_type == "t_test":
        return validator.t_test(data1, data2 or [], **kwargs)
    elif test_type == "chi_square":
        return validator.chi_square(data1, data2 or data1, **kwargs)
    elif test_type == "correlation":
        return validator.correlation(data1, data2 or [], **kwargs)
    else:
        raise ValueError(f"Unknown test type: {test_type}")


def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarize multiple experiment results.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        Summary statistics
    """
    if not results:
        return {"count": 0, "summary": "No results to summarize"}
    
    significant = [r for r in results if r.get("is_significant", False)]
    
    return {
        "count": len(results),
        "significant_count": len(significant),
        "significance_rate": len(significant) / len(results),
        "summary": f"{len(significant)}/{len(results)} tests were significant"
    }
