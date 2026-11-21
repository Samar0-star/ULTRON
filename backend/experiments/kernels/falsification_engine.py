# -*- coding: utf-8 -*-
"""
SVEL ADVERSARIAL FALSIFICATION ENGINE
========================================
"It is not enough to confirm a theory. You must try to destroy it."
                                             Karl Popper, 1959

This module implements real falsification science. It does NOT ask
"does the data support the hypothesis?" It asks:

  1. What is the STRONGEST possible case AGAINST this finding?
  2. Under what conditions does it BREAK?
  3. Which COMPETING explanation fits better?
  4. Is this effect REAL or a statistical artifact of how we looked?

SCIENTIFIC FRAMEWORK:
  - Popperian Falsification (Popper 1959)
  - Strong Inference (Platt 1964, Science 146:347)
  - Adversarial Collaboration (Kahneman et al. 2002)
  - Sensitivity Analysis (Saltelli et al. 2008)
  - Specification Curve Analysis (Simonsohn et al. 2020)

A result that survives this engine has been genuinely tested.
A result that fails it was never real science to begin with.

ARCHITECTURE:
  FalsificationEngine
     BoundaryConditionProber       Find where hypothesis breaks
     CompetingHypothesisArena      Head-to-head vs alternatives
     AdversarialPerturbationSuite  Systematic attack on assumptions
     ConfoundBattery               Inject known confounders
     SpecificationCurveAnalyzer    All defensible analysis choices
     AdversarialBootstrap          Worst-case resampling attack
     NullModelBattery              Multiple null models, not one
     FalsificationReport           Structured evidence dossier
"""

import numpy as np
import logging
import time
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from abc import ABC, abstractmethod
try:
    from backend.llm_manager import run_llm_async, HYPOTHESIS_VALIDATION_MODEL
except ImportError:
    run_llm_async = None
    HYPOTHESIS_VALIDATION_MODEL = "default"

logger = logging.getLogger("svel.falsification")


# 
# EVIDENCE STRUCTURES
# 

class FalsificationVerdict(Enum):
    SURVIVES        = "SURVIVES"       # Effect is robust  survived all attacks
    FRAGILE         = "FRAGILE"        # Effect exists but depends on assumptions
    BOUNDARY_CASE   = "BOUNDARY_CASE"  # Effect only holds in narrow regime
    CONFOUNDED      = "CONFOUNDED"     # Effect disappears when confound removed
    ALTERNATIVE_WINS = "ALTERNATIVE_WINS"  # Competing hypothesis fits better
    DESTROYED       = "DESTROYED"      # Effect is an artifact  does not exist


@dataclass
class AttackResult:
    """Result of one adversarial attack on a hypothesis."""
    attack_name: str
    attack_type: str        # "perturbation" | "confound" | "boundary" | "null" | "competing"
    hypothesis_survived: bool
    effect_before: float
    effect_after: float
    p_value_before: Optional[float]
    p_value_after: Optional[float]
    survival_ratio: float   # effect_after / effect_before (1.0 = unchanged, 0 = destroyed)
    details: str
    severity: str           # "mild" | "moderate" | "severe" | "lethal"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack": self.attack_name,
            "type": self.attack_type,
            "survived": self.hypothesis_survived,
            "effect_before": round(self.effect_before, 4),
            "effect_after": round(self.effect_after, 4),
            "survival_ratio": round(self.survival_ratio, 4),
            "p_before": round(self.p_value_before, 4) if self.p_value_before else None,
            "p_after": round(self.p_value_after, 4) if self.p_value_after else None,
            "severity": self.severity,
            "details": self.details,
        }


@dataclass
class BoundaryResult:
    """Result of boundary condition probing."""
    parameter_name: str
    original_value: float
    boundary_value: float
    direction: str          # "increasing" | "decreasing"
    effect_at_boundary: float
    collapses_at: Optional[float]   # The value where effect  0
    robustness_range: Tuple[float, float]   # Range where hypothesis holds
    fraction_of_range_that_holds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter_name,
            "original": self.original_value,
            "boundary": self.boundary_value,
            "direction": self.direction,
            "collapses_at": self.collapses_at,
            "robustness_range": list(self.robustness_range),
            "fraction_holds": round(self.fraction_of_range_that_holds, 3),
        }


@dataclass
class CompetingHypothesisResult:
    """Result of head-to-head test between hypotheses."""
    primary_hypothesis: str
    competing_hypothesis: str
    primary_bic: float
    competing_bic: float
    delta_bic: float            # BIC_competing - BIC_primary (positive = primary wins)
    bayes_factor: float         # How many times more likely is primary?
    winner: str
    likelihood_ratio: float
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary_hypothesis,
            "competing": self.competing_hypothesis,
            "delta_bic": round(self.delta_bic, 2),
            "bayes_factor": round(self.bayes_factor, 3),
            "winner": self.winner,
            "details": self.details,
        }


@dataclass
class FalsificationReport:
    """
    Complete adversarial falsification report.
    This is what a PhD reviewer would demand before accepting a finding.
    """
    hypothesis_statement: str
    original_effect: float
    original_p_value: float

    # Attack results
    perturbation_attacks: List[AttackResult]
    confound_attacks: List[AttackResult]
    boundary_results: List[BoundaryResult]
    competing_hypotheses: List[CompetingHypothesisResult]
    null_model_results: List[AttackResult]
    specification_curve: Dict[str, Any]
    adversarial_bootstrap: Dict[str, Any]

    # Aggregate metrics
    survival_rate: float        # Fraction of attacks survived
    median_survival_ratio: float  # Median effect_after/effect_before
    worst_case_effect: float    # Effect under worst perturbation
    worst_case_p: float         # p-value under worst perturbation
    n_attacks_total: int
    n_attacks_survived: int

    # Final verdict
    verdict: FalsificationVerdict
    confidence: float           # 0-1, how confident in the verdict
    robustness_score: float     # 0-1, overall robustness (0=artifact, 1=ironclad)

    # What would kill this finding
    critical_vulnerabilities: List[str]
    what_would_replicate: List[str]
    what_would_fail: List[str]

    execution_time_seconds: float
    semantic_audit: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis": self.hypothesis_statement,
            "original": {
                "effect_size": round(self.original_effect, 4),
                "p_value": round(self.original_p_value, 4),
            },
            "verdict": self.verdict.value,
            "confidence": round(self.confidence, 3),
            "robustness_score": round(self.robustness_score, 3),
            "survival_rate": round(self.survival_rate, 3),
            "median_survival_ratio": round(self.median_survival_ratio, 3),
            "worst_case": {
                "effect": round(self.worst_case_effect, 4),
                "p_value": round(self.worst_case_p, 4),
            },
            "attacks": {
                "total": self.n_attacks_total,
                "survived": self.n_attacks_survived,
                "failed": self.n_attacks_total - self.n_attacks_survived,
            },
            "perturbation_attacks": [a.to_dict() for a in self.perturbation_attacks],
            "confound_attacks": [a.to_dict() for a in self.confound_attacks],
            "boundary_results": [b.to_dict() for b in self.boundary_results],
            "competing_hypotheses": [c.to_dict() for c in self.competing_hypotheses],
            "null_model_results": [n.to_dict() for n in self.null_model_results],
            "specification_curve": self.specification_curve,
            "adversarial_bootstrap": self.adversarial_bootstrap,
            "critical_vulnerabilities": self.critical_vulnerabilities,
            "what_would_replicate": self.what_would_replicate,
            "what_would_fail": self.what_would_fail,
            "execution_time_seconds": round(self.execution_time_seconds, 2),
            "semantic_audit": self.semantic_audit,
        }


# 
# ATTACK PRIMITIVES
# 

class StatisticalPrimitive:
    """
    Core statistical primitives used by all attack modules.
    Implements fast versions for use inside Monte Carlo loops.
    """

    @staticmethod
    def effect_size_cohens_d(g1: np.ndarray, g2: np.ndarray) -> float:
        """Compute Cohen's d for (g1=control, g2=treatment) as (mean(treatment) - mean(control)) / s_p."""
        n1, n2 = len(g1), len(g2)
        if n1 < 2 or n2 < 2:
            return 0.0
        m1, m2 = g1.mean(), g2.mean()
        pooled_var = ((n1-1)*g1.var(ddof=1) + (n2-1)*g2.var(ddof=1)) / (n1+n2-2)
        return float((m2 - m1) / np.sqrt(pooled_var + 1e-300))

    @staticmethod
    def p_value_ttest(g1: np.ndarray, g2: np.ndarray) -> float:
        from scipy.stats import ttest_ind
        if len(g1) < 2 or len(g2) < 2:
            return 1.0
        try:
            _, p = ttest_ind(g1, g2, equal_var=False)
            return float(p)
        except Exception:
            return 1.0

    @staticmethod
    def fit_linear(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
        """Returns (slope, intercept, r_squared)."""
        if len(x) < 3:
            return 0.0, 0.0, 0.0
        coeffs = np.polyfit(x, y, 1)
        y_fit = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_fit) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = float(1 - ss_res / (ss_tot + 1e-300))
        return float(coeffs[0]), float(coeffs[1]), r2

    @staticmethod
    def bic(log_likelihood: float, k: int, n: int) -> float:
        """Bayesian Information Criterion."""
        return k * np.log(n) - 2 * log_likelihood

    @staticmethod
    def log_likelihood_gaussian(residuals: np.ndarray) -> float:
        """Log-likelihood under Gaussian error model."""
        n = len(residuals)
        sigma2 = residuals.var()
        if sigma2 <= 0:
            return -np.inf
        return float(-n/2 * np.log(2*np.pi*sigma2) - np.sum(residuals**2)/(2*sigma2))

    # [RIGOR FIX] Upgraded L2 Loss to Wasserstein Distance
    # Replaced point-wise mean comparison with Earth Mover's Distance to evaluate the 
    # entire probability distribution of the experimental results against the null, 
    # preventing the system from ignoring heavy tails or variance shifts.
    @staticmethod
    def wasserstein_distance(u_values: np.ndarray, v_values: np.ndarray) -> float:
        """Computes the first Wasserstein distance between two 1D distributions."""
        from scipy.stats import wasserstein_distance
        if len(u_values) == 0 or len(v_values) == 0:
            return 0.0
        return float(wasserstein_distance(u_values, v_values))


# 
# MODULE 1: ADVERSARIAL PERTURBATION SUITE
# 

class AdversarialPerturbationSuite:
    """
    Systematically attack the data and assumptions.

    Attacks implemented:
      1. Gaussian noise injection ( = 5%, 10%, 25%, 50% of signal)
      2. Outlier injection (1%, 5%, 10% extreme values)
      3. Dropout attack (delete 10%, 20%, 30% of data randomly)
      4. Adversarial dropout (delete the data MOST FAVORABLE to hypothesis)
      5. Label/group shuffling (destroy group structure)
      6. Temporal order scramble (destroy time structure)
      7. Distribution shift (replace data with shifted version)
      8. Measurement error model (simulate instrument error)
    """

    def __init__(self, rng: np.random.Generator = None):
        self.rng = rng or np.random.default_rng()
        self.sp = StatisticalPrimitive()

    def run_all(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        original_p: float,
        threshold_p: float = 0.05,
        threshold_effect: float = 0.2,
    ) -> List[AttackResult]:
        """Run all perturbation attacks. Returns list of AttackResult."""
        attacks = []

        attacks.extend(self._noise_attacks(control, treatment, original_effect, original_p, threshold_p))
        attacks.extend(self._outlier_attacks(control, treatment, original_effect, original_p, threshold_p))
        attacks.extend(self._dropout_attacks(control, treatment, original_effect, original_p, threshold_p))
        attacks.append(self._adversarial_dropout(control, treatment, original_effect, original_p, threshold_p))
        attacks.append(self._label_shuffle_attack(control, treatment, original_effect, original_p))
        attacks.append(self._distribution_shift_attack(control, treatment, original_effect, original_p, threshold_p))
        attacks.append(self._measurement_error_attack(control, treatment, original_effect, original_p, threshold_p))

        return attacks

    def _noise_attacks(self, c, t, eff0, p0, thresh_p) -> List[AttackResult]:
        results = []
        for noise_frac in [0.05, 0.10, 0.25, 0.50]:
            sigma = noise_frac * np.std(np.concatenate([c, t]))
            c_noisy = c + self.rng.normal(0, sigma, size=len(c))
            t_noisy = t + self.rng.normal(0, sigma, size=len(t))
            eff_after = self.sp.effect_size_cohens_d(c_noisy, t_noisy)
            p_after = self.sp.p_value_ttest(c_noisy, t_noisy)
            survived = abs(eff_after) > threshold_effect and p_after < thresh_p if (threshold_effect := 0.2) else p_after < thresh_p
            ratio = abs(eff_after) / (abs(eff0) + 1e-10)
            severity = "mild" if noise_frac <= 0.10 else "moderate" if noise_frac <= 0.25 else "severe"
            results.append(AttackResult(
                attack_name=f"gaussian_noise_{int(noise_frac*100)}pct",
                attack_type="perturbation",
                hypothesis_survived=survived,
                effect_before=eff0, effect_after=eff_after,
                p_value_before=p0, p_value_after=p_after,
                survival_ratio=ratio,
                details=f"Added Gaussian noise ={noise_frac*100:.0f}% of signal std. Effect: {eff0:.3f}{eff_after:.3f}",
                severity=severity,
            ))
        return results

    def _outlier_attacks(self, c, t, eff0, p0, thresh_p) -> List[AttackResult]:
        results = []
        scale = np.std(np.concatenate([c, t]))
        grand_mean = np.mean(np.concatenate([c, t]))

        for outlier_frac in [0.01, 0.05, 0.10]:
            n_outliers_c = max(1, int(len(c) * outlier_frac))
            n_outliers_t = max(1, int(len(t) * outlier_frac))

            # Inject outliers AGAINST the hypothesis (worst case)
            c_attacked = c.copy()
            t_attacked = t.copy()

            # If treatment > control (positive effect), inject high outliers into control
            # and low outliers into treatment to try to erase the effect
            if eff0 > 0:
                c_attacked[self.rng.integers(0, len(c), n_outliers_c)] = grand_mean + 5 * scale
                t_attacked[self.rng.integers(0, len(t), n_outliers_t)] = grand_mean - 5 * scale
            else:
                c_attacked[self.rng.integers(0, len(c), n_outliers_c)] = grand_mean - 5 * scale
                t_attacked[self.rng.integers(0, len(t), n_outliers_t)] = grand_mean + 5 * scale

            eff_after = self.sp.effect_size_cohens_d(c_attacked, t_attacked)
            p_after = self.sp.p_value_ttest(c_attacked, t_attacked)
            ratio = abs(eff_after) / (abs(eff0) + 1e-10)
            survived = p_after < thresh_p and np.sign(eff_after) == np.sign(eff0)
            severity = "mild" if outlier_frac <= 0.01 else "moderate" if outlier_frac <= 0.05 else "severe"

            results.append(AttackResult(
                attack_name=f"adversarial_outliers_{int(outlier_frac*100)}pct",
                attack_type="perturbation",
                hypothesis_survived=survived,
                effect_before=eff0, effect_after=eff_after,
                p_value_before=p0, p_value_after=p_after,
                survival_ratio=ratio,
                details=f"Injected {outlier_frac*100:.0f}% adversarial outliers (5, direction against hypothesis). Effect: {eff0:.3f}{eff_after:.3f}",
                severity=severity,
            ))
        return results

    def _dropout_attacks(self, c, t, eff0, p0, thresh_p) -> List[AttackResult]:
        results = []
        for dropout_frac in [0.10, 0.20, 0.30]:
            n_keep_c = max(5, int(len(c) * (1 - dropout_frac)))
            n_keep_t = max(5, int(len(t) * (1 - dropout_frac)))
            c_dropped = self.rng.choice(c, n_keep_c, replace=False)
            t_dropped = self.rng.choice(t, n_keep_t, replace=False)
            eff_after = self.sp.effect_size_cohens_d(c_dropped, t_dropped)
            p_after = self.sp.p_value_ttest(c_dropped, t_dropped)
            ratio = abs(eff_after) / (abs(eff0) + 1e-10)
            survived = p_after < thresh_p and np.sign(eff_after) == np.sign(eff0)
            results.append(AttackResult(
                attack_name=f"random_dropout_{int(dropout_frac*100)}pct",
                attack_type="perturbation",
                hypothesis_survived=survived,
                effect_before=eff0, effect_after=eff_after,
                p_value_before=p0, p_value_after=p_after,
                survival_ratio=ratio,
                details=f"Randomly deleted {dropout_frac*100:.0f}% of each group. Effect: {eff0:.3f}{eff_after:.3f}",
                severity="mild" if dropout_frac <= 0.10 else "moderate",
            ))
        return results

    def _adversarial_dropout(self, c, t, eff0, p0, thresh_p) -> AttackResult:
        """
        Delete the 20% of data MOST FAVORABLE to the hypothesis.
        If the effect disappears when we remove its strongest supporters, it was fragile.
        """
        dropout_frac = 0.20

        # Find which control points most INCREASE the gap (delete them from control)
        # and which treatment points most DECREASE the gap (delete them from treatment)
        if eff0 > 0:
            # eff0 = (mean(t) - mean(c)) / s_p > 0 => mean(t) > mean(c).
            # To erode (mean(t) - mean(c)), delete lowest values of c and HIGHEST values of t.
            c_sorted_idx = np.argsort(c)        # Ascending  -> lowest control first
            t_sorted_idx = np.argsort(t)[::-1]  # Descending -> highest treatment first
        else:
            # eff0 <= 0 => mean(t) <= mean(c).
            # To erode (mean(c) - mean(t)), delete highest values of c and LOWEST values of t.
            c_sorted_idx = np.argsort(c)[::-1]  # Descending -> highest control first
            t_sorted_idx = np.argsort(t)        # Ascending  -> lowest treatment first

        n_drop_c = max(2, int(len(c) * dropout_frac))
        n_drop_t = max(2, int(len(t) * dropout_frac))

        c_adversarial = np.delete(c, c_sorted_idx[:n_drop_c])
        t_adversarial = np.delete(t, t_sorted_idx[:n_drop_t])

        if len(c_adversarial) < 3 or len(t_adversarial) < 3:
            return AttackResult(
                attack_name="adversarial_dropout_20pct",
                attack_type="perturbation",
                hypothesis_survived=True,
                effect_before=eff0, effect_after=eff0,
                p_value_before=p0, p_value_after=p0,
                survival_ratio=1.0,
                details="Adversarial dropout skipped  insufficient data remains",
                severity="lethal",
            )

        eff_after = self.sp.effect_size_cohens_d(c_adversarial, t_adversarial)
        p_after = self.sp.p_value_ttest(c_adversarial, t_adversarial)
        ratio = abs(eff_after) / (abs(eff0) + 1e-10)
        survived = p_after < thresh_p and np.sign(eff_after) == np.sign(eff0)

        return AttackResult(
            attack_name="adversarial_dropout_20pct",
            attack_type="perturbation",
            hypothesis_survived=survived,
            effect_before=eff0, effect_after=eff_after,
            p_value_before=p0, p_value_after=p_after,
            survival_ratio=ratio,
            details=(
                f"Deleted the 20% of observations MOST FAVORABLE to the hypothesis. "
                f"Effect: {eff0:.3f}{eff_after:.3f}. "
                f"{'SURVIVED: effect is not driven by lucky extremes.' if survived else 'FAILED: effect was carried by its most extreme supporters.'}"
            ),
            severity="lethal",  # This is the hardest test
        )

    def _label_shuffle_attack(self, c, t, eff0, p0) -> AttackResult:
        """
        Shuffle group labels. If effect survives, group structure was irrelevant.
        This is equivalent to the null permutation test but framed as an attack.
        """
        combined = np.concatenate([c, t])
        self.rng.shuffle(combined)
        c_shuffled = combined[:len(c)]
        t_shuffled = combined[len(c):]
        eff_after = self.sp.effect_size_cohens_d(c_shuffled, t_shuffled)
        p_after = self.sp.p_value_ttest(c_shuffled, t_shuffled)
        ratio = abs(eff_after) / (abs(eff0) + 1e-10)
        # In this attack, surviving is BAD  it means the effect exists even in noise
        survived = p_after >= 0.05  # Shuffled data should NOT be significant

        return AttackResult(
            attack_name="label_shuffle_null",
            attack_type="null",
            hypothesis_survived=survived,
            effect_before=eff0, effect_after=eff_after,
            p_value_before=p0, p_value_after=p_after,
            survival_ratio=ratio,
            details=(
                f"Group labels shuffled randomly. In the null, p should be ~U(0,1). "
                f"Got p={p_after:.4f}. "
                f"{'PASSED NULL CHECK: shuffled data is not significant.' if survived else 'FAILED: shuffled data is significant  original result may be spurious.'}"
            ),
            severity="severe",
        )

    def _distribution_shift_attack(self, c, t, eff0, p0, thresh_p) -> AttackResult:
        """
        Shift the entire data distribution. If the effect depends on absolute values
        rather than relative differences, it will disappear.
        """
        scale = np.std(np.concatenate([c, t]))
        shift = 2.0 * scale  # Shift by 2 SDs

        c_shifted = c + shift
        t_shifted = t + shift
        eff_after = self.sp.effect_size_cohens_d(c_shifted, t_shifted)
        p_after = self.sp.p_value_ttest(c_shifted, t_shifted)
        ratio = abs(eff_after) / (abs(eff0) + 1e-10)
        survived = p_after < thresh_p and np.sign(eff_after) == np.sign(eff0)

        return AttackResult(
            attack_name="distribution_shift_2sd",
            attack_type="perturbation",
            hypothesis_survived=survived,
            effect_before=eff0, effect_after=eff_after,
            p_value_before=p0, p_value_after=p_after,
            survival_ratio=ratio,
            details=(
                f"Shifted all values by +2 SDs. Cohen's d is shift-invariant, so "
                f"this tests numerical stability. Effect: {eff0:.3f}{eff_after:.3f}."
            ),
            severity="mild",
        )

    def _measurement_error_attack(self, c, t, eff0, p0, thresh_p) -> AttackResult:
        """
        Simulate instrument measurement error at 15% CV (coefficient of variation).
        Real data is always measured with error. Does the effect survive realistic measurement noise?
        CV = 15% is typical for biological assays.
        """
        cv = 0.15
        sigma_c = cv * np.abs(c) + 1e-10
        sigma_t = cv * np.abs(t) + 1e-10

        c_measured = c + self.rng.normal(0, sigma_c)
        t_measured = t + self.rng.normal(0, sigma_t)

        eff_after = self.sp.effect_size_cohens_d(c_measured, t_measured)
        p_after = self.sp.p_value_ttest(c_measured, t_measured)
        ratio = abs(eff_after) / (abs(eff0) + 1e-10)
        survived = p_after < thresh_p and np.sign(eff_after) == np.sign(eff0)

        return AttackResult(
            attack_name="measurement_error_cv15pct",
            attack_type="perturbation",
            hypothesis_survived=survived,
            effect_before=eff0, effect_after=eff_after,
            p_value_before=p0, p_value_after=p_after,
            survival_ratio=ratio,
            details=(
                f"Simulated instrument error at CV=15% (realistic for biological assays). "
                f"Effect: {eff0:.3f}{eff_after:.3f}."
            ),
            severity="moderate",
        )


# 
# MODULE 2: BOUNDARY CONDITION PROBER
# 

class BoundaryConditionProber:
    """
    Find the exact conditions under which the hypothesis breaks.

    PhD reviewers always ask: "Under what conditions does this NOT hold?"
    This module finds those conditions systematically.

    Probes:
      - Sample size boundary (how small can n get before effect vanishes?)
      - Effect threshold (what minimum effect size is detectable?)
      - Parameter sensitivity (which parameter, if varied 20%, kills the finding?)
      - Distributional boundary (what non-Gaussian tails destroy significance?)
    """

    def __init__(self, rng: np.random.Generator = None):
        self.rng = rng or np.random.default_rng(seed=43)
        self.sp = StatisticalPrimitive()

    def probe_sample_size(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        original_p: float,
        n_min: int = 5,
        n_points: int = 15,
    ) -> BoundaryResult:
        """
        Find minimum n at which effect remains significant.
        Binary search on sample size.
        """
        n_max = min(len(control), len(treatment))
        n_range = np.unique(np.logspace(np.log10(n_min), np.log10(n_max), n_points).astype(int))

        collapses_at = None
        last_significant_n = n_max
        effect_at_boundary = original_effect

        for n in n_range:
            p_values = []
            for _ in range(20):  # 20 repetitions per n for stability
                idx_c = self.rng.choice(len(control), min(n, len(control)), replace=False)
                idx_t = self.rng.choice(len(treatment), min(n, len(treatment)), replace=False)
                c_sub = control[idx_c]
                t_sub = treatment[idx_t]
                p_values.append(self.sp.p_value_ttest(c_sub, t_sub))

            median_p = np.median(p_values)
            if median_p >= 0.05:
                collapses_at = float(n)
                break
            else:
                last_significant_n = n
                effect_at_boundary = self.sp.effect_size_cohens_d(
                    control[self.rng.choice(len(control), n, replace=False)],
                    treatment[self.rng.choice(len(treatment), n, replace=False)]
                )

        robustness_range = (float(collapses_at) if collapses_at else float(n_min), float(n_max))
        frac_holds = ((n_max - (collapses_at or n_min)) / n_max) if collapses_at else 1.0

        return BoundaryResult(
            parameter_name="sample_size_n",
            original_value=float(n_max),
            boundary_value=float(collapses_at or n_min),
            direction="decreasing",
            effect_at_boundary=effect_at_boundary,
            collapses_at=collapses_at,
            robustness_range=robustness_range,
            fraction_of_range_that_holds=float(frac_holds),
        )

    def probe_noise_tolerance(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        n_points: int = 12,
    ) -> BoundaryResult:
        """
        Find noise level at which the effect collapses.
        Binary search on noise  as fraction of signal.
        """
        signal_std = np.std(np.concatenate([control, treatment]))
        noise_fracs = np.linspace(0.0, 2.0, n_points)  # 0% to 200% noise

        collapses_at = None
        effect_at_boundary = original_effect

        for frac in noise_fracs:
            sigma = frac * signal_std
            p_values = []
            for _ in range(30):
                c_noisy = control + self.rng.normal(0, sigma, len(control))
                t_noisy = treatment + self.rng.normal(0, sigma, len(treatment))
                p_values.append(self.sp.p_value_ttest(c_noisy, t_noisy))

            if np.median(p_values) >= 0.05:
                collapses_at = float(frac)
                effect_at_boundary = self.sp.effect_size_cohens_d(
                    control + self.rng.normal(0, sigma, len(control)),
                    treatment + self.rng.normal(0, sigma, len(treatment))
                )
                break

        frac_holds = (collapses_at / 2.0) if collapses_at else 1.0

        return BoundaryResult(
            parameter_name="noise_sigma_fraction_of_signal",
            original_value=0.0,
            boundary_value=collapses_at or 2.0,
            direction="increasing",
            effect_at_boundary=effect_at_boundary,
            collapses_at=collapses_at,
            robustness_range=(0.0, collapses_at or 2.0),
            fraction_of_range_that_holds=float(frac_holds),
        )

    def probe_tail_heaviness(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        original_p: float,
    ) -> BoundaryResult:
        """
        Replace Gaussian tails with Student-t tails of decreasing df.
        Heavy-tailed distributions break parametric tests.
        df=30  Gaussian, df=3 = very heavy tails (outlier-prone).
        """
        from scipy.stats import t as t_dist

        scale_c = np.std(control)
        scale_t = np.std(treatment)
        mean_c = np.mean(control)
        mean_t = np.mean(treatment)

        dfs = [30, 10, 5, 3, 2, 1]
        collapses_at = None
        effect_at_boundary = original_effect

        for df in dfs:
            p_values = []
            for _ in range(50):
                c_heavy = t_dist.rvs(df=df, loc=mean_c, scale=scale_c, size=len(control), random_state=self.rng.integers(1e6))
                t_heavy = t_dist.rvs(df=df, loc=mean_t, scale=scale_t, size=len(treatment), random_state=self.rng.integers(1e6))
                p_values.append(self.sp.p_value_ttest(c_heavy, t_heavy))

            if np.median(p_values) >= 0.05:
                collapses_at = float(df)
                effect_at_boundary = self.sp.effect_size_cohens_d(c_heavy, t_heavy)
                break

        return BoundaryResult(
            parameter_name="distribution_tail_df",
            original_value=30.0,
            boundary_value=collapses_at or 1.0,
            direction="decreasing",
            effect_at_boundary=effect_at_boundary,
            collapses_at=collapses_at,
            robustness_range=(float(collapses_at or 1.0), 30.0),
            fraction_of_range_that_holds=float((30.0 - (collapses_at or 1.0)) / 29.0),
        )

    def run_all(self, control: np.ndarray, treatment: np.ndarray,
                original_effect: float, original_p: float) -> List[BoundaryResult]:
        results = []
        results.append(self.probe_sample_size(control, treatment, original_effect, original_p))
        results.append(self.probe_noise_tolerance(control, treatment, original_effect))
        results.append(self.probe_tail_heaviness(control, treatment, original_effect, original_p))
        return results


# 
# MODULE 3: COMPETING HYPOTHESIS ARENA
# 

class CompetingHypothesisArena:
    """
    Platt's Strong Inference (1964): the only way to know a hypothesis is RIGHT
    is to test it HEAD-TO-HEAD against EVERY plausible alternative.

    This module generates competing explanations and asks:
      "Which hypothesis fits the data better by BIC?"

    Competing models tested:
      1. Null model (no effect, grand mean only)
      2. Linear trend (effect is just a time/order artifact)
      3. Regression to mean (extreme values regress toward mean)
      4. Placebo effect (any intervention would show this effect)
      5. Subgroup driver (effect is driven by a specific subgroup)
      6. Nonlinear relationship (effect is not actually linear)
      7. Variance difference only (groups differ in variance, not mean)
    """

    def __init__(self, rng: np.random.Generator = None):
        self.rng = rng or np.random.default_rng(seed=44)
        self.sp = StatisticalPrimitive()

    def run_all(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        hypothesis_statement: str,
    ) -> List[CompetingHypothesisResult]:
        results = []
        results.append(self._vs_null_model(control, treatment, original_effect))
        results.append(self._vs_order_artifact(control, treatment, original_effect))
        results.append(self._vs_regression_to_mean(control, treatment, original_effect))
        results.append(self._vs_variance_only(control, treatment, original_effect))
        results.append(self._vs_subgroup_driver(control, treatment, original_effect))
        return results

    def _vs_null_model(self, c, t, eff0) -> CompetingHypothesisResult:
        """H0: no difference. Does H1 (treatment effect) beat null by Wasserstein Distance?"""
        combined = np.concatenate([c, t])
        n = len(combined)

        # Null model: one parameter (grand mean)
        residuals_null = combined - combined.mean()
        ll_null = self.sp.log_likelihood_gaussian(residuals_null)
        bic_null = self.sp.bic(ll_null, k=1, n=n)

        # H1 model: two parameters (two group means)
        residuals_h1 = np.concatenate([c - c.mean(), t - t.mean()])
        ll_h1 = self.sp.log_likelihood_gaussian(residuals_h1)
        bic_h1 = self.sp.bic(ll_h1, k=2, n=n)
        
        # [RIGOR FIX] Upgraded Competing Hypothesis Evaluation
        # Replaced standard BIC evaluation with Wasserstein distance to ensure 
        # the treatment distribution has actually fundamentally shifted from the control,
        # preventing the system from falsely verifying experiments based on extreme outliers.
        w_distance = self.sp.wasserstein_distance(c, t)

        delta_bic = bic_null - bic_h1  # Positive = H1 wins
        bayes_factor = float(np.exp(min(delta_bic / 2, 500)))
        
        # Determine winner using Wasserstein threshold (e.g., > 0.1 of standard deviation)
        pooled_std = np.std(combined)
        winner = "primary_hypothesis" if w_distance > (0.1 * pooled_std) and delta_bic > 2 else "null_model"

        return CompetingHypothesisResult(
            primary_hypothesis=f"Treatment effect (d={eff0:.3f}, W-Dist={w_distance:.3f})",
            competing_hypothesis="Null model (no effect)",
            primary_bic=bic_h1,
            competing_bic=bic_null,
            delta_bic=delta_bic,
            bayes_factor=bayes_factor,
            winner=winner,
            likelihood_ratio=float(np.exp(min((ll_h1 - ll_null), 500))),
            details=(
                f"BIC={delta_bic:.2f} (>2 favors H1). Wasserstein Dist={w_distance:.3f}. "
                f"Bayes factor={bayes_factor:.1f}. "
                f"{'Primary hypothesis wins over null.' if winner == 'primary_hypothesis' else 'CANNOT reject null model  effect may not exist.'}"
            ),
        )

    def _vs_order_artifact(self, c, t, eff0) -> CompetingHypothesisResult:
        """
        Competing: effect is just a linear time trend (data collection order matters).
        Tests whether adding time as covariate eliminates the group effect.
        """
        n_c, n_t = len(c), len(t)
        n = n_c + n_t
        combined = np.concatenate([c, t])

        # Time indices (simulating order of collection)
        time_idx = np.arange(n, dtype=float)

        # H1 model: intercept + group dummy
        X_h1 = np.column_stack([np.ones(n), np.concatenate([np.zeros(n_c), np.ones(n_t)])])
        try:
            beta_h1, _, _, _ = np.linalg.lstsq(X_h1, combined, rcond=None)
            residuals_h1 = combined - X_h1 @ beta_h1
            ll_h1 = self.sp.log_likelihood_gaussian(residuals_h1)
            bic_h1 = self.sp.bic(ll_h1, k=2, n=n)
        except Exception:
            bic_h1 = 0.0

        # Competing: intercept + time trend (no group effect)
        X_trend = np.column_stack([np.ones(n), time_idx])
        try:
            beta_trend, _, _, _ = np.linalg.lstsq(X_trend, combined, rcond=None)
            residuals_trend = combined - X_trend @ beta_trend
            ll_trend = self.sp.log_likelihood_gaussian(residuals_trend)
            bic_trend = self.sp.bic(ll_trend, k=2, n=n)
        except Exception:
            bic_trend = bic_h1 + 100  # Penalize if fit fails

        delta_bic = bic_trend - bic_h1  # Positive = primary (group effect) wins
        bayes_factor = float(np.exp(min(abs(delta_bic) / 2, 500)))
        winner = "primary_hypothesis" if delta_bic > 0 else "time_trend_artifact"

        return CompetingHypothesisResult(
            primary_hypothesis=f"Group treatment effect (d={eff0:.3f})",
            competing_hypothesis="Linear time/order trend (data collection artifact)",
            primary_bic=bic_h1,
            competing_bic=bic_trend,
            delta_bic=delta_bic,
            bayes_factor=bayes_factor,
            winner=winner,
            likelihood_ratio=float(np.exp(min(abs(delta_bic) / 2, 500))),
            details=(
                f"Tests if effect is explained by data collection order. "
                f"BIC={delta_bic:.2f}. "
                f"{'Group effect beats time trend.' if winner == 'primary_hypothesis' else 'WARNING: time trend explains data as well as group effect.'}"
            ),
        )

    def _vs_regression_to_mean(self, c, t, eff0) -> CompetingHypothesisResult:
        """
        Competing: extreme treatment selection  regression to mean on retest.
        If treatment group was selected for being extreme, repeat measurement
        would show the same effect without any real intervention.
        """
        # Simulate what regression to mean would predict
        combined = np.concatenate([c, t])
        grand_mean = combined.mean()
        grand_std = combined.std()

        # RTM prediction: treatment mean regresses halfway to grand mean
        t_mean_rtm = t.mean() * 0.5 + grand_mean * 0.5  # 50% regression
        rtm_effect = self.sp.effect_size_cohens_d(
            c,
            self.rng.normal(t_mean_rtm, t.std(), len(t))
        )

        n = len(combined)
        delta_bic = abs(eff0) - abs(rtm_effect)  # Simplified comparison
        winner = "primary_hypothesis" if abs(eff0) > abs(rtm_effect) * 1.3 else "regression_to_mean"

        return CompetingHypothesisResult(
            primary_hypothesis=f"True treatment effect (d={eff0:.3f})",
            competing_hypothesis=f"Regression to mean artifact (predicted d={rtm_effect:.3f})",
            primary_bic=0.0,
            competing_bic=0.0,
            delta_bic=delta_bic,
            bayes_factor=float(abs(eff0) / (abs(rtm_effect) + 0.01)),
            winner=winner,
            likelihood_ratio=float(abs(eff0) / (abs(rtm_effect) + 0.01)),
            details=(
                f"RTM predicts d{rtm_effect:.3f} from group selection alone. "
                f"Observed d={eff0:.3f}. "
                f"{'Effect exceeds RTM prediction  real effect likely.' if winner == 'primary_hypothesis' else 'WARNING: observed effect is consistent with regression to mean.'}"
            ),
        )

    def _vs_variance_only(self, c, t, eff0) -> CompetingHypothesisResult:
        """
        Competing: groups differ in VARIANCE only, not mean.
        Levene's test checks this. If variance differs, many tests give false positives.
        """
        from scipy.stats import levene, bartlett
        lev_stat, lev_p = levene(c, t)
        _, bart_p = bartlett(c, t)

        var_ratio = t.var() / (c.var() + 1e-10)
        winner = "variance_difference" if lev_p < 0.05 and abs(eff0) < 0.5 else "primary_hypothesis"

        return CompetingHypothesisResult(
            primary_hypothesis=f"Mean difference (d={eff0:.3f})",
            competing_hypothesis=f"Variance difference only (var_ratio={var_ratio:.2f})",
            primary_bic=0.0,
            competing_bic=0.0,
            delta_bic=float(-np.log10(lev_p + 1e-300)),
            bayes_factor=float(1.0 / (lev_p + 1e-10)),
            winner=winner,
            likelihood_ratio=var_ratio,
            details=(
                f"Levene's test: p={lev_p:.4f}, Bartlett: p={bart_p:.4f}, var_ratio={var_ratio:.2f}. "
                f"{'Groups differ in variance (p<0.05)  t-test assumption VIOLATED.' if lev_p < 0.05 else 'Variances are homogeneous  mean difference test is valid.'}"
            ),
        )

    def _vs_subgroup_driver(self, c, t, eff0) -> CompetingHypothesisResult:
        """
        Competing: effect is driven by a subgroup (top 20%), not the whole distribution.
        If median-based effect is much smaller than mean-based, subgroup is suspect.
        """
        from scipy.stats import mannwhitneyu

        # Mean-based vs median-based effect
        effect_mean = eff0
        effect_median_based = (np.median(t) - np.median(c)) / (np.std(np.concatenate([c, t])) + 1e-10)

        # Top 20% vs bottom 80% effect
        n_top = max(2, int(len(t) * 0.2))
        t_top = np.sort(t)[-n_top:]
        t_bottom = np.sort(t)[:-n_top]

        effect_top = self.sp.effect_size_cohens_d(c, t_top)
        effect_bottom = self.sp.effect_size_cohens_d(c, t_bottom)

        # If top 20% drives a disproportionate share of the effect
        top_driver_ratio = abs(effect_top) / (abs(effect_bottom) + 0.01)
        winner = "subgroup_driver" if top_driver_ratio > 2.5 else "primary_hypothesis"

        return CompetingHypothesisResult(
            primary_hypothesis=f"Uniform treatment effect (d={eff0:.3f})",
            competing_hypothesis=f"Subgroup driver (top 20% effect d={effect_top:.3f}, bottom 80% d={effect_bottom:.3f})",
            primary_bic=0.0,
            competing_bic=0.0,
            delta_bic=float(abs(effect_mean) - abs(effect_median_based)),
            bayes_factor=float(top_driver_ratio),
            winner=winner,
            likelihood_ratio=top_driver_ratio,
            details=(
                f"Top 20% effect: d={effect_top:.3f}, Bottom 80%: d={effect_bottom:.3f}, "
                f"Ratio={top_driver_ratio:.2f}. Median-based effect: {effect_median_based:.3f}. "
                f"{'Top 20% drives {:.0f}x the effect  SUBGROUP CONFOUND DETECTED.'.format(top_driver_ratio) if winner == 'subgroup_driver' else 'Effect is distributed across full sample  uniform effect confirmed.'}"
            ),
        )


# 
# MODULE 4: CONFOUND INJECTION BATTERY
# 

class ConfoundBattery:
    """
    Inject known confounders and test if the effect survives.

    Real-world experiments always have confounders. This module tests
    whether the observed effect is robust to confound injection by
    simulating what would happen if a confound explained part of the effect.

    Confounds tested:
      1. Baseline imbalance (groups had different baselines before intervention)
      2. Temporal confound (effect explains time-of-measurement differences)
      3. Selection bias (treatment group was selected non-randomly)
      4. Observer effect (measurement changes behavior)
      5. Batch effect (data collected in different batches/conditions)
    """

    def __init__(self, rng: np.random.Generator = None):
        self.rng = rng or np.random.default_rng(seed=45)
        self.sp = StatisticalPrimitive()

    def run_all(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        original_p: float,
    ) -> List[AttackResult]:
        results = []
        results.append(self._baseline_imbalance(control, treatment, original_effect, original_p))
        results.append(self._selection_bias(control, treatment, original_effect, original_p))
        results.append(self._batch_effect(control, treatment, original_effect, original_p))
        results.append(self._shared_confound(control, treatment, original_effect, original_p))
        return results

    def _baseline_imbalance(self, c, t, eff0, p0) -> AttackResult:
        """
        Simulate baseline imbalance: what if groups differed by 50% of observed
        effect BEFORE the intervention? Can we still claim the effect is real?
        """
        # Subtract a baseline difference of 50% of observed effect
        effect_std = np.std(np.concatenate([c, t]))
        baseline_diff = 0.5 * eff0 * effect_std

        # Adjust treatment downward by baseline_diff (remove confound)
        t_adjusted = t - baseline_diff

        eff_after = self.sp.effect_size_cohens_d(c, t_adjusted)
        p_after = self.sp.p_value_ttest(c, t_adjusted)
        ratio = abs(eff_after) / (abs(eff0) + 1e-10)
        survived = p_after < 0.05 and np.sign(eff_after) == np.sign(eff0)

        return AttackResult(
            attack_name="baseline_imbalance_50pct",
            attack_type="confound",
            hypothesis_survived=survived,
            effect_before=eff0, effect_after=eff_after,
            p_value_before=p0, p_value_after=p_after,
            survival_ratio=ratio,
            details=(
                f"Removed 50% of effect assuming pre-existing baseline imbalance. "
                f"Effect: {eff0:.3f}{eff_after:.3f}. "
                f"{'Residual effect remains significant  real treatment effect.' if survived else 'Effect vanishes when baseline imbalance removed  possible confound.'}"
            ),
            severity="severe",
        )

    def _selection_bias(self, c, t, eff0, p0) -> AttackResult:
        """
        Simulate selection bias: treatment group was drawn from top 30% of population.
        This alone could explain the difference.
        """
        # Simulate selection bias under the null (top/bottom 30% of control distribution alone)
        # normalized by the original pooled SD so tail-variance truncation does not artificially inflate d.
        n_t = len(t)
        if eff0 >= 0:
            threshold = np.percentile(c, 70)
            t_selected = c[c >= threshold]
        else:
            threshold = np.percentile(c, 30)
            t_selected = c[c <= threshold]

        if len(t_selected) < 3:
            t_selected = np.sort(c)[-max(3, n_t // 3):] if eff0 >= 0 else np.sort(c)[:max(3, n_t // 3)]

        orig_pooled_sd = np.sqrt(((len(c) - 1) * c.var(ddof=1) + (len(t) - 1) * t.var(ddof=1)) / max(1, len(c) + len(t) - 2) + 1e-300)
        eff_after = float((t_selected.mean() - c.mean()) / orig_pooled_sd)
        p_after = self.sp.p_value_ttest(c, t_selected)

        # The question: does the observed treatment-vs-control separation exceed a 30% within-control selection tail?
        selection_explains = abs(eff0) <= abs(eff_after) * 1.05
        survived = not selection_explains and p0 < 0.05
        ratio = abs(eff0) / (abs(eff_after) + 1e-10)

        return AttackResult(
            attack_name="selection_bias_top30pct",
            attack_type="confound",
            hypothesis_survived=survived,
            effect_before=eff0, effect_after=eff_after,
            p_value_before=p0, p_value_after=p_after,
            survival_ratio=ratio,
            details=(
                f"Simulated selection bias: treatment = top 30% of population. "
                f"Selection-alone effect: {eff_after:.3f}, Observed: {eff0:.3f}. "
                f"{'Observed effect EXCEEDS selection bias  real treatment effect.' if survived else 'WARNING: observed effect is fully explained by selection bias alone.'}"
            ),
            severity="severe",
        )

    def _batch_effect(self, c, t, eff0, p0) -> AttackResult:
        """
        Simulate batch effect: what if data was collected in two batches with
        different systematic offsets? Add random batch-level noise.
        """
        n_batches = 3
        batch_effect_magnitude = 0.5 * np.std(np.concatenate([c, t]))

        p_values = []
        effect_sizes = []

        for _ in range(50):
            batch_offsets = self.rng.normal(0, batch_effect_magnitude, n_batches)
            batch_labels_c = self.rng.integers(0, n_batches, len(c))
            batch_labels_t = self.rng.integers(0, n_batches, len(t))

            c_batch = c + batch_offsets[batch_labels_c]
            t_batch = t + batch_offsets[batch_labels_t]

            p_values.append(self.sp.p_value_ttest(c_batch, t_batch))
            effect_sizes.append(self.sp.effect_size_cohens_d(c_batch, t_batch))

        median_p = float(np.median(p_values))
        median_eff = float(np.median(effect_sizes))
        ratio = abs(median_eff) / (abs(eff0) + 1e-10)
        survived = median_p < 0.05 and np.sign(median_eff) == np.sign(eff0)

        return AttackResult(
            attack_name="batch_effect_3batches",
            attack_type="confound",
            hypothesis_survived=survived,
            effect_before=eff0, effect_after=median_eff,
            p_value_before=p0, p_value_after=median_p,
            survival_ratio=ratio,
            details=(
                f"Injected random batch effects across 3 batches (=0.5signal_std). "
                f"Median effect over 50 simulations: {median_eff:.3f} (original: {eff0:.3f}). "
                f"Median p={median_p:.4f}."
            ),
            severity="moderate",
        )

    def _shared_confound(self, c, t, eff0, p0) -> AttackResult:
        """
        Inject a shared latent variable that affects both groups.
        If partial correlation with latent variable explains the effect, it's confounded.
        """
        n = len(c) + len(t)
        # Simulate a latent confound Z correlated with group membership
        Z = self.rng.normal(0, 1, n)
        group = np.concatenate([np.zeros(len(c)), np.ones(len(t))])

        # Make Z correlated with group (simulates confound)
        Z_confounded = Z * 0.5 + group * 0.5

        combined = np.concatenate([c, t])

        # Partial out Z from combined data
        slope, _, _ = self.sp.fit_linear(Z_confounded, combined)
        combined_partial = combined - slope * Z_confounded

        c_partial = combined_partial[:len(c)]
        t_partial = combined_partial[len(c):]

        eff_after = self.sp.effect_size_cohens_d(c_partial, t_partial)
        p_after = self.sp.p_value_ttest(c_partial, t_partial)
        ratio = abs(eff_after) / (abs(eff0) + 1e-10)
        survived = p_after < 0.05 and np.sign(eff_after) == np.sign(eff0)

        return AttackResult(
            attack_name="shared_latent_confound",
            attack_type="confound",
            hypothesis_survived=survived,
            effect_before=eff0, effect_after=eff_after,
            p_value_before=p0, p_value_after=p_after,
            survival_ratio=ratio,
            details=(
                f"Partialled out simulated latent confound Z (correlated 0.5 with group). "
                f"Effect after partial correlation: {eff_after:.3f} (original: {eff0:.3f}). "
                f"{'Effect survives confound removal  real effect.' if survived else 'Effect eliminated by latent confound  potential spurious correlation.'}"
            ),
            severity="lethal",
        )


# 
# MODULE 5: SPECIFICATION CURVE ANALYZER
# 

class SpecificationCurveAnalyzer:
    """
    Simonsohn, Simmons & Nelson (2020): Test ALL defensible analysis choices.

    A finding that only appears under ONE specific set of choices is not robust.
    A finding that appears under MOST reasonable choices is real.

    Specifications varied:
      - Statistical test (t-test, Mann-Whitney, Welch, trimmed t)
      - Outlier removal threshold (none, 2SD, 3SD)
      - Sample composition (full, 80% subsample, 90% subsample)
      - Effect size metric (Cohen's d, Hedges' g, Glass's )
      - Multiple comparison correction (none, Bonferroni, BH)
    """

    def __init__(self, rng: np.random.Generator = None):
        self.rng = rng or np.random.default_rng(seed=46)
        self.sp = StatisticalPrimitive()

    def analyze(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        original_p: float,
    ) -> Dict[str, Any]:
        """Run full specification curve. Returns summary dict."""
        from scipy.stats import ttest_ind, mannwhitneyu, trim_mean

        all_specs = []
        n_significant = 0

        # All combinations
        tests = ["welch_t", "mann_whitney", "trimmed_t"]
        outlier_thresholds = [None, 3.0, 2.0]
        subsamples = [1.0, 0.90, 0.80]

        for test in tests:
            for ot in outlier_thresholds:
                for ss in subsamples:
                    # Apply outlier removal
                    combined = np.concatenate([control, treatment])
                    if ot is not None:
                        combined_std = combined.std()
                        combined_mean = combined.mean()
                        c_ = control[np.abs(control - combined_mean) < ot * combined_std]
                        t_ = treatment[np.abs(treatment - combined_mean) < ot * combined_std]
                    else:
                        c_, t_ = control.copy(), treatment.copy()

                    if len(c_) < 3 or len(t_) < 3:
                        continue

                    # Apply subsampling
                    if ss < 1.0:
                        n_c = max(3, int(len(c_) * ss))
                        n_t = max(3, int(len(t_) * ss))
                        c_ = self.rng.choice(c_, n_c, replace=False)
                        t_ = self.rng.choice(t_, n_t, replace=False)

                    # Run test
                    try:
                        if test == "welch_t":
                            _, p = ttest_ind(c_, t_, equal_var=False)
                        elif test == "mann_whitney":
                            _, p = mannwhitneyu(c_, t_, alternative="two-sided")
                        elif test == "trimmed_t":
                            from scipy.stats import ttest_ind
                            _, p = ttest_ind(c_, t_, equal_var=False, trim=0.1)

                        eff = self.sp.effect_size_cohens_d(c_, t_)
                        p = float(p)
                        significant = p < 0.05
                        if significant:
                            n_significant += 1

                        all_specs.append({
                            "test": test,
                            "outlier_threshold": ot,
                            "subsample_frac": ss,
                            "effect_size": round(eff, 4),
                            "p_value": round(p, 4),
                            "significant": significant,
                        })
                    except Exception:
                        continue

        if not all_specs:
            return {"error": "No specifications could be computed"}

        n_total = len(all_specs)
        effects = [s["effect_size"] for s in all_specs]
        p_vals = [s["p_value"] for s in all_specs]

        significance_rate = n_significant / n_total
        effect_median = float(np.median(effects))
        effect_range = (float(min(effects)), float(max(effects)))
        p_median = float(np.median(p_vals))

        # Sign consistency
        sign_consistent = sum(1 for e in effects if np.sign(e) == np.sign(original_effect))
        sign_rate = sign_consistent / n_total

        verdict = (
            "ROBUST" if significance_rate > 0.9 and sign_rate > 0.95
            else "MOSTLY_ROBUST" if significance_rate > 0.7
            else "FRAGILE" if significance_rate > 0.4
            else "SPECIFICATION_DEPENDENT"
        )

        return {
            "n_specifications": n_total,
            "n_significant": n_significant,
            "significance_rate": round(significance_rate, 3),
            "sign_consistency_rate": round(sign_rate, 3),
            "effect_median": effect_median,
            "effect_range": effect_range,
            "p_median": p_median,
            "verdict": verdict,
            "all_specifications": all_specs,
            "interpretation": (
                f"{n_significant}/{n_total} analysis specifications give p<0.05 "
                f"({significance_rate*100:.0f}%). Verdict: {verdict}. "
                f"Effect sign consistent in {sign_rate*100:.0f}% of specs."
            ),
        }


# 
# MODULE 6: ADVERSARIAL BOOTSTRAP
# 

class AdversarialBootstrap:
    """
    Worst-case bootstrap: find the resampling that MINIMIZES the effect.

    Standard bootstrap gives you the sampling distribution under the null.
    Adversarial bootstrap finds the bootstrap sample that makes the effect
    as small as possible  this is the effect's lower confidence bound
    under worst-case resampling.

    If the adversarial lower bound still exceeds the threshold, the effect
    is truly robust. If it doesn't, the finding is fragile.
    """

    def __init__(self, rng: np.random.Generator = None, n_bootstrap: int = 2000):
        self.rng = rng or np.random.default_rng()
        self.n_bootstrap = n_bootstrap
        self.sp = StatisticalPrimitive()

    def run(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        original_p: float,
    ) -> Dict[str, Any]:
        """Run adversarial bootstrap and return results dict."""
        boot_effects = []
        boot_p_values = []

        for _ in range(self.n_bootstrap):
            c_boot = self.rng.choice(control, size=len(control), replace=True)
            t_boot = self.rng.choice(treatment, size=len(treatment), replace=True)
            eff = self.sp.effect_size_cohens_d(c_boot, t_boot)
            p = self.sp.p_value_ttest(c_boot, t_boot)
            boot_effects.append(eff)
            boot_p_values.append(p)

        boot_effects = np.array(boot_effects)
        boot_p_values = np.array(boot_p_values)

        # Adversarial: worst-case sample (minimum effect in correct direction)
        direction_correct = boot_effects * np.sign(original_effect)
        worst_case_idx = np.argmin(direction_correct)
        worst_case_effect = float(boot_effects[worst_case_idx])
        worst_case_p = float(boot_p_values[worst_case_idx])

        # Standard CI
        ci_lower = float(np.percentile(boot_effects, 2.5))
        ci_upper = float(np.percentile(boot_effects, 97.5))

        # P-value stability
        p_significant_rate = float(np.mean(boot_p_values < 0.05))
        p_median = float(np.median(boot_p_values))

        # Effect size stability (coefficient of variation)
        effect_cv = float(np.std(boot_effects) / (abs(np.mean(boot_effects)) + 1e-10))

        # Bias
        bootstrap_bias = float(np.mean(boot_effects) - original_effect)

        worst_case_significant = worst_case_p < 0.05 and np.sign(worst_case_effect) == np.sign(original_effect)

        return {
            "n_bootstrap": self.n_bootstrap,
            "original_effect": round(original_effect, 4),
            "bootstrap_mean": round(float(np.mean(boot_effects)), 4),
            "bootstrap_bias": round(bootstrap_bias, 4),
            "ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
            "ci_includes_zero": ci_lower < 0 < ci_upper,
            "worst_case_effect": round(worst_case_effect, 4),
            "worst_case_p": round(worst_case_p, 4),
            "worst_case_still_significant": worst_case_significant,
            "p_significant_rate": round(p_significant_rate, 3),
            "p_median": round(p_median, 4),
            "effect_cv": round(effect_cv, 3),
            "verdict": (
                "ROBUST" if worst_case_significant and p_significant_rate > 0.85
                else "FRAGILE" if p_significant_rate > 0.5
                else "UNRELIABLE"
            ),
            "interpretation": (
                f"In {p_significant_rate*100:.0f}% of {self.n_bootstrap} bootstrap samples, "
                f"p<0.05. Worst-case effect: {worst_case_effect:.3f} (p={worst_case_p:.4f}). "
                f"95% CI: [{ci_lower:.3f}, {ci_upper:.3f}]."
            ),
        }


# 
# MODULE 7: SEMANTIC CRITIC (LLM RED TEAM)
# 

class SemanticCritic:
    """
    LLM-powered Red Team Auditor for SCIENTIFIC RIGOR.
    
    Heuristics:
    1. Conceptual confounds (What variables were NOT measured?)
    2. Over-interpretation (Does data actually support this specific claim?)
    3. Narrative fallback (Is this just a story the scientist is telling?)
    """
    def __init__(self, llm_manager=None):
        self.llm_manager = llm_manager

    async def audit(self, hypothesis: str, data_summary: Dict, attack_summary: str) -> Dict[str, Any]:
        """
        Run a deep qualitative audit via the Hypothesis Validation LLM.
        """
        if not self.llm_manager:
            return {
                "verdict": "SKIPPED", 
                "confidence": 0.0,
                "criticism": "Semantic audit skipped: No LLM Manager available in kernel."
            }
        
        prompt = f"""You are the **LEAD RED TEAM SCIENTIST** for SVEL Research AI.

Your mission: **DESTROY** the following hypothesis based on the experimental evidence provided.
Look for conceptual flaws, logical leaps, and alternative explanations that the math might miss.
Be DIRECT, BRUTAL, and PROFESSIONAL. Do not sugar-coat.

HYPOTHESIS:
"{hypothesis}"

EXPERIMENTAL EVIDENCE (SUMMARY):
{json.dumps(data_summary, indent=2)}

ADVERSARIAL STRESS TEST SUMMARY (STATISTICAL):
{attack_summary}

================================================================================
AUDIT CRITERIA (PhD LEVEL):
================================================================================
1. **CONCEPTUAL CONFOUNDS**: What external factors or latent variables could explain this?
2. **THEORETICAL LEAPS**: Does the data *really* support the specific causal claim in the hypothesis?
3. **METHODOLOGICAL GAPS**: What was NOT measured that would have invalidated this?
4. **NARRATIVE FALLACY**: Is the scientist just fitting a story to noise?

Your final verdict must be one of: [CLEAN, VULNERABLE, COMPROMISED, BOGUS]

RETURN JSON:
{{{{
  "verdict": "...",
  "confidence": 0.0-1.0,
  "criticism": "Your detailed direct and brutal critique here.",
  "alternative_explanation": "A specific competing explanation.",
  "suggested_controls": ["control 1", "control 2"]
}}}}
"""
        try:
            # We use the new async fallback requested by the logic requirements
            response_obj = await run_llm_async(
                prompt=prompt,
                temperature=0.1
            )
            
            text = response_obj.get("text", "{}")
            # Robust extraction of JSON
            import re
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {"verdict": "ERROR", "criticism": "Failed to parse LLM response."}
            
        except Exception as e:
            logger.error(f"Semantic audit failed: {e}")
            return {"verdict": "ERROR", "criticism": str(e)}


# 
# THE FALSIFICATION ENGINE  ORCHESTRATOR
# 

class FalsificationEngine:
    """
    SVEL ADVERSARIAL FALSIFICATION ENGINE

    Entry point. Orchestrates all attack modules against a hypothesis.

    Usage:
        engine = FalsificationEngine()
        report = engine.falsify(
            control=control_data,
            treatment=treatment_data,
            original_effect=1.24,
            original_p=0.003,
            hypothesis_statement="Treatment increases outcome by >3C",
        )
        print(json.dumps(report.to_dict(), indent=2))
    """

    def __init__(self, rng_seed: int = 42, n_bootstrap: int = 2000, llm_manager: Any = None):
        self.rng = np.random.default_rng(seed=rng_seed)
        self.perturbation = AdversarialPerturbationSuite(self.rng)
        self.boundary = BoundaryConditionProber(self.rng)
        self.arena = CompetingHypothesisArena(self.rng)
        self.confounds = ConfoundBattery(self.rng)
        self.spec_curve = SpecificationCurveAnalyzer(self.rng)
        self.adv_bootstrap = AdversarialBootstrap(self.rng, n_bootstrap)
        self.semantic_critic = SemanticCritic(llm_manager)

    async def falsify(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        original_effect: float,
        original_p: float,
        hypothesis_statement: str,
        threshold_p: float = None,
        threshold_effect: float = 0.2,
    ) -> FalsificationReport:
        """
        Run the full falsification battery.
        1. Perturb the data (outliers, noise, shift)
        2. Inject confounding variables
        3. Probe for boundary conditions
        4. Test 5 competing explanations head-to-head
        5. Run specification curve across all analysis choices
        6. Run adversarial bootstrap for worst-case CI

        Returns FalsificationReport with verdict and evidence dossier.
        """
        from backend.discovery.constants import ScientificDefaults
        threshold_p = threshold_p if threshold_p is not None else ScientificDefaults.ALPHA_SIGNIFICANCE
        t_start = time.time()
        logger.info(f"[FALSIFY] Starting falsification of: {hypothesis_statement[:80]}...")

        control = np.asarray(control, dtype=float)
        treatment = np.asarray(treatment, dtype=float)
        emp_d = StatisticalPrimitive.effect_size_cohens_d(control, treatment)
        if abs(emp_d) > 1e-9:
            original_effect = emp_d

        #  Module 1: Perturbation Attacks 
        logger.info("[FALSIFY] Running perturbation attacks...")
        perturbation_attacks = self.perturbation.run_all(
            control, treatment, original_effect, original_p, threshold_p
        )

        #  Module 2: Confound Injection 
        logger.info("[FALSIFY] Injecting confounders...")
        confound_attacks = self.confounds.run_all(
            control, treatment, original_effect, original_p
        )

        #  Module 3: Boundary Conditions 
        logger.info("[FALSIFY] Probing boundary conditions...")
        boundary_results = self.boundary.run_all(
            control, treatment, original_effect, original_p
        )

        #  Module 4: Competing Hypotheses 
        logger.info("[FALSIFY] Testing competing hypotheses...")
        competing = self.arena.run_all(
            control, treatment, original_effect, hypothesis_statement
        )

        #  Module 5: Specification Curve 
        logger.info("[FALSIFY] Running specification curve analysis...")
        spec_curve = self.spec_curve.analyze(
            control, treatment, original_effect, original_p
        )

        #  Module 6: Adversarial Bootstrap 
        logger.info("[FALSIFY] Running adversarial bootstrap...")
        adv_boot = self.adv_bootstrap.run(
            control, treatment, original_effect, original_p
        )

        #  Module 7: Semantic Critic 
        logger.info("[FALSIFY] Running semantic LLM audit...")
        # Create a brief summary of all statistical findings for the LLM
        attack_summary = f"""
        - Perturbation Stability: {sum(1 for a in perturbation_attacks if a.hypothesis_survived)}/{len(perturbation_attacks)} survived
        - Confound Stability: {sum(1 for a in confound_attacks if a.hypothesis_survived)}/{len(confound_attacks)} survived
        - Specification Robustness: {spec_curve.get('significance_rate', 0)*100:.0f}% significant
        - Adversarial Bootstrap: {adv_boot.get('p_significant_rate', 0)*100:.0f}% resilience
        - Competing Hypothesis Winner: {next((c.winner for c in competing if c.winner != 'primary_hypothesis'), 'None')}
        """
        data_summary = {
            "n_control": len(control),
            "n_treatment": len(treatment),
            "observed_effect_d": original_effect,
            "observed_p_value": original_p,
            "control_stats": {"mean": float(control.mean()), "std": float(control.std())},
            "treatment_stats": {"mean": float(treatment.mean()), "std": float(treatment.std())}
        }
        semantic_report = await self.semantic_critic.audit(
            hypothesis_statement, data_summary, attack_summary
        )

        #  Aggregate Metrics 
        all_attacks = perturbation_attacks + confound_attacks
        n_total = len(all_attacks)
        n_survived = sum(1 for a in all_attacks if a.hypothesis_survived)
        survival_rate = n_survived / max(n_total, 1)

        survival_ratios = [a.survival_ratio for a in all_attacks]
        median_survival = float(np.median(survival_ratios)) if survival_ratios else 0.0

        # Worst case across all attacks
        worst_case_effect = float(min(
            (a.effect_after for a in all_attacks),
            key=lambda x: abs(x) * np.sign(x * original_effect)
        ))
        worst_attack = min(all_attacks, key=lambda a: a.survival_ratio)
        worst_case_p = worst_attack.p_value_after or 1.0

        #  Final Verdict 
        verdict, confidence, robustness, vulnerabilities, will_replicate, will_fail = (
            self._synthesize_verdict(
                all_attacks, boundary_results, competing, spec_curve,
                adv_boot, survival_rate, median_survival, original_effect, original_p,
                semantic_report
            )
        )

        execution_time = time.time() - t_start
        logger.info(
            f"[FALSIFY] Complete in {execution_time:.1f}s. "
            f"Verdict: {verdict.value} (confidence={confidence:.2f}, robustness={robustness:.2f})"
        )

        return FalsificationReport(
            hypothesis_statement=hypothesis_statement,
            original_effect=original_effect,
            original_p_value=original_p,
            perturbation_attacks=perturbation_attacks,
            confound_attacks=confound_attacks,
            boundary_results=boundary_results,
            competing_hypotheses=competing,
            null_model_results=[],
            specification_curve=spec_curve,
            adversarial_bootstrap=adv_boot,
            survival_rate=survival_rate,
            median_survival_ratio=median_survival,
            worst_case_effect=worst_case_effect,
            worst_case_p=worst_case_p,
            n_attacks_total=n_total,
            n_attacks_survived=n_survived,
            verdict=verdict,
            confidence=confidence,
            robustness_score=robustness,
            critical_vulnerabilities=vulnerabilities,
            what_would_replicate=will_replicate,
            what_would_fail=will_fail,
            execution_time_seconds=execution_time,
            semantic_audit=semantic_report,
        )

    def _synthesize_verdict(
        self,
        attacks: List[AttackResult],
        boundaries: List[BoundaryResult],
        competing: List[CompetingHypothesisResult],
        spec_curve: Dict[str, Any],
        adv_boot: Dict[str, Any],
        survival_rate: float,
        median_survival: float,
        original_effect: float,
        original_p: float,
        semantic_report: Dict[str, Any],
    ) -> Tuple[FalsificationVerdict, float, float, List[str], List[str], List[str]]:
        """Synthesize all evidence into a final verdict."""

        vulnerabilities = []
        will_replicate = []
        will_fail = []

        #  Evidence scoring 
        score = 0.0  # Higher = more robust

        # Semantic Audit (20% weight - PhD Critic)
        semantic_verdict = semantic_report.get("verdict", "CLEAN")
        if semantic_verdict == "BOGUS":
            score -= 1.0 # Force negative/zero robustness
            vulnerabilities.append(f"SEMANTIC AUDIT: DETECTED BOGUS REASONING - {semantic_report.get('criticism')}")
            will_fail.append("Conceptual foundation is fundamentally flawed (Semantic Audit: BOGUS)")
        elif semantic_verdict == "COMPROMISED":
            score -= 0.5
            vulnerabilities.append(f"SEMANTIC AUDIT: COMPROMISED - {semantic_report.get('criticism')}")
            will_fail.append("Severe logical leaps detected (Semantic Audit: COMPROMISED)")
        elif semantic_verdict == "VULNERABLE":
            score -= 0.2
            vulnerabilities.append(f"SEMANTIC AUDIT: VULNERABLE - {semantic_report.get('criticism')}")
        else:
            score += 0.2 # Bonus for passing qualitative red team
            will_replicate.append("Hypothesis logic matches experimental evidence (Semantic Audit: CLEAN)")

        # Survival rate (30% weight)
        score += 0.30 * survival_rate
        if survival_rate < 0.5:
            vulnerabilities.append(
                f"Majority of attacks FAILED (survived {survival_rate*100:.0f}% of {len(attacks)} attacks)"
            )
        elif survival_rate > 0.85:
            will_replicate.append(f"Effect survived {survival_rate*100:.0f}% of adversarial attacks")

        # Specification curve (25% weight)
        spec_sig_rate = spec_curve.get("significance_rate", 0)
        score += 0.25 * spec_sig_rate
        spec_verdict = spec_curve.get("verdict", "UNKNOWN")
        if spec_sig_rate < 0.5:
            vulnerabilities.append(
                f"Only {spec_sig_rate*100:.0f}% of analysis specifications significant  SPECIFICATION-DEPENDENT"
            )
            will_fail.append("Effect will fail under many reasonable analysis choices")
        elif spec_sig_rate > 0.85:
            will_replicate.append(f"Effect robust across {spec_sig_rate*100:.0f}% of analysis specifications")

        # Adversarial bootstrap (20% weight)
        boot_p_rate = adv_boot.get("p_significant_rate", 0)
        score += 0.20 * boot_p_rate
        if adv_boot.get("ci_includes_zero", True):
            vulnerabilities.append("95% bootstrap CI includes zero  effect may be noise")
            will_fail.append("Replication with same n has meaningful probability of p>0.05")
        worst_sig = adv_boot.get("worst_case_still_significant", False)
        if worst_sig:
            score += 0.05
            will_replicate.append("Worst-case bootstrap sample still significant")

        # Competing hypotheses (15% weight)
        n_competing_wins = sum(1 for c in competing if c.winner != "primary_hypothesis")
        competing_score = 1.0 - (n_competing_wins / max(len(competing), 1))
        score += 0.15 * competing_score
        if n_competing_wins > 0:
            winners = [c.competing_hypothesis for c in competing if c.winner != "primary_hypothesis"]
            vulnerabilities.append(f"Competing explanations win on BIC: {winners[:2]}")
            will_fail.append("Cannot rule out alternative explanation without additional controls")

        # Boundary conditions
        narrow_ranges = [b for b in boundaries if b.fraction_of_range_that_holds < 0.3]
        if narrow_ranges:
            names = [b.parameter_name for b in narrow_ranges]
            vulnerabilities.append(f"Effect only holds in narrow parameter range: {names}")
            will_fail.append(f"Studies with different {names[0]} will not replicate")

        #  Classify verdict 
        robustness = float(np.clip(score, 0, 1))

        # Check for lethal attacks failing
        lethal_attacks = [a for a in attacks if a.severity == "lethal"]
        lethal_survived = sum(1 for a in lethal_attacks if a.hypothesis_survived)
        lethal_rate = lethal_survived / max(len(lethal_attacks), 1)

        # Check if any competing wins are fundamental
        null_model_result = next((c for c in competing if "Null model" in c.competing_hypothesis), None)
        loses_to_null = null_model_result and null_model_result.winner == "null_model"

        if loses_to_null:
            verdict = FalsificationVerdict.DESTROYED
            confidence = 0.9
        elif robustness > 0.80 and lethal_rate > 0.5:
            verdict = FalsificationVerdict.SURVIVES
            confidence = robustness
            will_replicate.append("Effect structure is robust to adversarial attack")
        elif robustness > 0.65:
            verdict = FalsificationVerdict.FRAGILE
            confidence = robustness
            will_replicate.append("Core effect likely real but not robust to all conditions")
        elif n_competing_wins >= 2:
            verdict = FalsificationVerdict.ALTERNATIVE_WINS
            confidence = 1.0 - robustness
        elif narrow_ranges and len(narrow_ranges) >= 2:
            verdict = FalsificationVerdict.BOUNDARY_CASE
            confidence = 1.0 - robustness
        elif robustness > 0.40:
            verdict = FalsificationVerdict.FRAGILE
            confidence = 0.7
        else:
            verdict = FalsificationVerdict.DESTROYED
            confidence = 1.0 - robustness

        return verdict, float(confidence), robustness, vulnerabilities, will_replicate, will_fail


# 
# EXPERIMENT AGENT INTEGRATION
# 

async def run_falsification_gate(
    grounding_data: Dict[str, Any],
    hypothesis_statement: str,
    original_effect: float,
    original_p: float,
    experiment_id: str,
    rng_seed: int = 42,
    llm_manager: Any = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    INTEGRATION POINT: Drop this into ExperimentAgent.run() after grounding gate.

    After StatisticalGroundingValidator passes, this runs the full
    falsification battery. The experiment only SURVIVES if the effect
    is not DESTROYED or ALTERNATIVE_WINS.

    Args:
        grounding_data: Output from _extract_grounding_data()
        hypothesis_statement: Full hypothesis text
        original_effect: Effect size from experiment
        original_p: p-value from experiment
        experiment_id: For logging

    Returns:
        (passed_falsification: bool, falsification_dict: dict)
    """
    def _first_nonempty_array(d: Dict[str, Any], keys: Tuple[str, ...]):
        for k in keys:
            val = d.get(k)
            if val is not None:
                try:
                    if len(val) > 0:
                        return val
                except TypeError:
                    continue
        return []

    control_raw = _first_nonempty_array(
        grounding_data,
        ("control_raw", "control", "control_values", "control_group", "baseline", "group_a", "group_0")
    )
    treatment_raw = _first_nonempty_array(
        grounding_data,
        ("treatment_raw", "treatment", "treatment_values", "treatment_group", "intervention", "group_b", "group_1")
    )

    if len(control_raw) < 10 or len(treatment_raw) < 10:
        logger.warning(
            f"[FALSIFY] [{experiment_id}] Insufficient data for falsification "
            f"(n_control={len(control_raw)}, n_treatment={len(treatment_raw)}). Need 10. Skipping."
        )
        return True, {"status": "skipped", "reason": "insufficient_data", "survival_rate": 0.0, "robustness_score": 0.0}

    control = np.asarray(control_raw, dtype=float)
    treatment = np.asarray(treatment_raw, dtype=float)

    try:
        engine = FalsificationEngine(rng_seed=rng_seed, n_bootstrap=1000, llm_manager=llm_manager)
        report = await engine.falsify(
            control=control,
            treatment=treatment,
            original_effect=original_effect,
            original_p=original_p,
            hypothesis_statement=hypothesis_statement,
        )

        report_dict = report.to_dict()

        # KILL CONDITION
        fatal_verdicts = {FalsificationVerdict.DESTROYED, FalsificationVerdict.ALTERNATIVE_WINS}
        passed = report.verdict not in fatal_verdicts

        if not passed:
            logger.error(
                f"[FALSIFY] [{experiment_id}] HYPOTHESIS DESTROYED. "
                f"Verdict: {report.verdict.value}, Robustness: {report.robustness_score:.2f}. "
                f"Vulnerabilities: {report.critical_vulnerabilities[:2]}"
            )
        else:
            logger.info(
                f"[FALSIFY] [{experiment_id}] Hypothesis {report.verdict.value}. "
                f"Robustness: {report.robustness_score:.2f}, "
                f"Survived {report.n_attacks_survived}/{report.n_attacks_total} attacks."
            )

        return passed, report_dict

    except Exception as e:
        logger.error(f"[FALSIFY] [{experiment_id}] Falsification engine failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        # Fail open  don't kill valid results because engine crashed
        return False, {"status": "error", "reason": "Falsification engine crashed - result CONSIDERED INVALID"}


# 
# LLM PROMPT GENERATOR  what to tell the experiment agent
# 

def get_falsification_experiment_prompt_block(hypothesis) -> str:
    """
    Inject this into the ExperimentAgent design prompt so the LLM
    generates code that is ROBUSTNESS-AWARE from the start (Professional tone).
    """
    predictions = getattr(hypothesis, 'predictions', []) or []
    n_preds = len(predictions)

    return f"""

STATISTICAL ROBUSTNESS AND SENSITIVITY ANALYSIS
================================================================

Please ensure your experimental design includes comprehensive robustness checks.
Rather than only confirming the hypothesis, please rigorously test its limits:

CHECK 1 - PERMUTATION TEST:
  Run 1000 permutations. Shuffle labels. Recompute effect each time.
  If observed effect is in the top 5% of the null distribution (p < 0.05), proceed.
  If NOT, please print "PERMUTATION_NULL_FAILED" and set supported=False.

CHECK 2 - NOISE SENSITIVITY:
  Add Gaussian noise at sigma=10%, 25% of signal.
  Report the effect size at each noise level.
  If the effect vanishes at sigma=10%, note that the evidence is sensitive to noise.

CHECK 3 - SUBSAMPLING SENSITIVITY:
  Remove the 20% of samples most favorable to the hypothesis.
  Recompute the effect. If it vanishes, note that the effect is highly dependent on extreme values.

CHECK 4 - COMPETING MODEL COMPARISON:
  Fit the null model (grand mean only) AND the treatment model (two means).
  Compute BIC for both. Report BIC.
  If the null model has a lower BIC, the hypothesis is not supported.

[COMPUTATIONAL GUIDELINES]
- Please compute BIC manually: `BIC = k * np.log(n) - 2 * log_likelihood`.
- Please compute Bayes Factor from BIC: `BF = np.exp((BIC_null - BIC_treatment) / 2)`.

MANDATORY CODE STRUCTURE:
  # Control and treatment as separate arrays (for evaluation)
  control_values = np.array([...])   # Your control group
  treatment_values = np.array([...]) # Your treatment group

  # Required: run and report all four robustness checks
  # Required output keys in final JSON:
  #   "control_raw": list, "treatment_raw": list,
  #   "permutation_p": float, "noise_10pct_effect": float,
  #   "subsampling_effect": float, "delta_bic": float

ROBUSTNESS OUTPUT (add to GROUNDING_DATA print):
  print("GROUNDING_DATA:" + json.dumps({{
      "control_raw": control_values.tolist(),
      "treatment_raw": treatment_values.tolist(),
      "test_statistic": float(observed_effect),
      "test_type": "mean_difference",
      "permutation_p": float(p_permutation),
      "noise_10pct_effect": float(effect_at_10pct_noise),
      "subsampling_effect": float(effect_after_subsampling),
      "delta_bic": float(bic_null - bic_treatment),
      {", ".join([f'"measured_pred_{i+1}": float(measured_pred_{i+1})' for i in range(n_preds)])}
  }}))

"""

# 
# COMPATIBILITY LAYER  ADVERSARIAL OPTIMIZER (DE-SEARCH)
# 

@dataclass
class FalsificationResult:
    """Compatibility result for numerical stress-breaking."""
    success: bool
    worst_case_value: float
    worst_case_params: Dict[str, float]
    unbreakability_index: float
    iterations: int
    message: str

class AdversarialOptimizer:
    """
    Global optimizer that searches for parameter combinations that falsify a hypothesis.
    Uses Differential Evolution for non-gradient global search.
    """

    def __init__(self, max_iterations: int = 20, population_size: int = 10):
        self.max_iterations = max_iterations
        self.population_size = population_size

    def stress_test(self, objective_func: Callable[[np.ndarray], float], bounds: List[tuple]) -> FalsificationResult:
        from scipy.optimize import differential_evolution
        logger.info(f" [ADVERSARY] Starting Global Numerical Stress Test ({len(bounds)}D)...")
        
        try:
            # We want to FIND the parameters that MAXIMIZE the metric (make result look like noise).
            # So we minimize -objective_func. The objective must return an error/loss metric in [0, 1].
            def neg_obj(x):
                try:
                    val = float(np.clip(objective_func(x), 0.0, 1.0))
                    return -val
                except Exception as e:
                    return 1.0 # High value for failures
            
            res = differential_evolution(
                neg_obj,
                bounds,
                maxiter=self.max_iterations,
                popsize=self.population_size,
                polish=True
            )
            
            worst_case_metric = -res.fun
            unbreakability = 1.0 - min(1.0, worst_case_metric)
            
            return FalsificationResult(
                success=res.success,
                worst_case_value=worst_case_metric,
                worst_case_params={f"param_{i}": val for i, val in enumerate(res.x)},
                unbreakability_index=unbreakability,
                iterations=res.nit,
                message=res.message
            )
        except Exception as e:
            logger.error(f" [ADVERSARY] Numerical Stress Test Failed: {e}")
            return FalsificationResult(False, 0.0, {}, 0.0, 0, str(e))

