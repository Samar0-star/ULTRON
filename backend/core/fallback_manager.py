"""
Fallback Manager - API Failure Handling
========================================

Handles API failures with automatic provider switching and retry logic.

Fallback Chain:
1. OpenAI (primary)
2. Local models (if available)
3. Cached results (if applicable)

Features:
- Multi-tier fallback at every layer
- Exponential backoff retry
- Circuit breaker pattern
- Fallback event broadcasting
- Statistics tracking
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from backend.llm_manager import get_model, get_fallback
except ImportError:
    try:
        from llm_manager import get_model, get_fallback
    except ImportError:
        def get_model(task): return __import__("backend.llm_manager", fromlist=["get_model"]).get_model(task)
        def get_fallback(task): return "sonnet-4.6"


class ProviderStatus(Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class FallbackEvent:
    """Records a fallback occurrence"""
    primary_provider: str
    fallback_provider: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    operation: str = ""
    success: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        return {
            "primary": self.primary_provider,
            "fallback": self.fallback_provider,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "success": self.success
        }


class FallbackManager:
    """
    Manages API failure fallbacks with automatic provider switching.

    Handles:
    - Provider health tracking
    - Retry with exponential backoff
    - Circuit breaker pattern
    - Fallback event broadcasting
    """

    def __init__(self, message_bus=None):
        """
        Args:
            message_bus: Optional message bus for event broadcasting
        """
        self.message_bus = message_bus

        # Provider health tracking
        self._provider_health: Dict[str, ProviderStatus] = {}
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._last_failure: Dict[str, float] = {}

        # Circuit breaker config
        self.circuit_breaker_threshold = 5  # Failures before opening circuit
        self.circuit_breaker_timeout = 60.0  # Seconds before retry

        # Statistics
        self._stats = {
            "total_operations": 0,
            "fallbacks_triggered": 0,
            "providers_recovered": 0,
            "events": []
        }

        logger.info(" FallbackManager initialized")

    async def execute_with_fallback(
        self,
        fn: Callable,
        *args,
        fallback_chain: Optional[List[str]] = None,
        max_retries: int = 3,
        operation_name: str = "unknown",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute function with automatic fallback.

        Args:
            fn: Async function to execute
            args: Positional arguments for fn
            fallback_chain: Provider chain (default: ["openai", "anthropic", "gemini"])
            max_retries: Retries per provider
            operation_name: Name for logging
            kwargs: Keyword arguments for fn

        Returns:
            {
                "status": "success"|"error",
                "result": Any,
                "provider": str,
                "fallbacks": List[FallbackEvent],
                "error": str|None
            }
        """
        self._stats["total_operations"] += 1

        if fallback_chain is None:
            fallback_chain = ["openai", "anthropic", "gemini"]

        errors = []
        fallback_events = []

        for provider_idx, provider in enumerate(fallback_chain):
            # Check circuit breaker
            if self._is_circuit_open(provider):
                logger.warning(f" Circuit breaker open for {provider}, skipping")
                continue

            # Mark provider as healthy on first attempt
            if provider not in self._provider_health:
                self._provider_health[provider] = ProviderStatus.HEALTHY

            # Retry loop for this provider
            for attempt in range(max_retries):
                try:
                    logger.debug(
                        f" Attempt {attempt+1}/{max_retries} "
                        f"with provider: {provider}"
                    )

                    # Set provider context (implementation-specific)
                    self._set_provider_context(provider, kwargs)

                    # Execute function (support both sync and async callables)
                    import inspect
                    res = fn(*args, **kwargs)
                    result = await res if inspect.isawaitable(res) else res

                    # Success!
                    self._record_success(provider)

                    # Publish fallback event if not primary
                    if provider_idx > 0:
                        event = FallbackEvent(
                            primary_provider=fallback_chain[0],
                            fallback_provider=provider,
                            reason=f"Primary failed: {errors[0] if errors else 'unknown'}",
                            operation=operation_name,
                            success=True
                        )
                        fallback_events.append(event)
                        await self._publish_fallback_event(event)

                        self._stats["fallbacks_triggered"] += 1
                        logger.info(
                            f" Fallback successful: {fallback_chain[0]}  {provider}"
                        )

                    return {
                        "status": "success",
                        "result": result,
                        "provider": provider,
                        "fallbacks": [e.to_dict() for e in fallback_events],
                        "error": None
                    }

                except Exception as e:
                    error_msg = str(e)
                    errors.append({
                        "provider": provider,
                        "attempt": attempt + 1,
                        "error": error_msg
                    })

                    self._record_failure(provider)

                    logger.warning(
                        f" Attempt {attempt+1} failed with {provider}: {error_msg}"
                    )

                    # Exponential backoff
                    if attempt < max_retries - 1:
                        backoff = min(2 ** attempt, 10)  # Max 10 seconds
                        await asyncio.sleep(backoff)

        # All providers exhausted
        self._stats["events"].append({
            "timestamp": time.time(),
            "operation": operation_name,
            "result": "all_providers_failed",
            "errors": errors
        })

        return {
            "status": "error",
            "result": None,
            "provider": None,
            "fallbacks": [e.to_dict() for e in fallback_events],
            "error": f"All providers failed. Errors: {errors}"
        }

    def _set_provider_context(self, provider: str, kwargs: Dict[str, Any]):
        """Set provider-specific context in kwargs"""
        if "provider" in kwargs:
            kwargs["provider"] = provider

        if "model" in kwargs:
            task_hint = kwargs.get("task_hint", "routing")
            model_mapping = {
                "openai": get_model(task_hint),
                "anthropic": get_fallback(task_hint),
                "gemini": get_model("vision"),
            }
            kwargs["model"] = model_mapping.get(provider, kwargs.get("model"))

    def _is_circuit_open(self, provider: str) -> bool:
        """Check if circuit breaker is open for provider"""

        if provider not in self._failure_counts:
            return False

        failures = self._failure_counts[provider]

        if failures < self.circuit_breaker_threshold:
            return False

        # Check if timeout has elapsed
        last_failure = self._last_failure.get(provider, 0)
        elapsed = time.time() - last_failure

        if elapsed >= self.circuit_breaker_timeout:
            # Reset circuit breaker
            logger.info(f" Circuit breaker reset for {provider}")
            self._failure_counts[provider] = 0
            self._provider_health[provider] = ProviderStatus.HEALTHY
            self._stats["providers_recovered"] += 1
            return False

        # Circuit still open
        self._provider_health[provider] = ProviderStatus.DOWN
        return True

    def _record_success(self, provider: str):
        """Record successful operation"""
        # Reset failure count
        if provider in self._failure_counts:
            old_count = self._failure_counts[provider]
            self._failure_counts[provider] = 0

            if old_count > 0:
                logger.info(f" Provider {provider} recovered")
                self._stats["providers_recovered"] += 1

        self._provider_health[provider] = ProviderStatus.HEALTHY

    def _record_failure(self, provider: str):
        """Record failed operation"""
        self._failure_counts[provider] += 1
        self._last_failure[provider] = time.time()

        failures = self._failure_counts[provider]

        if failures >= self.circuit_breaker_threshold:
            self._provider_health[provider] = ProviderStatus.DOWN
            logger.error(
                f" Circuit breaker opened for {provider} "
                f"({failures} failures)"
            )
        elif failures >= 2:
            self._provider_health[provider] = ProviderStatus.DEGRADED

    async def _publish_fallback_event(self, event: FallbackEvent):
        """Publish fallback event to message bus"""
        if self.message_bus:
            try:
                from backend.core.message_bus import MessageType

                await self.message_bus.publish(
                    msg_type=MessageType.FALLBACK_TRIGGERED,
                    sender="fallback_manager",
                    payload=event.to_dict()
                )
            except Exception as e:
                logger.warning(f"Failed to publish fallback event: {e}")

    def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers"""
        health_report = {}

        for provider, status in self._provider_health.items():
            failures = self._failure_counts.get(provider, 0)
            last_failure = self._last_failure.get(provider, 0)
            time_since_failure = time.time() - last_failure if last_failure > 0 else None

            health_report[provider] = {
                "status": status.value,
                "failure_count": failures,
                "last_failure": last_failure if last_failure > 0 else None,
                "time_since_failure_s": time_since_failure,
                "circuit_open": self._is_circuit_open(provider)
            }

        return health_report

    def get_stats(self) -> Dict[str, Any]:
        """Get fallback manager statistics"""
        return {
            "total_operations": self._stats["total_operations"],
            "fallbacks_triggered": self._stats["fallbacks_triggered"],
            "providers_recovered": self._stats["providers_recovered"],
            "fallback_rate": (
                self._stats["fallbacks_triggered"] / self._stats["total_operations"]
                if self._stats["total_operations"] > 0 else 0.0
            ),
            "provider_health": self.get_provider_health(),
            "recent_events": self._stats["events"][-10:]  # Last 10 events
        }

    def reset_stats(self):
        """Reset statistics"""
        self._stats = {
            "total_operations": 0,
            "fallbacks_triggered": 0,
            "providers_recovered": 0,
            "events": []
        }

    def reset_circuit_breaker(self, provider: str):
        """Manually reset circuit breaker for a provider"""
        if provider in self._failure_counts:
            self._failure_counts[provider] = 0
            self._provider_health[provider] = ProviderStatus.HEALTHY
            logger.info(f" Manually reset circuit breaker for {provider}")

    def force_provider_down(self, provider: str, duration: float = 300.0):
        """Manually mark provider as down for a duration"""
        self._failure_counts[provider] = self.circuit_breaker_threshold
        self._last_failure[provider] = time.time()
        self._provider_health[provider] = ProviderStatus.DOWN

        logger.warning(
            f" Manually marked {provider} as down for {duration}s"
        )

        # Schedule recovery if an event loop is running
        async def recover():
            await asyncio.sleep(duration)
            self.reset_circuit_breaker(provider)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(recover())
        except RuntimeError:
            pass


# Global singleton
_global_fallback_manager: Optional[FallbackManager] = None


def get_fallback_manager(message_bus=None) -> FallbackManager:
    """Get global fallback manager instance"""
    global _global_fallback_manager
    if _global_fallback_manager is None:
        _global_fallback_manager = FallbackManager(message_bus=message_bus)
    return _global_fallback_manager


def reset_fallback_manager():
    """Reset global fallback manager (for testing)"""
    global _global_fallback_manager
    _global_fallback_manager = None
