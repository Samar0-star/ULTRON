"""
SVEL TEMPLATE REGISTRY
========================
Hybrid Template + LLM Integration System
Connects orphaned templates to ExperimentAgent
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from backend.experiments.templates import (
    TEMPLATE_REGISTRY,
    find_applicable_templates,
    get_templates_by_domain,
    get_all_templates
)
from backend.experiments.templates.base import TemplateBase, TemplateCustomizationParams
from backend.experiments.models import ExperimentProtocol

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """
    Central registry for experiment templates with hybrid LLM enhancement.
    Bridges the gap between template generation and LLM customization.
    """
    
    def __init__(self):
        self._registry = TEMPLATE_REGISTRY
        logger.info(f"TemplateRegistry initialized with {len(self._registry)} templates")
    
    @property
    def template_count(self) -> int:
        return len(self._registry)
    
    def get_template(self, name: str) -> Optional[TemplateBase]:
        """Get a template by name."""
        return self._registry.get(name)
    
    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self._registry.keys())
    
    def find_best_template(
        self,
        hypothesis: Any,
        experiment_type: str = None,
        domain: str = None,
        use_llm: bool = True
    ) -> Optional[TemplateBase]:
        """
        Find the best template for a hypothesis.
        
        TIER 1: Heuristic matching (fast)
        TIER 2: LLM semantic selection (accurate)
        
        Args:
            hypothesis: Hypothesis object or statement string
            experiment_type: Optional experiment type filter
            domain: Optional domain filter
            use_llm: Whether to use LLM for selection
            
        Returns:
            Best matching template or None
        """
        hypothesis_str = str(hypothesis.statement) if hasattr(hypothesis, 'statement') else str(hypothesis)
        
        logger.info(f"[TEMPLATES] Finding best template for: {hypothesis_str[:80]}...")
        
        # Get candidates using existing system
        if not use_llm:
            from backend.experiments.templates import search_templates
            candidates = search_templates(hypothesis_str, top_k=5)
            if domain:
                domain_filtered = [t for t in candidates if getattr(t, "domain", None) == domain]
                if domain_filtered:
                    candidates = domain_filtered
        else:
            candidates = find_applicable_templates(
                hypothesis=hypothesis,
                top_k=5,
                use_llm=use_llm,
                domain=domain
            )
        
        if not candidates:
            logger.warning(f"[TEMPLATES] No templates found for hypothesis")
            return None
        
        # Return highest scored template
        best = candidates[0]
        logger.info(f"[TEMPLATES] Selected: {best.name} (domain: {best.domain}, rigor: {best.rigor_score})")
        return best
    
    def generate_protocol(
        self,
        template: TemplateBase,
        hypothesis: Any,
        **kwargs
    ) -> ExperimentProtocol:
        """
        Generate a protocol using a template.
        
        Args:
            template: Template to use
            hypothesis: Hypothesis to test
            **kwargs: Additional customization params
            
        Returns:
            ExperimentProtocol
        """
        params = TemplateCustomizationParams(
            hypothesis=hypothesis,
            hypothesis_id=getattr(hypothesis, 'id', ''),
            custom_variables=kwargs.get('custom_variables', {}),
            data_paths=kwargs.get('data_paths', {}),
            options=kwargs
        )
        
        logger.info(f"[TEMPLATES] Generating protocol with {template.name}")
        protocol = template.generate_protocol(params)
        
        # Track usage
        template.usage_count += 1
        
        return protocol
    
    def get_template_metadata(self, template: TemplateBase) -> Dict[str, Any]:
        """Get metadata for a template."""
        return {
            "name": template.name,
            "title": template.title,
            "domain": template.domain,
            "experiment_type": str(template.experiment_type),
            "description": template.description[:200] + "...",
            "suitable_for": template.suitable_for,
            "requirements": template.requirements,
            "complexity_score": template.complexity_score,
            "rigor_score": template.rigor_score,
            "usage_count": getattr(template, 'usage_count', 0),
            "success_rate": getattr(template, 'success_rate', 1.0)
        }


# Global registry instance
_registry: Optional[TemplateRegistry] = None


def get_template_registry() -> TemplateRegistry:
    """Get or create the global template registry."""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
    return _registry


def find_best_template(
    hypothesis: Any,
    domain: str = None,
    use_llm: bool = True
) -> Optional[TemplateBase]:
    """Convenience function to find best template."""
    return get_template_registry().find_best_template(
        hypothesis=hypothesis,
        domain=domain,
        use_llm=use_llm
    )


def list_available_templates(domain: str = None) -> List[Dict[str, Any]]:
    """List all available templates with metadata."""
    registry = get_template_registry()
    
    if domain:
        templates = get_templates_by_domain(domain)
    else:
        templates = get_all_templates()
    
    return [registry.get_template_metadata(t) for t in templates]


def get_template_stats() -> Dict[str, Any]:
    """Get statistics about template usage."""
    registry = get_template_registry()
    return {
        "total_templates": registry.template_count,
        "available_templates": registry.list_templates(),
        "domains": list(set(
            t.domain for t in get_all_templates()
        ))
    }
