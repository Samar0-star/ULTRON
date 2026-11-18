# backend/core/schemas/hypothesis.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Prediction(BaseModel):
    variable: str = Field(description="Observable variable name")
    direction: str = Field(description="Expected relationship or trend: positive, negative, threshold, nonlinear")
    expected_magnitude: Optional[str] = Field(default=None, description="Quantified effect size or range")
    falsification_condition: str = Field(description="Exact observational or experimental condition that invalidates this prediction")

class ScientificHypothesisSchema(BaseModel):
    statement: str = Field(description="Falsifiable scientific claim in simple, unambiguous language")
    domain: str = Field(description="Scientific discipline or domain")
    key_variables: Dict[str, str] = Field(description="Mapping of physical/empirical variables to operational definitions")
    functional_form: str = Field(description="Mathematical or formal relationship expression, e.g. Y = a * X^b")
    falsification_experiment: str = Field(description="Specific empirical experiment protocol designed to disprove the hypothesis")
    predictions: List[Prediction] = Field(min_length=1, description="Deductive predictions under experimental conditions")
    prior_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Initial epistemic prior confidence")
