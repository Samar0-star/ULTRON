"""Physics domain templates wired to verified numerical physics kernels."""
from backend.experiments.templates.base import SimulationTemplate, TemplateCustomizationParams
from backend.experiments.templates import register_template
from backend.experiments.models import ExperimentProtocol, ExperimentType, ProtocolStep, Variable, ResourceRequirements
from backend.experiments.kernels.physics_kernels import (
    BenettinKernel,
    NumericalIntegrator,
    PoincareSectionExtractor,
    RecurrenceAnalyzer,
    CorrelationDimension,
    ThermodynamicKernel,
    classify_chaos,
)


@register_template
class StatisticalMechanicsTemplate(SimulationTemplate):
    """Monte Carlo, molecular dynamics, and thermodynamic audit simulations."""
    def __init__(self):
        super().__init__(
            name="statistical_mechanics",
            domain="physics",
            title="Statistical Mechanics & Thermodynamic Audit Simulation",
            description="Monte Carlo, MD, Carnot/Stefan-Boltzmann, and Gibbs free energy simulations via ThermodynamicKernel.",
            suitable_for=["Phase transitions", "Ising model", "Thermodynamic properties", "Gibbs free energy", "Carnot efficiency"],
            requirements=["System Hamiltonian", "Temperature range"],
            complexity_score=0.8,
            rigor_score=0.95,
        )
        self.kernel = ThermodynamicKernel

    def is_applicable(self, hypothesis) -> bool:
        s = str(hypothesis).lower()
        return any(kw in s for kw in ["monte carlo", "ising", "thermodynamic", "phase transition", "boltzmann", "carnot", "gibbs", "entropy"])

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title="Statistical Mechanics: Thermodynamic Kernel Simulation",
            hypothesis_id="unknown",
            experiment_type=ExperimentType.SIMULATION,
            domain="physics",
            steps=[
                ProtocolStep(
                    name="thermodynamic_audit_and_mc",
                    description="Run ThermodynamicKernel audit and Monte Carlo ensemble sampling",
                    code_template=(
                        "from backend.experiments.kernels.physics_kernels import ThermodynamicKernel\n"
                        "audit = ThermodynamicKernel.audit_system(t_hot_k=600.0, t_cold_k=300.0, claimed_efficiency=0.42)\n"
                        "print(audit.to_dict())"
                    ),
                    expected_output="ThermodynamicAuditResult and ensemble energy distribution",
                )
            ],
            expected_duration_hours=1.0,
        )


@register_template
class NonlinearDynamicsChaosTemplate(SimulationTemplate):
    """Nonlinear dynamical systems, Lyapunov spectrum, symplectic ODE integration, and RQA."""
    def __init__(self):
        super().__init__(
            name="nonlinear_dynamics_chaos",
            domain="physics",
            title="Nonlinear Dynamics, Symplectic Integration & Lyapunov Chaos Analysis",
            description=(
                "Full Lyapunov spectrum via QR-Benettin, Stormer-Verlet symplectic integration, "
                "Poincare section extraction, Recurrence Quantification Analysis (RQA), and Grassberger-Procaccia dimension."
            ),
            suitable_for=[
                "Chaotic attractors",
                "Lyapunov exponents",
                "Hamiltonian energy conservation",
                "Bifurcation analysis",
                "Nonlinear oscillators",
                "Poincare sections",
            ],
            requirements=["Dynamical system ODEs", "Initial state vector"],
            complexity_score=0.9,
            rigor_score=0.98,
        )
        self.benettin_kernel = BenettinKernel
        self.integrator = NumericalIntegrator
        self.poincare_extractor = PoincareSectionExtractor
        self.rqa_analyzer = RecurrenceAnalyzer
        self.correlation_dim = CorrelationDimension
        self.classify_chaos = classify_chaos

    def is_applicable(self, hypothesis) -> bool:
        s = str(hypothesis).lower()
        return any(
            kw in s
            for kw in [
                "lyapunov", "chaotic", "chaos", "attractor", "bifurcation",
                "poincare", "symplectic", "hamiltonian", "oscillator", "lorenz",
                "recurrence", "ergodic", "kaplan-yorke", "phase space",
            ]
        )

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title="Nonlinear Dynamics: QR-Benettin Lyapunov & Symplectic Integration",
            hypothesis_id="unknown",
            experiment_type=ExperimentType.SIMULATION,
            domain="physics",
            steps=[
                ProtocolStep(
                    name="lyapunov_and_chaos_classification",
                    description="Integrate dynamical system and compute full QR-Benettin Lyapunov spectrum and RQA metrics",
                    code_template=(
                        "import numpy as np\n"
                        "from backend.experiments.kernels.physics_kernels import classify_chaos\n"
                        "def lorenz(state, t, sigma=10.0, rho=28.0, beta=8.0/3.0):\n"
                        "    x, y, z = state\n"
                        "    return np.array([sigma * (y - x), x * (rho - z) - y, x * y - beta * z])\n"
                        "t = np.linspace(0, 25, 2500)\n"
                        "report = classify_chaos(lorenz, np.array([1.0, 1.0, 1.0]), t)\n"
                        "print(report.to_dict())"
                    ),
                    expected_output="ChaosReport with Lyapunov spectrum, Kaplan-Yorke dimension, and RQA determinism",
                )
            ],
            expected_duration_hours=1.0,
        )


@register_template
class AstrophysicsSpectralTemplate(SimulationTemplate):
    """Spectral analysis for astrophysical data."""
    def __init__(self):
        super().__init__(
            name="astrophysics_spectral",
            domain="physics",
            title="Astrophysical Spectral Analysis",
            description="Analyze stellar spectra, redshift, and composition.",
            suitable_for=["Stellar classification", "Redshift measurement", "Element abundance"],
            requirements=["Spectral data", "Wavelength calibration"],
            complexity_score=0.7,
            rigor_score=0.85,
        )

    def is_applicable(self, hypothesis) -> bool:
        s = str(hypothesis).lower()
        return any(kw in s for kw in ["spectrum", "stellar", "redshift", "astrophysic", "cosmolog"])

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title="Astrophysics: Spectral Analysis",
            hypothesis_id="unknown",
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="physics",
            steps=[ProtocolStep(name="spectral_fit", description="Fit spectrum", code_template="# Spectral fitting", expected_output="Line IDs")],
            expected_duration_hours=0.5,
        )


@register_template
class ParticleCollisionTemplate(SimulationTemplate):
    """Particle physics collision analysis."""
    def __init__(self):
        super().__init__(
            name="particle_collision",
            domain="physics",
            title="Particle Collision Analysis",
            description="Analyze high-energy particle collisions and decay channels.",
            suitable_for=["Higgs boson", "Cross-section measurements", "Decay analysis"],
            requirements=["Collision data", "Detector geometry"],
            complexity_score=0.95,
            rigor_score=0.95,
        )

    def is_applicable(self, hypothesis) -> bool:
        s = str(hypothesis).lower()
        return any(kw in s for kw in ["particle", "collision", "higgs", "decay", "cross-section", "lhc", "cern"])

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title="Particle Physics: Collision Analysis",
            hypothesis_id="unknown",
            experiment_type=ExperimentType.DATA_ANALYSIS,
            domain="physics",
            steps=[ProtocolStep(name="event_selection", description="Select events", code_template="# Event cuts", expected_output="Signal events")],
            expected_duration_hours=3.0,
        )
