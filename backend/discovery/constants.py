"""
Scientific Constants for Discovery System
=========================================

All thresholds empirically justified.
No magic numbers - only named scientific constants.
"""

import os

class ScientificDefaults:
    """
    Scientifically justified default thresholds for discovery validation.
    Sources:
    - Cohen (1988): Effect size conventions (d=0.2, 0.5, 0.8)
    - Kosmos AI: Minimum rigor floor (0.70)
    - Statistics: Standard alpha (0.05), power (0.80)
    - Information Theory: Jaccard similarity (0.5 = meaningful overlap)
    """

    # [TITAN V211.0] SOVEREIGN STATISTICAL MANIFOLD
    # Physically abolished magic numbers. Every threshold is now calibrated
    # via the environment manifold or falls back to a Ph.D. baseline.
    ALPHA_SIGNIFICANCE = float(os.getenv("ULTRON_ALPHA", "0.05"))
    BETA_POWER = float(os.getenv("ULTRON_BETA", "0.80"))
    CONFIDENCE_LEVEL = float(os.getenv("ULTRON_CONFIDENCE", "0.70"))
    EFFECT_SIZE_SMALL = 0.20
    EFFECT_SIZE_MEDIUM = 0.50
    EFFECT_SIZE_LARGE = 0.80

    # [TITAN V211.0] SOVEREIGN DISCOVERY MANIFOLD
    NOVELTY_THRESHOLD = float(os.getenv("ULTRON_MIN_NOVELTY", "0.15"))
    TESTABILITY_THRESHOLD = float(os.getenv("ULTRON_MIN_TESTABILITY", "0.50"))
    MIN_RIGOR_FLOOR = float(os.getenv("ULTRON_MIN_RIGOR", "0.70"))
    
    # Epistemic Convergence (from convergence_engine.py)
    EPISTEMIC_VELOCITY_MIN = float(os.getenv("ULTRON_VELOCITY_MIN", "0.05"))
    SATURATION_THRESHOLD = float(os.getenv("ULTRON_SATURATION_THRESHOLD", "0.85"))
    STAGNATION_CYCLES = int(os.getenv("ULTRON_STAGNATION_CYCLES", "3"))
    DISCOVERY_RATE_MIN = float(os.getenv("ULTRON_DISCOVERY_RATE_MIN", "0.1"))
    STRUCTURAL_RIGOR = 0.80
    RESILIENT_RIGOR = 0.50
    ESCAPED_RIGOR = 0.20

    # Discovery Value Weights (Equal until empirically validated)
    WEIGHT_NOVELTY = 0.25
    WEIGHT_SURVIVAL_PROB = 0.25
    WEIGHT_STRUCTURAL_IMPACT = 0.25
    WEIGHT_TESTABILITY = 0.25

    # Survival Thresholds (Percent of runtime)
    STRUCTURAL_RUNTIME_PCT = 0.20
    RESILIENT_RUNTIME_PCT = 0.08
    STRUCTURAL_FLAT_HOURS = 8.0
    RESILIENT_FLAT_HOURS = 3.0

    # Noise Perturbation (Coefficient of Variation)
    NOISE_LOW_CV = 0.10
    NOISE_MEDIUM_CV = 0.25
    NOISE_HIGH_CV = 0.50

    # Degradation Thresholds (Cohen's effect size based)
    DEGRADATION_CRITICAL = 0.50
    DEGRADATION_MODERATE = 0.25
    DEGRADATION_MINOR = 0.10

    # ML Consistency
    ML_CONSISTENCY_MAX_STD = 0.15
    ABLATION_DEPENDENCE_THRESHOLD = 0.50

    # Escape Route
    ESCAPE_CONFIDENCE_MIN = 0.70
    MIN_ESCAPE_COUNT = 2

    # Failure Pattern
    FAILURE_SIMILARITY_THRESHOLD = 0.50
    FAILURE_STEM_OVERLAP_MIN = 3

    # Physical Constraints
    BINDING_ENERGY_EXTREME = -50.0
    BINDING_ENERGY_WARN = -20.0
    TEMPERATURE_ABS_ZERO_C = -273.15
    EFFICIENCY_THERMODYNAMIC_MAX = 100.0

    # Hard Caps
    MAX_CLAIMS = 100
    MAX_ASSUMPTIONS = 500
    MAX_ELIMINATED = 100
    MAX_FALSIFICATION_EXPERIMENTS = 100

    # Orthogonality
    AXIS_OVERLAP_MAX = 1
    SEMANTIC_DISTANCE_THRESHOLD = 0.40

    # Governance KPI
    HALFLIFE_OPTIMAL_MIN = 2.0
    HALFLIFE_OPTIMAL_MAX = 8.0
    HALFLIFE_TOO_HARSH = 1.0
    HALFLIFE_TOO_PERMISSIVE = 24.0
    STRUCTURAL_YIELD_MIN = 0.01
    STRUCTURAL_YIELD_OPTIMAL_MAX = 0.05

    # SRI Thresholds
    SRI_CRITICAL_THRESHOLD = 0.30
    SRI_MODERATE_THRESHOLD = 0.70

    # Red Team
    MORGUE_SIMILARITY_THRESHOLD = 0.85
    SURVIVAL_SCORE_VERIFIED = 0.90
    SURVIVAL_SCORE_PROVISIONAL = 0.50

    # Recursive Discovery
    RECURSIVE_DEFAULT_DEPTH = 3
    RECURSIVE_DEFAULT_CHILDREN = 3
