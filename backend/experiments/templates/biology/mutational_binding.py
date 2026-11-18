"""
ULTRON BIOLOGY DOMAIN: BIOPHYSICAL MUTATIONAL & STRUCTURAL TEMPLATES
=====================================================================
PhD-level biophysical analysis for protein interfaces, binding affinity (ddG),
thermodynamic stability, and crystallographic contact networks.
Enforces zero mock data and strict empirical grounding in SKEMPI-v2 and PDB files.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.experiments.templates.base import (
    TemplateBase,
    DataAnalysisTemplate,
    SimulationTemplate,
    StatisticalTemplate,
    TemplateCustomizationParams,
)
from backend.experiments.templates import register_template
from backend.experiments.models import (
    ExperimentProtocol,
    ProtocolStep,
    ExperimentType,
    Variable,
    ResourceRequirements,
)

logger = logging.getLogger("ultron.experiments.templates.biology")


@register_template
class BiophysicalMutationalBindingTemplate(DataAnalysisTemplate):
    """
    Template for empirical biophysical mutational affinity analysis.
    Validates changes in binding free energy (ddG) from empirical repositories (SKEMPI-v2)
    and evaluates thermodynamic parameters (Kd, deltaH, deltaS).
    """

    def __init__(self):
        super().__init__(
            name="biophysical_mutational_binding",
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="biology",
            title="Biophysical Mutational & Binding Affinity Analysis (ULTRON-APEX)",
            description=(
                "Empirical biophysical mutational analysis evaluating binding free energy "
                "changes (ddG), thermodynamic parameters (Kd, deltaH, deltaS), and "
                "electrostatic interactions from empirical databases (SKEMPI-v2)."
            ),
            suitable_for=[
                "protein-protein interaction",
                "SARS-CoV-2 Spike RBD",
                "ACE2 receptor binding",
                "mutational binding free energy",
                "SKEMPI empirical affinity",
                "affinity shift ddG",
                "thermodynamic stability",
                "epitope mutation impact",
            ],
            requirements=["pandas", "numpy", "scipy", "data/skempi_v2.csv"],
            complexity_score=0.85,
            rigor_score=1.0,
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        text = str(hypothesis).lower()
        keywords = [
            "spike", "rbd", "ace2", "skempi", "mutation", "mutant",
            "binding affinity", "free energy", "ddg", "kd", "thermodynamic",
            "n501y", "k417n", "e484k", "affinity", "electrostatic",
            "protein", "residue", "amino acid", "interface"
        ]
        return any(kw in text for kw in keywords)

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"Biophysical Mutational Binding Analysis: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="biology",
            description=self.description,
            steps=[
                ProtocolStep(
                    name="load_and_filter_empirical_mutations",
                    description=(
                        "1. Load empirical binding affinity dataset (e.g. data/skempi_v2.csv).\n"
                        "2. Filter records matching target protein complex (e.g. Spike RBD / ACE2 or target homologues).\n"
                        "3. Extract wild-type and mutant Kd, affinity shifts, and compute empirical ddG = R * T * ln(Kd_mut / Kd_wt).\n"
                        "4. Filter out any missing or ungrounded measurements."
                    ),
                    code_template="""# ZERO-SHOT EMPIRICAL MANDATE:
# Load SKEMPI-v2 dataset and compute mutational binding free energy shifts (ddG).
# DO NOT generate synthetic measurements. Rely strictly on empirical observations.
""",
                    expected_output="Curated mutation affinity dataframe with ddG",
                ),
                ProtocolStep(
                    name="inferential_biostatistical_test",
                    description=(
                        "1. Perform normality testing (Shapiro-Wilk) on wild-type vs mutant distributions.\n"
                        "2. Perform Levene variance equality test.\n"
                        "3. Calculate Welch's t-test or Mann-Whitney U for statistical significance.\n"
                        "4. Compute Cohen's d effect size and 95% BCa bootstrap confidence interval."
                    ),
                    code_template="""# INFERENTIAL STATISTICAL HYPOTHESIS TESTING:
# Compute exact p-value, effect size, and bootstrap confidence intervals on empirical distributions.
""",
                    expected_output="Statistical test diagnostics, p-value, effect size, and confidence interval",
                ),
            ],
            resource_requirements=ResourceRequirements(cpu_cores=4, memory_gb=8),
            expected_duration_hours=1.0,
        )


@register_template
class StructuralInterfaceBiophysicsTemplate(SimulationTemplate):
    """
    Template for crystallographic structural interface analysis.
    Parses PDB coordinate files (e.g. 6LZG) to measure residue-residue contact distances,
    hydrogen bonding networks, salt bridges, and buried surface areas at the binding interface.
    """

    def __init__(self):
        super().__init__(
            name="structural_interface_biophysics",
            experiment_type=ExperimentType.COMPUTATIONAL,
            domain="biology",
            title="Crystallographic Interface & Electrostatic Contact Analysis",
            description=(
                "First-principles structural analysis of protein-protein interfaces from "
                "crystallographic coordinates (PDB). Measures interatomic contact networks, "
                "salt bridges, hydrogen bonds, and electrostatic interface changes across variants."
            ),
            suitable_for=[
                "crystallographic interface",
                "PDB coordinates",
                "atomic contact network",
                "salt bridges and hydrogen bonds",
                "6LZG interface geometry",
                "structural biophysics",
                "electrostatic interface potential",
            ],
            requirements=["numpy", "scipy", "data/6lzg.pdb"],
            complexity_score=0.90,
            rigor_score=1.0,
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        text = str(hypothesis).lower()
        keywords = [
            "pdb", "crystallographic", "crystal structure", "6lzg", "contact",
            "distance", "salt bridge", "hydrogen bond", "interface geometry",
            "spatial", "atomic", "coordinate", "structure", "conformation"
        ]
        return any(kw in text for kw in keywords)

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"Structural Interface Biophysics: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=ExperimentType.COMPUTATIONAL,
            domain="biology",
            description=self.description,
            steps=[
                ProtocolStep(
                    name="parse_pdb_interface",
                    description=(
                        "1. Parse atomic coordinates from crystallography file (e.g. data/6lzg.pdb).\n"
                        "2. Isolate interacting chains (e.g. Chain A: human ACE2, Chain B: SARS-CoV-2 Spike RBD).\n"
                        "3. Compute all inter-chain atomic pairwise Euclidean distances.\n"
                        "4. Identify interface residues defined by distance cutoff < 5.0 Angstroms."
                    ),
                    code_template="""# ZERO-SHOT STRUCTURAL BIOPHYSICS MANDATE:
# Parse real PDB atomic coordinates and extract interface contact network.
# DO NOT fabricate atomic coordinates.
""",
                    expected_output="Residue contact distance matrix and interface residue list",
                ),
                ProtocolStep(
                    name="electrostatic_and_hbond_audit",
                    description=(
                        "1. Scan for putative salt bridges (basic Arg/Lys to acidic Asp/Glu within 4.0 A).\n"
                        "2. Scan for donor-acceptor hydrogen bonding pairs at key mutation sites (417, 484, 501).\n"
                        "3. Quantify how specific mutations (e.g. K417N loss of salt bridge with ACE2 D30) disrupt contacts."
                    ),
                    code_template="""# CONTACT NETWORK FALSIFICATION:
# Calculate electrostatic contact shifts and thermodynamic impact on interface stability.
""",
                    expected_output="Contact disruption metric and interaction classification",
                ),
            ],
            resource_requirements=ResourceRequirements(cpu_cores=4, memory_gb=8),
            expected_duration_hours=1.0,
        )


@register_template
class EmpiricalBiostatisticsTemplate(StatisticalTemplate):
    """
    Template for rigorous bio-statistical falsification and power analysis.
    Ensures empirical biological hypotheses undergo strict parametric/non-parametric tests.
    """

    def __init__(self):
        super().__init__(
            name="empirical_biostatistics",
            experiment_type=ExperimentType.STATISTICAL,
            domain="biology",
            title="Empirical Bio-statistical Rigor and Hypothesis Falsification",
            description=(
                "Inferential biostatistical testing pipeline: Normality tests (Shapiro-Wilk), "
                "variance equality (Levene), Welch's t-test or Mann-Whitney U, Cohen's d effect sizes, "
                "and 95% BCa bootstrap confidence intervals for biophysical experimental groups."
            ),
            suitable_for=[
                "biostatistical testing",
                "effect size estimation",
                "hypothesis falsification",
                "normality and variance testing",
                "bootstrap confidence intervals",
            ],
            requirements=["scipy", "statsmodels", "numpy", "pandas"],
            complexity_score=0.75,
            rigor_score=1.0,
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        text = str(hypothesis).lower()
        keywords = [
            "significance", "p-value", "statistical", "hypothesis", "falsif",
            "confidence interval", "effect size", "distribution", "cohen"
        ]
        return any(kw in text for kw in keywords)

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"Empirical Bio-statistical Rigor: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=ExperimentType.STATISTICAL,
            domain="biology",
            description=self.description,
            steps=[
                ProtocolStep(
                    name="rigorous_hypothesis_evaluation",
                    description="Execute assumption tests, inferential significance testing, and bootstrap confidence intervals.",
                    code_template="""# BIO-STATISTICAL EVALUATION:
# Execute full diagnostic suite with zero-shot empirical computation.
""",
                    expected_output="Inferential report with p-value, effect size, and confidence intervals",
                )
            ],
            resource_requirements=ResourceRequirements(cpu_cores=4, memory_gb=8),
            expected_duration_hours=0.5,
        )
