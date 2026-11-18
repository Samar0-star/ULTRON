from pathlib import Path
import asyncio
import logging
import os
import time
import json
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from backend.core.events.event_bus import events
from backend.core.planning.plan_creator import ResearchTask
from backend.config_beast import beast_config
from backend.core.skill_injector import get_expert_system

logger = logging.getLogger(__name__)

class ConsensusEngine:
    """
    Verifies findings across multiple agents with domain expertise.
    """
    def __init__(self, llm_manager: Any = None, expert_system: Any = None):
        self.llm_manager = llm_manager
        self.expert_system = expert_system or get_expert_system()

    async def verify_finding(self, finding: Dict[str, Any], goal: str, domain: str = "general") -> bool:
        """
        Ask the LLM to verify if the finding supports the goal.
        REAL IMPLEMENTATION: Now uses surgical skill injection for the tribunal and quantitative validation.
        """
        debug_mode = os.getenv("GODZILLA_DEBUG_MODE", "false").lower() == "true"
        if not self.llm_manager:
            logger.error(" [CRITICAL] ConsensusEngine: No LLM manager available. Rejecting finding for safety.")
            return False # STRICT FALLBACK

        # P0-37: Unwrap nested router/agent envelopes ('result' -> 'result' -> 'summary'/'text'/'content')
        res_obj = finding.get("result", finding) if isinstance(finding, dict) else finding
        if isinstance(res_obj, dict) and "result" in res_obj and isinstance(res_obj["result"], dict):
            res_obj = res_obj["result"]
        summary = ""
        if isinstance(res_obj, dict):
            summary = str(res_obj.get("summary") or res_obj.get("text") or res_obj.get("findings") or "")
        if not summary and isinstance(finding, dict):
            summary = str(finding.get("content") or finding.get("summary") or finding.get("text") or "")
        if not summary.strip():
            return False

        base_prompt = f"""
+------------------------------------------------------------------------------+
|  CONSENSUS TRIBUNAL - TRUTH VERIFICATION ENGINE                             |
+------------------------------------------------------------------------------+

RESEARCH GOAL: {goal}

FINDING UNDER REVIEW:
{summary[:10000]}

Evaluate the finding and return a JSON object with the following fields:
- "verdict": "YES" (approved) or "NO" (rejected).
- "metrics_found": A dictionary of extracted numeric metrics (e.g. {{"effect_size": 1.25, "p_value": 0.004, "confidence": 0.95}} or domain-specific quantitative values). Use float values for all numbers.
- "reasoning": Brief reasoning.

Return ONLY valid raw JSON."""

        # [GODZILLA UPGRADE] Inject Meta Skills for critical tribunal thinking
        prompt = await self.expert_system.inject_meta_skills(
            base_prompt, 
            query=f"adversarial review critical thinking for {goal}",
            domain=domain
        )

        try:
            result = await asyncio.to_thread(
                self.llm_manager.run,
                prompt=prompt,
                mode="fast", # Use fast model for verification
                temperature=0.1
            )
            text = result.get("text", "").strip()
            
            # Direct JSON Parser
            from backend.utils.json_repair import repair_json
            parsed = None
            try:
                # Find JSON bounds
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    json_str = text[start:end+1]
                    parsed = repair_json(json_str)
                    if not parsed:
                        parsed = json.loads(json_str)
            except Exception as e:
                logger.warning(f" [CONSENSUS] Failed to parse JSON response: {e}")

            if not parsed or not isinstance(parsed, dict):
                import re
                # Robust extraction for structured or unstructured verdict statements
                match_explicit = re.search(r'(?i)(?:"verdict"|verdict)\s*[:=]\s*["\']?(YES|NO)["\']?', text)
                if match_explicit:
                    verdict = match_explicit.group(1).upper()
                else:
                    # Fallback to isolated word boundary match
                    has_yes = bool(re.search(r'\bVERDICT\s*:\s*YES\b|\bVERDICT\s+YES\b', text, re.I))
                    has_no = bool(re.search(r'\bVERDICT\s*:\s*NO\b|\bVERDICT\s+NO\b', text, re.I))
                    if has_yes and not has_no:
                        verdict = "YES"
                    elif has_no:
                        verdict = "NO"
                    else:
                        # Fail-closed for consensus safety if completely unparseable
                        verdict = "NO"
                metrics = {}
            else:
                verdict = str(parsed.get("verdict", "NO")).strip().upper()
                metrics = parsed.get("metrics_found", {})
                if not isinstance(metrics, dict):
                    metrics = {}

            # Quantitative Metric Gate Checks
            goal_lower = goal.lower()
            if verdict == "YES":
                # Check accuracy drop constraints only for explicit model accuracy goals
                if any(x in goal_lower for x in ["accuracy drop", "accuracy loss", "acc drop", "acc loss"]) and any(x in goal_lower for x in ["<0.5%", "less than 0.5%", "under 0.5%"]):
                    for key in ["accuracy_drop", "accuracy_loss", "acc_drop", "acc_loss"]:
                        val = metrics.get(key)
                        if val is not None:
                            if val > 0.005:
                                logger.warning(f" [QUANTITATIVE GATE] Verdict overridden to NO: accuracy drop ({val}) exceeds goal constraint (0.005)")
                                verdict = "NO"
                                break

                # Check FLOPs reduction constraints only for explicit compute reduction goals
                if any(x in goal_lower for x in ["flops reduction", "parameter reduction", "pruning reduction", "compression reduction"]) and "60%" in goal_lower:
                    for key in ["flops_reduction", "parameter_reduction", "reduction", "flops_reduced", "r"]:
                        val = metrics.get(key)
                        if val is not None:
                            if val < 0.60:
                                logger.warning(f" [QUANTITATIVE GATE] Verdict overridden to NO: flops reduction ({val}) is below goal constraint (0.60)")
                                verdict = "NO"
                                break

            # [GODZILLA NUDITY]
            if debug_mode:
                logger.info(f" [CONSENSUS_STRICT] VERDICT: {verdict} | SOURCE: {text[:200]}")

            return verdict == "YES"
        except Exception as e:
            logger.error(f" [ERROR] CONSENSUS CRITICAL FAILURE: {e}")
            return False 

@dataclass
class SwarmMember:
    agent_id: str
    status: str
    current_task: Optional[str] = None

class SwarmManager:
    """
    PROJECT GODZILLA: PHASE 31 - MASSIVE PARALLELISM
    Manages a swarm of up to 200 concurrent micro-agents.
    Uses a Worker Pool pattern with an asyncio Queue.
    """
    def __init__(self, max_parallel: int = 50, router: Any = None, llm_manager: Any = None):
        self.max_parallel = max_parallel # Can be scaled to 200
        self.router = router
        self.llm_manager = llm_manager
        self.expert_system = get_expert_system()
        self.consensus_engine = ConsensusEngine(llm_manager=llm_manager, expert_system=self.expert_system)
        
        # Rate Limiting
        # We allow a burst of concurrent requests, but we might want to throttle logic inside the worker
        self._token_bucket = None

    @property
    def token_bucket(self) -> asyncio.Semaphore:
        if self._token_bucket is None:
            try:
                self._token_bucket = asyncio.Semaphore(self.max_parallel * 2)
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop_policy().get_event_loop()
                except Exception:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                self._token_bucket = asyncio.Semaphore(self.max_parallel * 2)
        return self._token_bucket

    @token_bucket.setter
    def token_bucket(self, value: Any):
        self._token_bucket = value 

    async def execute_swarm(
        self, 
        tasks: List[ResearchTask], 
        session_id: str,
        mission_id: str,
        on_event: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Legacy wrapper for execute_swarm_stream.
        Collects all results into a list (Memory usage spike warning).
        """
        results = []
        async for result in self.execute_swarm_stream(tasks, session_id, on_event):
            results.append(result)
        return results

    async def execute_swarm_stream(
        self, 
        tasks: List[ResearchTask], 
        session_id: str,
        on_event: Optional[Any] = None
    ):
        """
        [GODZILLA OPTIMIZATION]
        Yields results as they are completed. 
        Zero-accumulation in SwarmManager RAM.
        """
        logger.info(f" [SWARM] Deploying Godzilla Swarm: {len(tasks)} tasks with {self.max_parallel} workers")
        
        local_queue = asyncio.Queue()
        results_queue = asyncio.Queue() # For streaming back to caller
        
        for task in tasks:
            local_queue.put_nowait(task)
            
        num_workers = min(self.max_parallel, len(tasks))
        workers = []
        worker_tasks_map = {}
        active_tasks = {}
        for i in range(num_workers):
            worker_id = f"Agent-{i+1:03d}"
            t = asyncio.create_task(
                self._worker(worker_id, session_id, local_queue, results_queue, on_event, active_tasks)
            )
            workers.append(t)
            worker_tasks_map[worker_id] = t
            
        # Monitor progress with Serial Rescue Fallback
        tasks_remaining = len(tasks)
        scavenged_task_ids = set()
        while tasks_remaining > 0:
            try:
                result = await asyncio.wait_for(results_queue.get(), timeout=10.0) # check every 10s
                results_queue.task_done()
                if isinstance(result, dict) and result.get("status") == "cancelled" and result.get("task_id") in scavenged_task_ids:
                    scavenged_task_ids.discard(result.get("task_id"))
                    continue
                yield result
                tasks_remaining -= 1
            except asyncio.TimeoutError:
                now = time.time()
                for w_id, (start_time, hung_task) in list(active_tasks.items()):
                    if now - start_time > 900.0:
                        logger.warning(f" [SCAVENGER] Worker {w_id} hung. Cancelling and re-enqueuing task {hung_task.id}...")
                        scavenged_task_ids.add(hung_task.id)
                        t = worker_tasks_map.get(w_id)
                        if t and not t.done():
                            t.cancel()
                        
                        # Re-enqueue
                        local_queue.put_nowait(hung_task)
                        active_tasks.pop(w_id, None)
                        
                        # Re-create worker
                        new_t = asyncio.create_task(
                            self._worker(w_id, session_id, local_queue, results_queue, on_event, active_tasks)
                        )
                        workers.append(new_t)
                        worker_tasks_map[w_id] = new_t
                if all(w.done() for w in workers) and results_queue.empty() and local_queue.empty():
                    logger.warning(" [SCAVENGER] All workers terminated with no remaining queued items; exiting monitor loop.")
                    break

        # Final Shutdown
        for w in workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        
        logger.info(f" [SUCCESS] Swarm Mission Complete.")

    async def _execute_task_direct(self, task: ResearchTask, session_id: str, on_event: Optional[Any]):
        """Direct, non-parallel execution for rescue operations. Hardened with Consensus Engine."""
        target_agent = task.required_agents[0] if task.required_agents else "research_agent"
        payload = getattr(task, "payload", None) or {}
        meta = getattr(task, "metadata", None) or {}
        task_domain = (
            getattr(task, "domain", None)
            or (payload.get("domain") if isinstance(payload, dict) else None)
            or (meta.get("domain") if isinstance(meta, dict) else None)
            or os.environ.get("ULTRON_DOMAIN", "general")
        )
        
        if on_event:
            try:
                if asyncio.iscoroutinefunction(on_event):
                    await on_event("task_start", {"task_id": task.id, "worker_id": "RESCUE_AGENT"})
                else:
                    on_event("task_start", {"task_id": task.id, "worker_id": "RESCUE_AGENT"})
            except Exception as e:
                logger.warning(f"on_event callback failed: {e}")
            
        await events.emit(
            event_type="SWARM_TASK_STARTED",
            payload={"session_id": session_id, "task_id": task.id, "worker_id": "RESCUE_AGENT", "description": getattr(task, "requirements", f"Task {task.id}")},
            source="SwarmManager"
        )
            
        route_args = {
            "agent_name": target_agent,
            "payload": payload,
            "context": {
                "orchestrator": "DeepResearch",
                "task_id": task.id,
                "session_id": session_id,
                "DOMAIN": task_domain
            }
        }
        
        try:
            res = await self.router.route(task.description, **route_args)
            inner_res = res.get("result", res) if isinstance(res, dict) else res
            is_success = isinstance(inner_res, dict) and inner_res.get("status") in ("success", "completed")
            
            # [GODZILLA RIGOR] Hardened Rescue: Rescued tasks MUST still pass Judgment Day
            verified = True
            if self.consensus_engine and is_success:
                goal = task.description
                verified = await self.consensus_engine.verify_finding(res, goal, domain=task_domain)
                
                if not verified:
                     logger.warning(f" [RESCUE_JUDGMENT] Rescued finding REJECTED for task {task.id}")
                     return {
                         "task_id": task.id, 
                         "status": "rejected", 
                         "error": "Rescued finding failed consensus (Low Rigor/Hallucination)"
                     }

            return {"task_id": task.id, "status": "completed", "result": res}
        except Exception as e:
            logger.error(f" [RESCUE_FAILURE] Serial rescue failed for {task.id}: {e}")
            return {"task_id": task.id, "status": "error", "error": str(e)}

    async def _worker(self, worker_id: str, session_id: str, queue: asyncio.Queue, results_queue: asyncio.Queue, on_event: Optional[Any] = None, active_tasks: Optional[Dict] = None):
        """
        Micro-Agent Worker Loop.
        Pulls from Queue -> Executes -> Pushes Result.
        """
        logger.debug(f"{worker_id} reporting for duty.")
        debug_mode = os.getenv("GODZILLA_DEBUG_MODE", "false").lower() == "true"
        
        # Lightweight staggered startup jitter (configurable via SWARM_STARTUP_JITTER_MAX)
        import random
        max_jitter = float(os.environ.get("SWARM_STARTUP_JITTER_MAX", "0.15"))
        if max_jitter > 0:
            await asyncio.sleep(random.uniform(0.01, max_jitter))

        while True:
            task = None
            try:
                # Wait for a task. If cancelled here, no task is taken, so no task_done needed.
                task = await queue.get()
            except asyncio.CancelledError:
                logger.debug(f"{worker_id} cancelled while waiting for task.")
                break # Exit loop if cancelled while waiting for a task
            
            # [GODZILLA RECOVERY] RESTORING CORE EXECUTION LOGIC
            try:
                # Execute Task
                try:
                    logger.debug(f"{worker_id} picked up task: {task.id}")
                    if active_tasks is not None:
                        active_tasks[worker_id] = (time.time(), task)
                    
                    # [GODZILLA NUDITY]
                    if debug_mode and task:
                        logger.debug(f"[NUDITY] [SWARM_TASK_START] {worker_id} -> {task.id}")
                        logger.debug(f"[NUDITY] [TASK_PAYLOAD]: {json.dumps(getattr(task, 'payload', {}))}")

                    if on_event:
                        try:
                            if asyncio.iscoroutinefunction(on_event):
                                await on_event("task_start", {"task_id": task.id, "worker_id": worker_id})
                            else:
                                on_event("task_start", {"task_id": task.id, "worker_id": worker_id})
                        except Exception as e:
                            logger.warning(f"on_event callback failed: {e}")

                    # Emit EventBus event
                    await events.emit(
                        event_type="SWARM_TASK_STARTED",
                        payload={"session_id": session_id, "task_id": task.id, "worker_id": worker_id, "description": getattr(task, "requirements", f"Task {task.id}")},
                        source="SwarmManager"
                    )

                    # Determine target agent (canonicalize legacy micro-agents to 2027 Sovereign Agents)
                    target_agent = None
                    if hasattr(task, "required_agents") and task.required_agents:
                        target_agent = task.required_agents[0]
                    sovereign_map = {
                        "web_search_agent": "research_agent",
                        "doc_reader_agent": "research_agent",
                        "summarizer_agent": "research_agent",
                        "qa_agent": "research_agent",
                        "data_analyzer_agent": "experiment_agent",
                        "ml_model_builder_agent": "experiment_agent",
                        "fact_checker_agent": "red_team_agent",
                    }
                    if target_agent in sovereign_map:
                        target_agent = sovereign_map[target_agent]
                    elif not target_agent and getattr(task, "task_type", "") == "experiment":
                        target_agent = "experiment_agent"

                    # [GODZILLA CONTEXT BRIDGE]
                    # Ensure scientific seeds are converted to agent-readable text if missing
                    payload = getattr(task, "payload", None) or {}
                    meta = getattr(task, "metadata", None) or {}
                    task_domain = (
                        getattr(task, "domain", None)
                        or (payload.get("domain") if isinstance(payload, dict) else None)
                        or (meta.get("domain") if isinstance(meta, dict) else None)
                        or os.environ.get("ULTRON_DOMAIN", "general")
                    )
                    if not payload.get("text") and payload.get("scientific_seeds"):
                        seeds = payload.get("scientific_seeds")
                        if isinstance(seeds, list):
                            payload["text"] = "\n\n---\n\n".join([str(s) for s in seeds])
                            logger.debug(f" [BRIDGE] Injected {len(seeds)} scientific seeds into task {task.id} payload.")

                    # [TITAN MANDATE] Inject Physical Tool Schemas and Requirements
                    if not payload.get("requirements"):
                        payload["requirements"] = task.description
                        
                    payload["MANDATORY_TOOL_SCHEMAS"] = {
                        "experiment_agent": {"required": ["statement"], "help": "Provide hypothesis statement for experimental validation."},
                        "mhd-modeling": {"required": ["query"], "help": "Use 'query' for MHD calculations."},
                        "grad-shafranov-solvers": {"required": ["query"], "help": "Use 'query' for equilibrium solving."}
                    }

                    # EXECUTE WITH RATE LIMIT PROTECTION
                    async with self.token_bucket:
                        if self.router:
                            route_args = {
                                "agent_name": target_agent,
                                "orchestrator": "DeepResearch",
                                "payload": payload,
                                "context": {
                                    "orchestrator": "DeepResearch",
                                    "research_session": True,
                                    "task_id": task.id, 
                                    "task_type": task.task_type,
                                    "required_tools": task.required_tools,
                                    "required_skills": getattr(task, "required_skills", []),
                                    "session_id": session_id, 
                                    "DOMAIN": task_domain
                                }
                            }
                            
                            if asyncio.iscoroutinefunction(self.router.route):
                                result = await self.router.route(task.description, **route_args)
                            else:
                                # Synchronous fallback
                                result = await asyncio.to_thread(self.router.route, task.description, **route_args)
                        else:
                            # [STOP] GODZILLA RIGOR: FATAL INFRASTRUCTURE ERROR
                            msg = f"FATAL_ROUTING_ERROR: SwarmManager has no router! Cannot execute task {task.id}"
                            logger.critical(f" [FATAL] {msg}")
                            raise RuntimeError(msg)
                            
                    # [TITAN 3] JUDGMENT DAY: Consensus Engine Verification
                    # P0-37: Unwrap router envelope ('result' -> 'result') when checking execution status
                    verified = True
                    inner_res = result.get("result", result) if isinstance(result, dict) else result
                    is_success = isinstance(inner_res, dict) and inner_res.get("status") in ("success", "completed")
                    if self.consensus_engine and is_success:
                        goal = task.description
                        verified = await self.consensus_engine.verify_finding(result, goal, domain=task_domain)
                        
                        if not verified:
                             logger.warning(f" [JUDGMENT] Finding REJECTED by Consensus Engine for task {task.id}")
                             result["status"] = "rejected"
                             result["rejection_reason"] = "Consensus Engine Verification Failed (Hallucination/Irrelevance)"
                    
                    # Store Result via Streaming Queue
                    await results_queue.put({
                        "task_id": task.id,
                        "worker_id": worker_id, 
                        "result": result,
                        "status": "completed" if verified else "rejected"
                    })
                    
                    if on_event:
                        try:
                            if asyncio.iscoroutinefunction(on_event):
                                await on_event("task_complete", {"task_id": task.id, "worker_id": worker_id, "result": result})
                            else:
                                on_event("task_complete", {"task_id": task.id, "worker_id": worker_id, "result": result})
                        except Exception as e:
                            logger.warning(f"on_event callback failed: {e}")

                    await events.emit(
                        event_type="SWARM_TASK_COMPLETED",
                        payload={"session_id": session_id, "task_id": task.id, "worker_id": worker_id},
                        source="SwarmManager"
                    )

                except Exception as e:
                    logger.error(f"{worker_id} failed task {task.id}: {e}")
                    await results_queue.put({
                        "task_id": task.id,
                        "worker_id": worker_id, 
                        "error": str(e),
                        "status": "failed"
                    })
                    if on_event:
                        try:
                            if asyncio.iscoroutinefunction(on_event):
                                await on_event("task_fail", {"task_id": task.id, "worker_id": worker_id, "error": str(e)})
                            else:
                                on_event("task_fail", {"task_id": task.id, "worker_id": worker_id, "error": str(e)})
                        except Exception as e:
                            logger.warning(f"on_event callback failed: {e}")
            
            except asyncio.CancelledError:
                logger.debug(f"{worker_id} cancelled during task execution.")
                # We picked the task, so we MUST notify the results_list before marking task_done
                # or the orchestrator will wait forever.
                await results_queue.put({
                    "task_id": task.id if task else "unknown",
                    "worker_id": worker_id,
                    "error": "Task cancelled (worker shutdown or timeout)",
                    "status": "cancelled"
                })
                raise 
            except BaseException as e:
                # Catch-all for extreme failures (KeyboardInterrupt, etc.)
                logger.critical(f"{worker_id} encountered critical crash: {e}")
                if task:
                    await results_queue.put({
                        "task_id": task.id,
                        "worker_id": worker_id,
                        "error": f"Critical worker crash: {str(e)}",
                        "status": "crashed"
                    })
                raise
            finally:
                if active_tasks is not None:
                    active_tasks.pop(worker_id, None)
                if task:
                    # Mark task as done regardless of success/failure/cancellation
                    queue.task_done()

# Factory
_swarm_manager: Optional[SwarmManager] = None

def get_swarm_manager(router=None, llm_manager=None) -> SwarmManager:
    global _swarm_manager
    if _swarm_manager is None:
        max_agents = beast_config.orchestration.max_parallel_agents
        _swarm_manager = SwarmManager(max_parallel=max_agents, router=router, llm_manager=llm_manager)
    else:
        # [GODZILLA FIX] Force-update existing singleton if new components provided
        if router:
            _swarm_manager.router = router
            logger.info(" SwarmManager: Router updated in existing singleton.")
        if llm_manager:
            _swarm_manager.llm_manager = llm_manager
            _swarm_manager.consensus_engine.llm_manager = llm_manager
            logger.info(" SwarmManager: LLMManager updated in existing singleton.")
            
    return _swarm_manager
