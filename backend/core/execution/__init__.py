"""
Execution Module for Avon-2 Deep Mode
=======================================

Provides code execution, statistical analysis, and experiment management.
"""

from backend.core.execution.statistics import (
    StatisticalValidator,
    run_statistical_test,
    summarize_results
)
from backend.execution.sandbox import (
    GodModeSandbox,
    SandboxProvider
)

__all__ = [
    "StatisticalValidator",
    "run_statistical_test",
    "summarize_results",
    "GodModeSandbox",
    "SandboxProvider"
]
