"""
SVEL EXPERIMENT TEMPLATE BASE
===============================
Provides base class for templates that do not use the high-level base.py architecture.
Used primarily by specialized ML and Physics kernels.
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

class BaseExperimentTemplate(ABC):
    """
    Standard interface for all experiment templates.
    """
    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain

    @abstractmethod
    def generate_protocol(self, hypothesis: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the protocol for an experiment."""
        pass
