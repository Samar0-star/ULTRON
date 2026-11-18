"""
Plan Reviewer for Avon-2 Deep Mode
====================================

Reviews research plans before execution to catch issues:
- Feasibility problems
- Missing dependencies
- Resource conflicts
- Strategic gaps
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.core.planning.plan_creator import ResearchPlan

logger = logging.getLogger(__name__)


@dataclass
class PlanReview:
    """Result of plan review"""
    plan_id: str
    is_approved: bool
    overall_score: float  # 0.0-1.0
    
    # Issue breakdown
    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    # Scores by category
    feasibility_score: float = 0.0
    coherence_score: float = 0.0
    coverage_score: float = 0.0
    resource_score: float = 0.0
    
    summary: str = ""
    reviewed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "is_approved": self.is_approved,
            "overall_score": self.overall_score,
            "issues": self.issues,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "scores": {
                "feasibility": self.feasibility_score,
                "coherence": self.coherence_score,
                "coverage": self.coverage_score,
                "resources": self.resource_score
            },
            "summary": self.summary,
            "reviewed_at": self.reviewed_at.isoformat()
        }


class PlanReviewer:
    """
    Reviews research plans before execution.
    
    Checks for:
    - Task feasibility
    - Dependency correctness
    - Resource availability
    - Strategic coherence
    
    Example:
        ```python
        reviewer = PlanReviewer(llm_manager=llm_manager)
        review = reviewer.review(plan)
        
        if review.is_approved:
            execute_plan(plan)
        else:
            revised_plan = creator.revise_plan(plan, review.to_dict(), context)
        ```
    """
    
    APPROVAL_THRESHOLD = 0.5  # Plans must score >= 0.5 to be approved
    
    def __init__(
        self,
        llm_manager=None,
        approval_threshold: float = 0.5,
        available_tools: Optional[List[str]] = None,
        available_agents: Optional[List[str]] = None
    ):
        """
        Initialize Plan Reviewer.
        
        Args:
            llm_manager: LLM manager for intelligent review
            approval_threshold: Minimum score for approval
            available_tools: List of available tool names
            available_agents: List of available agent names
        """
        self.llm_manager = llm_manager
        self.approval_threshold = approval_threshold
        
        # DYNAMIC TOOL LOADING
        if available_tools:
            self.available_tools = available_tools
        else:
            try:
                from backend.tools.tool_registry import REGISTRY
                # Use list_tools() to get tool names
                self.available_tools = REGISTRY.list_tools()
            except ImportError:
                logger.warning("PlanReviewer: REGISTRY import failed, using fallback tools")
                self.available_tools = [
                    "web_search", "scholar_search", "code_executor", 
                    "data_analyzer", "summarizer", "writer", 
                    "table_extractor", "deep_paper_reader", "fact_checker",
                    "ml_model_builder", "web_crawler", "social_media_agent", 
                    "video_analyzer_agent", "executor_agent", "experiment_agent",
                    "pubmed_tool", "biorxiv_tool", "twitter_academic_tool", 
                    "youtube_tool", "image_processor", "jupyter_exporter"
                ]

        self.available_agents = available_agents or [
            "research_agent", "writer_agent", "qa_agent",
            "planner_agent", "summarizer_agent", "web_search_agent",
            "red_team_agent", "fact_checker_agent", "code_executor",
            "critic", "data_analyst", "visualizer", "deep_paper_reader",
            "experiment_agent", "doc_reader_agent", "ml_model_builder_agent",
            "report_composer_agent"
        ]
        
        # Lazy load llm_manager
        if self.llm_manager is None:
            try:
                from backend.llm_manager import llm_manager
                self.llm_manager = llm_manager
            except ImportError:
                logger.warning("LLM manager not available for plan review")
        
        logger.info(f"PlanReviewer initialized (threshold={approval_threshold}, tools={len(self.available_tools)})")
    
    def review(self, plan: ResearchPlan) -> PlanReview:
        """
        Review a research plan.
        
        Args:
            plan: Plan to review
            
        Returns:
            PlanReview with approval status and feedback
        """
        logger.info(f"Reviewing plan {plan.id} with {len(plan.tasks)} tasks")
        
        issues = []
        warnings = []
        suggestions = []
        
        # Check 1: Feasibility - do required tools/agents exist?
        feasibility_score, feasibility_issues = self._check_feasibility(plan)
        issues.extend(feasibility_issues)
        
        # Check 2: Coherence - do tasks make sense together?
        coherence_score = self._check_coherence(plan)
        
        # Check 3: Coverage - is objective adequately addressed?
        coverage_score = self._check_coverage(plan)
        
        # Check 4: Resources - are time estimates reasonable?
        resource_score, resource_warnings = self._check_resources(plan)
        warnings.extend(resource_warnings)
        
        # Check 5: Dependencies - are they valid?
        dep_issues = self._check_dependencies(plan)
        issues.extend(dep_issues)
        
        # Calculate overall score
        overall_score = (
            feasibility_score * 0.3 +
            coherence_score * 0.25 +
            coverage_score * 0.25 +
            resource_score * 0.2
        )
        
        # Penalty for critical issues
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        if critical_issues:
            overall_score *= 0.5
        
        # Standard approval manifold
        is_approved = overall_score >= self.approval_threshold and len(critical_issues) == 0
        
        # Generate suggestions if not approved

        if not is_approved:
            suggestions = self._generate_suggestions(plan, issues)
        
        summary = self._generate_summary(
            is_approved, overall_score, len(issues), len(warnings)
        )
        
        review = PlanReview(
            plan_id=plan.id,
            is_approved=is_approved,
            overall_score=overall_score,
            issues=issues,
            warnings=warnings,
            suggestions=suggestions,
            feasibility_score=feasibility_score,
            coherence_score=coherence_score,
            coverage_score=coverage_score,
            resource_score=resource_score,
            summary=summary
        )
        
        logger.info(f"Review complete: approved={is_approved}, score={overall_score:.2f}")
        return review
    
    def _check_feasibility(self, plan: ResearchPlan) -> tuple:
        """Check if required tools and agents are available (FUZZY MATCHING + HARDWARE BYPASS)"""
        score = 1.0
        issues = []
        
        # Pre-normalize available tools for O(1) exact matching
        norm_tools = {t.lower().replace("_", "").replace("-", "").replace("tool", "").replace("database", "").strip(): t for t in self.available_tools}
        
        # HARDWARE BYPASS: List of PHYSICAL LAB EQUIPMENT only (not computational tools!)
        # [V255+] REMOVED: 'software', 'model', 'computer', 'engine', 'machine' — these are computational and DO exist
        PHYSICAL_HARDWARE = {"pipette", "beaker", "centrifuge", "sequencer", "spectrometer", "microscope", "reagent", "lab", "physical", "equipment", "synthesizer", "cluster"}
        
        # [V255+ & P0-99] Explicit computational & scientific library allowlist to prevent false positives
        COMPUTATIONAL_TOOLS_PRESENT = {
            "ml_model_builder", "ml_model_builder_agent", "mlmodelbuilder",
            "model", "modelbuilder", "statsmodels", "statsmodel",
            "experiment_agent", "experimentagent", "code_executor", "codeexecutor",
            "python", "scipy", "numpy", "pandas", "biopython", "biopdb", "pytorch", "torch",
            "sklearn", "scikitlearn", "matplotlib", "seaborn", "plotly", "networkx",
            "rdkit", "openmm", "mdanalysis", "reportgenerator", "report_generator",
            "research_agent", "researchagent", "red_team_agent", "redteamagent",
            "writer_agent", "writeragent", "report_composer_agent", "reportcomposeragent",
            "data_analyzer", "dataanalyzer", "data_analyzer_agent", "doc_reader", "docreader",
            "deep_paper_reader", "deeppaperreader", "summarizer", "fact_checker", "factchecker"
        }

        sovereign_agent_aliases = {
            "web_search_agent": "research_agent",
            "doc_reader_agent": "research_agent",
            "summarizer_agent": "research_agent",
            "qa_agent": "research_agent",
            "data_analyzer_agent": "experiment_agent",
            "ml_model_builder_agent": "experiment_agent",
            "fact_checker_agent": "red_team_agent",
        }

        for task in plan.tasks:
            # Check tools - FIXED: Precision Normalization
            for tool in task.required_tools:
                # [GODZILLA FIX] Ensure tool is a string
                tool_str = str(tool.get("name") if isinstance(tool, dict) else tool)
                
                # [GODZILLA FIX 2] Strip versioning for matching (e.g. summarizer_v1.2 -> summarizer)
                # This handles LLMs that hallucinate versions despite mandates.
                tool_base = tool_str.split("_v")[0].split("-v")[0].strip()
                
                tool_clean = tool_base.lower().replace("_", "").replace("-", "").replace("tool", "").replace("database", "").strip()
                
                # 1a. Computational tool explicit allowlist (NEVER bypass these)
                if tool_clean in COMPUTATIONAL_TOOLS_PRESENT:
                    logger.debug(f"PlanReviewer: Resolved '{tool_str}' as known computational tool")
                    continue
                
                # 1b. Physical Hardware Bypass (lab equipment only)
                if any(hw in tool_clean for hw in PHYSICAL_HARDWARE):
                    logger.info(f"PlanReviewer: [BYPASS] Simulating physical hardware requirement: '{tool_str}' mapped to 'experiment_agent'")
                    if "experiment_agent" not in task.required_tools:
                        task.required_tools.append("experiment_agent")
                    # We continue without raising an issue for the physical tool, 
                    # but we implicitly mandate computational simulation.
                    continue

                # 2. Fuzzy/Normalized Matching
                # Check both the literal tool name and the base name (no version)
                if tool_str in self.available_tools or tool_base in self.available_tools or tool_clean in norm_tools:
                    logger.debug(f"PlanReviewer: Resolved '{tool_str}' to available toolset")
                
                # 3. Scientific Software Fallback (e.g. arXiv API -> arxiv_search)
                elif any(k in tool_clean for k in ("arxiv", "scholar", "pubmed", "biorxiv", "crossref", "search", "crawler", "reader", "report", "jupyter")):
                    logger.info(f"PlanReviewer: Resolved scientific/search tool '{tool_str}'")
                else:
                    issues.append({
                        "type": "missing_tool",
                        "task_id": task.id,
                        "item": tool,
                        "severity": "critical",
                        "message": f"Task {task.id} requires unavailable tool: {tool}"
                    })
                    score -= 0.15
            
            # Check agents - Map legacy micro-agents to Sovereign Agents
            for idx, agent in enumerate(list(task.required_agents)):
                agent_str = str(agent.get("name") if isinstance(agent, dict) else agent)
                if agent_str in sovereign_agent_aliases:
                    task.required_agents[idx] = sovereign_agent_aliases[agent_str]
                    agent_str = task.required_agents[idx]
                
                if agent_str not in self.available_agents:
                    if any(k in agent_str.lower() for k in ("doc", "read", "search", "summar", "qa", "research")):
                        logger.info(f"PlanReviewer: Mapping agent '{agent_str}' -> 'research_agent'")
                        task.required_agents[idx] = "research_agent"
                        continue
                    if any(k in agent_str.lower() for k in ("exp", "data", "analy", "model", "code", "sim")):
                        logger.info(f"PlanReviewer: Mapping agent '{agent_str}' -> 'experiment_agent'")
                        task.required_agents[idx] = "experiment_agent"
                        continue
                    if any(k in agent_str.lower() for k in ("red", "fact", "critic", "verif")):
                        logger.info(f"PlanReviewer: Mapping agent '{agent_str}' -> 'red_team_agent'")
                        task.required_agents[idx] = "red_team_agent"
                        continue

                    issues.append({
                        "type": "missing_agent",
                        "task_id": task.id,
                        "item": agent_str,
                        "severity": "warning",
                        "message": f"Task {task.id} requires unavailable agent: {agent_str}"
                    })
                    score -= 0.1
        
        return max(0.0, score), issues
    
    def _check_coherence(self, plan: ResearchPlan) -> float:
        """Check if tasks form a coherent strategy"""
        if not plan.tasks:
            return 0.0
        
        score = 0.8  # Base coherence
        
        # Check for mix of task types
        task_types = set(t.task_type for t in plan.tasks)
        if len(task_types) >= 3:
            score += 0.1  # Good variety
        elif len(task_types) == 1:
            score -= 0.1  # Too homogeneous
        
        # Check exploration/exploitation balance
        exploration_count = sum(1 for t in plan.tasks if t.is_exploration)
        actual_ratio = exploration_count / len(plan.tasks)
        expected_ratio = plan.exploration_ratio
        
        if abs(actual_ratio - expected_ratio) > 0.2:
            score -= 0.1  # Imbalanced
        
        return min(1.0, max(0.0, score))
    
    def _check_coverage(self, plan: ResearchPlan) -> float:
        """Check if objective is adequately covered"""
        if not plan.research_objective or not plan.tasks:
            return 0.5
        
        # Simple heuristic: check if key terms appear in task descriptions
        objective_words = set(plan.research_objective.lower().split())
        
        covered_count = 0
        for task in plan.tasks:
            task_words = set(task.description.lower().split())
            if objective_words & task_words:
                covered_count += 1
        
        coverage = covered_count / len(plan.tasks)
        return min(1.0, coverage * 1.5)  # Scale up a bit
    
    def _check_resources(self, plan: ResearchPlan) -> tuple:
        """Check resource/time estimates"""
        warnings = []
        
        total_minutes = sum(t.estimated_minutes for t in plan.tasks)
        
        # Warn if total time is very high
        if total_minutes > 480:  # 8 hours
            warnings.append(f"Total estimated time is {total_minutes/60:.1f} hours - consider parallel execution")
        
        # Check for unrealistic estimates
        for task in plan.tasks:
            if task.estimated_minutes < 5:
                warnings.append(f"Task {task.id} may be underestimated ({task.estimated_minutes} min)")
            elif task.estimated_minutes > 120:
                warnings.append(f"Task {task.id} may be too long ({task.estimated_minutes} min) - consider splitting")
        
        # Score based on warnings
        score = 1.0 - (len(warnings) * 0.1)
        return max(0.0, score), warnings
    
    def _check_dependencies(self, plan: ResearchPlan) -> List[Dict[str, Any]]:
        """Check for dependency issues"""
        issues = []
        task_ids = {t.id for t in plan.tasks}
        
        for task in plan.tasks:
            for dep_id in task.dependencies:
                # HARDENING: Handle LLMs that return dicts for dependencies
                effective_dep_id = dep_id
                if isinstance(dep_id, dict):
                    effective_dep_id = dep_id.get("id") or dep_id.get("task_id")
                
                if not isinstance(effective_dep_id, str):
                    logger.warning(f"Task {task.id} has invalid dependency type: {type(dep_id)}")
                    continue

                if effective_dep_id not in task_ids:
                    issues.append({
                        "type": "invalid_dependency",
                        "task_id": task.id,
                        "dependency": effective_dep_id,
                        "severity": "critical",
                        "message": f"Task {task.id} depends on non-existent task {effective_dep_id}"
                    })
        
        # Check for circular dependencies (full DFS cycle detection across multi-hop chains)
        adj: Dict[str, List[str]] = {}
        for task in plan.tasks:
            deps = []
            for d in task.dependencies:
                eff_d = d.get("id") or d.get("task_id") if isinstance(d, dict) else d
                if isinstance(eff_d, str) and eff_d in task_ids:
                    deps.append(eff_d)
            adj[task.id] = deps

        visited: Dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited
        cycle_tasks = set()

        def _dfs_cycle(node: str):
            visited[node] = 1
            for nbr in adj.get(node, []):
                state = visited.get(nbr, 0)
                if state == 1:
                    cycle_tasks.add(node)
                    cycle_tasks.add(nbr)
                elif state == 0:
                    _dfs_cycle(nbr)
            visited[node] = 2

        for t_id in task_ids:
            if visited.get(t_id, 0) == 0:
                _dfs_cycle(t_id)

        for cyc_tid in sorted(cycle_tasks):
            issues.append({
                "type": "circular_dependency",
                "task_id": cyc_tid,
                "severity": "critical",
                "message": f"Task {cyc_tid} is part of a circular dependency cycle"
            })
        
        return issues
    
    def _generate_suggestions(
        self,
        plan: ResearchPlan,
        issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate suggestions to fix issues"""
        suggestions = []
        
        for issue in issues:
            if issue["type"] == "missing_tool":
                tool = issue["item"]
                suggestions.append(
                    f"Replace {tool} with an available alternative or remove the requirement"
                )
            elif issue["type"] == "missing_agent":
                agent = issue["item"]
                suggestions.append(
                    f"Use a different agent than {agent} or restructure the task"
                )
            elif issue["type"] == "invalid_dependency":
                suggestions.append(
                    f"Fix dependency for task {issue['task_id']}"
                )
        
        return suggestions[:5]  # Limit suggestions
    
    def _generate_summary(
        self,
        is_approved: bool,
        score: float,
        issue_count: int,
        warning_count: int
    ) -> str:
        """Generate human-readable review summary"""
        if is_approved:
            return (
                f"APPROVED (score: {score:.2f}). "
                f"Plan is ready for execution. "
                f"{warning_count} minor warnings noted."
            )
        else:
            return (
                f"NEEDS REVISION (score: {score:.2f}). "
                f"Found {issue_count} issues and {warning_count} warnings. "
                f"Please address critical issues before proceeding."
            )


def review_research_plan(
    plan: ResearchPlan,
    llm_manager=None
) -> PlanReview:
    """
    Convenience function to review a research plan.
    
    Args:
        plan: Plan to review
        llm_manager: LLM manager (uses singleton if None)
        
    Returns:
        PlanReview
    """
    reviewer = PlanReviewer(llm_manager=llm_manager)
    return reviewer.review(plan)
