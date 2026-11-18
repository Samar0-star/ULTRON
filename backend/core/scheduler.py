import logging
import time
from enum import Enum
from typing import Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass

from backend.core.capacity.memory_bucket import MemoryTokenBucket
from backend.core.api.models import Provider

logger = logging.getLogger("avon.scheduler")

class ScheduleStatus(str, Enum):
    GRANTED = "granted"
    QUEUED = "queued"
    REJECTED = "rejected"  # Use for SLA violations

@dataclass
class JobContext:
    job_id: str
    priority: int  # 10=Standard, 100=Interactive
    max_wait: float # Seconds
    created_at: float

class GlobalScheduler:
    """
    Central brain for API capacity management.
    Replacing "Key Rotation" with "Capacity Scheduling".
    """
    
    def __init__(self, redis_url: str = None):
        logger.info(" GlobalScheduler: Using MEMORY backend (Isolated Compute Node).")
        self.bucket = MemoryTokenBucket()

        # In a real system, these would likely come from dynamic config or DB
        self.limits = {
            Provider.OPENAI: {"rpm": 5000, "tpm": 150000, "conc": 20, "base_conc": 20},
            Provider.ANTHROPIC: {"rpm": 4000, "tpm": 200000, "conc": 20, "base_conc": 20},
            Provider.GEMINI: {"rpm": 600, "tpm": 1000000, "conc": 5, "base_conc": 5},
            Provider.MOONSHOT: {"rpm": 300, "tpm": 10000, "conc": 1, "base_conc": 1}, # Strict
        }
        
        # Feedback memory: {provider: [error_timestamps]}
        self._error_history: Dict[str, List[float]] = {}

    def acquire_non_blocking(self, 
                           provider: Union[Provider, str], 
                           cost_estimate: int, 
                           context: JobContext) -> Tuple[ScheduleStatus, str]:
        """
        Request capacity. Returns status immediately.
        Does NOT block the thread.
        Accepts both Provider enum and string (e.g. "openai").
        """
        # Convert string to Provider enum if needed
        provider_value = provider.value if hasattr(provider, 'value') else str(provider)
        
        # 1. Check SLA Deadline
        elapsed = time.time() - context.created_at
        if elapsed > context.max_wait:
            logger.warning(f"SLA Deadline Exceeded ({elapsed}s > {context.max_wait}s) but REJECTION DISABLED for stability.")
            # return ScheduleStatus.REJECTED, "sla_deadline_exceeded"

        # 2. Check Job Fairness (Stub - would check Redis job:{id} counters)
        # fairness_ok = self.check_fairness(context.job_id)
        # if not fairness_ok: return ScheduleStatus.QUEUED, "fairness_throttle"

        # 3. Check Global Capacity
        # Try to look up by enum first, then by string
        if hasattr(provider, 'value'):
            limit = self.limits.get(provider, {"rpm": 60, "tpm": 10000, "conc": 1})
        else:
            # String lookup - try to convert
            try:
                provider_enum = Provider(provider)
                limit = self.limits.get(provider_enum, {"rpm": 60, "tpm": 10000, "conc": 1})
            except ValueError:
                limit = {"rpm": 60, "tpm": 10000, "conc": 1}
        key_base = f"limiter:{provider_value}:global" 

        allowed, reason = self.bucket.acquire(
            key_base, 
            cost=cost_estimate, 
            rpm=limit["rpm"], 
            tpm=limit["tpm"], 
            concurrency=limit["conc"]
        )

        if allowed:
            return ScheduleStatus.GRANTED, "ok"
        else:
            # In a real implementation: Push to Redis List (Queue)
            # self.queue.push(context, provider, cost_estimate)
            return ScheduleStatus.QUEUED, reason

    def release(self, provider: Union[Provider, str], cost_actual: int, success: bool = True):
        """
        Record completion.
        Updates Concurrency and Feedback Loop.
        Accepts both Provider enum and string (e.g. "openai").
        """
        provider_value = provider.value if hasattr(provider, 'value') else str(provider)
        key_base = f"limiter:{provider_value}:global"
        self.bucket.release(key_base)
        
        # Feedback Loop: Adjust concurrency based on success/failure
        if not success:
            self._report_error(provider)
        else:
            self._report_success(provider)

    def _report_error(self, provider: Union[Provider, str]):
        """Back off on error (429/401/403)."""
        try:
            provider_enum = provider if isinstance(provider, Provider) else Provider(provider)
        except ValueError:
            return
        if provider_enum in self.limits:
            limit = self.limits[provider_enum]
            old_conc = limit["conc"]
            # Multiplicative backoff (reduce to 70%)
            limit["conc"] = max(1, int(old_conc * 0.7))
            logger.warning(f" [SCHEDULER] Backing off {provider_enum.value}: Concurrency {old_conc} -> {limit['conc']}")

    def _report_success(self, provider: Union[Provider, str]):
        """Slowly ramp back up on success."""
        try:
            provider_enum = provider if isinstance(provider, Provider) else Provider(provider)
        except ValueError:
            return
        if provider_enum in self.limits:
            limit = self.limits[provider_enum]
            if limit["conc"] < limit["base_conc"]:
                # Additive increase
                limit["conc"] += 1
                logger.info(f" [SCHEDULER] Ramping up {provider_enum.value}: Concurrency -> {limit['conc']}")

    def estimate_cost(self, prompt: str, model: str) -> int:
        """Simple token-based cost estimator."""
        # Heuristic: 1 char = 0.25 tokens
        return len(prompt) // 4

# Singleton
_scheduler = None
def get_scheduler() -> GlobalScheduler:
    global _scheduler
    if not _scheduler:
        # Fallback to localhost, in reality load from ENV
        _scheduler = GlobalScheduler()
    return _scheduler
