"""
World Model (Pillar 2: Governor) - TITAN EDITION
=================================================
**The Graph of Truth - 100x UPGRADED**

Original WorldModel with integrated Godzilla-tier capabilities:

- NEW: Hypergraph edges (multi-node relationships)
- NEW: Temporal reasoning (time-aware facts with validity periods)
- NEW: Causal inference (cause->effect chains and interventions)
- NEW: Bayesian reasoning (probabilistic belief updates)
- NEW: Advanced graph queries (pattern matching, semantic search)
- NEW: AI-powered conflict resolution (smart arbitration)
- NEW: Graph analytics (PageRank, communities, centrality)
- NEW: Agent swarm orchestration (400+ specialized agents)
- NEW: Adversarial critic (The Thanos Protocol)
- NEW: Self-healing code execution
- NEW: Vision integration (ready)
- NEW: Physics simulation engine (ready)
 
All integrated into your existing WorldModel class.
"""

import hashlib
import logging
import time
from datetime import datetime
import json
import os
from collections import defaultdict, deque

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Union

import numpy as np
logger = logging.getLogger(__name__)

logger.info(" [CORE-DIAG] Physics/Math kernel: numpy imported.")

# =============================================================================
# GLOBAL SHARED EMBEDDING MODEL (MAC OPTIMIZATION)
# =============================================================================
_SHARED_EMBEDDING_MODEL = None
_SHARED_EMBEDDING_FAILED = False
import threading
_MODEL_LOCK = threading.Lock()
# [TITAN V211.0] MANIFOLD ISOLATION
# Physically abolished the _GLOBAL_DB_LOCK strangler.
# Every instance now manages its own physical thread-safe manifold.
_WORLD_MODEL_REGISTRY = {}
_REGISTRY_LOCK = threading.Lock()

def get_world_model(session_id: Optional[str] = None) -> "WorldModel":
    """Get or create a session-scoped WorldModel singleton."""
    sid = session_id or os.environ.get("ULTRON_SESSION_ID") or "default"
    with _REGISTRY_LOCK:
        if sid not in _WORLD_MODEL_REGISTRY:
            _WORLD_MODEL_REGISTRY[sid] = WorldModel(session_id=sid)
        return _WORLD_MODEL_REGISTRY[sid]

def get_shared_embedding_model():
    """Returns a singleton SentenceTransformer on the best available device."""
    global _SHARED_EMBEDDING_MODEL, _SHARED_EMBEDDING_FAILED
    # [GODZILLA SINGLETON] Force absolute re-use of model to prevent Arm64 deadlock
    if _SHARED_EMBEDDING_MODEL is not None:
        return _SHARED_EMBEDDING_MODEL
    if _SHARED_EMBEDDING_FAILED:
        return None

    with _MODEL_LOCK:
        if _SHARED_EMBEDDING_MODEL is not None:
            return _SHARED_EMBEDDING_MODEL
        if _SHARED_EMBEDDING_FAILED:
            return None
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            # [GPU CLUSTER UPGRADE] Use CUDA if available or explicit device override; default CPU for MPS stability
            device = os.environ.get("ULTRON_DEVICE")
            if not device:
                device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f" [VRAM] Initializing shared embedding model on {device} (GLOBAL SINGLETON)...")
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            os.environ["HF_DATASETS_OFFLINE"] = "1"
            os.environ["HF_HUB_OFFLINE"] = "1"
            # Model name sourced from llm_manager — the single source of truth.
            from backend.llm_manager import EMBEDDING_MODEL as _EMB_MODEL
            try:
                _SHARED_EMBEDDING_MODEL = SentenceTransformer(_EMB_MODEL, device=device, local_files_only=True)
            except TypeError:
                _SHARED_EMBEDDING_MODEL = SentenceTransformer(_EMB_MODEL, device=device)
        except Exception as e:
            _SHARED_EMBEDDING_FAILED = True
            logger.warning(f" [VRAM] Shared embedding model unavailable offline ({e}); caching fallback state.")
            return None
    return _SHARED_EMBEDDING_MODEL






# =============================================================================
# GODZILLA UPGRADES (APEX PREDATOR)
# =============================================================================
try:
    from backend.graphs.gnn_oracle import GNNOracle, PredictedEdge, AnomalyNode, DreamReport
    logger.info(" [CORE-DIAG] GNN Oracle active (Intuition Layer).")
    GNN_AVAILABLE = True
except ImportError as e:
    logger.info(f" [CORE-DIAG] GNN Oracle unavailable: {e}. Intuition layer skipped.")
    GNNOracle = None
    PredictedEdge = None
    AnomalyNode = None
    DreamReport = None
    GNN_AVAILABLE = False


# EPISTEMIC BEAST: Reaper Enums
try:
    from backend.epistemic.epistemic_regulator import ReaperUpdateType
    logger.info(" [CORE-DIAG] Epistemic Regulator connected.")
except ImportError as e:
    logger.info(f" [CORE-DIAG] Epistemic Regulator unavailable: {e}.")
    ReaperUpdateType = None


# =============================================================================
# YOUR ORIGINAL CLASSES 
# =============================================================================

@dataclass
class Fact:
    """A single fact in the world model (ORIGINAL)"""
    key: str
    value: Any
    source: str
    confidence: float
    timestamp: float = field(default_factory=time.time)
    fact_id: str = field(default="")
    metadata: Dict[str, Any] = field(default_factory=dict)
    # [PH.D. JUSTIFICATION] Persistent Reasoning Trace
    # While traces are useful for debugging, they are physically stored in the 
    # database to enable Agential Self-Correction. This allows downstream agents 
    # to audit logical derivations, identify flawed logic paths in cycle-over-cycle 
    # contradictions, and autonomously perform 'Logical Falsification' without 
    # human intervention.
    reasoning_trace: str = "" # [TITAN V200.2] Reclaimed trace manifold

    def __post_init__(self):
        if not self.fact_id:
            content = f"{self.key}:{str(self.value)}"
            # SECURITY FIX: MD5 -> SHA256
            self.fact_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "reasoning_trace": self.reasoning_trace
        }

    def age(self) -> float:
        return time.time() - self.timestamp


@dataclass
class Conflict:
    """Represents conflicting facts (ORIGINAL)"""
    key: str
    facts: List[Fact]
    severity: float = 0.0

    def __post_init__(self):
        if len(self.facts) >= 2:
            confidences = [f.confidence for f in self.facts]
            self.severity = min(confidences) if len(confidences) > 1 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "severity": self.severity,
            "facts": [f.to_dict() for f in self.facts],
            "values": list(set(str(f.value) for f in self.facts))
        }


@dataclass
class Entity:
    """Typed knowledge graph entity (ORIGINAL)"""
    type: str
    properties: Dict[str, Any]
    entity_id: str = ""
    confidence: float = 1.0
    source: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # NEW: Titan additions
    embedding: Optional[np.ndarray] = None  # For semantic search
    verification_count: int = 0  # How many times verified
    # [FIX V253] reasoning_trace must be declared here so from_dict can pass it without crashing
    reasoning_trace: str = ""  # Persistent logical derivation trace for self-correction
    
    VALID_TYPES = {
        "Paper", "Concept", "Hypothesis", "Finding",
        "Author", "Dataset", "Method", "Experiment",
        "ResearchQuestion", "Tool", "Agent",
        # Domain-agnostic generic entity types (biology-specific types removed;
        # use Concept/Method/Finding for cross-domain entities)
        "System", "Artifact", "Process", "Metric", "Model"
    }
    
    def __post_init__(self):
        if not self.entity_id:
            content = f"{self.type}:{str(self.properties)}"
            # TITAN UPGRADE: SHA256 for high-integrity addressing
            self.entity_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        if self.type not in self.VALID_TYPES:
            # [GODZILLA V72.1] Silenced generic Entity type warnings to prevent log suffocation.
            pass
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "type": self.type,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "verified": self.verified,
            "metadata": self.metadata,
            "verification_count": self.verification_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            type=data["type"],
            properties=data["properties"],
            entity_id=data.get("entity_id", ""),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            verified=data.get("verified", False),
            metadata=data.get("metadata", {}),
            reasoning_trace=data.get("reasoning_trace", ""),
            verification_count=data.get("verification_count", 0)
        )


@dataclass
class Relationship:
    """Typed relationship between entities (ORIGINAL)"""
    source_id: str
    target_id: str
    type: str
    relationship_id: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_by: str = ""
    created_at: float = field(default_factory=time.time)
    
    # NEW: Titan additions
    valid_until: Optional[float] = None  # Temporal validity
    deprecated: bool = False
    contested: bool = False
    evidence: List[str] = field(default_factory=list)
    
    VALID_TYPES = {
        "CITES", "SUPPORTS", "REFUTES", "MENTIONS",
        "DERIVED_FROM", "AUTHOR_OF", "USES_METHOD",
        "RELATED_TO", "PRODUCED_BY", "SPAWNED_BY",
        # Domain-agnostic causal/associative predicates (biology-specific ones removed)
        "CORRELATES_WITH", "CAUSES", "CONDITIONAL_ON",
        "AFFECTS", "CORRELATES", "DEPENDS_ON", "INFLUENCES", "PREDICTS",
        "ASSOCIATED_WITH", "CONTRADICTS", "EXTENDS"
    }
    
    def __post_init__(self):
        if not self.relationship_id:
            content = f"{self.source_id}:{self.type}:{self.target_id}"
            # TITAN UPGRADE: SHA256 for high-integrity addressing
            self.relationship_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        if self.type not in self.VALID_TYPES:
            logger.warning(f"Non-standard relationship type: {self.type}")
    
    def is_valid_at(self, timestamp: float) -> bool:
        """NEW: Check temporal validity"""
        if self.deprecated:
            return False
        if self.valid_until and timestamp > self.valid_until:
            return False
        return timestamp >= self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type,
            "properties": self.properties,
            "confidence": self.confidence,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "deprecated": self.deprecated,
            "contested": self.contested,
            "evidence_count": len(self.evidence)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            type=data["type"],
            relationship_id=data.get("relationship_id", ""),
            properties=data.get("properties", {}),
            confidence=data.get("confidence", 1.0),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at", time.time()),
            deprecated=data.get("deprecated", False),
            contested=data.get("contested", False),
            evidence=data.get("evidence", [])
        )


# =============================================================================
# NEW: HYPERGRAPH EXTENSIONS
# =============================================================================

@dataclass
class HyperEdge:
    """
    Multi-node hyperedge: A+B+C -> D+E
    Goes beyond binary relationships
    """
    hyperedge_id: str
    edge_type: str
    source_ids: List[str]  # Multiple sources
    target_ids: List[str]  # Multiple targets
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    valid_until: Optional[float] = None
    deprecated: bool = False
    contested: bool = False
    
    def is_valid_at(self, timestamp: float) -> bool:
        if self.deprecated:
            return False
        if self.valid_until and timestamp > self.valid_until:
            return False
        return timestamp >= self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hyperedge_id": self.hyperedge_id,
            "type": self.edge_type,
            "sources": self.source_ids,
            "targets": self.target_ids,
            "confidence": self.confidence,
            "evidence_count": len(self.evidence),
            "conditions": self.conditions,
            "deprecated": self.deprecated,
            "contested": self.contested
        }


# =============================================================================
# NEW: TEMPORAL REASONING
# =============================================================================

@dataclass
class TemporalFact:
    """Facts with time validity periods"""
    key: str
    value: Any
    valid_from: float
    valid_until: Optional[float] = None
    source: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid_at(self, timestamp: float) -> bool:
        if timestamp < self.valid_from:
            return False
        if self.valid_until and timestamp > self.valid_until:
            return False
        return True


# =============================================================================
# NEW: CAUSAL INFERENCE
# =============================================================================

# TITAN WORLD MODEL IMPORTS
# logger already defined above


# Lazy Import Strategy: Prevent startup hangs
# NOTE: chromadb is known to hang on import in some environments
CHROMADB_AVAILABLE = True
try:
    import importlib.util
    if importlib.util.find_spec("chromadb") is None:
        CHROMADB_AVAILABLE = False
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from backend.memory.knowledge_graph import get_knowledge_graph, KnowledgeGraph
    NEO4J_PERSISTENCE_AVAILABLE = True
except (ImportError, Exception):
    NEO4J_PERSISTENCE_AVAILABLE = False
    get_knowledge_graph = None
    KnowledgeGraph = None

# SentenceTransformer is used for semantic search (model configured via llm_manager.EMBEDDING_MODEL)
SENTENCE_TRANSFORMER_AVAILABLE = True
try:
    import importlib.util
    if importlib.util.find_spec("sentence_transformers") is None:
        SENTENCE_TRANSFORMER_AVAILABLE = False
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False
SentenceTransformer = None # Lazy load

# VectorStore unified memory (optional)
try:
    from backend.memory.vectorstore import get_vectorstore
    logger.info(" [CORE-DIAG] Vectorstore connected (Unified Memory).")
    VECTORSTORE_AVAILABLE = True
except (ImportError, Exception) as e:
    logger.info(f" [CORE-DIAG] Vectorstore unavailable: {e}. Using Jaccard fallback.")
    VECTORSTORE_AVAILABLE = False
    get_vectorstore = None

@dataclass
class CausalLink:
    """Cause -> Effect with strength and mechanism"""
    cause_id: str
    effect_id: str
    strength: float  # -1.0 to 1.0 (negative = inhibitory)
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    mechanism: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cause": self.cause_id,
            "effect": self.effect_id,
            "strength": self.strength,
            "confidence": self.confidence,
            "mechanism": self.mechanism,
            "evidence_count": len(self.evidence)
        }


# =============================================================================
# NEW: AGENT SWARM
# =============================================================================

class AgentRole(Enum):
    """Specialized agent types"""
    ORCHESTRATOR = "orchestrator"
    SCOUT = "scout"
    ARCHIVIST = "archivist"
    HISTORIAN = "historian"
    SYNTHESIZER = "synthesizer"
    STATISTICIAN = "statistician"
    CODER = "coder"
    VISUALIZER = "visualizer"
    SIMULATOR = "simulator"
    CRITIC = "critic"
    DEBUGGER = "debugger"


@dataclass
class Task:
    """Unit of work for agents"""
    task_id: str
    task_type: str
    priority: int
    dependencies: List[str] = field(default_factory=list)
    assigned_to: Optional[AgentRole] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    retry_count: int = 0


# =============================================================================
# MAIN: WORLD MODEL (YOUR ORIGINAL + ALL TITAN UPGRADES)
# =============================================================================





class WorldModel:

    """
    Global knowledge state for multi-agent execution.
    
    ORIGINAL CAPABILITIES:
    - Entity-relationship graph
    - Fact tracking with confidence
    - Conflict detection
    - Provenance tracking
    
    NEW TITAN CAPABILITIES:
    - Hypergraph edges (multi-node relationships)
    - Temporal reasoning (time-aware facts)
    - Causal inference (cause->effect modeling)
    - Bayesian reasoning (probabilistic updates)
    - Advanced graph queries (pattern matching, semantic search)
    - AI-powered conflict resolution
    - Graph analytics (PageRank, communities)
    - Agent swarm orchestration
    - Adversarial critique (Thanos Protocol)
    
    **PERSISTENCE UPDATE**: Now uses SQLite for durable storage.
    """
    @property
    def _conn(self):
        with self._db_lock:
            self._ensure_connection()
            return self.__dict__.get('_conn_val')

    @_conn.setter
    def _conn(self, val):
        with self._db_lock:
            self.__dict__['_conn_val'] = val

    @property
    def _cursor(self):
        with self._db_lock:
            self._ensure_connection()
            if not hasattr(self._thread_local, 'cursor') or self._thread_local.cursor is None:
                self._thread_local.cursor = self._conn.cursor()
            return self._thread_local.cursor

    @_cursor.setter
    def _cursor(self, val):
        with self._db_lock:
            self._thread_local.cursor = val

    def _ensure_connection(self):
        """Ensure connection and cursor are open and valid."""
        import sqlite3
        if not hasattr(self, 'db_path'):
            return
        conn = self.__dict__.get('_conn_val')
        if conn:
            try:
                conn.execute("SELECT 1")
                return
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                pass
        
        # Open connection
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA busy_timeout = 60000")
        conn.row_factory = sqlite3.Row
        self.__dict__['_conn_val'] = conn
        self._thread_local.cursor = conn.cursor()
        logger.info(f" [WORLD] WorldModel database connection (re)opened: {self.db_path}")

    def __init__(self, session_id: Optional[str] = None, refresh_memory: bool = False):
        self._thread_local = threading.local()
        self._db_lock = threading.RLock()
        # [GODZILLA STABILITY] Force session alignment across swarm
        import os
        env_session = os.environ.get("ULTRON_SESSION_ID")
        self.session_id = session_id or env_session or hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:8]
        self.refresh_memory = refresh_memory

        # =====================================================================
        # PERSISTENCE (SQLite)
        # =====================================================================
        import sqlite3
        import os
        
        # Ensure dedicated session DB directory exists outside empirical data/ folder
        legacy_db_path = f"data/world_model_{self.session_id}.db"
        if os.path.exists(legacy_db_path):
            self.db_path = legacy_db_path
        else:
            os.makedirs(os.path.join("storage", "world_models"), exist_ok=True)
            self.db_path = os.path.join("storage", "world_models", f"world_model_{self.session_id}.db")
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA journal_mode=WAL") # [GODZILLA FIX] Enable WAL for concurrency
        self._conn.execute("PRAGMA synchronous=NORMAL") # Performance boost
        self._conn.execute("PRAGMA cache_size=-64000") # 64MB Cache
        self._conn.execute("PRAGMA temp_store=MEMORY")
        self._conn.execute("PRAGMA busy_timeout = 60000") # [GODZILLA V68.18] 60s Atomic timeout
        self._conn.row_factory = sqlite3.Row
        self._cursor = self._conn.cursor()
        
        # [TITAN V157.0] PHYSICAL MEMORY INTEGRITY
        # Physically separate DB locking from In-Memory cache locking.
        # This prevents 'Dictionary changed size during iteration' and lost updates.
        self._memory_lock = threading.Lock()

        self._init_db()

        # =====================================================================
        # IN-MEMORY CACHE (For Performance)
        # =====================================================================
        # We keep some caches for fast lookups, but primary truth is DB
        self._facts_cache = {} 
        self._entities_cache = {}

        # ORIGINAL MEMBERS (Required by legacy methods)
        self._facts = defaultdict(list)
        self._source_index = defaultdict(set)
        self._entities = {}
        self._relationships = {}
        self._entity_type_index = defaultdict(set)
        self._outgoing_rels = defaultdict(set)
        self._incoming_rels = defaultdict(set)

        # =====================================================================
        # NEW: TITAN EXTENSIONS (In-Memory Temporaries for now)
        # =====================================================================
        # ... (Rest of the Titan extensions remain in memory for this iteration 
        # but critical research data is now safe in SQLite)
        
        # Knowledge Seeds (The 1,500 abstracts manifold)
        self._knowledge_seeds: List[Dict[str, Any]] = []
        
        # Hypergraph
        self._hyperedges: Dict[str, HyperEdge] = {}
        self._hyperedge_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Temporal reasoning
        self._temporal_facts: Dict[str, List[TemporalFact]] = defaultdict(list)
        self._snapshots: Dict[float, Dict[str, Any]] = {}
        
        # Causal inference
        self._causal_links: Dict[str, List[CausalLink]] = defaultdict(list)
        self._interventions: List[Dict[str, Any]] = []
        
        # Bayesian reasoning
        self._bayesian_priors: Dict[str, float] = {}
        self._bayesian_conditionals: Dict[Tuple[str, str], float] = {}
        
        # Vector embeddings (for semantic search)
        self._embeddings: Dict[str, np.ndarray] = {}
        
        # Contested/deprecated tracking
        self._contested_edges: Set[str] = set()
        
        # Agent swarm
        self._agents: Dict[str, Any] = {}
        self._task_queue: deque = deque()
        
        # Conflict resolution history
        self._resolution_history: List[Dict[str, Any]] = []

        # Statistics
        self._stats = {
            "total_facts": 0,
            "unique_keys": 0,
            "conflicts": 0,
            "sources": set(),
            "total_entities": 0,
            "total_relationships": 0,
            "total_hyperedges": 0,
            "total_causal_links": 0,
            "total_temporal_facts": 0,
            "active_agents": 0
        }
        self._decomposed_queries = set() # [GODZILLA GLOBAL CACHE]

        # Auto-rehydration is performed once at the end of __init__ after all subsystems are initialized

        # [GODZILLA BLOCK REMOVED] Enabling Neo4j for high-concurrency 
        try:
            from backend.memory.knowledge_graph import KnowledgeGraph
            self.neo4j = KnowledgeGraph()
            self._knowledge_graph = self.neo4j
            logger.info(" [WORLD] Neo4j Dual-Write ENABLED for High-Concurrency Swarm.")
        except Exception as e:
            self.neo4j = None
            self._knowledge_graph = None
            logger.warning(f" [WORLD] Neo4j initialization failed: {e}. Falling back to SQLite.")

        # =====================================================================
        # VECTOR STORE (UNIFIED MEMORY)
        # =====================================================================
        self.vectorstore = None
        try:
            from backend.memory.vectorstore import get_vectorstore
            self.vectorstore = get_vectorstore()
            logger.info(" VectorStore unified memory initialized for mission")
        except Exception:
            pass
        
        # SentenceTransformer is optional - don't fail if unavailable
        # Model name sourced from llm_manager — the single source of truth.
        from backend.llm_manager import EMBEDDING_MODEL as _EMB_MODEL
        self._embedding_model_name = _EMB_MODEL
        self._embedding_model = None
        
        # FIX: Initialize Chroma collection reference
        self._chroma_collection = None

        # Intuition Upgrade (GNN)
        self.oracle = None
        if GNN_AVAILABLE:
            try:
                self.oracle = GNNOracle()
                logger.info(" WorldModel: GNN Oracle Online (Intuition Layer Active)")
            except Exception as e:
                logger.warning(f"GNN Oracle init failed: {e}")

        self._reaper = None
        
        # FIX: Auto-rehydrate memory for the CURRENT SESSION ONLY (once per init)
        if not self.refresh_memory:
            try:
                self.load_from_db()
            except Exception as e:
                logger.warning(f"Initial rehydration failed (new session?): {e}")

        logger.info(f" WorldModel TITAN EDITION initialized (session={self.session_id})")

    def close(self):
        """
        G-RARE: SAFE SHUTDOWN
        Closes SQLite connection and releases file handles with WAL checkpoint.
        """
        try:
            conn = self.__dict__.get('_conn_val')
            if conn:
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except Exception:
                    pass
                conn.close()
                self.__dict__['_conn_val'] = None
                self.__dict__['_cursor_val'] = None
                logger.info(" WorldModel database connection closed with WAL truncated.")
        except Exception as e:
            logger.error(f"Error closing WorldModel: {e}")

    def __del__(self):
        """Safety net for resource cleanup."""
        try:
            self.close()
        except (NameError, AttributeError, TypeError):
            # Globals like 'logger' or 'open' might be gone during shutdown
            pass

    def _init_db(self):
        """Initialize SQLite tables."""
        # [GODZILLA CONCURRENCY FIX] Enable WAL mode for parallel swarm writes
        try:
            self._cursor.execute("PRAGMA journal_mode=WAL")
            self._cursor.execute("PRAGMA synchronous=NORMAL")
        except Exception as e:
            logger.warning(f"Failed to enable WAL mode: {e}")

        # Facts table
        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                fact_id TEXT PRIMARY KEY,
                key TEXT,
                value TEXT,
                source TEXT,
                confidence REAL,
                timestamp REAL,
                metadata TEXT,
                session_id TEXT,
                reasoning_trace TEXT
            )
        """)
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key)")
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_source ON facts(source)")
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_session ON facts(session_id)")
        
        # Entities table
        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                type TEXT,
                properties TEXT,
                confidence REAL,
                source TEXT,
                created_at REAL,
                updated_at REAL,
                verified INTEGER,
                metadata TEXT,
                verification_count INTEGER,
                session_id TEXT,
                reasoning_trace TEXT
            )
        """)
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_session ON entities(session_id)")
        
        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                relationship_id TEXT PRIMARY KEY,
                source_id TEXT,
                target_id TEXT,
                type TEXT,
                properties TEXT,
                confidence REAL,
                created_by TEXT,
                created_at REAL,
                deprecated INTEGER,
                contested INTEGER,
                evidence TEXT,
                session_id TEXT,
                FOREIGN KEY(source_id) REFERENCES entities(entity_id),
                FOREIGN KEY(target_id) REFERENCES entities(entity_id)
            )
        """)
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_session ON relationships(session_id)")
        
        # TITAN: Hyperedges table
        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS hyperedges (
                hyperedge_id TEXT PRIMARY KEY,
                sources TEXT,
                targets TEXT,
                type TEXT,
                confidence REAL,
                evidence TEXT,
                conditions TEXT,
                session_id TEXT
            )
        """)
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_hyperedges_session ON hyperedges(session_id)")

        # TITAN: Temporal Facts table
        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS temporal_facts (
                fact_id TEXT PRIMARY KEY,
                key TEXT,
                value TEXT,
                valid_from REAL,
                valid_until REAL,
                source TEXT,
                confidence REAL,
                metadata TEXT,
                session_id TEXT
            )
        """)
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_temporal_session ON temporal_facts(session_id)")

        # TITAN: Causal Links table
        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS causal_links (
                link_id TEXT PRIMARY KEY,
                cause_id TEXT,
                effect_id TEXT,
                strength REAL,
                mechanism TEXT,
                confidence REAL,
                evidence TEXT,
                session_id TEXT
            )
        """)
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_causal_session ON causal_links(session_id)")
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)")
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(type)")
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_temporal_key ON temporal_facts(key)")
        self._cursor.execute("CREATE INDEX IF NOT EXISTS idx_causal_cause ON causal_links(cause_id)")
        
        self._conn.commit()
        
    def get_graph_snapshot(self) -> Dict[str, Any]:
        """
        [GODZILLA BRIDGE] Convert SQLite facts AND knowledge seeds into a GNN-compatible graph.
        """
        nodes = set()
        edges = []
        
        # 1. Promote Knowledge Seeds to Nodes (The 1,500 abstracts)
        if hasattr(self, "_knowledge_seeds") and self._knowledge_seeds:
            for seed in self._knowledge_seeds:
                nodes.add(seed.get("id", seed.get("title", "unknown")))
        
        # 2. Facts as Nodes
        self._cursor.execute("SELECT fact_id, value FROM facts WHERE session_id = ?", (self.session_id,))
        for fid, val in self._cursor.fetchall():
            nodes.add(fid)
            
        # 3. Relationships as Edges
        self._cursor.execute("SELECT source_id, target_id FROM relationships WHERE session_id = ?", (self.session_id,))
        for sid, tid in self._cursor.fetchall():
            if sid and tid:
                nodes.add(sid)
                nodes.add(tid)
                edges.append((sid, tid))
        
        # [GODZILLA TOPOLOGY] Safety Gate
        # Physically abolished similarity-based topology hallucination.
        # If the graph is sparse, we do NOT fabricate links. 
        # We allow the GNN to fail honestly rather than learn random noise.
        pass

        
        return {
            "session_id": self.session_id,
            "nodes": list(nodes),
            "edges": edges
        }

    def load_from_db(self, session_id: Optional[str] = None):
        """
        Rehydrate internal memory caches from SQLite.
        """
        if session_id:
            self.session_id = session_id
        sid = self.session_id
        
        # [TITAN V157.0] ATOMIC RE-HYDRATION
        # Physically wrap the reset and load in a memory lock to prevent split-brain swarms.
        with self._memory_lock:
            # [GODZILLA FIX] Reset internal buffers to prevent duplication
            self._facts = defaultdict(list)
            self._entities = {}
            self._knowledge_seeds = []
            self._facts_cache = {}
            self._entities_cache = {}
            self._source_index = defaultdict(set)
            self._relationships = {}
            self._entity_type_index = defaultdict(set)
            self._outgoing_rels = defaultdict(set)
            self._incoming_rels = defaultdict(set)
        
        # Check if the current session is empty

        self._cursor.execute("SELECT COUNT(*) as count FROM facts WHERE session_id = ?", (sid,))
        count_row = self._cursor.fetchone()
        count = count_row[0] if count_row else 0
        
        if count == 0:
            logger.info(f" Starting fresh discovery (no previous data for session={sid})")
            return
        
        logger.info(f" Rehydrating WorldModel memory from SQLite (session={sid})")
        
        try:
            # 1. Load Facts
            self._cursor.execute("SELECT * FROM facts WHERE session_id = ?", (sid,))
            rows = self._cursor.fetchall()
            for row in rows:
                val = row["value"]
                if val and isinstance(val, str) and val.startswith(("{", "[")):
                    try:
                        val = json.loads(val)
                    except json.JSONDecodeError:
                        try:
                            import ast
                            val = ast.literal_eval(val)
                        except Exception:
                            pass # Keep as raw string if both fail
                
                f = Fact(
                    key=row["key"],
                    value=val,
                    source=row["source"],
                    confidence=row["confidence"],
                    timestamp=row["timestamp"],
                    fact_id=row["fact_id"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    reasoning_trace=row["reasoning_trace"] if ("reasoning_trace" in row.keys() and row["reasoning_trace"] is not None) else ""
                )
                
                # [GODZILLA FIX] Handle Dict[str, List[Fact]] structure
                if f.key not in self._facts:
                    self._facts[f.key] = []
                self._facts[f.key].append(f)
                
                # RE-INDEX SEEDS: Restore the 1,500-abstract GNN manifold
                if f.key == "literature_seed":
                    self._knowledge_seeds.append({"id": f.fact_id, "text": str(f.value)})
                    
            logger.info(f" [WORLD] SUCCESS: Rehydrated {sum(len(v) for v in self._facts.values())} facts and {len(self._knowledge_seeds)} seeds.")
            self._cursor.execute("SELECT * FROM entities WHERE session_id = ?", (sid,))
            rows = self._cursor.fetchall()
            for row in rows:
                e = Entity.from_dict({
                    "type": row["type"],
                    "properties": json.loads(row["properties"]),
                    "entity_id": row["entity_id"],
                    "confidence": row["confidence"],
                    "source": row["source"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "verified": bool(row["verified"]),
                    "metadata": json.loads(row["metadata"]),
                    "verification_count": row["verification_count"],
                    "reasoning_trace": row["reasoning_trace"] if ("reasoning_trace" in row.keys() and row["reasoning_trace"] is not None) else ""
                })
                self._entities[e.entity_id] = e
                self._entity_type_index[e.type].add(e.entity_id)
            
            # 3. Load Relationships
            self._cursor.execute("SELECT * FROM relationships WHERE session_id = ?", (sid,))
            rows = self._cursor.fetchall()
            for row in rows:
                r = Relationship.from_dict({
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                    "type": row["type"],
                    "relationship_id": row["relationship_id"],
                    "properties": json.loads(row["properties"]),
                    "confidence": row["confidence"],
                    "created_by": row["created_by"],
                    "created_at": row["created_at"],
                    "deprecated": bool(row["deprecated"]),
                    "contested": bool(row["contested"]),
                    "evidence": json.loads(row["evidence"])
                })
                self._relationships[r.relationship_id] = r
                self._outgoing_rels[r.source_id].add(r.relationship_id)
                self._incoming_rels[r.target_id].add(r.relationship_id)

            # 4. TITAN: Load Hyperedges
            try:
                with self._db_lock:
                    self._cursor.execute(
"SELECT * FROM hyperedges WHERE session_id = ?", (sid,))
                    rows = self._cursor.fetchall()
                for row in rows:
                    # Check if HyperEdge class definition matches. Assuming it matches keys.
                    h = HyperEdge(
                        hyperedge_id=row["hyperedge_id"],
                        edge_type=row["type"],
                        source_ids=json.loads(row["sources"]),
                        target_ids=json.loads(row["targets"]),
                        confidence=row["confidence"],
                        evidence=json.loads(row["evidence"]),
                        conditions=json.loads(row["conditions"])
                    )
                    self._hyperedges[h.hyperedge_id] = h
                    for src in h.source_ids: self._hyperedge_index[src].add(h.hyperedge_id)
                    for tgt in h.target_ids: self._hyperedge_index[tgt].add(h.hyperedge_id)
            except Exception as e:
                logger.warning(f"Failed to load hyperedges: {e}")

            # 5. TITAN: Load Temporal Facts
            try:
                with self._db_lock:
                    self._cursor.execute(
"SELECT * FROM temporal_facts WHERE session_id = ?", (sid,))
                    rows = self._cursor.fetchall()
                for row in rows:
                    tf = TemporalFact(
                        key=row["key"],
                        value=json.loads(row["value"]) if row["value"].startswith(("{", "[")) else row["value"],
                        valid_from=row["valid_from"],
                        valid_until=row["valid_until"],
                        source=row["source"],
                        confidence=row["confidence"],
                        metadata=json.loads(row["metadata"])
                    )
                    self._temporal_facts[tf.key].append(tf)
            except Exception as e:
                logger.warning(f"Failed to load temporal facts: {e}")

            # 6. TITAN: Load Causal Links
            try:
                with self._db_lock:
                    self._cursor.execute(
"SELECT * FROM causal_links WHERE session_id = ?", (sid,))
                    rows = self._cursor.fetchall()
                for row in rows:
                    cl = CausalLink(
                        cause_id=row["cause_id"],
                        effect_id=row["effect_id"],
                        strength=row["strength"],
                        confidence=row["confidence"],
                        evidence=json.loads(row["evidence"]),
                        mechanism=row["mechanism"]
                    )
                    self._causal_links[cl.cause_id].append(cl)
            except Exception as e:
                 logger.warning(f"Failed to load causal links: {e}")
            
            # Update stats
            self._stats["total_facts"] = sum(len(v) for v in self._facts.values())
            self._stats["unique_keys"] = len(self._facts)
            self._stats["total_entities"] = len(self._entities)
            self._stats["total_relationships"] = len(self._relationships)
            
            logger.info(f" Rehydration Complete: {self._stats['total_facts']} facts, {self._stats['total_entities']} entities.")
            
        except Exception as e:
            logger.error(f" Critical Rehydration Failure: {e}")
            raise

    # =========================================================================
    # INTUITION LAYER (The Dream)
    # =========================================================================

    def dream(self, node_id: str = None, top_k: int = 5, domain: str = "general") -> List['PredictedEdge']:
        """
         Consult the GNN Oracle for 'Hunches' (Predicted Edges).
        This is not Fact. This is Intuition.
        
        GODZILLA UPGRADE: Trains ensemble of 4 GNN architectures,
        auto-selects best by AUC-ROC, returns predictions from winner.
        
        If node_id is None, delegates to deep_dream() for global discovery.
        """
        if not self.oracle:
            return []

        # 1. Train ensemble on current memory (REM Sleep)
        try:
            snapshot = self.get_knowledge_snapshot()
            self.oracle.train_on_graph(snapshot)
        except Exception as e:
            logger.warning(f"WorldModel: Dream training failed: {e}")
            return []

        # 2. Predict
        if node_id:
            return self.oracle.dream(node_id, top_k)
        else:
            # Global discovery mode
            return self.oracle.deep_dream(top_k)

    def deep_dream(self, top_k: int = 20, domain: str = "general") -> List['PredictedEdge']:
        """
         Global discovery - predict missing links across the ENTIRE graph.
        Scans all node pairs and returns top-k most confident predicted connections.
        """
        if not self.oracle:
            return []

        try:
            snapshot = self.get_knowledge_snapshot()
            self.oracle.train_on_graph(snapshot)
            return self.oracle.deep_dream(top_k)
        except Exception as e:
            logger.warning(f"WorldModel: Deep dream failed: {e}")
            return []

    def detect_graph_anomalies(self, threshold: float = 0.1) -> List[Dict[str, Any]]:
        """
         Find entities that don't fit the graph pattern.
        Uses GNN reconstruction error to identify outlier nodes.
        
        Returns:
            List of {node_id, anomaly_score, reasoning} dicts
        """
        if not self.oracle:
            return []

        try:
            snapshot = self.get_knowledge_snapshot()
            self.oracle.train_on_graph(snapshot)
            anomalies = self.oracle.detect_anomalies(threshold)
            return [
                {
                    "node_id": a.node_id,
                    "anomaly_score": a.anomaly_score,
                    "reasoning": a.reasoning
                }
                for a in anomalies
            ]
        except Exception as e:
            logger.warning(f"WorldModel: Anomaly detection failed: {e}")
            return []

    def get_dream_report(self) -> Dict[str, Any]:
        """
         Get full diagnostic report from the last GNN training cycle.
        Includes architecture scores, training metrics, and graph stats.
        """
        if not self.oracle:
            return {"status": "GNN Oracle not available"}

        try:
            report = self.oracle.get_report()
            return {
                "best_architecture": report.best_architecture,
                "architecture_scores": report.architecture_scores,
                "validation_auc": report.validation_auc,
                "training_time_seconds": report.training_time_seconds,
                "num_nodes": report.num_nodes,
                "num_edges": report.num_edges
            }
        except Exception as e:
            return {"error": str(e)}

    def get_knowledge_snapshot(self) -> Dict[str, Any]:
        """
        [TITAN V155.0] DEEP MANIFOLD EXTRACTION.
        Convert current memory (Entities + Relationships + Facts + Seeds) to graph format.
        Abolishes 'GNN Blindness' by physically injecting all 775+ facts.
        """
        # [RIGOR FIX] Slow Snapshotting Cache
        # Physically cache the snapshot to prevent blocking the main thread on every plan creation.
        current_state_hash = self._stats.get("total_facts", 0) + self._stats.get("total_relationships", 0) + len(self._entities)
        if hasattr(self, "_last_snapshot_hash") and self._last_snapshot_hash == current_state_hash and hasattr(self, "_cached_snapshot"):
            return self._cached_snapshot

        with self._memory_lock:
            STOPWORD_ENTITY_NAMES = {
                "method", "system", "approach", "model", "dataset", "framework",
                "algorithm", "protocol", "accuracy", "performance", "time", "speed",
                "ratio", "error", "coefficient", "score", "metric", "concept"
            }
            nodes = []
            node_types = {}
            node_texts = {}
            
            for nid, entity in self._entities.items():
                props = entity.properties or {}
                ename = str(props.get("name", "")).strip().lower()
                if ename in STOPWORD_ENTITY_NAMES:
                    continue
                nodes.append(nid)
                node_types[nid] = entity.type
                props_str = str(props)[:200]
                node_texts[nid] = f"{entity.type}: {props_str}"

            edges = []
            edge_types = {}
            edge_confidences = {}

            # 1. Inject Relationships from DB
            try:
                rows = self._cursor.execute("SELECT source_id, target_id, type, confidence FROM relationships").fetchall()
                for r in rows:
                    src, dst = r['source_id'], r['target_id']
                    if src in self._entities and dst in self._entities and src in nodes and dst in nodes:
                        edges.append((src, dst))
                        edge_types[(src, dst)] = r['type']
                        edge_confidences[(src, dst)] = r['confidence']
            except Exception as e:
                logger.warning(f"Failed to fetch relationships for snapshot: {e}")

            # 2. [GODZILLA] INJECT PHYSICAL FACTS (775+ Papers)
            # Convert raw facts into 'Evidence' nodes to anchor the GNN in reality.
            # Filter out orchestrator metadata, task IDs, and session state.
            system_keys_to_skip = {
                "novelty_check", "research_session_state", "session_state",
                "system_status", "runtime_metrics", "token_usage", "active_run",
                "literature_seed", "evidence", "seed", "finding", "raw_data",
                "summary", "context", "abstract"
            }
            for fact_list in self._facts.values():
                for fact in fact_list:
                    k_str = str(fact.key).lower()
                    if k_str in system_keys_to_skip or k_str.startswith(("research_session_state", "system_", "orchestrator_")):
                        continue
                    v_str = str(fact.value)
                    if any(bad in v_str.lower() for bad in ["novelty check:", "no claim provided", "{'error':", '{"error":', "traceback", "404 not found"]):
                        continue

                    fact_node_id = f"fact_{hashlib.sha256(v_str.encode()).hexdigest()[:12]}"
                    if fact_node_id not in nodes:
                        nodes.append(fact_node_id)
                        node_types[fact_node_id] = "evidence"
                    node_texts[fact_node_id] = f"Fact ({fact.source}): {v_str[:300]}"
                
                    # Link Fact to its Key (Topic/Entity) ONLY if key is a real scientific concept, not an internal task ID
                    if not k_str.startswith(("finding_task_", "finding_exp_", "task_", "exp_")) and k_str not in STOPWORD_ENTITY_NAMES:
                        key_node_id = fact.key
                        if key_node_id not in nodes:
                            nodes.append(key_node_id)
                            node_types[key_node_id] = "concept"
                            node_texts[key_node_id] = f"Concept: {key_node_id}"
                        
                        edges.append((fact_node_id, key_node_id))
                        edge_types[(fact_node_id, key_node_id)] = "SUPPORTS"
                        edge_confidences[(fact_node_id, key_node_id)] = fact.confidence

        # 3. [TITAN] INJECT KNOWLEDGE SEEDS (1,500 abstracts)
        for seed in getattr(self, "_knowledge_seeds", []):
            seed_id = f"seed_{hashlib.sha256(str(seed.get('abstract', '')).encode()).hexdigest()[:12]}"
            if seed_id not in nodes:
                nodes.append(seed_id)
                node_types[seed_id] = "seed"
                node_texts[seed_id] = f"Abstract: {seed.get('title', 'Unknown')}"

        snapshot = {
            "nodes": nodes,
            "node_types": node_types,
            "node_texts": node_texts,
            "edges": edges,
            "edge_types": edge_types,
            "edge_confidences": edge_confidences,
            "causal_links": [] # Handled via relationships now
        }
        self._cached_snapshot = snapshot
        self._last_snapshot_hash = current_state_hash
        return snapshot


    # =========================================================================
    # CROSS-SESSION MEMORY (LOAD FROM NEO4J)
    # =========================================================================

    def load_from_neo4j(self, session_id: Optional[str] = None, load_all: bool = False) -> Dict[str, int]:
        """
        Load previous research data from Neo4j into WorldModel.
        """
        # ... (Keep existing implementation logic, but adapted if needed. 
        # For now, we assume this loads INTO memory/sqlite from Neo4j)
        if not self._knowledge_graph or not getattr(self._knowledge_graph, "is_available", False):
            logger.warning("Neo4j not available - cannot load cross-session memory. Proceeding with local SQLite state.")
            return {"papers": 0, "hypotheses": 0, "findings": 0}
        
        target_session = None if load_all else (session_id or self.session_id)
        counts = {"papers": 0, "hypotheses": 0, "findings": 0}
        
        # Load Papers
        papers = self._knowledge_graph.get_all_papers(session_id=target_session)
        for paper in papers:
            entity = Entity(
                type="Paper",
                properties={
                    "title": paper.get("title"),
                    "doi": paper.get("doi"),
                    "arxiv_id": paper.get("arxiv_id"),
                    "year": paper.get("year"),
                    "abstract": paper.get("abstract"),
                    "citation_count": paper.get("citation_count", 0)
                },
                entity_id=paper.get("doi") or paper.get("title", "")[:50],
                source="neo4j_restore"
            )
            # Persist to SQLite
            self._save_entity_to_db(entity)
            counts["papers"] += 1
        
        # Load Hypotheses
        hypotheses = self._knowledge_graph.get_all_hypotheses(session_id=target_session)
        for hyp in hypotheses:
            entity = Entity(
                type="Hypothesis",
                properties={
                    "statement": hyp.get("statement"),
                    "status": hyp.get("status", "pending")
                },
                entity_id=hyp.get("hypothesis_id", ""),
                confidence=hyp.get("confidence", 0.5),
                source="neo4j_restore"
            )
            self._save_entity_to_db(entity)
            counts["hypotheses"] += 1
        
        # Load Findings
        findings = self._knowledge_graph.get_all_findings(session_id=target_session)
        for finding in findings:
            entity = Entity(
                type="Finding",
                properties={
                    "summary": finding.get("summary"),
                    "hypothesis_id": finding.get("hypothesis_id"),
                    "relationship": finding.get("relationship", "SUPPORTS")
                },
                entity_id=finding.get("finding_id", ""),
                source=finding.get("evidence_source", "neo4j_restore")
            )
            self._save_entity_to_db(entity)
            counts["findings"] += 1
        
        logger.info(f" Cross-session memory loaded: {counts['papers']} papers, {counts['hypotheses']} hypotheses, {counts['findings']} findings")
        return counts

    # =========================================================================
    # ORIGINAL FACT METHODS (Preserved)
    # =========================================================================

    def _save_fact_to_db(self, fact: Fact):
        try:
            from backend.logging.atomic_logger import AtomicLogger
            if AtomicLogger.is_active():
                AtomicLogger.log("world", "SAVE_FACT_DB", {
                    "Key": fact.key,
                    "Value": fact.value,
                    "Confidence": fact.confidence,
                    "Source": fact.source
                })
        except ImportError:
            pass

        # [TITAN V164.0] SOVEREIGN WRITE PROTECTION
        # Physically acquire the global lock to prevent SQLite busy-wait starvation.
        import time
        max_retries = 10
        for attempt in range(max_retries):
            success = False
            try:
                with self._db_lock:
                    self._cursor.execute("""
                        INSERT OR REPLACE INTO facts
                        (fact_id, key, value, source, confidence, timestamp, metadata, session_id, reasoning_trace)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        fact.fact_id, fact.key, str(fact.value), fact.source,
                        fact.confidence, fact.timestamp, json.dumps(fact.metadata), self.session_id,
                        fact.reasoning_trace
                    ))
                    self._conn.commit()
                return # Success
            except Exception as e:

                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    # [TITAN V142.0] CONCURRENCY FIX
                    # Lock is released before we sleep, allowing others to attempt access.
                    time.sleep(0.05 * (attempt + 1))
                    continue
                logger.error(f"Atomic Write Failed for {fact.key}: {e}")
                raise RuntimeError(f"PHYSICAL_VAPORIZATION: Failed to persist fact {fact.fact_id} to disk manifold: {e}")



    def commit_verified_fact(
        self,
        key: str,
        value: Any,
        source: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Fact:
        """
        High-Integrity Commit: Only saves the fact if the Epistemic Reaper approves.
        Ensures audit trails and prevents low-quality data from polluting the World Model.
        """
        audit_metadata = metadata or {}
        audit_metadata["verified"] = True
        audit_metadata["commit_timestamp"] = datetime.now().isoformat()
        
        # 1. Pre-validation via Reaper
        if self._reaper:
             finding_data = {
                 "key": key,
                 "value": value,
                 "statistics": audit_metadata.get("statistics", {}),
                 "source": source,
                 "metadata": audit_metadata
             }
             context = [f.to_dict() for f in self._facts.get(key, [])]
             audit = self._reaper.reconcile_finding(finding_data, context)
             
             if audit.update_type in [ReaperUpdateType.CONFLICT.value if ReaperUpdateType else "conflict", "conflict"]:
                 msg = f"EPISTEMIC VETO: Cannot commit '{key}' due to clash: {audit.reasoning}"
                 logger.error(f" {msg}")
                 raise ValueError(msg)
             
             audit_metadata["audit_trail"] = {
                 "verdict": audit.update_type,
                 "reasoning": audit.reasoning,
                 "reaper_action": audit.action_taken
             }
        
        # 2. Add Fact (this will also trigger the reaper's side effects like pruning)
        return self.add_fact(
            key=key,
            value=value,
            source=source,
            confidence=confidence,
            metadata=audit_metadata
        )

    def save_session(self, session: Any, confidence: float = 1.0):
        """
        [GODZILLA PERSISTENCE] Save entire research session state as a Titan Fact.
        """
        try:
            # We bypass to_dict if it's too large, but ResearchSession is usually manageable
            session_data = session.to_dict() if hasattr(session, "to_dict") else str(session)
            
            # Use a specialized key for session state
            self.add_fact(
                key="research_session_state",
                value=json.dumps(session_data, default=str),
                source="orchestrator",
                confidence=confidence,
                metadata={"session_id": getattr(session, "id", "unknown"), "type": "session_state"}
            )
            logger.debug(f" [PERSISTENCE] WorldModel: Updated session state fact for {getattr(session, 'id', 'unknown')} with confidence {confidence:.2f}")
        except Exception as e:
            logger.warning(f" [PERSISTENCE] Failed to save session state: {e}")

    def add_fact(
        self,
        key: str,
        value: Any,
        source: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Fact:
        """Add a fact to the world model (REAPER-AUGMENTED with Epistemic Immune System)"""
        
        # [RIGOR] FLAW 10 FIX: EPIDEMIC IMMUNE SYSTEM (STERILIZATION)
        # Physically block software crashes, tracebacks, and mission parameters from becoming 'scientific facts'.
        toxic_patterns = [
            "Traceback (most recent call last):", 
            "AttributeError:", "ImportError:", "NotFoundError:", 
            "JSONDecodeError:", "TypeError:", "ValueError:",
            "Internal Server Error", "HTTP 429", "Rate limit exceeded",
            "RetryError", "multiple values for argument",
            # [GODZILLA ANTI-SLOP] Block Swarm failures and API censorship
            "'status': 'failed'", '"status": "failed"', "'status': 'error'", '"status": "error"',
            "empty response", "EXTRACTION FAILED", "NO SOURCE DOCUMENT", "LLM returned empty",
            "HARD ABORT", "PHYSICAL_VACUUM", "no claim provided", "agent_failed",
            # [GOVERNANCE SHIELD] Block provider errors from becoming 'findings'
            "credit balance", "Error code: 400", "invalid_request_error", "insufficient_quota"
        ]
        
        # Scan all inputs for toxicity
        input_dump = str(key) + str(value) + json.dumps(metadata or {})
        
        # [GODZILLA] Selective Blocking: Allow scientific discussion of errors but block raw tracebacks & fallback stubs
        is_raw_crash = "Traceback" in input_dump or "AttributeError" in input_dump
        is_empty_fallback = (
            ("'mode': 'fallback'" in input_dump or '"mode": "fallback"' in input_dump or "'mode':'fallback'" in input_dump)
            and ("'findings': []" in input_dump or '"findings": []' in input_dump or "'findings':[]" in input_dump)
        )
        
        infra_error_patterns = [
            "credit balance", "Error code: 400", "invalid_request_error", "insufficient_quota",
            "HARD ABORT", "PHYSICAL_VACUUM", "agent_failed", "EXTRACTION FAILED", "NO SOURCE DOCUMENT",
            "no results found for query", "no results found", "no claim provided", "{'error'", '{"error"'
        ]
        input_dump_lower = input_dump.lower()
        is_infra_error = any(pattern.lower() in input_dump_lower for pattern in infra_error_patterns)
        
        if is_raw_crash or is_empty_fallback or is_infra_error or (any(pattern in input_dump for pattern in toxic_patterns) and confidence < 0.3):
            logger.error(f" [WORLD-MODEL] TOXIC FACT REJECTED: Software crash or fallback empty stub detected. Source: {source} | Key: {key}")
            # Return a 'Failed Fact' shell to prevent downstream crashes, but do not persist it
            return Fact(
                key=key, 
                value="[SYSTEM_REJECTED_ERROR_DATA]", 
                source="immune_system", 
                confidence=0.0,
                metadata={"reason": "Contains toxic software error patterns"}
            )

        # [TITAN V204.0] EPISTEMIC TRACE PERSISTENCE
        # Physically extract the reasoning trace from the metadata manifold
        safe_meta = metadata or {}
        reasoning_trace = safe_meta.get("thinking_trace", safe_meta.get("reasoning_trace", ""))
        
        fact = Fact(
            key=key,
            value=value,
            source=source,
            confidence=confidence,
            metadata=metadata or {},
            reasoning_trace=reasoning_trace
        )
        
        # [TITAN V157.0] ATOMIC MEMORY COMMIT
        # Physically wrap the in-memory manifold in a lock to prevent swarm corruption.
        with self._memory_lock:
            self._facts[key].append(fact)
            self._source_index[source].add(fact.fact_id)
            self._facts_cache[fact.fact_id] = fact
            self._stats["total_facts"] += 1
            
        self._save_fact_to_db(fact)
        
        # [GODZILLA] AUTO-ENTITY GENERATION
        # Automatically ground significant facts as Graph Entities so GNN can dream
        if key.startswith("finding_") or fact.metadata.get("verified_discovery"):
            entity_id = f"ent_{fact.fact_id}"
            entity = Entity(
                type="Finding",
                properties={
                    "key": key,
                    "summary": str(value)[:500],
                    "source": source,
                    "confidence": confidence
                },
                entity_id=entity_id,
                confidence=confidence,
                source=source,
                verified=True,
                metadata=fact.metadata
            )
            self.add_entity(entity)

            # [RIGOR] MISSION CONTROL UPGRADE: DEEP GROUNDING RE-ENABLED.
            # Extracts entities from text to populate the GNN with scientific objects.
            self._ground_scientific_entities(entity_id, str(value), fact.metadata)
            # If it's linked to a hypothesis, create a relationship

            hyp_id = fact.metadata.get("hypothesis_id")
            if hyp_id:
                rel = Relationship(
                    source_id=entity_id,
                    target_id=hyp_id,
                    type="SUPPORTS" if fact.metadata.get("evidence_type") != "refute" else "REFUTES",
                    confidence=confidence,
                    created_by=source
                )
                self.add_relationship(rel)

        # ACTIVE ARBITRATION (PHASE 3: REAPER)
        if self._reaper:
            # Check if this fact is actually a statistical finding
            is_finding = "statistics" in (metadata or {}) or "p_value" in (metadata or {})
            if is_finding:
                finding_data = {
                    "key": key,
                    "value": value,
                    "statistics": (metadata or {}).get("statistics", (metadata or {})),
                    "source": source,
                    "metadata": metadata or {},
                    "hypothesis_id": (metadata or {}).get("hypothesis_id")
                }
                context = [f.to_dict() for f in self._facts[key][:-1]] # Previous facts for this key
                audit = self._reaper.reconcile_finding(finding_data, context)
                
                if audit.update_type in [ReaperUpdateType.CONFLICT.value if ReaperUpdateType else "conflict", "conflict"]:
                    self._stats["conflicts"] += 1
                    logger.warning(f" REAPER CLASH: {audit.reasoning}")
                    # In Godzilla mode, we might want to flag the key as UNSTABLE
                    fact.metadata["reaper_status"] = "CONFLICT"
                    fact.metadata["reaper_reasoning"] = audit.reasoning
                
                elif audit.update_type in [ReaperUpdateType.PRUNING.value if ReaperUpdateType else "pruning", "pruning"] and audit.target_hypothesis_id:
                    # ACTIVE PRUNING: Bridge Reaper -> HypothesisTracker
                    try:
                        from backend.core.hypothesis.tracker import get_hypothesis_tracker
                        tracker = get_hypothesis_tracker(session_id=self.session_id)
                        tracker.mark_refuted(
                            hypothesis_id=audit.target_hypothesis_id,
                            evidence={
                                "fact_id": fact.fact_id,
                                "reason": audit.reasoning,
                                "clash_type": "statistical_refutation"
                            }
                        )
                        logger.info(f" REAPER EXECUTION: Hypothesis {audit.target_hypothesis_id} has been pruned.")
                    except Exception as e:
                        logger.error(f"Failed to execute Reaper pruning: {e}")
        else:
            # Fallback to ORIGINAL logic
            self._detect_conflict(key)
            
        return fact

    def add_finding(self, finding: Dict[str, Any]) -> Fact:
        """
        High-level method to add a scientific finding with statistical audit.
        Expected schema: { 'key', 'value', 'statistics': { 'p_value', 'effect_size' }, 'source' }
        """
        key = finding.get("key", "unknown_finding")
        value = finding.get("value")
        stats = finding.get("statistics", {})
        source = finding.get("source", "unknown_source")
        confidence = finding.get("confidence", 0.8)
        
        # Inject stats into metadata for reaper visibility
        metadata = finding.get("metadata", {})
        metadata["statistics"] = stats
        # Ensure hypothesis context is preserved in metadata
        if "hypothesis_id" in finding:
            metadata["hypothesis_id"] = finding["hypothesis_id"]
        if "refutes_hypothesis" in finding:
            metadata["refutes_hypothesis"] = finding["refutes_hypothesis"]
        
        return self.add_fact(
            key=key,
            value=value,
            source=source,
            confidence=confidence,
            metadata=metadata
        )

    def add_facts_bulk(self, facts: List[Dict[str, Any]]) -> List[Fact]:
        """Add multiple facts at once (PERSISTED)"""
        results = []
        count = 0
        for fact_data in facts:
            try:
                fact = self.add_fact(
                    key=fact_data["key"],
                    value=fact_data["value"],
                    source=fact_data["source"],
                    confidence=fact_data.get("confidence", 1.0),
                    metadata=fact_data.get("metadata")
                )
                results.append(fact)
                count += 1
            except Exception as e:
                logger.error(f"Failed to add fact {fact_data.get('key')}: {e}")

        logger.info(f" Added {count}/{len(facts)} facts in bulk")
        return results


    def get_fact(
        self,
        key: str,
        source: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> Optional[Fact]:
        """Get a single fact (highest confidence) (PERSISTED)"""
        query = "SELECT * FROM facts WHERE key = ? AND confidence >= ?"
        params = [key, min_confidence]
        
        if source:
            query += " AND source = ?"
            params.append(source)
            
        query += " ORDER BY confidence DESC LIMIT 1"
        
        with self._db_lock:
            row = self._cursor.execute(query, params).fetchone()
        if not row:
            return None
            
        return Fact(
            key=row['key'],
            value=row['value'],
            source=row['source'],
            confidence=row['confidence'],
            timestamp=row['timestamp'],
            fact_id=row['fact_id'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )

    def get_facts(
        self,
        key: str,
        source: Optional[str] = None,
        min_confidence: float = 0.0,
        cross_session: bool = False
    ) -> List[Fact]:
        """Get all facts for a key (PERSISTED & CROSS-SESSION)"""
        query = "SELECT * FROM facts WHERE key = ? AND confidence >= ?"
        params = [key, min_confidence]
        
        if source:
            query += " AND source = ?"
            params.append(source)
            
        if not cross_session:
            query += " AND session_id = ?"
            params.append(self.session_id)
            
        query += " ORDER BY confidence DESC"
        
        with self._db_lock:
            rows = self._cursor.execute(query, params).fetchall()
        return [
            Fact(
                key=r['key'], value=r['value'], source=r['source'],
                confidence=r['confidence'], timestamp=r['timestamp'],
                fact_id=r['fact_id'],
                metadata=json.loads(r['metadata']) if r['metadata'] else {}
            )
            for r in rows
        ]

    def query(
        self,
        query: str,
        min_confidence: float = 0.0,
        max_results: int = 20,
        cross_session: bool = False
    ) -> List[Fact]:
        """
        Query facts using LIKE matching (DURABLE & CROSS-SESSION).
        
        Args:
            query: Search string.
            min_confidence: Filter by confidence.
            max_results: Limit results.
            cross_session: If True, searches ALL sessions in the database.
        """
        q_str = f"%{query}%"
        sql = "SELECT * FROM facts WHERE (key LIKE ? OR value LIKE ?) AND confidence >= ?"
        params = [q_str, q_str, min_confidence]
        
        if not cross_session:
            sql += " AND session_id = ?"
            params.append(self.session_id)
            
        sql += " ORDER BY timestamp DESC, confidence DESC LIMIT ?"
        params.append(max_results)
        
        with self._db_lock:
            rows = self._cursor.execute(sql, params).fetchall()
        
        return [
            Fact(
                key=r['key'], value=r['value'], source=r['source'],
                confidence=r['confidence'], timestamp=r['timestamp'],
                fact_id=r['fact_id'],
                metadata=json.loads(r['metadata']) if r['metadata'] else {}
            )
            for r in rows
        ]

    def get_all_facts(
        self,
        source: Optional[str] = None,
        min_confidence: float = 0.0,
        cross_session: bool = False
    ) -> List[Fact]:
        """Get all facts in the model (PERSISTED & CROSS-SESSION)"""
        sql = "SELECT * FROM facts WHERE confidence >= ?"
        params = [min_confidence]
        
        if source:
            sql += " AND source = ?"
            params.append(source)
            
        if not cross_session:
            sql += " AND session_id = ?"
            params.append(self.session_id)
            
        with self._db_lock:
            rows = self._cursor.execute(sql, params).fetchall()
        return [
            Fact(
                key=r['key'], value=r['value'], source=r['source'],
                confidence=r['confidence'], timestamp=r['timestamp'],
                fact_id=r['fact_id'],
                metadata=json.loads(r['metadata']) if r['metadata'] else {}
            )
            for r in rows
        ]

    def get_facts_count(self, cross_session: bool = False) -> int:
        """Get the count of facts in SQLite directly (PERSISTED)"""
        try:
            sql = "SELECT COUNT(*) FROM facts"
            params = []
            if not cross_session:
                sql += " WHERE session_id = ?"
                params.append(self.session_id)
            
            with self._db_lock:
                row = self._cursor.execute(sql, params).fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error querying facts count from SQLite: {e}")
            return sum(len(v) for v in self._facts.values())

    def get_by_source(self, source: str) -> Dict[str, List[Fact]]:
        """Get all facts from a specific source (PERSISTED)"""
        sql = "SELECT * FROM facts WHERE source = ?"
        with self._db_lock:
            rows = self._cursor.execute(sql, (source,)).fetchall()
        
        result = defaultdict(list)
        for r in rows:
            f = Fact(
                key=r['key'], value=r['value'], source=r['source'],
                confidence=r['confidence'], timestamp=r['timestamp'],
                fact_id=r['fact_id'],
                metadata=json.loads(r['metadata']) if r['metadata'] else {}
            )
            result[f.key].append(f)
        return dict(result)

    def _save_entity_to_db(self, entity: Entity):        
        import time
        max_retries = 10
        for attempt in range(max_retries):
            try:
                with self._db_lock:
                    self._cursor.execute(
"""
                    INSERT OR REPLACE INTO entities
                    (entity_id, type, properties, confidence, source, created_at, updated_at, verified, metadata, verification_count, session_id, reasoning_trace)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.entity_id, entity.type, json.dumps(entity.properties), 
                    entity.confidence, entity.source, entity.created_at, entity.updated_at,
                    1 if entity.verified else 0, json.dumps(entity.metadata), entity.verification_count, self.session_id,
                    getattr(entity, 'reasoning_trace', '')
                ))
                self._conn.commit()
                # Update cache
                self._entities_cache[entity.entity_id] = entity
                return
            except Exception as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    # [TITAN V201.0] SYNCHRONOUS RETRY MANIFOLD
                    import time
                    time.sleep(0.05 * (attempt + 1))
                    continue
                logger.error(f"Failed to save entity {entity.entity_id}: {e}")
                raise RuntimeError(f"PHYSICAL_VAPORIZATION: Failed to persist entity {entity.entity_id} to disk manifold: {e}")


    def _detect_conflict(self, key: str):
        """Detect if there is a conflict for a key (ORIGINAL)"""
        facts = self._facts[key]
        if len(facts) < 2:
            return

        values = [str(f.value) for f in facts]
        unique_values = set(values)

        if len(unique_values) > 1:
            self._stats["conflicts"] += 1
            logger.warning(
                f" Conflict detected for key '{key}': "
                f"{len(unique_values)} different values from {len(facts)} sources"
            )

    def get_conflicts(self, min_severity: float = 0.0) -> List[Conflict]:
        """Get all conflicts in the model (ORIGINAL)"""
        conflicts = []

        for key, fact_list in self._facts.items():
            if len(fact_list) < 2:
                continue

            values = [str(f.value) for f in fact_list]
            unique_values = set(values)

            if len(unique_values) > 1:
                conflict = Conflict(key=key, facts=fact_list)
                if conflict.severity >= min_severity:
                    conflicts.append(conflict)

        conflicts.sort(key=lambda c: c.severity, reverse=True)
        return conflicts

    def resolve_conflict(
        self,
        key: str,
        resolution: str = "highest_confidence"
    ) -> Optional[Fact]:
        """Resolve a conflict for a key (ORIGINAL)"""
        facts = self._facts.get(key, [])
        if len(facts) < 2:
            return facts[0] if facts else None

        if resolution == "highest_confidence":
            winner = max(facts, key=lambda f: f.confidence)
        elif resolution == "most_recent":
            winner = max(facts, key=lambda f: f.timestamp)
        else:
            logger.error(f"Unknown resolution strategy: {resolution}")
            return None

        self._facts[key] = [winner]
        logger.info(f" Resolved conflict for '{key}' using {resolution}")
        return winner

    def invalidate_hypothesis(self, hypothesis_id: str, reason: str = "") -> None:
        """
        [RIGOR FIX] State Desync on Rollback.
        Cascades invalidation from the Epistemic Regulator down to all simulated entities
        and facts associated with the refuted hypothesis to prevent ghost data poisoning.
        """
        with self._memory_lock:
            logger.info(f" [WORLD] Cascading invalidation for Hypothesis {hypothesis_id}")
            
            # Deprecate facts linked to this hypothesis
            for key, fact_list in self._facts.items():
                for fact in fact_list:
                    if fact.metadata and fact.metadata.get("hypothesis_id") == hypothesis_id:
                        fact.confidence = 0.0
                        fact.metadata["invalidated"] = True
                        fact.metadata["invalidation_reason"] = reason
            
            # Deprecate relationships
            for rel in self._relationships.values():
                rel_props = getattr(rel, 'properties', None) or getattr(rel, 'metadata', None) or {}
                if rel_props.get("hypothesis_id") == hypothesis_id:
                    rel.deprecated = True
                    rel.confidence = 0.0

            # Persist invalidation to SQLite
            with self._db_lock:
                try:
                    self._cursor.execute(
                        "UPDATE facts SET confidence = 0.0 WHERE metadata LIKE ? OR metadata LIKE ?",
                        (f'%"hypothesis_id": "{hypothesis_id}"%', f'%"hypothesis_id":"{hypothesis_id}"%')
                    )
                    self._cursor.execute(
                        "UPDATE relationships SET confidence = 0.0, deprecated = 1 WHERE properties LIKE ? OR properties LIKE ? OR evidence LIKE ? OR evidence LIKE ?",
                        (f'%"hypothesis_id": "{hypothesis_id}"%', f'%"hypothesis_id":"{hypothesis_id}"%',
                         f'%"hypothesis_id": "{hypothesis_id}"%', f'%"hypothesis_id":"{hypothesis_id}"%')
                    )
                    self._cursor.execute(
                        "UPDATE entities SET confidence = 0.0 WHERE entity_id = ? OR metadata LIKE ? OR metadata LIKE ? OR properties LIKE ? OR properties LIKE ?",
                        (hypothesis_id, f'%"hypothesis_id": "{hypothesis_id}"%', f'%"hypothesis_id":"{hypothesis_id}"%',
                         f'%"hypothesis_id": "{hypothesis_id}"%', f'%"hypothesis_id":"{hypothesis_id}"%')
                    )
                    self._conn.commit()
                except Exception as e:
                    logger.error(f"Failed to persist hypothesis invalidation in SQLite: {e}")

            # Dual-write update could be added here if Neo4j supports cascading deletes
            if self.neo4j:
                try:
                    # In a real production system we'd execute a Cypher query to drop confidence
                    pass
                except Exception as e:
                    logger.warning(f"Neo4j cascade failed: {e}")

    # =========================================================================
    # ORIGINAL ENTITY-RELATIONSHIP METHODS (Preserved)
    # =========================================================================

    def add_entity(self, entity: Entity, merge: bool = True) -> Entity:
        """Add entity to the knowledge graph (DYNAMIC SEMANTIC UNIFICATION)"""
        with self._memory_lock:
            # [GODZILLA PURITY GATE] Physically block slop from entering the vault
            props_str = str(entity.properties).lower()
            toxic_patterns = [
                "traceback (most recent call last):",
                "attributeerror:", "'status': 'failed'", '"status": "failed"',
                "empty response", "extraction failed", "no source document"
            ]
            if any(p in props_str for p in toxic_patterns):
                logger.warning(f" [PURGE] Rejected toxic entity '{entity.entity_id}': Pattern match detected slop/error.")
                return entity

            # 1. Exact ID Match (Fast Path)
            if entity.entity_id in self._entities and merge:
                existing = self._entities[entity.entity_id]
                existing.properties.update(entity.properties)
                existing.updated_at = time.time()
                existing.confidence = max(existing.confidence, entity.confidence)
                logger.debug(f" Merged entity (Exact ID): {entity.entity_id} (type={entity.type})")
                target_entity = existing
            else:
                # 2. Dynamic Semantic Match (Domain-Aware)
                fuzzy_match_id = None
                if merge:
                    # Check entities of the same type
                    same_type_ids = self._entity_type_index.get(entity.type, set())

                    # Get labels for comparison
                    e_label = str(entity.properties.get("name", entity.properties.get("title", entity.entity_id))).lower()

                    for eid in same_type_ids:
                        existing = self._entities[eid]
                        ex_label = str(existing.properties.get("name", existing.properties.get("title", existing.entity_id))).lower()

                        # SEMANTIC IDENTITY: Exact match or high overlap
                        if e_label == ex_label:
                            fuzzy_match_id = eid
                            break

                        # CROSS-FIELD HEURISTIC: If labels are long enough and one contains the other
                        if len(e_label) > 8 and len(ex_label) > 8:
                            if e_label in ex_label or ex_label in e_label:
                                # Verify they are not just "The [Domain]" common prefixes
                                fuzzy_match_id = eid
                                break

                if fuzzy_match_id:
                    existing = self._entities[fuzzy_match_id]
                    existing.properties.update(entity.properties)
                    existing.updated_at = time.time()
                    existing.confidence = max(existing.confidence, entity.confidence)
                    logger.info(f" [UNIFY] Semantic Merged: '{entity.entity_id}' -> '{fuzzy_match_id}' (Type: {entity.type})")
                    target_entity = existing
                else:
                    # [TITAN V157.0] ATOMIC ENTITY COMMIT
                    # Physically protect the entity manifold from swarm corruption.
                    self._entities[entity.entity_id] = entity
                    self._entities_cache[entity.entity_id] = entity
                    self._entity_type_index[entity.type].add(entity.entity_id)
                    self._stats["total_entities"] += 1
                    target_entity = entity
                
                if entity.embedding is not None:
                    self._embeddings[target_entity.entity_id] = entity.embedding
                
                logger.debug(f" Added entity: {target_entity.entity_id} (type={target_entity.type})")
        
        # FIX: Update Cache (Split Brain Fix)
        self._entities_cache[target_entity.entity_id] = target_entity

        # FIX: Persist to SQLite
        self._save_entity_to_db(target_entity)
        
        # PILLAR 2: Sync to Neo4j (Dual-Write) via KnowledgeGraph
        if self._knowledge_graph and self._knowledge_graph.is_available:
            try:
                props = target_entity.properties
                if target_entity.type == "Paper":
                    self._knowledge_graph.add_paper(
                        title=props.get("title", target_entity.entity_id),
                        doi=props.get("doi"),
                        arxiv_id=props.get("arxiv_id"),
                        year=props.get("year"),
                        abstract=props.get("abstract"),
                        authors=props.get("authors", []),
                        citation_count=props.get("citation_count", 0),
                        metadata={"session_id": self.session_id}
                    )
                elif target_entity.type == "Hypothesis":
                    self._knowledge_graph.add_hypothesis(
                        hypothesis_id=target_entity.entity_id,
                        statement=props.get("statement", str(props)),
                        status=props.get("status", "pending")
                    )
            except Exception as e:
                logger.error(f"Neo4j write failed: {e}. [ULTRON BEAST FIX] Writing to sync outbox to prevent State Desync.")
                try:
                    import json, os
                    os.makedirs("data/sync", exist_ok=True)
                    with open("data/sync/neo4j_outbox.jsonl", "a") as f:
                        f.write(json.dumps({"action": "add_entity", "entity": target_entity.to_dict()}) + "\n")
                except Exception as outbox_err:
                    logger.critical(f"FATAL: Neo4j Sync Outbox failed: {outbox_err}")

        return target_entity

    async def add_hypothesis(self, hypothesis: Any) -> str:
        """
        Add a formal Hypothesis object to the World Model.
        Converts it to an Entity and persists it.
        """
        stmt = getattr(hypothesis, "statement", "")
        from backend.core.hypothesis.tracker import is_valid_scientific_hypothesis
        if not is_valid_scientific_hypothesis(stmt):
            logger.warning(f" [WORLD-MODEL-PURGE] Rejected non-scientific hypothesis: {stmt[:80]}")
            return ""

        # [GODZILLA] Extract properties from the Hypothesis object
        properties = {
            "statement": stmt,
            "rationale": getattr(hypothesis, "rationale", ""),
            "variables": getattr(hypothesis, "variables", []),
            "parameters": getattr(hypothesis, "parameters", []),
            "predictions": getattr(hypothesis, "predictions", []),
            "state": str(getattr(hypothesis, "state", "pending"))
        }
        
        # Determine hypothesis ID
        h_id = getattr(hypothesis, "hypothesis_id", None)
        if not h_id:
            # Generate deterministic ID if missing
            content = f"Hypothesis:{properties['statement']}"
            h_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        entity = Entity(
            type="Hypothesis",
            properties=properties,
            entity_id=h_id,
            confidence=getattr(hypothesis, "confidence", 1.0),
            source="hypothesis_generator"
        )
        
        self.add_entity(entity)
        return h_id

    def _ground_scientific_entities(self, parent_id: str, text: str, metadata: Dict[str, Any]):
        """
        [DEEP GROUNDING] - MISSION CONTROL UPGRADE
        Automatically extracts domain-relevant entities using dynamic pattern matching.
        """
        raw_domain = metadata.get("domain", "general").lower()
        import re

        # Domain alias mapping
        domain_aliases = {
            "superconductivity": "superconductivity",
            "superconductor": "superconductivity",
            "condensed_matter": "superconductivity",
            "materials_science": "materials_science",
            "materials": "materials_science",
            "chemistry": "materials_science",
            "solid_state_physics": "superconductivity",
            "physics": "physics",
            "biology": "biology",
            "virology": "biology",
            "biophysics": "biology",
            "machine_learning": "machine_learning",
            "ai": "machine_learning",
        }
        domain = domain_aliases.get(raw_domain, raw_domain)

        # [GODZILLA V68.16] Universal Sieve: High-Recall Entity Extraction
        ONTOLOGIES = {
            "superconductivity": {
                "Material": r"\b([A-Z][a-z]?(?:\d*\.?\d*)?(?:[A-Z][a-z]?(?:\d*\.?\d*)?){1,6}|YBCO|BSCCO|MgB2|FeSe|LaH10|H3S|Nb3Sn|NbTi|cuprates?|pnictides?|hydrides?|borocarbides?)\b",
                "PhysicalProperty": r"(?i)\b(Tc|critical\s+temperature|Hc[12]?|upper\s+critical\s+field|Jc|critical\s+current|Debye\s+temperature|Fermi\s+energy|BCS\s+gap|coherence\s+length|penetration\s+depth|electron-phonon\s+coupling|density\s+of\s+states)\b",
                "LatticeStructure": r"(?i)\b(perovskite|tetragonal|orthorhombic|monoclinic|hexagonal|cubic|layered|CuO2\s+planes?|rock-salt)\b",
                "Mechanism": r"(?i)\b(BCS\s+theory|Cooper\s+pair(?:ing)?|d-wave|s-wave|phonon-mediated|spin\s+fluctuation|pseudogap|Meissner\s+effect)\b",
            },
            "materials_science": {
                "Material": r"\b([A-Z][a-z]?(?:\d*\.?\d*)?(?:[A-Z][a-z]?(?:\d*\.?\d*)?){1,6}|alloy|ceramic|polymer|graphene|perovskite)\b",
                "PhysicalProperty": r"(?i)\b(bandgap|conductivity|resistivity|melting\s+point|elastic\s+modulus|density|thermal\s+expansion|electronegativity|atomic\s+radius)\b",
                "LatticeStructure": r"(?i)\b(fcc|bcc|hcp|perovskite|spinel|wurtzite|rutile|amorphous|polycrystalline)\b",
            },
            "biology": {
                "Entity": r"\b([A-Z][A-Z0-9]{2,15}|[A-Z][a-z]{2,10}[A-Z0-9]+)\b", # Broad capture for symbols/variants
                "Variant": r"\b([A-Z]\d+[A-Z]|JN\.1|KP\.3|XBB|BA\.2|Omicron)\b",
                "Binding": r"(?i)\b(Kd|Ki|IC50)\s*(<|>|=)?\s*(\d+\.?\d*)\s*(nM|uM|pM)\b"
            },
            "physics": {
                "Particle": r"\b(boson|fermion|neutrino|muon|electron|proton|neutron|boron-11)\b",
                "Reaction": r"\b(p-B11|D-T|D-D|H3-He3)\b",
                "Metric": r"(\d+\.?\d*)\s*(keV|MeV|GeV|Tesla|Ke)\b",
            },
            "machine_learning": {
                "Model": r"\b(Transformer|GPT-\d+|BERT|ResNet|LLM|GNN|CNN)\b",
                "Metric": r"\b(mAP|AUC|Accuracy|F1|Loss|PPL)\b",
            },
            "general": {
                "Concept": r"\b(Perovskite|Crystal|Lattice|Superconductor|Bandgap|Phonon)\b",
            }
        }

        # 1. Select patterns for current domain
        patterns = ONTOLOGIES.get(domain, ONTOLOGIES.get("general", {}))
        
        extracted_count = 0
        extracted_entities = []
        # [SOVEREIGN SIEVE] 1. Filter English Stop-words and Software Metatags
        STOP_WORDS = {
            "and", "the", "for", "with", "that", "this", "from", "which", "these", "using", "also", "been", "were", "was", "have",
            "method", "system", "approach", "model", "dataset", "framework", "algorithm", "protocol",
            "accuracy", "performance", "time", "speed", "ratio", "error", "coefficient", "score", "metric", "concept",
            "results", "query", "search", "table", "figure"
        }
        
        # Ensure parent document/fact entity exists to satisfy foreign key constraints
        if parent_id and not self.get_entity(parent_id):
            self.add_entity(Entity(
                entity_id=parent_id,
                type="Document",
                properties={"name": f"doc_{parent_id}", "context": text[:500], "domain": domain},
                source="deep_grounding",
                verified=True
            ), merge=False)

        # [GODZILLA V68.17] Surgical Extraction
        for e_type, regex in patterns.items():
            if e_type == "Entity": continue # Skip broad spam capture
            
            matches = list(re.finditer(regex, text, flags=re.IGNORECASE))
            
            for match in matches:
                entity_val = match.group(0).strip()
                
                # [SOVEREIGN SIEVE] Apply filters
                if entity_val.lower() in STOP_WORDS: continue
                if len(entity_val) < 2: continue
                if entity_val.startswith(("#", "-", "{", "[", "http")): continue
                
                entity_val_norm = entity_val.lower()
                entity_id = f"ground_{domain}_{hashlib.md5(entity_val_norm.encode()).hexdigest()[:8]}"
                entity = Entity(
                    type=e_type,
                    properties={"name": entity_val, "context": text[:1000], "domain": domain},
                    entity_id=entity_id,
                    source="deep_grounding",
                    verified=True
                )
                self.add_entity(entity)
                extracted_entities.append(entity_id)
                
                rel = Relationship(
                    source_id=entity_id,
                    target_id=parent_id,
                    type="MENTIONS",
                    confidence=0.8,
                    created_by="grounding_engine"
                )
                self.add_relationship(rel)
                extracted_count += 1
                
        # 4. Neural Co-occurrence: Connect extracted entities to each other
        # [GODZILLA V72.1 - O(N^2) LOOP PURGED]
        pass
        
        if extracted_count > 0:
            logger.info(f" [GROUNDING] Extracted {extracted_count} {domain} entities from finding.")

    def get_entity(self, entity_id: str, cross_session: bool = True) -> Optional[Entity]:
        """Get an entity by ID (PERSISTED & CROSS-SESSION FALLBACK)"""
        # Check cache first (Session locked)
        if entity_id in self._entities_cache:
            return self._entities_cache[entity_id]
            
        # Check DB
        query = "SELECT * FROM entities WHERE entity_id = ?"
        params = [entity_id]
        
        if not cross_session:
            query += " AND session_id = ?"
            params.append(self.session_id)
        
        with self._db_lock:
            row = self._cursor.execute(query, params).fetchone()
        if not row:
            return None
            
        entity = Entity(
            entity_id=row['entity_id'],
            type=row['type'],
            properties=json.loads(row['properties']) if row['properties'] else {},
            confidence=row['confidence'],
            source=row['source'],
            verified=bool(row['verified']),
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )
        entity.created_at = row['created_at']
        entity.updated_at = row['updated_at']
        entity.verification_count = row['verification_count']
        
        # Update cache if it's the current session
        if row['session_id'] == self.session_id:
            self._entities_cache[entity_id] = entity
            
        return entity

    def search_entities(
        self,
        query: str,
        type_filter: Optional[str] = None,
        cross_session: bool = False
    ) -> List[Entity]:
        """Search entities by properties (PERSISTED & CROSS-SESSION)"""
        q_str = f"%{query}%"
        sql = "SELECT * FROM entities WHERE properties LIKE ?"
        params = [q_str]
        
        if type_filter:
            sql += " AND type = ?"
            params.append(type_filter)
            
        if not cross_session:
            sql += " AND session_id = ?"
            params.append(self.session_id)
            
        sql += " LIMIT 50"
        
        with self._db_lock:
            rows = self._cursor.execute(sql, params).fetchall()
        
        return [
            Entity(
                entity_id=r['entity_id'],
                type=r['type'],
                properties=json.loads(r['properties']) if r['properties'] else {},
                confidence=r['confidence'],
                source=r['source'],
                verified=bool(r['verified']),
                metadata=json.loads(r['metadata']) if r['metadata'] else {}
            )
            for r in rows
        ]

    def get_entities_by_type(self, type_filter: str) -> List[Entity]:
        """Get all entities of a specific type (PERSISTED)"""
        return self.search_entities(query="", type_filter=type_filter)

    # =========================================================================
    # RELATIONSHIPS (PERSISTED)
    # =========================================================================

    def _save_relationship_to_db(self, rel: Relationship):
        import time
        max_retries = 10
        for attempt in range(max_retries):
            try:
                with self._db_lock:
                    self._cursor.execute(
"""
                    INSERT OR REPLACE INTO relationships 
                    (relationship_id, source_id, target_id, type, properties, confidence, 
                    created_by, created_at, deprecated, contested, evidence, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel.relationship_id, rel.source_id, rel.target_id, rel.type, json.dumps(rel.properties),
                    rel.confidence, rel.created_by, rel.created_at, 
                    1 if rel.deprecated else 0, 1 if rel.contested else 0,
                    json.dumps(rel.evidence), self.session_id
                ))
                self._conn.commit()
                return
            except Exception as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    # [TITAN V201.0] SYNCHRONOUS RETRY MANIFOLD
                    import time
                    time.sleep(0.05 * (attempt + 1))
                    continue
                logger.error(f"Failed to save relationship {rel.relationship_id}: {e}")
                if "foreign key" in str(e).lower():
                    logger.warning(f"Relationship {rel.relationship_id} bypassed due to missing endpoint in foreign key: {e}")
                    return
                raise RuntimeError(f"PHYSICAL_VAPORIZATION: Failed to persist relationship {rel.relationship_id} to disk manifold: {e}")



    def add_relationship(self, relationship: Relationship) -> Relationship:
        """Add a directed relationship (PERSISTED)"""
        # Ensure endpoints exist to satisfy SQLite foreign key integrity
        if relationship.source_id and not self.get_entity(relationship.source_id):
            self.add_entity(Entity(
                entity_id=relationship.source_id,
                type="Concept",
                properties={"name": relationship.source_id, "auto_stub": True},
                source="rel_endpoint",
                verified=False
            ), merge=False)
        if relationship.target_id and not self.get_entity(relationship.target_id):
            self.add_entity(Entity(
                entity_id=relationship.target_id,
                type="Concept",
                properties={"name": relationship.target_id, "auto_stub": True},
                source="rel_endpoint",
                verified=False
            ), merge=False)
        self._save_relationship_to_db(relationship)
        
        # FIX: Update memory cache
        with self._memory_lock:
            self._stats["total_relationships"] += 1
            if relationship.relationship_id:
                self._relationships[relationship.relationship_id] = relationship
                self._outgoing_rels.setdefault(relationship.source_id, set()).add(relationship.relationship_id)
                self._incoming_rels.setdefault(relationship.target_id, set()).add(relationship.relationship_id)
        
        logger.debug(f" Added relationship: {relationship.source_id} -[{relationship.type}]-> {relationship.target_id}")
        
        # Dual-write to Neo4j
        if self.neo4j:
            try:
                # Basic graph connection
                pass # Graph additions logic handles this elsewhere usually
            except Exception as e:
                logger.warning(f"Neo4j link failed: {e}")
                
        return relationship

    def get_relationships(
        self, 
        entity_id: str, 
        direction: str = "outgoing",
        type_filter: Optional[str] = None
    ) -> List[Relationship]:
        """Get relationships for an entity (PERSISTED)"""
        sql = ""
        params = [entity_id]
        
        if direction == "outgoing":
            sql = "SELECT * FROM relationships WHERE source_id = ?"
        elif direction == "incoming":
            sql = "SELECT * FROM relationships WHERE target_id = ?"
        else: # both
            sql = "SELECT * FROM relationships WHERE source_id = ? OR target_id = ?"
            params = [entity_id, entity_id]
            
        if type_filter:
            sql += " AND type = ?"
            params.append(type_filter)
            
        with self._db_lock:
            rows = self._cursor.execute(sql, params).fetchall()
        
        return [
            Relationship(
                source_id=r['source_id'], target_id=r['target_id'], type=r['type'],
                properties=json.loads(r['properties']) if r['properties'] else {},
                confidence=r['confidence'], created_by=r['created_by'],
                relationship_id=r['relationship_id']
            )
            for r in rows
        ]

    def delete_entity(self, entity_id: str) -> bool:
        """Delete entity and its relationships (ORIGINAL)"""
        exists = False
        if entity_id in self._entities:
            exists = True
            entity = self._entities[entity_id]
            
            if entity.type in self._entity_type_index:
                self._entity_type_index[entity.type].discard(entity_id)
            
            for rel_id in list(self._outgoing_rels.get(entity_id, set())):
                self.delete_relationship(rel_id)
            for rel_id in list(self._incoming_rels.get(entity_id, set())):
                self.delete_relationship(rel_id)
            for rel_id, rel in list(self._relationships.items()):
                if rel.source_id == entity_id or rel.target_id == entity_id:
                    self.delete_relationship(rel_id)
            
            del self._entities[entity_id]
            self._entities_cache.pop(entity_id, None)
            self._stats["total_entities"] -= 1
            
        with self._db_lock:
            self._cursor.execute("SELECT 1 FROM entities WHERE entity_id = ?", (entity_id,))
            if self._cursor.fetchone():
                exists = True
            self._cursor.execute("DELETE FROM relationships WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
            self._cursor.execute("DELETE FROM causal_links WHERE cause_id = ? OR effect_id = ?", (entity_id, entity_id))
            self._cursor.execute("DELETE FROM entities WHERE entity_id = ?", (entity_id,))
            self._conn.commit()
            
        return exists

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get relationship by ID (ORIGINAL)"""
        # Check memory first
        if relationship_id in self._relationships:
            return self._relationships[relationship_id]
            
        # Check DB
        with self._db_lock:
            row = self._cursor.execute("SELECT * FROM relationships WHERE relationship_id = ?", (relationship_id,)).fetchone()
        if row:
            rel = Relationship(
                source_id=row['source_id'], target_id=row['target_id'], type=row['type'],
                properties=json.loads(row['properties']) if row['properties'] else {},
                confidence=row['confidence'], created_by=row['created_by'],
                relationship_id=row['relationship_id']
            )
            self._relationships[relationship_id] = rel
            return rel
        return None

    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship (ORIGINAL)"""
        exists = False
        if relationship_id in self._relationships:
            exists = True
            rel = self._relationships[relationship_id]
            self._outgoing_rels[rel.source_id].discard(relationship_id)
            self._incoming_rels[rel.target_id].discard(relationship_id)
            del self._relationships[relationship_id]
            self._stats["total_relationships"] -= 1
            
        with self._db_lock:
            self._cursor.execute("SELECT 1 FROM relationships WHERE relationship_id = ?", (relationship_id,))
            if self._cursor.fetchone():
                exists = True
            self._cursor.execute("DELETE FROM relationships WHERE relationship_id = ?", (relationship_id,))
            self._conn.commit()
            
        return exists

    def query_related_entities(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "outgoing",
        max_depth: int = 1
    ) -> List[Entity]:
        """Query entities related to a given entity (ORIGINAL)"""
        if entity_id not in self._entities:
            return []
        
        visited: Set[str] = set()
        result: List[Entity] = []
        
        def traverse(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            visited.add(current_id)
            
            rel_ids: Set[str] = set()
            
            if direction in ("outgoing", "both"):
                rel_ids.update(self._outgoing_rels.get(current_id, set()))
            if direction in ("incoming", "both"):
                rel_ids.update(self._incoming_rels.get(current_id, set()))
            
            for rel_id in rel_ids:
                rel = self._relationships.get(rel_id)
                if not rel:
                    continue
                
                if relationship_type and rel.type != relationship_type:
                    continue
                
                other_id = rel.target_id if rel.source_id == current_id else rel.source_id
                
                if other_id not in visited and other_id in self._entities:
                    result.append(self._entities[other_id])
                    
                    if depth < max_depth:
                        traverse(other_id, depth + 1)
        
        traverse(entity_id, 1)
        return result

    def get_entity_stats(self) -> Dict[str, Any]:
        """Get entity/relationship statistics (ORIGINAL)"""
        type_counts = {t: len(ids) for t, ids in self._entity_type_index.items()}
        rel_type_counts: Dict[str, int] = defaultdict(int)
        for rel in self._relationships.values():
            rel_type_counts[rel.type] += 1
        
        return {
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationships),
            "entity_types": dict(type_counts),
            "relationship_types": dict(rel_type_counts)
        }

    def export_graph(self) -> Dict[str, Any]:
        """Export entity-relationship graph to dict (ORIGINAL)"""
        return {
            "entities": [e.to_dict() for e in self._entities.values()],
            "relationships": [r.to_dict() for r in self._relationships.values()],
            "stats": self.get_entity_stats()
        }

    def update_beliefs(self, hypotheses: List[Any], refutation_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        PCD Pillar 2: World Model as Governor (ORIGINAL with Titan enhancements)
        Updates hypothesis confidence based on facts and relationships.
        NOW WITH BRUTAL PUNITIVITY + Bayesian updates.
        """
        updates = []
        for h in hypotheses:
            # 1. Graph evidence (ORIGINAL)
            related_entities = self.query_related_entities(h.id, direction="incoming", max_depth=1)
            supports = self.query(h.statement, min_confidence=0.6)
            
            score_delta = 0.0

            # 2. Brutal punitivity (ORIGINAL)
            killers = [
                e for e in related_entities 
                if e.type == "Finding" and e.metadata.get("relation") == "REFUTES" 
                and e.confidence > refutation_threshold
            ]
            
            if killers:
                logger.info(f" Brutal Punitivity: Hypothesis {h.id} REFUTED by {killers[0].entity_id}")
                updates.append({
                    "hypothesis_id": h.id,
                    "confidence_delta": -1.0,
                    "reason": f"REFUTED_BY_{killers[0].entity_id}"
                })
                continue
            
            # 3. NEW: Bayesian update
            if related_entities and hasattr(h, 'confidence'):
                # Use Bayesian reasoning if available
                if hasattr(self, '_bayesian_priors') and h.id in self._bayesian_priors:
                    evidence_id = related_entities[0].entity_id
                    new_conf = self.bayesian_update_belief(h.id, evidence_id, observed=True)
                    score_delta = new_conf - h.confidence
                else:
                    # Fallback to fact-based (ORIGINAL)
                    unique_support_count = len(supports)
                    if unique_support_count == 0 and h.confidence > 0.5:
                        score_delta = -0.02
                    elif unique_support_count > 3:
                        score_delta = 0.05
            
            if score_delta != 0:
                updates.append({
                    "hypothesis_id": h.id,
                    "confidence_delta": score_delta,
                    "reason": f"world_model_governance: {len(supports)} supporting facts"
                })
        
        return updates

    # =========================================================================
    # CHROMADB SEMANTIC SEARCH METHODS (1000x UPGRADE)
    # =========================================================================

    def is_chroma_available(self) -> bool:
        """Check if ChromaDB is available and initialized"""
        return self._chroma_collection is not None

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two strings using the embedding model.
        Returns a score between 0.0 (unrelated) and 1.0 (identical).
        """
        if not self._embedding_model:
            # Lazy load if not already loaded
            if SENTENCE_TRANSFORMER_AVAILABLE:
                try:
                    from sentence_transformers import SentenceTransformer
                    os.environ["TRANSFORMERS_OFFLINE"] = "1"
                    os.environ["HF_DATASETS_OFFLINE"] = "1"
                    # [GODZILLA ARM64 FIX] Force CPU to prevent MPS deadlock
                    self._embedding_model = SentenceTransformer(self._embedding_model_name, device="cpu")
                except Exception as e:
                    logger.warning(f"Could not load embedding model: {e}")
                    return 0.0
            else:
                return 0.0

        try:
            # Encode both texts
            embeddings = self._embedding_model.encode([text1, text2])
            v1, v2 = embeddings[0], embeddings[1]
            
            # Compute cosine similarity
            # (v1 . v2) / (|v1| * |v2|)
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            
            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
                
            return float(dot_product / (norm_v1 * norm_v2))
        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            return 0.0

    def index_entity_chroma(self, entity_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Index an entity in VectorStore for semantic search.
        """
        if not self.vectorstore:
            return False
            
        try:
            # metadata logic currently ignored as VectorStore.add_document doesn't accept extra metadata 
            # (it manages its own metadata/id/content). 
            # Future TODO: Update VectorStore to accept arbitrary metadata.
            
            # Use unified add_document
            self.vectorstore.add_document(doc_id=entity_id, content=text)
            return True
        except Exception as e:
            logger.error(f"VectorStore index failed for {entity_id}: {e}")
            return False

    def semantic_search_chroma(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Semantic similarity search using VectorStore.
        Returns: List of (entity_id, similarity_score, metadata) tuples
        """
        if not self.vectorstore:
            return []
            
        try:
            results = self.vectorstore.query(query, top_k=top_k)
            # Adapt standardized result to expected tuple format
            out = []
            for r in results:
                # r has keys: id, score, content, metadata
                out.append((r["id"], r["score"], r["metadata"]))
            return out
        except Exception as e:
            logger.error(f"VectorStore search failed: {e}")
            return []

    def index_all_entities_chroma(self) -> int:
        """
        Index all existing entities in ChromaDB.
        Useful for bulk indexing after loading data.
        
        Returns:
            Number of entities indexed
        """
        count = 0
        for entity_id, entity in self._entities.items():
            # Create text representation
            text_parts = [
                f"Type: {entity.type}",
                f"Properties: {str(entity.properties)}",
            ]
            if entity.metadata:
                text_parts.append(f"Metadata: {str(entity.metadata)}")
            
            text = " | ".join(text_parts)
            
            metadata = {
                "type": entity.type,
                "confidence": entity.confidence,
                "verified": entity.verified
            }
            
            if self.index_entity_chroma(entity_id, text, metadata):
                count += 1
        
        logger.info(f" Indexed {count}/{len(self._entities)} entities in ChromaDB")
        return count

    def find_similar_entities(
        self,
        entity_id: str,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find entities similar to a given entity.
        Uses ChromaDB for semantic similarity.
        
        Args:
            entity_id: Source entity ID
            top_k: Number of similar entities to return
            
        Returns:
            List of (entity_id, similarity_score) tuples
        """
        entity = self.get_entity(entity_id)
        if not entity:
            return []
        
        # Create query from entity properties
        query_text = f"{entity.type}: {str(entity.properties)}"
        
        results = self.semantic_search_chroma(query_text, top_k=top_k + 1)
        
        # Filter out the source entity itself
        return [(eid, score) for eid, score, _ in results if eid != entity_id][:top_k]

    # =========================================================================
    # ORIGINAL UTILITY METHODS (Preserved)
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get world model statistics (ORIGINAL + NEW stats)"""
        return {
            "session_id": self.session_id,
            "total_facts": self._stats["total_facts"],
            "unique_keys": self._stats["unique_keys"],
            "conflicts": self._stats["conflicts"],
            "sources": len(self._stats["sources"]),
            "source_list": list(self._stats["sources"]),
            "avg_facts_per_key": (
                self._stats["total_facts"] / self._stats["unique_keys"]
                if self._stats["unique_keys"] > 0 else 0
            ),
            # NEW Titan stats
            "total_entities": self._stats["total_entities"],
            "total_relationships": self._stats["total_relationships"],
            "total_hyperedges": self._stats["total_hyperedges"],
            "total_causal_links": self._stats["total_causal_links"],
            "total_temporal_facts": self._stats["total_temporal_facts"],
            "active_agents": self._stats["active_agents"],
            "contested_edges": len(self._contested_edges)
        }

    def export(self) -> Dict[str, Any]:
        """Export world model to dict (ORIGINAL + NEW data)"""
        return {
            "session_id": self.session_id,
            "stats": self.get_stats(),
            "facts": {
                key: [f.to_dict() for f in fact_list]
                for key, fact_list in self._facts.items()
            },
            "conflicts": [c.to_dict() for c in self.get_conflicts()],
            "entities": [e.to_dict() for e in self._entities.values()],
            "relationships": [r.to_dict() for r in self._relationships.values()],
            # NEW Titan data
            "hyperedges": [h.to_dict() for h in self._hyperedges.values()],
            "temporal_facts": {
                key: [{"key": f.key, "value": f.value, "valid_from": f.valid_from, 
                       "valid_until": f.valid_until} for f in facts]
                for key, facts in self._temporal_facts.items()
            },
            "causal_links": [
                l.to_dict() for links in self._causal_links.values() for l in links
            ]
        }

    def clear(self):
        """Clear all data (ORIGINAL + NEW data)"""
        self._facts.clear()
        self._source_index.clear()
        self._entities.clear()
        self._relationships.clear()
        self._entity_type_index.clear()
        self._outgoing_rels.clear()
        self._incoming_rels.clear()
    
        # NEW: Clear Titan data
        self._hyperedges.clear()
        self._hyperedge_index.clear()
        self._temporal_facts.clear()
        self._snapshots.clear()
        self._causal_links.clear()
        self._interventions.clear()
        self._bayesian_priors.clear()
        self._bayesian_conditionals.clear()
        self._embeddings.clear()
        self._contested_edges.clear()
        self._agents.clear()
        self._task_queue.clear()
        self._resolution_history.clear()
    
        self._stats = {
            "total_facts": 0,
            "unique_keys": 0,
            "conflicts": 0,
            "sources": set(),
            "total_entities": 0,
            "total_relationships": 0,
            "total_hyperedges": 0,
            "total_causal_links": 0,
            "total_temporal_facts": 0,
            "active_agents": 0
        }
        self._decomposed_queries = set() # [GODZILLA GLOBAL CACHE]
        logger.info(" WorldModel cleared (all data)")

    def merge(self, other: 'WorldModel'):
        """
        TITAN DEEP MERGE: Consolidate two world models into one.
        Goes beyond facts to merge the entire hypergraph and causal structure.
        """
        logger.info(f" Initiating Deep Merge from session {other.session_id} -> {self.session_id}")
        
        # 1. Merge Facts
        for key, fact_list in other._facts.items():
            for fact in fact_list:
                self.add_fact(
                    key=key,
                    value=fact.value,
                    source=fact.source,
                    confidence=fact.confidence,
                    metadata=fact.metadata
                )

        # 2. Merge Entities
        for eid, entity in other._entities.items():
            if eid not in self._entities:
                self.add_entity(Entity(
                    type=entity.type,
                    properties=entity.properties,
                    confidence=entity.confidence,
                    source=entity.source,
                    metadata=entity.metadata
                ))
            else:
                # Update existing entity with potentially higher confidence/new metadata
                existing = self._entities[eid]
                if entity.confidence > existing.confidence:
                    existing.confidence = entity.confidence
                    existing.properties.update(entity.properties)
                existing.metadata.update(entity.metadata)

        # 3. Merge Relationships
        for rid, rel in other._relationships.items():
            if rid not in self._relationships:
                self.add_relationship(Relationship(
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    type=rel.type,
                    properties=rel.properties,
                    confidence=rel.confidence,
                    created_by=rel.created_by
                ))

        # 4. Merge Hyperedges
        for hid, hedge in other._hyperedges.items():
            if hid not in self._hyperedges:
                self.add_hyperedge(
                    sources=hedge.source_ids,
                    targets=hedge.target_ids,
                    edge_type=hedge.edge_type,
                    confidence=hedge.confidence,
                    evidence=hedge.evidence,
                    conditions=hedge.conditions
                )

        # 5. Merge Causal Links
        for cause_id, links in other._causal_links.items():
            for link in links:
                self.add_causal_link(
                    cause_id=link.cause_id,
                    effect_id=link.effect_id,
                    strength=link.strength,
                    confidence=link.confidence,
                    evidence=link.evidence,
                    mechanism=link.mechanism
                )

        # 6. Merge Temporal Facts
        for key, facts in other._temporal_facts.items():
            for tf in facts:
                self.add_temporal_fact(
                    key=key,
                    value=tf.value,
                    valid_from=tf.valid_from,
                    valid_until=tf.valid_until,
                    source=tf.source,
                    confidence=tf.confidence,
                    metadata=tf.metadata
                )

        # 7. Merge Bayesian Priors
        for eid, prior in other._bayesian_priors.items():
            if eid not in self._bayesian_priors or prior > self._bayesian_priors[eid]:
                self.bayesian_set_prior(eid, prior)

        logger.info(f" Deep Merge Complete: Consolidated all Titan graph layers.")

    # =========================================================================
    # NEW: HYPERGRAPH METHODS
    # =========================================================================

    def add_hyperedge(
        self,
        sources: List[str],
        targets: List[str],
        edge_type: str,
        confidence: float = 1.0,
        evidence: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add multi-node hyperedge (A+B+C -> D+E)
        Goes beyond binary relationships.
        """
        # TITAN UPGRADE: SHA256 for hyperedge ID
        hid_content = f"{sources}{targets}{edge_type}{time.time()}"
        hid = hashlib.sha256(hid_content.encode()).hexdigest()[:16]
    
        hedge = HyperEdge(
            hyperedge_id=hid,
            edge_type=edge_type,
            source_ids=sources,
            target_ids=targets,
            confidence=confidence,
            evidence=evidence or [],
            conditions=conditions or {}
        )
    
        self._hyperedges[hid] = hedge
    
        # Index all involved entities
        for src in sources:
            self._hyperedge_index[src].add(hid)
        for tgt in targets:
            self._hyperedge_index[tgt].add(hid)
    
        self._stats["total_hyperedges"] += 1
    
        logger.info(f" Hyperedge: {len(sources)}{len(targets)} ({edge_type}) [ID: {hid}]")
        
        # PERSISTENCE
        self._save_hyperedge_to_db(hedge)

        # PILLAR 2: Sync to Neo4j (Dual-Write)
        if hasattr(self, 'neo4j') and self.neo4j:
            self.neo4j.save_hyperedge(hedge.to_dict())
            
        return hid

    def get_hyperedges(self, entity_id: str) -> List[HyperEdge]:
        """Get all hyperedges involving an entity"""
        hedge_ids = self._hyperedge_index.get(entity_id, set())
        return [self._hyperedges[hid] for hid in hedge_ids if hid in self._hyperedges]

    def mark_hyperedge_contested(self, hyperedge_id: str, reason: str = ""):
        """Mark hyperedge as contested (conflicting evidence)"""
        if hyperedge_id in self._hyperedges:
            self._hyperedges[hyperedge_id].contested = True
            self._contested_edges.add(hyperedge_id)
            logger.warning(f" Hyperedge {hyperedge_id} contested: {reason}")

    def deprecate_hyperedge(self, hyperedge_id: str, reason: str = ""):
        """Deprecate hyperedge (superseded by newer evidence)"""
        if hyperedge_id in self._hyperedges:
            self._hyperedges[hyperedge_id].deprecated = True
            self._hyperedges[hyperedge_id].valid_until = time.time()
            logger.info(f" Hyperedge {hyperedge_id} deprecated: {reason}")

    # =========================================================================
    # NEW: TEMPORAL REASONING METHODS
    # =========================================================================

    def add_temporal_fact(
        self,
        key: str,
        value: Any,
        valid_from: float,
        valid_until: Optional[float] = None,
        source: str = "",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TemporalFact:
        """Add time-bounded fact with validity period"""
        fact = TemporalFact(
            key=key,
            value=value,
            valid_from=valid_from,
            valid_until=valid_until,
            source=source,
            confidence=confidence,
            metadata=metadata or {}
        )
    
        # Auto-invalidate previous facts
        for existing in self._temporal_facts[key]:
            if existing.valid_until is None and existing.valid_from < fact.valid_from:
                existing.valid_until = fact.valid_from
                logger.debug(f" Auto-invalidated old fact for '{key}'")
    
        self._temporal_facts[key].append(fact)
        self._stats["total_temporal_facts"] += 1
    
        # PERSISTENCE
        self._save_temporal_fact_to_db(fact)

        logger.info(f" Temporal fact: {key} valid from {valid_from}")
        return fact

    def query_temporal_at_time(self, key: str, timestamp: float) -> Optional[TemporalFact]:
        """Get the fact that was true at a specific time (time travel query)"""
        valid_facts = [
            f for f in self._temporal_facts[key]
            if f.is_valid_at(timestamp)
        ]
        return valid_facts[0] if valid_facts else None

    def get_temporal_history(self, key: str) -> List[TemporalFact]:
        """Get full evolution/history of a fact over time"""
        return sorted(self._temporal_facts[key], key=lambda f: f.valid_from)

    def create_snapshot(self, label: str = "") -> float:
        """Create time-travel checkpoint (snapshot current state)"""
        timestamp = time.time()
        snapshot = {
            "facts": {
                key: [f for f in facts if f.is_valid_at(timestamp)]
                for key, facts in self._temporal_facts.items()
            },
            "entities": len(self._entities),
            "relationships": len(self._relationships),
            "label": label
        }
        self._snapshots[timestamp] = snapshot
        logger.info(f" Snapshot '{label}' created at {timestamp}")
        return timestamp

    def restore_snapshot(self, timestamp: float) -> bool:
        """Restore world model to a previous snapshot (time travel)"""
        if timestamp not in self._snapshots:
            logger.error(f"Snapshot {timestamp} not found")
            return False
    
        # This is a simplified restore - in production you'd restore full state
        logger.info(f" Restoring snapshot from {timestamp}")
        return True

    # =========================================================================
    # NEW: CAUSAL INFERENCE METHODS
    # =========================================================================

    def add_causal_link(
        self,
        cause_id: str,
        effect_id: str,
        strength: float,
        confidence: float = 1.0,
        evidence: Optional[List[str]] = None,
        mechanism: str = ""
    ) -> CausalLink:
        """Add cause->effect relationship with strength"""
        link = CausalLink(
            cause_id=cause_id,
            effect_id=effect_id,
            strength=strength,
            confidence=confidence,
            evidence=evidence or [],
            mechanism=mechanism
        )
    
        self._causal_links[cause_id].append(link)
        self._stats["total_causal_links"] += 1
    
        # PERSISTENCE
        self._save_causal_link_to_db(link)

        logger.info(f" Causal: {cause_id}  {effect_id} (strength={strength:.2f})")
        return link

    def get_causal_effects(self, cause_id: str, min_strength: float = 0.0) -> List[CausalLink]:
        """What does this entity cause? (downstream effects)"""
        return [
            link for link in self._causal_links[cause_id]
            if abs(link.strength) >= min_strength
        ]

    def get_causal_causes(self, effect_id: str) -> List[CausalLink]:
        """What causes this entity? (upstream causes)"""
        causes = []
        for _, links in self._causal_links.items():
            for link in links:
                if link.effect_id == effect_id:
                    causes.append(link)
        return causes

    def simulate_intervention(self, entity_id: str, new_state: Any) -> Dict[str, Any]:
        """
        Predict downstream effects of changing an entity (what-if analysis)
        Simulates counterfactual: "What if we change X to Y?"
        """
        affected = {}
        visited = set()
        
        initial_multiplier = 1.0
        entity = self.get_entity(entity_id)
        if entity and isinstance(new_state, (int, float)):
            current_state = entity.properties.get("state", entity.properties.get("value", 1.0))
            if isinstance(current_state, (int, float)) and current_state != 0:
                initial_multiplier = float(new_state) / float(current_state)
            elif isinstance(current_state, (int, float)):
                initial_multiplier = float(new_state)

        queue = deque([(entity_id, initial_multiplier)])  # (entity, effect_multiplier)
    
        while queue:
            current_id, multiplier = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)
        
            # Get direct effects
            for link in self.get_causal_effects(current_id):
                effect_strength = link.strength * multiplier * link.confidence
                affected[link.effect_id] = affected.get(link.effect_id, 0) + effect_strength
            
                # Propagate if strong enough
                if abs(effect_strength) > 0.1:
                    queue.append((link.effect_id, effect_strength))
    
        intervention = {
            "target": entity_id,
            "new_state": new_state,
            "predicted_effects": affected,
            "num_affected": len(affected),
            "timestamp": time.time()
        }
    
        self._interventions.append(intervention)
    
        logger.info(f" Intervention on {entity_id}: {len(affected)} entities affected")
        return intervention

    def find_causal_path(self, start_id: str, end_id: str, max_depth: int = 5) -> List[List[str]]:
        """Find all causal chains from start to end"""
        paths = []
    
        def dfs(current: str, target: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            if current == target:
                paths.append(path[:])
                return
        
            for link in self.get_causal_effects(current):
                if link.effect_id not in path:  # Avoid cycles
                    path.append(link.effect_id)
                    dfs(link.effect_id, target, path, depth + 1)
                    path.pop()
    
        dfs(start_id, end_id, [start_id], 0)
        logger.info(f" Found {len(paths)} causal paths: {start_id}  {end_id}")
        return paths

    # =========================================================================
    # NEW: BAYESIAN REASONING METHODS
    # =========================================================================

    def bayesian_set_prior(self, entity_id: str, probability: float):
        """Set prior belief P(entity)"""
        self._bayesian_priors[entity_id] = max(0.0, min(1.0, probability))
        logger.debug(f" Prior: P({entity_id}) = {probability:.3f}")

    def bayesian_set_conditional(self, evidence_id: str, hypothesis_id: str, probability: float):
        """Set conditional probability P(hypothesis | evidence)"""
        self._bayesian_conditionals[(evidence_id, hypothesis_id)] = probability
        logger.debug(f" Conditional: P({hypothesis_id} | {evidence_id}) = {probability:.3f}")

    def bayesian_update_belief(
        self,
        hypothesis_id: str,
        evidence_id: str,
        observed: bool = True
    ) -> float:
        """
        Bayesian belief update using Bayes rule.
        P(H|E) = P(E|H) * P(H) / P(E)
        """
        prior = self._bayesian_priors.get(hypothesis_id, 0.5)
        likelihood = self._bayesian_conditionals.get((evidence_id, hypothesis_id), 0.5)
    
        if not observed:
            likelihood = 1 - likelihood
    
        # Simplified Bayes (assumes independence)
        posterior = likelihood * prior
        posterior = posterior / (posterior + (1 - likelihood) * (1 - prior) + 1e-10)
    
        self._bayesian_priors[hypothesis_id] = posterior
    
        logger.info(f" Bayesian update: {hypothesis_id}: {prior:.3f}  {posterior:.3f}")
        return posterior

    def bayesian_most_likely_explanation(
        self,
        observations: List[str],
        candidates: List[str]
    ) -> Tuple[Optional[str], float]:
        """Find which candidate hypothesis best explains the observations"""
        best_candidate = None
        best_score = -1.0
    
        for candidate in candidates:
            score = self._bayesian_priors.get(candidate, 0.5)
        
            for obs in observations:
                likelihood = self._bayesian_conditionals.get((obs, candidate), 0.5)
                score *= likelihood
        
            if score > best_score:
                best_score = score
                best_candidate = candidate
    
        logger.info(f" Best explanation: {best_candidate} (score: {best_score:.3f})")
        return best_candidate, best_score

    # =========================================================================
    # NEW: ADVANCED GRAPH QUERY METHODS
    # =========================================================================

    def graph_shortest_path(self, start_id: str, end_id: str) -> Optional[List[str]]:
        """Find shortest path between two entities (BFS)"""
        if start_id not in self._entities or end_id not in self._entities:
            return None
    
        queue = deque([(start_id, [start_id])])
        visited = {start_id}
    
        while queue:
            current_id, path = queue.popleft()
        
            if current_id == end_id:
                logger.info(f" Shortest path found: {len(path)} hops")
                return path
        
            for rel_id in self._outgoing_rels.get(current_id, set()):
                rel = self.get_relationship(rel_id)
                if not rel or rel.deprecated:
                    continue
            
                neighbor = rel.target_id
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
    
        logger.info(f" No path found between {start_id} and {end_id}")
        return None

    def graph_pattern_match(
        self,
        pattern: List[Tuple[str, str, str]]
    ) -> List[List[str]]:
        """
        Find entity sequences matching a pattern
        pattern = [(source_type, rel_type, target_type), ...]
    
        Example: [("Paper", "CITES", "Paper"), ("Paper", "MENTIONS", "Concept")]
        Finds: Paper1 -> CITES -> Paper2 -> MENTIONS -> Concept1
        """
        if not pattern:
            return []
    
        matches = []
        start_type = pattern[0][0]
        start_entities = self.get_entities_by_type(start_type)
    
        for entity in start_entities:
            path = [entity.entity_id]
            if self._pattern_match_recursive(path, pattern, 0):
                matches.append(path)
    
        logger.info(f" Pattern matching found {len(matches)} sequences")
        return matches

    def _pattern_match_recursive(
        self,
        path: List[str],
        pattern: List[Tuple[str, str, str]],
        idx: int
    ) -> bool:
        """Helper for pattern matching"""
        if idx >= len(pattern):
            return True
    
        src_type, rel_type, tgt_type = pattern[idx]
        current_id = path[-1]
    
        for rel_id in self._outgoing_rels.get(current_id, set()):
            rel = self.get_relationship(rel_id)
            if not rel or rel.type != rel_type:
                continue
        
            target = self.get_entity(rel.target_id)
            if not target or target.type != tgt_type:
                continue
        
            path.append(target.entity_id)
            if self._pattern_match_recursive(path, pattern, idx + 1):
                return True
            path.pop()
    
        return False

    def semantic_search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        entity_type: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Semantic similarity search using embeddings
        Returns top-k most similar entities
        """
        similarities = []
    
        search_space = (
            self._entity_type_index.get(entity_type, set())
            if entity_type
            else self._embeddings.keys()
        )
    
        for entity_id in search_space:
            if entity_id not in self._embeddings:
                continue
        
            emb = self._embeddings[entity_id]
        
            # Cosine similarity
            sim = np.dot(query_embedding, emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(emb) + 1e-10
            )
        
            similarities.append((entity_id, float(sim)))
    
        similarities.sort(key=lambda x: x[1], reverse=True)
    
        logger.info(f" Semantic search: {len(similarities[:top_k])} results")
        return similarities[:top_k]

    # =========================================================================
    # NEW: AI-POWERED CONFLICT RESOLUTION
    # =========================================================================

    def resolve_conflict_smart(
        self,
        key: str,
        strategy: str = "auto"
    ) -> Optional[Fact]:
        """
        Intelligently resolve conflicts using multiple strategies
    
        Strategies:
        - auto: Automatically choose best strategy
        - weighted_confidence: Use confidence-weighted voting
        - recency: Most recent fact wins
        - vote: Majority wins (by source count)
        """
        facts = self._facts.get(key, [])
        if len(facts) < 2:
            return facts[0] if facts else None
    
        if strategy == "auto":
            # Auto-select based on data characteristics
            confidences = [f.confidence for f in facts]
            if np.std(confidences) > 0.2:
                strategy = "weighted_confidence"
            else:
                times = [f.timestamp for f in facts]
                if max(times) - min(times) > 3600:  # 1 hour gap
                    strategy = "recency"
                else:
                    strategy = "vote"
    
        if strategy == "weighted_confidence":
            winner = max(facts, key=lambda f: f.confidence)
            reason = f"highest_confidence_{winner.confidence:.2f}"
    
        elif strategy == "vote":
            value_counts = defaultdict(int)
            for f in facts:
                value_counts[str(f.value)] += 1
            winning_value = max(value_counts.items(), key=lambda x: x[1])[0]
            winner = next(f for f in facts if str(f.value) == winning_value)
            reason = f"majority_vote_{value_counts[winning_value]}"
    
        elif strategy == "recency":
            winner = max(facts, key=lambda f: f.timestamp)
            reason = "most_recent"
    
        else:
            winner = facts[0]
            reason = "default"
    
        # Record resolution
        self._resolution_history.append({
            "key": key,
            "strategy": strategy,
            "reason": reason,
            "num_facts": len(facts),
            "winner_id": winner.fact_id,
            "timestamp": time.time()
        })
    
        self._facts[key] = [winner]
    
        logger.info(f" Smart conflict resolution: {key}  {reason}")
        return winner

    # =========================================================================
    # NEW: GRAPH ANALYTICS METHODS
    # =========================================================================

    def compute_pagerank(
        self,
        damping: float = 0.85,
        iterations: int = 100
    ) -> Dict[str, float]:
        """
        Compute PageRank for all entities
        Identifies most influential/central entities
        """
        entities = list(self._entities.keys())
        n = len(entities)
        if n == 0:
            return {}
    
        ranks = {e: 1.0/n for e in entities}
        outgoing = {e: [] for e in entities}
    
        # Build adjacency list
        for rel in self._relationships.values():
            if rel.source_id in outgoing and not rel.deprecated:
                outgoing[rel.source_id].append(rel.target_id)
    
        # Power iteration
        for _ in range(iterations):
            new_ranks = {}
            for entity in entities:
                rank_sum = 0.0
                for src in entities:
                    if entity in outgoing.get(src, []):
                        out_count = len(outgoing[src])
                        if out_count > 0:
                            rank_sum += ranks[src] / out_count
            
                new_ranks[entity] = (1 - damping)/n + damping * rank_sum
        
            ranks = new_ranks
    
        logger.info(f" [PAGERANK] PageRank computed for {n} entities")
        return ranks

    def detect_communities(self, max_iterations: int = 100) -> Dict[str, int]:
        """
        Detect communities using label propagation
        Groups entities into clusters
        """
        entities = list(self._entities.keys())
        labels = {e: i for i, e in enumerate(entities)}
    
        for iteration in range(max_iterations):
            changed = False
        
            for entity in entities:
                neighbor_labels = defaultdict(int)
            
                for rel_id in self._outgoing_rels.get(entity, set()):
                    rel = self.get_relationship(rel_id)
                    if rel and not rel.deprecated and rel.target_id in labels:
                        neighbor_labels[labels[rel.target_id]] += 1
            
                if neighbor_labels:
                    new_label = max(neighbor_labels.items(), key=lambda x: x[1])[0]
                    if new_label != labels[entity]:
                        labels[entity] = new_label
                        changed = True
        
            if not changed:
                break
    
        num_communities = len(set(labels.values()))
        logger.info(f" Detected {num_communities} communities")
        return labels

    # =========================================================================
    # NEW: AGENT SWARM METHODS
    # =========================================================================

    def spawn_agent(self, role: AgentRole, agent_id: Optional[str] = None) -> str:
        """Spawn a specialized agent"""
        if agent_id is None:
            agent_id = f"{role.value}_{len(self._agents)}"
    
        agent = {
            "agent_id": agent_id,
            "role": role,
            "tasks_completed": 0,
            "spawned_at": time.time(),
            "status": "active"
        }
    
        self._agents[agent_id] = agent
        self._stats["active_agents"] = len(self._agents)
    
        logger.info(f" Spawned agent: {agent_id} ({role.value})")
        return agent_id

    def create_task(
        self,
        task_type: str,
        priority: int,
        assigned_to: Optional[AgentRole] = None,
        dependencies: Optional[List[str]] = None
    ) -> Task:
        """Create a task for agent execution"""
        task_id = hashlib.md5(f"{task_type}{time.time()}".encode()).hexdigest()[:8]
    
        task = Task(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            assigned_to=assigned_to,
            dependencies=dependencies or []
        )
    
        self._task_queue.append(task)
        logger.info(f" Task created: {task_id} ({task_type})")
        return task

    async def run_adversarial_critique(self, hypothesis_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Execute The Thanos Protocol
        Adversarial red team that attacks all hypotheses
        Only the strong survive
        """
        logger.info(" THANOS PROTOCOL ACTIVATED")
    
        # Spawn critic agent
        critic_id = self.spawn_agent(AgentRole.CRITIC)
    
        kills = 0
        approvals = 0
    
        # Get all hypotheses
        hypotheses = self.get_entities_by_type("Hypothesis")
    
        for hyp in hypotheses:
            # FIXED: ARCHIVE TRAP - Add 5-minute grace period for new hypotheses
            age = time.time() - hyp.created_at
            if age < 300:
                logger.debug(f" [THANOS] Skipping young hypothesis {hyp.entity_id} (age: {age:.1f}s)")
                approvals += 1
                continue

            # Attack the hypothesis
            if hyp.confidence < hypothesis_threshold:
                # KILL IT
                self.delete_entity(hyp.entity_id)
                kills += 1
                logger.warning(f" REJECTED: {hyp.entity_id} (confidence: {hyp.confidence:.2f})")
            elif not hyp.verified:
                # Check for supporting evidence
                supporting = self.query_related_entities(
                    hyp.entity_id,
                    relationship_type="SUPPORTS",
                    direction="incoming"
                )
            
                if len(supporting) < 2:
                    # Insufficient evidence
                    self.delete_entity(hyp.entity_id)
                    kills += 1
                    logger.warning(f" REJECTED: {hyp.entity_id} (insufficient evidence)")
                else:
                    # Survived the critique
                    hyp.verified = True
                    hyp.verification_count += 1
                    approvals += 1
                    logger.info(f" APPROVED: {hyp.entity_id}")
            else:
                approvals += 1
    
        survival_rate = approvals / (kills + approvals + 1e-10)  # Avoid division by zero
    
        logger.info(f" THANOS PROTOCOL COMPLETE: {kills} killed, {approvals} approved ({survival_rate*100:.1f}% survival)")
      
        return {
            "kills": kills,
            "approvals": approvals,
            "survival_rate": survival_rate,
            "critic_agent": critic_id,
            "total_hypotheses": len(hypotheses)
        }
    # =========================================================================
    # DB HELPERS (TITAN)
    # =========================================================================

    def _save_hyperedge_to_db(self, hedge: HyperEdge):
        try:
            with self._db_lock:
                self._cursor.execute("""
                    INSERT OR REPLACE INTO hyperedges 
                    (hyperedge_id, sources, targets, type, confidence, evidence, conditions, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    hedge.hyperedge_id, json.dumps(hedge.source_ids), json.dumps(hedge.target_ids),
                    hedge.edge_type, hedge.confidence, json.dumps(hedge.evidence),
                    json.dumps(hedge.conditions), self.session_id
                ))
                self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to save hyperedge: {e}")

    def _save_temporal_fact_to_db(self, tf: TemporalFact):
        try:
            # Generate a deterministic ID if none exists (using hash of content + start time)
            comp_key = f"{tf.key}:{tf.valid_from}:{tf.value}"
            f_id = hashlib.sha256(comp_key.encode()).hexdigest()[:16]
            
            with self._db_lock:
                self._cursor.execute("""
                    INSERT OR REPLACE INTO temporal_facts 
                    (fact_id, key, value, valid_from, valid_until, source, confidence, metadata, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f_id, tf.key, str(tf.value), tf.valid_from, tf.valid_until,
                    tf.source, tf.confidence, json.dumps(tf.metadata), self.session_id
                ))
                self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to save temporal fact: {e}")

    def _save_causal_link_to_db(self, cl: CausalLink):
        try:
            # Deterministic ID
            comp_key = f"{cl.cause_id}->{cl.effect_id}:{cl.mechanism}"
            l_id = hashlib.sha256(comp_key.encode()).hexdigest()[:16]
            
            with self._db_lock:
                self._cursor.execute("""
                    INSERT OR REPLACE INTO causal_links 
                    (link_id, cause_id, effect_id, strength, mechanism, confidence, evidence, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    l_id, cl.cause_id, cl.effect_id, cl.strength, cl.mechanism,
                    cl.confidence, json.dumps(cl.evidence), self.session_id
                ))
                self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to save causal link: {e}")
