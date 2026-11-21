"""
Execution & Statistical Analysis Module
=======================================
Provides statistical validation and empirical hypothesis testing.
"""

from backend.core.execution.statistics import (
    StatisticalValidator,
    run_statistical_test,
    summarize_results
)

__all__ = [
    "StatisticalValidator",
    "run_statistical_test",
    "summarize_results"
]
