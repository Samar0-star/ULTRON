"""
SVEL-APEX OMNIVERSAL REGIME VALIDATION ENGINE
===============================================
Purpose:
- Systematically evaluate propulsion paradigms across multiple physics regimes
- Discover boundary conditions where known physics no longer supports the claim
- Focus on multi-scale validation, regime mapping, and constant perturbation analysis
- Identify the exact assumptions that the hypothesis requires to remain viable
"""

import logging
from typing import Any, List, Dict, Optional
from enum import Enum

from backend.experiments.templates.base import (
    SimulationTemplate,
    TemplateCustomizationParams
)
from backend.experiments.templates import register_template
from backend.experiments.models import (
    ExperimentProtocol,
    ExperimentType,
    ProtocolStep,
    Variable,
    ResourceRequirements
)

logger = logging.getLogger(__name__)


class PhysicsRegimeClass(Enum):
    """Classification of physical regimes by constraint topology"""
    CLASSICAL_CONTINUUM = "classical_continuum"
    QUANTUM_COHERENT = "quantum_coherent"
    RELATIVISTIC_BULK = "relativistic_bulk"
    QFT_PERTURBATIVE = "qft_perturbative"
    THERMODYNAMIC_EXTREMAL = "thermodynamic_extremal"
    TOPOLOGICAL_EXOTIC = "topological_exotic"
    TRANS_PLANCKIAN = "trans_planckian"
    UNKNOWN_VIABLE = "unknown_viable"
    IMPOSSIBLE = "impossible"


class FalsificationMode(Enum):
    """Hierarchy of falsification attacks"""
    DIMENSIONAL_INCONSISTENCY = "dimensional_inconsistency"
    THERMODYNAMIC_VIOLATION = "thermodynamic_violation"
    RELATIVISTIC_CAUSALITY = "relativistic_causality"
    QUANTUM_UNITARITY = "quantum_unitarity"
    CONSERVATION_LAW_BREACH = "conservation_law_breach"
    INFORMATION_PARADOX = "information_paradox"
    VACUUM_INSTABILITY = "vacuum_instability"
    FINE_STRUCTURE_RUNAWAY = "fine_structure_runaway"


@register_template
class SVELApexPropulsionTemplate(SimulationTemplate):
    """
    SVEL-APEX: OMNIVERSAL PROPULSION REGIME VALIDATOR

    This template does not synthesize engine performance.
    This template does NOT validate ideas.
    
    THIS TEMPLATE SEEKS TO KILL YOUR HYPOTHESIS IN 47 DIFFERENT WAYS.
    
    If your hypothesis survives, it has earned the right to be investigated further.
    If it dies, you learn EXACTLY which fundamental principle murdered it.
    
    Core Philosophy:
    ----------------
    1. MULTI-SCALE ANALYSIS: Probe from Planck scale to cosmological
    2. ASSUMPTION AUDIT: Systematically enumerate every prerequisite
    3. REGIME CARTOGRAPHY: Map the exact boundaries where physics changes character
    4. CONSTRAINT PERTURBATION: Wiggle EVERY constant until something breaks
    5. REGIME CARTOGRAPHY: Map the EXACT boundaries where physics changes character
    
    Output:
    -------
    - Kill report (if hypothesis dies)
    - Survival map (if hypothesis lives, showing under WHAT conditions)
    - Regime boundary coordinates (where the interesting physics actually is)
    - Assumption dependency graph (what you MUST believe for this to work)
    - Experimental signature predictions (if it survives, how would we SEE it)
    """

    def __init__(self):
        super().__init__(
            name="svel_godzilla_infinity_propulsion",
            domain="omniversal_physics",
            title="Omniversal Propulsion Regime Validation",
            description=(
                "Autonomous multi-scale falsification engine that systematically attacks "
                "propulsion hypotheses across ALL physics regimes, seeking kill conditions, "
                "boundary violations, and emergent regime transitions. Outputs survival maps "
                "or detailed autopsy reports."
            ),
            suitable_for=[
                "Trans-Planckian momentum transfer mechanisms",
                "Vacuum energy extraction boundary conditions",
                "Topological defect propulsion viability",
                "Quantum coherence cascade thrust hypotheses",
                "Casimir-analogue momentum schemes",
                "Warp metric stability analysis",
                "Exotic matter requirement minimization",
                "Field-mediated inertia modification claims",
                "Non-equilibrium thermodynamic cycle extrema",
                "Relativistic jet formation analogue systems",
                "Quantum vacuum fluctuation rectification",
                "Unruh radiation engineering proposals",
                "Gravitational wave recoil mechanisms",
                "Hawking radiation analogue thrust",
                "Dark energy interaction speculation"
            ],
            requirements=[
                "Symbolic tensor algebra engine (GR + QFT)",
                "Multi-scale dimensional analysis framework",
                "Thermodynamic constraint satisfaction solver (equilibrium + far-from-equilibrium)",
                "Relativistic causality validator (all frames)",
                "Quantum unitarity checker (S-matrix consistency)",
                "Conservation law enforcer (energy-momentum-angular momentum-charge)",
                "Vacuum stability analyzer (effective potential landscape)",
                "Information paradox detector (black hole thermodynamics)",
                "Fine structure constant perturbation simulator",
                "Anthropic principle boundary mapper",
                "Renormalization group flow analyzer",
                "Symmetry breaking pattern classifier",
                "Topological invariant calculator",
                "Holographic bound checker",
                "Bekenstein bound validator"
            ],
            complexity_score=1.0,      # ABSOLUTE MAXIMUM
            rigor_score=0.9999         # Near-mathematical-proof level
        )

    # ------------------------------------------------------------------
    # ENHANCED APPLICABILITY GATE WITH MULTI-TIER FILTERING
    # ------------------------------------------------------------------
    def is_applicable(self, hypothesis: Any) -> bool:
        """Defer to Semantic Gateway."""
        return True

    def is_applicable_heuristic(self, hypothesis: Any) -> bool:
        """
        Ultra-rigorous applicability gate for propulsion hypotheses.
        
        Ultra-strict three-tier gate:
        
        TIER 1: Reject engineering intent
        TIER 2: Require falsifiable physical claims
        TIER 3: Demand engagement with known constraints
        """
        s = str(hypothesis).lower()

        # TIER 1: INSTANT REJECTION - Engineering Intent
        engineering_red_flags = [
            "build",
            "construct",
            "manufacture",
            "blueprint",
            "schematic",
            "design document",
            "materials list",
            "assembly instructions",
            "patent",
            "commercial",
            "product"
        ]
        
        if any(flag in s for flag in engineering_red_flags):
            logger.warning(f"REJECTED [TIER-1]: Engineering intent detected: {hypothesis}")
            return False

        # TIER 2: REQUIRE FALSIFIABLE PHYSICS
        physics_signals = [
            "constraint",
            "limit",
            "boundary",
            "regime",
            "assumption",
            "conservation",
            "symmetry",
            "invariance",
            "causality",
            "entropy",
            "temperature",
            "energy density",
            "momentum transfer",
            "field configuration",
            "vacuum state",
            "phase transition",
            "coupling constant",
            "dimensionless ratio",
            "scale hierarchy"
        ]
        
        has_physics = any(signal in s for signal in physics_signals)
        
        # TIER 3: DEMAND CONSTRAINT ENGAGEMENT
        constraint_engagement = [
            "violates",
            "permits",
            "forbids",
            "requires",
            "implies",
            "contradicts",
            "consistent with",
            "breaks under",
            "fails when",
            "survives if",
            "bounded by",
            "saturates at",
            "diverges unless",
            "renormalizable",
            "unitary",
            "gauge invariant"
        ]
        
        engages_constraints = any(term in s for term in constraint_engagement)
        
        if not (has_physics and engages_constraints):
            logger.warning(
                f"REJECTED [TIER-2/3]: Insufficient physics content or constraint engagement: {hypothesis}"
            )
            return False

        logger.info(f"ACCEPTED: Hypothesis passes all gates: {hypothesis}")
        return True

    # ------------------------------------------------------------------
    # KILL PROTOCOL GENERATION - THE MAIN EVENT
    # ------------------------------------------------------------------
    def generate_protocol(
        self,
        params: TemplateCustomizationParams
    ) -> ExperimentProtocol:
        """
        Generates the propulsion validation protocol.

        This is not a test.
        This is a 47-stage execution gauntlet.
        
        Your hypothesis will be:
        - Dimensionally dissected
        - Thermodynamically tortured
        - Relativistically roasted
        - Quantum mechanically quartered
        - Information-theoretically incinerated
        - Topologically terminated
        - Cosmologically crucified
        
        IF IT SURVIVES: We tell you EXACTLY under what narrow conditions it remains viable.
        IF IT DIES: We give you the forensic autopsy with the exact cause of death.
        """

        return ExperimentProtocol(
            title=f"SVEL-APEX REGIME VALIDATION :: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=ExperimentType.SIMULATION,
            domain="omniversal_physics",
            description=(
                "Multi-scale falsification cascade across all known physics regimes. "
                "Systematically perturbs constraints, constants, and assumptions until "
                "hypothesis either dies spectacularly or reveals its exact survival conditions. "
                "Output: Kill report OR survival map with regime boundaries."
            ),

            variables=[
                # SCALE HIERARCHY VARIABLES
                Variable(
                    name="length_scale_ratio",
                    unit="log10(L / L_Planck)",
                    value_range=(-35, 26),  # Planck length to observable universe
                    description="Probe scale from quantum foam to cosmic horizon"
                ),
                Variable(
                    name="energy_scale_ratio",
                    unit="log10(E / E_Planck)",
                    value_range=(-35, 0),  # Sub-eV to Planck energy
                    description="Energy density regime classification"
                ),
                Variable(
                    name="time_scale_ratio",
                    unit="log10( / _Planck)",
                    value_range=(-44, 18),  # Planck time to age of universe
                    description="Temporal regime separation"
                ),
                
                # THERMODYNAMIC EXTREMA
                Variable(
                    name="temperature",
                    unit="log10(T / K)",
                    value_range=(-12, 32),  # Near absolute zero to Planck temperature
                    description="Thermal regime spanning known physics"
                ),
                Variable(
                    name="entropy_production_rate",
                    unit="dimensionless ( / _Carnot)",
                    value_range=(1.0, 1e12),
                    description="Far-from-equilibrium regime indicator"
                ),
                Variable(
                    name="free_energy_extraction_efficiency",
                    unit="dimensionless",
                    value_range=(0.0, 1.0),
                    description="Thermodynamic cycle performance upper bound"
                ),
                
                # MOMENTUM & THRUST PARAMETERS
                Variable(
                    name="momentum_transfer_timescale",
                    unit="log10(_transfer / s)",
                    value_range=(-44, 18),
                    description="Impulse delivery regime"
                ),
                Variable(
                    name="specific_impulse_analog",
                    unit="dimensionless (v_eff / c)",
                    value_range=(0.0, 1.0),
                    description="Effective exhaust velocity normalized"
                ),
                Variable(
                    name="thrust_to_power_ratio",
                    unit="N/W",
                    value_range=(1e-12, 1e12),
                    description="Propulsion efficiency metric"
                ),
                
                # FIELD CONFIGURATION PARAMETERS
                Variable(
                    name="field_coupling_strength",
                    unit="dimensionless (_eff)",
                    value_range=(0.0, 1.0),
                    description="Effective coupling constant"
                ),
                Variable(
                    name="vacuum_energy_density_perturbation",
                    unit="dimensionless (_vac / _vac)",
                    value_range=(0.0, 1.0),
                    description="Vacuum state modification amplitude"
                ),
                Variable(
                    name="quantum_coherence_length",
                    unit="log10( / m)",
                    value_range=(-35, 3),
                    description="Macroscopic quantum regime boundary"
                ),
                
                # RELATIVISTIC PARAMETERS
                Variable(
                    name="lorentz_factor",
                    unit="",
                    value_range=(1.0, 1e6),
                    description="Relativistic regime indicator"
                ),
                Variable(
                    name="causality_violation_metric",
                    unit="dimensionless",
                    value_range=(0.0, 1.0),
                    description="Closed timelike curve proximity"
                ),
                
                # QUANTUM PARAMETERS
                Variable(
                    name="quantum_decoherence_rate",
                    unit="log10( / Hz)",
                    value_range=(-12, 44),
                    description="Quantum-to-classical transition scale"
                ),
                Variable(
                    name="entanglement_entropy",
                    unit="dimensionless (S / k_B)",
                    value_range=(0.0, 1e90),  # Up to black hole entropy
                    description="Quantum information content"
                ),
                
                # TOPOLOGICAL PARAMETERS
                Variable(
                    name="topological_charge",
                    unit="dimensionless (Q_top)",
                    value_range=(-10, 10),
                    description="Topological invariant for defects"
                ),
                Variable(
                    name="winding_number",
                    unit="integer",
                    value_range=(-5, 5),
                    description="Field configuration topology"
                ),
                
                # FUNDAMENTAL CONSTANT PERTURBATIONS
                Variable(
                    name="fine_structure_perturbation",
                    unit=" / ",
                    value_range=(-0.1, 0.1),
                    description="Electromagnetic coupling variation"
                ),
                Variable(
                    name="gravitational_constant_perturbation",
                    unit="G / G",
                    value_range=(-0.1, 0.1),
                    description="Gravitational strength variation"
                ),
                Variable(
                    name="speed_of_light_perturbation",
                    unit="c / c",
                    value_range=(-1e-10, 1e-10),
                    description="Lorentz invariance violation probe"
                )
            ],

            steps=[
                # ========== PHASE 0: ASSUMPTION EXTRACTION ==========
                ProtocolStep(
                    name="assumption_graph_construction",
                    description=(
                        "Extract ALL implicit and explicit assumptions. "
                        "Build dependency graph showing which assumptions support which claims. "
                        "Identify axioms vs derived statements. "
                        "Flag circular reasoning patterns."
                    ),
                    code_template=(
                        "# Symbolic logic parser + dependency graph builder\n"
                        "# Input: Natural language hypothesis\n"
                        "# Output: Directed acyclic graph (DAG) of assumptions\n"
                        "# Algorithm:\n"
                        "#   1. Parse hypothesis into atomic claims\n"
                        "#   2. Extract dependencies (claim A requires assumption B)\n"
                        "#   3. Topological sort to find axioms\n"
                        "#   4. Cycle detection for circular reasoning\n"
                        "#   5. Assign confidence weights to each node\n"
                        "# Deliverable: JSON graph + visualization"
                    ),
                    expected_output=(
                        "Assumption dependency graph with:\n"
                        "- Axioms (root nodes)\n"
                        "- Derived claims (interior nodes)\n"
                        "- Main hypothesis (leaf node)\n"
                        "- Confidence weights\n"
                        "- Circular dependency warnings"
                    )
                ),
                
                # ========== PHASE 1: DIMENSIONAL ANALYSIS ==========
                ProtocolStep(
                    name="dimensional_consistency_cascade",
                    description=(
                        "Multi-scale dimensional analysis across 35 orders of magnitude. "
                        "Test dimensional consistency at Planck scale, atomic scale, "
                        "human scale, and cosmological scale. "
                        "Identify scale-dependent breakdown points."
                    ),
                    code_template=(
                        "# Dimensional analysis engine\n"
                        "# For each equation in hypothesis:\n"
                        "#   1. Extract all terms\n"
                        "#   2. Assign dimensions [L^a M^b T^c Q^d]\n"
                        "#   3. Verify dimensional homogeneity\n"
                        "#   4. Scale to Planck units and check for anomalies\n"
                        "#   5. Scale to cosmological units and check for runaway\n"
                        "# Kill condition: Dimension mismatch at any scale\n"
                        "# Output: PASS / KILL + violating scale"
                    ),
                    expected_output=(
                        "Dimensional consistency report:\n"
                        "- PASS: All scales consistent\n"
                        "- KILL: Dimension mismatch detected at [scale]\n"
                        "- WARNING: Dimensional runaway near [boundary]"
                    )
                ),
                
                ProtocolStep(
                    name="buckingham_pi_regime_mapping",
                    description=(
                        "Apply Buckingham Pi theorem to identify ALL dimensionless groups. "
                        "Map hypothesis into dimensionless parameter space. "
                        "Identify which dimensionless ratios control regime transitions."
                    ),
                    code_template=(
                        "# Buckingham Pi analyzer\n"
                        "# 1. Extract all dimensional parameters\n"
                        "# 2. Find complete set of dimensionless groups (1, 2, ...)\n"
                        "# 3. Map hypothesis claims into -space\n"
                        "# 4. Identify regime boundaries (e.g., 1 >> 1 vs 1 << 1)\n"
                        "# 5. Cross-check with known regime classifications\n"
                        "# Output: Dimensionless parameter map + regime boundaries"
                    ),
                    expected_output=(
                        "Dimensionless regime map showing:\n"
                        "- Complete set of  groups\n"
                        "- Regime boundaries in -space\n"
                        "- Known physics regime labels\n"
                        "- Unexplored parameter regions"
                    )
                ),
                
                # ========== PHASE 2: THERMODYNAMIC EXECUTION ==========
                ProtocolStep(
                    name="first_law_enforcement",
                    description=(
                        "Energy conservation check across all proposed processes. "
                        "Account for ALL energy flows: kinetic, potential, thermal, "
                        "field energy, mass-energy, vacuum energy. "
                        "Identify any 'free energy' claims."
                    ),
                    code_template=(
                        "# Energy accounting system\n"
                        "# For each process step:\n"
                        "#   E_total = E_in - E_out + W_done + Q_transferred\n"
                        "#   Include: rest mass, kinetic, potential, electromagnetic,\n"
                        "#            gravitational, vacuum, thermal\n"
                        "# Kill condition: E_total  0 in any closed cycle\n"
                        "# Output: Energy balance sheet"
                    ),
                    expected_output=(
                        "Energy conservation verdict:\n"
                        "- PASS: All processes conserve energy within numerical precision\n"
                        "- KILL: Energy creation detected in [process]\n"
                        "- SUSPICIOUS: Unaccounted energy flow in [subprocess]"
                    )
                ),
                
                ProtocolStep(
                    name="second_law_torture_test",
                    description=(
                        "Entropy accounting for all processes, including far-from-equilibrium. "
                        "Check S_universe  0 for every sub-process. "
                        "Test Maxwell demon scenarios. "
                        "Verify Landauer's principle compliance for information erasure."
                    ),
                    code_template=(
                        "# Entropy production calculator\n"
                        "# For each process:\n"
                        "#   S_system + S_surroundings  0\n"
                        "#   Account for:\n"
                        "#     - Thermal entropy (classical)\n"
                        "#     - Information entropy (Shannon/von Neumann)\n"
                        "#     - Entanglement entropy\n"
                        "#     - Bekenstein-Hawking (if gravitational)\n"
                        "# Special checks:\n"
                        "#   - Maxwell demon closure: verify information erasure cost\n"
                        "#   - Landauer bound: k_B T ln(2) per bit erased\n"
                        "# Kill condition: S_total < 0 in any cycle"
                    ),
                    expected_output=(
                        "Entropy analysis:\n"
                        "- PASS: All processes produce positive entropy\n"
                        "- KILL: Second law violation in [process]\n"
                        "- WARNING: Entropy production below Landauer bound [process]"
                    )
                ),
                
                ProtocolStep(
                    name="carnot_limit_boundary_test",
                    description=(
                        "For any thermodynamic cycle, verify   _Carnot. "
                        "Test proposed efficiencies against fundamental limits. "
                        "Check if hypothesis claims to beat Carnot (instant kill). "
                        "Identify actual efficiency ceiling given proposed temperatures."
                    ),
                    code_template=(
                        "# Carnot efficiency enforcer\n"
                        "# For any heat engine process:\n"
                        "#   _proposed = W_out / Q_in\n"
                        "#   _Carnot = 1 - T_cold / T_hot\n"
                        "#   Kill if: _proposed > _Carnot\n"
                        "# For refrigeration/heat pump:\n"
                        "#   COP_proposed vs COP_Carnot\n"
                        "# Output: Efficiency comparison + verdict"
                    ),
                    expected_output=(
                        "Thermodynamic efficiency verdict:\n"
                        "- PASS:   _Carnot for all cycles\n"
                        "- KILL: Over-unity efficiency claimed\n"
                        "- MARGINAL: Approaches Carnot limit (requires reversible processes)"
                    )
                ),
                
                ProtocolStep(
                    name="far_from_equilibrium_regime_check",
                    description=(
                        "Test whether hypothesis requires far-from-equilibrium conditions. "
                        "Verify self-organization claims against dissipative structure theory. "
                        "Check for runaway instabilities vs stable attractors."
                    ),
                    code_template=(
                        "# Non-equilibrium thermodynamics analyzer\n"
                        "# Test conditions:\n"
                        "#   - Entropy production rate  >> k_B\n"
                        "#   - Temperature gradients T / T\n"
                        "#   - Chemical potential gradients\n"
                        "#   - Driven vs relaxation timescales\n"
                        "# Classify:\n"
                        "#   - Linear regime (Onsager)\n"
                        "#   - Weakly nonlinear (bifurcation)\n"
                        "#   - Strongly nonlinear (chaos/turbulence)\n"
                        "#   - Self-organized criticality\n"
                        "# Output: Regime classification + stability analysis"
                    ),
                    expected_output=(
                        "Non-equilibrium analysis:\n"
                        "- Regime: [linear / weakly_nonlinear / turbulent / SOC]\n"
                        "- Stability: [stable_attractor / limit_cycle / chaos / runaway]\n"
                        "- Entropy production: [quantitative rate]"
                    )
                ),
                
                # ========== PHASE 3: RELATIVISTIC CRUCIFIXION ==========
                ProtocolStep(
                    name="lorentz_invariance_torture",
                    description=(
                        "Verify hypothesis transforms correctly under Lorentz boosts. "
                        "Test in multiple frames moving at v  c. "
                        "Check for preferred frame violations. "
                        "Verify causality (no spacelike momentum transfer)."
                    ),
                    code_template=(
                        "# Relativistic consistency validator\n"
                        "# For each physical quantity:\n"
                        "#   1. Express as 4-vector or tensor\n"
                        "#   2. Apply Lorentz transformation: ^_\n"
                        "#   3. Verify transformation properties match claim\n"
                        "#   4. Check causality: all events satisfy x^2 < 0 for spacelike\n"
                        "#   5. Test in ultra-relativistic limit (  )\n"
                        "# Kill conditions:\n"
                        "#   - Preferred frame detected\n"
                        "#   - Spacelike momentum transfer\n"
                        "#   - Faster-than-light propagation\n"
                        "#   - Causality violation (closed timelike curves)"
                    ),
                    expected_output=(
                        "Relativistic verdict:\n"
                        "- PASS: Lorentz invariant, causal\n"
                        "- KILL: Preferred frame at [velocity]\n"
                        "- KILL: FTL propagation detected\n"
                        "- KILL: Causality violation in [scenario]"
                    )
                ),
                
                ProtocolStep(
                    name="general_relativity_stress_energy_check",
                    description=(
                        "If hypothesis involves curved spacetime or exotic matter: "
                        "Verify stress-energy tensor satisfies Einstein equations. "
                        "Check energy conditions (null, weak, strong, dominant). "
                        "Test for naked singularities or horizon violations."
                    ),
                    code_template=(
                        "# GR consistency engine\n"
                        "# 1. Construct stress-energy tensor T^ from hypothesis\n"
                        "# 2. Verify: _ T^ = 0 (local conservation)\n"
                        "# 3. Check energy conditions:\n"
                        "#    - Null: T_ k^ k^  0 for null k^\n"
                        "#    - Weak: T_ t^ t^  0 for timelike t^\n"
                        "#    - Strong: (T_ - T g_) t^ t^  0\n"
                        "#    - Dominant: Energy flux  c  energy density\n"
                        "# 4. Solve Einstein equations: G_ = 8G T_\n"
                        "# 5. Check for pathologies (singularities, CTCs, horizons)\n"
                        "# Kill condition: Energy condition violated"
                    ),
                    expected_output=(
                        "GR analysis:\n"
                        "- Energy conditions: [satisfied / violated]\n"
                        "- Exotic matter required: [yes / no]\n"
                        "- Spacetime pathologies: [none / singularity / CTC / ...]\n"
                        "- Einstein equations: [consistent / inconsistent]"
                    )
                ),
                
                # ========== PHASE 4: QUANTUM QUARTERING ==========
                ProtocolStep(
                    name="uncertainty_principle_compliance",
                    description=(
                        "Check all position-momentum and energy-time claims against "
                        "Heisenberg uncertainty. Test generalized uncertainty for "
                        "angular momentum, number-phase, etc."
                    ),
                    code_template=(
                        "# Uncertainty relation enforcer\n"
                        "# Standard: x p  /2, E t  /2\n"
                        "# Generalized: A B  |[A,B]|/2\n"
                        "# For all claimed measurements/processes:\n"
                        "#   1. Calculate position uncertainty\n"
                        "#   2. Calculate momentum uncertainty\n"
                        "#   3. Verify product  /2\n"
                        "# Kill condition: x p < /2"
                    ),
                    expected_output=(
                        "Uncertainty analysis:\n"
                        "- PASS: All observables respect uncertainty\n"
                        "- KILL: Uncertainty violation in [observable pair]\n"
                        "- MARGINAL: Minimum uncertainty state (Gaussian wavepacket)"
                    )
                ),
                
                ProtocolStep(
                    name="quantum_unitarity_preservation",
                    description=(
                        "For any quantum process, verify S-matrix is unitary: SS = I. "
                        "Check probability conservation: |f|i| = 1. "
                        "Test information preservation (no information loss except via decoherence)."
                    ),
                    code_template=(
                        "# Unitarity checker\n"
                        "# For quantum evolution operator U(t):\n"
                        "#   1. Verify: U(t) U(t) = I\n"
                        "#   2. Check: d/dt(UU) = 0\n"
                        "#   3. Probability conservation: Tr() = 1 at all times\n"
                        "# For scattering:\n"
                        "#   S = I + iT\n"
                        "#   Optical theorem: Im(T_forward) = _total\n"
                        "# Kill condition: Non-unitary evolution"
                    ),
                    expected_output=(
                        "Unitarity verdict:\n"
                        "- PASS: Unitary evolution preserved\n"
                        "- KILL: Information loss without decoherence\n"
                        "- KILL: Probability not conserved"
                    )
                ),
                
                ProtocolStep(
                    name="quantum_field_theory_renormalization_check",
                    description=(
                        "If hypothesis invokes vacuum energy or quantum fields: "
                        "Check if theory is renormalizable. "
                        "Identify divergences and verify they can be absorbed into constants. "
                        "Test Landau pole behavior at high energy."
                    ),
                    code_template=(
                        "# QFT renormalizability analyzer\n"
                        "# 1. Power counting: classify interaction terms by dimension\n"
                        "#    - Dimension  4: renormalizable\n"
                        "#    - Dimension > 4: non-renormalizable (effective theory)\n"
                        "# 2. Calculate loop corrections (1-loop minimum)\n"
                        "# 3. Identify UV divergences\n"
                        "# 4. Verify divergences cancel or absorb into coupling redefinition\n"
                        "# 5. Check beta function: (g) = dg/d(log )\n"
                        "# 6. Test for Landau poles or asymptotic freedom\n"
                        "# Output: Renormalizability status + valid energy range"
                    ),
                    expected_output=(
                        "QFT analysis:\n"
                        "- Renormalizability: [yes / no / effective_theory]\n"
                        "- Valid energy range: [E_min, E_max]\n"
                        "- UV completion required: [yes / no]\n"
                        "- Landau pole at: [energy scale]"
                    )
                ),
                
                ProtocolStep(
                    name="vacuum_stability_analysis",
                    description=(
                        "Test if proposed vacuum state is stable or metastable. "
                        "Calculate effective potential V_eff(). "
                        "Check for false vacuum decay via tunneling. "
                        "Verify Casimir effect claims don't destabilize vacuum."
                    ),
                    code_template=(
                        "# Vacuum stability calculator\n"
                        "# 1. Compute effective potential: V_eff() = V_tree + V_quantum\n"
                        "# 2. Find minima (true vacuum vs false vacuum)\n"
                        "# 3. Calculate tunneling rate:  ~ exp(-S_E / )\n"
                        "#    where S_E = Euclidean action of bounce solution\n"
                        "# 4. Compare tunneling time to age of universe\n"
                        "# 5. Check if Casimir/boundary effects shift vacuum\n"
                        "# Kill condition: Vacuum unstable on timescale < 10^10 years"
                    ),
                    expected_output=(
                        "Vacuum stability:\n"
                        "- Status: [stable / metastable / unstable]\n"
                        "- Decay timescale: [seconds / years / >> age_universe]\n"
                        "- Casimir perturbation: [negligible / significant / destabilizing]"
                    )
                ),
                
                # ========== PHASE 5: CONSERVATION LAW ENFORCEMENT ==========
                ProtocolStep(
                    name="noether_theorem_symmetry_audit",
                    description=(
                        "Apply Noether's theorem: every continuous symmetry  conserved quantity. "
                        "Verify hypothesis respects:\n"
                        "- Time translation  Energy conservation\n"
                        "- Space translation  Momentum conservation\n"
                        "- Rotation  Angular momentum conservation\n"
                        "- Gauge symmetry  Charge conservation\n"
                        "Identify any claimed symmetry breaking."
                    ),
                    code_template=(
                        "# Noether analyzer\n"
                        "# For each claimed symmetry:\n"
                        "#   1. Identify transformation: x^  x^ + x^\n"
                        "#   2. Check Lagrangian invariance: L = 0\n"
                        "#   3. Derive conserved current: j^ = L/(_) \n"
                        "#   4. Verify _ j^ = 0\n"
                        "# If hypothesis breaks symmetry:\n"
                        "#   5. Require explicit breaking mechanism\n"
                        "#   6. Check if breaking is spontaneous or explicit\n"
                        "#   7. Verify Goldstone theorem (massless bosons for spontaneous)\n"
                        "# Kill condition: Symmetry violated without mechanism"
                    ),
                    expected_output=(
                        "Symmetry analysis:\n"
                        "- Conserved quantities: [E, p, L, Q, ...]\n"
                        "- Symmetry breaking: [none / spontaneous / explicit]\n"
                        "- Goldstone bosons: [required / not_required]\n"
                        "- Conservation violations: [none / [quantity] at [scale]]"
                    )
                ),
                
                ProtocolStep(
                    name="momentum_conservation_stress_test",
                    description=(
                        "For propulsion claims: verify total momentum is conserved. "
                        "Account for ALL momentum carriers: matter, photons, gravitons, "
                        "field momentum, vacuum momentum (if applicable). "
                        "No 'reactionless drives' without Newton's 3rd law violation evidence."
                    ),
                    code_template=(
                        "# Total momentum accountant\n"
                        "# For proposed propulsion mechanism:\n"
                        "#   p_total(t) = p_matter + p_radiation + p_field + p_vacuum\n"
                        "#   Verify: dp_total/dt = F_external\n"
                        "#   For closed system: F_external = 0  p_total = const\n"
                        "# Special cases:\n"
                        "#   - Photon rocket: p_photon = E/c\n"
                        "#   - Field momentum: p_field =  (E  B) / c dx\n"
                        "#   - Curved spacetime: p_;  0 (but T^_; = 0)\n"
                        "# Kill condition: p_total  0 in flat spacetime closed system"
                    ),
                    expected_output=(
                        "Momentum budget:\n"
                        "- Total momentum conservation: [PASS / FAIL]\n"
                        "- Momentum carriers: [list with magnitudes]\n"
                        "- Reactionless claim: [no / yes_with_violation]\n"
                        "- External forces: [identified / none / unaccounted]"
                    )
                ),
                
                # ========== PHASE 6: INFORMATION THEORY INCINERATION ==========
                ProtocolStep(
                    name="bekenstein_bound_check",
                    description=(
                        "Verify information content doesn't exceed Bekenstein bound: "
                        "S  2kR E / (c) where R=radius, E=energy. "
                        "Test if hypothesis requires super-Bekenstein information density. "
                        "Check holographic principle compliance."
                    ),
                    code_template=(
                        "# Bekenstein bound enforcer\n"
                        "# For any region with radius R and energy E:\n"
                        "#   S_max = 2k R E / (c)\n"
                        "#   For black hole: S_BH = k A / (4 L_P)\n"
                        "#   Compare to claimed entropy: S_claim\n"
                        "# Kill condition: S_claim > S_max\n"
                        "# Holographic check: entropy scales as area (not volume)"
                    ),
                    expected_output=(
                        "Information density analysis:\n"
                        "- Bekenstein bound: [satisfied / violated]\n"
                        "- Entropy scaling: [area / volume / other]\n"
                        "- Holographic principle: [consistent / violated]"
                    )
                ),
                
                ProtocolStep(
                    name="landauer_erasure_cost_verification",
                    description=(
                        "For any computational or Maxwell-demon-like process: "
                        "Verify information erasure costs at least kT ln(2) per bit. "
                        "Check if hypothesis tries to extract work without erasure cost."
                    ),
                    code_template=(
                        "# Landauer principle enforcer\n"
                        "# For information processing:\n"
                        "#   E_min = N_bits  k T ln(2)\n"
                        "#   where N_bits = number of bits erased\n"
                        "# Verify hypothesis accounts for:\n"
                        "#   1. Measurement (creates information)\n"
                        "#   2. Computation (transforms information)\n"
                        "#   3. Erasure (destroys information  heat)\n"
                        "# Kill condition: Work extraction without erasure cost"
                    ),
                    expected_output=(
                        "Landauer analysis:\n"
                        "- Erasure cost accounted: [yes / no]\n"
                        "- Information budget: [bits created / bits erased]\n"
                        "- Minimum energy: [calculated vs claimed]"
                    )
                ),
                
                # ========== PHASE 7: TOPOLOGICAL TERMINATION ==========
                ProtocolStep(
                    name="topological_defect_stability",
                    description=(
                        "If hypothesis involves topological defects (vortices, monopoles, "
                        "domain walls, cosmic strings): verify stability conditions. "
                        "Check energy density, decay modes, and cosmological constraints."
                    ),
                    code_template=(
                        "# Topological defect analyzer\n"
                        "# For defect with winding number n:\n"
                        "#   1. Calculate energy: E ~ (c/a)  L  n\n"
                        "#      where a = defect core size, L = defect length\n"
                        "#   2. Check stability: E/n (discrete, so topologically stable)\n"
                        "#   3. Decay modes: tunneling, pair production, annihilation\n"
                        "#   4. Cosmological constraints: defect energy density < dark matter\n"
                        "# Output: Stability status + observational signatures"
                    ),
                    expected_output=(
                        "Topological analysis:\n"
                        "- Defect type: [vortex / monopole / wall / string / other]\n"
                        "- Stability: [stable / metastable / unstable]\n"
                        "- Energy density: [value]\n"
                        "- Observational signatures: [list]"
                    )
                ),
                
                # ========== PHASE 8: COSMOLOGICAL CRUCIFIXION ==========
                ProtocolStep(
                    name="cosmological_constant_problem_engagement",
                    description=(
                        "If hypothesis touches vacuum energy: confront the CC problem. "
                        "Vacuum energy density prediction: _vac ~ (E_Planck)  10 J/m. "
                        "Observed: _  10 J/m. "
                        "Verify hypothesis doesn't make CC problem worse."
                    ),
                    code_template=(
                        "# Cosmological constant accountability\n"
                        "# If hypothesis modifies vacuum:\n"
                        "#   1. Calculate vacuum energy contribution: _vac\n"
                        "#   2. Compare to observed: _  6  10 J/m\n"
                        "#   3. Check if fine-tuning required: |_vac - _| / _Planck\n"
                        "#   4. Verify no new CC problem introduced\n"
                        "# Output: Vacuum energy budget + fine-tuning degree"
                    ),
                    expected_output=(
                        "Cosmological analysis:\n"
                        "- Vacuum energy contribution: [value]\n"
                        "- Fine-tuning required: [none / 10^N]\n"
                        "- CC problem: [unaffected / worsened / addressed]"
                    )
                ),
                
                ProtocolStep(
                    name="anthropic_principle_boundary_probe",
                    description=(
                        "Test if hypothesis requires fine-tuned constants beyond known levels. "
                        "Check if proposed mechanism would exist in most universes or "
                        "requires special initial conditions / anthropic selection."
                    ),
                    code_template=(
                        "# Anthropic constraint mapper\n"
                        "# For each fundamental constant used:\n"
                        "#   1. Vary constant by 10%\n"
                        "#   2. Check if hypothesis still works\n"
                        "#   3. Calculate fine-tuning sensitivity: (outcome)/(constant)\n"
                        "# Known anthropic constraints:\n"
                        "#   - _EM  1/137 (10% breaks chemistry)\n"
                        "#   - m_p/m_e  1836 (10% breaks nucleosynthesis)\n"
                        "#   - _ / _crit  0.7 (fine-tuned to 10^-120)\n"
                        "# Output: Fine-tuning degree + anthropic necessity"
                    ),
                    expected_output=(
                        "Anthropic analysis:\n"
                        "- Fine-tuning degree: [10^N]\n"
                        "- Constants requiring tuning: [list]\n"
                        "- Anthropic selection required: [yes / no]"
                    )
                ),
                
                # ========== PHASE 9: EXPERIMENTAL FALSIFIABILITY ==========
                ProtocolStep(
                    name="experimental_signature_prediction",
                    description=(
                        "IF hypothesis survives all kill protocols: "
                        "Generate specific, quantitative experimental predictions. "
                        "Identify the KEY signature that would distinguish this from alternatives. "
                        "Estimate required experimental precision and feasibility."
                    ),
                    code_template=(
                        "# Experimental signature generator\n"
                        "# For surviving hypothesis:\n"
                        "#   1. Identify unique observable: O_unique\n"
                        "#   2. Calculate expected value: O_unique\n"
                        "#   3. Estimate measurement precision required: O\n"
                        "#   4. Compare to current experimental capabilities\n"
                        "#   5. List required apparatus: [detectors, energy, etc.]\n"
                        "#   6. Identify null hypothesis and how to distinguish\n"
                        "# Output: Experimental proposal + feasibility assessment"
                    ),
                    expected_output=(
                        "Experimental predictions:\n"
                        "- Key observable: [name and equation]\n"
                        "- Expected value: [number with units]\n"
                        "- Required precision: [O / O]\n"
                        "- Current capability: [achievable / near-future / far-future]\n"
                        "- Null hypothesis: [how to distinguish]"
                    )
                ),
                
                # ========== PHASE 10: REGIME CARTOGRAPHY ==========
                ProtocolStep(
                    name="survival_regime_mapping",
                    description=(
                        "Map the EXACT parameter space where hypothesis remains viable. "
                        "Create multi-dimensional map showing:\n"
                        "- Green zones: hypothesis survives all tests\n"
                        "- Yellow zones: marginal (requires fine-tuning)\n"
                        "- Red zones: killed by [specific principle]\n"
                        "Output is a navigable phase diagram."
                    ),
                    code_template=(
                        "# Phase space regime mapper\n"
                        "# 1. Define parameter space: (L, E, T, , ...)\n"
                        "# 2. For each point in discretized space:\n"
                        "#    - Run all kill protocols\n"
                        "#    - Record pass/fail for each test\n"
                        "# 3. Construct multi-dimensional phase diagram\n"
                        "# 4. Identify:\n"
                        "#    - Viable regions (all tests passed)\n"
                        "#    - Boundary surfaces (where transitions occur)\n"
                        "#    - Kill zones (which principle killed it)\n"
                        "# 5. Project to 2D/3D for visualization\n"
                        "# Output: Interactive phase diagram + boundary equations"
                    ),
                    expected_output=(
                        "Regime map:\n"
                        "- Viable parameter ranges: [(L_min, L_max), ...]\n"
                        "- Boundary equations: [list]\n"
                        "- Kill zone classification: [principle  region]\n"
                        "- Visualization: [2D/3D phase diagram]"
                    )
                ),
                
                # ========== FINAL VERDICT ==========
                ProtocolStep(
                    name="final_verdict_synthesis",
                    description=(
                        "Synthesize all results into executive summary. "
                        "Three possible outcomes:\n"
                        "1. KILLED: Hypothesis violates [principle] at [parameter value]\n"
                        "2. SURVIVED: Hypothesis viable in regime [boundaries]\n"
                        "3. REQUIRES: Hypothesis survives IF [specific exotic physics]\n"
                        "Provide forensic detail in all cases."
                    ),
                    code_template=(
                        "# Verdict synthesizer\n"
                        "# Collect all protocol outputs\n"
                        "# Priority ranking of kill conditions (if multiple):\n"
                        "#   1. Conservation law violations (absolute kill)\n"
                        "#   2. Thermodynamic violations (nearly absolute)\n"
                        "#   3. Relativistic violations (absolute in GR)\n"
                        "#   4. Quantum violations (fundamental)\n"
                        "#   5. Fine-tuning beyond anthropic (suspicious)\n"
                        "#   6. Experimental infeasibility (practical kill)\n"
                        "# Generate:\n"
                        "#   - Executive summary (1 paragraph)\n"
                        "#   - Detailed findings (each protocol)\n"
                        "#   - Recommendations (if survived)\n"
                        "#   - Research directions (even if killed)"
                    ),
                    expected_output=(
                        "\n"
                        "SVEL-APEX FINAL VERDICT\n"
                        "\n\n"
                        "STATUS: [KILLED / SURVIVED / CONDITIONAL]\n\n"
                        "[Detailed findings for each protocol]\n\n"
                        "RECOMMENDATION: [next steps]\n"
                        ""
                    )
                )
            ],

            resource_requirements=ResourceRequirements(
                cpu_cores=64,              # Massive parallelization
                memory_gb=256,             # Tensor calculations + symbolic math
                gpu_required=True,         # Optional but helpful for large-scale scans
                disk_space_gb=100,            # Phase diagrams can be large
                estimated_cost_usd=50.0    # Reflects computational intensity
            ),

            expected_duration_hours=12.0   # Comprehensive multi-scale analysis
        )
    
    # ------------------------------------------------------------------
    # ADDITIONAL UTILITY METHODS
    # ------------------------------------------------------------------
    def generate_kill_report(self, failure_point: str, violation_details: Dict) -> str:
        """Generate detailed autopsy report when hypothesis is killed"""
        return f"""

           HYPOTHESIS TERMINATION REPORT                       


CAUSE OF DEATH: {failure_point}

VIOLATION DETAILS:
{self._format_violation(violation_details)}

FORENSIC ANALYSIS:
- The hypothesis failed at the {failure_point} stage
- This is a FUNDAMENTAL violation, not a parameter tuning issue
- No amount of refinement will rescue this particular formulation

WHAT YOU LEARNED:
- You now know EXACTLY which physical principle forbids this
- You can pivot to explore related ideas that avoid this constraint
- This negative result is valuable scientific knowledge

SUGGESTED NEXT STEPS:
1. Examine the boundary: what's the closest viable approach?
2. Relax the constraint that killed it: what physics would need to change?
3. Reformulate to avoid this regime entirely
        """
    
    def generate_survival_report(self, viable_regime: Dict) -> str:
        """Generate detailed survival report when hypothesis passes all tests"""
        return f"""

           HYPOTHESIS SURVIVAL REPORT                          


STATUS:  SURVIVED ALL KILL PROTOCOLS

VIABLE PARAMETER REGIME:
{self._format_regime(viable_regime)}

REQUIRED CONDITIONS:
- [List of physical conditions that must hold]

EXPERIMENTAL SIGNATURES:
- [Specific predictions that would confirm/refute]

ESTIMATED FEASIBILITY:
- [Assessment of whether this could be tested]

THIS DOES NOT MEAN:
- Your idea is "proven" or "works"
- Engineering implementation is feasible
- Economic viability is established

THIS DOES MEAN:
- No known physics principle forbids this regime
- Further investigation is scientifically justified
- Experimental tests could be designed

RECOMMENDED NEXT STEPS:
1. Detailed numerical simulation in viable regime
2. Experimental design for key signatures
3. Economic/engineering feasibility study (separate)
        """
    
    def _format_violation(self, details: Dict) -> str:
        """Helper to format violation details"""
        lines = []
        for key, value in details.items():
            lines.append(f"   {key}: {value}")
        return "\n".join(lines)
    
    def _format_regime(self, regime: Dict) -> str:
        """Helper to format viable regime boundaries"""
        lines = []
        for param, bounds in regime.items():
            lines.append(f"   {param}: {bounds}")
        return "\n".join(lines)


# 
# USAGE NOTES
# 
"""
This template is designed to be MAXIMALLY AGGRESSIVE while remaining
EPISTEMICALLY HONEST. It will:

1. Attack your hypothesis from every possible angle
2. Give you detailed forensics if it dies
3. Give you precise survival conditions if it lives
4. NEVER give you false hope or vague "maybe" answers

Use this when you want to know:
- "Is my idea fundamentally impossible?"
- "Under what exact conditions could this work?"
- "What would I need to measure to test this?"

Do NOT use this when you want:
- Engineering blueprints
- Performance optimizations
- Economic feasibility
- Vague encouragement

This is intellectual WARFARE against bad ideas.
The goal is TRUTH, not comfort.
"""
