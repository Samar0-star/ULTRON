"""
SVEL Core Engine Components
===========================
Core mathematical and causal components:
- Causal World Model (Causal DAG, HyperEdge, Fact, Conflict)
- Statistical Grounding & Validation
"""

from backend.core.world_model import WorldModel, Fact, Conflict, HyperEdge, get_world_model

__all__ = [
    'WorldModel',
    'Fact',
    'Conflict',
    'HyperEdge',
    'get_world_model'
]

