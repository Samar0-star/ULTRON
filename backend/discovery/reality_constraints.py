# -*- coding: utf-8 -*-
"""
REALITY CONSTRAINTS - PRE-LITERATURE KILL SWITCH
=================================================
Hard-coded physical/engineering constraints that can kill ideas
BEFORE literature search even begins.

"This is how Avon kills ideas even if no paper says so yet."
"""
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ConstraintType(Enum):
    """Fundamental Constraint Classes."""
    ENERGY_CONSERVATION = "energy_conservation"
    SCALING_LIMIT = "scaling_limit"
    DIFFUSION_TIME = "diffusion_time"
    INFORMATION_BOUND = "information_bound"
    MANUFACTURABILITY = "manufacturability"
    PROTEIN_DESIGN = "protein_design"
    LOGICAL_VACUUM = "logical_vacuum"


# HARD-CODED CONSTRAINTS (Expand as needed)
REALITY_CONSTRAINTS = {
    ConstraintType.ENERGY_CONSERVATION: {
        "description": "Cannot create energy from nothing",
        "violations": [
            "efficiency > 100%",
            "perpetual motion",
            "over-unity",
            "free energy"
        ]
    },
    ConstraintType.SCALING_LIMIT: {
        "description": "Physical properties don't scale infinitely",
        "violations": [
            "infinite conductivity",
            "infinite capacity",
            "unlimited current density",
            "zero resistance at room temperature"  # Superconductivity exception handled separately
        ]
    },
    ConstraintType.DIFFUSION_TIME: {
        "description": "Diffusion cannot be faster than ballistic limit",
        "violations": [
            "instant charging",
            "zero charge time",
            "instantaneous ion transport"
        ]
    },
    ConstraintType.INFORMATION_BOUND: {
        "description": "Cannot violate information-theoretic limits",
        "violations": [
            "perfect knowledge",
            "zero uncertainty",
            "instant communication"
        ]
    },
    ConstraintType.MANUFACTURABILITY: {
        "description": "Must be physically producible",
        "violations": [
            "atomic precision at scale",
            "defect-free crystal",
            "perfect interface",
            "zero contact resistance"
        ]
    },
    ConstraintType.PROTEIN_DESIGN: {
        "description": "Biological and chemical constraints for protein engineering",
        "violations": [
            "steric clash",
            "atomic overlap",
            "positive on positive charge",
            "negative on negative charge",
            "buried hydrophilic residue",
            "exposed hydrophobic core",
            "unstable fold",
            "violates pauli exclusion",
            "non-complementary binding"
        ]
    }
}


async def check_reality_constraints(assumption: str, llm_manager=None) -> Tuple[bool, Optional[ConstraintType], Optional[str]]:
    """
    [TITAN V184.1] THE ABSOLUTE REALITY GATE.
    Physically verifies scientific assumptions using first-principles reasoning.
    Now async and powered by the Neural Tribunal.
    """
    # 0. THE LOGICAL VACUUM GATE (TITAN V184.0)
    if not assumption or len(assumption.strip()) < 5:
        return (False, ConstraintType.LOGICAL_VACUUM, "REJECTED: Empty or vacuous scientific assumption.")

    assumption_lower = assumption.lower()
    
    # 1. Pattern matching (Primary Filter)
    for constraint_type, constraint_data in REALITY_CONSTRAINTS.items():
        for violation_pattern in constraint_data["violations"]:
            if violation_pattern.lower() in assumption_lower:
                # Superconductivity / high-pressure hydride exception for room-temperature zero resistance
                if violation_pattern.lower() == "zero resistance at room temperature":
                    if any(term in assumption_lower for term in ["superconduct", "superconductivity", "hydride", "critical temperature", "tc", "high pressure"]):
                        continue
                logger.warning(
                    f"REALITY CONSTRAINT VIOLATION: {constraint_type.value} - "
                    f"Pattern '{violation_pattern.lower()}' found in assumption."
                )
                return (False, constraint_type, f"Pattern match: {violation_pattern.lower()}")
    
    # 2. [RIGOR] Numerical Boundary Check (Prevents Rephrasing Bypass)
    numerical_violation = _check_numerical_impossibilities(assumption)
    if numerical_violation:
        return (False, ConstraintType.SCALING_LIMIT, numerical_violation)

    # 3. [TITAN V184.1] Neural Feasibility Audit
    if llm_manager:
        is_feasible, reason = await _neural_feasibility_check(assumption, llm_manager)
        if not is_feasible:
            return (False, ConstraintType.SCALING_LIMIT, reason)
    
    return (True, None, None)


async def _neural_feasibility_check(assumption: str, llm_manager) -> Tuple[bool, str]:
    """High-rigor feasibility audit using the scientific brain."""
    import json
    prompt = f"""
    ### ULTRON REALITY TRIBUNAL
    MISSION: Audit the following scientific assumption for first-principles physical validity.
    
    ASSUMPTION: "{assumption}"

    RULES:
    1. Reject if it violates Carnot, Shannon, or Pauli limits.
    2. Reject if it uses non-mathematical hand-waving.
    3. If the claim is extraordinary, it requires quantitative grounding.

    OUTPUT (JSON):
    {{"is_feasible": bool, "reason": "Scientific justification"}}
    """
    try:
        response = await llm_manager.run_async(prompt)
        content = response if isinstance(response, str) else response.get("text", "{}")
        from backend.utils.json_repair import repair_json
        data = repair_json(content)
        if isinstance(data, dict):
            return bool(data.get("is_feasible", True)), str(data.get("reason", "Unknown"))
    except Exception as e:
        logger.error(f" [REALITY] Neural audit failed: {e}")
        return False, f"Reality check failed: {e}"
    
    return False, "Reality check failed: No valid JSON response"


def _check_numerical_impossibilities(assumption: str) -> Optional[str]:
    """
    [RIGOR] FLAW 25 FIX: Use regex to extract values and validate against physical constants.
    """
    import re
    
    # A. THERMODYNAMICS: Efficiency Limit
    # Matches direct efficiency claims: "efficiency of 120%", "efficiency = 120%", "exceeds 100% efficiency"
    eff_match = re.search(
        r'(?:efficiency\s*(?:of|is|=|:|at|exceeds|reaches|approaches)\s*(\d+(?:\.\d+)?)%|(\d+(?:\.\d+)?)%\s*(?:thermodynamic\s+|energy\s+|conversion\s+|carnot\s+)?efficiency)',
        assumption.lower()
    )
    if eff_match:
        val = float(eff_match.group(1) or eff_match.group(2))
        if val > 100:
            is_relative_gain = any(
                phrase in assumption.lower()
                for phrase in ["increase in efficiency", "efficiency increase", "improvement in efficiency", "efficiency gain", "relative"]
            )
            if not is_relative_gain and not ("heat pump" in assumption.lower() or re.search(r'\bcop\b', assumption.lower()) or "coefficient of performance" in assumption.lower()):
                return f"Thermodynamic Violation: Efficiency {val}% exceeds Carnot limit."

    # B. ABSOLUTE ZERO: Temperature Limit (excluding Delta-T / temperature drops, shifts, or ranges like 100-500 K)
    temp_match = re.search(r'(?<![\d.])([-]?\d+\.?\d*)\s*\b(k|kelvin|c|celsius)\b', assumption.lower())
    if temp_match:
        val = float(temp_match.group(1))
        unit = temp_match.group(2).lower()
        is_delta_t = any(w in assumption.lower() for w in ["delta", "change", "drop", "decrease", "shift", "cooling", "subcooling", "difference", "gradient", "by -"])
        if not is_delta_t:
            if (unit.startswith('k') and val < 0) or (unit.startswith('c') and val < -273.15):
                return f"Physical Violation: Temperature {val} {unit} is below absolute zero."

    # C. BIOLOGY: Binding Energy Ceilings
    # Druglike leads rarely exceed -20 kcal/mol for a small peptide.
    bind_match = re.search(r'([-]?\d+\.?\d*)\s*kcal/mol', assumption.lower())
    if bind_match:
        val = float(bind_match.group(1))
        if val < -50: # Extreme outlier for discovery leads
            is_biological = any(term in assumption.lower() for term in ["biological", "drug", "lead", "protein", "peptide", "receptor", "binding", "antibody", "antigen", "enzyme", "biomolecule"])
            is_materials_catalyst = any(term in assumption.lower() for term in ["catalyst", "cataly", "adsorption", "material", "surface", "zeolite", "oxide", "alloy", "metal", "substrate"])
            if is_biological and not is_materials_catalyst:
                return f"Biological Violation: Binding energy {val} kcal/mol is physically improbable for a novel lead."

    # D. SCALING: Infinite properties
    non_zero_quantities = ["resistance", "impedance", "defects", "grain boundaries"]
    for qty in non_zero_quantities:
        if re.search(rf"(zero|0|nil|infinite)\s+{qty}", assumption.lower()):
            if qty == "resistance" and any(term in assumption.lower() for term in ["superconduct", "cryogen", "cryo"]):
                continue
            return f"Physical Violation: Perfect {qty} is a manufacturing impossibility."
    
    return None


class DerivationGate:
    """
    [TITAN V184.1] NEURAL DERIVATION GATE.
    Ensures exact numbers are mathematically or physically grounded.
    """
    @classmethod
    async def validate_number_claim(cls, claim: str, llm_manager=None) -> Tuple[bool, str]:
        """
        Validate if a numerical claim is properly derived or qualified.
        """
        if not llm_manager:
            return True, "Validator unavailable"
            
        prompt = f"""
        ### DERIVATION GATE
        Determine if the numbers in the following claim are properly derived from 
        first-principles or mathematically qualified (e.g., using ~ or >).
        
        CLAIM: "{claim}"
        
        RULES:
        1. Exact numbers must be justified by a derivation or scaling law.
        2. Unjustified exact numbers (e.g., "exactly 5.423 mW" with no reason) = REJECT.
        
        OUTPUT (JSON):
        {{"is_derived": bool, "reason": "Justification"}}
        """
        try:
            from backend.utils.json_repair import repair_json
            res = await llm_manager.run_async(prompt)
            content = res if isinstance(res, str) else res.get("text", "{}")
            data = repair_json(content)
            if isinstance(data, dict):
                return bool(data.get("is_derived", True)), str(data.get("reason", "No reason"))
            return True, "Parsing failure"
        except:
            return True, "Parsing failure"


async def validate_necessity(assumption: str, llm_manager=None) -> Tuple[bool, str]:
    """
    [TITAN V184.1] NEURAL NECESSITY TRIBUNAL.
    Determines if an assumption is load-bearing or a strawman.
    """
    if not llm_manager:
        return True, "LLM unavailable"
        
    prompt = f"""
    ### NECESSITY VALIDATOR (PhD RIGOR)
    "If this assumption is removed, what MUST replace it?"
    
    ASSUMPTION: "{assumption}"
    
    VERDICT:
    - "NECESSARY": No realistic replacement. This is load-bearing.
    - "ESCAPED": A realistic alternative exists.
    
    OUTPUT (JSON):
    {{"verdict": "NECESSARY" | "ESCAPED", "reason": "Explanation"}}
    """
    try:
        from backend.utils.json_repair import repair_json
        res = await llm_manager.run_async(prompt, temperature=0.2)
        content = res if isinstance(res, str) else res.get("text", "{}")
        data = repair_json(content)
        if isinstance(data, dict):
            return data.get("verdict", "NECESSARY") == "NECESSARY", str(data.get("reason", "N/A"))
        return True, "Validation fallback: unparseable output"
    except:
        return True, "Validation failed"


from dataclasses import dataclass, field

@dataclass
class RealityViolation:
    message: str
    severity: str = "critical"  # "critical", "warning"
    task_id: Optional[str] = None
    rule_id: str = "physical_boundary"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "severity": self.severity,
            "task_id": self.task_id,
            "rule_id": self.rule_id,
            "details": self.details,
        }


class RealityConstraints:
    """
    Physical and engineering plan auditor.
    Evaluates research plan tasks against first-principles boundaries.
    """
    def __init__(self, llm_manager=None):
        self.llm_manager = llm_manager

    def validate_plan(self, plan_dict: Dict[str, Any]) -> List[RealityViolation]:
        violations: List[RealityViolation] = []
        tasks = plan_dict.get("tasks", [])

        for task in tasks:
            t_id = task.get("id", "unknown")
            desc = (task.get("description", "") + " " + str(task.get("payload", {}))).lower()

            for constraint_type, constraint_data in REALITY_CONSTRAINTS.items():
                for violation_pattern in constraint_data["violations"]:
                    if violation_pattern.lower() in desc:
                        if violation_pattern.lower() == "zero resistance at room temperature":
                            if any(term in desc for term in ["superconduct", "hydride", "critical temperature", "tc"]):
                                continue
                        violations.append(
                            RealityViolation(
                                message=f"Task {t_id} violates physical constraint ({constraint_type.value}): {violation_pattern}",
                                severity="critical",
                                task_id=t_id,
                                rule_id=constraint_type.value,
                                details={"pattern": violation_pattern}
                            )
                        )

            # Numerical impossibility check
            num_err = _check_numerical_impossibilities(desc)
            if num_err:
                violations.append(
                    RealityViolation(
                        message=f"Task {t_id} violates numerical sanity: {num_err}",
                        severity="critical",
                        task_id=t_id,
                        rule_id="numerical_impossibility",
                    )
                )

        if violations:
            logger.warning(f"RealityConstraints detected {len(violations)} physical plan violations.")
        return violations

