# backend/central_router_beast.py
"""
CentralRouterBeast  consolidated router with Graph & UltronMeta Orchestrator integration.
TITAN V68.14: Final Sovereignty Edition.

UPGRADES:
- Total Visualization Excision: Legacy viz modules and ghosts DELETED.
- JSON-Safe Data Logging: No more string amputation. Recursive JSON pruning active.
- Metal/MPS Unlocked: Optimized for hardware acceleration.
"""

from __future__ import annotations

import os
import re
import json
import asyncio
import time
import uuid
import logging
import traceback
import threading

import concurrent.futures
import pkgutil
import importlib
import shutil
import inspect
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union, Tuple

logger = logging.getLogger("ultron.central_router_beast")
logger.setLevel(os.getenv("BEAST_LOG_LEVEL", "INFO"))

logger.debug("CentralRouterBeast: Standard library imports done.")
logger.debug("CentralRouterBeast: Importing backend.core modules...")

# /core infrastructure integration
try:
    logger.debug("CentralRouterBeast: Importing WorldModel...")
    from backend.core.world_model import WorldModel, get_shared_embedding_model
    from backend.core.message_bus import get_message_bus
    from backend.core.result_merger import ResultMerger
    CORE_AVAILABLE = True
    logger.debug("CentralRouterBeast: Core modules imported.")
except ImportError as e:
    logger.critical(f" [INTEGRITY CRITICAL] Core ULTRON modules missing: {e}")
    if os.getenv("GODZILLA_MODE", "false").lower() == "true":
        raise RuntimeError("GODZILLA_MODE requires core infrastructure. Aborting.")
    CORE_AVAILABLE = False

# Data Logger for analytics and audit trails
try:
    from backend.services.data_logger import data_logger
    DATA_LOGGING_ENABLED = True
except ImportError:
    data_logger = None
    DATA_LOGGING_ENABLED = False

def _json_safe_truncate(obj: Any, max_chars: int = 100000, max_items: int = 5000) -> Any:
    """
    Safely serialize large research results without aggressive truncation.
    """
    if isinstance(obj, str):
        return obj[:max_chars] + " [TRUNCATED]" if len(obj) > max_chars else obj
    if isinstance(obj, dict):
        return {k: _json_safe_truncate(v, max_chars, max_items) for k, v in obj.items()}
    if isinstance(obj, list):
        items = obj[:max_items] if max_items is not None else obj
        return [_json_safe_truncate(v, max_chars, max_items) for v in items]
    return obj

def _log_research_data(query: str, result: Any, 
                       session_id: Optional[str] = None, engine: str = "unknown",
                       tools_used: Optional[List[str]] = None) -> None:
    """
    Log research query and response for model training.
    """
    if not DATA_LOGGING_ENABLED or not data_logger:
        return
    
    try:
        # Extract text response from various result formats
        response_text = None
        if isinstance(result, dict):
            # JSON-SAFE TRUNCATION
            safe_result = _json_safe_truncate(result, 100000)
            response_text = json.dumps(safe_result)
        elif isinstance(result, str):
            response_text = result[:100000]
        else:
            response_text = str(result)[:50000]
        
        data_logger.log_quick(
            query=query,
            response=response_text,
            session_id=session_id,
            tools_used=tools_used or [engine],
            success=True
        )
    except Exception as e:
        logger.warning(f"Failed to log research data: {e}")

from backend.llm_manager import LLMManager

# Trace logging setup
TRACE_LOG_PATH = os.getenv("ULTRON_TRACE_LOG", "logs/ultron_traces.jsonl")

def _write_trace(trace: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(TRACE_LOG_PATH) if TRACE_LOG_PATH and os.path.dirname(TRACE_LOG_PATH) else "logs", exist_ok=True)
        with open(TRACE_LOG_PATH, 'a', encoding='utf-8') as f:
            entry = {**trace, "ts": datetime.utcnow().isoformat()}
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.debug(f"Failed to write trace: {e}")

def _safe_import(module_path: str, attr: Optional[str] = None):
    try:
        m = importlib.import_module(module_path)
        return getattr(m, attr) if attr else m
    except Exception:
        return None

# =============================================================================
# Decision trace and selector cache
# =============================================================================
try:
    from backend.core.selector_cache import SelectorCache
except ImportError:
    class SelectorCache:
        def __init__(self, **kwargs): pass
        def get(self, *args): return None
        def set(self, *args): pass

class DecisionTrace:
    def __init__(self, query: str = ""):
        self.trace_id = str(uuid.uuid4())[:8]
        self.query = query
        self.start_ts = time.time()
        self.steps: List[Dict[str, Any]] = []
        self.candidates: List[Dict[str, Any]] = []
        self.selected: Optional[str] = None
        self.selected_confidence: float = 0.0
        self.attempts: List[Dict[str, Any]] = []
        self.meta: Dict[str, Any] = {}

    def add_step(self, name: str, info: Dict[str, Any]):
        self.steps.append({"name": name, "ts": time.time(), "info": info})

    def add_candidate(self, name: str, score: float, reason: str = ""):
        self.candidates.append({"name": name, "score": float(score), "reason": reason, "ts": time.time()})

    def set_selected(self, name: Optional[str], confidence: float = 0.0):
        self.selected = name
        self.selected_confidence = float(confidence)

    def finalize(self, error: Optional[str] = None):
        self.meta["error"] = error
        self.meta["duration_s"] = time.time() - self.start_ts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "selected": self.selected,
            "selected_confidence": self.selected_confidence,
            "candidates": self.candidates,
            "steps": self.steps,
            "attempts": self.attempts,
            "meta": self.meta,
        }

# ---------------------------------------------------------------------
# CentralRouterBeast
# ---------------------------------------------------------------------
class CentralRouterBeast:
    def __init__(
        self,
        adapters: Optional[Dict[str, Any]] = None,
        result_store: Optional[Any] = None,
        max_workers: int = 8,
        max_parallel_tools: int = 4,
        debug: bool = False,
    ):
        logger.info("Starting CentralRouterBeast [TITAN V68.14]")
        self.adapters: Dict[str, Any] = adapters or {}
        self.agent_map: Dict[str, Any] = {}
        self.tool_map: Dict[str, Any] = {}
        
        # Core Infrastructure
        self.world_model = None
        self.message_bus = None
        self.neural_fractalizer = None
        self.result_merger = None

        if CORE_AVAILABLE:
            try:
                # [FIX] Neural Fractalizer moved to orchestration
                from backend.orchestration.singularity import SingularityEngine
                from backend.llm_manager import get_llm_manager
                brain = get_llm_manager()
                self.neural_fractalizer = SingularityEngine(router=self, llm_manager=brain)


                self.result_merger = ResultMerger()
                self.message_bus = get_message_bus()
            except Exception as e:
                logger.warning(f"Core infrastructure boot failed: {e}")

        # Lazy load result store
        try:
            from backend.memory.result_store import get_result_store
            self.result_store = get_result_store()
        except:
            self.result_store = None

        # LLM Manager
        from backend.llm_manager import llm_manager
        self.llm_manager = llm_manager

        # Discover Agents
        self._discover_agents()
        
        # Tool Mapping
        try:
            from backend.tools.tool_registry import REGISTRY
            self.tool_map = {n: True for n in REGISTRY.list_tools()}
        except:
            self.tool_map = {}

        self.selector_cache = SelectorCache(max_size=2048)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.max_parallel_tools = max_parallel_tools

    # Canonical mapping of deprecated 2025 micro-agents -> 2027 Sovereign Agents
    SOVEREIGN_AGENT_ALIASES: Dict[str, str] = {
        "web_search_agent": "research_agent",
        "doc_reader_agent": "research_agent",
        "summarizer_agent": "research_agent",
        "qa_agent": "research_agent",
        "data_analyzer_agent": "experiment_agent",
        "ml_model_builder_agent": "experiment_agent",
        "fact_checker_agent": "red_team_agent",
    }

    def _discover_agents(self):
        """Discover and instantiate the 2027 Sovereign Frontier Agent Fleet."""
        sovereign_agents_to_register = [
            ("research_agent", "backend.agents.research_agent", "ResearchAgent"),
            ("experiment_agent", "backend.agents.experiment_agent", "ExperimentAgent"),
            ("red_team_agent", "backend.agents.red_team_agent", "RedTeamAgent"),
            ("writer_agent", "backend.agents.writer_agent", "GodzillaWriterAgent"),
            ("report_composer_agent", "backend.agents.report_composer", "ReportComposerAgent"),
        ]

        for key, module_path, class_name in sovereign_agents_to_register:
            try:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                instance = cls()
                if hasattr(instance, "llm_manager"):
                    instance.llm_manager = self.llm_manager
                if hasattr(instance, "router"):
                    instance.router = self
                if key == "research_agent" and hasattr(instance, "set_router"):
                    instance.set_router(self)

                self.agent_map[key] = instance
                logger.info(f" [DISCOVERY] Sovereign Agent registered: {key}")
            except Exception as e:
                logger.error(f" [DISCOVERY] Failed to register {key}: {e}")

        # Bind legacy micro-agent aliases directly to the Sovereign Agent instances
        # so zero 2025 micro-agent wrappers are instantiated or invoked by the router.
        for legacy_key, sovereign_key in self.SOVEREIGN_AGENT_ALIASES.items():
            if sovereign_key in self.agent_map:
                self.agent_map[legacy_key] = self.agent_map[sovereign_key]

    async def route(self, query: str, **kwargs) -> Dict[str, Any]:
        trace = DecisionTrace(query=query)
        try:
            # 1. EXPLICIT BYPASS (with Sovereign Agent canonicalization)
            explicit_agent = kwargs.get("agent_name")
            if explicit_agent in self.SOVEREIGN_AGENT_ALIASES:
                explicit_agent = self.SOVEREIGN_AGENT_ALIASES[explicit_agent]
            if explicit_agent and explicit_agent in self.agent_map:
                logger.info(f" ROUTER BYPASS: Explicit Sovereign agent: {explicit_agent}")
                res = await self.execute_agent_async(explicit_agent, query, kwargs, trace)
                _log_research_data(query, res, kwargs.get("mission_id"), kwargs.get("session_id"), explicit_agent)
                return {"agent": explicit_agent, "result": res, "trace": trace.to_dict()}

            # 2. ULTRON CORE REDIRECT
            ctx = kwargs.get("context") or {}
            in_session = (
                kwargs.get("orchestrator") == "DeepResearch"
                or (isinstance(ctx, dict) and (ctx.get("orchestrator") == "DeepResearch" or ctx.get("research_session")))
            )
            if not in_session:
                logger.info(" ROUTER DECISION: Redirecting to ResearchAgent (Main Entry)")
                res = await self.execute_agent_async("research_agent", query, {**kwargs, "deep_mode": True}, trace)
                _log_research_data(query, res, kwargs.get("mission_id"), kwargs.get("session_id"), "research_agent")
                return {"engine": "ultron_engine", "result": res, "trace": trace.to_dict()}

            # 3. SELECT SOVEREIGN COMPONENT
            detection = await self.select_component_via_llm(query, kwargs.get("context"))
            comp = detection.get("selected")
            if comp in self.SOVEREIGN_AGENT_ALIASES:
                comp = self.SOVEREIGN_AGENT_ALIASES[comp]

            if comp in self.agent_map:
                res = await self.execute_agent_async(comp, query, kwargs, trace)
                return {"agent": comp, "result": res, "trace": trace.to_dict()}

            return {"error": "no_suitable_component", "trace": trace.to_dict()}

        except Exception as e:
            logger.exception("Routing failed")
            return {"error": str(e), "traceback": traceback.format_exc()}

    # Alias for route
    route_async = route

    async def select_component_via_llm(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Only expose Sovereign Agents to the LLM selector (never 2025 micro-agent aliases)
        in_session = isinstance(context, dict) and (context.get("orchestrator") == "DeepResearch" or context.get("research_session"))
        cands = [
            k for k in self.agent_map.keys()
            if k not in self.SOVEREIGN_AGENT_ALIASES and not (in_session and k == "research_agent" and context.get("block_research_agent"))
        ]
        prompt = f"Select the best Sovereign agent from {cands} for: {query}. Return JSON: {{\"selected\": \"name\"}}"
        try:
            from backend.llm_manager import TASK_ROUTING_MODEL
            from backend.utils.json_repair import repair_json
            raw = await self.llm_manager.run_async(prompt, model=TASK_ROUTING_MODEL)
            text = raw.get("text", "{}") if isinstance(raw, dict) else str(raw)
            parsed = repair_json(text)
            if isinstance(parsed, dict) and parsed.get("selected"):
                sel = parsed.get("selected")
                sel = self.SOVEREIGN_AGENT_ALIASES.get(sel, sel)
                return {"selected": sel, "confidence": 1.0}
            return {"selected": "research_agent", "confidence": 0.5}
        except Exception as e:
            logger.warning(f"Component selection parsing failed: {e}")
            return {"selected": "research_agent", "confidence": 0.5}

    async def execute_agent_async(self, agent_name: str, query: str, kwargs: Dict[str, Any], trace: DecisionTrace) -> Dict[str, Any]:
        agent = self.agent_map.get(agent_name)
        if not agent: return {"error": "agent_not_found"}
        
        try:
            payload = kwargs.get("payload") or {}
            task = {"payload": {"query": query, **payload}, "meta": kwargs.get("meta", {})}
            
            ctx = kwargs.get("context") or {}
            combined_context = {**kwargs, **(ctx if isinstance(ctx, dict) else {})}
            if hasattr(agent, "run"):
                res = agent.run(task, combined_context)
                if inspect.isawaitable(res): res = await res
                return res
            return {"error": "invalid_agent_interface"}
        except Exception as e:
            return {"error": f"agent_failed: {str(e)}"}

def get_router():
    # Global singleton pattern
    if not hasattr(get_router, "_instance"):
        get_router._instance = CentralRouterBeast()
    return get_router._instance

# Backward compatibility and modern standardized aliases
CentralRouter = CentralRouterBeast
get_router_instance = get_router

