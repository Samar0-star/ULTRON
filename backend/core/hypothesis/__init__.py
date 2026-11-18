"""
Hypothesis Package for Avon-2 Deep Mode
=========================================

Provides hypothesis lifecycle management, novelty checking, and prioritization.
"""

from backend.core.hypothesis.models import (
    Hypothesis,
    HypothesisState,
    NoveltyReport,
    TestabilityReport,
    PriorityRanking
)

__all__ = [
    "Hypothesis",
    "HypothesisState",
    "NoveltyReport",
    "TestabilityReport",
    "PriorityRanking"
]
