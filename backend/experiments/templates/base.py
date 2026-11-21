"""
SVEL Template Base Class
==========================
Base class for all PhD-level experiment templates.
Enhanced with SVEL-specific features.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging
import re

from backend.experiments.models import (
    ExperimentProtocol,
    ExperimentType,
    ProtocolStep,
    Variable,
    StatisticalTestSpec,
    ValidationCheck,
    ResourceRequirements
)

logger = logging.getLogger("svel.experiments.templates")


@dataclass
class TemplateCustomizationParams:
    """Parameters for customizing a template."""
    hypothesis: Any  # Hypothesis object
    hypothesis_id: str = ""  # Added for Apex templates
    custom_variables: Dict[str, Any] = field(default_factory=dict)
    data_paths: Dict[str, str] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)


class TemplateBase(ABC):
    """
    Abstract base class for all experiment templates.
    
    Each template represents a PhD-level research methodology
    that can be applied to test hypotheses in a specific domain.
    """
    
    def __init__(
        self,
        name: str,
        experiment_type: ExperimentType,
        domain: str,
        title: str,
        description: str,
        suitable_for: List[str],
        requirements: List[str],
        complexity_score: float = 0.5,
        rigor_score: float = 0.8
    ):
        self.name = name
        self.experiment_type = experiment_type
        self.domain = domain
        self.title = title
        self.description = description
        self.suitable_for = suitable_for
        self.requirements = requirements
        self.complexity_score = complexity_score
        self.rigor_score = rigor_score
        
        # Usage tracking
        self.usage_count = 0
        self.success_rate = 1.0
    
    @abstractmethod
    def is_applicable(self, hypothesis: Any) -> bool:
        """
        Check if this template is applicable to a hypothesis.
        """
        pass
    
    @abstractmethod
    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        """
        Generate a complete experiment protocol.
        """
        pass
    
    def get_keywords(self) -> List[str]:
        """Get keywords for semantic matching."""
        keywords = []
        keywords.extend(self.suitable_for)
        for phrase in self.suitable_for:
            for w in re.findall(r"[a-zA-Z0-9_-]+", str(phrase).lower()):
                if len(w) > 3:
                    keywords.append(w)
        keywords.extend(self.domain.split("_"))
        for w in re.findall(r"[a-zA-Z0-9_-]+", self.title.lower()):
            if len(w) > 2:
                keywords.append(w)
        return list(set(keywords))
    
    def matches_query(self, query: str) -> float:
        """
        Score how well this template matches a query.
        """
        query_lower = query.lower()
        keywords = self.get_keywords()
        
        matches = sum(1 for kw in keywords if kw.lower() in query_lower)
        
        # Boost for exact domain match
        if self.domain.lower() in query_lower:
            matches += 3
        
        base_score = matches / max(1.0, len(keywords) * 0.3)
        try:
            if type(self).is_applicable_heuristic is not TemplateBase.is_applicable_heuristic:
                if self.is_applicable_heuristic(query):
                    base_score += 0.5
            elif not self.is_applicable("__unmatched_sentinel_token_999__") and self.is_applicable(query):
                base_score += 0.5
        except Exception:
            pass
        return min(1.0, base_score)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template metadata to dict."""
        return {
            "name": self.name,
            "experiment_type": self.experiment_type.value if hasattr(self.experiment_type, "value") else str(self.experiment_type),
            "domain": self.domain,
            "title": self.title,
            "description": self.description,
            "suitable_for": self.suitable_for,
            "requirements": self.requirements,
            "complexity_score": self.complexity_score,
            "rigor_score": self.rigor_score
        }

    def get_metadata_summary(self) -> str:
        """Get a concise summary for LLM context."""
        return (
            f"TEMPLATE: {self.name} ({self.title})\n"
            f"DOMAIN: {self.domain}\n"
            f"DESCRIPTION: {self.description}\n"
            f"SUITABLE FOR: {', '.join(self.suitable_for)}\n"
        )

    def is_applicable_heuristic(self, hypothesis: Any) -> bool:
        """
        Fast keyword-based check for initial filtering.
        """
        s = str(hypothesis).lower()
        try:
            if not self.is_applicable("__unmatched_sentinel_token_999__") and self.is_applicable(hypothesis):
                return True
        except Exception:
            pass
        return any(kw.lower() in s for kw in self.get_keywords())


class DataAnalysisTemplate(TemplateBase):
    """Base class for data analysis templates."""
    
    def __init__(self, **kwargs):
        kwargs.setdefault("experiment_type", ExperimentType.DATA_ANALYSIS)
        super().__init__(**kwargs)


class SimulationTemplate(TemplateBase):
    """Base class for simulation templates."""
    
    def __init__(self, **kwargs):
        kwargs.setdefault("experiment_type", ExperimentType.SIMULATION)
        super().__init__(**kwargs)


class StatisticalTemplate(TemplateBase):
    """Base class for statistical analysis templates."""
    
    def __init__(self, **kwargs):
        kwargs.setdefault("experiment_type", ExperimentType.STATISTICAL)
        super().__init__(**kwargs)


class MLTemplate(TemplateBase):
    """Base class for machine learning templates."""
    
    def __init__(self, **kwargs):
        kwargs.setdefault("experiment_type", ExperimentType.MACHINE_LEARNING)
        super().__init__(**kwargs)
