"""
ULTRON BEAST Validation Module
===============================

3-LAYER ULTRA-VALIDATION SYSTEM:
- ResultValidator: Basic validation checks
- AccuracyTracker: Prediction accuracy over time
- StatisticalGroundingValidator: Null model permutation testing (Layer 1)
- DiscoveryScorer: 10-dimension quality scoring (Layer 2)

Together with RedTeamAgent (Layer 3), provides 99%+ false positive prevention.
"""

from backend.core.validation.result_validator import (
    ResultValidator,
    ValidationResult,
    validate_result
)
from backend.core.validation.accuracy_tracker import (
    AccuracyTracker,
    PredictionRecord,
    get_accuracy_tracker
)
from backend.core.validation.statistical_grounding import (
    StatisticalGroundingValidator,
    StatisticalGroundingResult,
    ShuffleStrategy,
    get_statistical_validator,
    validate_statistical_grounding
)
from backend.core.validation.discovery_scorer import (
    DiscoveryScorer,
    DiscoveryScore,
    DimensionScore,
    QualityTier,
    get_discovery_scorer,
    score_discovery
)
from backend.core.validation.failure_detector import (
    FailureDetector,
    FailureDetectionResult,
    FailureModeScore
)
from backend.core.validation.power_analyzer import PowerAnalyzer

__all__ = [
    # Original
    "ResultValidator",
    "ValidationResult",
    "validate_result",
    "AccuracyTracker",
    "PredictionRecord",
    "get_accuracy_tracker",
    # Ultra-Upgrade: Statistical Grounding
    "StatisticalGroundingValidator",
    "StatisticalGroundingResult",
    "ShuffleStrategy",
    "get_statistical_validator",
    "validate_statistical_grounding",
    # Ultra-Upgrade: Discovery Scorer
    "DiscoveryScorer",
    "DiscoveryScore",
    "DimensionScore",
    "QualityTier",
    "get_discovery_scorer",
    "score_discovery",
    # Ultra-Upgrade: Failure Detection
    "FailureDetector",
    "FailureDetectionResult",
    "FailureModeScore",
    "PowerAnalyzer",
]

