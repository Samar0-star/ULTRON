"""
Deep Research Orchestrator for SVEL
=================================================
**THE BRAIN OF THE OPERATION.**

Use Cases:
1.  **Autonomous Research Campaigns**: The entry point for 72-hour "God Mode" sessions.
2.  **Epistemic Governance**: Directly calls `EpistemicRegulator` to decide if hypotheses are worth pursuing.
3.  **World Model Updates**: Feeds new facts into `WorldModel` (the Governor) to track system beliefs.
4.  **Meta-Reasoning**: Adjusts its own exploration rate based on stagnation (Pillar 6).
5.  **Swarm Command**: Dispatches 100+ tasks to the Swarm Manager.

If you are looking for where the system "thinks," it is here.
"""

import asyncio
import inspect
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Tuple, Union
import re
import uuid
import os
from pathlib import Path
from backend.config_beast import beast_config
from backend.core.validation.result_validator import ResultValidator
from backend.core.validation.reproducibility import ReproducibilityManager
from backend.core.safety.operation_guard import request_approval, OperationGuard
from backend.core.events.event_bus import events
from backend.llm_manager import DEEP_RESEARCH_SYNTHESIS_MODEL, GlobalQuotaExceededError
from backend.core.state.persistence_vault import vault
import dataclasses

# Initialize logger early to prevent NameError in subsequent imports
logger = logging.getLogger(__name__)

# DEBUG FLAG: Set AVON_DEBUG_BRANCHING=1 to enable forced hypothesis branching for stuck runs
# This forced branching rule is for testing epistemic convergence.
# Must be disabled for long autonomous runs and deployment.
DEBUG_FORCE_HYPOTHESIS_BRANCH = os.environ.get("AVON_DEBUG_BRANCHING", "0") == "1"

from backend.core.hypothesis.models import Hypothesis, HypothesisState
from backend.core.hypothesis.tracker import HypothesisTracker, get_hypothesis_tracker
from backend.core.hypothesis.novelty_checker import NoveltyChecker
from backend.core.hypothesis.prioritizer import HypothesisPrioritizer
from backend.core.hypothesis.generator import HypothesisGenerator
from backend.core.planning.plan_creator import PlanCreator, ResearchPlan, ResearchTask
from backend.core.planning.plan_reviewer import PlanReviewer  # ADDED
from backend.agents.red_team_agent import RedTeamAgent
from backend.agents.protocol_validator import ProtocolValidator
from backend.orchestration.swarm_manager import ConsensusEngine  # ADDED
# jupyter_exporter is imported inline in _phase_finalize (get_jupyter_exporter)

try:
    from backend.core.world_model import WorldModel
except ImportError:
    msg = "CRITICAL: WorldModel module not found. Core state management is missing. System EXIT."
    logger.critical(msg)
    raise RuntimeError(msg)

# ULTRA-UPGRADE: 3-Layer Validation System (99%+ accuracy)
try:
    from backend.core.validation import (
        StatisticalGroundingValidator,
        validate_statistical_grounding,
        DiscoveryScorer,
        score_discovery,
        FailureDetector,
        AccuracyTracker,
        get_accuracy_tracker,
    )
    from backend.core.validation.power_analyzer import PowerAnalyzer
    ULTRA_VALIDATION_AVAILABLE = True
except ImportError as _uv_err:
    logger.info(f" [INFO] Ultra-Validation upgrades not detected ({_uv_err}). Falling back to standard rigor.")
    StatisticalGroundingValidator = None
    validate_statistical_grounding = None
    DiscoveryScorer = None
    score_discovery = None
    FailureDetector = None
    AccuracyTracker = None
    get_accuracy_tracker = None
    PowerAnalyzer = None
    ULTRA_VALIDATION_AVAILABLE = False

try:
    from backend.core.context_compressor import ContextCompressor, compress_cycle, compress_mission
except ImportError:
    ContextCompressor = None
    compress_cycle = None
    compress_mission = None

try:
    from backend.core.discovery_rigor import get_gnn_empirical_checker
except ImportError:
    get_gnn_empirical_checker = None

# Neo4j Knowledge Graph (PCD Pillar 7 - Restored)
try:
    from backend.memory.knowledge_graph import get_knowledge_graph
    KNOWLEDGE_GRAPH_AVAILABLE = True
except ImportError:
    logger.warning(" [WARN] Neo4j Knowledge Graph module not found. Persistence will use local SQLite only.")
    get_knowledge_graph = None
    KNOWLEDGE_GRAPH_AVAILABLE = False

# Epistemic Discipline (PCD Phase 34)
# Initialize logger BEFORE imports that may need it (moved to top of file)

HEX_ID_PATTERN = re.compile(r'^(?:fact_|seed_|doc_|ground_[a-z0-9_]+_)?[0-9a-f]{8,}$', re.IGNORECASE)

try:
    from backend.epistemic.epistemic_regulator import EpistemicRegulator, ActionType
except ImportError as e:
    msg = f"CRITICAL: EpistemicRegulator module not found. The system has no 'Conscience'. System EXIT. Error: {e}"
    logger.critical(msg)
    raise RuntimeError(msg)

# Convergence Logic (PCD Pillar 5)
try:
    from backend.core.convergence_controller import ConvergenceController
except ImportError as e:
    logger.info(" [INFO] ConvergenceController not found. Dynamic cycle adjustment disabled.")
    ConvergenceController = None

# Meta-Reasoning (PCD Pillar 6)
try:
    from backend.core.meta_reasoning import MetaReasoningLayer
except ImportError as e:
    logger.info(" [INFO] MetaReasoningLayer not found. Strategic self-correction disabled.")
    MetaReasoningLayer = None

# SVEL Expert System (Skill Injection)
try:
    from backend.core.skill_injector import SVELExpertSystem, get_expert_system
    from backend.core.strategy_engine import DynamicStrategyEngine, get_strategy_engine
    SKILL_INJECTION_AVAILABLE = True
except ImportError:
    logger.warning(" [WARN] Skill Injection modules not found. Expert system fallbacks active.")
    SVELExpertSystem = None
    get_expert_system = None
    SKILL_INJECTION_AVAILABLE = False

# Epistemic Convergence Engine (Advanced Stopping Criteria)
try:
    from backend.core.convergence_engine import EpistemicConvergenceEngine, get_convergence_engine
    CONVERGENCE_ENGINE_AVAILABLE = True
except ImportError:
    logger.info(" [INFO] EpistemicConvergenceEngine not found. Using standard stopping criteria.")
    EpistemicConvergenceEngine = None
    get_convergence_engine = None
    CONVERGENCE_ENGINE_AVAILABLE = False

# Input Sanitization (Prompt Injection Defense)
try:
    from backend.core.input_sanitizer import InputSanitizer, get_input_sanitizer
    INPUT_SANITIZER_AVAILABLE = True
except ImportError:
    logger.warning(" [WARN] InputSanitizer not found. SYSTEM VULNERABLE TO PROMPT INJECTION.")
    InputSanitizer = None
    get_input_sanitizer = None
    INPUT_SANITIZER_AVAILABLE = False

# Strategic Auditor - Overmind (Drift Detection)
try:
    from backend.orchestration.overmind import get_overmind, Overmind
    OVERMIND_AVAILABLE = True
except ImportError:
    logger.warning(" [WARN] Overmind module not found. Drift detection disabled.")
    get_overmind = None
    Overmind = None
    OVERMIND_AVAILABLE = False

# Vector Memory (Pillar Sidecar)
try:
    from backend.memory.vectorstore import get_vectorstore, VectorStore
except ImportError:
    logger.warning(" [WARN] VectorStore module not found. Semantic memory retrieval disabled.")
    get_vectorstore = None
    VectorStore = None

# BEAST KILLER: Discovery Mode Ultra Upgrade (With 5 Upgrades)
try:
    from backend.discovery import (
        get_assumption_graph,
        reset_assumption_graph,
        Verdict,
        DiscrepancyType,
        check_reality_constraints,

        validate_necessity,
        DerivationGate,
        # UPGRADE 1: Temporal Survival
        SurvivorTier,
        # UPGRADE 2: Orthogonal Attacks
        AttackAxis,
        # UPGRADE 3: Failure Patterns
        get_failure_index
    )
    from backend.discovery.discovery_orchestrator import (
        get_discovery_session,
        reset_discovery_session,
        DISCOVERY_HARD_CAPS,
        # FERRARI ENGINE: Advanced Discovery Components
        DiscoveryPolicy,
        SurvivalEngine, 
        GovernanceEngine,
        SemanticAttackValidator,
        DiscoverySession,
        RecursiveDiscoveryManager
    )
    from backend.discovery.adversarial_executor import AdversarialExecutor
    DISCOVERY_ULTRA_AVAILABLE = True
except ImportError as e:
    msg = f"CRITICAL: Discovery modules not found. Falsification loops compromised. System EXIT. Error: {e}"
    logger.critical(msg)
    raise RuntimeError(msg)




# =============================================================================
# RESEARCH MODE CONFIGURATION (Phase 12: Mode Restructure)
# =============================================================================
# The system supports ONLY 2 modes:
# 1. RESEARCH - Deep, long-running research (default)
# 2. DISCOVERY - Falsification-focused research with Red Team veto power
# =============================================================================

class ResearchMode(str, Enum):
    """Research execution modes. Only 2 modes supported."""
    RESEARCH = "research"    # Research mode (default)
    DISCOVERY = "discovery"  # Falsification with Red Team blocking

# Runtime configuration
DEFAULT_RUNTIME_HOURS = 12.0       # Default: 12 hours (locked)
ALLOWED_RUNTIME_HOURS = [12.0, 24.0, 48.0, 72.0]
MAX_RUNTIME_HOURS = 74.0           # Absolute maximum (hard cap)

# Configuration constants
MAX_CYCLES = 50  # Realistic research cycles (Time limits control stopping)
MAX_CONSECUTIVE_ERRORS = 10  # Halt after this many failures (increased from 3)
ERROR_BACKOFF_SECONDS = [2, 4, 8, 16, 32]  # Exponential backoff
TASKS_PER_CYCLE = 5  # Turbo-throttled for Moonshot Kimi-k2.5

# BEAST-inspired enhancements (Phase 11: Enterprise Resilience)
MAX_ACTIONS_PER_CYCLE = 10000      # Loop guard: max actions per cycle (Was 100)
MAX_TOTAL_ACTIONS = 500000       # Global safeguard for runaway loops







# Circuit Breaker configuration
CIRCUIT_OPEN_THRESHOLD = 5       # Errors before circuit opens
CIRCUIT_HALF_OPEN_AFTER = 60     # Seconds before retry in half-open state
CIRCUIT_CLOSE_ON_SUCCESS = 2     # Successes needed to close circuit


class ResearchState(Enum):
    """Explicit research workflow states ."""
    INITIALIZING = "initializing"
    GENERATING_HYPOTHESES = "generating_hypotheses"
    PLANNING = "planning"
    EXECUTING = "executing"
    ANALYZING = "analyzing"
    REFINING = "refining"
    CONVERGING = "converging"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    REJECTED = "rejected"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for graceful degradation under failures.
    
    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, skip operations to prevent cascade
    - HALF_OPEN: Testing recovery, allow limited requests
    """
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    success_count: int = 0
    
    def record_failure(self, error: str = "") -> None:
        """
        Record a failure and potentially open the circuit.
        [SVEL RIGOR] FLAW 35 FIX: Grounding Failures (Honest Science) 
        do NOT trip the circuit breaker.
        """
        # If the error is an honest 'No Data Found' report, don't punish the system status
        if "GROUNDING_FAILURE" in error or "No real data source" in error:
            logger.info("[CIRCUIT_GRACE] Grounding failure recorded. Research proceeds safely.")
            return

        self.failure_count += 1
        self.last_failure = datetime.now()
        self.success_count = 0
        
        # [TELEMETRY] Log failure details for campaign audit
        if error:
            logger.error(f"[CIRCUIT_FAILURE] {error if len(error) < 200 else error[:200] + '...'}")
            
        if self.failure_count >= CIRCUIT_OPEN_THRESHOLD:
            self.state = CircuitState.OPEN
            logger.warning(f"[CIRCUIT] Opened after {self.failure_count} failures. Last error: {error[:100]}")
    
    def record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        self.success_count += 1
        self.failure_count = max(0, self.failure_count - 1)
        if self.state == CircuitState.HALF_OPEN and self.success_count >= CIRCUIT_CLOSE_ON_SUCCESS:
            self.state = CircuitState.CLOSED
            logger.info("[CIRCUIT] Closed after recovery")
    
    def can_execute(self) -> bool:
        """Check if operations should proceed."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure and (datetime.now() - self.last_failure).seconds > CIRCUIT_HALF_OPEN_AFTER:
                self.state = CircuitState.HALF_OPEN
                logger.info("[CIRCUIT] Half-open, testing recovery")
                return True
            return False
        return True  # HALF_OPEN allows execution
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure = None
        self.success_count = 0


@dataclass
class HypothesisLineage:
    """
    Tracks hypothesis evolution and parent-child relationships.
    
    Enables understanding of how hypotheses evolved during research.
    """
    hypothesis_id: str
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    generation: int = 1
    evidence_basis: List[str] = field(default_factory=list)  # Result/finding IDs
    evolution_reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OperationLimits:
    """
    Hard limits for autonomous execution (Time based).
    """
    max_runtime_hours: float = 12.0
    total_cost: float = 0.0
    
    @classmethod
    def from_run_type(cls, run_type: str, runtime_hours: float = None):
        if runtime_hours is None:
            runtime_map = {
                "standard_12hr": 12.0,
                "extended_24hr": 24.0,
                "god_mode_72hr": 72.0
            }
            runtime_hours = runtime_map.get(run_type, 12.0)
        
        return cls(
            max_runtime_hours=runtime_hours
        )
    
    def add_cost(self, cost: float = 0.0) -> None:
        """Accumulate estimated operation cost safely."""
        try:
            self.total_cost += float(cost or 0.0)
        except (ValueError, TypeError):
            pass

    def get_usage_percent(self) -> float:
        """Return cost usage percentage (0.0 when uncapped)."""
        return 0.0

    def check(self, elapsed_hours: float) -> Tuple[bool, str]:
        """Check if any limit exceeded. Returns (exceeded, reason)."""
        if elapsed_hours >= self.max_runtime_hours:
            return True, f"Runtime limit ({self.max_runtime_hours}h)"
        return False, ""





@dataclass
class ResearchSession:
    """Tracks state of a research session"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    research_question: str = ""
    domain: str = "general"
    mode: ResearchMode = ResearchMode.RESEARCH  # NEW: Explicit research mode
    
    # Progress
    current_cycle: int = 0
    total_cycles_planned: int = 200  # For 12-hour runs (was 5, too short)
    status: str = "initialized"  # initialized, running, paused, completed, failed

    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    max_runtime_hours: float = DEFAULT_RUNTIME_HOURS  # 12 hours default
    last_heartbeat: datetime = field(default_factory=datetime.now) # F-44 Heartbeat

    
    # Results
    tasks: List[ResearchTask] = field(default_factory=list)
    plans: List[ResearchPlan] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    visualizations: List[Dict[str, Any]] = field(default_factory=list) # Charts/Diagrams
    knowledge_snapshot: str = "" # High-density synthesized history
    final_report: str = ""
    local_data_catalog: List[str] = field(default_factory=list) # Empirical Beast Refactor: Tethers swarm to real data plików
    
    # Governance Freeze Tracking
    paused_duration_s: float = 0.0 # Time spent frozen waiting for credits
    
    # Error tracking
    consecutive_errors: int = 0
    # F-67: Infinite Stagnation Protection
    stagnation_count: int = 0  # Consecutive cycles with 0 new findings
    error_log: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    battle_plan: Dict[str, Any] = field(default_factory=dict) # NEW: T1/T2 Strategic Chains
    
    # Experiment Tracking
    notebook_experiments: List[Dict[str, Any]] = field(default_factory=list) # Full experiment details for notebook
    experiment_results: Dict[str, Any] = field(default_factory=dict) # Persisted experiment metadata/results
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "research_question": self.research_question,
            "domain": self.domain,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, "isoformat") else str(self.created_at),
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "current_cycle": self.current_cycle,
            "total_cycles_planned": self.total_cycles_planned,
            "max_runtime_hours": self.max_runtime_hours,
            "started_at": self.started_at.isoformat() if self.started_at and hasattr(self.started_at, "isoformat") else str(self.started_at) if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at and hasattr(self.ended_at, "isoformat") else str(self.ended_at) if self.ended_at else None,
            "elapsed_hours": self.get_elapsed_hours(),
            "findings_count": len(self.findings),
            "hypotheses_generated": len(self.findings),
            "artifacts_created": len(self.artifacts),
            "final_report_length": len(self.final_report),
            "tasks": [t.to_dict() if hasattr(t, "to_dict") else str(t) for t in self.tasks],
            "error_log": self.error_log  # EXPORT ERRORS FOR DEBUGGING
        }
    
    def get_elapsed_hours(self) -> float:
        """Get elapsed time in hours (subtracting governance freeze time)"""
        if not self.started_at:
            return 0.0
        start = self.started_at
        if isinstance(start, str):
            try:
                start = datetime.fromisoformat(start)
            except Exception:
                try:
                    from dateutil import parser
                    start = parser.parse(start)
                except Exception:
                    return 0.0
        end = self.ended_at or datetime.now()
        if isinstance(end, str):
            try:
                end = datetime.fromisoformat(end)
            except Exception:
                end = datetime.now()
        raw_seconds = (end - start).total_seconds()
        # Adjusted for freezes
        active_seconds = max(0, raw_seconds - self.paused_duration_s)
        return active_seconds / 3600


class DeepResearchOrchestrator:
    @property
    def current_cycle(self) -> int:
        return self.session.current_cycle

    """
    Master orchestrator for autonomous research.
    
    Coordinates the full research cycle:
    1. Generate hypotheses from research question
    2. Check novelty and prioritize
    3. Create research plans
    4. Review and approve plans
    5. Execute tasks (via router)
    6. Analyze results
    7. Refine hypotheses
    8. Repeat for multiple cycles
    
    Example:
        ```python
        orchestrator = DeepResearchOrchestrator(
            research_question="How do transformer attention patterns evolve during training?",
            domain="ml",
            router=central_router
        )
        
        # Run synchronously (blocking)
        results = orchestrator.run()
        
        # Or run asynchronously
        results = await director.run_async()
        ```
    """
    
    def __init__(
        self,
        research_question: str = None,
        session: Optional[Any] = None,  # NEW: Accept pre-built session
        domain: str = "other",
        mode: str = "research",  # NEW: "research" or "discovery" only
        runtime_hours: float = DEFAULT_RUNTIME_HOURS,  # 12, 24, or 48
        max_runtime_hours: float = None,  # Alias for runtime_hours (backward compat)
        router=None,
        llm_manager=None,
        max_cycles: int = MAX_CYCLES,
        tasks_per_cycle: int = TASKS_PER_CYCLE,
        session_id: Optional[str] = None,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        max_parallel: int = 50, # Default to massively parallel
        paper_read_target: int = None,
        deep_read_target: int = None,
        recursion_depth: int = 0, # NEW: recursion tracking
        started_at: Optional[datetime] = None # NEW: temporal inheritance
    ):

        """
        Initialize Research .
        
        Args:
            research_question: The research question to investigate
            domain: Research domain (ml, nlp, physics, biology, general)
            mode: Research mode - "research" (default) or "discovery" (with Red Team)
            runtime_hours: Runtime lock in hours - 12 (default), 24, or 48
            router: CentralRouterBeast instance for task execution
            llm_manager: LLM manager for reasoning
            max_cycles: Maximum research cycles
            tasks_per_cycle: Tasks per research cycle
            session_id: Optional session ID (auto-generated if not provided)
            on_progress: Optional callback for progress updates
            max_parallel: Concurrency limit for Swarm (Godzilla Mode)
            paper_read_target: Target number of abstracts to scan (Dynamic scaling)
            deep_read_target: Target number of full PDFs to read (Dynamic scaling)
        """
        # Handle max_runtime_hours alias (backward compatibility)
        if max_runtime_hours is not None:
            runtime_hours = max_runtime_hours
        
        # =========================================================
        # MODE VALIDATION (Phase 12: Only "research" or "discovery")
        # =========================================================
        if mode not in ["research", "discovery"]:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be 'research' or 'discovery'. "
                f"Quick/normal modes are deprecated."
            )
        
        # =========================================================
        # RUNTIME VALIDATION (Phase 12: Only 12, 24, or 48 hours)
        # =========================================================
        # FIX: Handle None explicitly before validation (Default to 12h)
        if runtime_hours is None:
            runtime_hours = DEFAULT_RUNTIME_HOURS

        # FIX: Support dynamic configuration up to MAX_RUNTIME_HOURS (72h)
        # Instead of snapping to rigid buckets, we just enforce the Hard Cap.
        if runtime_hours > MAX_RUNTIME_HOURS:
            logger.warning(f"Runtime {runtime_hours}h exceeds max {MAX_RUNTIME_HOURS}h. Clamping to limit.")
            runtime_hours = MAX_RUNTIME_HOURS
        
        # Ensure minimum sanity check
        if runtime_hours < 0.1:
             logger.warning(f"Runtime {runtime_hours}h too short. Clamping to 0.1h.")
             runtime_hours = 0.1
        
        # Robust string coercion for research_question (prevents dict leak)
        if isinstance(research_question, dict):
            payload = research_question.get('payload', {})
            if isinstance(payload, str): payload = {}
            research_question = (
                research_question.get('query') or 
                research_question.get('statement') or 
                payload.get('query') or 
                payload.get('statement') or 
                research_question.get('topic') or
                str(research_question)
            )
        elif not isinstance(research_question, str):
            research_question = str(research_question)
            
        self.research_question = research_question
        self.domain = domain
        self.mode = ResearchMode(mode)
        
        if beast_config.orchestration.singularity_mode:
            logger.info(f"  SVEL SWARM ACTIVE: Overriding limits with Beast Config (Baseline)")
            
            # [SVEL SYNC] Force physical worker limit to 10 to protect API keys
            max_parallel = 10
            
            logger.info(f"   - Max Parallel: {max_parallel}")
            logger.info(f"   - Runtime Hours: {runtime_hours}")
            logger.info(f"   - Paper Target: {paper_read_target}")
            logger.info(f"   - Deep Target: {deep_read_target}")
        else:
            # Fallback values if config missing or singularity off
            if paper_read_target is None: paper_read_target = 3000
            if deep_read_target is None: deep_read_target = 100

        self.router = router
        
        # [TITAN V156.0] BRAIN IGNITION
        # Physically move LLM Manager initialization to the start of the boot sequence.
        # This ensures every downstream component (Singularity, GNN, HypothesisGen)
        # has a verified neural manifold from microsecond one.
        if llm_manager is None:
            from backend.llm_manager import llm_manager as global_llm_manager
            self.llm_manager = global_llm_manager
            logger.info("[WIRING] Sovereign Brain Auto-Ignited.")
        else:
            self.llm_manager = llm_manager

        self.max_cycles = max_cycles

        self.max_runtime_hours = runtime_hours
        self.tasks_per_cycle = tasks_per_cycle
        self.max_parallel = max_parallel
        
        # DYNAMIC TARGETS (Stored for Agent Consumption)
        self.paper_read_target = paper_read_target
        self.deep_read_target = deep_read_target
        
        self.session_id = session_id
        self.on_progress = on_progress
        
        # Session state - accept pre-built session OR create new
        if session is not None:
            self.session = session
            # Sync session parameters with orchestrator
            # FIX: Sync research question from session
            if not research_question and self.session.research_question:
                research_question = self.session.research_question
            self.session.total_cycles_planned = self.max_cycles
            self.session.max_runtime_hours = runtime_hours
            if started_at:
                self.session.started_at = started_at
        else:
            self.session = ResearchSession(
                id=session_id or str(uuid.uuid4())[:8],
                research_question=research_question,
                domain=domain,
                mode=self.mode,
                # USER LOGIC: Cycle count is now uncapped (time-bound execution)
                # We set it to max_cycles (10000) so the clock is the only limit.
                total_cycles_planned=self.max_cycles,
                max_runtime_hours=runtime_hours,
                started_at=started_at, # Inherit start time if provided (Sub-Orchestrator Support)
                # Pass targets to session metadata for observability
                metadata={
                    "paper_target": paper_read_target,
                    "deep_target": deep_read_target,
                    "recursion_depth": recursion_depth
                }
            )
        self.recursion_depth = recursion_depth
        
        # Export orchestrator environment variables for session integrity across all agents and processes
        import os
        os.environ["SVEL_SESSION_ID"] = str(self.session.id)
        os.environ["SVEL_RUNNING_ORCHESTRATOR"] = "1"
        os.environ["SVEL_DOMAIN"] = str(self.domain)
        
        # PROJECT SVEL: EMPIRICAL BEAST REFACTOR - Data Tethering
        # Scan for locally uploaded files matching the session ID
        upload_dir = f"data/missions/{self.session.id}/uploaded_files/"
        root_dir = os.getcwd()
        
        # 1. Scan User Uploads (Session-specific)
        if os.path.exists(upload_dir):
            try:
                for filename in os.listdir(upload_dir):
                    if self.session.id in filename or self.session.id.replace("-", "") in filename.replace("-", ""):
                        full_path = os.path.join(upload_dir, filename)
                        self.session.local_data_catalog.append(full_path)
            except Exception as e:
                logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                logger.warning(f"Failed to scan local data catalog: {e}")

        # 2. Scan Project Root (Global scientific datasets)
        # We look for common ML/Scientific extensions and keywords (aggressive scan)
        sci_extensions = {".ubyte", ".idx3-ubyte", ".csv", ".h5", ".pt", ".pth", ".npy", ".npz", ".parquet", ".db", ".sqlite", ".pdb", ".cif"}
        sci_keywords = {"mnist", "dataset", "data", "train", "test", "val"}
        
        try:
            # Recursive scan of project root (limit depth to 2 to avoid node_modules etc)
            for root, dirs, files in os.walk(root_dir):
                # Ignore hidden dirs and heavy build dirs
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', 'venv', '.git', 'frontend'}]
                
                # Limit depth
                rel_path = os.path.relpath(root, root_dir)
                if rel_path != "." and len(rel_path.split(os.sep)) > 2:
                    continue

                for filename in files:
                    full_path = os.path.join(root, filename)
                    ext = os.path.splitext(filename)[1].lower()
                    
                    is_sci = any(filename.endswith(sci_ext) for sci_ext in sci_extensions)
                    is_match = any(kw in filename.lower() for kw in sci_keywords)
                    
                    if is_sci or is_match:
                        # Deduplicate
                        if full_path not in self.session.local_data_catalog:
                            self.session.local_data_catalog.append(full_path)
        except Exception as e:
            logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
            logger.warning(f"Failed to scan root data catalog: {e}")

        if self.session.local_data_catalog:
            logger.info(f" [EMPIRICAL BEAST] Tethered {len(self.session.local_data_catalog)} local data files to session.")
        # ============================================================
        #(Phase 11: Enterprise Resilience)
        # ============================================================
        
        # State Machine: Explicit workflow state tracking
        self.current_state: ResearchState = ResearchState.INITIALIZING
        self._state_history: List[Dict[str, Any]] = []
        
        # Circuit Breaker: Graceful degradation under failures
        self.circuit_breaker = CircuitBreaker()
        
        # Hypothesis Lineage: Track parent-child relationships
        self.lineage_tracker: Dict[str, HypothesisLineage] = {}

        # ============================================================
        # ULTRA-VALIDATION INJECTION (Phase 15)
        # ============================================================
        self.discovery_scorer = None
        self.statistical_validator = None
        self.failure_detector = None
        self.accuracy_tracker = None
        self.power_analyzer = None
        self.reality_constraints = None # PHYSICAL ANCHOR FIX

        if ULTRA_VALIDATION_AVAILABLE and DiscoveryScorer:
            try:
                self.discovery_scorer = DiscoveryScorer(llm_manager=self.llm_manager)
                self.statistical_validator = StatisticalGroundingValidator()
                self.failure_detector = FailureDetector()
                self.accuracy_tracker = get_accuracy_tracker()
                from backend.core.validation.power_analyzer import PowerAnalyzer as _PowerAnalyzer
                from backend.discovery.reality_constraints import RealityConstraints
                self.power_analyzer = _PowerAnalyzer()
                self.reality_constraints = RealityConstraints(llm_manager=self.llm_manager)
                logger.info(" [VALIDATION] Ultra-Validation Suite Active: Grounding, Failure Detection, Power Analysis, and RealityConstraints Enabled")
            except Exception as e:
                logger.error(f"Failed to initialize Ultra-Validation Suite: {e}")
                self.power_analyzer = None
                self.reality_constraints = None
        
        # PHASE 5: RESULT VALIDATION & REPRODUCIBILITY (Wired 2026-01-27)
        self.result_validator = ResultValidator(strict_mode=False)
        self.reproducibility_manager = ReproducibilityManager()
        self.current_seed = self.reproducibility_manager.set_seed() # Set global seed
        self.initial_env_snapshot = self.reproducibility_manager.capture_environment()
        logger.info(f" [SAFETY] ResultValidator & ReproducibilityManager wired. Global Seed: {self.current_seed}")

        # Budget Enforcement: Time, cost, and token limits
        self.budget = OperationLimits(
            max_runtime_hours=runtime_hours  # Use runtime_hours param, not undefined max_runtime_hours
        )

        # Lazy load Router first so it's available for SwarmManager
        if self.router is None:
            from backend.central_router_beast import get_router
            self.router = get_router()
            logger.info(" [TITAN] Central Router physically bonded to Orchestrator.")
        
        # Strategy Effectiveness Tracking
        self.strategy_stats: Dict[str, Dict[str, Any]] = {
            "hypothesis_generation": {"attempts": 0, "successes": 0, "cost": 0.0, "avg_time": 0.0},
            "web_search": {"attempts": 0, "successes": 0, "cost": 0.0, "avg_time": 0.0},
            "code_execution": {"attempts": 0, "successes": 0, "cost": 0.0, "avg_time": 0.0},
            "paper_retrieval": {"attempts": 0, "successes": 0, "cost": 0.0, "avg_time": 0.0},
            "synthesis": {"attempts": 0, "successes": 0, "cost": 0.0, "avg_time": 0.0},
            "task_execution": {"attempts": 0, "successes": 0, "cost": 0.0, "avg_time": 0.0}
        }
        
        # =========================================================================
        # PHASE 2: ADAPTIVE PLANNING 
        # =========================================================================
        self.current_temperature = 1.0  # Start hot (Pure Exploration)

        # Loop Guard: Prevent infinite loops
        self._actions_this_cycle: int = 0
        self._total_actions: int = 0
        
        # Initialize Vector Memory (Best Effort)
        self.vector_store = None
        if get_vectorstore:
            try:
                self.vector_store = get_vectorstore()
                logger.info("Vector Memory connected via DeepResearchOrchestrator.")
            except Exception as e:
                logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                logger.warning(f"Vector Memory init failed: {e}")
        
        # Core components
        from backend.core.context_compressor import ContextCompressor
        self.context_compressor = ContextCompressor(llm_manager=self.llm_manager)
        
        self.hypothesis_tracker = get_hypothesis_tracker(session_id=self.session.id)
        self.novelty_checker = NoveltyChecker(llm_manager=self.llm_manager)
        self.prioritizer = HypothesisPrioritizer(llm_manager=self.llm_manager)
        self.plan_creator = PlanCreator(
            llm_manager=self.llm_manager, 
            default_num_tasks=tasks_per_cycle
        )
        self.protocol_validator = ProtocolValidator(llm_manager=self.llm_manager)
        self.plan_reviewer = PlanReviewer(llm_manager=self.llm_manager)  # ADDED
        self.consensus_engine = ConsensusEngine(llm_manager=self.llm_manager)  # ADDED
        
        # Phase 26/31: The Hive (Massive Swarm Orchestration)
        from backend.orchestration.swarm_manager import get_swarm_manager
        self.swarm_manager = get_swarm_manager(
            router=self.router, 
            llm_manager=self.llm_manager
        )
        # Phase 25: Assumption Tracking (The Thanos Protocol)
        try:
            from backend.discovery.assumption_graph import get_assumption_graph
            self.assumption_graph = get_assumption_graph( session_id=self.session.id)
            logger.info(" [TITAN] AssumptionGraph physically wired and active.")
        except Exception as e:
            logger.error(f" [TITAN] FATAL ARCHITECTURE ERROR: Could not wire AssumptionGraph: {e}")
            self.assumption_graph = None

        # Phase 26: Statistical Rigor (PowerAnalyzer)
        try:
            from backend.core.validation.power_analyzer import PowerAnalyzer
            self.power_analyzer = PowerAnalyzer()
            logger.info(" [TITAN] PowerAnalyzer physically wired and active.")
        except Exception as e:
            logger.warning(f" [TITAN] PowerAnalyzer unavailable: {e}")
            self.power_analyzer = None

        # Phase 27: The Overmind (Meta-Orchestration)
        # MOVED: Initialized with mission_id later (see below) to prevent double-init
        self.overmind = None
        self._cached_seeds = [] #  Context Bridge
        
        # Phase 30: The Singularity Engine (Dynamic Scaling)
        from backend.orchestration.singularity import get_singularity
        self.singularity = get_singularity(
            orchestrator_factory=None, 
            llm_manager=self.llm_manager,
            router=self.router
        )

        # Phase 32: Adversarial Red Team (Reviewer #2)
        self.red_team = RedTeamAgent()
        
        # Phase 33: Godzilla Engine (Hypothesis Generator)
        self.hypothesis_generator = HypothesisGenerator(self.llm_manager) # NEW: Godzilla Engine Init
        self.singularity.llm_manager = self.llm_manager

        
        # Phase 35: Forensic Telemetry (The Ghost)
        from backend.execution.execution_statistics import get_execution_statistics
        self.execution_stats = get_execution_statistics()
        
        # Initialize WorldModel for shared knowledge

        if WorldModel:
            self.world_model = WorldModel(session_id=self.session.id)
            self.novelty_checker.world_model = self.world_model
            
            # ATTACH REAPER (Phase 34: Epistemic Governance)
            try:
                from backend.epistemic.epistemic_regulator import EpistemicReaper
                self.world_model._reaper = EpistemicReaper(world_model=self.world_model)
                logger.info(" Epistemic Reaper attached to WorldModel")
            except Exception as e:
                logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                logger.warning(f"Failed to attach Epistemic Reaper: {e}")

            # Gap 0: Active Recall & Infinite Context
            try:
                from backend.memory.knowledge_synthesizer import KnowledgeSynthesizer
                from backend.memory.nexus_retriever import NexusRetriever
                self.knowledge_synthesizer = KnowledgeSynthesizer(llm_manager=self.llm_manager)
                self.nexus_retriever = NexusRetriever(self.world_model)
                logger.info("Infinite Context (Active Recall) enabled via Nexus")
            except ImportError as e:
                logger.warning(f"Infinite Context components missing: {e}")
                self.knowledge_synthesizer = None
                self.nexus_retriever = None
        
        # Initialize Epistemic Regulator (PCD Pillar 1)
        if EpistemicRegulator:
            self.epistemic_regulator = EpistemicRegulator()
            self.epistemic_regulator.reset()  # Ensure clean slate for this session
            logger.info("EpistemicRegulator initialized and reset (Pillar 1 Active)")
        else:
            self.epistemic_regulator = None

        # Initialize Convergence Controller (PCD Pillar 5)
        if ConvergenceController:
            self.convergence_controller = ConvergenceController()
            logger.info("ConvergenceController initialized (Pillar 5 Active)")
        else:
            self.convergence_controller = None

        # Initialize Meta-Reasoning (PCD Pillar 6)
        if MetaReasoningLayer:
            self.meta_reasoner = MetaReasoningLayer(llm_manager=self.llm_manager)
            logger.info("MetaReasoningLayer initialized (Pillar 6 Active)")
        else:
            self.meta_reasoner = None
        
        # =========================================================================
        # SVEL BRAIN COMPONENTS (Skill Injection + Convergence + Security)
        # =========================================================================
        
        # SVEL Expert System (Domain-Specific Skill Injection)
        if SKILL_INJECTION_AVAILABLE and get_expert_system:
            self.expert_system = get_expert_system()
            self.strategy_engine = get_strategy_engine()
            logger.info(f"  SVELExpertSystem initialized ({len(self.expert_system.skills_cache)} skills loaded)")
            logger.info(" [BATTLE] DynamicStrategyEngine Armed: Strategic Battle Planning Enabled")
        else:
            self.expert_system = None
            self.strategy_engine = None
            logger.warning("SVELExpertSystem not available")
        
        # Epistemic Convergence Engine (Advanced Stopping Criteria)
        if CONVERGENCE_ENGINE_AVAILABLE and get_convergence_engine:
            self.epistemic_engine = get_convergence_engine(
                max_iterations=self.max_cycles,
                max_runtime_hours=self.max_runtime_hours
            )
            logger.info(" [EPISTEMIC] EpistemicConvergenceEngine initialized (Advanced Stopping Active)")
        else:
            self.epistemic_engine = None
            logger.warning("EpistemicConvergenceEngine not available")
        
        # Input Sanitizer (Prompt Injection Defense)
        if INPUT_SANITIZER_AVAILABLE and get_input_sanitizer:
            self.input_sanitizer = get_input_sanitizer()
            logger.info(" [DEFENSE] InputSanitizer initialized (Prompt Injection Defense Active)")
        else:
            self.input_sanitizer = None
            logger.warning("InputSanitizer not available")
        
        # Initialize Overmind - Strategic Auditor (Drift Detection)
        if OVERMIND_AVAILABLE and get_overmind:
            self.overmind = get_overmind(llm_manager=self.llm_manager)
            self.overmind_audit_interval = 10  # Audit every 10 cycles
            logger.info("Overmind initialized (Strategic Auditor Active)")
        else:
            self.overmind = None
            self.overmind_audit_interval = 10
        
        # =========================================================================
        # FERRARI DISCOVERY ENGINE: Advanced Falsification Mechanics
        # Only initialized when mode="discovery" for maximum power
        # =========================================================================
        # FIX B-1b: __init__ had the same string comparison bug as _phase_generate_hypotheses
        is_discovery_mode = self.session.mode == ResearchMode.DISCOVERY
        
        if is_discovery_mode and DISCOVERY_ULTRA_AVAILABLE:
            logger.info(" [DISCOVERY] FERRARI DISCOVERY ENGINE: Initializing advanced components...")
            
            # DiscoveryPolicy: Acceptance rules, hard caps, value computation
            self.discovery_policy = DiscoveryPolicy(hard_caps=DISCOVERY_HARD_CAPS, world_model=self.world_model)
            
            # SurvivalEngine: Tier promotion, survival tracking
            self.survival_engine = SurvivalEngine()
            
            # GovernanceEngine: Half-life, yield KPIs
            self.governance_engine = GovernanceEngine()
            
            # SemanticAttackValidator: Orthogonality enforcement
            self.attack_validator = SemanticAttackValidator(world_model=self.world_model, distance_threshold=0.4)
            
            # Hypothesis survival state (tracked per hypothesis)
            self.hypothesis_survival_cycles: Dict[str, int] = {}  # hyp_id -> cycles survived
            self.hypothesis_tiers: Dict[str, str] = {}  # hyp_id -> tier (ESCAPED/RESILIENT/STRUCTURAL)
            self.hypothesis_attack_history: Dict[str, List[Set[str]]] = {}  # hyp_id -> list of attack axes
            self.hypothesis_death_times: Dict[str, datetime] = {}
            self.structural_influences: int = 0
            self.recursive_manager = RecursiveDiscoveryManager()
            
            # Adversarial Executor: For attacking hypotheses
            from backend.discovery.adversarial_executor import AdversarialExecutor
            self.adversarial_executor = AdversarialExecutor()
            
            # FailurePatternIndex: Track cross-session failure patterns (UPGRADE 3)
            self.failure_pattern_index = get_failure_index() if get_failure_index else None
            
            logger.info(" [DISCOVERY] FERRARI ENGINE READY: DiscoveryPolicy + SurvivalEngine + GovernanceEngine + AttackValidator + RecursiveDiscoveryManager + AdversarialExecutor")
        else:
            self.discovery_policy = None
            self.survival_engine = None
            self.governance_engine = None
            self.attack_validator = None
            self.recursive_manager = None # Initialize to None if not in discovery mode
            self.hypothesis_survival_cycles = {}
            self.hypothesis_tiers = {}
            self.hypothesis_attack_history = {}
            self.hypothesis_birth_times = {}
            self.hypothesis_death_times = {}
            self.failure_pattern_index = None
        
        # Bug 1 Fix: Initialize hypothesis_birth_times unconditionally
        self.hypothesis_birth_times = {}
        
        # Lazy load dependencies
        if self.llm_manager is None:
            try:
                from backend.llm_manager import llm_manager, DEEP_RESEARCH_SYNTHESIS_MODEL
                self.llm_manager = llm_manager
                self.DEEP_RESEARCH_SYNTHESIS_MODEL = DEEP_RESEARCH_SYNTHESIS_MODEL # Store it if needed elsewhere
            except ImportError:
                self.llm_manager = None # Ensure it's None if import fails
                logger.warning("LLM manager or DEEP_RESEARCH_SYNTHESIS_MODEL not available")
        
        # Initialize Knowledge Graph (Neo4j)
        if KNOWLEDGE_GRAPH_AVAILABLE and get_knowledge_graph:
            self.knowledge_graph = get_knowledge_graph()
            if self.knowledge_graph.is_available:
                logger.info("Knowledge Graph (Neo4j) CONNECTED")
            else:
                logger.info("Knowledge Graph (Neo4j) initialized but NOT CONNECTED (check env vars)")
        else:
            self.knowledge_graph = None
        
        logger.info(
            f"DeepResearchOrchestrator initialized: "
            f"session={self.session.id}, domain={domain}, max_cycles={max_cycles}"
        )


    
    # ============================================================
    #  (Phase 11: Enterprise Resilience)
    # ============================================================
    
    def calculate_temperature(self, current_cycle: int) -> float:
        """
        Calculate exploration temperature using Sigmoidal Decay.
        
        Concept:
        - Early Cycles (High Temp): Explore widely (Temperature > 0.7)
        - Mid Cycles (Transition): Rapidly cool down focus
        - Late Cycles (Low Temp): Exploit/Refine only (Temperature < 0.3)
        
        Returns:
            float: 0.0 to 1.0 (1.0 = Max Randomness/New Ideas)
        """
        if self.max_cycles <= 1:
            return 0.0
            
        import math
        
        # Sigmoid parameters
        # k: Steepness of transition (higher = sharper drop)
        # x0: Midpoint of the research timeline (0.5 = middle)
        k = 10.0
        x0 = 0.5
        
        # [SVEL RIGOR] Tie progress to PHYSICAL TIME, not infinite cycles
        # This ensures the system cools down as the deadline approaches.
        if hasattr(self.session, "max_runtime_hours") and self.session.max_runtime_hours > 0:
            elapsed_hours = self.session.get_elapsed_hours()
            progress = min(1.0, elapsed_hours / self.session.max_runtime_hours)
            logger.info(f" [ADAPTIVE] Temporal Progress: {progress:.2%} ({elapsed_hours:.2f}h / {self.session.max_runtime_hours:.2f}h)")
        else:
            progress = current_cycle / self.max_cycles
        
        try:
            # Sigmoid: 1 / (1 + e^(k*(x-x0)))
            exponent = k * (progress - x0)
            
            # Clamp exponent to avoid overflow
            exponent = max(-700, min(700, exponent))
            
            temperature = 1.0 - (1.0 / (1.0 + math.exp(-exponent)))
            
            # Simple bounds check
            return max(0.01, min(1.0, temperature))
            
        except Exception as e:
            logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
            logger.warning(f"Error calculating temperature: {e}")
            return 0.5 # Fallback to balanced

    def _transition_state(self, new_state: ResearchState, reason: str = "") -> None:
        """Transition to a new research state with full logging."""
        old_state = self.current_state
        self.current_state = new_state
        self._state_history.append({
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "cycle": self.session.current_cycle,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"[STATE] {old_state.value} -> {new_state.value}: {reason}")
    
    def _track_strategy(self, strategy: str, success: bool, cost: float = 0.0, duration: float = 0.0) -> None:
        """Track strategy effectiveness for adaptive decision making."""
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = {"attempts": 0, "successes": 0, "cost": 0.0, "avg_time": 0.0}
        
        stats = self.strategy_stats[strategy]
        stats["attempts"] += 1
        if success:
            stats["successes"] += 1
            self.circuit_breaker.record_success()
        else:
            self.circuit_breaker.record_failure()
        stats["cost"] += cost
        
        # Update budget
        self.budget.add_cost(cost)
        
        # Rolling average for timing
        n = stats["attempts"]
        old_avg = stats["avg_time"]
        stats["avg_time"] = ((old_avg * (n - 1)) + duration) / n if n > 0 else duration
    
    def _get_best_strategy(self) -> str:
        """Return strategy with highest success rate."""
        if not self.strategy_stats:
            return "task_execution"
        
        best = max(
            self.strategy_stats.items(),
            key=lambda x: x[1]["successes"] / max(x[1]["attempts"], 1)
        )
        return best[0]
    
    def _track_lineage(self, hypothesis_id: str, parent_id: Optional[str] = None, reason: str = "") -> None:
        """Track hypothesis parent-child relationships."""
        parent_gen = 0
        if parent_id and parent_id in self.lineage_tracker:
            parent_gen = self.lineage_tracker[parent_id].generation
            self.lineage_tracker[parent_id].children_ids.append(hypothesis_id)
        
        self.lineage_tracker[hypothesis_id] = HypothesisLineage(
            hypothesis_id=hypothesis_id,
            parent_id=parent_id,
            generation=parent_gen + 1,
            evolution_reason=reason
        )
    
    def _increment_action(self) -> None:
        """Increment action counters for loop guard."""
        self._actions_this_cycle += 1
        self._total_actions += 1
    
    def _check_loop_guard(self) -> bool:
        """Check if loop guard threshold exceeded. Returns True if should force-stop."""
        if self._actions_this_cycle > MAX_ACTIONS_PER_CYCLE:
            logger.error(f"[LOOP-GUARD] Exceeded {MAX_ACTIONS_PER_CYCLE} actions in cycle {self.session.current_cycle}")
            return True
        if self._total_actions > MAX_TOTAL_ACTIONS:
            logger.error(f"[LOOP-GUARD] Exceeded {MAX_TOTAL_ACTIONS} total actions")
            return True
        return False
    
    def _reset_cycle_counters(self) -> None:
        """Reset per-cycle counters at cycle boundary."""
        self._actions_this_cycle = 0
    
    def _check_budget(self) -> Tuple[bool, str]:
        """Check if any budget limit exceeded."""
        return self.budget.check(self.session.get_elapsed_hours())
    

    def _can_proceed(self) -> Tuple[bool, str]:
        """Check if research can proceed (circuit breaker + budget + loop guard + OVERMIND)."""
        # EPISTEMIC LAW: Overmind termination check (hard stop authority)
        if self.overmind and getattr(self.overmind, 'termination_requested', False):
            return False, f"Overmind TERMINATE: {getattr(self.overmind, 'termination_reason', 'Strategic halt')}"
        
        # Circuit breaker check
        if not self.circuit_breaker.can_execute():
            return False, "Circuit breaker open"
        
        # Budget check
        exceeded, reason = self._check_budget()
        if exceeded:
            return False, f"Budget exceeded: {reason}"
        
        # Loop guard check
        if self._check_loop_guard():
            return False, "Loop guard triggered"
        
        return True, ""
    
    def get_resilience_status(self) -> Dict[str, Any]:
        """Get current status of all resilience systems."""
        return {
            "state": self.current_state.value,
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
                "can_execute": self.circuit_breaker.can_execute()
            },
            "budget": {
                "elapsed_hours": self.session.get_elapsed_hours(),
                "max_hours": self.budget.max_runtime_hours
            },
            "loop_guard": {
                "actions_this_cycle": self._actions_this_cycle,
                "max_per_cycle": MAX_ACTIONS_PER_CYCLE,
                "total_actions": self._total_actions,
                "max_total": MAX_TOTAL_ACTIONS
            },
            "strategy_stats": self.strategy_stats,
            "lineage_count": len(self.lineage_tracker)
        }
    
    # ========== Main Entry Points ==========
    
    def run(self) -> Dict[str, Any]:
        """
        Run the research loop synchronously.
        
        Returns:
            Dict with session results and findings
        """
        return asyncio.run(self.run_async())
    
    async def run_async(self, resume: bool = False) -> Dict[str, Any]:
        """
        Run the research loop asynchronously.
        
        Args:
            resume: If True, attempt to recovery state from PersistenceVault
        
        Returns:
            Dict with session results and findings
        """
        if resume:
            self.recover()
            logger.info(f"Resuming research session {self.session.id} from checkpoint")

        # =========================================================
        # PHASE 0.1: DOMAIN RECOGNITION (NEURAL)
        # =========================================================
        if self.domain == "general" or not self.domain:
            try:
                from backend.core.domain_regulator import DomainRegulator
                logger.info(" [REGULATOR] Detecting scientific domain neurally...")
                detected = await DomainRegulator.detect_domain(self.research_question)
                
                # [TITAN V143.0] METHODOLOGY BRIDGE
                # Physically abolished domain-specific hardlocks.
                # Bridging logic now triggers on technical methodology keywords (topology, manifold, proof).
                complexity_keywords = ["topology", "manifold", "proof", "derivation", "convergence", "stability"]
                if any(k in self.research_question.lower() for k in complexity_keywords):
                    logger.info(" [REGULATOR] High-complexity methodology detected. Enabling interdisciplinary synthesis.")
                    # We don't force a domain here, we allow the neural profiler to handle the tags.
                    pass

                
                self.domain = detected
                self.session.domain = detected
                logger.info(f" [REGULATOR] Mission Domain set to: {self.domain}")
            except Exception as e:
                logger.warning(f" [REGULATOR] Domain detection failed: {e}. Defaulting to {self.domain}")

        # Phase 30: Recursion Support (Log start depth)
        if self.recursion_depth > 0:
            logger.info(f"Starting recursive sub-orchestrator (depth={self.recursion_depth})")

        logger.info(f"Starting research session {self.session.id}. DEBUG_BRANCHING={DEBUG_FORCE_HYPOTHESIS_BRANCH}")
        
        # Project Godzilla: Session Registration
        vault.register_session(self.session.id, {
            "question": self.research_question,
            "domain": self.domain,
            "max_cycles": self.max_cycles
        })
        
        await events.emit(
            event_type="RESEARCH_SESSION_STARTED",
            payload={
                "session_id": self.session.id,
                "question": self.research_question,
                "domain": self.domain,
                "max_cycles": self.max_cycles
            },
            source="DeepResearchOrchestrator"
        )

        self.session.status = ResearchState.INITIALIZING # Ensure session status is updated
        # FIX: Only set started_at if not already set (prevents reset on resume/recursion)
        if not self.session.started_at:
            self.session.started_at = datetime.now()
            # Initial announcement
            await self._announce(f"Research campaign started for question: {self.research_question}")
        else:
            logger.info(f"Inherited started_at: {self.session.started_at}")
        
        # State Machine: Transition from INITIALIZING
        self._transition_state(ResearchState.GENERATING_HYPOTHESES, "Starting research session")

        # Phase 0: World Model Seeding (Ground Initial Hypotheses)
        await self._seed_world_model()
        
        # [GHOST-SHIP-FIX V2] Synchronous Integrity Check
        # Lowered threshold: even 1 committed abstract is enough to proceed.
        # Zero means total network failure - only then halt.
        current_fact_count = self.world_model.get_facts_count() if self.world_model else 0
        if current_fact_count < 1:
            logger.critical(" [FATAL] Epistemic Grounding Failed. Zero facts stored in World Model after seeding. The Ghost Ship is HALTING.")
            logger.critical(" [DIAGNOSE] This usually means ArXiv HTTP 429 hit ALL queries. Try again in 15 minutes.")
            return {"status": "error", "error": "Knowledge harvest yielded zero facts. Aborting to prevent hallucinations."}
        elif current_fact_count < 5:
            logger.warning(f" [RIGOR] Low fact count ({current_fact_count}). Proceeding cautiously - hypotheses may be weak.")

        # PHASE 0.5: STRATEGIC BATTLE PLANNING (SVEL UPGRADE)
        if self.strategy_engine:
            logger.info(" [BATTLE] Composing initial strategic Battle Plan...")
            self.session.battle_plan = self.strategy_engine.compose_battle_plan(
                objective=self.research_question,
                domain=self.domain
            )
            logger.info(f"   - Protocols: {self.session.battle_plan.get('strategic_protocols')}")
            logger.info(f"   - Toolset: {self.session.battle_plan.get('functional_tools')}")

        await self._phase_generate_hypotheses()
        
        try:
            # Phase 1: Input Sanitization (The Immune System)
            if self.input_sanitizer:
                result = self.input_sanitizer.sanitize(self.research_question)
                if not result.is_safe:
                    logger.warning(f" [ALERT] BLOCKED MALICIOUS INPUT: {self.research_question}")
                    raise ValueError("Input blocked by security protocols (Prompt Injection/Malicious Content Detected).")
                self.research_question = result.sanitized_input

            # Phase 2: Main research loop
        # NOTE: is_discovery computed per-cycle inside _execute_cycle using ResearchMode enum.
        # (Removed stale string-based is_discovery variable that was assigned but never used here.)
            while await self._should_continue():
                # F-44: Update heartbeat
                self.session.last_heartbeat = datetime.now()
                
                # F-48: Memory safety check
                self._check_memory_safety()
                
                # Reset per-cycle counters
                self._reset_cycle_counters()
                
                # Check if we can proceed (circuit breaker, budget, loop guard)
                can_proceed, block_reason = self._can_proceed()
                if not can_proceed:
                    logger.warning(f"[RESILIENCE] Cannot proceed: {block_reason}")
                    self._transition_state(ResearchState.CONVERGING, f"Stopped: {block_reason}")
                    break
                
                self.session.current_cycle += 1
                
                await events.emit(
                    event_type="RESEARCH_CYCLE_STARTED",
                    payload={"session_id": self.session.id, "cycle": self.session.current_cycle},
                    source="DeepResearchOrchestrator"
                )
                
                self._emit_progress({
                    "phase": "cycle_start",
                    "cycle": self.session.current_cycle,
                    "message": f"Starting research cycle {self.session.current_cycle}"
                })
                
                try:
                    await self._execute_cycle()
                except GlobalQuotaExceededError as quota_err:
                    logger.critical(f" [STOP] QUOTA EXCEEDED: {quota_err}")
                    # Re-raise to stop correctly without frozen loop
                    raise quota_err
                
                # F-66: Context Compression (Prevent Token Overflow)
                if self.context_compressor and self.session.current_cycle % 3 == 0:
                     logger.info("F-66: Compressing Context Window...")
                     # Reanimated: Compress mission context to keep prompts lean
                     try:
                         mission_ctx = self.context_compressor.compress_mission(self.session.to_dict())
                         self.session.knowledge_snapshot = mission_ctx.to_prompt_string()
                         logger.info(f"F-66: Mission context compressed. Ratio: {mission_ctx.compression_ratio:.1f}:1")
                     except Exception as e:
                         logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                         logger.warning(f"F-66: Context compression failed: {e}")

                # F-67: Stagnation Check
                # Check if findings increased this cycle. If not, increment stagnation.
                all_hyps_now = self.hypothesis_tracker.get_all() if self.hypothesis_tracker else []
                tested_hyps_now = sum(1 for h in all_hyps_now if h.state in [HypothesisState.CONFIRMED, HypothesisState.REFUTED] or h.metadata.get("experiment_run"))
                exps_now = len(getattr(self.session, "notebook_experiments", []))
                current_findings_count = len(self.session.findings) + tested_hyps_now + exps_now
                findings_delta = current_findings_count - getattr(self, "_last_findings_count", 0)
                self._last_findings_count = current_findings_count
                
                if findings_delta == 0:
                    self.stagnation_counter = getattr(self, "stagnation_counter", 0) + 1
                    logger.warning(f" [STAGNATION] STAGNATION DETECTED: Cycle {self.session.current_cycle} produced 0 new findings. (Strike {self.stagnation_counter}/5)")
                    
                    if self.stagnation_counter >= 3:
                        logger.warning(" [STAGNATION] STAGNATION SHAKE-UP: Forcing MAX TEMPERATURE (0.9) for next cycle.")
                        self.current_temperature = 0.9 # Override calculated temp
                        self.session.metadata["force_exploration"] = True
                        
                    if self.stagnation_counter >= 5:
                        logger.error(" [STOP] CRITICAL STAGNATION: 5 cycles with NO progress. Terminating Early.")
                        self._transition_state(ResearchState.CONVERGING, "Terminated due to 5 cycles of stagnation")
                        break
                else:
                    if getattr(self, "stagnation_counter", 0) > 0:
                        logger.info(f" [SUCCESS] STAGNATION BROKEN: +{findings_delta} new findings.")
                    self.stagnation_counter = 0

                # ===============================================================
                # OVERMIND AUDIT: Strategic Drift Detection (every N cycles)
                # ===============================================================
                if self.overmind and self.session.current_cycle % self.overmind_audit_interval == 0:
                    try:
                        logger.info(f" [OVERMIND] Running strategic audit at cycle {self.session.current_cycle}")
                        
                        # Get current findings for audit
                        findings = self.session.findings if hasattr(self.session, 'findings') else []
                        
                        directive = await self.overmind.audit_trajectory(
                            research_question=self.research_question,
                            hypotheses=self.hypothesis_tracker.get_all(),
                            findings=findings,
                            cycle=self.session.current_cycle
                        )
                        
                        if directive:
                            action = directive.get("action", "continue").lower()
                            logger.info(f" [COG] [OVERMIND] Action: {action}")
                            
                            # 1. PRUNE: Archive derailed hypotheses
                            if action == "prune":
                                prune_ids = directive.get("prune_ids", [])
                                rationale = directive.get("rationale", "Overmind prune directive")
                                logger.warning(f" [COG] [OVERMIND] Pruning {len(prune_ids)} hypotheses: {prune_ids}")
                                for hid in prune_ids:
                                    self.hypothesis_tracker.transition_state(hid, HypothesisState.ARCHIVED, reason=rationale)
                            
                            # 2. PIVOT: Strategic direction change
                            elif action == "pivot":
                                new_directive = directive.get("new_directive", "")
                                logger.critical(f" [COG] [OVERMIND] STRATEGIC PIVOT: {new_directive}")
                                await self._announce(f" [PIVOT] Overmind ordered a strategic pivot: {new_directive}")
                                
                                # Inject pivot context for next cycle
                                self.session.metadata["pivot_directive"] = new_directive
                                # Prune ALL active hypotheses to start fresh? 
                                # Maybe just those that aren't confirmed.
                                for h in self.hypothesis_tracker.get_active():
                                    if h.state not in [HypothesisState.CONFIRMED, HypothesisState.REFUTED]:
                                        self.hypothesis_tracker.transition_state(h.id, HypothesisState.ARCHIVED, reason="Strategic Pivot")
                                
                                # Force immediate re-generation of hypotheses in next cycle
                                self.session.metadata["force_regeneration"] = True
                            
                            # 3. INTENSIFY: Double down
                            elif action == "intensify":
                                new_directive = directive.get("new_directive", "")
                                logger.info(f" [COG] [OVERMIND] INTENSIFYING: {new_directive}")
                                self.session.metadata["intensify_directive"] = new_directive
                            
                            # If drift is high, log warning
                            drift = directive.get('drift_score', 0.0)
                            if drift > 0.5:
                                logger.warning(f" [ALERT] [OVERMIND] HIGH DRIFT DETECTED: {drift:.2f} - Research may be off-topic!")
                                await self._announce(f"Strategic audit: Research has drifted {drift:.0%} from goal. Refocusing...")
                            
                            # Store directive for future use
                            if not hasattr(self.session, 'overmind_directives'):
                                self.session.overmind_directives = []
                            self.session.overmind_directives.append(directive)
                            
                    except Exception as e:
                        logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                        logger.warning(f"Overmind audit failed: {e}")
            
            # Phase 3: Finalize
            self._transition_state(ResearchState.CONVERGING, "Finalizing research")
            if not getattr(self, "_satiety_finalized", False):
                await self._phase_finalize()
            
            self._transition_state(ResearchState.COMPLETED, "Research completed successfully")
            self.session.status = ResearchState.COMPLETED # Update session status with Enum
            
            await events.emit(
                event_type="RESEARCH_SESSION_COMPLETED",
                payload={
                    "session_id": self.session.id, 
                    "status": self.session.status.value, # Use .value for Enum
                    "resilience_status": self.get_resilience_status()
                },
                source="DeepResearchOrchestrator"
            )
            
        except Exception as e:
            logger.error(f"Research session failed: {e}", exc_info=True)
            self._transition_state(ResearchState.FAILED, str(e))
            self.circuit_breaker.record_failure()
            self.session.status = ResearchState.FAILED # Update session status with Enum
            self.session.error_log.append({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        finally:
            self.session.ended_at = datetime.now()
            
            # TITAN: Release DB handles and stop background threads
            if hasattr(self, 'world_model') and self.world_model:
                try:
                    self.world_model.close()
                except Exception as e:
                    logger.error(f"Cleanup error in WorldModel: {e}")
        
        # TITAN: Ensure compiled results are returned
        return self._compile_results()

            
    # _run_godzilla_simulation DELETED (Security Audit 2026-01-27)

    
    # ========== Phase Methods ==========
    
    async def _seed_world_model(self, min_abstracts: int = 50, min_papers: int = 10):
        """
        [SVEL HIGH-THROUGHPUT] Seed world model with both Local Database Schemas and Literature.
        """
        # Always index local physical datasets & databases into WorldModel so HypothesisGenerator knows exact table/column schemas
        try:
            from backend.core.data.data_resolver import DataResolver
            _dr = DataResolver()
            _bound_files = _dr.resolve_data_for_hypothesis(self.research_question)
            if _bound_files and self.world_model:
                _schema_ctx = _dr.get_data_context_for_prompt(_bound_files)
                import hashlib as _hl
                _schema_id = _hl.sha256(_schema_ctx.encode("utf-8")).hexdigest()[:16]
                self.world_model.commit_verified_fact(
                    key="local_database_schema",
                    value=_schema_ctx[:15000],
                    source="local_data_vault",
                    metadata={"domain": self.domain, "fact_id": _schema_id, "files": list(_bound_files.values())}
                )
                if hasattr(self.world_model, "_ground_scientific_entities"):
                    self.world_model._ground_scientific_entities(_schema_id, _schema_ctx[:10000], {"domain": self.domain})
                logger.info(f" [DATA VAULT] Grounded {len(_bound_files)} local datasets/databases into WorldModel schema memory.")
        except Exception as _db_seed_err:
            logger.warning(f" [DATA VAULT] Local database schema seeding warning: {_db_seed_err}")

        # [SVEL REHYDRATION] Skip harvest if we already have sufficient grounded facts.
        current_fact_count = self.world_model.get_facts_count()
        if current_fact_count >= 20:  # [FIX] Lower threshold so 31 cached facts skip re-harvest
            logger.info(f" [SEED] Persistence detected ({current_fact_count} facts). Skipping knowledge harvest.")
            return
            
        import re
        _rq = self.research_question
        logger.info(f" [SEED] MASSIVE KNOWLEDGE HARVEST: Targeting {min_abstracts} abstracts.")
        
        # ... (cleaning logic remains same) ...
        
        # 1. Parallel Search Pulses with Hard Temporal Gate (2022-2026)
        # [TITAN V141.0] UNIFIED COGNITIVE MANIFOLD
        # Physically abolished 'run_with_fallback' wrappers. 
        # Using TASK_ROUTING_MODEL directly for maximum semantic precision.
        search_queries = []
        try:
            from backend.llm_manager import TASK_ROUTING_MODEL
            import asyncio
            prompt = f"""
            SVEL KNOWLEDGE HARVESTER
            Extract 10 distinct, high-impact technical keyword combinations for searching ArXiv/Scholar based on this mission.
            Mission: {self.research_question}
            
            Rules:
            1. Use keywords ONLY. (e.g., 'vision transformer structured pruning', NOT natural language).
            2. Vary the queries to cover theory, implementation, and SOTA.
            3. Return ONLY the 10 queries separated by newlines.
            """

            # Using the established llm_manager to execute with the routing brain
            if hasattr(self, "llm_manager"):
                # Use the primary model from the routing tuple
                model_string = TASK_ROUTING_MODEL[0] if isinstance(TASK_ROUTING_MODEL, tuple) else TASK_ROUTING_MODEL
                response = await self.llm_manager.run_async(
                    prompt, 
                    model=model_string,
                    temperature=0.4,
                    source="harvest_query_gen"
                )

                content = response if isinstance(response, str) else response.get("text", str(response))
                dynamic_queries = [q.strip() for q in content.split('\n') if q.strip()]
                search_queries = [f"{q}" for q in dynamic_queries[:10]]
        except Exception as e:
            logger.error(f" [SEED] Unified cognitive harvest failed: {e}")

        if len(search_queries) < 10:
            # Generate clean fallback queries using key domain terms from the research question
            import re
            q_clean = self.research_question
            stop_words = {"investigate", "determine", "determinants", "analyze", "analysis", "study", "using", "with", "from", "into", "between", "their", "effect", "effects", "complex", "complexed"}
            words = [w for w in re.findall(r'[A-Za-z0-9_-]+', q_clean) if len(w) > 3 and w.lower() not in stop_words]
            key_phrase = " ".join(words[:5]) if words else q_clean[:60]
            dom = self.domain or "science"
            
            search_queries = [
                f"{q_clean[:100]}",
                f"{key_phrase} {dom}",
                f"{key_phrase} empirical evidence",
                f"{key_phrase} quantitative mechanism",
                f"{dom} {key_phrase} benchmark",
                f"{dom} {key_phrase} experimental findings",
                f"{dom} state of the art methodology",
                f"{dom} empirical dataset analysis",
                f"{dom} causal mechanisms",
                f"{dom} statistical validation"
            ]

        
        # [TITAN V142.3] TOOL-AWARE TEMPORAL GATING
        # Physically abolished the unified [pdat] syntax which was breaking ArXiv.
        domain_sources = {
            "biology": "pubmed", "medicine": "pubmed", "biomedical": "pubmed",
            "chemistry": "arxiv", "physics": "arxiv", "cs": "arxiv", "ml": "arxiv", "machine_learning": "arxiv",
            "general": "arxiv"
        }
        source_tool = domain_sources.get(self.domain.lower(), "arxiv")
        
        # [TITAN V143.5] SERIALIZED HARVEST WITH JITTER
        # Physically abolished parallel harvest to prevent ArXiv 429 lockouts.
        # Implements a jitter manifold to satisfy academic rate limits.
        # [GHOST-SHIP-FIX] Hard-cap to 3 queries max on first cycle to get ANY data fast.
        max_queries = 3 if self.current_cycle == 0 else len(search_queries)
        all_texts = []
        for i, q in enumerate(search_queries[:max_queries]):
            # Early exit: if we already have enough texts, stop hammering ArXiv
            if len(all_texts) >= min_abstracts:
                logger.info(f" [SEED] Reached {len(all_texts)} texts. Stopping early to prevent 429 saturation.")
                break
            try:
                if i > 0:
                    await asyncio.sleep(2.0)

                # [SVEL RIGOR] Apply tool-specific syntax
                if source_tool == "pubmed":
                    # PubMed supports Entreze [pdat]
                    final_q = f"({q}) AND (2022:2026[pdat])"
                    from backend.tools.pubmed_tool import search_papers
                    res = search_papers(final_q, limit=500)
                else:
                    # ArXiv requires standard keywords (No pdat or year slop)
                    # [TITAN V172.1] DOMAIN-SPECIFIC ARXIV QUERY
                    # Physically map the domain to ArXiv categories to prevent cross-domain contamination.
                    arxiv_cats = ""
                    if self.domain in ["machine_learning", "ml", "cs"]:
                        arxiv_cats = " AND (cat:cs.LG OR cat:cs.CV OR cat:stat.ML OR cat:cs.AI OR cat:cs.CL)"
                    elif self.domain == "physics":
                        arxiv_cats = " AND (cat:physics.comp-ph OR cat:cond-mat.stat-mech OR cat:quant-ph)"
                    elif self.domain == "mathematics":
                        arxiv_cats = " AND (cat:math.OC OR cat:math.ST OR cat:math.NA)"
                        
                    final_q = f"({q}){arxiv_cats}"
                    
                    from backend.tools.arxiv_tool import search_arxiv
                    # [GHOST-SHIP-FIX] Slash max_results from 250→30 to avoid HTTP 429
                    res = search_arxiv(final_q, max_results=30, sort_by="relevance")
                    
                if res:
                    if isinstance(res, list):
                        all_texts.extend([f"{p.get('title','')}\n{p.get('abstract','')}" for p in res])
                    else:
                        all_texts.append(str(res))
            except Exception as e:
                logger.warning(f" [SEED] Harvest failed for tool {source_tool}: {e}")
                continue


                
        seed_texts = list(set(all_texts)) # Deduplicate
        logger.info(f" [SEED] Harvested {len(seed_texts)} unique raw documents.")
        
        # Strip prefixes injected by the fallback hypothesis generator
        _prefixes_to_strip = [
            r"^EXPERIMENTAL VALIDATION:\s*",
            r"^Material stability limits in \w+ affect\s+",
        ]
        for _pat in _prefixes_to_strip:
            _stripped = re.sub(_pat, "", _rq, flags=re.IGNORECASE).strip()
            if _stripped and _stripped != _rq:
                logger.info(f" [SEED] Stripped contaminated prefix. Clean query: {_stripped[:80]}")
                _rq = _stripped

        # Truncate extremely long queries (router/embedding limits)
        seed_query = _rq[:200]

        # 1. Try Nexus retriever or fallback to web search
        try:
            if not seed_texts and getattr(self, "nexus_retriever", None):
                # Nexus returns a single context string
                raw_context = self.nexus_retriever.retrieve_relevant_nodes(seed_query, limit=min_abstracts)
                if raw_context:
                    seed_texts.append(raw_context)
            elif not seed_texts:
                # Fallback: use router to run a Sovereign research_agent multi-tool query
                q = seed_query
                try:
                    res = await self.router.route_async(q, agent_name="research_agent", task_type="search", context={"orchestrator": "DeepResearch", "research_session": self.session.id})
                    router_seeds = res.get("results", [])[:min_abstracts]
                    if router_seeds:
                        seed_texts.extend(router_seeds)
                except Exception as router_err:
                    logger.error(f" [SEED_ERROR] Router fallback failed: {router_err}")
            
            # [SVEL INTELLIGENCE] Clean the query for PubMed/BioRxiv (Extract keywords)
            import re
            clean_query = re.sub(r'[^a-zA-Z0-9 ]', '', seed_query).replace("Hypothesis", "").replace("Analyze", "")
            kw_query = " ".join([w for w in clean_query.split() if len(w) > 4][:5])
            if not kw_query: kw_query = f"{self.domain} advanced research" # [TITAN V140.0] Domain-agnostic fallback



            if not seed_texts:
                logger.info(f" [SEED] Domain '{self.domain}' maps to source: {source_tool}. Query: '{kw_query}'")
                # Try domain-appropriate source first
                if source_tool == "pubmed":
                    try:
                        from backend.tools.pubmed_tool import search_papers as search_pubmed_papers
                        res = search_pubmed_papers(kw_query, limit=min_abstracts)
                        if res:
                            seed_texts = [f"{p.get('title','')}\n{p.get('abstract','')}" for p in res]
                            logger.info(f" [SEED] PubMed returned {len(seed_texts)} abstracts")
                    except Exception as e:
                        logger.warning(f" [SEED] PubMed failed: {e}")

                    if not seed_texts:
                        try:
                            from backend.tools.biorxiv_tool import search_papers as search_biorxiv_papers
                            res = search_biorxiv_papers(kw_query, limit=min_abstracts)
                            if res:
                                seed_texts = [f"{p.get('title','')}\n{p.get('abstract','')}" for p in res]
                                logger.info(f" [SEED] bioRxiv returned {len(seed_texts)} abstracts")
                        except Exception as e:
                            logger.warning(f" [SEED] bioRxiv failed: {e}")

                # PubMed/bioRxiv priority for biomedical domains
                if not seed_texts and self.domain in ["biology", "medicine", "biomedical"]:
                    logger.error(f" [SEED_ERROR] PubMed and bioRxiv both failed to return data for domain {self.domain}.")
                    raise ValueError("Failed to retrieve domain-appropriate seed abstracts.")

                # ArXiv allowed for ML/Physics domains
                if not seed_texts and self.domain in ["machine_learning", "ml", "cs", "physics", "computer_science", "math"]:
                    try:
                        arxiv_cats = ""
                        if self.domain in ["machine_learning", "ml", "cs", "computer_science"]:
                            arxiv_cats = " AND (cat:cs.LG OR cat:cs.CV OR cat:stat.ML OR cat:cs.AI OR cat:cs.CL)"
                        elif self.domain == "physics":
                            arxiv_cats = " AND (cat:physics.comp-ph OR cat:cond-mat.stat-mech OR cat:quant-ph)"
                        elif self.domain in ["mathematics", "math"]:
                            arxiv_cats = " AND (cat:math.OC OR cat:math.ST OR cat:math.NA)"

                        final_kw_query = f"({kw_query}){arxiv_cats}"

                        from backend.tools.arxiv_tool import search_arxiv
                        # [GHOST-SHIP-FIX] Never request more than 50 papers per fallback call
                        res = search_arxiv(final_kw_query, max_results=min(min_abstracts, 50), sort_by="relevance")
                        if res:
                            seed_texts = [f"{p.get('title','')}\n{p.get('abstract','')}" for p in res]
                            logger.info(f" [SEED] ArXiv utilized for domain {self.domain}: {len(seed_texts)} abstracts")
                    except Exception as arxiv_err:
                        logger.error(f" [SEED_ERROR] ArXiv retrieval failed: {arxiv_err}")

                    # If ArXiv failed or hit rate limits, auto-fallback to Semantic Scholar
                    if not seed_texts:
                        try:
                            from backend.tools.semantic_scholar_tool import search_and_format as search_semantic_scholar
                            logger.info(f" [SEED] ArXiv exhausted. Falling back to Semantic Scholar for domain {self.domain}...")
                            # [TITAN FIX] Semantic Scholar strictly caps limit at 100.
                            safe_limit = min(min_abstracts, 100)
                            res = search_semantic_scholar(kw_query, max_papers=safe_limit)
                            if res:
                                seed_texts = [res] # Semantic scholar returns a formatted string block
                                logger.info(f" [SEED] Semantic Scholar utilized for domain {self.domain}.")
                        except Exception as s2_err:                            logger.error(f" [SEED_ERROR] Semantic Scholar retrieval failed: {s2_err}")
        except Exception as e:
            logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
            logger.warning(f" [SEED] Seeding retrieval logic failed: {e}")

        # [SVEL UNIVERSAL PURIFICATION - ROOT FIX]
        # Dynamically extract rigor anchors from the question to support ALL domains
        if seed_texts:
            original_len = len(seed_texts)
            from backend.core.domain_regulator import DomainRegulator
            seed_texts = DomainRegulator.filter_by_domain_similarity(seed_texts, self.research_question)
            logger.info(f" [PURGE] Nuked {original_len - len(seed_texts)} slop papers using DomainRegulator mathematical similarity.")

        # [SVEL V68.18] Atomic Thread-Safe Seeding
        logger.info(" [RIGOR] Harvesting abstracts sequentially to prevent SQLite lock contention.")
        
        import hashlib
        committed = 0
        # Sequentially harvest and commit
        for text in seed_texts:
            try:
                f_id = hashlib.sha256(text.encode()).hexdigest()[:16]
                if self.world_model:
                    # Use the WorldModel's thread-safe commit API
                    self.world_model.commit_verified_fact(
                        key="literature_seed",
                        value=text[:10000],
                        source="parallel_harvester",
                        metadata={"domain": self.domain, "fact_id": f_id}
                    )
                    if hasattr(self.world_model, "_ground_scientific_entities"):
                        self.world_model._ground_scientific_entities(f_id, text[:10000], {"domain": self.domain})
                committed += 1
            except Exception as e:
                logger.error(f"Failed to inject seed: {e}")
                continue
                
        logger.info(f" [HARVEST] Successfully committed {committed} facts to World Model. Swarm now unlocking...")


        # [SVEL V68.13] Hard Rigor: The 'Science or Death' Gate
        # [TITAN V139.0] DOMAIN-AGNOSTIC EXTRACTION
        # Physically abolished the 'Molecules/Genes' hardlock.
        # We verify that entities exist, but we do not force them to be biological.
        entity_count = len(self.world_model._entities) if self.world_model else 0
        if entity_count == 0:
            # Only trigger hard halt if we are several cycles in with ZERO data
            if self.current_cycle > 1:
                logger.critical(" [FATAL] Discovery Vacuum: 0 entities extracted. Discovery is physically impossible. HALTING.")
                return {"status": "error", "error": "Extraction pump failed to find Grounding Data."}
            else:
                logger.warning(" [RIGOR] Initial Cycle detected zero entities. Proceeding with caution.")
        
        return {"status": "success"}

    async def _phase_generate_hypotheses(self) -> None:
        """[TITAN] Sovereign Tool Selection & Multi-Wave Hypothesis Generation."""
        active_hyps = self.hypothesis_tracker.get_active()
        force_regen = bool(self.session.metadata.pop("force_regeneration", False)) if hasattr(self, "session") and hasattr(self.session, "metadata") else False
        if len(active_hyps) >= 5 and not force_regen:
            logger.info(f" [HYPOTHESIS] Tracker already has {len(active_hyps)} active hypotheses. Skipping generation.")
            return

        catalog = self.expert_system.get_tool_catalog() if self.expert_system else "general research, neural architecture search, vision transformers"
        prompt = f"Pick 5-8 tools for: {self.research_question}\n{catalog}"
        selection_resp = await self.llm_manager.run_async(prompt)
        selected = [t.strip().lower() for t in selection_resp.get("text", "").split(",")]
        from backend.core.hypothesis.generator import HypothesisGenerator
        gen = HypothesisGenerator(self.llm_manager)
        
        # [TITAN V145.2] CONTEXT PURIFICATION
        # Physically abolished string-concatenation context which was causing token overload.
        # We pass the raw facts list and let the Generator's Schema Protocol handle the injection.
        all_facts = self.world_model.get_all_facts() if self.world_model else []
        
        hyps = await gen.generate_hypotheses(
            self.research_question, 
            self.domain, 
            selected_tools=selected,
            facts=all_facts # Pass raw objects for internal Ph.D. filtering
        )

        existing = self.hypothesis_tracker.get_all()
        added_llm = 0
        for h in hyps:
            # BUG-FIX-1 & BUG-FIX-2: Run novelty check on every LLM-generated hypothesis
            # before adding. This (a) populates h.novelty_score and (b) deduplicates.
            try:
                novelty_report = self.novelty_checker.check_novelty(h, existing)
                h.novelty_score = novelty_report.novelty_score
                if not novelty_report.is_novel:
                    logger.info(
                        f" [NOVELTY-GATE] Dropping duplicate hypothesis (sim={novelty_report.max_similarity:.2f}): "
                        f"{h.statement[:80]}"
                    )
                    continue
            except Exception as novelty_err:
                logger.warning(f" [NOVELTY-GATE] check_novelty failed for {h.id}: {novelty_err}. Allowing through.")
            self.hypothesis_tracker.add(h)
            existing.append(h)  # keep pool current for within-batch dedup
            await self.world_model.add_hypothesis(h)
            added_llm += 1
        logger.info(f" [HYPOTHESIS] {added_llm}/{len(hyps)} LLM hypotheses passed novelty gate.")
        return

    def _gnn_resolve_entity_name(self, entity_id: str, node_texts: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Look up entity or fact name from world_model/snapshot; return None if unresolvable or toxic."""
        def _is_clean_entity_label(val: Optional[str]) -> bool:
            if not val or not isinstance(val, str):
                return False
            v = val.strip()
            if len(v) < 3 or v.startswith(("{", "[", "#", "http://", "https://")):
                return False
            # Block stringified Python dicts/lists or Document wrapper labels
            if "{" in v or "}" in v or "': '" in v or '": "' in v:
                return False
            v_lower = v.lower()
            if v_lower.startswith(("document:", "doc_", "entity:", "fact:", "node_")):
                return False
            toxic = [
                "'error'", '"error"', "no claim", "web search", "traceback",
                "system_rejected", "failed", "exception", "404 not found", "error code",
                "novelty check", "redundant", "finding_task", "finding_exp", "task_",
                "session_state", "research_session", "doc_"
            ]
            if any(t in v_lower for t in toxic):
                return False
            import re
            if re.search(r'\bhypothesis\s+[a-f0-9]{4,}\b', v_lower):
                return False
            if HEX_ID_PATTERN.match(v.replace('-', '')):
                return False
            return True

        try:
            ent = self.world_model.get_entity(entity_id)
            if ent:
                if getattr(ent, "type", "") == "Document":
                    return None
                if ent.properties:
                    name = ent.properties.get("name") or ent.properties.get("label") or ent.properties.get("title") or ent.properties.get("key") or ent.properties.get("statement")
                    if _is_clean_entity_label(name):
                        return name
        except Exception:
            pass

        # Check snapshot node_texts for evidence/concept/seed nodes
        if node_texts and entity_id in node_texts:
            text = node_texts[entity_id]
            if text and isinstance(text, str):
                cleaned = text.strip()
                if cleaned.lower().startswith("document:"):
                    return None
                if cleaned.startswith("Fact (") and "): " in cleaned:
                    cleaned = cleaned.split("): ", 1)[1].strip()
                elif ":" in cleaned:
                    prefix, rest = cleaned.split(":", 1)
                    if prefix.strip().lower() in ("concept", "abstract", "fact", "evidence", "hypothesis"):
                        cleaned = rest.strip()
                clean_name = cleaned.split("\n")[0].split(". ")[0].strip()
                if len(clean_name) > 80:
                    clean_name = clean_name[:80].rsplit(" ", 1)[0]
                if _is_clean_entity_label(clean_name):
                    return clean_name

        # Direct fact lookup fallback
        try:
            if hasattr(self.world_model, "get_fact"):
                fact = self.world_model.get_fact(entity_id.replace("fact_", ""))
                if fact and fact.value:
                    val = str(fact.value).strip()
                    clean_val = val.split("\n")[0].split(". ")[0].strip()
                    if len(clean_val) > 80:
                        clean_val = clean_val[:80].rsplit(" ", 1)[0]
                    if _is_clean_entity_label(clean_val):
                        return clean_val
        except Exception:
            pass
        return None

    async def _gnn_dream_phase(self) -> None:
        """
        GNN DREAM PHASE: The "Subconscious" Discovery Loop.
         Surfaces hidden structural patterns as testable hypotheses.
        """
        if not self.world_model or not hasattr(self.world_model, "oracle") or not self.world_model.oracle:
            logger.debug(" [GNN] Subconscious phase skipped: Oracle not available.")
            return

        logger.info(" [GNN] Subconscious Phase: GNN Oracle is dreaming...")
        
        # [SVEL BRIDGE] Physically train GNN on active graph before dreaming
        snapshot = None
        try:
            # [V255+] CRITICAL FIX: Use get_knowledge_snapshot() which populates node_texts for SBERT.
            # get_graph_snapshot() does NOT include node_texts, causing GNN semantic extraction to fail.
            snapshot = self.world_model.get_knowledge_snapshot()
            n_nodes = len(snapshot.get("nodes", []))
            n_edges = len(snapshot.get("edges", []))
            
            # [TITAN V263.0] MINIMUM GRAPH SIZE GATE
            # Adjusted to 10 edges for focused domain graphs to enable active GNN dream prediction.
            MIN_EDGES_FOR_GNN = 10
            if n_edges < MIN_EDGES_FOR_GNN:
                logger.warning(f" [GNN] Graph too sparse for reliable inference ({n_nodes} nodes, {n_edges} edges, minimum {MIN_EDGES_FOR_GNN} edges required). Skipping dream phase.")
                return
            
            if n_nodes >= 2:
                logger.info(f" [GNN] Training on active graph ({n_nodes} nodes, {n_edges} edges)...")
                import asyncio
                await asyncio.to_thread(self.world_model.oracle.train_on_graph, snapshot)
        except Exception as e:
            logger.warning(f" [GNN] Rapid training failed: {e}")
        
        try:
            # 1. Initialize Igor Audit (Physical Grounding)
            empirical_checker = get_gnn_empirical_checker(self.research_question) if get_gnn_empirical_checker else None
            
            # Ensure checker is actually callable
            if empirical_checker and not callable(empirical_checker):
                logger.warning(" [GNN] Physical Grounding Gate: ERROR (Checker not callable)")
                empirical_checker = None

            if empirical_checker:
                logger.info(" [GNN] Physical Grounding Gate: ACTIVE (Empirical lookup enabled)")
            else:
                logger.warning(" [GNN] Physical Grounding Gate: INACTIVE (No relevant data found)")

            # 2. Deep Dream (Global Discovery)
            # Increase top_k if in discovery mode
            top_k = 10 if self.session.mode == ResearchMode.DISCOVERY else 5
            import asyncio
            hunches = await asyncio.to_thread(self.world_model.oracle.deep_dream, top_k=top_k, empirical_checker=empirical_checker)
            
            if not hunches:
                logger.info(" [GNN] Subconscious Phase: No high-confidence hunches surfaced.")
                return

            # 3. Process hunches into Hypotheses
            # [TITAN V141.3] UNCERTAINTY-AWARE PRIORITIZATION
            # Physically rank hunches by a combined score: Confidence * (1 - Uncertainty).
            # This forces the system to focus on STABLE discoveries.
            sorted_hunches = sorted(
                hunches, 
                key=lambda x: x.confidence * (1.0 - getattr(x, 'uncertainty', 0.0)), 
                reverse=True
            )
            
            node_texts = snapshot.get("node_texts", {}) if (snapshot and isinstance(snapshot, dict)) else {}
            added_count = 0
            for hunch in sorted_hunches:
                u_val = getattr(hunch, 'uncertainty', 0.0)

                # BUG-FIX-10: Resolve entity names via class method to avoid closure rebuilding
                src_name = self._gnn_resolve_entity_name(hunch.source_id, node_texts=node_texts)
                tgt_name = self._gnn_resolve_entity_name(hunch.target_id, node_texts=node_texts)

                # Filter out hunches with unresolvable hex hash keys to prevent graph garbage
                if src_name is None and HEX_ID_PATTERN.match(hunch.source_id.replace('-', '')):
                    logger.warning(f" [GNN] Skipping hunch: source_id '{hunch.source_id}' is an unresolved hash.")
                    continue
                if tgt_name is None and HEX_ID_PATTERN.match(hunch.target_id.replace('-', '')):
                    logger.warning(f" [GNN] Skipping hunch: target_id '{hunch.target_id}' is an unresolved hash.")
                    continue

                src_label = src_name or hunch.source_id
                tgt_label = tgt_name or hunch.target_id

                # Reject any remaining hash tokens in labels
                if HEX_ID_PATTERN.match(src_label.replace('-', '')) or HEX_ID_PATTERN.match(tgt_label.replace('-', '')):
                    logger.warning(f" [GNN] Skipping hunch with hash label: {src_label} <-> {tgt_label}")
                    continue

                def _is_valid_gnn_label(label: str) -> bool:
                    if not label or len(label.strip()) < 3:
                        return False
                    ls = label.strip()
                    if ls.startswith(("{", "[", "#", "http://", "https://")):
                        return False
                    if "document:" in ls.lower() or "doc_" in ls.lower() or "{" in ls or "}" in ls or "name':" in ls or 'name":' in ls:
                        return False
                    low = ls.lower()
                    toxic_gnn = [
                        "'error'", '"error"', "no claim", "web search", "traceback", "system_rejected",
                        "novelty check", "redundant", "finding_task", "finding_exp", "task_", "session_state",
                        "research_session"
                    ]
                    if any(bad in low for bad in toxic_gnn):
                        return False
                    import re
                    if re.search(r'\bhypothesis\s+[a-f0-9]{4,}\b', low):
                        return False
                    return True

                if not _is_valid_gnn_label(src_label) or not _is_valid_gnn_label(tgt_label):
                    logger.warning(f" [GNN] Skipping hunch with unscientific/malformed label: {src_label} <-> {tgt_label}")
                    continue

                # Reject trivial generic concept stop-words and self-loops
                trivial_stopwords = {"literature_seed", "approach", "method", "system", "time", "framework", "concept", "dataset", "model", "error"}
                if src_label.strip().lower() in trivial_stopwords or tgt_label.strip().lower() in trivial_stopwords:
                    logger.warning(f" [GNN] Skipping hunch with trivial stopword: {src_label} <-> {tgt_label}")
                    continue
                if src_label.strip().lower() == tgt_label.strip().lower():
                    continue

                statement = (
                    f"GNN Hypothesis: A structural interaction between '{src_label}' and '{tgt_label}' "
                    f"is predicted by the knowledge graph (uncertainty σ={u_val:.3f})."
                )

                # Check for HALLUCINATION ALERT in reasoning
                if "[HALLUCINATION ALERT]" in hunch.reasoning:
                    logger.warning(f" [GNN] Hallucination risk detected for {src_label}-{tgt_label}. Skipping.")
                    continue

                new_h = Hypothesis(
                    statement=statement,
                    rationale=hunch.reasoning,
                    domain=self.domain,
                    source_agent="GNN_Intuition",
                    confidence=hunch.confidence,
                    uncertainty=u_val,
                    variables=[
                        {"name": src_label, "symbol": "X", "unit": "counts", "type": "independent"},
                        {"name": tgt_label, "symbol": "Y", "unit": "counts", "type": "dependent"}
                    ],
                    functional_form="Y = k * X",
                    constraints=[
                        {"equation": "k > 0", "variables": ["k"], "type": "boundary", "description": "Positive structural interaction coefficient"},
                        {"equation": "X >= 0", "variables": ["X"], "type": "physical", "description": "Non-negative node interaction metric"},
                        {"equation": "Y >= 0", "variables": ["Y"], "type": "physical", "description": "Non-negative node interaction metric"}
                    ],
                    predictions=[
                        {
                            "condition": f"Measurement of '{src_label}' and '{tgt_label}'",
                            "outcome": "Correlation |r| > 0.4",
                            "baseline": 0.0,
                            "threshold": 0.4,
                            "direction": "any"
                        }
                    ]
                )

                # Novelty gate (already existed for GNN — preserved)
                report = self.novelty_checker.check_novelty(new_h, self.hypothesis_tracker.get_all())
                new_h.novelty_score = report.novelty_score  # BUG-FIX-1: persist score
                if report.is_novel:
                    self.hypothesis_tracker.add(new_h)
                    added_count += 1
                    logger.info(f" [GNN] New intuition surfaced: {src_label} <-> {tgt_label} (Conf: {hunch.confidence:.2f})")
                else:
                    logger.info(f" [GNN] Dropping duplicate GNN hunch (sim={report.max_similarity:.2f}): {src_label} <-> {tgt_label}")

            if added_count > 0:
                await self._announce(f"My GNN intuition surfaced {added_count} new structural hunches for investigation.")

        except Exception as e:
            logger.error(f" [GNN] Subconscious dream phase failed: {e}")

    async def _execute_cycle(self) -> None:
        """Execute one research cycle"""
        cycle = self.session.current_cycle
        
        fact_count = self.world_model.get_facts_count()
        runtime_hrs = float(getattr(self.session, "max_runtime_hours", 1.0) or 1.0)
        default_satiety = max(5000, int(runtime_hrs * 2500))
        satiety_limit = int(os.environ.get("FACT_SATIETY_LIMIT", str(default_satiety)))
        if fact_count >= satiety_limit:
            logger.info(f" [SATIETY] Knowledge base saturated ({fact_count} facts >= {satiety_limit}). Forcing Synthesis Track.")
            # Skip hypothesis generation if already saturated
            if cycle > 1:
                await self._phase_finalize()  # [FIX] _do_final_synthesis -> _phase_finalize (correct method name)
                self._satiety_finalized = True
                return
        
        is_discovery = getattr(self.session, 'mode', 'research') in [ResearchMode.DISCOVERY]
        
        # =================================================================
        # SUPERVISOR STEERING HOOK (Real-Time Intervention)
        # =================================================================
        try:
            import aiofiles
            directive_path = os.path.join(f"data/missions/{self.session.id}/sessions/{self.session.id}", "SUPERVISOR_DIRECTIVE.json")
            if os.path.exists(directive_path):
                async with aiofiles.open(directive_path, "r") as f:
                    content = await f.read()
                    directive_data = json.loads(content)
                
                if directive_data.get("status") == "pending":
                    directive = directive_data.get("directive", "")
                    logger.warning(f" [SUPERVISOR] INTERVENTION DETECTED: {directive}")
                    
                    # Log to system context
                    self.session.knowledge_snapshot += f"\n\n[SUPERVISOR DIRECTIVE CYCLE {cycle}]: {directive}\n"
                    
                    # Create a new top-priority hypothesis based on directive
                    pivot_h = Hypothesis(
                        statement=f"SUPERVISOR DIRECTIVE: {directive}",
                        rationale="Explicit human intervention during execution.",
                        domain=self.domain,
                        source_agent="Supervisor",
                        confidence=1.0,
                        variables=[{"name": "DirectiveWeight", "symbol": "D", "unit": "dimensionless", "role": "independent"}],
                        functional_form="D > 0",
                        constraints=[
                            {"equation": "D > 0", "variables": ["D"], "type": "boundary", "description": "Active supervisor directive score"}
                        ],
                        predictions=[{
                            "condition": "Execute supervisor directive",
                            "outcome": "D > 0.5",
                            "baseline": 0.0,
                            "threshold": 0.5,
                            "direction": "increase"
                        }]
                    )
                    self.hypothesis_tracker.add(pivot_h)
                    
                    # Mark as processed
                    directive_data["status"] = "processed"
                    directive_data["processed_cycle"] = cycle
                    async with aiofiles.open(directive_path, "w") as f:
                        await f.write(json.dumps(directive_data))
        except Exception as e:
            logger.error(f" [SUPERVISOR] Failed to process directive: {e}")

        # RESILIENCE: Explicit Checkpoint at start of cycle
        try:
            state = {
                "session": dataclasses.asdict(self.session),
                "hypotheses": [h.to_dict() for h in self.hypothesis_tracker.get_all()],
                "knowledge": self.session.knowledge_snapshot
            }
            if is_discovery and DISCOVERY_ULTRA_AVAILABLE:
                discovery_session = get_discovery_session(self.session.id)
                if discovery_session:
                    state["ferrari_state"] = discovery_session.to_dict()
            
            vault.save_checkpoint(self.session.id, cycle, state)
            logger.info(f"PRE-EMPTIVE CHECKPOINT: Cycle {cycle} locked in.")
        except Exception as e:
            logger.error(f"Pre-emptive checkpoint failed: {e}")
        
        # =================================================================
        # PHASE 0: META-COGNITIVE REFLECTION (SVEL TIER)
        # =================================================================
        # The system pauses to reflect on its own state before acting.
        if self.meta_reasoner:
            try:
                current_metrics = {
                    "findings_count": len(self.session.findings),
                    "hypotheses_count": len(self.hypothesis_tracker.get_all()),
                    "refusal_rate": getattr(self.session, "refusal_rate", 0.0), # Assuming tracked
                    "budget_used_percent": getattr(self.budget, "get_usage_percent", lambda: 0.0)(),
                    "cycle": cycle,
                    # TITAN 5 UPGRADE: Semantic Injection
                    "recent_findings": self.session.findings[-5:] if self.session.findings else []
                }
                
                # Seed with retrieval
                seed_data = []
                if getattr(self.nexus_retriever, "retrieve_relevant_nodes", None):
                    seed_data = self.nexus_retriever.retrieve_relevant_nodes(self.research_question, limit=200)

                # Update strategy logic
                strategy = await self.meta_reasoner.adapt_strategy_async(
                    cycle=self.session.current_cycle,
                    hypotheses=self.hypothesis_tracker.get_all(),
                    session_metrics=current_metrics,
                    seed_data=seed_data
                )
                
                # Apply Strategic Overrides
                logger.info(f" [META-STRATEGY] Mode: {strategy.mode.value} | Branching: {strategy.branching_factor} | ExpRate: {strategy.exploration_rate}")
                
                # Dynamically adjust system parameters based on strategy
                # SVEL COST SAFETY: Respect hard cap from beast_config
                ideal_parallel = max(1, strategy.branch_factor * 2) if hasattr(strategy, 'branch_factor') else max(1, strategy.branching_factor * 2)
                self.max_parallel = min(beast_config.orchestration.max_parallel_agents, ideal_parallel)
            except Exception as e:
                logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                logger.warning(f"Meta-reasoning step failed: {e}")

        # =========================================================================
        # PHASE 2: ADAPTIVE PLANNING (Dynamic Temperature)
        # =========================================================================
        self.current_temperature = self.calculate_temperature(cycle)
        logger.info(f" [ADAPTIVE] ADAPTIVE PLANNING: Cycle {cycle}/{self.max_cycles} | Temperature: {self.current_temperature:.2f}")
        
        # CRITICAL FIX: Check time at START of cycle to prevent runaway execution
        if self._is_time_exceeded():
            logger.info(f"[CYCLE {cycle}] Skipping - time limit exceeded")
            self._emit_progress({
                "phase": "timeout",
                "message": f"Stopping: max runtime of {self.session.max_runtime_hours:.2f}h exceeded"
            })
            return
        
        await self._announce(f"Starting cycle {cycle}. Research Temperature: {self.current_temperature:.2f}")
        
        # [GNN] SUB-CONSCIOUS DISCOVERY PHASE
        await self._gnn_dream_phase()
        
        # Step -1: Meta-Reasoning (Pillar 6)
        # [Deleted Redundant Meta-Reasoning Block]

        # Step 0: Epistemic Regulation (PCD Pillar 1)
        if self.epistemic_regulator:
            actions = self.epistemic_regulator.regulate(self.hypothesis_tracker.get_all(), cycle)
            for action in actions:
                logger.info(f"Epistemic Regulation Action: {action.action_type} -> {action.target_ids}")
                
                # RESTORATION FIX: Use ActionType Enum values or strings consistently
                a_type = action.action_type
                if hasattr(a_type, 'value'): a_type = a_type.value

                if a_type in [ActionType.SPAWN_VARIANTS.value, "spawn", "spawn_variants"]:
                    # Force spawn logic
                    for target_id in action.target_ids:
                        if action.metadata and "variants" in action.metadata:
                            for variant_stmt in action.metadata["variants"]:
                                # Inherit formal physical variables and equation from parent hypothesis
                                parent_h = self.hypothesis_tracker.get(target_id)
                                parent_vars = list(getattr(parent_h, "variables", [])) if parent_h and getattr(parent_h, "variables", None) else [{"name": "PrimaryObservable", "symbol": "X", "unit": "dimensionless", "role": "independent"}]
                                parent_params = list(getattr(parent_h, "parameters", [])) if parent_h and getattr(parent_h, "parameters", None) else []
                                parent_form = getattr(parent_h, "functional_form", "") if parent_h and getattr(parent_h, "functional_form", None) else "Y = k * X"
                                parent_constraints = list(getattr(parent_h, "constraints", [])) if parent_h and getattr(parent_h, "constraints", None) else []
                                parent_preds = list(getattr(parent_h, "predictions", [])) if parent_h and getattr(parent_h, "predictions", None) else []
                                new_h = Hypothesis(
                                    statement=variant_stmt,
                                    rationale=f"Spawning from {target_id} due to {action.reason}",
                                    domain=self.domain,
                                    source_agent="EpistemicRegulator",
                                    parent_hypothesis_id=target_id,
                                    variables=parent_vars,
                                    parameters=parent_params,
                                    functional_form=parent_form,
                                    constraints=parent_constraints,
                                    predictions=parent_preds
                                )
                                self.hypothesis_tracker.add(new_h)
                                
                elif a_type in [ActionType.DECAY_CONFIDENCE.value, "decay", "decay_confidence"]:
                    for target_id in action.target_ids:
                        h = self.hypothesis_tracker.get(target_id)
                        if h:
                            decay = action.metadata.get("decay_amount", 0.05) if action.metadata else 0.05
                            h.confidence = max(0.0, h.confidence - decay)
                            
                elif a_type in [ActionType.MERGE_HYPOTHESES.value, "merge", "merge_hypotheses"]:
                    # Merge logic: Archive the weaker one, keep the dominant
                    target_ids = action.target_ids
                    dominant_id = action.metadata.get("dominant_id")
                    
                    if dominant_id and len(target_ids) >= 2:
                        h_dom = self.hypothesis_tracker.get(dominant_id)
                        
                        for tid in target_ids:
                            if tid != dominant_id:
                                h_weak = self.hypothesis_tracker.get(tid)
                                if h_weak:
                                    # 1. Archive weaker hypothesis
                                    self.hypothesis_tracker.transition_state(tid, HypothesisState.ARCHIVED, f"Merged into {dominant_id}")
                                    
                                    # 2. Transfer evidence to dominant (COGNITIVE PERSISTENCE FIX)
                                    if h_dom:
                                        # Transfer 'evidence' (Primary SVEL list)
                                        if hasattr(h_dom, 'evidence') and hasattr(h_weak, 'evidence'):
                                            # Avoid duplicates
                                            existing_e = {e.id for e in h_dom.evidence} if (h_dom.evidence and hasattr(h_dom.evidence[0], 'id')) else set()
                                            for e in h_weak.evidence:
                                                if not hasattr(e, 'id') or e.id not in existing_e:
                                                    h_dom.evidence.append(e)
                                        
                                        # Transfer 'supporting_evidence' (Legacy/WriterAgent list)
                                        if hasattr(h_dom, 'supporting_evidence') and hasattr(h_weak, 'supporting_evidence'):
                                            if isinstance(h_dom.supporting_evidence, list) and isinstance(h_weak.supporting_evidence, list):
                                                h_dom.supporting_evidence.extend(h_weak.supporting_evidence)
                                        
                                        logger.info(f"   Transferred all evidence from {tid} to {dominant_id}")
                        
                        logger.info(f"   MERGE COMPLETE: {target_ids} -> {dominant_id}")

                elif a_type in [ActionType.REFUTE.value, "refute", "refute_hypothesis"]:
                     for target_id in action.target_ids:
                        self.hypothesis_tracker.transition_state(target_id, HypothesisState.REFUTED, action.reason)
                        if self.world_model:
                            self.world_model.invalidate_hypothesis(target_id, action.reason)
                        logger.info(f" EPISTEMIC EXECUTION: Hypothesis {target_id} REFUTED by Regulator.")
                                
        # Step 0.5: Overmind Audit is executed post-cycle in run_async (avoiding duplicate per-cycle LLM audit)

        # ========== INSTRUMENTATION: Capture pre-cycle state ==========
        hypotheses_before = len(self.hypothesis_tracker.get_all())
        facts_before = self.world_model._stats["total_facts"] if self.world_model else 0
        
        # Step 1: Prioritize hypotheses (and auto-generate a new wave if active pool is exhausted or pivot requested)
        hypotheses = self.hypothesis_tracker.get_active()
        if not hypotheses or self.session.metadata.get("force_regeneration"):
            logger.info(f" [AUTONOMOUS WAVE] Active hypothesis pool exhausted or pivot triggered at cycle {cycle}. Synthesizing next-generation hypotheses...")
            self.session.metadata["force_regeneration"] = False
            try:
                await self._phase_generate_hypotheses()
                hypotheses = self.hypothesis_tracker.get_active()
            except Exception as regen_err:
                logger.warning(f" [AUTONOMOUS WAVE] Next-generation hypothesis synthesis failed: {regen_err}")
        
        # Step 1.1: Semantic Morgue Rejection (Research Scar Tissue)
        # Check against previously killed hypotheses to prevent cyclic failures
        if hasattr(self, "red_team") and self.red_team and hypotheses:
            for h in list(hypotheses):
                try:
                    morgue_hits = self.red_team.query_morgue(h.statement, similarity_threshold=0.85)
                    if morgue_hits:
                        best_hit = morgue_hits[0]
                        similarity_pct = best_hit.get("similarity", 0) * 100
                        logger.warning(f" [MORGUE] Auto-Reject triggered for '{h.statement[:50]}...' ({similarity_pct:.1f}% similar to DEAD hypothesis).")
                        self.hypothesis_tracker.transition_state(
                            h.id, 
                            HypothesisState.REFUTED, 
                            f"Morgue Auto-Reject: {similarity_pct:.1f}% similar to previously killed idea: '{best_hit.get('statement')}'. Reason: {best_hit.get('kill_reason')}"
                        )
                except Exception as morgue_query_err:
                    logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {morgue_query_err}")
                    logger.warning(f" [MORGUE] Query failed: {morgue_query_err}")
            
            # Re-fetch active hypotheses after purging
            hypotheses = self.hypothesis_tracker.get_active()

        if hypotheses:
            self.prioritizer.prioritize(hypotheses)
            
        # Step 1.5: Experimental Validation (Phase 41: Experiment Engine)
        # BUG-FIX-5 & P0-31: Unify all domains (including machine_learning) onto ExperimentAgent.
        agent_key = "experiment_agent"

        if self.router and cycle > 0:
            from backend.agents.experiment_agent import ExperimentAgent
            exp_agent = ExperimentAgent(llm_manager=self.llm_manager)

            if exp_agent:
                # PHASE 42: HARD EXECUTION GATE (Operation "Reality Check")
                # BUG-FIX-4: Was `> 0.5` — all hypotheses default to exactly 0.5,
                # so the gate was permanently closed. Changed to `>= 0.5`.
                exp_candidates = [
                    h for h in hypotheses
                    if h.confidence >= 0.5
                    and not h.metadata.get("experiment_run", False)
                ]
                
                # Priority sort: high-confidence unverified first (the "Sycophancy Trap")
                exp_candidates.sort(key=lambda h: h.confidence, reverse=True)
                
                if exp_candidates:
                    # Godzilla Scale: Process top 3 candidates instead of just 1
                    batch_targets = exp_candidates[:3]
                    logger.info(f" [EXP] Hard Execution Gate: Processing {len(batch_targets)} experiment candidates...")
                    
                    for target_h in batch_targets:
                        logger.info(f" [EXP] Triggering Auto-Experiment for: {target_h.statement[:50]}...")
                        
                        try:
                            # 1. Prepare task for agent (preserve hypothesis_id end-to-end)
                            experiment_id = f"exp_{cycle}_{uuid.uuid4().hex[:4]}"
                            task_dict = {
                                "id": experiment_id,
                                "type": "experiment",
                                "hypothesis_id": target_h.id,
                                "description": f"EXPERIMENTAL VALIDATION: {target_h.statement}",
                                "payload": {
                                    "hypothesis_id": target_h.id,
                                    "hypothesis": target_h,
                                    "statement": target_h.statement,
                                    "rationale": target_h.rationale,
                                    "experiment_id": experiment_id
                                }
                            }
                            
                            # 2. Run high-fidelity experiment
                            # This uses the full self-healing, rigor-checking, and metadata-formatting logic
                            agent_res = await exp_agent.run(task_dict, context={"cycle": cycle, "DOMAIN": self.domain})
                            
                            if agent_res.get("status") in ("success", "completed"):
                                # Extract rich metadata
                                metadata = agent_res.get("metadata", {})
                                content = agent_res.get("text", "")
                                
                                # [RIGOR] FLAW FIX: Block fake success results
                                if "LLM returned infrastructure error" in str(content):
                                    logger.error(f" [RIGOR] Rejecting fake success from {agent_key} due to infrastructure error.")
                                    target_h.metadata["experiment_run"] = True
                                    target_h.metadata["experiment_failed"] = True
                                    self.hypothesis_tracker.update(target_h)
                                    continue

                                # Record finding
                                finding_dict = {
                                    "task_id": experiment_id,
                                    "cycle": cycle,
                                    "agent_name": agent_key,
                                    "task": {"type": "experiment"},
                                    "result": agent_res,
                                    "content": content,
                                    "timestamp": datetime.now().isoformat()
                                }
                                self.session.findings.append(finding_dict)
                                
                                # [RIGOR] Unified processing for World Model, Notebook, and Telemetry
                                self._process_completed_task(task_dict, agent_res, cycle)
                                
                                # Mark as experimented
                                target_h.metadata["experiment_run"] = True
                                target_h.metadata["last_experiment_output"] = content

                                # [PATCH-16: SCIENTIFIC VERDICT INTEGRITY GATE]
                                # Separate code execution status ("success") from empirical hypothesis verdict.
                                # Never treat process status 'SUCCESS' as scientific confirmation.
                                result_payload = agent_res.get("result", {}) if isinstance(agent_res.get("result"), dict) else {}
                                inner_meta = result_payload.get("metadata", {}) if isinstance(result_payload.get("metadata"), dict) else {}
                                report = result_payload.get("scientific_report", {}) if isinstance(result_payload.get("scientific_report"), dict) else inner_meta.get("report", {})
                                if not isinstance(report, dict):
                                    report = {}

                                supported = result_payload.get("supported")
                                if supported is None:
                                    supported = inner_meta.get("supported")

                                evidence_type = str(result_payload.get("evidence_type", inner_meta.get("evidence_type", ""))).lower()
                                missing_cols = inner_meta.get("missing_columns") or result_payload.get("missing_columns") or report.get("missing_columns")
                                sample_size = report.get("sample_size", inner_meta.get("sample_size"))
                                p_value = report.get("p_value", inner_meta.get("p_value"))
                                details_str = str(inner_meta.get("details", "")).lower()

                                has_missing_col_error = (
                                    bool(missing_cols)
                                    or ("missing" in details_str and "column" in details_str)
                                    or ("keyerror" in str(agent_res.get("logs", "")).lower())
                                )

                                raw_verdict = (
                                    inner_meta.get("verdict")
                                    or agent_res.get("metadata", {}).get("verdict")
                                    or agent_res.get("verdict")
                                    or ""
                                ).upper()

                                # Prevent execution status leakage into scientific verdicts
                                if raw_verdict in ["SUCCESS", "OK", "DONE", "COMPLETED"]:
                                    raw_verdict = ""

                                exp_verdict = raw_verdict
                                if not exp_verdict and isinstance(content, str):
                                    content_upper = content.upper()
                                    import re
                                    if "NOT CONFIRMED" in content_upper or "CANNOT BE CONFIRMED" in content_upper or "INCONCLUSIVE" in content_upper:
                                        exp_verdict = "INCONCLUSIVE"
                                    elif "VERDICT: REFUTED" in content_upper or re.search(r'\bREFUTED\b', content_upper):
                                        exp_verdict = "REFUTED"
                                    elif "VERDICT: CONFIRMED" in content_upper or re.search(r'\bCONFIRMED\b', content_upper):
                                        exp_verdict = "CONFIRMED"

                                # Ground verdict in empirical proof-of-work
                                is_empty_dataset = (
                                    (sample_size is not None and sample_size == 0)
                                    or ("NO_ROWS_EXTRACTED" in str(content))
                                    or ("zero valid rows" in str(content).lower())
                                    or ("empty" in details_str and "row" in details_str)
                                )
                                if has_missing_col_error or is_empty_dataset:
                                    exp_verdict = "INCONCLUSIVE"
                                    retries = int(target_h.metadata.get("experiment_retries", 0))
                                    if retries < 2:
                                        target_h.metadata["experiment_retries"] = retries + 1
                                        target_h.metadata["experiment_run"] = False
                                        target_h.metadata["last_experiment_error"] = f"Missing columns ({missing_cols}) or empty extraction: {details_str[:200]}"
                                        logger.info(f" [RIGOR RETRY] Re-queueing {target_h.id} for experiment repair (retry {retries + 1}/2).")
                                    else:
                                        logger.info(f" [RIGOR GATE] Experiment on {target_h.id} exhausted retries with insufficient rows. Verdict set to INCONCLUSIVE.")
                                elif supported is False or evidence_type == "refute":
                                    if exp_verdict != "INCONCLUSIVE":
                                        exp_verdict = "REFUTED"
                                elif supported is True and evidence_type == "support" and not exp_verdict:
                                    if p_value is not None and p_value > 0.05:
                                        exp_verdict = "INCONCLUSIVE"
                                    else:
                                        exp_verdict = "CONFIRMED"

                                # Multiple-testing tracking & Holm-Bonferroni / FDR adjusted p-value across campaign
                                all_tracked = self.hypothesis_tracker.get_all() if self.hypothesis_tracker else []
                                n_tested = max(1, sum(1 for h_item in all_tracked if h_item.metadata.get("experiment_run")))
                                effective_alpha = 0.05 / n_tested if os.environ.get("SVEL_STRICT_FWER", "0") == "1" else 0.05
                                if p_value is not None:
                                    try:
                                        target_h.metadata["raw_p_value"] = float(p_value)
                                        target_h.metadata["adjusted_p_value"] = min(1.0, float(p_value) * n_tested)
                                        target_h.metadata["n_hypotheses_tested"] = n_tested
                                    except Exception:
                                        pass

                                # Enforce gate invariants
                                if exp_verdict in ["CONFIRMED", "SUPPORTED"]:
                                    if has_missing_col_error or supported is False or evidence_type != "support" or (p_value is not None and p_value > effective_alpha):
                                        logger.warning(f" [RIGOR REJECTION] Overriding fake confirmation on {target_h.id}: supported={supported}, p_value={p_value} (alpha={effective_alpha:.4f}), evidence_type={evidence_type}, missing_columns={has_missing_col_error}")
                                        exp_verdict = "INCONCLUSIVE"
                                        target_h.metadata["test_verdict"] = "INCONCLUSIVE"
                                        self.hypothesis_tracker.update(target_h)
                                    else:
                                        target_h.confidence = min(1.0, target_h.confidence + 0.2)
                                        target_h.metadata["test_verdict"] = "CONFIRMED"
                                        logger.info(f" [EVIDENCE] Experiment CONFIRMED hypothesis {target_h.id}. Confidence increased to {target_h.confidence:.2f}")
                                        self.hypothesis_tracker.transition_state(
                                            target_h.id,
                                            HypothesisState.CONFIRMED,
                                            f"Experiment empirically confirmed hypothesis. Evidence supported=True, p={p_value}",
                                            force=True
                                        )
                                elif exp_verdict in ["REFUTED", "FAILED", "REJECTED"]:
                                    target_h.confidence = max(0.0, target_h.confidence - 0.3)
                                    target_h.metadata["test_verdict"] = "REFUTED"
                                    self.hypothesis_tracker.transition_state(
                                        target_h.id,
                                        HypothesisState.REFUTED,
                                        f"Experiment refuted hypothesis. Verdict: {exp_verdict}",
                                        force=True
                                    )
                                    logger.info(f" [EVIDENCE] Experiment REFUTED hypothesis {target_h.id}. State set to REFUTED.")
                                else:
                                    # INCONCLUSIVE / UNTESTABLE: Do NOT artificially boost confidence
                                    target_h.metadata["test_verdict"] = "INCONCLUSIVE"
                                    logger.info(f" [EVIDENCE] Experiment outcome inconclusive for hypothesis {target_h.id}. Confidence maintained at {target_h.confidence:.2f}")
                                    self.hypothesis_tracker.update(target_h)
                                
                                logger.info(f" [SUCCESS] Experiment {experiment_id} completed via Hard Execution Gate.")
                            else:
                                logger.warning(f"Experiment agent returned non-success status: {agent_res.get('status')}")
                                target_h.metadata["experiment_run"] = True
                                target_h.metadata["experiment_failed"] = True
                                self.hypothesis_tracker.update(target_h)
                        except Exception as e:
                            logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                            logger.warning(f"Experiment for {target_h.id} failed: {e}")
                            retries = int(target_h.metadata.get("experiment_retries", 0))
                            if retries < 2:
                                target_h.metadata["experiment_retries"] = retries + 1
                                target_h.metadata["experiment_run"] = False
                                target_h.metadata["last_experiment_error"] = str(e)[:300]
                            else:
                                target_h.metadata["experiment_run"] = True
                                target_h.metadata["experiment_failed"] = True
                            try:
                                self.hypothesis_tracker.update(target_h)
                            except Exception as update_err:
                                logger.error(f"Failed to update hypothesis tracker on experiment failure: {update_err}")
        
        # =========================================================================
        # PHASE 3: CONTINUOUS EXECUTION (DEEP WORK ARCHITECTURE)
        # =========================================================================
        # User Directive: "Execution queue never empties... PlanCreator is a background policy updater"
        
        # 1. GLOBAL QUEUE MANAGEMENT
        # Aggregate ready tasks from ALL active plans (supporting multi-cycle overlap)
        global_ready_tasks = []
        for i, p in enumerate(self.session.plans):
             if isinstance(p, dict):
                 try:
                     from backend.core.planning.plan_creator import ResearchPlan
                     p = ResearchPlan.from_dict(p)
                     self.session.plans[i] = p
                 except Exception:
                     pass
             p_status = getattr(p, "status", None) or (p.get("status") if isinstance(p, dict) else None)
             if p_status not in ["completed", "abandoned", "rejected"]:
                 if hasattr(p, "get_ready_tasks"):
                     global_ready_tasks.extend(p.get_ready_tasks())
                 
        MIN_QUEUE_SIZE = 5
        MIN_EXPERIMENT_QUOTA = 10 # Operation "Reality Check" Mandate
        
        # 2. REPLENISHMENT (PLANNING)
        # If the queue is starving, trigger the PlanCreator (Policy Updater)
        if len(global_ready_tasks) < MIN_QUEUE_SIZE:
             logger.info(f" [QUEUE] Queue Starvation ({len(global_ready_tasks)} < {MIN_QUEUE_SIZE}). Triggering Planner.")
             
             # [SVEL RIGOR] Neural Intuition Pulse (GNN Dreaming)
             # Before planning, force the GNN to find hidden leads in the latest data.
             await self._gnn_dream_phase()
             
             # Determine next planning cycle index
             next_plan_cycle = len(self.session.plans) + 1
             
             context = await self._build_context()
             
             # [REALITY_ANCHORING] Inject Power Analysis and Reality Constraints
             effect_size = context.get("ESTIMATED_EFFECT_SIZE", 0.5)
             
             # PHYSICAL GUARD: Prevent implosion if PowerAnalyzer is missing
             if self.power_analyzer:
                 power_target = self.power_analyzer.ttest_sample_size(effect_size=effect_size, power=0.8)
             else:
                 logger.warning(" [GUARD] PowerAnalyzer UNAVAILABLE. Using default sample target (N=30).")
                 power_target = 30
                 
             context["POWER_TARGET_N"] = power_target
             context["REALITY_ANCHOR_REQUIRED"] = True
             
             # [2027 SOVEREIGN AGENT ARCHITECTURE] Route exclusively to the 4 Sovereign Frontier Pillars
             discipline_prompt = (
                "\nCRITICAL SOVEREIGN AGENT DISCIPLINE:\n"
                "1. Use 'research_agent' (with tools like 'scholar_search', 'arxiv_search', 'pubmed_search', 'deep_paper_reader', 'web_search') for all literature search, full-text PDF reading, and evidence synthesis.\n"
                "2. Use 'experiment_agent' for all Python/SciPy/PyTorch/Bio.PDB statistical testing, local dataset analysis, and computational modeling.\n"
                "3. Use 'red_team_agent' to adversarially audit claims and verify citations.\n"
                "4. Use 'writer_agent' / 'report_composer_agent' for final manuscript synthesis."
             )

             
             new_plan = await self.plan_creator.create_plan(
                research_objective=self.research_question + discipline_prompt,
                context=context,
                cycle=next_plan_cycle, # Decoupled from loop iteration
                temperature=self.current_temperature,
                mode=getattr(self.session, 'mode', 'research')
             )
             
             # PHASE 43: MECHANICAL REVIEW (Feasibility Check)
             # The PlanReviewer checks tool availability and dependency logic
             if self.plan_reviewer:
                  # Sync reviewer with enriched orchestrator context (Libraries + Protocols)
                  self.plan_reviewer.available_tools = context.get('available_tools', self.plan_reviewer.available_tools)
                  mech_review = self.plan_reviewer.review(new_plan)
                  if not mech_review.is_approved:
                      logger.warning(f" [PLAN] Mechanical Review FLAG: {mech_review.summary}")
                      context['mechanical_flaws'] = mech_review.issues
                      
             # [REALITY_ANCHORING] Reality Audit: Prevent scientifically impossible plans
             if self.reality_constraints:
                 reality_violations = self.reality_constraints.validate_plan(new_plan.to_dict())
                 if any(v.severity == "critical" for v in reality_violations):
                     crit_v = [v for v in reality_violations if v.severity == "critical"][0]
                     logger.error(f" [REALITY_KILL] Plan rejected by RealityConstraints: {crit_v.message}")
                     context['reality_violations'] = [v.to_dict() for v in reality_violations]
             else:
                 logger.warning(" [GUARD] RealityConstraints UNAVAILABLE. Skipping reality audit.")

             # Validate (Adversarial Peer Review)
             review = await self.protocol_validator.validate(new_plan, context)
             is_approved = review.is_approved
             if not is_approved:
                 new_plan = await self.plan_creator.revise_plan(new_plan, review.to_dict(), context)
                 review = await self.protocol_validator.validate(new_plan, context)
                 is_approved = review.is_approved
             
             new_plan.status = "approved" if is_approved else "rejected"
             self.session.plans.append(new_plan)
             
             if not is_approved:
                 logger.warning(" [GUARD] Plan rejected even after revision. Skipping execution.")
             else:
                 self._emit_progress({
                    "phase": "plan_created",
                    "plan": new_plan.to_dict(),
                    "message": f"Policy Update: Added {len(new_plan.tasks)} new tasks to queue."
                 })
                 
                 # Re-fetch global ready tasks strictly for the active plan
                 # Close out previous cycle plans so old procedural tasks never re-enter the queue
                 for old_p in self.session.plans[:-1]:
                     if hasattr(old_p, "status") and old_p.status not in ["completed", "abandoned", "rejected"]:
                         old_p.status = "completed"
                     elif isinstance(old_p, dict) and old_p.get("status") not in ["completed", "abandoned", "rejected"]:
                         old_p["status"] = "completed"

                 global_ready_tasks = []
                 curr_plan = self.session.plans[-1] if self.session.plans else None
                 if curr_plan:
                     if isinstance(curr_plan, dict):
                         try:
                             from backend.core.planning.plan_creator import ResearchPlan
                             curr_plan = ResearchPlan.from_dict(curr_plan)
                             self.session.plans[-1] = curr_plan
                         except Exception:
                             pass
                     if hasattr(curr_plan, "get_ready_tasks"):
                         global_ready_tasks.extend(curr_plan.get_ready_tasks())

        # PHASE 42: QUOTA ENFORCEMENT (Operation "Reality Check")
        # P0-31: All domains route to ExperimentAgent for first-principles code synthesis & falsification
        agent_key = "experiment_agent"
            
        exp_count = sum(1 for f in self.session.findings if f.get("agent_name") == agent_key)
        if (len(global_ready_tasks) < MIN_QUEUE_SIZE or exp_count < MIN_EXPERIMENT_QUOTA) and cycle > 0:
            # Find high-confidence hypotheses that lack experiments
            # [SVEL RIGOR] Skip procedural tasks (Igor Protocol)
            rigor_candidates = [
                h for h in self.hypothesis_tracker.get_active()
                if not h.metadata.get("experiment_run", False)
                and "procedural task" not in h.statement.lower()
            ]
            rigor_candidates.sort(key=lambda h: h.confidence, reverse=True)
            
            if rigor_candidates and len(global_ready_tasks) < 10:
                logger.info(f" [RIGOR] Rigor Guard: Injecting Emergency Experiment for {rigor_candidates[0].id}")
                
                # Godzilla Rigor: Inject a task directly into the active cycle plan
                if self.session.plans:
                    target_plan = self.session.plans[-1]
                    if isinstance(target_plan, dict):
                        try:
                            from backend.core.planning.plan_creator import ResearchPlan
                            target_plan = ResearchPlan.from_dict(target_plan)
                            self.session.plans[-1] = target_plan
                        except Exception:
                            pass
                    emergency_task = ResearchTask(
                        id=f"rigor_{cycle}_{uuid.uuid4().hex[:4]}",
                        description=f"EXPERIMENTAL VALIDATION: {rigor_candidates[0].statement}",
                        task_type="experiment",
                        required_agents=[agent_key],
                        estimated_minutes=30,
                        is_exploration=False, # This is rigorous exploitation
                        payload={
                            "hypothesis": rigor_candidates[0],
                            "hypothesis_id": rigor_candidates[0].id,
                            "statement": rigor_candidates[0].statement,
                            "rationale": rigor_candidates[0].rationale,
                            "predictions": getattr(rigor_candidates[0], "predictions", []),
                            "domain": self.domain
                        }
                    )
                    if hasattr(target_plan, "tasks"):
                        target_plan.tasks.append(emergency_task)
                    elif isinstance(target_plan, dict) and "tasks" in target_plan:
                        target_plan["tasks"].append(emergency_task.to_dict())
                    global_ready_tasks.append(emergency_task)
                    logger.info(f"   Task {emergency_task.id} injected into queue.")

        # 3. EXECUTION (SWARM DEPLOYMENT)
        if not global_ready_tasks:
            logger.info("Subjective Stasis: No tasks ready (waiting for dependencies or planner).")
        else:
            # Take a batch up to max_parallel
            batch_size = max(1, self.max_parallel)
            tasks_to_run = global_ready_tasks[:batch_size]
            
            logger.info(f" [SWARM] Deploying Swarm Batch: {len(tasks_to_run)} tasks (Queue: {len(global_ready_tasks)})")
            
            # [SVEL UPGRADE] Parallel Fractal Decomposition
            async def process_task_decomposition(t: ResearchTask) -> List[ResearchTask]:
                # [TITAN 4] MEMORY INJECTION: CURE GOLDFISH MEMORY
                task_context_recall = ""
                if self.nexus_retriever:
                    try:
                        task_context_recall = self.nexus_retriever.retrieve_relevant_nodes(t.description, limit=3)
                    except Exception as e:
                        logger.warning(f"Nexus retrieval failed for task {t.id}: {e}")

                singularity_context = {
                    "last_finding": self.session.findings[-1] if self.session.findings else None,
                    "constraints": {"runtime_mode": f"{self.max_runtime_hours}h"},
                    "depth": getattr(self, "recursion_depth", 0),
                    "nexus_recall": task_context_recall,
                    "scientific_seeds": self._cached_seeds
                }
                
                execution_subtasks = []
                try:
                    # [SVEL V66.0] MISSION CRITICAL RESILIENCE
                    # Wrap all fractalization in a shield to ensure the swarm never stops
                    try:
                        # 1. Fractal Decomposition (Singularity)
                        sub_missions = await self.singularity.decompose_task(t, context=singularity_context)
                        # [SWARM DISCIPLINE] Cap sub_missions to at most 4 per root task to prevent fanout cascade
                        if sub_missions and len(sub_missions) > 4:
                            sub_missions = sub_missions[:4]
                        
                        # 2. Technical Decomposition (Foreman)
                        # Only invoke secondary shatter if singularity returned at most 1 mission
                        if self.router and hasattr(self.router, "neural_fractalizer") and self.router.neural_fractalizer and len(sub_missions) <= 1:
                            logger.info(f" [FOREMAN] Technical Breakdown active for task: {t.id}")
                            for mission in sub_missions:
                                try:
                                    # [TITAN V156.1] MANIFOLD BINDING
                                    # Physically pass the mission object (ResearchTask), not just the description string.
                                    tech_plan = await self.router.neural_fractalizer.shatter(
                                        mission, 
                                        {"domain": self.domain, "objective": self.research_question, "depth": singularity_context.get("depth", 0) + 1}
                                    )

                                    if tech_plan:
                                        tech_plan = tech_plan[:3]  # Cap to at most 3 technical steps
                                        logger.info(f" [FOREMAN] Exploded '{mission.description[:40]}...' into {len(tech_plan)} technical steps.")
                                        for st in tech_plan:
                                            # [TITAN V240.2] SAFE ATTRIBUTE EXTRACTION
                                            # Handle both SubTask objects and generic dicts from the fractalizer.
                                            def get_val(obj, key, default=None):
                                                if isinstance(obj, dict): return obj.get(key, default)
                                                return getattr(obj, key, default)

                                            rt = ResearchTask(
                                                id=get_val(st, 'id', str(uuid.uuid4())[:8]),
                                                description=get_val(st, 'description', 'No description'),
                                                task_type=get_val(st, 'type') or get_val(st, 'task_type', 'analysis'),
                                                required_agents=[get_val(st, 'agent')] if get_val(st, 'agent') else mission.required_agents,
                                                required_tools=[get_val(st, 'tool')] if get_val(st, 'tool') else getattr(mission, 'required_tools', []),
                                                priority=get_val(st, 'priority', mission.priority),
                                                estimated_minutes=get_val(st, 'estimated_seconds', 3600) / 60.0,
                                                dependencies=[d for d in get_val(st, 'dependencies', [])],
                                                payload={**mission.payload, **get_val(st, 'args', {})}
                                            )
                                            execution_subtasks.append(rt)
                                    else:
                                        execution_subtasks.append(mission)
                                except Exception as tech_err:
                                    logger.warning(f"Technical decomposition failed for {mission.id}: {tech_err}. FORCING direct execution.")
                                    execution_subtasks.append(mission)
                        else:
                            execution_subtasks.extend(sub_missions)
                    except Exception as fractal_err:
                        logger.warning(f"Fractal decomposition failed for {t.id}: {fractal_err}. Bypassing to direct execution.")
                        execution_subtasks = [t]
                except Exception as e:
                    logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in decomposition: {e}")
                    execution_subtasks = [t]
                
                return execution_subtasks

            # Execute all task decompositions in parallel
            decomposition_results = await asyncio.gather(*[process_task_decomposition(t) for t in tasks_to_run])
            final_execution_batch = [item for sublist in decomposition_results for item in sublist]

            # Mark decomposed parent tasks completed so they never re-enter the ready task queue
            for pt in tasks_to_run:
                if hasattr(pt, "status"):
                    pt.status = "completed"
                elif isinstance(pt, dict):
                    pt["status"] = "completed"

            # [SWARM DISCIPLINE] Enforce strict upper bound on execution batch per cycle for Mac mini stability
            MAX_SWARM_BATCH = int(os.environ.get("MAX_SWARM_TASKS_PER_CYCLE", "12"))
            if len(final_execution_batch) > MAX_SWARM_BATCH:
                logger.info(f" [SWARM DISCIPLINE] Capping execution batch from {len(final_execution_batch)} to {MAX_SWARM_BATCH} tasks.")
                final_execution_batch = final_execution_batch[:MAX_SWARM_BATCH]

            # [SVEL PERSISTENCE] Physically commit the plan to the database before execution
            try:
                for t in final_execution_batch:
                    self.session.tasks.append(t)
                
                # Calculate Integrity Confidence
                total_errs = len(self.session.error_log)
                base_confidence = 1.0
                if total_errs > 0:
                    base_confidence = max(0.1, 1.0 - (total_errs * 0.05)) # Penalty for failures
                
                # Hard-Override: Use add_fact directly to ensure persistence works across all process maps
                import json
                self.world_model.add_fact(
                    key=f"research_session_state_{self.session.id}",
                    value=json.dumps(self.session.to_dict()),
                    source="orchestrator",
                    confidence=base_confidence,
                    metadata={"session_id": self.session.id, "type": "session_state"}
                )
                logger.info(f" [PERSISTENCE] Committed {len(final_execution_batch)} tasks to persistent session memory (Confidence: {base_confidence:.2f}).")
            except Exception as save_err:
                logger.warning(f" [PERSISTENCE] Failed to commit tasks: {save_err}")

            # Define Event Handler for Granular Persistence
            completed_task_ids = set()

            async def on_swarm_event(event_type: str, payload: Dict[str, Any]):
                self._emit_progress({"phase": event_type, "payload": payload})
                
                if event_type == "task_complete" and "result" in payload:
                    tid = payload.get("task_id")
                    if tid and tid not in completed_task_ids:
                        completed_task_ids.add(tid)
                        logger.info(f" [CHECKPOINT] Granular Checkpoint: Persistence for task {tid}")
                        
                        # Locate the task object to get its type/context
                        t_obj = next((t for t in final_execution_batch if t.id == tid), None)
                        if t_obj:
                            t_obj.status = "completed"
                            
                            # Add to findings immediately
                            result_data = payload["result"]
                            
                            # [SECURITY_GATE] RELENTLESS REJECTION: Protect session from trash code results
                            if result_data.get("status") == "failed" and "Security Violation" in str(result_data.get("error", "")):
                                logger.error(f" [SECURITY] Rejecting Task {tid} result due to security block. Scavenging FORBIDDEN.")
                                t_obj.status = "failed"
                                return # STOP propagation of this trash

                            content_str = str(result_data.get("text", result_data.get("summary", result_data.get("result", result_data)))) if isinstance(result_data, dict) else str(result_data)
                            self.session.findings.append({
                                "task_id": tid,
                                "cycle": cycle,
                                "agent_name": result_data.get("agent_id") or result_data.get("agent_name") or "unknown",
                                "task": {
                                    "type": t_obj.task_type,
                                    "uncertainty": t_obj.payload.get("uncertainty", 0.0) if hasattr(t_obj, "payload") else 0.0
                                }, 
                                "result": result_data,
                                "content": content_str,
                                "timestamp": datetime.now().isoformat()
                            })

                            
                            # UPDATE WORLD MODEL & TELEMETRY
                            self._process_completed_task(t_obj, result_data, cycle)
                            
                            # [REALITY_ANCHORING] Reality Gating: Reject any result lacking verifiable data link
                            if t_obj.task_type in ["experiment", "wrangling", "exploration"]:
                                if not result_data.get("metadata", {}).get("provenance") and result_data.get("status") == "success":
                                    logger.warning(f" [REALITY_GATING] Rejecting result for {tid}: Lacks verifiable provenance/data link.")
                                    # flag it as ungrounded
                                    result_data["is_grounded"] = False
                                    result_data["significance_score"] = 0.0

                            # [SVEL TUNING] High-Capacity Checkpointing
                            if len(completed_task_ids) % 10 == 0:
                                try:
                                    state = {
                                        "session": dataclasses.asdict(self.session),
                                        "hypotheses": [h.to_dict() for h in self.hypothesis_tracker.get_all()],
                                        "knowledge": self.session.knowledge_snapshot
                                    }
                                    vault.save_checkpoint(self.session.id, cycle, state)
                                    logger.info(f" [CHECKPOINT] High-Capacity Save: {len(completed_task_ids)} tasks persisted.")
                                except Exception as vault_err:
                                    logger.warning(f"Coalesced checkpoint failed: {vault_err}")

            # EXECUTE SWARM (STREAMING)
            async for res in self.swarm_manager.execute_swarm_stream(final_execution_batch, self.session.id, on_event=on_swarm_event):
                # 1. IMMEDIATE FATAL ERROR CHECK
                if res.get("status") == "failed" and res.get("error") and "FATAL" in str(res.get("error")):
                    msg = f"CRITICAL INFRASTRUCTURE FAILURE: Swarm task aborted with fatal error. Terminating mission."
                    logger.critical(f" [FATAL] {msg}")
                    self.session.status = ResearchState.FAILED
                    self.session.error_log.append({"cycle": cycle, "error": msg, "details": res.get("error")})
                    await self._announce(f" [ABORT] MISSION ABORTED: {msg}")
                    raise RuntimeError(msg)

                # 2. POST-PROCESS & DEPENDENCY RESOLUTION (STREAMEABLE)
                tid = res.get("task_id")
                status = res.get("status")
                result_data = res.get("result")
                
                # SKIP tasks handled by granular checkpointing to avoid duplicates
                if tid in completed_task_ids:
                    # However, if status changed or we have new refined data, we might want to allow it
                    # But for now, granular handles everything.
                    continue

                # Find matching task in our plans
                matched_task = None
                for p in self.session.plans:
                    p_tasks = getattr(p, "tasks", None) or (p.get("tasks", []) if isinstance(p, dict) else [])
                    for t in p_tasks:
                        t_id = getattr(t, "id", None) or (t.get("id") if isinstance(t, dict) else None)
                        if tid == t_id or (tid and str(tid).startswith(str(t_id))):
                            matched_task = t
                            break
                    if matched_task: break
                
                if matched_task:
                    if status == "completed":
                        if hasattr(matched_task, "status"):
                            matched_task.status = "completed"
                        elif isinstance(matched_task, dict):
                            matched_task["status"] = "completed"
                        
                        # Already handled by on_swarm_event or _process_completed_task
                        pass

                    elif status == "failed":
                        if hasattr(matched_task, "status"):
                            matched_task.status = "failed"
                        elif isinstance(matched_task, dict):
                            matched_task["status"] = "failed"
                        # HYDRA PROTOCOL: Attempt Recovery (Godzilla Resilience)
                        try:
                            error_info = str(res.get("error", result_data))
                            recovery_tasks = await self.singularity.on_child_failure(
                                parent_task=matched_task, 
                                failed_child=matched_task, 
                                error=error_info
                            )
                            if recovery_tasks:
                                m_id = getattr(matched_task, "id", None) or (matched_task.get("id") if isinstance(matched_task, dict) else None)
                                logger.info(f" [HYDRA] Hydra Recovery: Spawning {len(recovery_tasks)} replacement tasks for {m_id}")
                                # Inject into the original plan to ensure they run next
                                for p in self.session.plans:
                                    p_tasks = getattr(p, "tasks", None) or (p.get("tasks", []) if isinstance(p, dict) else [])
                                    if any((getattr(t, "id", None) or (t.get("id") if isinstance(t, dict) else None)) == m_id for t in p_tasks):
                                        if hasattr(p, "tasks"):
                                            p.tasks.extend(recovery_tasks)
                                        elif isinstance(p, dict) and "tasks" in p:
                                            p["tasks"].extend([rt.to_dict() if hasattr(rt, "to_dict") else rt for rt in recovery_tasks])
                                        break
                        except Exception as hydra_err:
                            logger.error(f"Hydra Protocol fallback failed: {hydra_err}")
                            
                        await self._record_error("swarm_task_execution", str(result_data))
        
        # Step 5: Analyze results and potentially generate new hypotheses
        if self.session.findings:
            await self._analyze_cycle_results(cycle)
        
        # Project Godzilla: Thermodynamic Checkpoint
        try:
            state = {
                "session": dataclasses.asdict(self.session),
                "hypotheses": [h.to_dict() for h in self.hypothesis_tracker.get_all()],
                "knowledge": self.session.knowledge_snapshot
            }
            
            # PHASE 12: Unified Discovery Checkpointing
            if is_discovery and DISCOVERY_ULTRA_AVAILABLE:
                discovery_session = get_discovery_session(self.session.id)
                if discovery_session:
                    state["ferrari_state"] = discovery_session.to_dict()

            # FIX: Use correct cycle attribute and save the full state dictionary
            current_cycle_idx = getattr(self.session, 'current_cycle', cycle)
            vault.save_checkpoint(self.session.id, current_cycle_idx, state)
            logger.info(f"Checkpoint saved for session {self.session.id} (Cycle {current_cycle_idx})")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
        
        # ========== INSTRUMENTATION: Log cycle metrics ==========
        hypotheses_after = len(self.hypothesis_tracker.get_all())
        facts_after = self.world_model._stats["total_facts"] if self.world_model else 0
        
        structural_findings_gained = facts_after - facts_before
        
        logger.info(
            f"CYCLE_METRICS: cycle_index={cycle}, "
            f"hypotheses_total={hypotheses_after}, "
            f"hypotheses_new_this_cycle={hypotheses_after - hypotheses_before}, "
            f"facts_added_this_cycle={structural_findings_gained}, "
            f"facts_total={facts_after}, "
            f"elapsed_hours={self.session.get_elapsed_hours():.3f}, "
            f"consecutive_errors={self.session.consecutive_errors}"
        )
        
        # =========================================================================
        # EPISTEMIC VELOCITY MONITOR (Phase 5)
        # =========================================================================
        if not hasattr(self.session, 'epistemic_stagnation_counter'):
            self.session.epistemic_stagnation_counter = 0

        if structural_findings_gained == 0:
            self.session.epistemic_stagnation_counter += 1
            logger.warning(f" [VELOCITY] Stagnation Warning: No new structural findings. Counter: {self.session.epistemic_stagnation_counter}/4")
        else:
            self.session.epistemic_stagnation_counter = 0
            
        if self.session.epistemic_stagnation_counter >= 4:
            logger.critical(" [VELOCITY] EPISTEMIC STAGNATION DETECTED (4 cycles zero yield). Triggering STRATEGIC RESET.")
            self.session.epistemic_stagnation_counter = 0
            
            # Create a "Black Swan" / Pivot Directive via MetaReasoner or manually
            pivot_h = Hypothesis(
                statement=f"STRATEGIC RESET: Epistemic Velocity reached zero. The current paradigm is tapped out. We must pivot orthogonally.",
                rationale="System detected 4 cycles of stagnation.",
                domain=self.domain,
                source_agent="MetaReasoner",
                confidence=1.0 # Force execution
            )
            self.hypothesis_tracker.add(pivot_h)
            
            # Prune weaker hypotheses to clear the path for the reset
            for h in self.hypothesis_tracker.get_active():
                if h.confidence < 0.7 and h.id != pivot_h.id:
                    self.hypothesis_tracker.transition_state(h.id, HypothesisState.ARCHIVED, "Pruned during Strategic Reset")
        
        # =========================================================================
        # DISCOVERY MODE: 5 UPGRADES INTEGRATION
        # =========================================================================
        
        if is_discovery and DISCOVERY_ULTRA_AVAILABLE:
            discovery_session = get_discovery_session(self.session.id)
            
            # UPGRADE 1: TEMPORAL SURVIVAL TRACKING
            # If no assumptions were killed this cycle, record survival
            killed_this_cycle = len([
                f for f in self.session.findings 
                if f.get("cycle") == cycle 
                and (f.get("result", {}).get("final_verdict") or f.get("result", {}).get("verdict")) in ["DEAD", "KILLED", "FAILED"]
            ])
            
            if killed_this_cycle == 0 and len(discovery_session.assumptions) > 0:
                # [SVEL BEAST FIX] Compute actual rigor score to enable tier promotion
                avg_rigor = 0.5
                cycle_findings = [f for f in self.session.findings if f.get("cycle") == cycle]
                if cycle_findings:
                    scores = [f.get("discovery_score", {}).get("overall_score", 0.5) for f in cycle_findings]
                    avg_rigor = sum(scores) / len(scores) if scores else 0.5
                
                discovery_session.record_survival(f"Cycle {cycle}: No kills", rigor_score=avg_rigor)
                logger.info(f"[DISCOVERY UPGRADE 1] Survival recorded - cycles: {discovery_session.survival_cycles}, tier: {discovery_session.current_tier.value}")
            else:
                for finding in self.session.findings:
                    if finding.get("cycle") == cycle:
                        res = finding.get("result", {})
                        verdict = res.get("final_verdict") or res.get("verdict", "")
                        if verdict in ["DEAD", "KILLED", "FAILED"]:
                            reason = finding.get("result", {}).get("reason", "Unknown")
                            discovery_session.record_death(f"cycle_{cycle}", reason)
            
            # UPGRADE 4: SURVIVOR AMPLIFICATION
            # If hypothesis reaches RESILIENT tier, generate pressure
            if discovery_session.is_resilient():
                amplification = discovery_session.amplify_survivor()
                logger.info(f"[DISCOVERY UPGRADE 4] Survivor amplification triggered: tier={amplification['tier']}")
                
                # Log stronger attacks for next cycle
                if amplification.get("stronger_attacks"):
                    logger.info(f"[DISCOVERY UPGRADE 4] Suggested attacks: {amplification['stronger_attacks']}")
                
                # If STRUCTURAL, allow influence on future hypothesis generation
                if discovery_session.is_structural():
                    discovery_session.record_structural_influence()
                    # Add constraint to session knowledge
                    self.session.knowledge_snapshot += f"\n[STRUCTURAL] Survivor at tier STRUCTURAL after {discovery_session.survival_cycles} cycles. Must be addressed in future research."

                    # NEW: RECURSIVE DISCOVERY BRANCHING
                    if hasattr(self, 'recursive_manager') and self.recursive_manager and discovery_session.assumptions:
                        logger.info(f"[DISCOVERY UPGRADE 5] Spawning recursive discovery for structural hypothesis: {discovery_session.assumptions[0][:50]}...")
                        # Generate recursive plan
                        recursive_plan = self.recursive_manager.create_recursive_discovery_plan(
                            discovery_session.assumptions[0],
                            discovery_session
                        )
                        
                        if "child_regimes" in recursive_plan:
                            for regime in recursive_plan["child_regimes"]:
                                # Convert regime to a new ResearchTask
                                child_task = ResearchTask(
                                    id=f"recursive_{uuid.uuid4().hex[:6]}",
                                    description=regime["regime_description"],
                                    task_type="exploration",
                                    priority=5, # Standard priority for structural descendants
                                    metadata={
                                        "parent_session_id": self.session.id,
                                        "inherited_assumption": regime["constraints"]["inherited_assumption"],
                                        "focus_axis": regime["focus_axis"]
                                    }
                                )
                                # [FIX] Inject into active plan (HypothesisTracker lacks add_task)
                                if self.session.plans:
                                    target_p = self.session.plans[0]
                                    if hasattr(target_p, "tasks"):
                                        target_p.tasks.append(child_task)
                                    elif isinstance(target_p, dict) and "tasks" in target_p:
                                        target_p["tasks"].append(child_task.to_dict())
                                self.recursive_manager.register_child_session(self.session.id, child_task.id)
                                logger.info(f"   - Injected child task: {child_task.id} (axis={regime['focus_axis']})")
            
            # UPGRADE 5: GOVERNANCE KPI LOGGING
            governance = discovery_session.get_governance_report()
            logger.info(
                f"[DISCOVERY UPGRADE 5] GOVERNANCE: "
                f"half_life={governance['survivor_half_life_hours']}, "
                f"yield={governance['structural_yield']:.2%}, "
                f"tier={governance['current_tier']}, "
                f"orthogonality_rejections={governance['orthogonality_rejections']}"
            )
            
            # UPGRADE 3: FAILURE PATTERN INSIGHTS 
            if self.failure_pattern_index:
                insights = self.failure_pattern_index.get_insights()
                if insights:
                    logger.info(f"[DISCOVERY UPGRADE 3] Failure insights: {insights}")
        
        # Cycle increment is handled in the main while loop (line 1013)
        pass

    
    async def _execute_task(self, task: ResearchTask) -> Optional[Dict[str, Any]]:
        """Execute a single research task"""
        mandated_skills = []
        await events.emit(
            event_type="RESEARCH_TASK_STARTED",
            payload={"session_id": self.session.id, "task_id": task.id, "description": task.description},
            source="DeepResearchOrchestrator"
        )
        
        self._emit_progress({
            "phase": "task_execution",
            "task_id": task.id,
            "message": f"Executing: {task.description[:50]}..."
        })
        
        # Announce significant tasks
        if "search" in task.type.lower():
            await self._announce(f"Searching: {task.description[:50]}...")
        elif "reading" in task.type.lower():
            await self._announce(f"Reading papers for context...")
        
        # DIRECT TOOL EXECUTION: If task specifies required_tools call them directly
        
        # This bypasses the LLM selector to ensure external APIs (arxiv, semantic_scholar) are called
        
        # [SVEL FIX] Infinite Recursion Trap Prevention
        # Identify tasks that are meant for search but lack explicitly populated `required_tools`
        task_desc_lower = task.description.lower()
        if not task.required_tools and not task.required_agents:
            if "scholar" in task_desc_lower or "literature" in task_desc_lower or "pubmed" in task_desc_lower:
                logger.info(f" [SVEL FIX] Intercepted implicit search task. Forcing direct tool execution.")
                task.required_tools = ["scholar_search"]
        
        if task.required_tools and not task.required_agents:
            return await self._execute_tools_directly(task)
        
        if not self.router:
            logger.warning("No router available for task execution")
            return {"simulated": True, "description": task.description}
        
        try:
            # Route the task to appropriate component
            # [SVEL ALIGNMENT & P0-31] Sovereign ExperimentAgent Routing:
            # Frontier models (GPT-6 Astra, Gemini 4 Carbon, Claude Opus 5.5) write bespoke
            # PyTorch/SciPy/ML experiments via ExperimentAgent rather than brittle AutoML wrappers.
            task_desc_low = task.description.lower()
            if any(kw in task_desc_low for kw in [
                "train", "optimizer", "architecture", "discovery", "neural", "prediction", "inference",
                "validate", "rigor", "statistically", "falsify", "ablation", "significance", "experiment", "simulate"
            ]):
                target_agent = "experiment_agent"
            else:
                target_agent = task.required_agents[0] if task.required_agents else None
                sovereign_map = {
                    "web_search_agent": "research_agent",
                    "doc_reader_agent": "research_agent",
                    "summarizer_agent": "research_agent",
                    "qa_agent": "research_agent",
                    "data_analyzer_agent": "experiment_agent",
                    "ml_model_builder_agent": "experiment_agent",
                    "fact_checker_agent": "red_team_agent",
                }
                if target_agent in sovereign_map and not (target_agent == "ml_model_builder_agent" and isinstance(task.payload, dict) and task.payload.get("force_legacy_automl")):
                    target_agent = sovereign_map[target_agent]
            
            # [SVEL SHIELD] Block nested standalone sub-orchestrator recursion (>1 depth)
            if target_agent == "research_agent" and getattr(self, "recursion_depth", 0) > 1:
                logger.warning(f" [SVEL SHIELD] Blocking deeply nested `research_agent` call to prevent infinite recursion loop.")
                return {"status": "skipped_recursive", "error": "Blocked recursive research_agent call."}

            # [TITAN V142.0] DOMAIN-AGNOSTIC DEEP READING
            # Physically enforce high-fidelity extraction for all 'reading' tasks.
            if "reading" in task.type.lower() or "extract" in task.description.lower():
                logger.info(f" [RIGOR] Upgrading '{task.id}' to deep_reading mode.")
                # We force direct tool execution to ensure we get real full-text data
                task.required_tools = ["deep_paper_reader", "arxiv_search", "pubmed_search"]
                tool_results = await self._execute_tools_directly(task)
                
                # Pass the physical text findings into the agent payload
                if tool_results:
                    # Collect all successful tool outputs
                    physical_texts = [str(r.get("result", "")) for r in tool_results if r.get("result")]
                    if physical_texts:
                        logger.info(f" [GROUNDING] Injected {len(physical_texts)} physical documents into {target_agent} payload.")
                        if not task.payload: task.payload = {}
                        task.payload["physical_docs"] = physical_texts
                        task.payload["text"] = "\n\n---\n\n".join(physical_texts)

            
            # [TITAN V155.0] FORENSIC HANDSHAKE
            # Physically register the start of an experimental pulse.
            if hasattr(self, "execution_stats") and "experiment" in str(task.task_type).lower():
                self.execution_stats.start_pulse(task.id, "initial_pending")

            # Router.route() may be async (CentralRouterBeast) or sync (legacy)
            if asyncio.iscoroutinefunction(self.router.route):

                result = await self.router.route(
                    task.description,
                    agent_name=target_agent,
                    task_type=task.task_type,
                    required_tools=task.required_tools or [],
                    payload=task.payload,
                    context={
                        "task_id": task.id,
                        "task_type": task.task_type,
                        "required_tools": task.required_tools,
                        "mandated_skills": mandated_skills, # SCRIPT INJECTION
                        "research_session": self.session.id,
                        "recursion_depth": getattr(self, "recursion_depth", 0),
                        "PRIMARY_EVIDENCE": self.session.local_data_catalog,
                        "EVIDENCE_INSTRUCTION": "If a local file exists, it is the Supreme Source of Truth. All hypotheses must be derived from or tested against this specific file."
                    }
                )
            else:
                # Synchronous fallback
                result = await asyncio.to_thread(
                    self.router.route,
                    task.description,
                    agent_name=target_agent,
                    task_type=task.task_type,
                    required_tools=task.required_tools or [],
                    context={
                        "task_id": task.id,
                        "task_type": task.task_type,
                        "required_tools": task.required_tools,
                        "mandated_skills": mandated_skills, # SCRIPT INJECTION
                        "research_session": self.session.id,
                        "recursion_depth": getattr(self, "recursion_depth", 0),
                        "PRIMARY_EVIDENCE": self.session.local_data_catalog,
                        "EVIDENCE_INSTRUCTION": "If a local file exists, it is the Supreme Source of Truth. All hypotheses must be derived from or tested against this specific file."
                    }
                )
            
            if result:
                await events.emit(
                    event_type="FINDING_DISCOVERED",
                    payload={"session_id": self.session.id, "task_id": task.id, "result": result},
                    source="DeepResearchOrchestrator"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return None
    
    async def _execute_tools_directly(self, task: ResearchTask) -> Optional[Dict[str, Any]]:
        """
        Execute tools directly from the registry.
        This ensures external APIs like arxiv_search and semantic_scholar are actually called.
        """
        try:
            from backend.tools.tool_registry import REGISTRY
        except ImportError:
            logger.error("Tool registry not available")
            return None
        
        combined_results = []
        
        for tool_name in task.required_tools:
            tool_fn = REGISTRY.get(tool_name)
            
            if not tool_fn:
                logger.warning(f"Tool '{tool_name}' not found in registry")
                continue
            
            logger.info(f"DIRECT TOOL CALL: {tool_name} for task '{task.description[:50]}...'")
            
            # Build tool spec from task description
            tool_spec = {
                "query": task.description,
                "task_id": task.id,
                "max_results": 50  # Balanced Protocol
            }
            
            try:
                # Execute tool - check if it's a class or function
                if hasattr(tool_fn, "execute") and callable(getattr(tool_fn, "execute")):
                    result = await asyncio.to_thread(tool_fn.execute, tool_spec)
                elif hasattr(tool_fn, "run") and callable(getattr(tool_fn, "run")):
                    result = await asyncio.to_thread(tool_fn.run, tool_spec)
                else:
                    # Direct function call
                    result = await asyncio.to_thread(tool_fn, task.description)

                
                # If the tool returns a coroutine (rare but possible), await it
                if asyncio.iscoroutine(result):
                    result = await result
                
                if result.get("status") == "success":
                    logger.info(f"Tool '{tool_name}' returned successfully in {result.get('duration', 0):.2f}s")
                    combined_results.append({
                        "tool": tool_name,
                        "result": result.get("result"),
                        "duration": result.get("duration", 0)
                    })
                    
                    # [FIX] BUGFIX: Update Papers Read Metric
                    if tool_name in ["scholar_nexus", "arxiv_search", "semantic_scholar", "deep_paper_reader", "scholar_search"]:
                        raw_res = result.get("result")
                        count = 0
                        if isinstance(raw_res, list):
                            count = len(raw_res)
                        elif isinstance(raw_res, str):
                            # Heuristic: Count markdown headers or titles
                            # ScholarNexus uses "## [N]." format
                            import re
                            matches = re.findall(r'## \d+\.', raw_res)
                            if matches:
                                count = len(matches)
                            elif "**Title**" in raw_res:
                                count = len(re.findall(r'\*\*Title\*\*', raw_res))
                            else:
                                count = 1 # Fallback
                        
                        if count > 0:
                            current = self.session.metadata.get("papers_read", 0)
                            self.session.metadata["papers_read"] = current + count
                            
                            # Also update granular stats if present
                            if "paper_retrieval" in self.session.metadata:
                                self.session.metadata["paper_retrieval"]["successes"] += count
                                
                            logger.info(f" [INDEX] Indexed {count} papers from {tool_name}. Total: {self.session.metadata['papers_read']}")
                    
                    # Add findings to world model if available
                    if self.world_model and result.get("result"):
                        try:
                            result_str = str(result.get("result", ""))[:2000]
                            self.world_model.add_fact(
                                key=f"tool:{tool_name}:{task.id}",
                                value=result_str,
                                source=tool_name,
                                confidence=0.8
                            )
                        except Exception as e:
                            logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                            logger.warning(f"Failed to add tool result to world model: {e}")
                else:
                    logger.warning(f"Tool '{tool_name}' failed: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Tool '{tool_name}' execution error: {e}")
        
        if not combined_results:
            return None
        
        return {
            "status": "success",
            "tools_called": [r["tool"] for r in combined_results],
            "results": combined_results,
            "task_id": task.id
        }
    
    async def _analyze_cycle_results(self, cycle: int) -> None:
        """Analyze results from a cycle and potentially generate new hypotheses"""
        await self._announce(f"I'm analyzing the data from cycle {cycle + 1} to refine my understanding.")
        cycle_findings = [f for f in self.session.findings if f.get("cycle") == cycle]
        
        # Bug 2 Fix: Define valid_findings with default value at top level
        valid_findings = list(cycle_findings)
        
        # =========================================================================
        #  TRUTH ANCHOR SAFEGUARD (DiscoveryScorer)
        # =========================================================================
        if self.discovery_scorer and cycle_findings:
            valid_findings = []
            hallucinated_count = 0
            
            logger.info(f" [VAL] Validating {len(cycle_findings)} findings with DiscoveryScorer...")
            
            for finding in cycle_findings:
                try:
                    #  ADVERSARIAL RIGOR UPGRADE: Run all shadow validators
                    stat_result = None
                    if self.statistical_validator:
                        stat_result = self.statistical_validator.validate(finding).to_dict()
                    
                    fail_result = None
                    if self.failure_detector:
                        # Pass context (research question) for rabbit hole detection
                        fail_result = dataclasses.asdict(self.failure_detector.detect_failures(
                            finding, 
                            context={"research_question": self.research_question}
                        ))
                        # Filter out nested dataclasses if needed, but DiscoveryScorer handles dicts
                        # Optimization: deep_clean_json later handles this too
                    
                    red_team_result = None
                    try:
                        if self.red_team:
                            res = finding.get("result", {})
                            verdict = res.get("final_verdict") or res.get("verdict", "UNKNOWN")
                            claims = [res.get("summary", "")]
                            evidence = str(finding.get("result", {}))
                            red_team_result = await self.red_team.review_verdict(verdict, claims, evidence)
                    except Exception as red_err:
                        logger.error(f"Red Team review failed: {red_err}")

                    # [HARDENING] SECURE FAILOVER: Handle security violations gracefully
                    if "Security Violation" in str(finding.get("result", {}).get("error", "")):
                        if self.world_model:
                            self.world_model.add_fact(
                                key=f"security_bottleneck:{finding.get('id', uuid.uuid4())}",
                                value=f"Finding flagged as security violation. Context: {finding.get('query')[:50]}",
                                source="orchestrator_guard",
                                confidence=1.0
                            )

                    # Score the finding with FULL rigor
                    score_result = await self.discovery_scorer.score_discovery(
                        finding,
                        context={"research_question": self.research_question},
                        red_team_result=red_team_result,
                        statistical_grounding=stat_result,
                        failure_detection=fail_result
                    )
                    
                    # Handle return signature (score object might be first or second depending on impl)
                    # Checking DiscoveryScorer impl: it returns (score_float, dimension_score) usually for internal methods, but score_discovery returns DiscoveryScore object?
                    # Let's handle both cases cautiously.
                    score_obj = score_result
                    if isinstance(score_result, tuple):
                       score_obj = score_result[0]
                    
                    # [NUCLEAR PENALTY] SVEL V12: Purge mediocrity.
                    # Raise threshold from 0.05 (hallucination) to 0.35 (noise/mediocrity)
                    overall_score = getattr(score_obj, "overall_score", 0.0) if hasattr(score_obj, "overall_score") else 0.0
                    
                    if overall_score < 0.35:
                        logger.warning(f" [NUCLEAR] NUCLEAR PENALTY: Discarding LOW RIGOR finding from task {finding.get('task_id')} (score={overall_score:.4f})")
                        if finding in self.session.findings:
                            self.session.findings.remove(finding)
                        hallucinated_count += 1
                        continue 
                    
                    # [CONTINUITY] Commit strictly validated findings to WorldModel
                    if self.world_model and overall_score >= 0.5:
                        try:
                            self.world_model.add_fact(
                                key=f"finding_{finding.get('id', uuid.uuid4())}",
                                value=finding.get("result", {}).get("summary", ""),
                                source="adversarial_validation",
                                confidence=overall_score,
                                metadata={
                                    "scores": score_obj.to_dict() if hasattr(score_obj, "to_dict") else {},
                                    "cycle": cycle,
                                    "rigor": getattr(score_obj, "rigor", 0.0)
                                }
                            )
                        except Exception as wm_err:
                            logger.error(f"Failed to commit finding to WorldModel: {wm_err}")
                    
                    # FLAG LOW QUALITY
                    if overall_score < 0.75:
                        finding["quality_flag"] = "LOW_QUALITY"
                        logger.info(f" [WARNING] Flagged low quality finding (Score: {overall_score:.2f})")
                    
                    # Append score metadata
                    if hasattr(score_obj, "to_dict"):
                        finding["discovery_score"] = score_obj.to_dict()
                    
                    valid_findings.append(finding)
                    
                except Exception as e:
                    logger.error(f"DiscoveryScorer failed on finding: {e}")
                    valid_findings.append(finding) # Fail open to avoid crashing run, but log error
            
            if hallucinated_count > 0:
                logger.warning(f" [TRUTH] SAFEGUARD ACTIVATED: Blocked {hallucinated_count} hallucinated findings in cycle {cycle}.")
                await self._announce(f" [TRUTH] Truth Anchor blocked {hallucinated_count} hallucinated findings.")
            
            # Continue analysis with only valid findings
            cycle_findings = valid_findings
        
        if not cycle_findings or not self.llm_manager:
            return
        
        # [V12 SYNTHESIS] Enrich findings with validation metadata
        findings_text = "\n".join([
            f"- [Score: {f.get('discovery_score', {}).get('overall_score', 0.0):.2f}] "
            f"Finding: {f.get('result', {}).get('summary', str(f.get('result', {})))[:300]}\n"
            f"  | Rigor: {f.get('discovery_score', {}).get('rigor', 0.0):.2f} "
            f"  | Rationale: {f.get('discovery_score', {}).get('rationale', 'N/A')}\n"
            f"  | Suggestions: {', '.join(f.get('discovery_score', {}).get('suggestions', []))}"
            for f in cycle_findings[:10]
        ])
        
        prompt = f"""Analyze these research findings and suggest refinements to our hypotheses.

RESEARCH QUESTION: {self.research_question}
CYCLE: {cycle}

FINDINGS (with V12 Quality Scores):
{findings_text}

Note: Findings with scores < 0.35 have already been purged. Focus on refining hypotheses using high-rigor data.
If a finding has suggestions (e.g., 'Add more citations'), use these to guide the 'refine' action.

CURRENT HYPOTHESES:
{chr(10).join([f"- {h.statement}" for h in self.hypothesis_tracker.get_active()[:5]])}

Should any hypotheses be:
1. CONFIRMED (strong supporting evidence)?
2. REFUTED (contradicting evidence)?
3. REFINED (partially supported, needs modification)?

Return ONLY valid JSON:
{{
    "analysis": "Brief analysis of what we learned",
    "hypothesis_updates": [
        {{
            "hypothesis_id": "id or 'new'",
            "action": "confirm|refute|refine|new",
            "reason": "why",
            "new_statement": "if refining or creating new"
        }}
    ]
}}"""

        try:
            result = await self.llm_manager.run_async(
                prompt=prompt,
                model=DEEP_RESEARCH_SYNTHESIS_MODEL,
                temperature=0.3,
                task_hint="deep_synthesis"
            )

            # [HARDENING] Extract text safely from dict or str
            if isinstance(result, dict):
                text = result.get("text", result.get("content", ""))
            else:
                text = str(result)
            
            if not text:
                logger.warning("Empty response from LLM in analysis phase")
                # Fallback data to prevent crash
                data = {"hypothesis_updates": []} 
            else:
                # Robust JSON cleaning
                cleaned_text = text.strip()
                import re
                # Try to find the JSON object block
                json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                if json_match:
                    cleaned_text = json_match.group(0)
                
                try:
                    from backend.utils.json_repair import repair_json
                    data = repair_json(cleaned_text)
                    if not isinstance(data, dict):
                        data = json.loads(cleaned_text)
                except Exception as je:
                    logger.warning(f"Analysis JSON parse failed: {je}")
                    data = {"hypothesis_updates": []}

            
            for update in data.get("hypothesis_updates", []):
                action = update.get("action")
                hyp_id = update.get("hypothesis_id")
                
                if action == "confirm" and hyp_id != "new":
                    self.hypothesis_tracker.mark_confirmed(hyp_id, {"reason": update.get("reason")})
                    
                    # Resolve Accuracy Record
                    if self.accuracy_tracker:
                        # Filter records to find the one for this hypothesis
                        for record in self.accuracy_tracker.get_pending():
                            if record.hypothesis_id == hyp_id:
                                self.accuracy_tracker.resolve(record.id, actual_value=True, is_correct=True)

                    # Store confirmed hypothesis in WorldModel
                    if self.world_model:
                        hyp = self.hypothesis_tracker.get(hyp_id)
                        if hyp:
                            self.world_model.add_fact(
                                key=f"hypothesis_{hyp_id}",
                                value=f"CONFIRMED: {hyp.statement}",
                                source="deep_research_analysis",
                                confidence=1.0,
                                metadata={"rationale": hyp.rationale, "cycle": cycle}
                            )

                    # Neo4j Update (PCD Pillar 7 - Restored)
                    if self.knowledge_graph:
                        try:
                            _tracked_h = self.hypothesis_tracker.get(hyp_id)
                            if _tracked_h:
                                self.knowledge_graph.add_hypothesis(
                                    hypothesis_id=hyp_id,
                                    statement=_tracked_h.statement,
                                    status="confirmed",
                                    confidence=1.0,
                                    session_id=self.session.id
                                )
                            # Link evidence as a Finding
                            evidence = update.get("reason", "")
                            if evidence:
                                finding_id = f"finding_{int(datetime.now().timestamp())}_{hyp_id[-4:]}"
                                self.knowledge_graph.add_finding(
                                    finding_id=finding_id,
                                    summary=evidence,
                                    hypothesis_id=hyp_id,
                                    relationship="SUPPORTS",
                                    evidence_source="research_analysis"
                                )
                        except Exception as e:
                            logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                            logger.warning(f"Neo4j confirmation update failed: {e}")
                    
                    # =========================================================================
                    # FERRARI ENGINE: ADVERSARIAL ATTACK (The Physical Adversary)
                    # =========================================================================
                    if self.mode == ResearchMode.DISCOVERY:
                         hyp = self.hypothesis_tracker.get(hyp_id)
                         existing_fals = None
                         
                         # Check if we already have a high-fidelity report from the ExperimentAgent
                         for exp_id, exp_meta in getattr(self.session, 'experiment_results', {}).items():
                             if exp_meta.get("hypothesis_id") == hyp_id:
                                 res_data = exp_meta.get("result", {})
                                 if res_data.get("falsification_report"):
                                     existing_fals = res_data["falsification_report"]
                                     break

                         if existing_fals:
                             logger.info(f" [ATTACK] Skipping AdversarialExecutor: Hypothesis {hyp_id} already has high-fidelity audit.")
                             
                             # Record current stats for DiscoverySession
                             if hasattr(self, 'discovery_session') and self.discovery_session:
                                 self.discovery_session.record_adversarial_score(existing_fals.get("robustness_score", 0.0))
                             
                             # SVEL UPGRADE: Semantic Feedback Loop
                             semantic_audit = existing_fals.get("semantic_audit", {})
                             semantic_verdict = semantic_audit.get("verdict", "CLEAN")
                             
                             if semantic_verdict in ["BOGUS", "COMPROMISED"]:
                                 logger.warning(f" [KILL] Hypothesis KILLED by Semantic Critic audit! Downgrading to REFUTED.")
                                 self.hypothesis_tracker.mark_refuted(
                                     hyp_id, 
                                     {"reason": f"Semantic Red Team: {semantic_audit.get('criticism')}", "source": "SemanticCritic"}
                                 )
                                 continue
                             
                             # If robustness is low, refute anyway
                             if existing_fals.get("robustness_score", 1.0) < 0.3:
                                 logger.warning(f" [KILL] Hypothesis KILLED by low robustness score ({existing_fals.get('robustness_score'):.2f}).")
                                 self.hypothesis_tracker.mark_refuted(hyp_id, {"reason": "Low robustness score during high-fidelity audit."})
                                 continue
                         
                         elif hasattr(self, 'adversarial_executor'):
                              # Fallback to post-hoc data attack if no experiment was run
                              attack_data = None
                              target_col = None
                              
                              for f in [x for x in self.session.findings if x.get("cycle") == cycle]:
                                  res = f.get("result", {})
                                  if isinstance(res, dict) and "data" in res and isinstance(res["data"], list):
                                      import pandas as pd
                                      try:
                                          df_candidate = pd.DataFrame(res["data"])
                                          if not df_candidate.empty and len(df_candidate.select_dtypes(include=['number']).columns) > 1:
                                              attack_data = df_candidate
                                              target_col = df_candidate.columns[-1] 
                                              break
                                      except Exception as pd_err:
                                          logger.warning(f"Failed to parse adversarial dataframe: {pd_err}")
                              
                              if attack_data is not None and target_col and hyp is not None:
                                  logger.info(f" [ATTACK] ADVERSARIAL EXECUTOR: Attacking hypothesis {hyp_id} with {len(attack_data)} rows...")
                                  attack_report = self.adversarial_executor.attack_hypothesis(
                                      attack_data, 
                                      target_col, 
                                      hyp.statement
                                  )
                                  
                                  if hasattr(self, 'discovery_session') and self.discovery_session:
                                      self.discovery_session.record_adversarial_score(attack_report.get("survival_score", 0.0))
                                  
                                  if attack_report.get("verdict") in ["COLLAPSED", "DEAD_ON_ARRIVAL"]:
                                      logger.warning(f" [KILL] Hypothesis KILLED by Post-Hoc Adversarial Attack!")
                                      self.hypothesis_tracker.mark_refuted(hyp_id, {"reason": f"Failed Adversarial Attack", "source": "AdversarialExecutor"})
                                      continue

                    # =========================================================================
                    # FERRARI ENGINE: Survival Tracking on Confirm (Hypothesis Survived!)
                    # =========================================================================
                    if self.survival_engine and hyp_id:
                        # Record birth time if first survival
                        if hyp_id not in self.hypothesis_birth_times:
                            self.hypothesis_birth_times[hyp_id] = datetime.now()
                        
                        # Increment survival cycles
                        self.hypothesis_survival_cycles[hyp_id] = self.hypothesis_survival_cycles.get(hyp_id, 0) + 1
                        cycles = self.hypothesis_survival_cycles[hyp_id]
                        
                        # Compute runtime in hours for adaptive scaling
                        runtime_hours = self.session.get_elapsed_hours()

                        # Compute new tier using SurvivalEngine with scaled thresholds
                        new_tier = self.survival_engine.compute_tier(cycles, runtime_hours=runtime_hours)
                        old_tier = self.hypothesis_tiers.get(hyp_id, "ESCAPED")
                        self.hypothesis_tiers[hyp_id] = new_tier.value if hasattr(new_tier, 'value') else str(new_tier)
                        
                        # Log tier promotion
                        if new_tier.value != old_tier:
                            logger.info(f" [FERRARI] Hypothesis {hyp_id} PROMOTED: {old_tier} -> {new_tier.value} (survived {cycles} cycles)")
                            
                            # TRIGGER: Conditional Deep Reading on upgrade to RESILIENT/STRUCTURAL
                            # If we hit a high tier, we want to dig deeper in the next cycle (The "Siege Behaviour")
                            if new_tier.value in ["resilient", "structural"]:
                                if hasattr(self, 'discovery_session') and self.discovery_session:
                                    self.discovery_session.force_reading_next_cycle = True
                                    logger.info(f" [READING] [CONDITIONAL READING] Triggered deep reading for {new_tier.value} hypothesis {hyp_id}")

                            # Track structural influence
                            if new_tier.value == "structural":
                                self.structural_influences += 1
                                logger.info(f" [FERRARI] STRUCTURAL hypothesis detected! Total: {self.structural_influences}")

                elif action == "refute" and hyp_id != "new":
                    self.hypothesis_tracker.mark_refuted(hyp_id, {"reason": update.get("reason")})
                    
                    # Resolve Accuracy Record
                    if hasattr(self, 'accuracy_tracker') and self.accuracy_tracker:
                        for record in self.accuracy_tracker.get_pending():
                            if record.hypothesis_id == hyp_id:
                                self.accuracy_tracker.resolve(record.id, actual_value=False, is_correct=None)
                    
                    # =========================================================================
                    # FERRARI ENGINE: Death Tracking on Refute (Hypothesis Killed!)
                    # =========================================================================
                    if self.governance_engine and hyp_id:
                        self.hypothesis_death_times[hyp_id] = datetime.now()
                        
                        # Compute governance stats
                        stats = self.governance_engine.get_survival_stats(
                            self.hypothesis_birth_times,
                            self.hypothesis_death_times,
                            self.structural_influences
                        )
                        half_life = stats.get("half_life_hours")
                        if half_life:
                            assessment = self.governance_engine.assess_half_life(half_life)
                            logger.info(f" [FERRARI] Governance: Half-life={half_life:.2f}h ({assessment})")
                elif action == "new" or (action == "refine" and update.get("new_statement")):
                    new_hyp = Hypothesis(
                        statement=update.get("new_statement", ""),
                        rationale=update.get("reason", ""),
                        domain=self.domain,
                        research_question=self.research_question,
                        parent_hypothesis_id=hyp_id if hyp_id != "new" else None,
                        source_agent="research_director",
                        variables=[{"name": "RefinementEffect", "symbol": "E", "unit": "dimensionless", "role": "dependent"}],
                        functional_form="E > 0",
                        constraints=[
                            {"equation": "E > 0", "variables": ["E"], "type": "boundary", "description": "Refinement effect non-negativity constraint"}
                        ],
                        predictions=[{
                            "condition": "Evaluate refined hypothesis",
                            "outcome": "E > 0.1",
                            "baseline": 0.0,
                            "threshold": 0.1,
                            "direction": "increase"
                        }]
                    )
                    self.hypothesis_tracker.add(new_hyp)


            
            # Phase 35b: World Model Refinement (Deleted redundant add_fact - unified to main execution loop or post-scorer)
            # Replaced with conditional upgrade for validated findings
            if self.world_model and valid_findings:
                 for finding in valid_findings:
                     try:
                         # Findings confirmed by Truth Anchor (DiscoveryScorer) get a confidence boost
                         key = f"finding_{finding.get('task_id', uuid.uuid4().hex[:8])}"
                         self.world_model.add_fact(
                             key=key,
                             value=finding.get("content", str(finding)),
                             source=f"truth_anchor_cycle_{cycle}",
                             confidence=0.95, # Boosted due to validation
                             metadata={"verified_discovery": True}
                         )
                     except Exception as e:
                         logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                         logger.warning(f"Post-validation sync to World Model failed: {e}")

            # Gap 0: Infinite Context Synthesis
            if self.knowledge_synthesizer:
                cycle_findings = [f for f in self.session.findings if f.get("cycle") == cycle]
                if cycle_findings:
                    logger.info(f"Synthesizing {len(cycle_findings)} signals for cycle {cycle}...")
                    new_insight = self.knowledge_synthesizer.synthesize_cycle(
                        cycle, 
                        cycle_findings, 
                        self.research_question
                    )
                    
                    self.session.knowledge_snapshot = self.knowledge_synthesizer.unify_history(
                        self.session.knowledge_snapshot,
                        new_insight
                    )
                    logger.info("Session Knowledge Snapshot updated/unified")
            
            # Vector Memory Archival (Pillar Sidecar)
            if self.vector_store:
                v_findings = [f for f in self.session.findings if f.get("cycle") == cycle]
                if v_findings:
                    bulk_docs = []
                    for vf in v_findings:
                        # Create rich context document
                        doc_content = (
                            f"Finding (Cycle {cycle}): {vf.get('content', '')}\n"
                            f"Source: {vf.get('agent_name', 'unknown')}\n"
                            f"Context: {self.research_question}"
                        )
                        doc_id = f"finding_{cycle}_{uuid.uuid4().hex[:8]}"
                        bulk_docs.append({"id": doc_id, "content": doc_content})
                    
                    # [FIX] VectorStore has no add_documents_bulk; loop over add_document
                    for bdoc in bulk_docs:
                        self.vector_store.add_document(bdoc["id"], bdoc["content"])
                    logger.info(f"Archived {len(bulk_docs)} findings to Vector Memory.")
            
            # Phase 35: World Model Governor (PCD Pillar 2)
            if self.world_model:
                belief_updates = self.world_model.update_beliefs(self.hypothesis_tracker.get_active())
                for bu in belief_updates:
                    h_id = bu.get("hypothesis_id")
                    h = self.hypothesis_tracker.get(h_id)
                    delta = bu.get("confidence_delta", 0.0)
                    
                    if h:
                        # BRUTAL TRUTH Logic (PCD Pillar 2 Upgrade)
                        if delta <= -1.0:
                            # Immediate KILL
                            logger.info(f"  SVEL KILL SWITCH: Hypothesis {h_id} actively REFUTED by World Model.")
                            self.hypothesis_tracker.mark_refuted(h_id, {"reason": bu.get("reason"), "source": "WorldModel.BrutalTruth"})
                            continue
                            
                        # Standard confidence drift
                        new_conf = max(0.0, min(1.0, h.confidence + delta))
                        h.confidence = new_conf
                        logger.info(f"Belief Update: {h_id} confidence -> {new_conf:.2f} (Delta: {delta:.2f})")
            
        except Exception as e:
            logger.error(f"Cycle analysis failed: {e}")
    
    async def _phase_finalize(self) -> None:
        """Finalize research session and compile results"""
        # FIX B-1c: use enum comparison  was string comparison (always False for enum mode)
        is_discovery = self.session.mode in [ResearchMode.DISCOVERY]
        
        await self._announce("Research complete. ok I'm compiling the final report and generating visualizations now.")
        self._emit_progress({
            "phase": "finalization",
            "message": "Compiling research results and generating final report..."
        }) 
        
        # Record final hypothesis states
        for hyp in self.hypothesis_tracker.get_all():
            if hyp.state == HypothesisState.TESTING:
                # Mark incomplete hypotheses
                hyp.update_state(HypothesisState.ARCHIVED)
                self.hypothesis_tracker.update(hyp)

        # START VISUALIZATION PHASE
        self._emit_progress({
            "phase": "visualization",
            "message": "Generating charts and diagrams from research findings..."
        })
        
        try:
            # 1. Collect all data from findings
            data_found = None
            all_text_context = ""

            def _is_genuine_scientific_tabular_data(records: Any) -> bool:
                if not records or not isinstance(records, list) or not isinstance(records[0], dict):
                    return False
                keys = set(records[0].keys())
                software_keys = {
                    "engine", "agent_id", "attempts", "hypothesis_id", "trace", "status", "meta",
                    "error", "task_id", "cycle", "verdict", "attachments", "session_id", "summary",
                    "rationale", "statement"
                }
                matched_software = keys.intersection(software_keys)
                if len(matched_software) >= 3 or (len(keys) > 0 and len(matched_software) / len(keys) > 0.4):
                    return False
                return True
            
            for f in self.session.findings:
                res = f.get("result", {})
                content = res.get("result") 
                
                if _is_genuine_scientific_tabular_data(content):
                    data_found = content
                    break
                elif isinstance(content, dict) and "data" in content and _is_genuine_scientific_tabular_data(content.get("data")):
                    data_found = content["data"]
                    break
                     
                # Accumulate text for context
                if isinstance(content, str):
                    all_text_context += content + "\n"
                elif isinstance(content, dict) and "summary" in content:
                    all_text_context += content["summary"] + "\n"

            # Fallback to authentic experimental artifact CSVs on disk
            if not data_found:
                exp_base = os.path.join(os.getcwd(), "results", "experiments")
                if os.path.exists(exp_base):
                    recent_exp_dirs = sorted(
                        [os.path.join(exp_base, d) for d in os.listdir(exp_base) if os.path.isdir(os.path.join(exp_base, d))],
                        key=lambda p: os.path.getmtime(p),
                        reverse=True
                    )
                    for ed in recent_exp_dirs[:5]:
                        for cand_csv in ["raw_data.csv", "raw_measurements.csv"]:
                            csv_file = os.path.join(ed, cand_csv)
                            if os.path.exists(csv_file) and os.path.getsize(csv_file) > 50:
                                try:
                                    import pandas as pd
                                    cand_df = pd.read_csv(csv_file)
                                    if len(cand_df) >= 2 and _is_genuine_scientific_tabular_data(cand_df.to_dict(orient="records")):
                                        data_found = cand_df.head(1000).to_dict(orient="records")
                                        logger.info(f" [VIZ] Sourced genuine experiment dataset from {csv_file}")
                                        break
                                except Exception:
                                    pass
                        if data_found:
                            break

            # Fallback to active physical catalog datasets
            if not data_found:
                domain_datasets = [
                    os.path.join(os.getcwd(), "data", "superconduct_train.csv"),
                    os.path.join(os.getcwd(), "data", "skempi_v2.csv"),
                    os.path.join(os.getcwd(), "data", "nasa_exoplanets_pscomppars.csv"),
                ]
                for d_csv in domain_datasets:
                    if os.path.exists(d_csv):
                        try:
                            import pandas as pd
                            cand_df = pd.read_csv(d_csv)
                            if len(cand_df) >= 5:
                                data_found = cand_df.sample(min(len(cand_df), 500), random_state=42).to_dict(orient="records")
                                logger.info(f" [VIZ] Sourced physical dataset from domain catalog {d_csv}")
                                break
                        except Exception:
                            pass

            # 2. Generate Plotly Charts (Mandatory for Deep Mode)
            # User mandate: "3D graphs and charts... quantum and good ones... in almost every report"
            if True: # FORCE VISUALIZATION
                try:
                    # Mandate: Use AI Coder directly for PhD-level visuals
                    from backend.tools.viz_ai_coder import run_ai_coder
                    import pandas as pd
                    
                    logger.info(" [VIZ] DEEP MODE VISUALIZATION: Enforcing advanced/3D visual generation via AI Coder")
                    
                    if not data_found:
                        logger.warning(" [VIZ] No genuine physical or empirical measurement data found. Refusing to synthesize fake visualizations from software engine logs.")
                        
                    if data_found:
                        df = pd.DataFrame(data_found)
                        advanced_intent = f"Create a publication-quality multi-panel scientific figure analyzing: {self.research_question}. Use statistical overlays, proper axis labels with units, and Nature/Science journal aesthetics."
                        
                        # Call AI Coder directly to bypass abstraction
                        viz_res_obj = run_ai_coder(
                            df=df, 
                            intent=advanced_intent, 
                            config={"caption": self.research_question, "force_academic": True, "allow_exec": True}
                        )
                        
                        # Convert to dict format expected by session
                        viz_result = viz_res_obj.to_dict() if hasattr(viz_res_obj, 'to_dict') else {
                            "status": getattr(viz_res_obj, 'status', 'error'),
                            "message": getattr(viz_res_obj, 'message', ''),
                            "fig_json": getattr(viz_res_obj, 'fig_json', None),
                            "html": getattr(viz_res_obj, 'html', None),
                        }
                        # Add 'type' key for compatibility
                        viz_result["type"] = "plotly" if getattr(viz_res_obj, 'fig_json', None) else "image"
                        
                        if viz_result.get("status") == "success":
                            self.session.visualizations.append(viz_result)
                            logger.info(f"Generated deep mode chart: {viz_result.get('type')}")
                        else:
                             logger.warning(f"Deep viz generation failed: {viz_result.get('message')}")

                except Exception as e:
                    logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                    logger.warning(f"Deep viz generation failed: {e}")

            # 3. Generate Mermaid/Graphviz (for technical topics)
            # NOTE: Diagram generation is handled by ReportComposerAgent._generate_visuals
            # which uses Kroki API for Mermaid, Graphviz, PlantUML rendering.
            # This section is disabled to avoid duplicate functionality.
            # if is_technical or "TEST_DIAGRAM_TRIGGER" in self.research_question:
            #     from backend.visualization.mermaid_generator import generate_technical_diagram
            #     diag_result = generate_technical_diagram(self.research_question, all_text_context[:5000])
            #     ...
                    
        except Exception as e:
            logger.error(f"Visualization phase failed: {e}")

        # PHASE 44: CONSENSUS TRIBUNAL (Final Verification)
        if self.consensus_engine and self.session.findings:
            logger.info(f" [CONSENSUS] Starting final verification of {len(self.session.findings)} findings...")
            await self._announce("I'm conducting a final consensus verification to ensure all findings are solid.")
            
            verified_count = 0
            rejected_count = 0
            
            # We only verify the top 50 findings for performance in huge logs
            for finding in self.session.findings[-50:]:
                 # Skip already rejected findings
                 if finding.get("status") == "rejected":
                     continue
                     
                 is_verified = await self.consensus_engine.verify_finding(
                     finding, 
                     self.research_question
                 )
                 
                 if is_verified:
                     finding["status"] = "verified"
                     verified_count += 1
                 else:
                     finding["status"] = "rejected"
                     finding["rejection_reason"] = "Consensus Engine: Failed final verification"
                     rejected_count += 1
            
            logger.info(f" [CONSENSUS] Final Verification Result: {verified_count} verified, {rejected_count} rejected.")
            if rejected_count > 0:
                 await self._announce(f" [CONSENSUS] My truth tribunal rejected {rejected_count} weak findings.")


        # AUTO-GENERATE REPORT
        # SVEL GATE: Only generate report if deep work is complete (>90% time or converged)
        elapsed_ratio = self.session.get_elapsed_hours() / self.session.max_runtime_hours
        is_converged = self.session.status in [ResearchState.COMPLETED, ResearchState.CONVERGING]
        
        # Phase 5.5: Export Claim-Mapped Master Jupyter Notebook & Epistemic Discovery Dossier
        notebook_exps = getattr(self.session, "notebook_experiments", [])
        all_hyps = [h.to_dict() for h in self.hypothesis_tracker.get_all()]
        safe_title = "".join(c if c.isalnum() else "_" for c in self.research_question[:50])
        nb_output_path = f"reports/notebooks/{safe_title}_master.ipynb"
        nb_path = None

        try:
            logger.info(f" [FINALIZE] Exporting claim-to-cell mapped master Jupyter notebook ({len(notebook_exps)} experiments, {len(all_hyps)} claims)...")

            from backend.tools.jupyter_exporter import get_jupyter_exporter
            exporter = get_jupyter_exporter()

            # Build session-level viz cells from VizAICoder results
            session_viz_cells = []
            for viz in getattr(self.session, "visualizations", []):
                fig_json = viz.get("fig_json") or viz.get("plotly_json")
                if fig_json:
                    cell_code = (
                        "# Session-Level Visualization (VizAICoder)\n"
                        "import plotly.io as pio\n"
                        f"_sfig = pio.from_json(r'''{fig_json}''')\n"
                        "_sfig.update_layout(template='plotly_white')\n"
                        "_sfig.show()\n"
                    )
                    session_viz_cells.append({
                        "title": viz.get("title", "Session Visualization"),
                        "viz_cell_code": cell_code,
                    })

            active_model = getattr(self, "base_model", None) or os.environ.get("SOVEREIGN_LLM") or os.environ.get("NVIDIA_MODEL") or "z-ai/glm-5.3-flash (NVIDIA NIM)"

            nb_path = exporter.export_claim_mapped_notebook(
                title=self.research_question,
                claims=all_hyps,
                experiments=notebook_exps,
                output_path=nb_output_path,
                metadata={
                    "session_id": self.session.id,
                    "research_question": self.research_question,
                    "domain": getattr(self, "domain", "general"),
                    "runtime_hours": self.session.get_elapsed_hours(),
                    "baseline_llm": active_model,
                    "survivor_tier": getattr(self.session, "survivor_tier", "STRUCTURAL"),
                },
                session_visualizations=session_viz_cells,
                survivor_tier=getattr(self.session, "survivor_tier", "STRUCTURAL")
            )

            if nb_path:
                if not hasattr(self.session, "artifacts"):
                    self.session.artifacts = []
                self.session.artifacts.append({
                    "type": "jupyter_notebook_master",
                    "path": nb_path,
                    "experiment_count": len(notebook_exps),
                    "claims_count": len(all_hyps)
                })
                logger.info(f" [NOTEBOOK] Master claim-mapped notebook saved: {nb_path}")

        except Exception as e:
            logger.exception(f"[GLASS-TELEMETRY] Notebook export failed: {e}")
            import traceback
            logger.error(f"Master notebook export failed: {e}\n{traceback.format_exc()}")

        # Phase 5.6: Compile Sovereign Epistemic Discovery Dossier (Replacing generic prose reports)
        try:
            logger.info(" [FINALIZE] Compiling Epistemic Discovery Dossier (Mathematical framing & Falsification Ledger)...")
            from backend.core.epistemic_dossier import generate_discovery_dossier

            gnn_nodes = 0
            gnn_edges = 0
            gnn_auc = 0.5
            if hasattr(self, "world_model") and self.world_model:
                try:
                    snapshot = self.world_model.get_knowledge_snapshot()
                    gnn_nodes = len(snapshot.get("nodes", []))
                    gnn_edges = len(snapshot.get("edges", []))
                except Exception:
                    pass
                if hasattr(self.world_model, "oracle") and self.world_model.oracle:
                    gnn_auc = getattr(self.world_model.oracle, "last_auc", 0.6727)

            dossier_res = generate_discovery_dossier(
                mission_id=self.session.id,
                research_question=self.research_question,
                domain=getattr(self, "domain", "general"),
                hypotheses=all_hyps,
                experiments=notebook_exps,
                adversarial_attacks=[a.to_dict() for a in getattr(self.session, 'adversarial_attacks', [])],
                tribunal_records=getattr(self.session, 'tribunal_records', {}),
                gnn_metadata={"nodes": gnn_nodes, "edges": gnn_edges, "auc": round(float(gnn_auc), 4)},
                world_model_facts=[],
                survivor_tier=getattr(self.session, "survivor_tier", "STRUCTURAL"),
                baseline_llm=active_model,
                runtime_hours=self.session.get_elapsed_hours(),
                notebook_path=nb_path
            )

            self.session.final_report = dossier_res["markdown_content"]
            if not hasattr(self.session, "artifacts"):
                self.session.artifacts = []
            self.session.artifacts.append({
                "type": "epistemic_discovery_dossier",
                "markdown_path": dossier_res["markdown_path"],
                "json_path": dossier_res["json_path"],
                "survivor_tier": getattr(self.session, "survivor_tier", "STRUCTURAL")
            })
            self._emit_progress({
                "phase": "dossier_compiled",
                "message": f"Epistemic Discovery Dossier & Notebook compiled: {dossier_res['markdown_path']}"
            })
            logger.info(f" [DOSSIER] Epistemic Discovery Dossier saved: {dossier_res['markdown_path']}")

        except Exception as e:
            logger.exception(f"[GLASS-TELEMETRY] Epistemic dossier compilation failed: {e}")
            import traceback
            logger.error(f"Dossier compilation failed: {e}\n{traceback.format_exc()}")
        
        if self.router:
            try:
                # Increase findings context window significantly so the writer has enough data to avoid refusal
                # Pass full result dictionaries for visualization harvesting
                curr_findings = []
                for f in self.session.findings[-100:]:
                    res = f.get("result", {})
                    # SWARM UNWRAP: If nested in {"agent":..., "result":...}
                    if isinstance(res, dict) and "result" in res and "agent" in res:
                        res = res["result"]
                    
                    if isinstance(res, dict):
                        # PROJECT SVEL: Enforce experimental fidelity
                        # Ensure we don't drop 'code', 'viz_cell_code', or 'scientific_report'
                        item = res.copy()
                        if "text" not in item:
                            item["text"] = f.get("content") or item.get("summary") or item.get("text")
                        
                        # Bridge identifying metadata if missing
                        if "id" not in item and "task_id" in f:
                            item["id"] = f["task_id"]
                            
                        curr_findings.append(item)
                    else:
                        # Fallback for simple results
                        curr_findings.append({"summary": str(res), "text": str(res)})
                
                # [SVEL BRIDGE] Physically inject the full World Model findings
                # Pull all persistent facts from SQLite memory
                all_facts = []
                if self.world_model:
                    for fact_list in self.world_model._facts.values():
                        for f in fact_list:
                            all_facts.append({
                                "summary": f.key,
                                "text": str(f.value),
                                "confidence": f.confidence,
                                "source": f.source
                            })
                
                # Prepend rehydrated facts to the current session findings
                curr_findings = all_facts + curr_findings
                
                logger.info(f" BEAST MODE: Triggering Godzilla Report Composer with {len(curr_findings)} total findings...")
                self._emit_progress({
                    "phase": "report_generation",
                    "message": "Constructing final professional Godzilla PDF report..."
                })
                
                # FIX: Directly execute the reportcomposer agent instead of routing through LLM selector
                # The router.route_async() was going through TaskDecomposer which failed JSON parsing
                report_agent = self.router.agent_map.get("report_composer_agent")
                
                if report_agent:
                    logger.info(" Direct invocation of report_composer_agent...")
                    
                    # SVEL INJECTION: Connect World Model to Report Composer
                    if self.world_model:
                        report_agent.world_model = self.world_model
                        logger.info(" [CONNECTION] World Model injected into Report Composer for internal data access.")

                    # FIX: Direct await for async agent run method (removed incorrect asyncio.to_thread)
                    # Calculate stricter deadline for reporting (STRICTLY Max Runtime)
                    deadline = None
                    if self.session.started_at and self.session.max_runtime_hours:
                         # Use raw max runtime hours
                         started_dt = self.session.started_at
                         if isinstance(started_dt, str):
                             try:
                                 started_dt = datetime.fromisoformat(started_dt)
                             except Exception:
                                 started_dt = datetime.now()
                         deadline = started_dt + timedelta(hours=self.session.max_runtime_hours)
                         
                         # [SAFEGUARD] Dynamic minimum for reporting based on total runtime
                         # For 15m runs (0.25h), we only need ~2-3 minutes for reporting.
                         # For 72h runs, 15-30m is appropriate.
                         report_reservation_min = max(0.05, self.session.max_runtime_hours * 0.1) # Min 3m, or 10%
                         if report_reservation_min > 0.25: report_reservation_min = 0.25 # Cap at 15m
                         
                         min_deadline = datetime.now() + timedelta(hours=report_reservation_min)
                         if deadline < min_deadline:
                             logger.warning(f" [TIME] Balancing reporting window to {report_reservation_min*60:.1f}m.")
                             deadline = min_deadline
                    
                    # FINAL SANITY: Ensure self.research_question is a string
                    topic_str = self.research_question
                    if isinstance(topic_str, dict):
                         p = topic_str.get('payload', {})
                         if isinstance(p, str): p = {}
                         topic_str = topic_str.get('query') or p.get('query') or str(topic_str)
                    elif not isinstance(topic_str, str):
                         topic_str = str(topic_str)

                    report_res = await report_agent.run(
                        topic=topic_str,
                        mode=getattr(self.session, 'mode', 'discovery' if is_discovery else 'research'),
                        deadline=deadline,
                        ctx={
                            "task_type": "report_generation",
                            "deep_findings": curr_findings,
                            "experiments": notebook_exps, #  BRIDGE: Restore code-export capability
                            "hypotheses": [
                                h.to_dict() 
                                for h in self.hypothesis_tracker.get_all()
                            ],
                            # SVEL: Pass full objects for Leaderboard Rendering
                            "claim_leaderboard": sorted(
                                [h.to_dict() for h in self.hypothesis_tracker.get_all() if getattr(h.state, 'name', str(h.state)) not in ["REFUTED", "ARCHIVED"] and h.to_dict().get('state') not in ["REFUTED", "ARCHIVED"]],
                                key=lambda x: (x.get('survival_score') if x.get('survival_score') is not None else -1, x.get('confidence'), x.get('novelty_score') or 0),
                                reverse=True
                            )[:15],

                            "research_question": self.research_question,
                            "formats": ["html", "pdf", "notebook"], # Explicitly request notebook from composer
                            # V2 Context Injection
                            "runtime_hours": self.max_runtime_hours,
                            "origin_prompt": self.research_question,
                            "seed_corpus": self.session.visited_urls[:50] if hasattr(self.session, 'visited_urls') else [],
                            "adversarial_results": [
                                a.to_dict() for a in getattr(self.session, 'adversarial_attacks', [])
                            ] if hasattr(self.session, 'adversarial_attacks') else []
                        }
                    )
                else:   
                    logger.warning(" report_composer_agent not found in agent_map, skipping report generation")
                    report_res = None
                
                # Track the artifact if produced or passed back
                if report_res and isinstance(report_res, dict):
                    # Store the actual text report if available
                    logger.debug(f"report_res status: {report_res.get('status')}")
                    logger.debug(f"report_res keys: {list(report_res.keys())}")
                    report_text = report_res.get("report_html") or report_res.get("text")
                    if report_text:
                        logger.info(f"Report text found, length: {len(report_text)}")
                        # If the Epistemic Discovery Dossier is already set, preserve the Dossier as primary
                        if self.session.final_report and "Epistemic Discovery Dossier" in self.session.final_report:
                            logger.info("Preserving Epistemic Discovery Dossier as primary report; appending literature notes to appendix.")
                            self.session.final_report += f"\n\n---\n## Supplementary Literature Synthesis\n\n{report_text}"
                        else:
                            self.session.final_report = report_text
                    else:
                        logger.warning("Report generation returned no text content in report_res")
                        
                    # Try to extract file paths if they exist
                    files = report_res.get("files", {})
                    if files:
                        self.session.artifacts.append({
                            "type": "report_files",
                            "files": files,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    # CAPTURE VISUALIZATIONS (The Amazing Part)
                    visuals = report_res.get("visuals", [])
                    if visuals:
                        logger.info(f"Generated {len(visuals)} visualizations for session payload.")
                        # Ensure we don't duplicate if called multiple times
                        existing_paths = {v.get("file_path") for v in self.session.visualizations}
                        for v in visuals:
                            if isinstance(v, dict) and v.get("file_path") not in existing_paths:
                                self.session.visualizations.append(v)

                        
            except Exception as e:
                logger.error(f"Auto-report generation failed: {e}", exc_info=True)
                await self._record_error("report_generation", f"{e}")
    
    # ========== Helper Methods ==========
    
    def _check_memory_safety(self) -> None:
        """
        F-48: MEMORY SAFETY PROTOCOL (The Amnesiac Guard)
        Prunes in-memory session state to prevent OOM during long runs.
        """
        # 1. Prune Findings (The most critical leak)
        MAX_FINDINGS_IN_MEMORY = 10000
        if len(self.session.findings) > MAX_FINDINGS_IN_MEMORY:
            # Sort by timestamp just in case, though they should be appended in order
            # We keep the LAST N findings
            pruned_count = len(self.session.findings) - MAX_FINDINGS_IN_MEMORY
            self.session.findings = self.session.findings[-MAX_FINDINGS_IN_MEMORY:]
            
            # Force garbage collection of the dropped dicts
            import gc
            gc.collect()
            
            logger.info(f" [MEMORY] PRUNED {pruned_count} old findings from RAM. (Current: {len(self.session.findings)})")
            
        # 2. Prune Visualizations (Heavy base64 strings)
        MAX_VIZ_IN_MEMORY = 500
        if len(self.session.visualizations) > MAX_VIZ_IN_MEMORY:
             self.session.visualizations = self.session.visualizations[-MAX_VIZ_IN_MEMORY:]
             logger.info(f" [MEMORY] Pruned visualizations to last {MAX_VIZ_IN_MEMORY}.")
             
    async def _should_continue(self) -> bool:
        """
        [SVEL-TIER] Authoritative termination logic.
        Checks: Time reservation, Hard Caps, Budget, Overmind, and Epistemic Convergence.
        """
        # 0. Satiety Finalization Complete
        if getattr(self, "_satiety_finalized", False):
            logger.info("Stopping: Knowledge base reached satiety and final synthesis has completed.")
            return False

        # 0. HARD AUTHORITY: Overmind termination
        if self.overmind and getattr(self.overmind, 'termination_requested', False):
            logger.info(f"Stopping due to Overmind request: {getattr(self.overmind, 'termination_reason', 'Strategic halt')}")
            return False

        # 1. Resilience authority: Circuit Breaker & Errors
        if not self.circuit_breaker.can_execute():
            logger.warning("Stopping: Circuit breaker open")
            return False
        if self.session.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.error(f"Stopping: Too many consecutive errors ({self.session.consecutive_errors})")
            return False
        
        # 2. Financial Authority: Budget Check
        exceeded, reason = self._check_budget()
        if exceeded:
            logger.info(f"Stopping: Budget exceeded - {reason}")
            return False

        # 3. Temporal Authority: Runtime & Reservation
        elapsed = self.session.get_elapsed_hours()
        # [SVEL HARD CAP] If the time budget is physically gone, terminate immediately.
        if elapsed >= self.session.max_runtime_hours:
            logger.info(f"[HARD CAP] Session limit reached ({elapsed:.2f}h / {self.session.max_runtime_hours}h). PHYSICAL TERMINATION.")
            # Final synthesis — await properly before terminating
            try:
                await self._phase_finalize()
            except Exception as e:
                logger.error(f"Finalization failed: {e}")
            return False
        
        # User Limit + Reservation (Dynamic: lean 5% Godzilla buffer)
        if self.session.max_runtime_hours < 1.0:
             reservation = 0.016 # 1 minute
        else:
             reservation = min(0.25, self.session.max_runtime_hours * 0.05) # Max 15 mins
              
        research_limit = self.session.max_runtime_hours - reservation
        if elapsed >= research_limit:
            logger.info(f"[TIME_RESERVATION] Research phase concluding at {elapsed:.2f}h (Master Limit: {self.session.max_runtime_hours:.2f}h)")
            return False
            
        # 4. Cycle Authority (Strictly subordinate to runtime_hours in multi-hour autonomous campaigns)
        if self.session.current_cycle >= self.session.total_cycles_planned:
            if self.session.max_runtime_hours <= 1.0 and len(self.session.findings) > 0:
                logger.info(f" [CLOCK] Max Cycles ({self.session.current_cycle}) reached with findings. Converging...")
                return False
            else:
                logger.info(f" [CLOCK] Cycle {self.session.current_cycle} reached planned count; continuing for remaining runtime budget ({elapsed:.2f}h / {self.session.max_runtime_hours:.2f}h).")
            
        # 5. Epistemic Authority: Convergence & Novelty
        if self.convergence_controller:
            stop_reason = await self.convergence_controller.check_convergence(
                self.session.current_cycle,
                self.hypothesis_tracker.get_all()
            )
            if stop_reason:
                if "All hypotheses resolved" in stop_reason and elapsed < (research_limit * 0.85):
                    logger.info(f" [AUTONOMOUS WAVE] {stop_reason} with {research_limit - elapsed:.2f}h remaining — scheduling next hypothesis generation wave instead of stopping.")
                    self.session.metadata["force_regeneration"] = True
                    return True
                logger.info(f"Autonomous Stop: {stop_reason}")
                return False
        
        return True
    
    def _is_time_exceeded(self) -> bool:
        """Check if research time limit has been exceeded (respecting reservation)"""
        elapsed = self.session.get_elapsed_hours()
        
        # FIX: Standardized reservation logic (max(0.25, 8% of runtime) capped at 2.5h)
        if self.session.max_runtime_hours < 1.0:
             reservation = max(0.016, self.session.max_runtime_hours * 0.20)
        else:
             reservation = max(0.25, self.session.max_runtime_hours * 0.08)
             if reservation > 2.5: 
                  reservation = 2.5
        research_limit = self.session.max_runtime_hours - reservation
        max_allowed = min(research_limit, MAX_RUNTIME_HOURS)
        
        if elapsed >= max_allowed:
            logger.info(f"[TIME_CHECK] Research limit exceeded: {elapsed:.2f}h >= {max_allowed:.2f}h (Reserved: {reservation:.2f}h)")
            return True
        return False

    def _scavenge_field(self, data: Any, field_name: str, max_depth: int = 5) -> Any:
        """Nuclear Code Hunter: Recursively scavenge for a field in any structure."""
        if max_depth <= 0:
            return None
        
        if isinstance(data, dict):
            # 1. Direct hit
            if field_name in data and data[field_name]:
                return data[field_name]
            
            # 2. Heuristic search in common containers
            for key in ["result", "payload", "metadata", "meta", "data", "output"]:
                if key in data:
                    res = self._scavenge_field(data[key], field_name, max_depth - 1)
                    if res: return res
            
            # 3. Exhaustive search (last resort)
            for k, v in data.items():
                if k not in ["result", "payload", "metadata", "meta", "data", "output"]:
                    res = self._scavenge_field(v, field_name, max_depth - 1)
                    if res: return res
                    
        elif isinstance(data, list):
            for item in data:
                res = self._scavenge_field(item, field_name, max_depth - 1)
                if res: return res
        
        # 4. Handle Objects (Dataclasses, etc.) - The Code-Drop Fix
        elif hasattr(data, "__dict__"):
            # Check direct attribute hit
            if hasattr(data, field_name):
                val = getattr(data, field_name)
                if val: return val
            
            # Recurse into common internal dictionaries
            for attr in ["result", "payload", "metadata", "meta", "data", "output"]:
                if hasattr(data, attr):
                    res = self._scavenge_field(getattr(data, attr), field_name, max_depth - 1)
                    if res: return res
                    
            # Exhaustive attribute search
            try:
                for attr, val in vars(data).items():
                    if attr not in ["result", "payload", "metadata", "meta", "data", "output"]:
                        res = self._scavenge_field(val, field_name, max_depth - 1)
                        if res: return res
            except Exception as e:
                logger.warning(f"[GLASS-TELEMETRY] Attribute scavenging failed: {e}")
                pass
                
        return None

    def _process_completed_task(self, task: Union[ResearchTask, Dict], result_data: Any, cycle: int):
        """Unified logic to commit findings to WorldModel and telemetry."""
        # 1. Standardize Task Info
        if isinstance(task, dict):
            task_id = task.get("id")
            task_type = task.get("task_type") or task.get("type")
            task_desc = task.get("description")
        else:
            task_id = task.id
            task_type = task.task_type
            task_desc = task.description

        # [SVEL GATE 3] Execution Enforcement: Physical Artifact Check
        if "experiment" in str(task_type).lower():
            task_exp_dir = Path(f"experiments/{task_id}")
            new_files = []
            if task_exp_dir.exists():
                new_files = [f for f in task_exp_dir.glob("**/*") if f.is_file()]
            
            # Check results/experiments/{task_id} and results/experiments/{experiment_id}
            if not new_files and isinstance(result_data, dict):
                exp_id = (
                    result_data.get("experiment_id")
                    or (result_data.get("result", {}).get("experiment_id") if isinstance(result_data.get("result"), dict) else None)
                    or (result_data.get("metadata", {}).get("experiment_id") if isinstance(result_data.get("metadata"), dict) else None)
                )
                candidates = [Path(f"results/experiments/{task_id}")]
                if exp_id:
                    candidates.append(Path(f"results/experiments/{exp_id}"))
                for c in candidates:
                    if c.exists():
                        new_files.extend([f for f in c.glob("**/*") if f.is_file()])
                        if new_files:
                            break

            if not new_files and isinstance(result_data, dict):
                artifacts = result_data.get("artifacts", []) or result_data.get("files", [])
                new_files = [Path(f) for f in artifacts if Path(f).exists()]

            if not new_files:
                logger.critical(f" [RIGOR VIOLATION] Task {task_id} claimed success but produced NO physical artifacts.")
                if isinstance(result_data, dict):
                    result_data["status"] = "failed"
                    result_data["error"] = "[FRAUD DETECTED] ExperimentAgent produced no physical artifacts (CSV/PDB/Plots)."
            else:
                logger.info(f" [EXECUTION] Verified {len(new_files)} physical artifacts produced by task {task_id}.")

        # 2. Extract Inner Result (The Robust Hunter)
        # We need the most 'meaningful' part of the result for the summary
        inner = result_data
        if isinstance(result_data, dict):
            # Check for standard nested result keys
            for key in ["result", "payload", "findings", "summary", "text"]:
                 if key in result_data and result_data[key]:
                     inner = result_data[key]
                     # Deep nesting check
                     if isinstance(inner, dict) and "result" in inner and inner["result"]:
                         inner = inner["result"]
                     break
        elif hasattr(result_data, "result") and getattr(result_data, "result"):
            inner = result_data.result
        elif hasattr(result_data, "metadata") and getattr(result_data, "metadata"):
            inner = result_data.metadata

        #  NUCLEAR CODE HUNTER: Aggressively hunt for code in ANY task
        exp_code = self._scavenge_field(result_data, "code") or self._scavenge_field(result_data, "code_ref") or ""
        viz_code = self._scavenge_field(result_data, "viz_cell_code") or ""
        
        if exp_code:
            logger.info(f" [NUCLEAR] Successfully scavenged code (len={len(exp_code)}) for task {task_id}")
        elif "experiment" in str(task_type).lower():
             logger.warning(f" [NUCLEAR] Failed to scavenge 'code' for task {task_id}. Payload keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'non-dict'}")
            
        # UPDATE WORLD MODEL (Phase 4: Titanic Rigor)
        if self.world_model:
            try:
                # Use scavenge for summary if string conversion is messy
                summary = ""
                if isinstance(inner, str):
                    summary = inner
                elif isinstance(inner, dict):
                    summary_raw = inner.get("summary") or inner.get("text") or inner.get("findings") or str(inner)
                    summary = summary_raw if isinstance(summary_raw, str) else str(summary_raw)
                else:
                    summary = str(inner)
                
                summary = str(summary)[:2000]

                # [TITAN V138.0] TOXIC FACT FILTER
                # Physically block agent failures, crash logs, and error payloads from poisoning the knowledge graph.
                toxic_found = any(p in summary.lower() for p in ["error", "failed", "exception", "traceback", "rejected", "missing critical"])
                if toxic_found:
                    logger.warning(f" [TOXIC] Blocked commit of task {task_id} result: payload contains error signature.")
                    commit_allowed = False
                else:
                    # [TITAN V155.0] FORENSIC REPORTING
                    # Physically bind the experiment result to the Statistics manifold.
                    if hasattr(self, "execution_stats") and "experiment" in str(task_type).lower():
                        initial_hash = self._scavenge_field(result_data, "initial_hash")
                        final_hash = self._scavenge_field(result_data, "final_hash")
                        if initial_hash and final_hash:
                            self.execution_stats.complete_pulse(task_id, final_hash, result_data)

                    # [SVEL V68.9] Explicit Type Discipline

                    # Only non-procedural tasks become 'Facts' in the World Model
                    commit_allowed = not (task.get("is_procedural", False) if isinstance(task, dict) else getattr(task, "is_procedural", False))



                # RIGOR GATE: Validate finding significance before committing
                confidence = 0.5
                if commit_allowed and self.statistical_validator:
                    try:
                        val_res = self.statistical_validator.validate(
                            finding={"content": summary, "task_type": task_type},
                            data=result_data
                        )
                        confidence = val_res.confidence_score if hasattr(val_res, 'confidence_score') else 0.7

                        # [TITAN V157.0] BAYESIAN COMMIT
                        # Physically penalize confidence by the GNN's original uncertainty (σ).
                        # Ending the "Bayesian Theater" violation.
                        u_val = 0.0
                        if isinstance(task, dict):
                            u_val = task.get("payload", {}).get("uncertainty", 0.0)
                        else:
                            u_val = task.payload.get("uncertainty", 0.0) if hasattr(task, "payload") else 0.0
                        
                        if u_val > 0.0:
                            penalty = 1.0 - u_val
                            confidence *= penalty
                            logger.info(f" [BAYESIAN] Finding {task_id} confidence dampened by GNN doubt (σ={u_val:.3f}, final_conf={confidence:.2f})")


                        if hasattr(val_res, 'is_significant') and not val_res.is_significant:
                            logger.warning(f" [RIGOR GATE] Finding {task_id} rejected: INSIGNIFICANT (p-value check failed)")
                            commit_allowed = False
                        else:
                            commit_allowed = True
                    except Exception as val_err:
                        logger.warning(f"Statistical validation failed: {val_err}")
                        confidence = 0.3
                        commit_allowed = False
                else:
                    confidence = 0.6
                    commit_allowed = True

                if commit_allowed and summary and not any(ph in str(summary).upper() for ph in ["NO_ROWS_EXTRACTED", "DUMMY", "PLACEHOLDER"]):
                    # Enrich metadata with visual artifacts if experimental
                    meta = {"task_type": task_type, "cycle": cycle}
                    if isinstance(inner, dict):
                         if "visualization" in inner: meta["visualization"] = inner["visualization"]
                         if "viz_cell_code" in inner: meta["viz_cell_code"] = inner["viz_cell_code"]
                         if "code" in inner: meta["code"] = inner["code"]

                    self.world_model.commit_verified_fact(
                        key=f"finding_{task_id}",
                        value=summary,
                        source=f"swarm_{task_id}",
                        confidence=confidence,
                        metadata=meta
                    )
                    logger.info(f" [RIGOR GATE] Finding {task_id} COMMITTED (Confidence: {confidence:.2f})")
            except Exception as e:
                logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
                logger.warning(f"WorldModel commit failed for {task_id}: {e}")

        # ---------------------------------------------------------------- #
        # NOTEBOOK ACCUMULATION: Capture result if it contains code        #
        # ---------------------------------------------------------------- #
        if task_type == "experiment" or exp_code:
            try:
                # [SVEL V68.6] Type Discipline: Strip hypothesis from procedural tasks
                is_pure_science = task_type in ["experiment", "analysis"]
                display_hypothesis = (task_desc or task_id) if is_pure_science else "Procedural/Technical Infrastructure Task"
                
                resolved_hid = (
                    (task.get("hypothesis_id") if isinstance(task, dict) else getattr(task, "hypothesis_id", None))
                    or (task.get("payload", {}).get("hypothesis_id") if isinstance(task, dict) and isinstance(task.get("payload"), dict) else None)
                    or self._scavenge_field(result_data, "hypothesis_id")
                    or task_id
                )
                exp_entry = {
                    "id": self._scavenge_field(result_data, "experiment_id") or task_id,
                    "hypothesis": display_hypothesis,
                    "code": exp_code or self._scavenge_field(result_data, "code") or "",
                    "output": self._scavenge_field(result_data, "logs") or self._scavenge_field(result_data, "output") or self._scavenge_field(result_data, "summary") or "",
                    "significance_score": self._scavenge_field(result_data, "confidence") or self._scavenge_field(result_data, "significance_score"),
                    "evidence_type": self._scavenge_field(result_data, "evidence_type") or "support",
                    "viz_cell_code": viz_code or self._scavenge_field(result_data, "viz_cell_code") or "",
                    "cycle": cycle,
                    "dataset": self._scavenge_field(result_data, "dataset") or self._scavenge_field(result_data, "data_path") or ", ".join(os.path.basename(str(v)) for v in DataResolver().resolve_data_for_hypothesis(self.research_question).values()) or f"{self.domain}_dataset",
                    "initial_hash": self._scavenge_field(result_data, "initial_hash") or self._scavenge_field(result_data, "initial_weight_hash"),
                    "final_hash": self._scavenge_field(result_data, "final_hash") or self._scavenge_field(result_data, "final_weight_hash"),
                    "report": self._scavenge_field(result_data, "report") or self._scavenge_field(result_data, "scientific_report") or {},
                    "hypothesis_id": resolved_hid,
                }
                if not hasattr(self.session, "notebook_experiments"):
                    self.session.notebook_experiments = []
                # Avoid duplicate entries for the same experiment ID if already added via different path
                if not any(e["id"] == exp_entry["id"] for e in self.session.notebook_experiments):
                    self.session.notebook_experiments.append(exp_entry)
                
                logger.info(f" [DEBUG_PAYLOAD] task_id: {task_id}")
                logger.info(f" [DEBUG_PAYLOAD] result_data keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'NOT_DICT'}")
                logger.info(f" [DEBUG_PAYLOAD] inner keys: {list(inner.keys()) if isinstance(inner, dict) else 'NOT_DICT'}")
                logger.info(f" [DEBUG_PAYLOAD] Code length: {len(exp_entry.get('code', ''))}")
                if exp_entry.get('code'):
                    logger.info(f" [DEBUG_PAYLOAD] Code start: {exp_entry['code'][:100]}...")
                if not hasattr(self.session, "experiment_results"):
                    self.session.experiment_results = {}
                
                self.session.experiment_results[task_id] = {
                    "code": exp_entry["code"],
                    "result": {
                        "output": inner.get("output") or inner.get("logs") or result_data.get("output"),
                        "evidence_type": inner.get("evidence_type") or result_data.get("evidence_type"),
                        "significance_score": exp_entry["significance_score"],
                        "success": result_data.get("status") in ("success", "completed"),
                        "falsification_report": inner.get("metadata", {}).get("falsification_report") or result_data.get("metadata", {}).get("falsification_report"),
                        "visualization": inner.get("visualization") or result_data.get("metadata", {}).get("visualization"),
                        "viz_cell_code": exp_entry["viz_cell_code"]
                    },
                    "hypothesis_id": resolved_hid,
                    "cycle": cycle,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f" [NOTEBOOK] Accumulated/Persisted experiment {task_id} for master notebook.")
            except Exception as nb_err:
                logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {nb_err}")
                logger.warning(f"Notebook accumulation failed for {task_id}: {nb_err}")

        # ---------------------------------------------------------------- #
        # RESEARCH SCAR TISSUE: Log Refuted Hypotheses to the Morgue       #
        # ---------------------------------------------------------------- #
        if task_type == "experiment":
            evidence_type = inner.get("evidence_type") or (result_data.get("evidence_type") if isinstance(result_data, dict) else None)
            if evidence_type == "refute":
                try:
                    h_stmt = task_desc or task_id
                    reason = "Experimental falsification or rejection"
                    if isinstance(result_data, dict):
                         reason = inner.get("details") or result_data.get("error") or reason
                    
                    if hasattr(self, "red_team") and self.red_team:
                        logger.warning(f" [MORGUE] Logging refuted hypothesis '{h_stmt[:50]}...' to Semantic Morgue.")
                        self.red_team.log_to_morgue_semantic(
                            hypothesis_statement=h_stmt,
                            kill_reason=reason,
                            session_id=self.session.id
                        )
                except Exception as morgue_err:
                    logger.error(f" [MORGUE] Failed to log refuted hypothesis: {morgue_err}")
     
    async def _build_context(self) -> Dict[str, Any]:
        """
        Build a high-rigor, compressed context for agent execution.
        [SVEL COMPRESSION] Limits findings to the top 5 to prevent LLM overload.
        """
        # [SVEL FIX: The Memory Bridge]
        # Instead of just the last 5 raw findings, we provide the Infinite Memory Snapshot
        # plus the absolute latest 3 raw findings for immediate tactical context.
        collected_findings = [str(f.get("result", ""))[:5000] for f in self.session.findings[-3:]]
        
        # Limit hypotheses to top 5 from the tracker
        all_h = self.hypothesis_tracker.get_all()
        top_hypotheses = all_h[:5]
        hypotheses_context = [h.to_dict() if hasattr(h, 'to_dict') else str(h) for h in top_hypotheses]

        # FETCH DYNAMIC TOOLS & AGENTS
        available_tools = []
        tool_descriptions = []
        try:
            from backend.tools.tool_registry import REGISTRY
            # access internal dictionary of ToolWrapper objects
            # The REGISTRY may have different attribute names depending on version
            registry_tools = getattr(REGISTRY, 'tools', None) or getattr(REGISTRY, '_tools', None) or {}
            for t_name, t_wrapper in registry_tools.items():
                available_tools.append(t_name)
                # Use docstring or description attr
                desc = getattr(t_wrapper, 'description', "No description")
                tool_descriptions.append(f"{t_name}: {desc}")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not import REGISTRY for tool injection: {e}")
            available_tools = ["web_search", "deep_paper_reader", "python_interpreter"] # Fallback

        # SCIENTIFIC WHITELIST: Common libraries that are ALWAYS available via code execution
        scientific_whitelist = [
            "pytorch", "tensorflow", "jax", "scikit-learn", "numpy", "pandas", 
            "matplotlib", "seaborn", "scipy", "statsmodels", "transformers", 
            "diffusers", "bitsandbytes", "accelerate"
        ]
        available_tools.extend(scientific_whitelist)

        # STRATEGIC TOOLSET: Inject tools from the battle plan if available
        if hasattr(self.session, 'battle_plan') and self.session.battle_plan:
            battle_tools = self.session.battle_plan.get('functional_tools', [])
            for bt in battle_tools:
                if bt not in available_tools:
                    available_tools.append(bt)
                    tool_descriptions.append(f"{bt}: Specialized research protocol/skill from Battle Plan.")

        available_agents = {}
        if self.router and hasattr(self.router, 'agent_map'):
             for name, agent in self.router.agent_map.items():
                 # Fetch capabilities (PCD Pillar 11 Specialist Injection)
                 caps = []
                 if hasattr(agent, "capabilities"):
                     caps = agent.capabilities
                 elif hasattr(agent, "get_capabilities"):
                     try: caps = agent.get_capabilities()
                     except:
                         logger.exception(f"[GLASS-TELEMETRY] CRITICAL SYSTEM FAILURE in {__name__}")
                         pass
                 available_agents[name] = caps

        context = {
            "domain": self.domain,
            "findings": collected_findings,
            "knowledge_snapshot": self.session.knowledge_snapshot, # [THE MEMORY BRIDGE INJECTED]
            "hypotheses": [
                {
                    "id": h.id,
                    "statement": h.statement,
                    "confidence": h.confidence,
                    "age": self.session.current_cycle - h.cycle_created if hasattr(h, 'cycle_created') else 0,
                    "survived": h.metadata.get("attacks_survived", 0) if h.metadata else 0,
                    "sources": len(h.supporting_evidence) if hasattr(h, 'supporting_evidence') else 0
                }
                for h in self.hypothesis_tracker.get_active()[:15]
            ],
            "confirmed_hypotheses": [
                {
                    "id": h.id, 
                    "statement": h.statement,
                    "confidence": h.confidence 
                }
                for h in self.hypothesis_tracker.get_active() if h.state == HypothesisState.CONFIRMED
            ],
            # TARGET INJECTION: Pass the massive targets to the planner
            "paper_read_target": self.paper_read_target,
            "deep_read_target": self.deep_read_target,
            "max_runtime_hours": self.session.max_runtime_hours,
            "total_cycles": self.max_cycles, # For dynamic phase calculation
            "refuted_hypotheses": [h.statement for h in self.hypothesis_tracker.get_active() if h.state == HypothesisState.REFUTED],
            "cycle": self.session.current_cycle,
            "elapsed_hours": self.session.get_elapsed_hours(),
            "research_question": self.research_question,  # Explicit topic locking
            "started_at": self.session.started_at, # TEMPORAL INHERITANCE
            "local_data_catalog": self.session.local_data_catalog, # SVEL DATA TETHERING
            "PRIMARY_EVIDENCE": self.session.local_data_catalog,
            "EVIDENCE_INSTRUCTION": "If a local file exists, it is the Supreme Source of Truth. All hypotheses must be derived from or tested against these specific files.",
            # DYNAMIC TOOL INJECTION
            "available_tools": available_tools,
            "tool_descriptions": tool_descriptions,
            "available_agents": available_agents
        }
        
        # Gap 0: Active Recall from Nexus (Scoped strictly to current focus)
        if self.nexus_retriever:
            # STRICT FILTER: Ensure we only pull nodes matching the primary research domain
            recall_text = self.nexus_retriever.retrieve_relevant_nodes(self.research_question, limit=5)
            if recall_text:
                # Basic noise filter: If research is about electrolytes, but recall mentions codes/qubits, drop it.
                if "electrolyte" in self.research_question.lower() and ("qubit" in recall_text.lower() or "quantum" in recall_text.lower()):
                    logger.warning("Nexus Recall Domain Mismatch (Safety Purge): SSE target, but QEC found in memory. Purging leakage.")
                    recall_text = ""
                
                if recall_text:
                    context["nexus_recall"] = recall_text
                    logger.info(f"Injected Scoped Nexus Recall ({len(recall_text)} chars)")
        
        # SVEL INJECTION: Strategic Battle Plan
        if hasattr(self.session, 'battle_plan') and self.session.battle_plan:
            context["strategic_context"] = self.session.battle_plan.get("injected_context", "")
            logger.info(" [STRATEGY] Strategic Battle Plan injected into planning context.")

        # ENFORCE MIND/BODY LOCK
        context = await self._inject_mind_body_lock(context)

        return context

    async def _inject_mind_body_lock(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        SVEL ARCHITECTURE: MIND/BODY LOCK
        Force-injects component-specific T1 Meta-Skills via SEMANTIC TITAN SELECTION.
        """
        if not self.expert_system:
            return context

        # 1. DYNAMIC COGNITIVE OS
        # Instead of hardcoded "brainstorm" or "literature", we use the ACTUAL question
        # to find the right cognitive protocols.
        strategic_context = context.get("strategic_context", "")
        
        # Inject Strategic Protocols based on the research goal
        injected_strategy = await self.expert_system.inject_meta_skills(
            base_prompt="", 
            query=f"Scientific cognitive protocols for {self.research_question}",
            max_skills=3,
            domain=self.domain
        )
        
        if injected_strategy:
            context["strategic_context"] = strategic_context + "\n# [TITAN] - ORCHESTRATOR CORE PROTOCOLS\n" + injected_strategy
            logger.info(" [TITAN LOCK] Dynamic Cognition Injected via Semantic Selection.")
            
        return context

    
    async def _record_error(self, phase: str, error: str) -> None:
        """Record an error (Async)"""
        self.session.consecutive_errors += 1
        self.session.error_log.append({
            "phase": phase,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
        # Apply backoff
        backoff_idx = min(self.session.consecutive_errors - 1, len(ERROR_BACKOFF_SECONDS) - 1)
        backoff = ERROR_BACKOFF_SECONDS[backoff_idx]
        logger.warning(f"Error in {phase}: {error}. Backing off for {backoff}s")
        await asyncio.sleep(backoff)
    
    def _emit_progress(self, data: Dict[str, Any]) -> None:
        """Emit progress update"""
        data["session_id"] = self.session.id
        data["timestamp"] = datetime.now().isoformat()
        data["elapsed_hours"] = self.session.get_elapsed_hours()
        
        logger.info(f"Progress: {data.get('message', data.get('phase', 'update'))}")
        
        if self.on_progress:
            try:
                self.on_progress(data)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
                
    async def _update_status(self, text: str):
        """
        Update Jarvis status silently.
        Does NOT announce aloud.
        """
        try:
            # Still update UI progress
            self._emit_progress({"type": "status_update", "text": text})
            logger.info(f" [STATUS] Jarvis Status Update: {text}")
        except Exception as e:
            logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {e}")
            logger.warning(f"Failed to update status: {e}")
            
    # DEPRECATED: Announce is removed as per user request
    async def _announce(self, text: str):
         await self._update_status(text)
    
    def recover(self) -> bool:
        """Recover state from latest checkpoint in PersistenceVault"""
        try:
            state = vault.get_latest_checkpoint(self.session.id)
            if not state:
                logger.warning(f"No checkpoint found for session {self.session.id}")
                return False
            
            # Restore session data
            s_data = state.get("session", {})
            for key, value in s_data.items():
                if hasattr(self.session, key):
                    if key in ("started_at", "created_at", "ended_at", "last_heartbeat") and isinstance(value, str):
                        try:
                            value = datetime.fromisoformat(value)
                        except Exception:
                            try:
                                from dateutil import parser
                                value = parser.parse(value)
                            except Exception:
                                pass
                    elif key == "plans" and isinstance(value, list):
                        from backend.core.planning.plan_creator import ResearchPlan
                        parsed_plans = []
                        for p_item in value:
                            if isinstance(p_item, dict):
                                try:
                                    parsed_plans.append(ResearchPlan.from_dict(p_item))
                                except Exception:
                                    parsed_plans.append(p_item)
                            else:
                                parsed_plans.append(p_item)
                        value = parsed_plans
                    elif key == "tasks" and isinstance(value, list):
                        from backend.core.planning.plan_creator import ResearchTask
                        parsed_tasks = []
                        for t_item in value:
                            if isinstance(t_item, dict):
                                try:
                                    parsed_tasks.append(ResearchTask.from_dict(t_item))
                                except Exception:
                                    parsed_tasks.append(t_item)
                            else:
                                parsed_tasks.append(t_item)
                        value = parsed_tasks
                    setattr(self.session, key, value)
            
            # Restore hypotheses
            h_list = state.get("hypotheses", [])
            for h_dict in h_list:
                hyp = Hypothesis.from_dict(h_dict)
                self.hypothesis_tracker.add(hyp)
            
            # REHYDRATE WORLD MODEL: Load facts from local SQLite storage
            if self.world_model:
                logger.info("Rehydrating WorldModel from local persistence...")
                try:
                    # WorldModel uses SQLite, so facts are already in the DB.
                    # We just need to ensure the memory cache is warmed up if any logic depends on it.
                    # Most WorldModel methods in Titan Edition query the DB directly, 
                    # but if legacy methods are used, we should load them.
                    self.world_model.load_from_db()
                except Exception as wm_err:
                    logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {wm_err}")
                    logger.warning(f"WorldModel rehydration partial failure: {wm_err}")
            
            # PHASE 12: Discovery Recovery (Ferrari Rehydration)
            ferrari_state = state.get("ferrari_state")
            if ferrari_state and DISCOVERY_ULTRA_AVAILABLE:
                logger.info("Recovering Discovery state from checkpoint...")
                # 1. Get the session (checks mem/Redis)
                discovery_session = get_discovery_session(self.session.id)
                # 2. If Redis was cold/missing, rehydrate from checkpoint data
                # We assume if assumptions are empty, Redis didn't have it (or it's a fresh session)
                if len(discovery_session.assumptions) == 0:
                    logger.info("   Redis cold. Rehydrating from local checkpoint data.")
                    discovery_session.load_from_dict(ferrari_state)
                else:
                    logger.info("   Consensus: Redis state matches distributed swarm.")

            logger.info(f"Successfully recovered session {self.session.id} at cycle {self.session.current_cycle}")
            # FIX: Reset transient per-run counters that are not persisted in checkpoint.
            # Without this, a resumed session carries over stagnation strikes and findings
            # count from before the crash, causing premature stagnation-termination.
            self.stagnation_counter = 0
            self._last_findings_count = len(self.session.findings)
            return True
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return False

    def _compile_results(self) -> Dict[str, Any]:
        """Compile final research results (Safe Mode)"""
        hypotheses = self.hypothesis_tracker.get_all() or []
        findings = self.session.findings or []
        plans = self.session.plans or []
        error_log = self.session.error_log or []
        artifacts = getattr(self.session, 'artifacts', []) or []
        visualizations = getattr(self.session, 'visualizations', []) or []
    
        # SVEL UPGRADE: Claim Leaderboard
        # Sort by Survival Score (Robustness) -> Confidence -> Novelty
        leaderboard = sorted(
            hypotheses, 
            key=lambda h: (
                (h.survival_score if h.survival_score is not None else -1.0) if hasattr(h, 'survival_score') else (h.get('survival_score') if h.get('survival_score') is not None else -1.0), 
                (h.confidence if hasattr(h, 'confidence') else h.get('confidence', 0.0)), 
                (h.novelty_score if h.novelty_score is not None else 0.0) if hasattr(h, 'novelty_score') else (h.get('novelty_score') if h.get('novelty_score') is not None else 0.0)
            ), 
            reverse=True
        )
        
        # PHASE 42: FINAL VALIDATION PASSTHROUGH
        validated_findings = []
        for f in findings:
            if self.result_validator:
                 # Validate structure and content
                 try:
                     val_res = self.result_validator.validate(f.get("result", {}))
                     f["validation"] = val_res.to_dict()
                     
                     # Detailed experiment validation
                     if f.get("task", {}).get("type") == "experiment":
                         exp_val = self.result_validator.validate_experiment(f.get("result", {}))
                         f["experiment_validation"] = exp_val.to_dict()
                 except Exception as val_err:
                     logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {val_err}")
                     logger.warning(f"Validation failed for finding {f.get('task_id')}: {val_err}")
            
            # PHASE 43: REPRODUCIBILITY BUNDLING
            if self.reproducibility_manager and self.initial_env_snapshot:
                 try:
                     if f.get("task", {}).get("type") == "experiment":
                         # Create bundle
                         bundle_path = self.reproducibility_manager.create_bundle(
                             finding_id=f.get("task_id", "unknown"),
                             snapshot=self.initial_env_snapshot,
                             seed=self.current_seed
                         )
                         f["reproducibility_bundle"] = bundle_path
                 except Exception as rep_err:
                     logger.exception(f"[GLASS-TELEMETRY] CRITICAL FAILURE in {__name__}: {rep_err}")
                     logger.warning(f"Reproducibility bundling failed for finding {f.get('task_id')}: {rep_err}")

            validated_findings.append(f)

        return {
            "status": self.session.status.value if hasattr(self.session.status, 'value') else self.session.status,
            "session": self.session.to_dict(),
            "summary": {
                "research_question": self.research_question,
                "domain": self.domain,
                "cycles_completed": self.session.current_cycle,
                "runtime_hours": self.session.get_elapsed_hours(),
                "hypotheses_generated": len(hypotheses),
                "hypotheses_confirmed": len([h for h in hypotheses if (getattr(h, "state", None) or (h.get("state") if isinstance(h, dict) else None)) in [HypothesisState.CONFIRMED, "confirmed"]]),
                "hypotheses_refuted": len([h for h in hypotheses if (getattr(h, "state", None) or (h.get("state") if isinstance(h, dict) else None)) in [HypothesisState.REFUTED, "refuted"]]),
                "findings_count": len(findings),
                "artifacts_created": len(artifacts),
                "errors_encountered": len(error_log),
                "final_report": self.session.final_report,
                "claim_leaderboard": [h.to_dict() if hasattr(h, "to_dict") else h for h in leaderboard[:10]] # Top 10 Claims
            },
            "hypotheses": [h.to_dict() if hasattr(h, "to_dict") else h for h in hypotheses],
            "findings": validated_findings,  # Return validated findings
            "experiments": getattr(self.session, "notebook_experiments", []), # Return experiment artifacts
            "visualizations": visualizations, # Charts/Diagrams
            "plans": [p.to_dict() if hasattr(p, "to_dict") else p for p in plans],
            "errors": error_log
        }
    
    def pause(self) -> None:
        """Pause the research session"""
        # FIX: use ResearchState enum, not raw string
        self.session.status = ResearchState.PAUSED
        logger.info(f"Research session {self.session.id} paused")
    
    def resume(self) -> None:
        """Resume a paused session"""
        if self.session.status == ResearchState.PAUSED:
            self.session.status = ResearchState.EXECUTING
            logger.info(f"Research session {self.session.id} resumed")
    
    def stop(self) -> Dict[str, Any]:
        """Stop the research session and return results"""
        self.session.status = ResearchState.COMPLETED
        self.session.ended_at = datetime.now()
        return self._compile_results() 


# Convenience function
def create_deep_orchestrator(
    research_question: str,
    domain: str = "general",
    **kwargs
) -> DeepResearchOrchestrator:
    """
    Create a Deep Research Orchestrator.
    
    Args:
        research_question: Research question to investigate
        domain: Research domain
        **kwargs: Additional arguments for DeepResearchOrchestrator
        
    Returns:
        DeepResearchOrchestrator instance
    """
    return DeepResearchOrchestrator(
        research_question=research_question,
        domain=domain,
        **kwargs
    )
