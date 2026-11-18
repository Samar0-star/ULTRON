"""
DYNAMIC STRATEGY ENGINE - Godzilla Tier
=======================================
This engine composes 'Skill Chains'sequences of Meta (T1) and Functional (T2) skills
tailored to specific research objectives.

It bridges the gap between high-level Meta-Reasoning and task-level execution.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.core.skill_injector import get_expert_system, Skill

logger = logging.getLogger(__name__)

class DynamicStrategyEngine:
    """
    Composes strategic battle plans by chaining specialized skills.
    """
    
    def __init__(self):
        self.expert_system = get_expert_system()
        
    def compose_battle_plan(self, objective: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a 'Skill Chain' for a given research objective.
        
        Args:
            objective: The research question or sub-task description.
            domain: The scientific domain (optional).
            
        Returns:
            A dictionary containing the meta-protocols and functional tools.
        """
        logger.info(f" Composing battle plan for: {objective}")
        
        # [V256] Normalise domain so the gate fires correctly
        effective_domain = (domain or "other").lower().replace(" ", "_").replace("-", "_")
        
        # 1. Select Meta-Protocol (T1)
        # We search for strategic skills that match the 'intent' of the objective
        meta_skills = self.expert_system.search_skills(objective, top_k=2, domain=effective_domain)
        meta_skills = [s for s in meta_skills if s.tier == "T1"]
        
        if not meta_skills:
            # Fallback to general research protocol
            if "hypothesis_generation_titan" in self.expert_system.meta_skills:
                meta_skills = [self.expert_system.meta_skills["hypothesis_generation_titan"]]
            else:
                meta_skills = []
                
        # 2. Select Functional Tools (T2)
        # Deep search for technical expertise
        functional_skills = self.expert_system.search_skills(objective, top_k=5, domain=effective_domain)
        functional_skills = [s for s in functional_skills if s.tier == "T2"]
        
        # 3. Build Chain
        battle_plan = {
            "objective": objective,
            "strategic_protocols": [s.name for s in meta_skills],
            "functional_tools": [s.name for s in functional_skills],
            "injected_context": self._build_context(meta_skills, functional_skills)
        }
        
        return battle_plan

    def _build_context(self, meta: List[Skill], functional: List[Skill]) -> str:
        """
        Formats the skill chain into a cohesive prompt block.
        """
        context = "#  [GODZILLA_BATTLE_PLAN] - Strategic Context\n"
        
        if meta:
            context += "\n## STRATEGIC PROTOCOLS (T1)\n"
            for s in meta:
                context += s.to_prompt_block(include_examples=False)
                
        if functional:
            context += "\n## FUNCTIONAL TOOLS & EXPERTISE (T2)\n"
            for s in functional:
                context += s.to_prompt_block(include_examples=True)
                
        return context

_strategy_engine_instance = None

def get_strategy_engine():
    global _strategy_engine_instance
    if _strategy_engine_instance is None:
        _strategy_engine_instance = DynamicStrategyEngine()
    return _strategy_engine_instance
