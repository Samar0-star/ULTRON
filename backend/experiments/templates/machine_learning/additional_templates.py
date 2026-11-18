"""
Empirical ML verification templates.
===================================
Replaces heuristic shortcuts with genuine statistical validation.
"""
from typing import Any, Dict, List, Optional
from backend.experiments.templates.base import MLTemplate
from backend.experiments.templates import register_template
from backend.experiments.models import ExperimentProtocol, ProtocolStep, Variable, ExperimentType, TemplateCustomizationParams

@register_template
class EmpiricalMLValidatorTemplate(MLTemplate):
    """
    Mandatory empirical ML validation
    Enforces:
    - Real CSV data loading (pd.read_csv)
    - Formal statistical significance (p-values)
    - No fabricated data manifold construction
    """

    def __init__(self):
        super().__init__(
            name="ml_empirical_validator",
            domain="machine_learning",
            title="ML Empirical Validation",
            description=(
                "Genuine statistical validation for ML models. Requires real data "
                "grounding and rigorous p-value testing."
            ),
            suitable_for=[
                "Model performance verification",
                "Binding affinity prediction",
                "Empirical data analysis"
            ],
            requirements=[
                "Pandas / Scipy backend",
                "Real CSV data file",
                "Welch's T-Test / Bootstrap analysis"
            ],
            complexity_score=0.8, 
            rigor_score=1.0
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        return True

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"EMPIRICAL VALIDATION :: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=ExperimentType.MACHINE_LEARNING,
            domain="machine_learning",
            description=(
                "Strict empirical gauntlet: Data Loading  Statistical Testing  "
                "Real-World Confidence Scoring."
            ),
            variables=[
                Variable(name="alpha_threshold", unit="raw", value="0.05"),
                Variable(name="bootstrap_samples", unit="N", value="1000")
            ],
            steps=[
                ProtocolStep(
                    name="real_data_ingestion",
                    description="Physically load resolved data using the pre-injected DATA_PRIMARY path and DF_PRIMARY DataFrame variable. Do NOT use pickle or hallucinate filenames.",
                    code_template="", # [TITAN FIX] Physically abolished hardcoding. Implementer must generate.
                    expected_output="Row count and Schema verification"
                ),
                ProtocolStep(
                    name="pytorch_neural_optimization",
                    description="Execute the deep learning hypothesis. Build a PyTorch neural network architecture (e.g. torch.nn.Linear, ViT, or ResNet) and train it using an Optimizer (SGD/Adam) with requires_grad=True to prove the hypothesis. Do NOT use scipy, statsmodels, or sklearn for this step.",
                    code_template="", # [TITAN FIX] Physically abolished hardcoding. Implementer must generate.
                    expected_output="Trained PyTorch model with updated weights (grad norm >= 1e-5)"
                ),
                ProtocolStep(
                    name="rigorous_evaluation",
                    description="Evaluate the trained PyTorch model against the baseline. Report the final performance metrics (e.g. loss, accuracy) derived directly from the neural network's predictions.",
                    code_template="", # [TITAN FIX] Physically abolished hardcoding. Implementer must generate.
                    expected_output="Evaluation metrics"
                )
            ]
        )

# Register the empirical template
class AdditionalTemplates:
    @staticmethod
    def get_templates():
        return [EmpiricalMLValidatorTemplate()]
