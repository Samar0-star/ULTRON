"""Additional chemistry templates with physically grounded workflows."""
from backend.experiments.templates.base import SimulationTemplate, DataAnalysisTemplate, TemplateCustomizationParams
from backend.experiments.templates import register_template
from backend.experiments.models import ExperimentProtocol, ExperimentType, ProtocolStep, Variable, ResourceRequirements


@register_template
class ReactionKineticsTemplate(DataAnalysisTemplate):
    """Chemical reaction kinetics analysis grounded in observed measurements."""
    def __init__(self):
        super().__init__(
            name="reaction_kinetics",
            domain="chemistry",
            title="Reaction Kinetics Analysis",
            description="Analyze reaction rates, rate constants, and mechanisms from observed data.",
            suitable_for=["Michaelis-Menten", "Arrhenius", "Rate law determination"],
            requirements=["Concentration vs time data", "Temperature data"],
            complexity_score=0.6, rigor_score=0.9
        )
    
    def is_applicable(self, hypothesis) -> bool:
        s = str(hypothesis).lower()
        return any(kw in s for kw in ['kinetic', 'rate constant', 'reaction rate', 'arrhenius', 'activation energy'])
    
    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title="Reaction Kinetics Analysis",
            hypothesis_id="unknown", experiment_type=ExperimentType.DATA_ANALYSIS, domain="chemistry",
            steps=[ProtocolStep(name="fit_kinetics", description="Load the measured reaction dataset, fit the rate law, and report the inferred kinetic parameters.", code_template="# ZERO-SHOT MANDATE: Load the observed reaction dataset and implement kinetic parameter estimation from scratch.", expected_output="Rate constants")],
            expected_duration_hours=0.5
        )


@register_template
class QuantumChemistryTemplate(SimulationTemplate):
    """DFT and ab initio calculations using real molecular geometry inputs."""
    def __init__(self):
        super().__init__(
            name="quantum_chemistry",
            domain="chemistry",
            title="Quantum Chemistry Calculations",
            description="DFT, Hartree-Fock, and post-HF calculations for molecular properties using the provided structure.",
            suitable_for=["Molecular orbitals", "Reaction barriers", "Spectroscopic properties"],
            requirements=["Molecular geometry", "Basis set specification"],
            complexity_score=0.95, rigor_score=0.95
        )
    
    def is_applicable(self, hypothesis) -> bool:
        s = str(hypothesis).lower()
        return any(kw in s for kw in ['dft', 'hartree-fock', 'molecular orbital', 'gaussian', 'basis set', 'ab initio'])
    
    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title="Quantum Chemistry: DFT Calculation",
            hypothesis_id="unknown", experiment_type=ExperimentType.COMPUTATIONAL, domain="chemistry",
            steps=[ProtocolStep(name="dft_calc", description="Load the actual molecular geometry, configure the quantum chemistry calculation, and compute energy and orbitals.", code_template="# ZERO-SHOT MANDATE: Implement the full DFT workflow from the supplied molecular geometry and basis specification.", expected_output="Energy and orbitals")],
            expected_duration_hours=2.0
        )


@register_template
class SpectroscopyTemplate(DataAnalysisTemplate):
    """Spectroscopic data analysis on measured spectra."""
    def __init__(self):
        super().__init__(
            name="spectroscopy_analysis",
            domain="chemistry",
            title="Spectroscopy Analysis",
            description="Analyze NMR, IR, UV-Vis, and mass spectrometry data from the observed spectra.",
            suitable_for=["Structure elucidation", "Peak assignment", "Quantification"],
            requirements=["Spectral data", "Reference spectra"],
            complexity_score=0.7, rigor_score=0.85
        )
    
    def is_applicable(self, hypothesis) -> bool:
        s = str(hypothesis).lower()
        return any(kw in s for kw in ['nmr', 'ir spectrum', 'uv-vis', 'mass spec', 'ftir', 'raman'])
    
    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title="Spectroscopy Analysis",
            hypothesis_id="unknown", experiment_type=ExperimentType.DATA_ANALYSIS, domain="chemistry",
            steps=[ProtocolStep(name="peak_analysis", description="Load the experimental spectra, detect peaks, and assign them using the referenced library or standards.", code_template="# ZERO-SHOT MANDATE: Implement spectral peak detection and assignment from the real spectrum inputs.", expected_output="Peak assignments")],
            expected_duration_hours=0.5
        )


@register_template
class RetrosynthesisTemplate(SimulationTemplate):
    """Retrosynthetic analysis for drug synthesis using reaction databases."""
    def __init__(self):
        super().__init__(
            name="retrosynthesis",
            domain="chemistry",
            title="Retrosynthetic Analysis",
            description="Retrosynthetic planning using reaction databases and actual target molecules.",
            suitable_for=["Drug synthesis", "Natural product synthesis", "Route optimization"],
            requirements=["Target molecule SMILES", "Reaction database access"],
            complexity_score=0.85, rigor_score=0.8
        )
    
    def is_applicable(self, hypothesis) -> bool:
        s = str(hypothesis).lower()
        return any(kw in s for kw in ['synthesis', 'retrosynthesis', 'reaction route', 'precursor'])
    
    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title="Retrosynthetic Analysis",
            hypothesis_id="unknown", experiment_type=ExperimentType.COMPUTATIONAL, domain="chemistry",
            steps=[ProtocolStep(name="retro_search", description="Load the target molecule and reaction database, then perform retrosynthetic route enumeration from scratch.", code_template="# ZERO-SHOT MANDATE: Implement retrosynthetic route search using the target molecule and reaction database inputs.", expected_output="Retrosynthetic routes")],
            expected_duration_hours=1.0
        )
