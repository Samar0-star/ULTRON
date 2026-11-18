# backend/core/schemas/agents.py
"""
Pydantic schemas for specialist agent structured LLM outputs.
Replaces brittle regex and delimiter splitting across reader, fact-checker,
summarizer, and analysis agents with type-safe structured data contracts.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

class FactCheckResult(BaseModel):
    """FactCheckerAgent structured claim verification."""
    verdict: Literal["verified", "unverified", "contradicted", "insufficient_evidence"] = Field(
        description="Truth-value status of the evaluated claim against empirical literature"
    )
    confidence: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description="Epistemic certainty (< 0.8 triggers conservative 'unverified' classification)"
    )
    supporting_sources: List[str] = Field(
        default_factory=list,
        description="Citations, DOIs, or arXiv IDs explicitly confirming the claim"
    )
    contradicting_sources: List[str] = Field(
        default_factory=list,
        description="Citations or literature records directly opposing the claim"
    )
    explanation: str = Field(description="Step-by-step fact-checking rationale")

class DocumentExtraction(BaseModel):
    """DocReaderAgent structured scientific paper ingestion."""
    title: str = Field(description="Exact publication title")
    authors: List[str] = Field(default_factory=list, description="Author list")
    methodology: Optional[str] = Field(default=None, description="Core computational or experimental methodology")
    key_findings: List[str] = Field(
        default_factory=list,
        description="Direct empirical claims and discoveries reported in the paper"
    )
    statistical_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted metrics: effect sizes, confidence intervals, p-values, sample sizes"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Author-acknowledged bounds, confounders, or assumptions"
    )

class MLCodeResult(BaseModel):
    """MLModelBuilderAgent code synthesis contract."""
    code: str = Field(description="Executable Python code block")
    architecture_description: str = Field(description="Overview of model architecture and hyperparameter choices")
    expected_output_format: str = Field(
        default="stdout",
        description="Format of model evaluation metrics emitted by the script"
    )

class SummaryResult(BaseModel):
    """SummarizerAgent concise extraction contract."""
    summary: str = Field(description="Synthesized summary preserving core quantitative claims")
    key_points: List[str] = Field(default_factory=list, description="Bulleted takeaway insights")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence in summary completeness")

class AnalysisOutput(BaseModel):
    """DataAnalyzerAgent structured dataset interpretation."""
    interpretation: str = Field(description="Scientific interpretation of computed metrics")
    statistical_findings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of verified numerical patterns, effect sizes, and p-values"
    )
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Certainty score of interpretation")
