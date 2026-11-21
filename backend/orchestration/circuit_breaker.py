"""
Circuit Breaker for SVEL Orchestration
========================================
Graceful degradation and fault tolerance for multi-day autonomous research sessions.

States:
- CLOSED: Normal operation, all tasks execute.
- OPEN: Failure threshold exceeded, operations suspended to prevent cascading crashes.
- HALF_OPEN: Trial mode, allowing limited probes to verify system recovery.

Includes Grounding Grace: Honest null/negative scientific results are NOT treated
as infrastructure failures, preventing campaign halts when ideas are refuted.
"""

from datetime import datetime, timedelta
from enum import Enum
import logging
from typing import Optional, Callable, Any

logger = logging.getLogger("orchestration.circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Production-grade circuit breaker with recovery backoff and Grounding Grace.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        half_open_success_threshold: int = 2
    ):
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)
        self.half_open_success_threshold = half_open_success_threshold

        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_failure: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()

    def record_failure(self, error: str = "", is_grounding_null: bool = False) -> None:
        """
        Record an operation failure.
        If is_grounding_null is True, grants Grounding Grace: honest scientific
        refutations do not trigger circuit trips.
        """
        if is_grounding_null:
            logger.info(f"[CIRCUIT BREAKER] Grounding Grace granted for null scientific finding: {error}")
            return

        self.failure_count += 1
        self.last_failure = datetime.now()
        logger.warning(f"[CIRCUIT BREAKER] Recorded failure #{self.failure_count}: {error}")

        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self._transition(CircuitState.OPEN)
        elif self.state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN)

    def record_success(self) -> None:
        """Record an operation success."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_success_threshold:
                self.failure_count = 0
                self.success_count = 0
                self._transition(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def can_execute(self) -> bool:
        """Check whether the circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure and (datetime.now() - self.last_failure) > self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def _transition(self, new_state: CircuitState) -> None:
        old_state = self.state
        self.state = new_state
        self.last_state_change = datetime.now()
        logger.info(f"[CIRCUIT BREAKER] Transition: {old_state.value} -> {new_state.value}")
