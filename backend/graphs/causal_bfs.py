"""
Causal BFS Intervention Engine
===============================
Deterministic causal graph traversal and counterfactual intervention simulator.

Traverses directed causal edges with decaying transmission multipliers to determine:
1. Downstream impact of proposed mutations or physical perturbations.
2. Contradiction paths between newly proposed hypotheses and established empirical facts.
3. Multi-hop causal mechanisms bridging distant literature findings.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple
import logging

logger = logging.getLogger("graphs.causal_bfs")


@dataclass
class CausalNode:
    id: str
    name: str
    domain: str
    value: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    source_id: str
    target_id: str
    relation: str  # e.g., "activates", "inhibits", "stabilizes", "destabilizes"
    weight: float = 1.0
    confidence: float = 1.0


@dataclass
class CausalPath:
    nodes: List[str]
    relations: List[str]
    cumulative_effect: float
    confidence: float


class CausalBFSEngine:
    """
    Evaluates interventions and traces causal mechanisms using breadth-first search.
    """

    def __init__(self, decay_rate: float = 0.85, max_depth: int = 5):
        self.decay_rate = decay_rate
        self.max_depth = max_depth
        self.nodes: Dict[str, CausalNode] = {}
        self.adjacency: Dict[str, List[CausalEdge]] = {}

    def add_node(self, node_id: str, name: str, domain: str = "general") -> None:
        self.nodes[node_id] = CausalNode(id=node_id, name=name, domain=domain)
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0, confidence: float = 1.0) -> None:
        if source_id not in self.adjacency:
            self.adjacency[source_id] = []
        if target_id not in self.adjacency:
            self.adjacency[target_id] = []

        edge = CausalEdge(source_id=source_id, target_id=target_id, relation=relation, weight=weight, confidence=confidence)
        self.adjacency[source_id].append(edge)

    def find_causal_paths(self, start_id: str, end_id: str) -> List[CausalPath]:
        """Find all causal paths from start_id to end_id within max_depth."""
        if start_id not in self.adjacency or end_id not in self.nodes:
            return []

        paths: List[CausalPath] = []
        # queue elements: (current_node, [node_history], [relation_history], current_effect, current_confidence)
        queue = deque([(start_id, [start_id], [], 1.0, 1.0)])

        while queue:
            curr, node_hist, rel_hist, effect, conf = queue.popleft()

            if curr == end_id and len(node_hist) > 1:
                paths.append(CausalPath(
                    nodes=node_hist,
                    relations=rel_hist,
                    cumulative_effect=effect,
                    confidence=conf
                ))
                continue

            if len(node_hist) > self.max_depth:
                continue

            for edge in self.adjacency.get(curr, []):
                nxt = edge.target_id
                if nxt in node_hist:  # Avoid cyclic loops
                    continue

                sign = -1.0 if "inhibit" in edge.relation or "destabilize" in edge.relation else 1.0
                step_effect = effect * edge.weight * sign * self.decay_rate
                step_conf = conf * edge.confidence

                queue.append((
                    nxt,
                    node_hist + [nxt],
                    rel_hist + [edge.relation],
                    step_effect,
                    step_conf
                ))

        return sorted(paths, key=lambda p: abs(p.cumulative_effect) * p.confidence, reverse=True)

    def simulate_intervention(self, intervention_node_id: str, delta: float = 1.0) -> Dict[str, float]:
        """
        Simulates the forward propagation of a counterfactual change (do(X = x + delta)).
        Returns the predicted shifted values of downstream nodes.
        """
        shifts: Dict[str, float] = {intervention_node_id: delta}
        queue = deque([(intervention_node_id, delta, 0)])
        visited: Set[str] = {intervention_node_id}

        while queue:
            curr, current_delta, depth = queue.popleft()
            if depth >= self.max_depth:
                continue

            for edge in self.adjacency.get(curr, []):
                nxt = edge.target_id
                sign = -1.0 if "inhibit" in edge.relation or "destabilize" in edge.relation else 1.0
                propagated = current_delta * edge.weight * sign * (self.decay_rate ** (depth + 1))

                shifts[nxt] = shifts.get(nxt, 0.0) + propagated

                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, propagated, depth + 1))

        return shifts
