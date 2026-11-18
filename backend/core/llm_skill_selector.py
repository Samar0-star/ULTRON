"""
LLM-BASED SKILL SELECTOR - INTELLIGENT SKILL CHOOSER
====================================================
Instead of just embedding similarity, use an LLM to REASON about which skills
are most relevant for a given task.

This selector:
1. Presents the LLM with all available skills
2. Asks it to SELECT the most relevant ones
3. Gets REASONING for each selection
4. Returns ranked skills with explanations
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SkillSelection:
    """Result of LLM skill selection with reasoning."""
    skill_name: str
    relevance_score: float  # 0-1
    reasoning: str
    rank: int


class LLMSkillSelector:
    """
    Intelligent skill selector that uses an LLM to reason about skill relevance.
    
    Instead of pure embedding similarity, this asks an LLM:
    - "Which skills would help solve this task?"
    - "Why is each skill relevant?"
    - "Rank them by importance"
    """
    
    def __init__(self, llm_manager, expert_system):
        self.llm_manager = llm_manager
        self.expert_system = expert_system
    
    def select_skills_with_reasoning(
        self,
        task_description: str,
        skill_tier: str = "auto",  # T1, T2, or auto
        max_skills: int = 5
    ) -> List[SkillSelection]:
        """
        Use LLM to intelligently select and rank skills.
        
        Args:
            task_description: What the user wants to do
            skill_tier: "T1" (meta), "T2" (functional), or "auto"
            max_skills: Maximum number of skills to select
            
        Returns:
            List of SkillSelection objects with reasoning
        """
        
        # 1. Get available skills
        if skill_tier == "T1":
            available_skills = self.expert_system.meta_skills
        elif skill_tier == "T2":
            available_skills = getattr(self.expert_system, "functional_skills", getattr(self.expert_system, "meta_skills", {}))
        else:
            available_skills = self.expert_system.skills_cache
        
        # 2. Build skill catalog for LLM
        skill_catalog = self._build_skill_catalog(available_skills)
        
        # 3. Ask LLM to select and rank
        prompt = f"""
You are an expert research strategist choosing which skills/tools to use for a task.

**TASK DESCRIPTION:**
{task_description}

**AVAILABLE SKILLS:**
{skill_catalog}

**YOUR JOB:**
Select the {max_skills} MOST RELEVANT skills for this task.
For each skill, provide:
1. Skill name (exact match from catalog)
2. Relevance score (0.0 to 1.0)
3. Brief reasoning (one sentence: WHY this skill helps)

**SELECTION CRITERIA:**
- Direct applicability to the task
- Complementary coverage (avoid redundancy)
- Prioritize skills that fill critical gaps

**OUTPUT FORMAT (strict JSON):**
{{
    "selections": [
        {{
            "skill_name": "exact_skill_name_from_catalog",
            "relevance_score": 0.95,
            "reasoning": "Why this skill is critical for this task"
        }}
    ]
}}

Return ONLY JSON. No explanations outside the JSON.
"""
        
        try:
            # 4. Execute LLM selection using resolved routing model
            from backend.llm_manager import TASK_ROUTING_MODEL
            routing_model = TASK_ROUTING_MODEL[0] if isinstance(TASK_ROUTING_MODEL, tuple) else TASK_ROUTING_MODEL
            result = self.llm_manager.run(
                prompt=prompt,
                model=routing_model,  # Fast model for selection
                temperature=0.2,      # Low temp for consistency
                max_tokens_override=None
            )
            
            # 5. Parse response
            from backend.utils.json_repair import repair_json
            raw_text = result.get("text", "") if isinstance(result, dict) else str(result)
            data = repair_json(raw_text)
            if isinstance(data, dict):
                selections = data.get("selections", [])
            elif isinstance(data, list):
                selections = data
            else:
                selections = []
            
            # 6. Validate and rank
            validated = []
            for idx, sel in enumerate(selections[:max_skills]):
                skill_name = sel.get("skill_name")
                
                # Verify skill exists
                if skill_name not in available_skills:
                    logger.warning(f"LLM selected non-existent skill: {skill_name}")
                    continue
                
                validated.append(SkillSelection(
                    skill_name=skill_name,
                    relevance_score=sel.get("relevance_score", 0.5),
                    reasoning=sel.get("reasoning", "No reasoning provided"),
                    rank=idx + 1
                ))
            
            logger.info(f" LLM selected {len(validated)} skills with reasoning")
            return validated
            
        except Exception as e:
            logger.error(f"LLM skill selection failed: {e}")
            # Fallback to semantic search
            return self._fallback_to_semantic(task_description, max_skills)
    
    def _build_skill_catalog(self, skills: Dict[str, Any]) -> str:
        """
        Build a compact catalog of skills for the LLM.
        Format: name | description | domain
        """
        catalog_lines = []
        items = skills.items() if isinstance(skills, dict) else [(getattr(s, "name", str(s)), s) for s in skills]
        for name, skill in list(items)[:50]:  # Limit to 50 to fit in context
            desc = getattr(skill, "description", str(skill))[:100]
            dom = getattr(skill, "domain", "general")
            catalog_lines.append(
                f"- **{name}**: {desc} [Domain: {dom}]"
            )
        
        return "\n".join(catalog_lines)
    
    def _fallback_to_semantic(self, query: str, max_skills: int) -> List[SkillSelection]:
        """Fallback to semantic search if LLM selection fails."""
        logger.warning("Falling back to semantic search")
        
        semantic_skills = self.expert_system.search_skills(query, top_k=max_skills)
        
        return [
            SkillSelection(
                skill_name=s.name,
                relevance_score=0.7,  # Default score
                reasoning="Selected via semantic similarity (fallback)",
                rank=idx + 1
            )
            for idx, s in enumerate(semantic_skills)
        ]
    
    def inject_skills_with_llm_selection(
        self,
        base_prompt: str,
        task_description: str,
        skill_tier: str = "auto",
        max_skills: int = 5,
        include_reasoning: bool = True
    ) -> str:
        """
        Complete injection pipeline with LLM selection.
        
        Returns:
            Enhanced prompt with skills + reasoning for selection
        """
        # 1. LLM selects skills
        selections = self.select_skills_with_reasoning(
            task_description=task_description,
            skill_tier=skill_tier,
            max_skills=max_skills
        )
        
        if not selections:
            return base_prompt
        
        # 2. Build injection header
        if skill_tier == "T1":
            header = "\n#  [STRATEGIC_PROTOCOL] - SELECTED META-SKILLS\n"
        else:
            header = "\n#  [FUNCTIONAL_EXPERTISE] - SELECTED DOMAIN SKILLS\n"
        
        if include_reasoning:
            header += "\n**SKILL SELECTION REASONING:**\n"
            for sel in selections:
                header += f"{sel.rank}. **{sel.skill_name}** (relevance: {sel.relevance_score:.2f})\n"
                header += f"    {sel.reasoning}\n"
            header += "\n---\n\n"
        
        # 3. Inject actual skill content
        skill_blocks = []
        for sel in selections:
            if sel.skill_name in self.expert_system.skills_cache:
                skill = self.expert_system.skills_cache[sel.skill_name]
                skill.usage_count = getattr(skill, "usage_count", 0) + 1
                skill_blocks.append(skill.to_prompt_block(include_examples=True))
        
        # 4. Assemble
        footer = "\n# \n"
        
        return header + "\n".join(skill_blocks) + footer + base_prompt


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def demo_llm_skill_selection():
    """Demonstrate LLM-based skill selection."""
    
    print("=" * 80)
    print("LLM-BASED SKILL SELECTOR DEMO")
    print("=" * 80)
    
    # Mock setup
    from backend.core.skill_injector import get_expert_system
    from backend.llm_manager import get_llm_manager
    
    expert = get_expert_system()
    llm_manager = get_llm_manager()
    
    selector = LLMSkillSelector(llm_manager, expert)
    
    # Example task
    task = """
    Analyze single-cell RNA-seq data from CRISPR-edited T cells.
    Find differentially expressed genes and visualize the results.
    """
    
    print(f"\n TASK: {task.strip()}")
    print("\n LLM SELECTING SKILLS...\n")
    
    # LLM selects skills
    selections = selector.select_skills_with_reasoning(
        task_description=task,
        skill_tier="T2",  # Functional skills
        max_skills=5
    )
    
    # Display results
    print(" SELECTED SKILLS:\n")
    for sel in selections:
        print(f"{sel.rank}. {sel.skill_name}")
        print(f"   Relevance: {sel.relevance_score:.2f}")
        print(f"   Reasoning: {sel.reasoning}")
        print()
    
    # Show enhanced prompt (excerpt)
    base_prompt = "Generate Python code for the task above."
    enhanced = selector.inject_skills_with_llm_selection(
        base_prompt=base_prompt,
        task_description=task,
        skill_tier="T2",
        max_skills=3,
        include_reasoning=True
    )
    
    print("=" * 80)
    print("ENHANCED PROMPT (EXCERPT):")
    print("=" * 80)
    print(enhanced[:1000] + "...")


if __name__ == "__main__":
    demo_llm_skill_selection()
