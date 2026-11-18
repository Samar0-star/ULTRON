from __future__ import annotations

# backend/observability/metrics.py
"""
Prometheus metrics wrapper for BEAST.
Creates counters/histograms if prometheus_client available; otherwise no-op.
"""

import logging
from typing import Optional
logger = logging.getLogger("beast.metrics")

try:
    from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
    METRIC_STEP_COUNT = Counter("beast_steps_total", "Total steps executed")
    METRIC_STEP_ERRORS = Counter("beast_step_errors_total", "Step errors")
    METRIC_STEP_LATENCY = Histogram("beast_step_latency_seconds", "Step latency")
    HAVE_PROM = True
except Exception:
    HAVE_PROM = False
    # no-op stand-ins
    class _Noop:
        def inc(self, *a, **k): pass
        def observe(self, *a, **k): pass
    METRIC_STEP_COUNT = METRIC_STEP_ERRORS = METRIC_STEP_LATENCY = _Noop()

def metrics_handler():
    """Return Prometheus metrics payload (bytes) or human-friendly fallback."""
    if HAVE_PROM:
        return generate_latest(REGISTRY)
    return b"# prometheus_client not available\n"

def observe_step(duration: float, error: bool = False):
    try:
        METRIC_STEP_COUNT.inc()
        if error:
            METRIC_STEP_ERRORS.inc()
        METRIC_STEP_LATENCY.observe(duration)
    except Exception:
        logger.exception("metrics observe failed")
