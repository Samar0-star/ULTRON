"""
SVEL Experiment Models
========================
Data models for experiment protocols, steps, and validation.
Ported and enhanced from SVEL.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid
import time
import random


class ExperimentType(Enum):
    """Types of experiments supported."""
    DATA_ANALYSIS = "data_analysis"
    SIMULATION = "simulation"
    COMPUTATIONAL = "computational"
    STATISTICAL = "statistical"
    MACHINE_LEARNING = "machine_learning"
    LITERATURE_SYNTHESIS = "literature_synthesis"
    META_ANALYSIS = "meta_analysis"
    HYPOTHESIS_TESTING = "hypothesis_testing"


@dataclass
class Variable:
    """Experiment variable definition."""
    name: str
    value: Any = None
    type: str = "str"  # string, integer, float, list, dict
    description: str = ""
    unit: Optional[str] = None
    value_range: Optional[Any] = None
    is_required: bool = True
    validation_regex: Optional[str] = None


@dataclass
class TemplateCustomizationParams:
    """Parameters for customizing a template."""
    hypothesis: Any  # Hypothesis object
    hypothesis_id: str = ""
    custom_variables: Dict[str, Any] = field(default_factory=dict)
    data_paths: Dict[str, str] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StatisticalTestSpec:
    """Specification for a statistical test."""
    test_type: str  # t_test, anova, spearman, fisher_exact, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    null_hypothesis: str = ""
    alternative_hypothesis: str = ""


@dataclass
class ValidationCheck:
    """Validation check for experiment quality."""
    check_type: str  # data_quality, sample_size, statistical_significance
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    severity: str = "error"  # error, warning, info


@dataclass
class ResourceRequirements:
    """Computational resource requirements."""
    estimated_runtime_seconds: int = 60
    memory_mb: int = 512
    memory_gb: Optional[float] = None  # Alias for high-memory tasks
    cpu_cores: int = 1
    requires_gpu: bool = False
    gpu_required: bool = False  # Alias for requires_gpu
    gpu_memory_mb: int = 0
    disk_space_mb: int = 100
    disk_space_gb: Optional[float] = None # Support GB

    def __post_init__(self):
        # Sync memory
        if self.memory_gb is not None:
            self.memory_mb = int(self.memory_gb * 1024)
        
        # Sync GPU requirement
        if self.gpu_required and not self.requires_gpu:
            self.requires_gpu = True
        if self.requires_gpu and not self.gpu_required:
            self.gpu_required = True
            
        # Sync disk space
        if self.disk_space_gb is not None:
            self.disk_space_mb = int(self.disk_space_gb * 1024)


@dataclass
class ProtocolStep:
    """Single step in an experiment protocol."""
    id: str = field(default_factory=lambda: f"step_{int(time.time())}_{random.randint(1000, 9999)}")
    name: str = ""
    description: str = ""
    code_template: str = ""
    expected_output: str = ""
    tools: List[str] = field(default_factory=list)
    validation: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "code_template": self.code_template,
            "expected_output": self.expected_output,
            "tools": self.tools,
            "validation": self.validation,
            "dependencies": self.dependencies,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count
        }

@dataclass
class ControlGroup:
    """Explicitly defined control group for active baseline comparison."""
    name: str
    description: str
    variables: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    sample_size: Optional[int] = None


@dataclass
class PowerAnalysisSpec:
    """Specification for ensuring statistical power before execution."""
    target_power: float = 0.80
    alpha: float = 0.05
    expected_effect_size: float = 0.5
    required_sample_size: Optional[int] = None
    rationale: str = ""


@dataclass
class ExperimentProtocol:
    """
    Complete experiment protocol — The Scientific Architecture.
    Enhanced with Kosmos-style structural discovery rigor.
    """
    title: str
    hypothesis_id: str
    experiment_type: ExperimentType
    domain: str
    description: str
    steps: List[ProtocolStep]
    variables: List[Variable] = field(default_factory=list)
    statistical_tests: List[StatisticalTestSpec] = field(default_factory=list)
    validation_checks: List[ValidationCheck] = field(default_factory=list)
    resource_requirements: Optional[ResourceRequirements] = None
    
    # Structural Rigor (Kosmos-Tier)
    control_groups: List[ControlGroup] = field(default_factory=list)
    power_analysis: Optional[PowerAnalysisSpec] = None
    random_seed: int = 42
    objective: str = ""
    
    expected_duration_hours: float = 1.0
    reproducibility_notes: List[str] = field(default_factory=list)
    
    # Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "2.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "hypothesis_id": self.hypothesis_id,
            "experiment_type": self.experiment_type.value if hasattr(self.experiment_type, "value") else str(self.experiment_type),
            "domain": self.domain,
            "description": self.description,
            "objective": self.objective,
            "steps": [s.to_dict() for s in self.steps],
            "variables": [{"name": v.name, "value": v.value} for v in self.variables],
            "control_groups": [vars(cg) for cg in self.control_groups],
            "power_analysis": vars(self.power_analysis) if self.power_analysis else None,
            "random_seed": self.random_seed,
            "expected_duration_hours": self.expected_duration_hours,
            "created_at": self.created_at.isoformat()
        }
    
    def get_code(self) -> str:
        """Get complete executable code from all steps."""
        return "\n\n".join([
            f"# === Step: {step.name} ===\n{step.code_template}"
            for step in self.steps
        ])


@dataclass
class ExperimentResult:
    """Result from executing an experiment protocol."""
    protocol_id: str
    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    validation_passed: bool = True
    statistical_results: Dict[str, Any] = field(default_factory=dict)
    
    # Evidence for hypothesis
    supports_hypothesis: Optional[bool] = None
    confidence_delta: float = 0.0
    evidence_summary: str = ""

