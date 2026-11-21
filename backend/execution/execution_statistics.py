# backend/execution/execution_statistics.py
"""
SVEL Execution Statistics (V168.0)
====================================
Tracks gradient flow, loss trajectories, and physical proof-of-work metrics.
Provides Ph.D. level forensic telemetry for model surgery and training pulses.
"""

import logging
import json
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("svel.execution_statistics")

@dataclass
class ExecutionPulse:
    """Metadata for a single experiment execution."""
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    initial_params_hash: Optional[str] = None
    final_params_hash: Optional[str] = None
    gradient_norm_avg: float = 0.0
    convergence_reached: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)

class ExecutionStatistics:
    """The central manifold for experimental telemetry."""
    
    def __init__(self, max_history_size: int = 1000):
        self._history: Dict[str, ExecutionPulse] = {}
        self._max_history_size = max_history_size
        self._lock = threading.RLock()
        self._global_stats = {
            "total_gradient_updates": 0,
            "mean_discovery_rigor": 0.0,
            "fraud_attempts_blocked": 0
        }

    def start_pulse(self, task_id: str, initial_hash: str):
        """Register the start of a physical experiment."""
        with self._lock:
            # Enforce history limit to prevent OOM
            if len(self._history) >= self._max_history_size:
                # Remove oldest entry
                oldest_key = next(iter(self._history))
                del self._history[oldest_key]
                
            self._history[task_id] = ExecutionPulse(
                task_id=task_id,
                start_time=time.time(),
                initial_params_hash=initial_hash
            )
        logger.info(f" [STATS] Pulse started for task {task_id}.")

    def complete_pulse(self, task_id: str, final_hash: str, metrics: Dict[str, Any]):
        """Record the final state of an experiment."""
        with self._lock:
            if task_id not in self._history:
                return
            
            pulse = self._history[task_id]
            pulse.end_time = time.time()
            pulse.final_params_hash = final_hash
            pulse.metrics = metrics
            
            # Verify physical transformation
            if final_hash == pulse.initial_params_hash:
                self._global_stats["fraud_attempts_blocked"] += 1
                pulse.convergence_reached = False
                logger.warning(f" [STATS] Fraud detected in task {task_id}: Tensor manifold remained static.")
            else:
                pulse.convergence_reached = True
                self._global_stats["total_gradient_updates"] += 1
                
        logger.info(f" [STATS] Pulse complete for task {task_id}. Converged: {pulse.convergence_reached}")

    def get_summary(self) -> Dict[str, Any]:
        """Get Ph.D. grade telemetry summary."""
        with self._lock:
            return {
                "active_pulses": len([p for p in self._history.values() if p.end_time is None]),
                "completed_pulses": len([p for p in self._history.values() if p.end_time is not None]),
                "global_stats": dict(self._global_stats),
                "last_updated": datetime.now().isoformat()
            }

# Singleton manifold
_STATS_MANAGER = ExecutionStatistics()

def get_execution_statistics() -> ExecutionStatistics:
    return _STATS_MANAGER
