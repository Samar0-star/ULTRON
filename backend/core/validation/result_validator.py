"""
Result Validator for Avon-2 Deep Mode
=======================================

Validates experiment and task results for correctness.
Detects failures, anomalies, and quality issues.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Result validation status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of validation"""
    status: ValidationStatus
    is_valid: bool
    confidence: float = 1.0  # 0.0-1.0
    
    # Checks performed
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    checks_warnings: List[str] = field(default_factory=list)
    
    # Details
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    validated_at: datetime = field(default_factory=datetime.now)
    validation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "checks": {
                "passed": self.checks_passed,
                "failed": self.checks_failed,
                "warnings": self.checks_warnings
            },
            "message": self.message,
            "details": self.details,
            "validated_at": self.validated_at.isoformat(),
            "validation_id": self.validation_id
        }


class ResultValidator:
    """
    Validates task and experiment results.
    
    Performs checks:
    - Completeness (all expected outputs present)
    - Type correctness
    - Range/bounds validation
    - Anomaly detection
    - Quality thresholds
    
    Example:
        ```python
        validator = ResultValidator()
        
        result = {
            "accuracy": 0.85,
            "loss": 0.15,
            "predictions": [1, 0, 1, 1]
        }
        
        validation = validator.validate(
            result,
            expected_keys=["accuracy", "loss"],
            thresholds={"accuracy": 0.7}
        )
        
        if validation.is_valid:
            save_result(result)
        ```
    """
    
    def __init__(
        self,
        strict_mode: bool = False,
        detect_anomalies: bool = True,
        session_id: str = "default"
    ):
        """
        Initialize Result Validator with Deterministic Seeding.
        """
        self.strict_mode = strict_mode
        self.detect_anomalies = detect_anomalies
        self.session_id = session_id
        
        # FIXED: Deterministic Global Seed
        import hashlib
        seed_hash = hashlib.sha256(session_id.encode()).hexdigest()
        self.global_seed = int(seed_hash[:8], 16) % (2**32)
        
        # Reduced logging to avoid init-spam
        logger.debug(f"ResultValidator armed for session {session_id} (Seed: {self.global_seed})")
    
    def validate(
        self,
        result: Dict[str, Any],
        expected_keys: Optional[List[str]] = None,
        expected_types: Optional[Dict[str, type]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        bounds: Optional[Dict[str, tuple]] = None
    ) -> ValidationResult:
        """
        Validate a result with Deep Statistical Grounding.
        """
        checks_passed = []
        checks_failed = []
        checks_warnings = []
        
        # Check 1: Result is not None/empty
        if not result:
            return ValidationResult(
                status=ValidationStatus.FAILED,
                is_valid=False,
                checks_failed=["result_empty"],
                message="Result is empty or None"
            )
        checks_passed.append("result_not_empty")

        # Statistical Grounding: Only compute 1-sample t-test if p_value is not already provided
        raw_data = result.get("raw_data")
        if raw_data and isinstance(raw_data, list) and len(raw_data) >= 2:
            import numpy as np
            from scipy import stats
            data_arr = np.asarray(raw_data, dtype=float)
            data_arr = data_arr[np.isfinite(data_arr)]
            if len(data_arr) >= 2:
                if "p_value" not in result or result["p_value"] is None:
                    control_data = result.get("control_data")
                    if control_data and isinstance(control_data, list) and len(control_data) >= 2:
                        ctrl_arr = np.asarray(control_data, dtype=float)
                        ctrl_arr = ctrl_arr[np.isfinite(ctrl_arr)]
                        t_stat, p_val = stats.ttest_ind(data_arr, ctrl_arr, equal_var=False)
                        pooled_sd = np.sqrt(((len(data_arr) - 1) * np.var(data_arr, ddof=1) + (len(ctrl_arr) - 1) * np.var(ctrl_arr, ddof=1)) / max(1, len(data_arr) + len(ctrl_arr) - 2))
                        eff = (np.mean(data_arr) - np.mean(ctrl_arr)) / (pooled_sd + 1e-12)
                    else:
                        null_baseline = float(result.get("baseline", 0.0))
                        t_stat, p_val = stats.ttest_1samp(data_arr, null_baseline)
                        eff = (np.mean(data_arr) - null_baseline) / (np.std(data_arr, ddof=1) + 1e-12)
                    result["p_value"] = float(p_val)
                    result.setdefault("effect_size", float(eff))
                p_check = float(result["p_value"])
                from backend.discovery.constants import ScientificDefaults
                if p_check < ScientificDefaults.ALPHA_SIGNIFICANCE:
                    checks_passed.append(f"statistically_significant:p={p_check:.4f}")
                else:
                    checks_failed.append(f"insignificant_results:p={p_check:.4f}")
        
        # Check 2: Expected keys present
        if expected_keys:
            missing = [k for k in expected_keys if k not in result]
            if missing:
                checks_failed.append(f"missing_keys:{','.join(missing)}")
            else:
                checks_passed.append("all_keys_present")
        
        # Check 3: Type checking
        if expected_types:
            for key, expected_type in expected_types.items():
                if key in result:
                    if not isinstance(result[key], expected_type):
                        checks_failed.append(
                            f"wrong_type:{key}:expected_{expected_type.__name__}"
                        )
                    else:
                        checks_passed.append(f"type_ok:{key}")
        
        # Check 4: Threshold validation
        if thresholds:
            for key, threshold in thresholds.items():
                if key in result and isinstance(result[key], (int, float)):
                    if result[key] < threshold:
                        checks_failed.append(
                            f"below_threshold:{key}:{result[key]}<{threshold}"
                        )
                    else:
                        checks_passed.append(f"threshold_ok:{key}")
        
        # Check 5: Bounds validation
        if bounds:
            for key, (min_val, max_val) in bounds.items():
                if key in result and isinstance(result[key], (int, float)):
                    value = result[key]
                    if value < min_val or value > max_val:
                        checks_failed.append(
                            f"out_of_bounds:{key}:{value}:[{min_val},{max_val}]"
                        )
                    else:
                        checks_passed.append(f"in_bounds:{key}")
        
        # Check 6: Anomaly detection
        if self.detect_anomalies:
            anomalies = self._detect_anomalies(result)
            checks_warnings.extend(anomalies)
        
        # Determine status
        if checks_failed:
            status = ValidationStatus.FAILED
            is_valid = False
        elif checks_warnings and self.strict_mode:
            status = ValidationStatus.WARNING
            is_valid = False
        elif checks_warnings:
            status = ValidationStatus.WARNING
            is_valid = True
        else:
            status = ValidationStatus.PASSED
            is_valid = True
        
        # Calculate confidence
        total_checks = len(checks_passed) + len(checks_failed) + len(checks_warnings)
        confidence = len(checks_passed) / total_checks if total_checks > 0 else 1.0
        
        message = self._generate_message(status, checks_passed, checks_failed, checks_warnings)
        
        return ValidationResult(
            status=status,
            is_valid=is_valid,
            confidence=confidence,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            checks_warnings=checks_warnings,
            message=message
        )
    
    def validate_experiment(
        self,
        result: Dict[str, Any],
        experiment_type: str = "general"
    ) -> ValidationResult:
        """
        Validate an experiment result with type-specific checks.
        
        Args:
            result: Experiment result
            experiment_type: Type of experiment
            
        Returns:
            ValidationResult
        """
        # Type-specific validation
        if experiment_type == "ml_experiment":
            return self.validate(
                result,
                expected_keys=["train_score", "test_score"],
                thresholds={"test_score": 0.0},
                bounds={
                    "train_score": (0.0, 1.0),
                    "test_score": (0.0, 1.0)
                }
            )
        elif experiment_type == "statistical_test":
            return self.validate(
                result,
                expected_keys=["p_value", "test_statistic"],
                bounds={"p_value": (0.0, 1.0)}
            )
        else:
            return self.validate(result)
    
    def _detect_anomalies(self, result: Dict[str, Any]) -> List[str]:
        """Simple anomaly detection"""
        anomalies = []
        
        for key, value in result.items():
            # Check for NaN/Inf
            if isinstance(value, float):
                if value != value:  # NaN check
                    anomalies.append(f"nan_value:{key}")
                elif abs(value) == float('inf'):
                    anomalies.append(f"inf_value:{key}")
            
            # Check for empty lists/dicts
            if isinstance(value, (list, dict)) and len(value) == 0:
                anomalies.append(f"empty_collection:{key}")
            
            # Check for suspiciously perfect values
            if key in ["accuracy", "score", "r2"] and value == 1.0:
                anomalies.append(f"perfect_score_suspicious:{key}")
        
        return anomalies
    
    def _generate_message(
        self,
        status: ValidationStatus,
        passed: List[str],
        failed: List[str],
        warnings: List[str]
    ) -> str:
        """Generate human-readable message"""
        if status == ValidationStatus.PASSED:
            return f"Validation passed ({len(passed)} checks)"
        elif status == ValidationStatus.FAILED:
            return f"Validation failed: {', '.join(failed[:3])}"
        elif status == ValidationStatus.WARNING:
            return f"Validation passed with warnings: {', '.join(warnings[:3])}"
        else:
            return "Validation skipped or error"


# Convenience function

def validate_result(
    result: Dict[str, Any],
    expected_keys: Optional[List[str]] = None,
    strict: bool = False
) -> ValidationResult:
    """
    Validate a result dictionary.
    
    Args:
        result: Result to validate
        expected_keys: Required keys
        strict: If True, fail on warnings
        
    Returns:
        ValidationResult
    """
    validator = ResultValidator(strict_mode=strict)
    return validator.validate(result, expected_keys=expected_keys)
