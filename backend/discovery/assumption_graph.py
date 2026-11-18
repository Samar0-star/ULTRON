# -*- coding: utf-8 -*-
"""
ASSUMPTION GRAPH (DAG)
==========================================
Implements a Directed Acyclic Graph for tracking assumption dependencies.

Rules:
1. Root = "Approach Viable"
2. Leaves = Measurable constraints
3. If a node is violated  auto-violate all upstream parents
4. Always attack the node with highest out-degree first
"""
import hashlib
import logging
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from enum import Enum

logger = logging.getLogger(__name__)

from backend.discovery.constants import ScientificDefaults


class Verdict(Enum):
    """Three-State Verdict System (Replaces Binary)."""
    DEAD = "dead"
    CONDITIONALLY_DEAD = "conditionally_dead"
    ESCAPED = "escaped"


class EscapeType(Enum):
    """Escape Route Types (Formal Enumeration)."""
    MATERIAL = "material"
    GEOMETRY = "geometry"
    OPERATING_REGIME = "operating_regime"
    CONTROL = "control"


@dataclass
class VerifiedEscape:
    """[RIGOR] FLAW 26 FIX: Escape routes must be backed by evidence."""
    exists: bool = False
    evidence_fact_id: Optional[str] = None
    confidence: float = 0.0


@dataclass
class EscapeRouteReport:
    """Mandatory Escape Route Output."""
    material_escape: VerifiedEscape = field(default_factory=VerifiedEscape)
    geometry_escape: VerifiedEscape = field(default_factory=VerifiedEscape)
    operating_regime_escape: VerifiedEscape = field(default_factory=VerifiedEscape)
    control_escape: VerifiedEscape = field(default_factory=VerifiedEscape)
    
    @staticmethod
    def _coerce_escape(val: Any) -> VerifiedEscape:
        if isinstance(val, VerifiedEscape):
            return val
        if isinstance(val, dict):
            return VerifiedEscape(
                exists=bool(val.get("exists", False)),
                evidence_fact_id=val.get("evidence_fact_id"),
                confidence=float(val.get("confidence", 0.8 if val.get("exists") else 0.0))
            )
        exists_b = bool(val)
        return VerifiedEscape(exists=exists_b, evidence_fact_id=None, confidence=0.8 if exists_b else 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_escape": self._coerce_escape(self.material_escape).__dict__,
            "geometry_escape": self._coerce_escape(self.geometry_escape).__dict__,
            "operating_regime_escape": self._coerce_escape(self.operating_regime_escape).__dict__,
            "control_escape": self._coerce_escape(self.control_escape).__dict__
        }
    
    @property
    def escape_count(self) -> int:
        # Only count escapes with high confidence evidence
        escapes = [
            self._coerce_escape(e)
            for e in [self.material_escape, self.geometry_escape, self.operating_regime_escape, self.control_escape]
        ]
        return sum(1 for e in escapes if e.exists and e.confidence >= 0.7)

    def get_verdict(self) -> Verdict:
        """Map verified escape routes to Verdict."""
        if self.escape_count >= 1:
            return Verdict.ESCAPED
        any_candidate = any(
            self._coerce_escape(e).exists
            for e in [self.material_escape, self.geometry_escape, self.operating_regime_escape, self.control_escape]
        )
        return Verdict.CONDITIONALLY_DEAD if any_candidate else Verdict.DEAD


class DiscrepancyType(Enum):
    """[TITAN V162.2] Generalized Empirical Discrepancy Framework."""
    EMPIRICAL_CONTRADICTION = "empirical_contradiction"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"
    BOUNDARY_VIOLATION = "boundary_violation"
    SIGNAL_COLLAPSE = "signal_collapse"


@dataclass
class VerifiedDiscrepancy:
    """Discrepancy backed by physical evidence."""
    detected: bool = False
    evidence_id: Optional[str] = None
    confidence: float = 0.0

@dataclass
class DiscrepancyReport:
    """Consolidated manifold of evidence against an approach."""
    contradictions: List[VerifiedDiscrepancy] = field(default_factory=list)
    inconsistencies: List[VerifiedDiscrepancy] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradictions": [d.__dict__ for d in self.contradictions],
            "inconsistencies": [d.__dict__ for d in self.inconsistencies]
        }
    
    @property
    def total_discrepancies(self) -> int:
        return sum([1 for d in self.contradictions + self.inconsistencies if d.detected and d.confidence >= 0.7])
    
    def get_verdict(self) -> Verdict:
        """Map evidence manifold to Approach Verdict."""
        if self.total_discrepancies >= 2:
            return Verdict.DEAD
        elif self.total_discrepancies == 1:
            return Verdict.CONDITIONALLY_DEAD
        else:
            return Verdict.ESCAPED



@dataclass
class AssumptionNode:
    """A node in the Assumption Graph."""
    id: str
    statement: str
    dependencies: List[str] = field(default_factory=list)  # Children that this node requires
    violated: bool = False
    violation_reason: Optional[str] = None
    violation_source: Optional[str] = None  # Paper/experiment citation
    
    @property
    def hash(self) -> str:
        """Unique hash for irreversibility tracking."""
        return hashlib.sha256(self.statement.lower().encode()).hexdigest()[:16]


class AssumptionGraph:
    """
    Directed Acyclic Graph for Assumption Dependencies.
    
    Structure:
    - Root: "Approach Viable" (abstract)
    - Intermediate: Sub-requirements
    - Leaves: Measurable constraints (numbers)
    """
    
    def __init__(self):
        self.nodes: Dict[str, AssumptionNode] = {}
        self.killed_hashes: Set[str] = set()  # IRREVERSIBILITY: Killed assumption hashes
        self._lock = threading.RLock()
        
        # Create root node
        self.root_id = "root_viable"
        self.nodes[self.root_id] = AssumptionNode(
            id=self.root_id,
            statement="Approach is Viable",
            dependencies=[]
        )
        
        logger.info("AssumptionGraph initialized with root node.")
    
    def add_assumption(self, statement: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Add an assumption to the graph.
        
        Args:
            statement: The assumption statement
            parent_id: ID of parent node (defaults to root)
            
        Returns:
            str: ID of the new node, or None if rejected (irreversibility)
        """
        with self._lock:
            # IRREVERSIBILITY CHECK
            node_hash = hashlib.sha256(statement.lower().encode()).hexdigest()[:16]
            if node_hash in self.killed_hashes:
                logger.warning(f"IRREVERSIBILITY: Rejected rephrased killed assumption: {statement[:50]}...")
                return None
            
            # Create node
            node_id = f"assumption_{len(self.nodes)}"
            node = AssumptionNode(
                id=node_id,
                statement=statement,
                dependencies=[]
            )
            self.nodes[node_id] = node
            
            # Link to parent
            parent = parent_id or self.root_id
            if parent in self.nodes:
                self.nodes[parent].dependencies.append(node_id)
            
            # [RIGOR FIX] Fast O(V+E) Cycle Detection
            # Abolish O(N^3) bottleneck. Use standard DFS cycle check.
            visited = set()
            rec_stack = set()
            
            def has_cycle(curr_id: str) -> bool:
                visited.add(curr_id)
                rec_stack.add(curr_id)
                for child_id in self.nodes[curr_id].dependencies:
                    if child_id not in visited:
                        if has_cycle(child_id): return True
                    elif child_id in rec_stack:
                        return True
                rec_stack.remove(curr_id)
                return False
                
            if has_cycle(self.root_id):
                # Revert
                self.nodes[parent].dependencies.remove(node_id)
                del self.nodes[node_id]
                logger.warning(f" [GRAPH] Cycle detected when adding {node_id}. Reverting.")
                return None
                
            logger.info(f"Added assumption [{node_id}]: {statement[:50]}...")
            return node_id
    
    def violate(self, node_id: str, reason: str, source: Optional[str] = None, _depth: int = 0) -> List[str]:
        """
        Violate a node and cascade to all upstream parents.
        
        FIX #20: Added _depth parameter to prevent stack overflow on deep graphs.
        
        Returns:
            List[str]: IDs of all nodes that were violated (including cascades)
        """
        with self._lock:
            MAX_CASCADE_DEPTH = 50  # FIX #20: Prevent stack overflow
            violated_nodes = []
            
            if _depth > MAX_CASCADE_DEPTH:
                logger.warning(f"CASCADE DEPTH LIMIT ({MAX_CASCADE_DEPTH}) reached, stopping propagation")
                return violated_nodes
            
            if node_id not in self.nodes:
                return violated_nodes
                
            node = self.nodes[node_id]
            if node.violated:
                return violated_nodes  # Already violated
                
            # Violate this node
            node.violated = True
            node.violation_reason = reason
            node.violation_source = source
            violated_nodes.append(node_id)
            
            # IRREVERSIBILITY: Lock this assumption forever
            self.killed_hashes.add(node.hash)
            
            logger.info(f"VIOLATED [{node_id}]: {node.statement[:50]}... Reason: {reason[:50]}")
            
            # CASCADE: Violate all upstream parents (with depth tracking)
            for parent_id, parent_node in self.nodes.items():
                if node_id in parent_node.dependencies and not parent_node.violated:
                    cascade_result = self.violate(parent_id, f"Dependency {node_id} violated", source, _depth + 1)
                    violated_nodes.extend(cascade_result)
            
            return violated_nodes
    
    def get_attack_priority(self) -> List[str]:
        """
        Get nodes ordered by attack priority (highest in-degree first).
        
        Returns:
            List[str]: Node IDs ordered by attack priority
        """
        # Calculate in-degree (number of dependents)
        in_degrees = {node_id: 0 for node_id in self.nodes}
        for node in self.nodes.values():
            for dep in node.dependencies:
                if dep in in_degrees:
                    in_degrees[dep] += 1
                    
        nodes_with_degree = []
        for node_id, node in self.nodes.items():
            if not node.violated and node_id != self.root_id:
                nodes_with_degree.append((node_id, in_degrees[node_id]))
        
        # Sort by in-degree descending
        nodes_with_degree.sort(key=lambda x: x[1], reverse=True)
        
        return [n[0] for n in nodes_with_degree]
    
    def get_verdict(self) -> Verdict:
        """Get the overall verdict based on graph state."""
        # If root is violated, entire approach is DEAD
        if self.nodes[self.root_id].violated:
            return Verdict.DEAD
        
        # Count violated vs total assumptions
        total_assumptions = len(self.nodes) - 1  # Exclude root
        violated_count = sum(1 for n in self.nodes.values() if n.violated and n.id != self.root_id)
        
        if violated_count == 0:
            return Verdict.ESCAPED
        elif violated_count < total_assumptions:
            return Verdict.CONDITIONALLY_DEAD
        else:
            return Verdict.DEAD
    def to_dict(self) -> Dict:
        """Export graph as dictionary."""
        return {
            "nodes": {
                node_id: {
                    "statement": node.statement,
                    "dependencies": node.dependencies,
                    "violated": node.violated,
                    "violation_reason": node.violation_reason,
                    "violation_source": node.violation_source
                }
                for node_id, node in self.nodes.items()
            },
            "killed_hashes": list(self.killed_hashes),
            "verdict": self.get_verdict().value
        }

    def load_from_dict(self, data: Dict[str, Any]):
        """Rehydrate graph from dictionary (Persistence Fix)."""
        nodes_data = data.get("nodes", {})
        self.nodes = {}
        for node_id, n_data in nodes_data.items():
            node = AssumptionNode(
                id=node_id,
                statement=n_data.get("statement", ""),
                dependencies=n_data.get("dependencies", []),
                violated=n_data.get("violated", False),
                violation_reason=n_data.get("violation_reason"),
                violation_source=n_data.get("violation_source")
            )
            self.nodes[node_id] = node
        
        self.killed_hashes = set(data.get("killed_hashes", []))
        logger.info(f"AssumptionGraph rehydrated with {len(self.nodes)} nodes.")


# User-scoped registry (Memory Cache with limited size)
from collections import OrderedDict
_user_graph_cache = OrderedDict()
MAX_CACHE_SIZE = 100
_graph_lock = threading.Lock()

def get_assumption_graph(mission_id: Optional[str] = None, session_id: str = "default") -> AssumptionGraph:
    """Get or create a user/session-scoped assumption graph."""
    global _user_graph_cache
    uid = mission_id or "default_user"
    cache_key = (uid, session_id)
    
    with _graph_lock:
        if cache_key in _user_graph_cache:
            # Move to end (LRU)
            graph = _user_graph_cache.pop(cache_key)
            _user_graph_cache[cache_key] = graph
            return graph
            
        # Create new
        if len(_user_graph_cache) >= MAX_CACHE_SIZE:
            _user_graph_cache.popitem(last=False)
            
        graph = AssumptionGraph()
        _user_graph_cache[cache_key] = graph
        logger.info(f" AssumptionGraph created for user: {uid}, session: {session_id}")
        return graph

def reset_assumption_graph(mission_id: Optional[str] = None, session_id: str = "default"):
    """Reset the assumption graph for a specific user session."""
    global _user_graph_cache
    uid = mission_id or "default_user"
    cache_key = (uid, session_id)
    with _graph_lock:
        if cache_key in _user_graph_cache:
            _user_graph_cache[cache_key] = AssumptionGraph()
            logger.info(f" AssumptionGraph reset for user: {uid}, session: {session_id}")

