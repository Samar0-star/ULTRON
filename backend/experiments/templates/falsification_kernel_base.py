"""
ULTRON Ph.D.-TIER FALSIFICATION BASE
====================================
Standard base classes for all high-fidelity scientific kernels.
Ensures structural traceability and mathematical rigor across domains.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json
import time
import numpy as np


class Verdict(str, Enum):
    PASS         = "PASS"
    FAIL         = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class FailureCategory(str, Enum):
    PHYSICAL_CONSTRAINT_VIOLATION = "physical_constraint_violation"
    INVARIANT_BREACH               = "invariant_breach"
    SENSITIVITY_EXPLOSION          = "sensitivity_explosion"
    CONVERGENCE_FAILURE            = "convergence_failure"
    NUMERICAL_INSTABILITY          = "numerical_instability"
    YIELD_BELOW_THRESHOLD          = "yield_below_threshold"
    IGNITION_NOT_ACHIEVED          = "ignition_not_achieved"


@dataclass
class FailureRecord:
    category  : str
    message   : str
    check_name: str
    evidence  : Dict[str, Any] = field(default_factory=dict)
    timestamp : float          = field(default_factory=time.time)

    @classmethod
    def make(cls, cat, msg, check_name="unknown", evidence=None):
        return cls(
            category=str(cat),
            message=msg,
            check_name=check_name,
            evidence=evidence or {},
        )


@dataclass
class FalsificationResult:
    kernel_id     : str
    config_fp     : str                 = ""
    verdict       : Verdict             = Verdict.INCONCLUSIVE
    checks        : Dict[str, Any]      = field(default_factory=dict)
    stress_summary: Dict[str, Any]      = field(default_factory=dict)
    confidence    : float               = 0.0
    failures      : List[FailureRecord] = field(default_factory=list)
    execution_time: float               = 0.0
    elapsed_s     : float               = 0.0
    message       : str                 = ""
    _t0           : float               = field(default_factory=time.time, repr=False)

    def add_failure(self, record: FailureRecord):
        self.failures.append(record)
        self.verdict = Verdict.FAIL

    def add_check(self, name: str, data: Dict[str, Any]):
        self.checks[name] = data

    def finalize(self):
        self.elapsed_s = round(time.time() - self._t0, 4)
        self.execution_time = self.elapsed_s
        self.verdict = Verdict.PASS if not self.failures else Verdict.FAIL

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("_t0", None)
        return d


@dataclass
class BaseKernelConfig:
    """Base configuration for scientific simulation kernels."""
    mc_trials         : int   = 200
    perturbation_scale: float = 0.10
    rng_seed          : int   = 42

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return config_fingerprint(self)


@dataclass
class BaseSuccessCriteria:
    """Base success criteria for scientific simulation kernels."""
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FalsificationKernel:
    """Abstract interface for all falsification kernels."""
    def __init__(self, cfg: Any = None, criteria: Any = None):
        self.cfg = cfg
        self.criteria = criteria

    def run(self, config: Any = None) -> FalsificationResult:
        raise NotImplementedError

    def run_nominal(self):
        raise NotImplementedError

    def run_stress(self):
        raise NotImplementedError


class PhysicalViolationError(RuntimeError):
    """Raised when a simulation state violates fundamental physical laws."""
    pass


class InvariantBreachError(RuntimeError):
    """Raised when a conservation law or mathematical invariant is breached."""
    pass


def config_fingerprint(cfg: Any) -> str:
    raw = json.dumps(asdict(cfg) if hasattr(cfg, "__dataclass_fields__") else str(cfg), sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def sensitivity_z_score(nominal: float, samples: List[float]) -> float:
    arr = np.asarray(samples, dtype=float)
    if arr.size == 0:
        return 0.0
    mu, sigma = float(arr.mean()), float(arr.std())
    return abs(float(nominal) - mu) / (sigma + 1e-10)
