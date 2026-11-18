# -*- coding: utf-8 -*-
"""
Reproducibility Manager - ULTRON Ultra-Upgrade
===============================================

Handles environment snapshots, seed management, and deterministic re-runs.
Ensures that a finding can be independently verified by replaying the 
exact conditions.

Ported and enhanced from Ultron Safety Pillar.
"""

import os
import sys
import json
import logging
import platform
import subprocess
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentSnapshot:
    """Snapshot of the execution environment."""
    os: str
    python_version: str
    packages: Dict[str, str]
    env_vars: Dict[str, str]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReproducibilityManager:
    """
    Manages seeds and environment state for research reproducibility.
    """

    def __init__(self, storage_dir: str = "storage/reproducibility"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._current_seed = None

    def set_seed(self, seed: Optional[int] = None) -> int:
        """
        Set a global seed for all common library random number generators.
        """
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
        
        self._current_seed = seed
        random.seed(seed)
        
        if np:
            np.random.seed(seed)
            
        # For torch/tensorflow, we'd add them here if present
        try:
            import torch
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
        except ImportError:
            pass

        logger.info(f" Seed set to: {seed}")
        return seed

    def capture_environment(self, sensitive_vars: List[str] = None) -> EnvironmentSnapshot:
        """
        Capture the current environment state.
        """
        sensitive_vars = sensitive_vars or ["API_KEY", "PASSWORD", "SECRET", "TOKEN"]
        
        # [RIGOR] FLAW FIX: No more subprocess calls during boot.
        # Spawning pip freeze during swarm initialization causes deadlocks.
        packages = {}
        try:
            from importlib import metadata
            for dist in metadata.distributions():
                packages[dist.metadata['Name']] = dist.version
        except Exception as e:
            logger.warning(f"Metadata capture failed: {e}. Skipping package version tracking for stability.")

        # Filter env vars
        env_vars = {}
        for k, v in os.environ.items():
            if not any(s in k.upper() for s in sensitive_vars):
                env_vars[k] = v

        return EnvironmentSnapshot(
            os=f"{platform.system()} {platform.release()}",
            python_version=sys.version,
            packages=packages,
            env_vars=env_vars
        )

    def create_bundle(self, finding_id: str, snapshot: EnvironmentSnapshot, seed: int) -> str:
        """
        Create a reproducibility bundle file.
        """
        bundle = {
            "finding_id": finding_id,
            "seed": seed,
            "environment": snapshot.to_dict()
        }
        
        file_path = os.path.join(self.storage_dir, f"repro_bundle_{finding_id}.json")
        with open(file_path, "w") as f:
            json.dump(bundle, f, indent=2)
            
        return file_path

    def verify_consistency(self, original_result: Any, new_result: Any, rtol: float = 1e-5, atol: float = 1e-8) -> bool:
        """
        Recursively verify numerical and structural consistency within floating-point tolerances.
        """
        if type(original_result) != type(new_result):
            if not (isinstance(original_result, (int, float)) and isinstance(new_result, (int, float))):
                return False
        if isinstance(original_result, dict) and isinstance(new_result, dict):
            if set(original_result.keys()) != set(new_result.keys()):
                return False
            return all(self.verify_consistency(original_result[k], new_result[k], rtol, atol) for k in original_result)
        if isinstance(original_result, (list, tuple)) and isinstance(new_result, (list, tuple)):
            if len(original_result) != len(new_result):
                return False
            return all(self.verify_consistency(a, b, rtol, atol) for a, b in zip(original_result, new_result))
        if np is not None and isinstance(original_result, np.ndarray) and isinstance(new_result, np.ndarray):
            if original_result.shape != new_result.shape:
                return False
            try:
                is_num = np.issubdtype(original_result.dtype, np.number) and np.issubdtype(new_result.dtype, np.number)
            except TypeError:
                is_num = False
            if is_num:
                return bool(np.allclose(original_result, new_result, rtol=rtol, atol=atol, equal_nan=True))
            return bool(np.array_equal(original_result, new_result))
        if isinstance(original_result, (int, float)) and isinstance(new_result, (int, float)):
            if np is not None:
                return bool(np.isclose(float(original_result), float(new_result), rtol=rtol, atol=atol, equal_nan=True))
            return abs(float(original_result) - float(new_result)) <= (atol + rtol * abs(float(new_result)))
        return bool(original_result == new_result)

