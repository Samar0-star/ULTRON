"""
Graph World Model
=================
Causal knowledge graph and epistemic governor.
Exposes WorldModel, Fact, Conflict, and Causal Hypergraph methods.
"""

from backend.core.world_model import (
    WorldModel,
    Fact,
    Conflict,
    HyperEdge,
    TemporalFact,
    CausalLink,
    get_world_model
)

__all__ = [
    "WorldModel",
    "Fact",
    "Conflict",
    "HyperEdge",
    "TemporalFact",
    "CausalLink",
    "get_world_model"
]
