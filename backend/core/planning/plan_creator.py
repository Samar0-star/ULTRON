"""
Plan Creator for ULTRON
===================================

Generates strategic research plans with exploration/exploitation balance.
Creates task lists for multi-cycle autonomous research.
"""

import json
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set
import asyncio
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ResearchTask:
    """A single task in the research plan"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: str = "research"  # primary field
    type: str = "research"      # [TITAN V176.2] DUAL BINDING FOR COMPATIBILITY
    description: str = ""
    expected_output: str = ""
    required_tools: List[str] = field(default_factory=list)
    required_agents: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list) # NEW: For Expert Systems
    is_exploration: bool = False  # True = explore new directions, False = exploit known paths
    priority: int = 5  # 1 = highest, 10 = lowest
    estimated_minutes: float = 30.0
    dependencies: List[str] = field(default_factory=list)  # IDs of tasks this depends on
    target_hypothesis_ids: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, skipped
    is_procedural: bool = False  # [GODZILLA] True = administrative/technical, False = scientific discovery
    metadata: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict) # [TITAN 3] Payload Support

    @property
    def agent(self) -> Optional[str]:
        """Compatibility alias for the primary required agent."""
        return self.required_agents[0] if self.required_agents else None

    @agent.setter
    def agent(self, value: str):
        """Allow setting the primary agent."""
        if not self.required_agents:
            self.required_agents = [value]
        else:
            self.required_agents[0] = value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (V177.0 Stable)"""
        return {
            "id": self.id,
            "task_type": self.task_type,
            "type": self.type,
            "description": self.description,
            "expected_output": self.expected_output,
            "required_tools": self.required_tools,
            "required_agents": self.required_agents,
            "required_skills": self.required_skills,
            "is_exploration": self.is_exploration,
            "priority": self.priority,
            "estimated_minutes": self.estimated_minutes,
            "dependencies": self.dependencies,
            "target_hypothesis_ids": self.target_hypothesis_ids,
            "status": self.status,
            "is_procedural": self.is_procedural,
            "metadata": self.metadata,
            "payload": self.payload
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchTask":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ResearchPlan:
    """A complete research plan for one cycle"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cycle: int = 1
    research_objective: str = ""
    tasks: List[ResearchTask] = field(default_factory=list)
    rationale: str = ""
    exploration_ratio: float = 0.3  # Dynamic per cycle
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "draft"  # draft, approved, executing, completed, revised
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cycle": self.cycle,
            "research_objective": self.research_objective,
            "tasks": [t.to_dict() for t in self.tasks],
            "rationale": self.rationale,
            "exploration_ratio": self.exploration_ratio,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "task_count": len(self.tasks),
            "estimated_total_minutes": sum(t.estimated_minutes for t in self.tasks)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchPlan":
        tasks = [ResearchTask.from_dict(t) for t in data.get("tasks", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            cycle=data.get("cycle", 1),
            research_objective=data.get("research_objective", ""),
            tasks=tasks,
            rationale=data.get("rationale", ""),
            exploration_ratio=data.get("exploration_ratio", 0.3),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            status=data.get("status", "draft")
        )
    
    def get_pending_tasks(self) -> List[ResearchTask]:
        """Get tasks that haven't been executed yet"""
        return [t for t in self.tasks if t.status == "pending"]
    
    def get_ready_tasks(self, completed_external_ids: Optional[Set[str]] = None) -> List[ResearchTask]:
        """
        Get tasks with all dependencies satisfied.
        
        Args:
            completed_external_ids: IDs of tasks completed in PREVIOUS cycles.
        """
        completed = {t.id for t in self.tasks if t.status == "completed"}
        if completed_external_ids:
            completed.update(completed_external_ids)
            
        return [
            t for t in self.tasks
            if t.status == "pending" and all(dep in completed for dep in t.dependencies)
        ]


class PlanCreator:
    """
    Strategic research planning agent.
    
    Generates task lists per cycle that advance the research objective
    while balancing exploration of new directions with exploitation
    of promising findings.
    """
    
    def __init__(
        self,
        llm_manager=None,
        default_num_tasks: int = 10
    ):
        """
        Initialize Plan Creator.
        
        Args:
            llm_manager: LLM manager for plan generation
            default_num_tasks: Default number of tasks per cycle
        """
        self.llm_manager = llm_manager
        self.default_num_tasks = default_num_tasks
        self.skill_selector = None
        
        # Lazy load llm_manager
        if self.llm_manager is None:
            try:
                from backend.llm_manager import llm_manager
                self.llm_manager = llm_manager
            except ImportError:
                logger.warning("LLM manager not available for plan creation")
        
        # Initialize Skill Selector
        if self.llm_manager:
            try:
                from backend.core.llm_skill_selector import LLMSkillSelector
                from backend.core.skill_injector import get_expert_system
                self.skill_selector = LLMSkillSelector(self.llm_manager, get_expert_system())
            except Exception as e:
                logger.warning(f"Failed to initialize LLMSkillSelector: {e}")
        
        logger.info(f"PlanCreator initialized (default_tasks={default_num_tasks})")
    
    def _get_exploration_ratio(self, cycle: int, total_cycles: int = 20) -> float:
        """
        Calculate dynamic exploration ratio using a Damped Sine Wave (Sawtooth).
        
        Rationale:
        - Research is not linear; it requires periodic "re-exploration" (Simulated Annealing).
        - Cycle 1-4: High Exploration (0.8 -> 0.4)
        - Cycle 5+: Oscillates between 0.2 (Deep Exploitation) and 0.5 (New Discovery).
        """
        if cycle <= 3:
            # Initial "Shock & Awe" Phase
            return max(0.4, 0.9 - (cycle * 0.15))
            
        # ADAPTIVE SCALING: Adjust wave period based on run duration
        period = 10 if total_cycles < 50 else 25
        
        # Long-run oscillation
        phase = (cycle - 3) % period
        
        # Discovery bursts happen in first 30% of the period
        if phase < (period * 0.3): 
            return 0.5  # Mini-Discovery Burst
        else:
            return 0.2  # Deep Execution/Validation
    
    async def create_plan(
        self,
        research_objective: str,
        context: Dict[str, Any],
        cycle: int = 1,
        num_tasks: Optional[int] = None,
        temperature: Optional[float] = None,     
        mode: str = "research"
    ) -> ResearchPlan:
        """
        Generate strategic research plan.
        """
        num_tasks = num_tasks or self.default_num_tasks
        context = context or {}
        total_cycles = context.get("total_cycles", 20)
        
        # Use dynamic temperature if provided, else use cyclical schedule
        if temperature is not None:
            exploration_ratio = temperature
        else:
            exploration_ratio = self._get_exploration_ratio(cycle, total_cycles)
        
        logger.info(f"Creating plan for cycle {cycle} (tasks={num_tasks}, exploration={exploration_ratio:.2f}, mode={mode})")
        
        if not self.llm_manager:
            raise RuntimeError("[HARD ABORT] LLM generation failed - cannot produce valid planning. Manual intervention required.")
        
        # Build planning prompt
        prompt = await self._build_planning_prompt(
            research_objective=research_objective,
            context=context,
            cycle=cycle,
            num_tasks=num_tasks,
            exploration_ratio=exploration_ratio,
            mode=mode
        )
        
        try:
            # F-68: Race Condition Fix - Deepcopy mutable context before passing to thread
            import copy
            safe_context = {
                "findings": context.get("findings", [])[:], # List copy
                "hypotheses": context.get("hypotheses", [])[:], # List copy
                "total_cycles": context.get("total_cycles", 20),
                "papers_read": context.get("papers_read", 0)
            }

            # Use asyncio.to_thread to prevent blocking the event loop
            # [GODZILLA SHIELD] Use source="plan_creator" to trigger high-rigor shielding
            result = await asyncio.to_thread(
                self.llm_manager.run,
                prompt=prompt,
                mode="stable_code",  # Use OpenAI for structured output
                temperature=0.4,
                max_tokens_override=None,
                source="plan_creator"
            )
            
            # Extract text safely from dict or str
            if isinstance(result, dict):
                text = result.get("text", result.get("content", ""))
            else:
                text = str(result)
            
            plan = self._parse_plan_response(text, cycle, exploration_ratio, research_objective, num_tasks)
            plan.research_objective = research_objective
            
            # --- SELF-CORRECTION LOOP (only when explicitly requested or when plan is empty/invalid) ---
            if self.llm_manager and (not plan.tasks or context.get("enable_self_critique", False)):
                refined_plan = await self._critique_and_refine(plan, research_objective, context, mode)
                if refined_plan and refined_plan.tasks:
                    plan = refined_plan
                    logger.info("Plan refined by Self-Correction Loop")

            # GOVERNANCE CHECK: Enforce Reading Policy (Auto-Correction)
            if mode == "discovery":
                total_cycles = context.get("total_cycles", 20)
                _, _, reading_policy = self._determine_discovery_phase(cycle, total_cycles)
                
                if reading_policy == "FORBIDDEN":
                    # Filter out any reading tasks
                    plan.tasks = [
                        t for t in plan.tasks 
                        if "deep_paper_reader" not in t.required_tools 
                        and "reading" not in t.description.lower()
                    ]
            elif mode in ["research", "deep_research"] and context.get("enforce_bulk_reading", False):
                # Optional batched reading when explicitly enabled
                paper_count = context.get("papers_read", 0)
                reading_tasks = [t for t in plan.tasks if "deep_paper_reader" in t.required_tools or "research_agent" in t.required_agents]
                
                if paper_count < 2000 and len(reading_tasks) == 0:
                    logger.info(" GOVERNANCE: Injecting Batched Reading Task (Sovereign ResearchAgent)")
                    batch_task = ResearchTask(
                        id=f"autogen_read_{cycle}",
                        task_type="research",
                        description=f"Deep Read Batch: {research_objective} (50 papers)",
                        expected_output="Extracted insights from 50 PDFs",
                        required_tools=["deep_paper_reader"],
                        required_agents=["research_agent"],
                        priority=1,
                        estimated_minutes=60
                    )
                    plan.tasks.insert(0, batch_task)

            logger.info(f"Created plan with {len(plan.tasks)} tasks")
            
            # [GODZILLA RESCUE] Hard-coded Plan Injection
            if not plan.tasks:
                logger.critical(" [RESCUE] LLM returned 0 tasks. Injecting Masterpiece Roadmap.")
                plan.tasks = [
                    ResearchTask(id=f"rescue_{cycle}_1", task_type="research", description=f"Extract empirical data regarding {research_objective}.", required_tools=["pubmed_search", "arxiv_search"], priority=1, estimated_minutes=30),
                    ResearchTask(id=f"rescue_{cycle}_2", task_type="analysis", description=f"Analyze datasets for {research_objective}.", required_tools=["code_executor"], priority=2, estimated_minutes=30),
                    ResearchTask(id=f"rescue_{cycle}_3", task_type="experiment", description="Execute modeling or simulation for the objective.", required_tools=["experiment_agent"], required_agents=["experiment_agent"], priority=3, estimated_minutes=60, dependencies=[f"rescue_{cycle}_1", f"rescue_{cycle}_2"]),
                    ResearchTask(id=f"rescue_{cycle}_4", task_type="synthesis", description="Generate high-rigor discovery report with falsification metrics.", required_tools=["report_generator"], priority=4, estimated_minutes=30, dependencies=[f"rescue_{cycle}_3"])
                ]
                plan.rationale = "Rescue roadmap injected to bypass LLM planning failure and ensure discovery execution."

            return plan
            
        except Exception as e:
            logger.error(f"Plan creation failed: {e}")
            logger.warning("[RETRY] Plan creation failed - waiting 3s then retrying once...")
            await asyncio.sleep(3)
            try:
                # One retry attempt
                result = await asyncio.to_thread(
                    self.llm_manager.run,
                    prompt=prompt,
                    mode="stable_code",
                    temperature=0.3,
                    max_tokens_override=None
                )
                if isinstance(result, dict):
                    text = result.get("text", result.get("content", ""))
                else:
                    text = str(result)
                plan = self._parse_plan_response(text, cycle, exploration_ratio, research_objective, num_tasks)
                plan.research_objective = research_objective
                if not plan.tasks:
                    logger.critical(" [RESCUE] LLM returned 0 tasks on retry. Injecting Masterpiece Roadmap.")
                    plan.tasks = [
                        ResearchTask(id=f"rescue_{cycle}_1", task_type="research", description=f"Extract empirical data regarding {research_objective}.", required_tools=["pubmed_search", "arxiv_search"], priority=1, estimated_minutes=30),
                        ResearchTask(id=f"rescue_{cycle}_2", task_type="analysis", description=f"Analyze datasets for {research_objective}.", required_tools=["code_executor"], priority=2, estimated_minutes=30),
                        ResearchTask(id=f"rescue_{cycle}_3", task_type="experiment", description="Execute modeling or simulation for the objective.", required_tools=["experiment_agent"], required_agents=["experiment_agent"], priority=3, estimated_minutes=60, dependencies=[f"rescue_{cycle}_1", f"rescue_{cycle}_2"]),
                        ResearchTask(id=f"rescue_{cycle}_4", task_type="synthesis", description="Generate high-rigor discovery report with falsification metrics.", required_tools=["report_generator"], priority=4, estimated_minutes=30, dependencies=[f"rescue_{cycle}_3"])
                    ]
                    plan.rationale = "Rescue roadmap injected to bypass LLM planning failure and ensure discovery execution."
                logger.info("[RETRY SUCCESS] Plan created successfully on retry")
                return plan
            except Exception as retry_e:
                logger.critical(f"[RESCUE] Plan creation exception after retry: {retry_e}. Injecting Sovereign Masterpiece Roadmap.")
                rescue_plan = ResearchPlan(
                    cycle=cycle,
                    tasks=[
                        ResearchTask(id=f"rescue_{cycle}_1", task_type="research", description=f"Extract empirical data regarding {research_objective}.", required_tools=["pubmed_search", "arxiv_search"], priority=1, estimated_minutes=30),
                        ResearchTask(id=f"rescue_{cycle}_2", task_type="analysis", description=f"Analyze datasets for {research_objective}.", required_tools=["code_executor"], priority=2, estimated_minutes=30),
                        ResearchTask(id=f"rescue_{cycle}_3", task_type="experiment", description="Execute modeling or simulation for the objective.", required_tools=["experiment_agent"], required_agents=["experiment_agent"], priority=3, estimated_minutes=60, dependencies=[f"rescue_{cycle}_1", f"rescue_{cycle}_2"]),
                        ResearchTask(id=f"rescue_{cycle}_4", task_type="synthesis", description="Generate high-rigor discovery report with falsification metrics.", required_tools=["report_generator"], priority=4, estimated_minutes=30, dependencies=[f"rescue_{cycle}_3"])
                    ],
                    rationale="Sovereign Masterpiece Roadmap injected following planning exception to guarantee mission continuation.",
                    exploration_ratio=exploration_ratio
                )
                rescue_plan.research_objective = research_objective
                return rescue_plan
    
    async def _build_planning_prompt(
        self,
        research_objective: str,
        context: Dict[str, Any],
        cycle: int,
        num_tasks: int,
        exploration_ratio: float,
        mode: str = "research"
    ) -> str:
        """Build the LLM prompt for plan generation (Mode Dispatcher)"""
        if mode == "discovery":
            return await self._build_discovery_prompt(
                research_objective, context, cycle, num_tasks, exploration_ratio
            )
        else:
            return await self._build_research_prompt(
                research_objective, context, cycle, num_tasks, exploration_ratio
            )

    def _determine_discovery_phase(self, cycle: int, total_cycles: int) -> Tuple[str, str, str]:
        """
        Determine the current Discovery Phase based on progress ratio.
        """
        progress = cycle / max(total_cycles, 1)
        
        if progress < 0.05: # First 5%
            return (
                "PHASE 0: SEEDING (WORLD MODELING)",
                "Build a rough world model. Scan abstract/surveys. Do NOT generate hypotheses yet.",
                "SHALLOW_READ_ONLY"
            )
        elif progress < 0.10: # Next 5%
            return (
                "PHASE 1: GENESIS (HYPOTHESIS GENERATION)",
                "Recombine concepts to propose cheap, falsifiable claims. Quantity over quality.",
                "SHALLOW_READ_AND_SEED"
            )
        elif progress < 0.40: # Next 30%
            return (
                "PHASE 2: EARLY ATTACK (FAST KILL)",
                "Kill weak ideas using Logic, Math, and Simulations.",
                "FORBIDDEN"
            )
        elif progress < 0.90: # Next 50%
            return (
                "PHASE 3: SIEGE (DEEP STRESS)",
                "Target 'RESILIENT' hypotheses. If attacks fail, read deeply to find subtle contradictions.",
                "CONDITIONAL"
            )
        else: # Final 10%
            return (
                "PHASE 4: VERDICT (FINAL EXAM)",
                "Verification reading and final judgment. Validate survivors.",
                "TARGETED_READING"
            )

    async def _build_discovery_prompt(
        self,
        research_objective: str,
        context: Dict[str, Any],
        cycle: int,
        num_tasks: int,
        exploration_ratio: float
    ) -> str:
        """Build distinct prompt for GODZILLA DISCOVERY mode"""
        findings = context.get("findings", [])
        hypotheses = context.get("hypotheses", [])
        # Include up to 50 recent findings for comprehensive multi-cycle synthesis.
        findings_str = "\n".join([f"- {f}" for f in findings[-50:]]) if findings else "None yet"
        
        # [GODZILLA FIX] Ensure research objective is present
        if not research_objective:
            research_objective = context.get("research_question", "Autonomous multi-domain scientific discovery")
            
        hypotheses_str = "None yet"
        if hypotheses: 
            hypotheses_str = ""
            for h in hypotheses[:30]:
                if isinstance(h, str):
                    hypotheses_str += f"- {h}\n"
                elif isinstance(h, dict):
                    hypotheses_str += (
                        f"- [{h.get('id', '?')}] (Conf: {float(h.get('confidence', 0.0) or 0.0):.2f} | "
                        f"Age: {h.get('age', 0)} | Survived: {h.get('survived', 0)}): "
                        f"{h.get('statement', '')}\n"
                    )
                else:
                    h_id = getattr(h, 'id', '?')
                    h_conf = float(getattr(h, 'confidence', 0.0) or 0.0)
                    h_stmt = getattr(h, 'statement', str(h))
                    h_meta = getattr(h, 'metadata', {}) or {}
                    hypotheses_str += (
                        f"- [{h_id}] (Conf: {h_conf:.2f} | "
                        f"Age: {h_meta.get('age', 0)} | Survived: {h_meta.get('attacks_survived', 0)}): "
                        f"{h_stmt}\n"
                    )
        
        # [ARCHITECTURAL MANDATE] Templates are EXCLUSIVELY for the experiment_agent.
        template_str = ""
        try:
            from backend.experiments.templates import find_applicable_templates, search_templates
            class DummyHypothesis:
                def __init__(self, s): self.statement = str(s)
            
            # [GODZILLA V68.31] Sovereign Domain Detection
            mission_domain = context.get("domain") or context.get("DOMAIN") or "general"
            if mission_domain.lower() == "ml": mission_domain = "machine_learning"
            if mission_domain.lower() == "cs": mission_domain = "computer_science"
            if mission_domain.lower() in ["general", "other", "other_scientific_domain"]:

                try:
                    from backend.core.domain_regulator import DomainRegulator
                    import asyncio
                    # [TITAN V207.0] ASYNC SOVEREIGNTY
                    # Physically awaited the domain judge to prevent event loop death.
                    mission_domain = await DomainRegulator.detect_domain(research_objective)
                    logger.info(f" [PLANNER] Autonomous Domain Recognition: {mission_domain.upper()}")
                except: mission_domain = "general"

            use_llm_flag = bool(self.llm_manager is not None and os.environ.get("ULTRON_OFFLINE_TESTS", "0") != "1")
            if use_llm_flag:
                applicable_templates = find_applicable_templates(
                    DummyHypothesis(research_objective), 
                    top_k=3, 
                    use_llm=True, 
                    domain=mission_domain
                )
            else:
                applicable_templates = search_templates(research_objective, top_k=3)
            
            if applicable_templates:
                template_str = "## RECOMMENDED EXPERIMENTAL TEMPLATES (ASSIGN TO experiment_agent ONLY)\n"
                for t in applicable_templates:
                    template_str += f"- **{t.name}**: {t.description} (MANDATORY AGENT: `experiment_agent`)\n"
        except Exception:
            applicable_templates = []
        
        # Ensure template_str is defined even if no templates found
        if not 'template_str' in locals() or not template_str:
            template_str = "## RECOMMENDED EXPERIMENTAL TEMPLATES\nNone selected. Design from first principles."

        arsenal_str, agents_str = self._format_tools_and_agents(context)
        total_cycles = context.get("total_cycles", 20)
        phase_name, phase_directive, reading_policy = self._determine_discovery_phase(cycle, total_cycles)

        is_graveyard = len(hypotheses) == 0
        goal_section = f"""
### OPERATIONAL CONTEXT: DISCOVERY PIPELINE (PHASE 2: RED TEAM)
Current Strategy: **{phase_name}**
Directive: {phase_directive}
Reading Policy: **{reading_policy}**

You are the **Adversarial Executor**.
Your Goal: **FALSIFICATION**. You must destroy the active hypotheses.
"""
        if is_graveyard:
            goal_section = f"""
###  PHOENIX PROTOCOL INITIATED (GRAVEYARD DETECTED)
**CRITICAL ALERT**: All active hypotheses have been destroyed.
Your Goal: **GENESIS**. You must RISE FROM THE ASHES.
"""

        prompt = f"""
 GODZILLA MODE: ADVERSARIAL ATTACK PLANNER
You are the STRATEGIC COORDINATOR for the **DISCOVERY PIPELINE**.
Current Cycle: {cycle}
Target Exploration Ratio: {exploration_ratio:.2f}

{goal_section}

###  SYSTEM KILL GATES (CRITICAL WARNING)
Your plan will be REJECTED if:
1.  **Non-Physical**: Tasks must test PHYSICAL REALITY, not policies.
2.  **Red Team Veto**: `red_team_agent` will block plans lacking "Mutually Exclusive Outcomes".
3.  **Orthogonality Check**: You MUST vary your attack vectors. Do not repeat the same attack type as the previous cycle.

## RESEARCH OBJECTIVE
{research_objective}

## CONTEXT
### Prior Findings (Recent)
{findings_str}

### Active Hypotheses
{hypotheses_str}

{template_str}

{arsenal_str}

{agents_str}

## PLANNING RULES (MASSIVE PARALLELISM)
1.  **THROUGHPUT**: Generate exactly {num_tasks} tasks.
2.  **FLATTEN DEPENDENCIES**: Minimize sequential chains to enable parallel execution.
3.  **AGENT UTILIZATION**: Assign specific agents. Use `experiment_agent` for ALL technical/numerical validation.
4.  **DETAIL MANDATE**: All tasks MUST have extreme methodological detail.
5.  **SKILL MANDATE (KOSMOS-TIER)**: For each task, you MUST specify exactly which Atomic Skills are needed in the `required_skills` field.
6.  **COMPUTATIONAL REALITY CONSTRAINTS**: Design tasks that execute cleanly within local workstation sandbox limits (vectorized NumPy/SciPy/PyTorch/Statsmodels/Bio.PDB analyses over full local datasets such as N = 1,000–50,000 rows are encouraged; avoid multi-day all-atom MD trajectories or unavailable external HPC cluster jobs).
## OUTPUT FORMAT
Return ONLY valid JSON:
{{
    "rationale": "Explanation of strategy",
    "tasks": [
        {{
            "task_type": "analysis|experiment|synthesis|validation",
            "description": "DETAILED description including search terms, parameters, and criteria",
            "expected_output": "What this task should produce",
            "required_tools": ["tool_name"],
            "required_agents": ["agent_name"],
            "required_skills": ["skill_folder_name"],
            "is_exploration": true|false,
            "priority": 1-10,
            "estimated_minutes": 15-120,
            "dependencies": []
        }}
    ]
}}"""
        return prompt

    async def _build_research_prompt(
        self,
        research_objective: str,
        context: Dict[str, Any],
        cycle: int,
        num_tasks: int,
        exploration_ratio: float
    ) -> str:
        """Build distinct prompt for DEEP RESEARCH mode"""
        findings = context.get("findings", [])
        hypotheses = context.get("hypotheses", [])
        # Include up to 50 recent findings for comprehensive multi-cycle synthesis.
        findings_str = "\n".join([f"- {f}" for f in findings[-50:]]) if findings else "None yet"
        
        # [GODZILLA FIX] Ensure research objective is present
        if not research_objective:
            research_objective = context.get("research_question", "Research objective")
            
        hypotheses_str = "None yet"
        if hypotheses:
            hypotheses_str = ""
            for h in hypotheses[:30]:
                if isinstance(h, str):
                    hypotheses_str += f"- {h}\n"
                elif isinstance(h, dict):
                    hypotheses_str += (
                        f"- [{h.get('id', '?')}] (Conf: {float(h.get('confidence', 0.0) or 0.0):.2f} | "
                        f"Age: {h.get('age', 0)}): {h.get('statement', '')}\n"
                    )
                else:
                    h_id = getattr(h, 'id', '?')
                    h_conf = float(getattr(h, 'confidence', 0.0) or 0.0)
                    h_stmt = getattr(h, 'statement', str(h))
                    h_meta = getattr(h, 'metadata', {}) or {}
                    hypotheses_str += (
                        f"- [{h_id}] (Conf: {h_conf:.2f} | "
                        f"Age: {h_meta.get('age', 0)}): {h_stmt}\n"
                    )
        
        knowledge_snapshot = context.get("knowledge_snapshot", "")

        # [ARCHITECTURAL MANDATE] Templates are EXCLUSIVELY for the experiment_agent.
        template_str = ""
        try:
            from backend.experiments.templates import find_applicable_templates, search_templates
            class DummyHypothesis:
                def __init__(self, s): self.statement = str(s)
            
            # [GODZILLA V68.31] Sovereign Domain Detection
            mission_domain = context.get("domain") or context.get("DOMAIN") or "general"
            if mission_domain.lower() == "ml": mission_domain = "machine_learning"
            if mission_domain.lower() == "cs": mission_domain = "computer_science"
            if mission_domain.lower() in ["general", "other", "other_scientific_domain"]:

                try:
                    from backend.core.domain_regulator import DomainRegulator
                    import asyncio
                    # [TITAN V207.0] ASYNC SOVEREIGNTY
                    # Physically awaited the domain judge to prevent event loop death.
                    mission_domain = await DomainRegulator.detect_domain(research_objective)
                    logger.info(f" [PLANNER] Autonomous Domain Recognition: {mission_domain.upper()}")
                except: mission_domain = "general"

            use_llm_flag = bool(self.llm_manager is not None and os.environ.get("ULTRON_OFFLINE_TESTS", "0") != "1")
            if use_llm_flag:
                applicable_templates = find_applicable_templates(
                    DummyHypothesis(research_objective), 
                    top_k=3, 
                    use_llm=True, 
                    domain=mission_domain
                )
            else:
                applicable_templates = search_templates(research_objective, top_k=3)
            
            if applicable_templates:
                template_str = "## RECOMMENDED EXPERIMENTAL TEMPLATES (ASSIGN TO experiment_agent ONLY)\n"
                for t in applicable_templates:
                    template_str += f"- **{t.name}**: {t.description} (MANDATORY AGENT: `experiment_agent`)\n"
        except Exception:
            applicable_templates = []
        
        if not 'template_str' in locals() or not template_str:
            template_str = "## RECOMMENDED EXPERIMENTAL TEMPLATES\nNone selected. Use semantic search."

        # Inject Meta-Skills (The "Elite Brain")
        meta_skills_str = ""
        try:
            from backend.core.skill_injector import get_expert_system
            expert = get_expert_system()
            meta_skills_str = await expert.inject_meta_skills("", query=research_objective, domain=mission_domain)
        except Exception:
            pass

        arsenal_str, agents_str = self._format_tools_and_agents(context)
        p_target = context.get("paper_read_target", 10000)
        d_target = context.get("deep_read_target", 2000)
        max_runtime = context.get("constraints", {}).get("runtime_mode", "1.0h")

        return f"""
{meta_skills_str}

 TACTICAL PLANNER: DEEP RESEARCH ORCHESTRATION
You are the STRATEGIC COORDINATOR for the **RESEARCH PIPELINE**.
Current Cycle: {cycle} | Goal: OBJECTIVE SYNTHESIS.
Remaining Time Budget: {max_runtime}
Scale: Scan {p_target}+ abstracts, Read {d_target}+ full PDFs.

You are the **Swarm Commander**. Gather evidence to test `Hypothesis.confidence`.
Avoid **Confirmation Bias**. Actively search for contradictory evidence.

## RESEARCH OBJECTIVE
{research_objective}

## CONTEXT
### Prior Findings (Recent)
{findings_str}

### Prior Research History
{knowledge_snapshot}

### Active Hypotheses
{hypotheses_str}

{template_str}

{arsenal_str}

{agents_str}

## PLANNING RULES (MASSIVE PARALLELISM)
1.  **THROUGHPUT**: Generate exactly {num_tasks} tasks.
2.  **MANDATORY PARALLELISM**: At least 3 tasks MUST have `dependencies: []`. Minimize sequential chains to enable parallel execution. 
    *   Example: Literature search, Data download, and Baseline modeling can all have `dependencies: []`.
3.  **MANDATORY EXPERIMENTATION**: You MUST assign at least one task to the `experiment_agent`. Plans without code execution are REJECTED.
4.  **SOVEREIGN RESEARCH & DEEP KNOWLEDGE**: Assign literature, web, and full-text PDF analysis tasks to `research_agent` (using tools like `scholar_search`, `arxiv_search`, `pubmed_search`, `deep_paper_reader`, `web_search`).
5.  **STRICT TOOL LITERALNESS**: You MUST use tool names EXACTLY as they appear in the registry. Do NOT add versions like '_v1.0'.
6.  **COMPUTATIONAL REALITY CONSTRAINTS**: Design tasks that execute cleanly within local workstation sandbox limits (vectorized NumPy/SciPy/PyTorch/Statsmodels/Bio.PDB analyses over full local datasets such as N = 1,000–50,000 rows are encouraged; avoid multi-day all-atom MD trajectories or unavailable external HPC cluster jobs).

## OUTPUT FORMAT
Return ONLY valid JSON:
{{
    "rationale": "Explanation of strategy",
    "tasks": [
        {{
            "task_type": "research|analysis|synthesis",
            "description": "DETAILED description including search terms, parameters, and criteria",
            "expected_output": "What this task should produce",
            "required_tools": ["tool_name"],
            "required_agents": ["agent_name"],
            "required_skills": ["skill_name_from_expert_system"],
            "is_exploration": true|false,
            "priority": 1-10,
            "estimated_minutes": 15-120,
            "dependencies": []
        }}
    ]
}}"""

    def _format_tools_and_agents(self, context: Dict[str, Any]) -> Tuple[str, str]:
        """Helper to format tool/agent lists uniformly with SUITABILITY HINTS"""
        available_tools = context.get("available_tools", [])
        if not available_tools:
            try:
                from backend.tools.tool_registry import REGISTRY
                available_tools = REGISTRY.list_tools()
            except ImportError:
                available_tools = ["web_search", "scholar_search", "deep_paper_reader", "executor"]
        
        available_agents = context.get("available_agents", []) or [
            "research_agent",
            "experiment_agent",
            "red_team_agent",
            "writer_agent",
            "report_composer_agent"
        ]

        # Categorize Tools with SUITABILITY HINTS
        tool_map = {
            "Scanning & Web": ["web_search", "web_crawler", "google_search", "beast_search", "twitter", "youtube"],
            "Scientific Literature & Full-Text": ["deep_paper", "scholar", "pubmed", "arxiv", "biorxiv"],
            "Execution & Lab": ["executor", "experiment", "code"],
            "Review & Adversarial Audit": ["red_team", "critic"],
            "Synthesis": ["writer", "report", "jupyter"]
        }
        
        categorized_tools = {k: [] for k in tool_map.keys()}
        categorized_tools["Other"] = []
        
        for tool in available_tools:
            placed = False
            for cat, keywords in tool_map.items():
                if any(k in tool.lower() for k in keywords):
                    categorized_tools[cat].append(f"`{tool}`")
                    placed = True
                    break
            if not placed:
                categorized_tools["Other"].append(f"`{tool}`")
                
        arsenal_str = "## FULL SYSTEM ARSENAL (AVAILABLE TOOLS)\n"
        for cat, tools in categorized_tools.items():
            if tools:
                arsenal_str += f"- **{cat}**: {', '.join(tools)}\n"
        
        agents_str = "## SOVEREIGN AGENT FLEET (ASSIGN THESE)\n"
        agents_str += (
            "- `research_agent`: Unified literature, full-text PDF, web search, & evidence synthesis engine\n"
            "- `experiment_agent`: Unified Python/SciPy/PyTorch/Bio.PDB computational experimentation & data analysis engine\n"
            "- `red_team_agent`: Adversarial falsification, citation verification, & claim auditing engine\n"
            "- `writer_agent` / `report_composer_agent`: Scientific manuscript & dossier synthesis\n"
        )
        if available_agents:
            agents_str += "Available: " + ", ".join([f"`{a}`" for a in available_agents]) + "\n"
            
        return arsenal_str, agents_str

    async def _critique_and_refine(
        self,
        plan: ResearchPlan,
        objective: str,
        context: Dict[str, Any],
        mode: str,
        attempt: int = 1,
        max_attempts: int = 2
    ) -> Optional[ResearchPlan]:
        """
        Self-Correction Loop: Critique the plan and refine if necessary.
        """
        if attempt > max_attempts:
            return None

        try:
            critique_prompt = f"""You are a RESEARCH PLAN CRITIC (GODZILLA TIER).
Review the following plan for objective: "{objective}".
Mode: {mode} | Plan JSON: {json.dumps(plan.to_dict(), indent=2)}

CRITERIA: Parallelism, Tool Specificity, Agent Suitability.
If the plan is good, output ONLY: "VERDICT: APPROVED"
If bad, output "VERDICT: REJECTED" followed by a list of flaws."""

            result = await asyncio.to_thread(self.llm_manager.run, prompt=critique_prompt, mode="stable_code", temperature=0.2)
            critique_text = result.get("text", result.get("content", "")) if isinstance(result, dict) else str(result)
            
            if "VERDICT: APPROVED" in critique_text:
                return None
            
            # Perform Refinement
            refine_prompt = f"""ORIGINAL PLAN:\n{json.dumps(plan.to_dict(), indent=2)}\n\nCRITIQUE:\n{critique_text}\n\nTASK: Regenerate the Plan JSON to address the critique."""

            result_refined = await asyncio.to_thread(self.llm_manager.run, prompt=refine_prompt, mode="stable_code", temperature=0.4)
            text_refined = result_refined.get("text", "") if isinstance(result_refined, dict) else str(result_refined)
            
            refined_plan = self._parse_plan_response(text_refined, plan.cycle, plan.exploration_ratio, objective, len(plan.tasks))
            
            # Recursive refinement
            further = await self._critique_and_refine(refined_plan, objective, context, mode, attempt + 1, max_attempts)
            return further if further else refined_plan
            
        except Exception as e:
            logger.warning(f"Self-Correction loop failed: {e}")
            return None

    def _parse_plan_response(
        self,
        response_text: str,
        cycle: int,
        exploration_ratio: float,
        objective: str = "Discovery Sweep",
        num_tasks: int = 5
    ) -> ResearchPlan:
        """Parse LLM response into ResearchPlan with Nuclear Clean logic."""
        if not response_text:
            raise RuntimeError("[HARD ABORT] LLM generation failed - cannot produce valid planning. Manual intervention required.")

        cleaned_text = response_text.strip()
        
        # Nuclear Clean: Isolate JSON block (either object {...} or array [...])
        brace_start = cleaned_text.find('{')
        brace_end = cleaned_text.rfind('}')
        bracket_start = cleaned_text.find('[')
        bracket_end = cleaned_text.rfind(']')

        if bracket_start != -1 and (brace_start == -1 or bracket_start < brace_start) and bracket_end > bracket_start:
            cleaned_text = cleaned_text[bracket_start:bracket_end+1]
        elif brace_start != -1 and brace_end > brace_start:
            cleaned_text = cleaned_text[brace_start:brace_end+1]
        
        try:
            from backend.utils.json_repair import repair_json
            data = repair_json(cleaned_text)
        except ImportError:
            try:
                data = json.loads(cleaned_text)
            except:
                data = None
            
        if not data:
            return ResearchPlan(cycle=cycle, tasks=[], rationale="FAILED_TO_PARSE", exploration_ratio=exploration_ratio)

        tasks = []
        if isinstance(data, list):
            raw_tasks = data
            rationale_text = "Extracted task list from response."
        elif isinstance(data, dict):
            raw_tasks = data.get("tasks", [])
            rationale_text = data.get("rationale", "")
        else:
            raw_tasks = []
            rationale_text = ""

        # P0-97: First pass - build old_id -> canonical new_id map so dependencies never break
        id_remap: Dict[str, str] = {}
        valid_raw_tasks: List[Dict[str, Any]] = []
        for raw_idx, task_data in enumerate(raw_tasks):
            if not isinstance(task_data, dict) or not task_data.get("description"):
                continue
            new_idx = len(valid_raw_tasks) + 1
            canonical_id = f"task_{cycle}_{new_idx}"
            orig_id = str(task_data.get("id", "")).strip()
            if orig_id:
                id_remap[orig_id] = canonical_id
            # Also map common shorthand references used by LLMs ('1', 'task_1', 't1', 'step_1')
            id_remap[str(new_idx)] = canonical_id
            id_remap[str(raw_idx + 1)] = canonical_id
            id_remap[f"task_{new_idx}"] = canonical_id
            id_remap[f"t{new_idx}"] = canonical_id
            id_remap[f"step_{new_idx}"] = canonical_id
            valid_raw_tasks.append((canonical_id, task_data))

        # Sovereign agent canonicalization map
        sovereign_agent_map = {
            "web_search_agent": "research_agent",
            "doc_reader_agent": "research_agent",
            "summarizer_agent": "research_agent",
            "qa_agent": "research_agent",
            "data_analyzer_agent": "experiment_agent",
            "ml_model_builder_agent": "experiment_agent",
            "fact_checker_agent": "red_team_agent",
        }

        for canonical_id, task_data in valid_raw_tasks:
            try:
                t_type = task_data.get("task_type") or task_data.get("type", "research")
                raw_deps = task_data.get("dependencies", []) or []
                remapped_deps: List[str] = []
                for dep in raw_deps:
                    dep_key = str(dep.get("id") or dep.get("task_id") if isinstance(dep, dict) else dep).strip()
                    if not dep_key:
                        continue
                    mapped_dep = id_remap.get(dep_key, dep_key)
                    if mapped_dep != canonical_id and mapped_dep not in remapped_deps:
                        remapped_deps.append(mapped_dep)

                raw_agents = task_data.get("required_agents", []) or []
                if isinstance(raw_agents, str):
                    raw_agents = [raw_agents]
                canonical_agents: List[str] = []
                for ag in raw_agents:
                    ag_name = str(ag.get("name") if isinstance(ag, dict) else ag).strip()
                    mapped_ag = sovereign_agent_map.get(ag_name, ag_name)
                    if mapped_ag and mapped_ag not in canonical_agents:
                        canonical_agents.append(mapped_ag)

                raw_hyps = task_data.get("target_hypothesis_ids", []) or []
                if isinstance(raw_hyps, str):
                    raw_hyps = [raw_hyps]

                task = ResearchTask(
                    id=canonical_id,
                    task_type=t_type,
                    type=t_type,
                    description=task_data.get("description", ""),
                    expected_output=task_data.get("expected_output", ""),
                    required_tools=task_data.get("required_tools", []) or [],
                    required_agents=canonical_agents,
                    required_skills=task_data.get("required_skills", []) or [],
                    is_exploration=bool(task_data.get("is_exploration", False)),
                    priority=int(task_data.get("priority", 5)),
                    estimated_minutes=float(task_data.get("estimated_minutes", 30)),
                    dependencies=remapped_deps,
                    target_hypothesis_ids=list(raw_hyps),
                    metadata=task_data.get("metadata", {}) if isinstance(task_data.get("metadata"), dict) else {},
                    payload=task_data.get("payload", {}) if isinstance(task_data.get("payload"), dict) else {},
                    status="pending"
                )
                tasks.append(task)
            except Exception:
                continue
        
        return ResearchPlan(
            cycle=cycle,
            tasks=tasks,
            rationale=rationale_text,
            exploration_ratio=exploration_ratio
        )

    async def revise_plan(self, plan: ResearchPlan, feedback: Dict[str, Any], context: Dict[str, Any]) -> ResearchPlan:
        """
        Revise the plan based on adversarial feedback.
        """
        logger.info(f" Revising plan {plan.cycle} based on feedback...")
        
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                backoff = min(2.0 * (2 ** (attempt - 1)), 8.0)
                logger.info(f"Retrying plan revision attempt {attempt+1} (backoff {backoff:.1f}s)...")
                await asyncio.sleep(backoff)
                
            try:
                # Build refinement prompt
                refine_prompt = f"""You are a STRATEGIC PLAN REVISER (Ph.D. Tier).
ORIGINAL PLAN:
{json.dumps(plan.to_dict(), indent=2)}

CRITIQUE:
{json.dumps(feedback, indent=2)}

TASK: Regenerate the Plan JSON to address the critique. Ensure you:
1. Increase Parallelism (minimize dependencies).
2. Fix Tool Specificity.
3. Fix Agent Suitability.
4. Maintain all critical research objectives.

Return ONLY valid JSON:
{{
    "rationale": "Explanation of changes",
    "tasks": [...]
}}"""

                result = await asyncio.to_thread(
                    self.llm_manager.run,
                    prompt=refine_prompt,
                    mode="stable_code",
                    temperature=0.4 + (attempt * 0.2),
                    source="plan_reviser"
                )
                
                text = result.get("text", "") if isinstance(result, dict) else str(result)
                
                revised_plan = self._parse_plan_response(text, plan.cycle, plan.exploration_ratio, getattr(plan, 'research_objective', 'Discovery'), len(plan.tasks))
                return revised_plan
                
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f" Plan revision terminal failure: {e}")
                    return plan
                logger.warning(f" Plan revision attempt {attempt+1} failed: {e}")

