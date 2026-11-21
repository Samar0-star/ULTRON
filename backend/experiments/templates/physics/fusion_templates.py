"""
SVEL-APEX PLASMA FUSION TEMPLATE v1.0
=======================================
High-fidelity simulation template for fusion plasma research.
Wraps the grounded FusionPlasmaKernel.
"""

from typing import List, Dict, Any, Optional
from backend.experiments.templates.base import SimulationTemplate, TemplateCustomizationParams
from backend.experiments.models import ExperimentProtocol, ProtocolStep, ExperimentType, Variable
from backend.experiments.templates import register_template

@register_template
class SVELApexFusionTemplate(SimulationTemplate):
    """
    Template for Inertial Confinement Fusion (ICF) and Aneutronic p-B experiments.
    """
    
    def __init__(self):
        super().__init__(
            name="plasma_fusion_simulation",
            experiment_type=ExperimentType.SIMULATION,
            domain="physics",
            title="Aneutronic Fusion Plasma Falsification",
            description="Rigorous simulation of p-B / D-T plasma burn using the FusionPlasmaKernel.",
            suitable_for=["fusion", "plasma", "ignition", "neutronics", "icf"],
            requirements=["numpy", "scipy", "statsmodels"],
            complexity_score=0.9,
            rigor_score=0.95
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        text = str(hypothesis).lower()
        return any(kw in text for kw in self.suitable_for)

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"PLASMA FUSION FALSIFICATION :: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=self.experiment_type,
            domain=self.domain,
            description=self.description,
            variables=[
                Variable(name="laser_power_PW", unit="PW", value_range=(0.1, 100.0)),
                Variable(name="plasma_density", unit="cm-3", value_range=(1e18, 1e26))
            ],
            steps=[
                ProtocolStep(
                    name="kernel_initialization",
                    description="Initialize the FusionPlasmaKernel with grounded adversarial biases.",
                    code_template="from backend.experiments.templates.physics.fusion_plasma_kernel import FusionPlasmaKernel, FusionPlasmaKernelConfig\ncfg = FusionPlasmaKernelConfig(laser_power_PW={laser_power_PW})",
                    expected_output="Configured plasma kernel"
                ),
                ProtocolStep(
                    name="yield_mapping",
                    description="Perform Monte Carlo mapping of neutron/energy yield with grounded timing jitter.",
                    code_template="result = timing_yield_map(nominal_jitter_us=0.1, tolerance_us=0.5, power_PW={laser_power_PW})",
                    expected_output="Statistical yield map"
                )
            ]
        )
