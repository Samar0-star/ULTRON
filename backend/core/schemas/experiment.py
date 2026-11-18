# backend/core/schemas/experiment.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ExperimentProtocolStep(BaseModel):
    step_number: int = Field(description="Step sequence index")
    action: str = Field(description="Action description: load_data, preprocess, statistical_test, simulate, plot")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Numerical parameters or configurations")

class ExperimentProtocolSchema(BaseModel):
    title: str = Field(description="Descriptive title of experiment")
    methodology: str = Field(description="Scientific methodology: parametric, non-parametric, simulation, GNN inference")
    statistical_tests: List[str] = Field(description="Specific statistical tests to compute, e.g. mann_whitney, bootstrap, fdr")
    sample_size: int = Field(default=100, description="Target sample size determined by power analysis")
    significance_level: float = Field(default=0.05, description="Alpha cutoff")
    steps: List[ExperimentProtocolStep] = Field(min_length=1, description="Sequential protocol steps")

class ExperimentMetrics(BaseModel):
    p_value: Optional[float] = Field(default=None, description="Computed p-value")
    effect_size: Optional[float] = Field(default=None, description="Computed effect size (Cohen's d or similar)")
    confidence_interval: Optional[List[float]] = Field(default=None, description="[lower, upper] bounds")
    statistical_power: Optional[float] = Field(default=None, description="Achieved statistical power")
    sample_count: Optional[int] = Field(default=None, description="Actual observations analyzed")

class ExperimentResultSchema(BaseModel):
    success: bool = Field(description="Whether the experiment script executed without runtime error")
    hypothesis_supported: bool = Field(description="Whether empirical metrics satisfy falsification criteria")
    metrics: ExperimentMetrics = Field(default_factory=ExperimentMetrics, description="Extracted statistical metrics")
    findings: List[str] = Field(default_factory=list, description="Concrete factual findings derived from results")
    artifacts: List[str] = Field(default_factory=list, description="File paths to generated figures, tables, or models")
    critique: Optional[str] = Field(default=None, description="Methodological limitations or caveats")
