"""
Hypothesis Prioritizer for ULTRON Deep Mode
=============================================

Ranks hypotheses using multi-criteria scoring:
1. Novelty (from novelty checker)
2. Feasibility (resource estimates)
3. Impact (LLM prediction)
4. Testability (LLM assessment)

"""

import logging
import json
from typing import Any, Dict, List, Optional

from backend.core.hypothesis.models import (
    Hypothesis,
    HypothesisState,
    PriorityRanking,
    TestabilityReport
)
from backend.llm_manager import PRIORITY_SCORING_MODEL

logger = logging.getLogger(__name__)


class HypothesisPrioritizer:
    """
    Prioritize and rank hypotheses using multi-criteria analysis.
    
    Combines novelty, feasibility, impact, and testability into
    a single priority score for ranking.
    
    Example:
        ```python
        prioritizer = HypothesisPrioritizer(llm_manager=llm_manager)
        ranked = prioritizer.prioritize(hypotheses)
        
        for hyp in ranked[:3]:
            print(f"Priority {hyp.priority_score}: {hyp.statement[:50]}")
        ```
    """
    
    DEFAULT_WEIGHTS = {
        "novelty": 0.25,
        "feasibility": 0.25,
        "impact": 0.30,
        "testability": 0.20
    }
    
    def __init__(
        self,
        llm_manager=None,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize hypothesis prioritizer.
        
        Args:
            llm_manager: LLM manager for impact/testability prediction
            weights: Scoring weights (novelty, feasibility, impact, testability)
        """
        self.llm_manager = llm_manager
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        
        # Normalize weights
        total = sum(self.weights.values())
        if total != 1.0:
            self.weights = {k: v/total for k, v in self.weights.items()}
        
        # Lazy load llm_manager
        if self.llm_manager is None:
            try:
                from backend.llm_manager import llm_manager
                self.llm_manager = llm_manager
            except ImportError:
                logger.warning("LLM manager not available for prioritization")
        
        logger.info(f"HypothesisPrioritizer initialized (weights={self.weights})")
    
    def prioritize(
        self,
        hypotheses: List[Hypothesis],
        run_analysis: bool = True
    ) -> List[Hypothesis]:
        """
        Prioritize and rank a list of hypotheses.
        
        Args:
            hypotheses: List of hypotheses to prioritize
            run_analysis: Whether to run impact/testability analysis if missing
            
        Returns:
            List of hypotheses sorted by priority (highest first)
        """
        logger.info(f"Prioritizing {len(hypotheses)} hypotheses")
        
        rankings = []
        
        for hyp in hypotheses:
            # Fill in missing scores if needed
            if run_analysis:
                self._ensure_scores(hyp)
            
            # Calculate weighted priority
            ranking = self._calculate_priority(hyp)
            rankings.append((hyp, ranking))
        
        # Sort by priority score
        rankings.sort(key=lambda x: x[1].priority_score, reverse=True)
        
        # Assign ranks and update hypotheses
        for i, (hyp, ranking) in enumerate(rankings):
            ranking.rank = i + 1
            hyp.priority_score = ranking.priority_score
            # DO NOT mutate the internal state machine here; prioritize() should be read-only for states.
        
        logger.info(f"Prioritization complete. Top score: {rankings[0][1].priority_score:.2f}" if rankings else "No hypotheses")
        
        return [hyp for hyp, _ in rankings]
    
    def _ensure_scores(self, hypothesis: Hypothesis) -> None:
        """Ensure hypothesis has all required scores"""
        if hypothesis.novelty_score is None:
            hypothesis.novelty_score = 0.5  # Default if not checked
        
        if hypothesis.feasibility_score is None:
            hypothesis.feasibility_score = self._estimate_feasibility(hypothesis)
        
        if hypothesis.impact_score is None:
            hypothesis.impact_score = self._predict_impact(hypothesis)
        
        if hypothesis.testability_score is None:
            report = self._assess_testability(hypothesis)
            hypothesis.testability_score = report.testability_score
    
    def _calculate_priority(self, hypothesis: Hypothesis) -> PriorityRanking:
        """Calculate weighted priority score"""
        w = self.weights
        
        novelty = hypothesis.novelty_score if hypothesis.novelty_score is not None else 0.5
        feasibility = hypothesis.feasibility_score if hypothesis.feasibility_score is not None else 0.5
        impact = hypothesis.impact_score if hypothesis.impact_score is not None else 0.5
        testability = hypothesis.testability_score if hypothesis.testability_score is not None else 0.5
        
        weighted_novelty = novelty * w["novelty"]
        weighted_feasibility = feasibility * w["feasibility"]
        weighted_impact = impact * w["impact"]
        weighted_testability = testability * w["testability"]
        
        priority_score = weighted_novelty + weighted_feasibility + weighted_impact + weighted_testability
        
        rationale = self._generate_rationale(novelty, feasibility, impact, testability)
        
        return PriorityRanking(
            hypothesis_id=hypothesis.id,
            priority_score=priority_score,
            rank=0,  # Will be set after sorting
            novelty_weight=w["novelty"],
            feasibility_weight=w["feasibility"],
            impact_weight=w["impact"],
            testability_weight=w["testability"],
            weighted_novelty=weighted_novelty,
            weighted_feasibility=weighted_feasibility,
            weighted_impact=weighted_impact,
            weighted_testability=weighted_testability,
            rationale=rationale
        )
    
    def _estimate_feasibility(self, hypothesis: Hypothesis) -> float:
        """
        Estimate feasibility score based on structural complexity.
        """
        import re
        # Base feasibility score
        score = 0.8
        
        # Structural complexity penalty (more parameters/variables is harder/requires more data)
        num_vars = len(getattr(hypothesis, "variables", []))
        num_params = len(getattr(hypothesis, "parameters", []))
        
        # Penalize by number of degrees of freedom
        score -= min(0.3, num_vars * 0.04)
        score -= min(0.3, num_params * 0.05)
        
        # Mathematical equation complexity penalty
        func_form = getattr(hypothesis, "functional_form", "")
        if func_form:
            # Count mathematical operators/symbols as a proxy for equation fitting complexity
            op_count = sum(func_form.count(op) for op in ["+", "-", "*", "/", "**", "log", "exp"])
            score -= min(0.2, op_count * 0.02)

        return max(0.1, min(1.0, score))
    
    def _predict_impact(self, hypothesis: Hypothesis) -> float:
        """
        Predict scientific impact using LLM.
        """
        if not self.llm_manager:
            return self._heuristic_impact(hypothesis)
        
        impact_prompt = f"""You are a senior research programme director reviewing a hypothesis for a high‑risk, high‑reward grant.
You must predict the *expected scientific impact* if the hypothesis is experimentally confirmed.
Do not guess — you must consider the full structure of the hypothesis.

SCIENTIFIC HYPOTHESIS:
Statement: {hypothesis.statement}
Domain: {hypothesis.domain}
Rationale: {getattr(hypothesis, 'rationale', 'Not provided')}
Variables: {json.dumps(getattr(hypothesis, 'variables', []), indent=2)}
Parameters: {json.dumps(getattr(hypothesis, 'parameters', []), indent=2)}
Functional Form: {getattr(hypothesis, 'functional_form', 'Not specified')}
Predictions: {json.dumps(getattr(hypothesis, 'predictions', []), indent=2)}
Falsification Criteria: {getattr(hypothesis, 'falsification_criteria', 'Not specified')}

────────────────────────────────────────────────────────
IMPACT ASSESSMENT FRAMEWORK (execute internally):
────────────────────────────────────────────────────────

1. **Scientific Novelty & Depth**
   – Does the hypothesis introduce a fundamentally new mechanism, a previously unrecognised coupling, or a non‑trivial mathematical structure? Rate 0.0 (trivial restatement) to 0.4 (genuinely transformative).

2. **Domain‑Wide Implications**
   – If true, would it change the foundational assumptions of the field? Would it open new experimental directions or kill existing research programmes? Rate 0.0 (affects only a niche sub‑problem) to 0.3 (reshapes the entire field).

3. **Translational / Application Potential**
   – Could it lead to new technologies, clinical outcomes, or industrial processes? How broad is the application? Rate 0.0 (no foreseeable application) to 0.2 (immediate, high‑value societal benefit).

4. **Rarity & Competitive Landscape**
   – Is this hypothesis one that few others are pursuing? Does it address a recognised critical gap? Rate 0.0 (crowded area, incremental) to 0.1 (unique, high‑risk/high‑reward).

5. **Falsifiability & Conclusiveness**
   – If confirmed, would the experiment be definitive? Does the hypothesis make precise, quantitative predictions that can be cleanly falsified? A hypothesis that cannot be decisively tested has low real‑world impact regardless of its intellectual appeal. This acts as a multiplier (0.0 – 1.0) on the sum of the above scores.

────────────────────────────────────────────────────────
OUTPUT FORMAT (strict JSON only, no prose):
────────────────────────────────────────────────────────
{{
  "impact_score": 0.0 to 1.0,
  "breakdown": {{
    "novelty_depth": 0.0,
    "domain_implications": 0.0,
    "application_potential": 0.0,
    "rarity_competitive": 0.0,
    "falsifiability_multiplier": 1.0
  }},
  "justification": "One paragraph of specific, citable reasoning that mentions the mechanism, the variables involved, and why this impact score is appropriate."
}}

RULES:
- The final impact_score = (novelty_depth + domain_implications + application_potential + rarity_competitive) * falsifiability_multiplier, clamped to [0.0, 1.0].
- If the hypothesis is too vague (no mechanism, no predictions), reflect that by setting falsifiability_multiplier to 0.1 and note the deficiency.
- Do not simply output 0.7 or 0.5. The score must be defensible.
- Return ONLY the JSON.
"""

        try:
            from backend.utils.json_repair import repair_json
            import re
            result = self.llm_manager.run(
                prompt=impact_prompt,
                model=PRIORITY_SCORING_MODEL,
                temperature=0.2,
                timeout=120
            )
            text = result.get("text", "") if isinstance(result, dict) else str(result)
            text = text.strip()
            if text:
                parsed = repair_json(text)
                if isinstance(parsed, dict) and "impact_score" in parsed:
                    return max(0.0, min(1.0, float(parsed["impact_score"])))
                key_match = re.search(r'"impact_score"\s*:\s*([0-9]*\.?[0-9]+)', text)
                if key_match:
                    return max(0.0, min(1.0, float(key_match.group(1))))
            return self._heuristic_impact(hypothesis)
        except Exception as e:
            logger.error(f"Impact prediction failed: {e}")
            return self._heuristic_impact(hypothesis)
    
    def _heuristic_impact(self, hypothesis: Hypothesis) -> float:
        """Heuristic-based impact scoring (fallback)"""
        score = 0.5
        statement = hypothesis.statement.lower()
        
        # High-impact indicators
        if any(term in statement for term in ["novel", "first", "breakthrough", "paradigm"]):
            score += 0.2
        
        if any(term in statement for term in ["general", "universal", "fundamental"]):
            score += 0.15
        
        # Lower impact indicators
        if any(term in statement for term in ["incremental", "minor", "specific case"]):
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _assess_testability(self, hypothesis: Hypothesis) -> TestabilityReport:
        """
        Assess testability based on structural clarity of variables, parameters and predictions.
        """
        # Methodology clarity scales with structured predictions and falsification criteria
        methodology_clarity = 0.5
        
        preds = getattr(hypothesis, "predictions", [])
        if preds:
            # Reward having multiple structured predictions with baselines and thresholds
            valid_preds = sum(
                1 for p in preds
                if (isinstance(p, dict) and p.get("baseline") is not None and p.get("threshold") is not None)
                or (isinstance(p, str) and len(p.strip()) > 3)
            )
            methodology_clarity += min(0.4, valid_preds * 0.1)
        
        if getattr(hypothesis, "falsification_criteria", ""):
            methodology_clarity += 0.1
            
        # Data availability is higher if variables have explicit names and empirical ranges
        data_availability = 0.5
        vars_list = getattr(hypothesis, "variables", [])
        if vars_list:
            vars_with_range = sum(
                1 for v in vars_list
                if (isinstance(v, dict) and v.get("empirical_range") is not None)
                or (isinstance(v, str) and len(v.strip()) > 1)
            )
            data_availability += min(0.4, vars_with_range * 0.1)
        else:
            data_availability = 0.3
            
        # Resource requirements is tied directly to the feasibility score
        feasibility = hypothesis.feasibility_score
        if feasibility is None:
            feasibility = self._estimate_feasibility(hypothesis)
        resource_requirements = feasibility
        
        # Clamp values
        data_availability = max(0.1, min(1.0, data_availability))
        methodology_clarity = max(0.1, min(1.0, methodology_clarity))
        resource_requirements = max(0.1, min(1.0, resource_requirements))
        
        # Weighted average
        testability_score = (
            data_availability * 0.3 +
            methodology_clarity * 0.4 +
            resource_requirements * 0.3
        )
        
        return TestabilityReport(
            hypothesis_id=hypothesis.id,
            testability_score=testability_score,
            is_testable=testability_score >= 0.5,
            data_availability=data_availability,
            methodology_clarity=methodology_clarity,
            resource_requirements=resource_requirements,
            time_estimate_hours=self._estimate_time(hypothesis),
            suggested_experiment_type=self._suggest_experiment_type(hypothesis),
            summary=f"Testability: {testability_score:.2f}"
        )
    
    def _estimate_time(self, hypothesis: Hypothesis) -> float:
        """Estimate time to test hypothesis (in hours)"""
        # Base time
        hours = 2.0
        
        statement = hypothesis.statement.lower()
        
        if "simple" in statement or "quick" in statement:
            hours *= 0.5
        if "complex" in statement or "extensive" in statement:
            hours *= 2
        if "ml" in hypothesis.domain or "training" in statement:
            hours *= 3
        
        return min(hours, 24.0)  # Cap at 24 hours
    
    def _suggest_experiment_type(self, hypothesis: Hypothesis) -> str:
        """Suggest experiment type based on hypothesis"""
        statement = hypothesis.statement.lower()
        
        if "model" in statement or "accuracy" in statement:
            return "ml_experiment"
        if "data" in statement or "analysis" in statement:
            return "data_analysis"
        if "compare" in statement or "versus" in statement:
            return "comparative_study"
        if "correlation" in statement or "relationship" in statement:
            return "statistical_analysis"
        
        return "general_experiment"
    
    def _generate_rationale(
        self,
        novelty: float,
        feasibility: float,
        impact: float,
        testability: float
    ) -> str:
        """Generate human-readable priority rationale"""
        factors = []
        
        if novelty >= 0.7:
            factors.append("high novelty")
        elif novelty <= 0.3:
            factors.append("low novelty")
        
        if impact >= 0.7:
            factors.append("high potential impact")
        elif impact <= 0.3:
            factors.append("limited impact")
        
        if feasibility >= 0.7:
            factors.append("highly feasible")
        elif feasibility <= 0.3:
            factors.append("resource-intensive")
        
        if testability >= 0.7:
            factors.append("easily testable")
        elif testability <= 0.3:
            factors.append("difficult to test")
        
        if factors:
            return "Priority based on: " + ", ".join(factors)
        return "Moderate priority across all factors"


def prioritize_hypotheses(
    hypotheses: List[Hypothesis],
    llm_manager=None,
    weights: Optional[Dict[str, float]] = None
) -> List[Hypothesis]:
    """
    Convenience function to prioritize hypotheses.
    
    Args:
        hypotheses: List to prioritize
        llm_manager: LLM manager (uses singleton if None)
        weights: Scoring weights
        
    Returns:
        Sorted list (highest priority first)
    """
    prioritizer = HypothesisPrioritizer(llm_manager=llm_manager, weights=weights)
    return prioritizer.prioritize(hypotheses)
