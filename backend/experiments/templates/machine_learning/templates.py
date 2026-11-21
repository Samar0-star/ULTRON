"""
SVEL-APEX MACHINE LEARNING TEMPLATE v1.0
==========================================
High-fidelity validation template for ML research.
"""

from typing import List, Dict, Any, Optional
from backend.experiments.templates.base import MLTemplate, TemplateCustomizationParams
from backend.experiments.templates import register_template
from backend.experiments.models import ExperimentProtocol, ProtocolStep, ExperimentType, Variable

@register_template
class SVELApexMLTemplate(MLTemplate):
    """
    Template for rigorous ML model verification and architecture audits.
    """
    
    def __init__(self):
        super().__init__(
            name="ml_architecture_audit",
            experiment_type=ExperimentType.MACHINE_LEARNING,
            domain="machine_learning",
            title="ML Architecture Audit",
            description="Autonomous ML falsification engine. Audits data leakage and adversarial robustness.",
            suitable_for=["transformer", "neural", "training", "leakage", "inference"],
            requirements=["torch", "scikit-learn", "transformers"],
            complexity_score=0.85,
            rigor_score=0.9
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        text = str(hypothesis).lower()
        return any(kw in text for kw in self.suitable_for)

    def generate_protocol(self, params: TemplateCustomizationParams) -> ExperimentProtocol:
        return ExperimentProtocol(
            title=f"ML AUDIT :: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=self.experiment_type,
            domain=self.domain,
            description=self.description,
            variables=[
                Variable(name="model_name", unit="str", value_range=(0, 0)),
                Variable(name="batch_size", unit="int", value_range=(1, 512))
            ],
            steps=[
                ProtocolStep(
                    name="data_leakage_check",
                    description="Perform rigorous audit for train/test contamination.",
                    code_template="""
import numpy as np
import pandas as pd

def audit_leakage(train_data_path, test_data_path):
    try:
        # Grounded Execution: Actually load the data
        train_df = pd.read_csv(train_data_path)
        test_df = pd.read_csv(test_data_path)
        
        # Calculate overlap hash
        train_hashes = set(train_df.apply(lambda row: hash(tuple(row)), axis=1))
        test_hashes = set(test_df.apply(lambda row: hash(tuple(row)), axis=1))
        
        overlap = train_hashes.intersection(test_hashes)
        leakage_rate = len(overlap) / len(test_hashes) if len(test_hashes) > 0 else 0
        
        return {"leakage_rate": leakage_rate, "overlap_count": len(overlap), "status": "FAIL" if leakage_rate > 0.01 else "PASS"}
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}

# Example invocation (Agent will provide paths)
# result = audit_leakage('data/train.csv', 'data/test.csv')
""",
                    expected_output="Leakage report"
                )
            ]
        )
