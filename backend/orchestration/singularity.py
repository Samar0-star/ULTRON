"""
The Singularity Engine (Dynamic Scaling)
========================================
**THE FRACTAL GENERATOR.**

Use Cases:
1.  **Infinite Decomposition**: Breaks a vague task ("Fix the economy") into 1,000 actionable atomic steps.
2.  **Parallelism Scaling**: Determines how wide the swarm should go (10 agents? 100 agents?).
3.  **Task Atomicization**: Ensures no task is too big for a single worker to handle.
4.  **Micro-Orchestration**: Spawns mini-orchestrators for complex sub-problems.

GODZILLA-TIER UPGRADES:
- Upgrade 1: Deterministic Complexity Gate (Efficiency)
- Upgrade 2: Failure Memory (Avoids bad splits)
- Upgrade 3: Decomposition Typing (Exploration vs Falsification)
- Upgrade 4: Redundancy Filter (Zero-token deduplication)
- Upgrade 5: Decomposition Memory (Meta-learning)

It turns "impossible" into "done."
"""
import hashlib
import json
import logging
import asyncio
import os
from typing import List, Dict, Any, Optional, Set

from backend.core.planning.plan_creator import ResearchTask, ResearchPlan
from backend.llm_manager import TASK_DECOMPOSITION_MODEL

# Conditional import to avoid circular dependency issues if file missing
try:
    from backend.discovery.failure_patterns import get_failure_index
    FAILURE_PATTERNS_AVAILABLE = True
except ImportError:
    FAILURE_PATTERNS_AVAILABLE = False
    
logger = logging.getLogger("backend.orchestration.singularity")

class SingularityEngine:
    """
    Handles 'Hyperscaling' by decomposing massive tasks into recursive child sessions.
    
    Now disciplined by:
    - Complexity Scoring (Math, not LLM)
    - Failure Memory (Scar tissue)
    - Redundancy Filtering (Hygiene)
    """
    
    def __init__(self, orchestrator_factory: Any = None, llm_manager: Any = None, router: Any = None):
        """
        Initialize the Fractal Generator.
        
        Args:
            orchestrator_factory: Factory to spawn new orchestrators
            llm_manager: LLM client for intelligent decomposition (REQUIRED)
            router: CentralRouterBeast for child execution
        """
        self.orchestrator_factory = orchestrator_factory
        self.llm_manager = llm_manager
        self.router = router
        
        # UPGRADE 5: Decomposition Memory
        # Key: hash(task_description), Value: {depth, child_count, status}
        self._decomposition_memory: Dict[str, Dict[str, Any]] = {}
        
        if not self.router:
            logger.warning("SingularityEngine initialized without router! Micro-orchestration will fail.")
    
    # UPGRADE 6: Hydra Protocol (Dynamic Recovery)
    async def re_decompose(self, failed_task: ResearchTask, error_context: str, depth: int = 1) -> List[ResearchTask]:
        """
        The Hydra Logic: Split a failed task into 2-3 simpler tasks.
        """
        # [ULTRON BEAST FIX] Kill the Hydra Death Spiral
        if depth > 3:
            logger.error(f" [HYDRA] Max recursion depth (3) reached for task {failed_task.id}. Aborting fractalization.")
            return []

        logger.info(f" [RECOVERY] Hydra Protocol Activated: recovering failed task {failed_task.id} (Depth: {depth})")
        
        prompt = f"""
        HYDRA PROTOCOL - FRACTAL RECOVERY
        
        The following task FAILED during execution:
        TASK: {failed_task.description}
        ERROR: {error_context}
        
        Your job is to BREAK IT DOWN into 2-3 simpler, easier sub-tasks that bypass the failure mode.
        If the error was "Missing Data", ask to "Search Alternative Sources".
        If the error was "Code Error", ask to "Debug and Write Simpler Code".
        
        Return ONLY a JSON list of new sub-tasks (dictionaries with 'description', 'task_type').
        """
        
        try:
            result = await asyncio.to_thread(
                self.llm_manager.run,
                prompt=prompt,
                model=TASK_DECOMPOSITION_MODEL
            )
            # Parse JSON logic similar to decompose_task
            
            # Handle different return types from LLM Manager (dict vs str)
            if isinstance(result, dict):
                text = result.get("text", result.get("content", "[]"))
            else:
                text = str(result)

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            try:
                from backend.utils.json_repair import repair_json
                sub_dicts = repair_json(text.strip())
                if not isinstance(sub_dicts, list):
                    if isinstance(sub_dicts, dict) and "subtasks" in sub_dicts:
                        sub_dicts = sub_dicts["subtasks"]
                    else:
                        sub_dicts = [sub_dicts]
            except Exception as pe:
                logger.error(f" [SINGULARITY] JSON repair failed in re_decompose: {pe}")
                sub_dicts = []

            new_tasks = []
            for d in sub_dicts:
                if not isinstance(d, dict): continue
                new_tasks.append(ResearchTask(
                    description=d.get("description", ""),
                    task_type=d.get("task_type", failed_task.task_type),
                    priority=failed_task.priority, # Keep priority
                    metadata={"recovery_parent": failed_task.id}
                ))
            
            return new_tasks


            
        except Exception as e:
            logger.error(f"Hydra Recovery Failed: {e}")
            return []

    async def on_child_failure(self, parent_task: ResearchTask, failed_child: ResearchTask, error: str) -> List[ResearchTask]:
        """
        Public handler for triggering Hydra Recovery.
        """
        child_id = getattr(failed_child, "id", None) or (failed_child.get("id") if isinstance(failed_child, dict) else "unknown")
        logger.warning(f"Singularity: Child task {child_id} failed. Reason: {error}")
        parent_payload = getattr(parent_task, "payload", None) if not isinstance(parent_task, dict) else parent_task.get("payload")
        curr_depth = parent_payload.get("recursion_depth", 0) if isinstance(parent_payload, dict) else 0
        return await self.re_decompose(failed_child, error, depth=int(curr_depth) + 1)

    def _complexity_score(self, task: ResearchTask) -> int:
        """
        UPGRADE 1: Deterministic Complexity Gate.
        
        Calculates a heuristic score for task complexity.
        LLM becomes secondary to this signal.
        
        Returns:
            Proportional to complexity (0-10+)
        """
        desc = task.description.lower()
        score = 0
        
        # Length heuristic (longer = more complex)
        score += len(desc) // 100
        
        # Conjunction heuristic (and/or = multiple parts)
        score += desc.count(" and ")
        score += desc.count(" or ")
        
        # Logic heuristic (if/when = conditional complexity)
        score += desc.count(" if ")
        score += desc.count(" when ")
        score += desc.count(" depends ")
        
        # Scope heuristic
        if "comprehensive" in desc or "detailed" in desc or "full" in desc:
            score += 1
            
        return score

    def _hash_task(self, description: str) -> str:
        """Create stable hash for a task description."""
        return hashlib.md5(description.encode()).hexdigest()

    async def shatter(self, task: ResearchTask, context: Dict[str, Any] = None) -> List[ResearchTask]:
        """[TITAN V155.0] Alias for decompose_task to support Supreme Orchestration."""
        return await self.decompose_task(task, context)

    async def decompose_task(self, task: ResearchTask, context: Dict[str, Any] = None) -> List[ResearchTask]:

        """
        Takes a complex parent task and breaks it into smaller, atomic sub-tasks.
        Now guarded by 5 layers of discipline.
        """
        context = context or {}
        depth = int(context.get("depth", task.payload.get("depth", 0) if isinstance(getattr(task, "payload", None), dict) else 0))
        if depth >= int(os.environ.get("SINGULARITY_MAX_DEPTH", "5")):
            logger.warning(f" [SINGULARITY] Depth limit reached ({depth}). Terminating decomposition before LLM call.")
            return [task]

        # 0. Safety Check
        if not self.llm_manager:
            logger.warning("Singularity: No LLM manager, returning original task.")
            return [task]
            
        # UPGRADE 1: Deterministic Gate
        # If task is simple math-wise, don't waste tokens asking LLM
        complexity = self._complexity_score(task)
        if complexity < 1:  # [TITAN V240.1] Aggressive Decomposition
            logger.debug(f"Singularity: Task atomic/simple (score={complexity}), skipping decomposition.")
            return [task]

        # UPGRADE 2: Failure Pattern Check
        # If this task pattern is known to cause failure/loops, don't split it further
        if FAILURE_PATTERNS_AVAILABLE:
            try:
                # [GODZILLA FIX] Define mission_id from context safely
                mission_id = context.get("session_id") or context.get("mission_id") or "default_user"
                fi = get_failure_index(mission_id)
                # Access internals carefully or use public API if available
                # Assuming get_insights() returns text descriptions of failures
                insights = fi.get_insights() if hasattr(fi, "get_insights") else []
                
                # Simple substring check (could be semantic in future)
                task_start = task.description[:50]
                if any(task_start in str(insight) for insight in insights):
                    logger.warning(f"Singularity: Known failure pattern detected for '{task_start}...'. Skipping split.")
                    return [task]
            except Exception as e:
                logger.warning(f"Singularity: Failure check failed: {e}")

        # UPGRADE 5: Memory Check
        # Have we decomposed this exact task before?
        try:
            # [DIAGNOSTIC] Ph.D. Level Integrity Check
            _ = task.type
        except AttributeError:
            import traceback
            traceback.print_exc()
            logger.error(f" [SINGULARITY] INTEGRITY FAILURE: ResearchTask object {task.id} missing 'type' attribute. Object vars: {vars(task) if hasattr(task, '__dict__') else 'No __dict__'}")
            # Structural fallback to prevent crash
            task.type = getattr(task, "task_type", "research")

        task_hash = self._hash_task(task.description)
        if task_hash in self._decomposition_memory:
            mem = self._decomposition_memory[task_hash]
            # If previously it yielded 0 children or failed, don't retry
            if mem.get("child_count", 0) == 0:
                 return [task]

        logger.info(f"Singularity Engine analyzing task for decomposition: {task.id} (Complexity: {complexity})")
        
        prompt = f"""
### SINGULARITY TASK ATOMIZER
Explode this task into a Massive Atomic Swarm of parallelizable sub-tasks.

TASK: {task.description}
OBJECTIVE: {context.get('research_question', 'UNDEFINED RESEARCH MISSION')}

OUTPUT FORMAT:
Return ONLY a raw JSON list of sub-tasks. 
Schema:
[
  {{
    "description": "Atomic action",
    "task_type": "research|analysis|validation",
    "decomposition_type": "exploration|falsification|survey",
    "required_agents": ["research_agent"|...],
    "priority": 5
  }}
]
"""

        try:
            result = await asyncio.to_thread(
                self.llm_manager.run,
                prompt=prompt,
                model=TASK_DECOMPOSITION_MODEL,
                # mode="agentic" -- DEPRECATED: explicitly passed model above
            )
            import json
            # Handle potential markdown wrapping
            depth = context.get("depth", 0)
        
            # [GODZILLA] Singularity Shield: Prevent infinite recursion
            if depth >= int(os.environ.get("SINGULARITY_MAX_DEPTH", "5")):
                logger.warning(f" [SINGULARITY] Depth limit reached ({depth}). Terminating decomposition.")
                return [task]
            
            # Handle different return types from LLM Manager (dict vs str)
            if isinstance(result, dict):
                text = result.get("text", result.get("content", "[]"))
            else:
                text = str(result)

            # [RIGOR] FLAW 32 FIX: Proactive Error Detection
            target_text = text.strip().lower()
            if not target_text or target_text == "error" or len(target_text) < 5:
                logger.critical(f" [SINGULARITY] LLM returned error/empty decomposition for {task.id}. ABORTING.")
                raise RuntimeError(f"Singularity Decomposition Failed: Task {task.id} could not be atomized.")

            # Clean text more aggressively (GODZILLA TIER)
            text = text.strip()
            
            # [UPGRADE] Strip Markdown Code Blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            # Robust JSON parsing (GODZILLA UPGRADE)
            try:
                from backend.utils.json_repair import repair_json
                # Attempt direct parse first for speed
                try:
                    parsed_data = json.loads(text)
                except:
                    parsed_data = repair_json(text)
                
                # Handle cases where repair_json returns a dict instead of a list
                if isinstance(parsed_data, dict):
                    if "tasks" in parsed_data:
                        sub_task_dicts = parsed_data["tasks"]
                    elif "sub_tasks" in parsed_data:
                        sub_task_dicts = parsed_data["sub_tasks"]
                    else:
                        # Wrap in list if it's a single task dictionary
                        sub_task_dicts = [parsed_data]
                elif isinstance(parsed_data, list):
                    sub_task_dicts = parsed_data
                else:
                    logger.error(f" [SINGULARITY] JSON parsing returned unexpected type: {type(parsed_data)}")
                    return [task]
                    
            except Exception as je:
                logger.error(f" [SINGULARITY] JSON parsing failed for task {task.id}: {je}")
                # Log a snippet of the malformed text for debugging
                logger.debug(f" [SINGULARITY] Malformed text: {text[:200]}...")
                # REJECTION RECOVERY: If decomposition fails, return original task instead of crashing
                return [task]

            # [HARDENING] Ensure we have a list to iterate over
            if not isinstance(sub_task_dicts, list):
                logger.warning(f" [SINGULARITY] LLM returned non-list decomposition: {type(sub_task_dicts)}. Returning original task.")
                return [task]

            
            if not sub_task_dicts:
                # Store memory: This task is atomic
                self._decomposition_memory[task_hash] = {"child_count": 0, "status": "atomic"}
                return [task]

            # UPGRADE 4: Redundancy Filter
            # Zero-token deduplication
            unique_tasks = []
            seen_descriptions: Set[str] = set()
            
            for d in sub_task_dicts:
                # [HARDENING] Skip malformed task entries (e.g. if it's a list of strings)
                if not isinstance(d, dict):
                    logger.warning(f" [SINGULARITY] Skipping non-dict task entry: {type(d)}")
                    continue
                    
                desc = d.get("description", "").strip()
                # Normalize key (DEEP DEDUPLICATION FIX: Increased from 60 to 200)
                key = desc[:200].lower()
                
                # Check for self-similarity (LLM repeating parent task)
                if desc == task.description:
                    continue
                    
                if key and key not in seen_descriptions:
                    seen_descriptions.add(key)
                    
                    # [CONTEXT PRESERVATION] If subtask description dropped specific parent target keywords, inject context
                    parent_kw = [w for w in ["6lzg", "2ajf", "6m0j", "skempi", "sars", "rbd", "ace2"] if w in task.description.lower()]
                    if parent_kw and not any(kw in desc.lower() for kw in parent_kw):
                        desc = f"{desc} (Target Context: {task.description})"

                    # [GODZILLA V68.9] Metadata Purge Protocol
                    # If this is a procedural task, we STRIP scientific metadata
                    # to prevent the 'Neural Leak' discovered in the V21.15 audit.
                    is_procedural = d.get("task_type") == "infrastructure"
                    
                    sub_payload = {
                        "assess_credibility": True,  # FORCE ON
                        "refine_query": True,        # FORCE ON
                        "depth": depth + 1,
                    }
                    
                    if not is_procedural and context.get("scientific_seeds"):
                        sub_payload["scientific_seeds"] = context.get("scientific_seeds", [])
                    
                    from backend.central_router_beast import CentralRouterBeast
                    alias_map = getattr(CentralRouterBeast, "SOVEREIGN_AGENT_ALIASES", {})
                    raw_agents = d.get("required_agents", task.required_agents) or ["research_agent"]
                    canonical_agents = []
                    for ag in raw_agents:
                        ag_clean = alias_map.get(str(ag).strip(), str(ag).strip())
                        if ag_clean not in canonical_agents:
                            canonical_agents.append(ag_clean)

                    # Create sub-task
                    new_task = ResearchTask(
                        id=f"{task.id}_sub{len(unique_tasks)}",
                        description=desc,
                        task_type=d.get("task_type", task.task_type),
                        priority=d.get("priority", task.priority),
                        required_agents=canonical_agents,
                        is_procedural=is_procedural,
                        payload=sub_payload
                    )
                    
                    # Tag metadata
                    if "decomposition_type" in d:
                        new_task.metadata["decomposition_type"] = d["decomposition_type"]
                    
                    unique_tasks.append(new_task)
            
            if not unique_tasks:
                return [task]

            # Store memory: Decomposition successful
            self._decomposition_memory[task_hash] = {
                "child_count": len(unique_tasks), 
                "status": "decomposed",
                "types": [t.metadata.get("decomposition_type") for t in unique_tasks]
            }

            logger.info(f"Singularity Engine decomposed task {task.id} into {len(unique_tasks)} atomic sub-tasks")
            return unique_tasks
            
        except Exception as e:
            logger.error(f"Singularity decomposition failed: {e}")
            return [task]

    def should_micro_orchestrate(self, task: ResearchTask) -> bool:
        """
        Determine if a task warrants micro-orchestration (spawning a child orchestrator).
        
        Triggers on:
        - Exploration-type tasks with high complexity
        - Tasks requiring deep multi-step reasoning
        """
        # Only micro-orchestrate exploration tasks
        meta = getattr(task, "metadata", None) or {}
        if not isinstance(meta, dict) or meta.get("decomposition_type") != "exploration":
            return False
        
        # Check complexity score
        complexity = self._complexity_score(task)
        if complexity >= 2:  # High complexity threshold
            logger.info(f" [MICRO] Task {task.id} qualifies for micro-orchestration (complexity={complexity})")
            return True
        
        # Check for explicit markers
        desc_lower = task.description.lower()
        if any(marker in desc_lower for marker in ["comprehensive analysis", "deep dive", "systematic review"]):
            logger.info(f" [MICRO] Task {task.id} qualifies for micro-orchestration (explicit marker)")
            return True
        
        return False

    async def execute_micro_orchestration(self, task: ResearchTask, session_id: str, depth: int = 1):
        """
        Spawns a temporary, specialized sub-orchestrator to solve an atomic problem.
        REAL IMPLEMENTATION: Recursive spawning.
        """
        logger.info(f"Singularity Engine spawning Micro-Orchestrator for task {task.id} (Depth {depth})")
        
        # FIX #12: Make max_depth configurable (was hardcoded to 2)
        import os
        max_depth = int(os.environ.get("SINGULARITY_MAX_DEPTH", "3"))
        
        # 1. Safety Limit: Prevent infinite recursion
        if depth > max_depth:
            logger.warning(f"Singularity: Max depth reached ({depth} > {max_depth}). Falling back to simple execution.")
            return {"status": "skipped_max_depth", "summary": f"Recursion limit reached (max={max_depth})."}

        # 2. Spawn Child Orchestrator
        try:
            # Import here to avoid circular dependency at module level
            from backend.orchestration.deep_research_orchestrator import DeepResearchOrchestrator
            
            # The child orchestrator is "short-lived" (max_cycles=1)
            # Use safe initialization
            child_orchestrator = DeepResearchOrchestrator(
                research_question=task.description,
                domain="general", # Inherit or generic
                max_cycles=1,     # One-shot solver
                max_runtime_hours=0.1, # 6 minutes max
                router=self.router, # CRITICAL: Inject parent router
                llm_manager=self.llm_manager, # CRITICAL: Inject parent LLM
                recursion_depth=depth + 1 # FIX: Pass depth to prevent infinite recursion
            )
            
            # 3. Execute Async
            logger.info(f"Singularity: Child Orchestrator {child_orchestrator.session_id} STARTING.")
            await child_orchestrator.run_async()
            
            # 4. Harvest Results safely (unwrap nested dicts without crashing on None/str)
            findings = []
            for f in (child_orchestrator.session.findings or []):
                if not isinstance(f, dict):
                    findings.append(str(f))
                    continue
                curr = f.get("result")
                while isinstance(curr, dict) and ("result" in curr or "results" in curr):
                    nxt = curr.get("result") if "result" in curr else curr.get("results")
                    if nxt is None or nxt is curr:
                        break
                    curr = nxt
                summary_obj = curr.get("summary", curr) if isinstance(curr, dict) else curr
                if isinstance(summary_obj, dict) and "claim_leaderboard" in summary_obj:
                    findings.append(json.dumps(summary_obj["claim_leaderboard"]))
                elif isinstance(curr, dict) and ("summary" in curr or "text" in curr):
                    findings.append(str(curr.get("summary") or curr.get("text") or ""))
                elif f.get("content") or f.get("summary"):
                    findings.append(str(f.get("content") or f.get("summary")))

            summary = "\n".join([s for s in findings if s])
            
            logger.info(f"Singularity: Child Orchestrator {child_orchestrator.session_id} FINISHED. {len(findings)} findings.")
            
            # UPGRADE 5: Update memory with outcome
            task_hash = self._hash_task(task.description)
            if task_hash not in self._decomposition_memory:
                self._decomposition_memory[task_hash] = {}
            self._decomposition_memory[task_hash]["outcome"] = "success" if findings else "empty"
            
            return {
                "status": "success", 
                "summary": summary, 
                "child_session_id": child_orchestrator.session_id
            }

        except Exception as e:
            logger.error(f"Singularity Micro-Orchestration FAILED: {e}")
            
            # HYDRA: Attempt Recovery?
            # If we are not too deep, maybe we return a "Partial Failure" signal 
            # that allows the parent to trigger re_decompose.
            # For now, we return error status.
            return {"status": "error", "error": str(e)}

# Alias for backward compatibility
Singularity = SingularityEngine

# Global Singularity Engine
_singularity: Optional[SingularityEngine] = None

def get_singularity(orchestrator_factory: Any = None, llm_manager: Any = None, router: Any = None) -> SingularityEngine:
    global _singularity
    if _singularity is None:
        _singularity = SingularityEngine(orchestrator_factory, llm_manager, router)
    
    # FORCED INJECTION: Always update if provided, even if already set
    # This prevents the 'No LLM Manager' warning when orchestrators are re-initialized
    if llm_manager:
        _singularity.llm_manager = llm_manager
    if orchestrator_factory:
        _singularity.orchestrator_factory = orchestrator_factory
    if router:
        _singularity.router = router
        
    return _singularity
