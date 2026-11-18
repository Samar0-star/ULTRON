"""
Task Decomposer
===============

Breaks complex queries into parallelizable subtasks using LLM analysis.

Features:
- Intelligent query analysis
- Dependency detection
- Parallel execution planning
- Agent/tool capability matching
- Time estimation
"""

import asyncio
import json
import logging
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
# CIRCULAR IMPORT FIX: TASK_DECOMPOSITION_MODEL imported in _call_llm method

logger = logging.getLogger(__name__)


def _safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """Safely serialize object to JSON, handling non-serializable types."""
    def safe_encoder(o):
        if callable(o):
            return f"<function:{getattr(o, '__name__', 'anonymous')}>"
        if hasattr(o, '__dict__'):
            return f"<object:{type(o).__name__}>"
        return str(o)
    
    try:
        return json.dumps(obj, indent=indent, default=safe_encoder)
    except Exception:
        return str(obj)


from backend.models.task import SubTask


class NeuralFractalizer:
    """
    [GODZILLA ENGINE] Explodes complex queries into atomic research heartbeats.
    """

    def __init__(self, llm_manager=None, router=None):
        self.llm_manager = llm_manager
        self.router = router
        self._recent_queries = set()
        self._capabilities_cache = {}
        logger.info("NeuralFractalizer: Singularity Engine ONLINE.")

    async def shatter(
        self, 
        query: Any, 
        context: Optional[Dict[str, Any]] = None, 
        max_subtasks: int = 10, 
        max_parallel: int = 50
    ) -> List[Any]:
        context = context or {}
        
        # Ensure query is a string (can be a ResearchTask object)
        query_str = query.description if hasattr(query, "description") else str(query)
        
        # [GODZILLA PERSISTENCE] Access the global cache from World Model if available
        global_cache = self._recent_queries
        if context.get("world_model") and hasattr(context["world_model"], "_decomposed_queries"):
            global_cache = context["world_model"]._decomposed_queries
        
        # [GODZILLA SEMANTIC LOOP GUARD] 
        # Block redundant fractalization if query is semantically similar to recent ones
        # Aggressive threshold (0.65) to catch drifted re-wordings
        q_words = set(re.sub(r'[^a-zA-Z0-9\s]', '', query_str.lower()).split())
        for recent in global_cache:
            r_words = set(re.sub(r'[^a-zA-Z0-9\s]', '', recent.lower()).split())
            overlap = len(q_words & r_words) / max(len(q_words), 1)
            if overlap > 0.65:
                logger.warning(f" [LOOP GUARD] Query semantically similar to recent decomposition (Overlap: {overlap:.2f}). Skipping: {query_str[:50]}...")
                return []
        
        global_cache.add(query_str)
        # Limit cache size to prevent memory leak
        if len(global_cache) > 100:
            # Pop an arbitrary item to maintain size
            global_cache.remove(next(iter(global_cache)))

        logger.info(f" Decomposing query: {query_str[:100]}...")
        
        agent_caps = self._get_agent_capabilities()
        tool_caps = self._get_tool_capabilities()
        
        MAX_ATTEMPTS = 3
        last_error = None
        
        for attempt in range(MAX_ATTEMPTS):
            try:
                # Use increasing temperature to break strategic deadlocks
                temp = 0.1 + (attempt * 0.3)
                prompt = self._build_decomposition_prompt(query, context, agent_caps, tool_caps, max_subtasks)
                
                response = await self.llm_manager.run_async(
                    prompt, 
                    source="decomposer",
                    temperature=temp
                )
                
                # [GODZILLA TYPE-SAFE] Extract text from dict or string
                raw_text = response
                if isinstance(response, dict):
                    raw_text = response.get("text") or response.get("content") or str(response)
                
                tasks = self._parse_llm_response(raw_text, max_parallel, original_query=query_str)
                
                logger.info(f" [DECOMPOSER] Success at attempt {attempt + 1}. Generated {len(tasks)} tasks.")
                return tasks[:max_subtasks]
                
            except Exception as e:
                last_error = e
                logger.warning(f" [DECOMPOSER] Attempt {attempt + 1} failed: {e}. Retrying with temp={0.1 + ((attempt+1) * 0.3):.1f}...")
                await asyncio.sleep(2) # Stagger to avoid rate limits
        
        # [FATAL] If we reach here, reasoning has failed. No faking allowed.
        logger.critical(f" [DECOMPOSER] TERMINAL FAILURE: Could not decompose query after {MAX_ATTEMPTS} attempts. Error: {last_error}")
        raise RuntimeError(f"Task Decomposition Failed Rigor Audit: {last_error}")

    async def _call_llm(self, prompt: str) -> str:
        """Helper to call LLM"""
        # Lazy import to avoid circular dependency
        from backend.llm_manager import TASK_DECOMPOSITION_MODEL
        
        if not self.llm_manager:
            raise ValueError("LLM Manager not initialized")
        
        # Support both new and old LLM manager interfaces
        if hasattr(self.llm_manager, "run"):
            # Check if run is async
            if asyncio.iscoroutinefunction(self.llm_manager.run):
                resp = await self.llm_manager.run(prompt=prompt, model=TASK_DECOMPOSITION_MODEL)
            else:
                resp = self.llm_manager.run(prompt=prompt, model=TASK_DECOMPOSITION_MODEL)
        elif callable(self.llm_manager):
            resp = self.llm_manager(prompt)
        else:
            raise ValueError("Invalid LLM Manager")
            
        if isinstance(resp, dict):
            return resp.get("text", "") or resp.get("content", "")
        return str(resp)

    def _build_decomposition_prompt(
        self,
        query: str,
        context: Dict,
        agent_capabilities: Dict[str, List[str]],
        tool_capabilities: Dict[str, List[str]],
        max_subtasks: int
    ) -> str:
        """Build the LLM prompt for decomposition with strict Tool/Skill separation."""
        
        # [GODZILLA TAXONOMY] Fetch real scientific skills from the Expert System
        try:
            from backend.core.skill_injector import get_expert_system
            expert = get_expert_system()
            skills_list = "\n".join([f"- {s}" for s in expert.list_skills()])
        except:
            skills_list = "Scientific discovery, data analysis, literature search"

        agent_list = "\n".join([
            f"- {name}: {', '.join(caps)}"
            for name, caps in agent_capabilities.items()
        ])

        # Tool list: Ensure we are only listing names, not skills here
        tool_list = "\n".join([f"- {name}" for name in tool_capabilities.keys()])

        return f"""# SINGULARITY TASK FRACTALIZATION (SOVEREIGN CLASS)
        ==================================================
        You are the **Singularity Engine**. Your goal is to explode a single complex query into a **Massive Atomic Swarm** of parallelizable sub-tasks.
        ## PRIMARY RESEARCH OBJECTIVE
        "{context.get('research_question', 'UNDEFINED RESEARCH MISSION')}"

        ## ACTIVE SUB-MISSION
        "{query}"
        
## DECOMPOSITION MANDATES
1. **Ph.D. LEVEL RIGOR**: Every task assigned to the `experiment_agent` MUST involve a physical or statistical simulation.
2. **STATISTICAL MANDATE**: Every experiment MUST include a hypothesis testing step (p-value, effect size).
3. **DATA ANALYSIS MANDATE**: Tasks involving loading, parsing, verifying schemas, or statistical profiling of local files (e.g. .csv, .parquet, data tables) MUST be assigned to `data_analyzer_agent`. NEVER assign local dataset reading, CSV parsing, or table verification to `research_agent`.
4. **LITERATURE MANDATE**: Tasks requiring literature search, paper reviews, or web queries MUST be assigned to `research_agent` or `doc_reader_agent`.
5. **TAXONOMY LOCK**: Distinguish between TOOLS and SKILLS.
    - `required_tools` MUST only contain names from the **AVAILABLE TOOLS** list.
    - `required_skills` MUST only contain names from the **AVAILABLE SKILLS** list.
6. **ATOMICITY**: Break tasks into the smallest possible unit of work.
7. **MAXIMUM PARALLELISM**: Maximize `can_run_parallel: true`.

## AVAILABLE AGENTS
{agent_list}

## AVAILABLE TOOLS (Executable Software)
{tool_list}

## AVAILABLE SKILLS (Scientific Methodologies)
{skills_list}

## OUTPUT FORMAT
You MUST return ONLY a raw JSON object. NO markdown fences. NO introductory text.
Schema:
{{
  "rationale": "High-level strategy",
  "subtasks": [
    {{
      "id": "sub_1",
      "description": "Atomic action",
      "type": "research|analysis|validation",
      "agent": "agent_id",
      "args": {{"param": "value"}},
      "required_tools": [],
      "required_skills": [],
      "can_run_parallel": true,
      "priority": 5
    }}
  ]
}}
"""

    def _parse_llm_response(
        self,
        llm_result: str,
        max_parallel: int,
        original_query: str = ""
    ) -> List[SubTask]:
        """Parse LLM response into SubTask objects using the Godzilla V25.0 Hunter."""
        from backend.utils.json_repair import repair_json
        
        data = repair_json(llm_result)
        
        if not data:
            logger.error(f" [CRITICAL] Failed to parse LLM decomposition response.")
            raise ValueError("No valid JSON found in decomposition response")

        # Normalize keys: accept subtasks or tasks
        raw_subtasks = []
        if isinstance(data, list):
            raw_subtasks = data
        elif isinstance(data, dict):
            raw_subtasks = data.get("subtasks", data.get("tasks", []))
        
        if not raw_subtasks:
            raise ValueError("No subtasks in parsed LLM response")

        # Convert to SubTask objects
        subtasks = []
        for i, st_data in enumerate(raw_subtasks):
            # Validate required fields
            if "id" not in st_data or "description" not in st_data:
                logger.warning(f"Skipping invalid subtask {i}: missing id or description")
                continue

            # [GODZILLA FIX] Agent Name Sanitizer
            # LLMs often hallucinate suffixes like ':agent' or ':dataanalyzeragent'
            agent_raw = st_data.get("agent")
            if agent_raw and ":" in agent_raw:
                agent_clean = agent_raw.split(":")[0].strip()
                logger.info(f" [SANITIZER] Mapped hallucinated agent '{agent_raw}' -> '{agent_clean}'")
                st_data["agent"] = agent_clean

            subtask = SubTask(
                id=st_data.get("id", f"subtask_{i+1}"),
                description=st_data["description"],
                type=st_data.get("type", "generic"),
                agent=st_data.get("agent"),
                tool=st_data.get("tool"),
                adapter=st_data.get("adapter"),
                args=st_data.get("args", {}),
                dependencies=st_data.get("dependencies", []),
                can_run_parallel=st_data.get("can_run_parallel", True),
                priority=st_data.get("priority", 5),
                estimated_seconds=st_data.get("estimated_seconds", 10.0),
                capabilities_needed=st_data.get("capabilities_needed", []),
                timeout=st_data.get("timeout", 120.0),
                retry_count=st_data.get("retry_count", 2)
            )

            subtasks.append(subtask)

        # Sort by priority
        subtasks.sort(key=lambda s: s.priority)

        # Enforce max parallel limit
        parallel_count = sum(1 for s in subtasks if s.can_run_parallel and not s.has_dependencies())
        if parallel_count > max_parallel:
            # Mark some as non-parallel
            parallel_tasks = [s for s in subtasks if s.can_run_parallel and not s.has_dependencies()]
            for task in parallel_tasks[max_parallel:]:
                task.can_run_parallel = False

        return subtasks

    def _get_agent_capabilities(self) -> Dict[str, List[str]]:
        """Get available agents and their capabilities"""

        if "agents" in self._capabilities_cache:
            return self._capabilities_cache["agents"]

        agents = {}
        legacy_aliases = getattr(self.router, "SOVEREIGN_AGENT_ALIASES", {
            "web_search_agent", "doc_reader_agent", "summarizer_agent",
            "qa_agent", "fact_checker_agent", "ml_model_builder_agent"
        })

        if self.router and hasattr(self.router, "agent_map"):
            for name, agent in self.router.agent_map.items():
                if name in legacy_aliases and name != "data_analyzer_agent":
                    continue
                if hasattr(agent, "capabilities"):
                    agents[name] = agent.capabilities
                elif hasattr(agent, "get_capabilities"):
                    try:
                        agents[name] = agent.get_capabilities()
                    except Exception as e:
                        logger.debug(f"Failed to get capabilities for {name}: {e}")
                        agents[name] = ["unknown"]
                else:
                    agents[name] = ["general"]

        self._capabilities_cache["agents"] = agents
        return agents

    def _get_tool_capabilities(self) -> Dict[str, List[str]]:
        """Get available tools and their capabilities - BEAST MODE ENHANCED"""

        if "tools" in self._capabilities_cache:
            return self._capabilities_cache["tools"]

        tools = {}
        
        # BEAST MODE: Direct REGISTRY import for full tool discovery
        try:
            from backend.tools.tool_registry import REGISTRY
            # [GODZILLA FIX] Use the correct public API for tool discovery
            tool_names = REGISTRY.list_tools()
            for name in tool_names:
                tools[name] = ["scientific_execution", "research"]
            
            logger.info(f" BEAST: Physically restored {len(tools)} real tools from REGISTRY")
        except ImportError:
            logger.warning("Tool registry not available for discovery")

        # Fallback: check router.tool_registry
        if not tools and self.router and hasattr(self.router, "tool_registry"):
            registry = self.router.tool_registry
            if hasattr(registry, "_meta"):
                for name, meta in registry._meta.items():
                    tools[name] = meta.get("capabilities", [])

        self._capabilities_cache["tools"] = tools
        return tools

    async def decompose_with_thinking(
        self,
        query: str,
        event_callback=None,
        context: Optional[Dict[str, Any]] = None,
        max_subtasks: int = 10,
        max_parallel: int = 50
    ) -> List[SubTask]:
        """
        Decompose query into subtasks, streaming real LLM thinking to event_callback.
        """
        context = context or {}
        
        logger.info(f" Decomposing query with thinking: {query[:100]}...")

        # Get capabilities
        agent_capabilities = self._get_agent_capabilities()
        tool_capabilities = self._get_tool_capabilities()

        # Build prompt
        prompt = self._build_decomposition_prompt(
            query=query,
            context=context,
            agent_capabilities=agent_capabilities,
            tool_capabilities=tool_capabilities,
            max_subtasks=max_subtasks
        )

        full_text = ""
        full_thinking = ""

        try:
            # Check if LLM manager supports streaming
            if self.llm_manager and hasattr(self.llm_manager, "stream_async"):
                if event_callback:
                    await event_callback("progress", {"phase": "Decomposition", "status": "analyzing"})
                
                # Stream both thinking and content
                async for chunk in self.llm_manager.stream_async(prompt, mode="thinking"):
                    chunk_type = chunk.get("type")
                    content = chunk.get("content", "")
                    
                    if chunk_type == "thinking":
                        full_thinking += content
                        if event_callback:
                            await event_callback("thinking", {"thought": content})
                            
                    elif chunk_type == "text":
                        full_text += content
                        
                    elif chunk_type == "error":
                        logger.error(f"Stream error: {content}")
            
            else:
                # Fallback to legacy non-streaming
                logger.warning("LLM Manager does not support stream_async, falling back")
                return await self.shatter(query, context, max_subtasks, max_parallel)

            # Log captured thinking
            if full_thinking:
                logger.info(f" Captured {len(full_thinking)} chars of thinking")

            # Parse final JSON
            subtasks = self._parse_llm_response(full_text, max_parallel, original_query=query)

            logger.info(
                f" Decomposed into {len(subtasks)} subtasks "
                f"({sum(1 for s in subtasks if s.can_run_parallel)} parallel-capable)"
            )

            return subtasks

        except Exception as e:
            logger.error(f" Decomposition failed: {e}")
            # Try to salvage if we have partial text that looks like JSON
            if full_text and "subtasks" in full_text:
                try:
                    return self._parse_llm_response(full_text, max_parallel, original_query=query)
                except Exception as e:
                    logger.debug(f"Salvage parse failed: {e}")
                    pass
                    
            return [
                SubTask(
                    id="step_1",
                    description=f"Search and synthesize primary literature for: {query[:80]}",
                    type="research",
                    agent="research_agent",
                    args={"query": query},
                    dependencies=[],
                    can_run_parallel=True,
                    priority=1,
                    timeout=120.0
                ),
                SubTask(
                    id="step_2",
                    description="Execute empirical validation and statistical analysis",
                    type="analysis",
                    agent="experiment_agent",
                    args={"query": query},
                    dependencies=["step_1"],
                    can_run_parallel=False,
                    priority=2,
                    timeout=120.0
                ),
                SubTask(
                    id="step_3",
                    description="Write comprehensive research report",
                    type="writing",
                    agent="writer_agent",
                    args={},
                    dependencies=["step_2"],
                    can_run_parallel=False,
                    priority=3,
                    timeout=120.0
                )
            ]


    def build_dag(self, subtasks: List[SubTask]) -> Dict[str, Any]:
        """
        Build DAG (Directed Acyclic Graph) from subtasks.

        Returns:
            {
                "nodes": {id: subtask},
                "edges": [(from_id, to_id), ...],
                "roots": [id, ...],  # No dependencies
                "execution_order": [[batch1], [batch2], ...]  # Parallel batches
            }
        """

        nodes = {st.id: st for st in subtasks}
        edges = []

        # Build edges from dependencies
        for st in subtasks:
            for dep_id in st.dependencies:
                if dep_id in nodes:
                    edges.append((dep_id, st.id))

        # Find roots (no dependencies)
        roots = [st.id for st in subtasks if not st.has_dependencies()]

        # Topological sort with parallel batching
        execution_order = []
        completed = set()
        remaining = set(nodes.keys())

        while remaining:
            # Find all tasks that can run now
            ready = [
                st_id for st_id in remaining
                if nodes[st_id].can_run_after(completed)
            ]

            if not ready:
                # Circular dependency detected
                logger.error(f" Circular dependency detected. Remaining: {remaining}")
                break

            execution_order.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        return {
            "nodes": {k: v.to_dict() for k, v in nodes.items()},
            "edges": edges,
            "roots": roots,
            "execution_order": execution_order,
            "total_subtasks": len(subtasks),
            "parallel_batches": len(execution_order),
            "max_parallel_in_batch": max(len(batch) for batch in execution_order) if execution_order else 0
        }

    def clear_cache(self):
        """Clear capabilities cache (for testing)"""
        self._capabilities_cache.clear()


# Canonical alias for backward compatibility and test suites
TaskDecomposer = NeuralFractalizer

