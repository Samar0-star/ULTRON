# backend/core/schemas/verdict.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class RedTeamVerdict(BaseModel):
    approved: bool = Field(description="Whether hypothesis survives adversarial critique")
    flaws_detected: List[str] = Field(default_factory=list, description="List of methodological, logical, or empirical flaws")
    counter_evidence: List[str] = Field(default_factory=list, description="Citations or prior art conflicting with claim")
    suggested_modifications: List[str] = Field(default_factory=list, description="Actionable recommendations to harden hypothesis")
    vulnerability_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Vulnerability rating (0=bulletproof, 1=fatally flawed)")

class ConsensusVerdictSchema(BaseModel):
    verdict: str = Field(description="Consensus decision: CONFIRMED, REFUTED, INCONCLUSIVE, or PENDING_EVIDENCE")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Epistemic confidence 0.0-1.0")
    supporting_reasons: List[str] = Field(default_factory=list, description="Key consensus supporting factors")
    dissenting_opinions: List[str] = Field(default_factory=list, description="Minority or adversarial critiques")
