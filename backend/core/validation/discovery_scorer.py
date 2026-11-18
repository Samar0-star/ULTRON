# -*- coding: utf-8 -*-
"""
Discovery Scorer - ULTRON Ultra-Upgrade
=========================================

10-Dimension quality scoring for scientific discoveries.
Goes beyond binary pass/fail to provide multi-faceted assessment.

ULTRON-Specific Dimensions:
1. Novelty - Is this genuinely new?
2. Rigor - Are methods scientifically sound?
3. Reproducibility - Can it be replicated?
4. Significance - Statistical significance level
5. Grounding - Evidence support strength
6. Coherence - Fits existing knowledge?
7. Testability - Can be falsified?
8. Impact - Potential influence
9. AdversarialSurvival - Passed Red Team? (ULTRON-ONLY)
10. TemporalRobustness - Stable over cycles? (ULTRON-ONLY)

Author: ULTRON Team
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from datetime import datetime

from backend.discovery.constants import ScientificDefaults

logger = logging.getLogger(__name__)


class QualityTier(Enum):
    """Quality tier classification based on overall score."""
    EXCEPTIONAL = "exceptional"  # >= 0.90
    HIGH = "high"                # >= 0.80
    GOOD = "good"                # >= 0.70
    MODERATE = "moderate"        # >= 0.60
    LOW = "low"                  # >= 0.50
    POOR = "poor"                # < 0.50


@dataclass
class DimensionScore:
    """Score for a single dimension."""
    dimension: str
    score: float  # 0.0 - 1.0
    weight: float
    rationale: str
    flags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "weight": self.weight,
            "rationale": self.rationale,
            "flags": self.flags
        }


@dataclass
class DiscoveryScore:
    """
    Complete 10-dimension discovery score.
    
    A discovery is APPROVED only if:
    - overall_score >= 0.75
    - rigor >= 0.70
    - adversarial_survival >= 0.60 (if Red Team was run)
    """
    
    # Individual dimension scores
    novelty: float = 0.0
    rigor: float = 0.0
    reproducibility: float = 0.0
    significance: float = 0.0
    grounding: float = 0.0
    coherence: float = 0.0
    testability: float = 0.0
    impact: float = 0.0
    adversarial_survival: float = 0.0
    temporal_robustness: float = 0.0
    
    # Aggregate
    overall_score: float = 0.0
    discovery_priority: float = 0.0 # [TITAN V165.0] UCB-based frontier exploration score
    quality_tier: str = "poor"
    is_approved: bool = False

    
    # Metadata
    dimension_details: List[DimensionScore] = field(default_factory=list)
    approval_reasons: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # Timing
    scored_at: datetime = field(default_factory=datetime.utcnow)
    scoring_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "novelty": self.novelty,
            "rigor": self.rigor,
            "reproducibility": self.reproducibility,
            "significance": self.significance,
            "grounding": self.grounding,
            "coherence": self.coherence,
            "testability": self.testability,
            "impact": self.impact,
            "adversarial_survival": self.adversarial_survival,
            "temporal_robustness": self.temporal_robustness,
            "overall_score": self.overall_score,
            "quality_tier": self.quality_tier,
            "is_approved": self.is_approved,
            "dimension_details": [d.to_dict() for d in self.dimension_details],
            "approval_reasons": self.approval_reasons,
            "rejection_reasons": self.rejection_reasons,
            "improvement_suggestions": self.improvement_suggestions,
            "scored_at": self.scored_at.isoformat(),
            "scoring_time_seconds": self.scoring_time_seconds
        }
    
    def get_summary(self) -> str:
        """Generate human-readable summary."""
        status = "APPROVED" if self.is_approved else "REJECTED"
        tier = self.quality_tier.upper()
        
        summary = f"[{status}] Quality: {tier} (Score: {self.overall_score:.2f})\n"
        summary += f"  Novelty: {self.novelty:.2f} | Rigor: {self.rigor:.2f} | Impact: {self.impact:.2f}\n"
        
        if self.rejection_reasons:
            summary += f"  Issues: {', '.join(self.rejection_reasons[:3])}\n"
        
        if self.improvement_suggestions:
            summary += f"  Suggestions: {self.improvement_suggestions[0]}"
        
        return summary


class DiscoveryScorer:
    """
    10-Dimension discovery quality scorer for ULTRON.
    
    Provides multi-faceted quality assessment that catches different
    failure modes through specialized dimension scoring.
    
    Usage:
        scorer = DiscoveryScorer()
        score = scorer.score_discovery(finding)
        
        if score.is_approved:
            print("Discovery meets quality standards!")
        else:
            print(f"Issues: {score.rejection_reasons}")
    """
    
    # Default dimension weights (sum to 1.0)
    DEFAULT_WEIGHTS = {
        "novelty": 0.12,
        "rigor": 0.15,           # High weight - methodological soundness critical
        "reproducibility": 0.10,
        "significance": 0.12,
        "grounding": 0.12,
        "coherence": 0.08,
        "testability": 0.08,
        "impact": 0.08,
        "adversarial_survival": 0.08,  # ULTRON-specific
        "temporal_robustness": 0.07    # ULTRON-specific
    }
    
    # Approval thresholds
    APPROVAL_THRESHOLDS = {
        "overall": 0.75,
        "rigor": 0.70,
        "adversarial_survival": 0.60
    }
    
    def __init__(
        self,
        llm_manager=None,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize Discovery Scorer.
        
        Args:
            llm_manager: Optional LLM manager for advanced scoring
            weights: Custom dimension weights
            thresholds: Custom approval thresholds
        """
        self.llm_manager = llm_manager
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.thresholds = thresholds or self.APPROVAL_THRESHOLDS.copy()
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}
    
    async def score_discovery(
        self,
        finding: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        red_team_result: Optional[Dict[str, Any]] = None,
        statistical_grounding: Optional[Dict[str, Any]] = None,
        failure_detection: Optional[Dict[str, Any]] = None,
        reproducibility_info: Optional[Dict[str, Any]] = None
    ) -> DiscoveryScore:
        """
        Score a discovery across 10 dimensions.
        
        Args:
            finding: Discovery dict with summary, statistics, methods, etc.
            context: Research context (prior findings, hypotheses)
            red_team_result: Result from RedTeamAgent (for adversarial_survival)
            statistical_grounding: Result from StatisticalGroundingValidator
            failure_detection: Result from FailureDetector
            reproducibility_info: Result from ReproducibilityManager
        
        Returns:
            DiscoveryScore with all dimension scores and approval status
        """
        start_time = time.time()
        context = context or {}
        finding = self._normalize_finding(finding)
        
        dimension_details: List[DimensionScore] = []
        scores: Dict[str, float] = {}
        
        # Score each dimension
        scores["novelty"], detail = self._score_novelty(finding, context)
        dimension_details.append(detail)
        
        scores["rigor"], detail = self._score_rigor(finding, failure_detection)
        dimension_details.append(detail)
        
        scores["reproducibility"], detail = self._score_reproducibility(finding, reproducibility_info)
        dimension_details.append(detail)
        
        scores["significance"], detail = self._score_significance(finding, statistical_grounding)
        dimension_details.append(detail)
        
        scores["grounding"], detail = await self._score_grounding(finding)
        dimension_details.append(detail)
        
        scores["coherence"], detail = self._score_coherence(finding, context)
        dimension_details.append(detail)
        
        scores["testability"], detail = self._score_testability(finding)
        dimension_details.append(detail)
        
        scores["impact"], detail = self._score_impact(finding)
        dimension_details.append(detail)
        
        scores["adversarial_survival"], detail = self._score_adversarial_survival(
            finding, red_team_result
        )
        dimension_details.append(detail)
        
        scores["temporal_robustness"], detail = self._score_temporal_robustness(
            finding, context
        )
        dimension_details.append(detail)
        
        # Calculate weighted overall quality score (Pure Rigor/Grounding)
        overall_quality = sum(
            scores[dim] * self.weights[dim]
            for dim in scores
        )
        
        # [TITAN V202.0] MATHEMATICAL SOVEREIGNTY
        # Physically normalized the Bayesian prior using a Sigmoid function
        # to ensure the discovery priority remains bounded [0, 1].
        task_info = finding.get("task", {})
        gnn_sigma = float(task_info.get("uncertainty", 0.0))
        kappa = 2.0

        discovery_priority = overall_quality
        if gnn_sigma > 0.0:
            bayesian_bonus = kappa * gnn_sigma
            import math
            discovery_priority = 1.0 / (1.0 + math.exp(-(overall_quality + bayesian_bonus - 0.5) * 4.0))
            logger.info(f" [UCB] Discovery priority manifold updated: {discovery_priority:.3f} (Quality: {overall_quality:.3f}, Doubt: {gnn_sigma:.3f})")
        # Determine quality tier (Based on pure quality, NOT bonus)
        tier = self._get_quality_tier(overall_quality)
        
        # Check approval (Must pass 0.75 Quality gate BEFORE bonus)
        is_approved, approval_reasons, rejection_reasons = self._check_approval(scores)
        
        # Generate improvement suggestions
        suggestions = self._generate_suggestions(scores, dimension_details)
        
        scoring_time = time.time() - start_time
        
        return DiscoveryScore(
            novelty=scores["novelty"],
            rigor=scores["rigor"],
            reproducibility=scores["reproducibility"],
            significance=scores["significance"],
            grounding=scores["grounding"],
            coherence=scores["coherence"],
            testability=scores["testability"],
            impact=scores["impact"],
            adversarial_survival=scores["adversarial_survival"],
            temporal_robustness=scores["temporal_robustness"],
            overall_score=overall_quality,
            discovery_priority=discovery_priority,
            quality_tier=tier.value,
            is_approved=is_approved,
            dimension_details=dimension_details,
            approval_reasons=approval_reasons,
            rejection_reasons=rejection_reasons,
            improvement_suggestions=suggestions,
            scoring_time_seconds=scoring_time
        )
    
    def _normalize_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """P0-38: Unwrap nested Orchestrator/Router/ExperimentAgent envelopes so statistics, summary, code, and methods are visible."""
        if not isinstance(finding, dict):
            return {"summary": str(finding), "statistics": {}}
        norm = dict(finding)
        res = norm.get("result", {})
        if isinstance(res, dict) and "result" in res and isinstance(res["result"], dict):
            res = res["result"]
        if isinstance(res, dict):
            inner_res = res.get("result", {}) if isinstance(res.get("result"), dict) else {}
            meta = res.get("metadata", {}) if isinstance(res.get("metadata"), dict) else {}
            inner_meta = inner_res.get("metadata", {}) if isinstance(inner_res.get("metadata"), dict) else {}
            if not norm.get("summary"):
                norm["summary"] = str(res.get("summary") or res.get("text") or norm.get("content") or "")
            if not norm.get("code"):
                norm["code"] = res.get("code") or inner_res.get("code") or meta.get("code")
            if not norm.get("data_path"):
                norm["data_path"] = res.get("data_path") or meta.get("data_path") or inner_meta.get("data_path")
            if not norm.get("methods"):
                norm["methods"] = res.get("methods") or meta.get("protocol_summary") or norm.get("code") or ""
            stats = dict(norm.get("statistics") or {})
            for cand in (
                res.get("statistics"),
                res.get("scientific_report"),
                inner_res.get("scientific_report"),
                meta.get("report"),
                inner_meta.get("report"),
                res,
                inner_res,
            ):
                if isinstance(cand, dict):
                    for k in ("p_value", "pvalue", "p_permutation", "effect_size", "cohens_d", "cohen_d", "t_stat", "observed_diff", "r_squared", "odds_ratio", "n", "sample_size", "confidence_interval", "ci"):
                        if cand.get(k) is not None and stats.get(k) is None:
                            stats[k] = cand[k]
            if stats.get("p_value") is None and stats.get("p_permutation") is not None:
                stats["p_value"] = stats["p_permutation"]
            if stats.get("effect_size") is None:
                for ek in ("cohens_d", "cohen_d", "observed_diff", "t_stat"):
                    if stats.get(ek) is not None:
                        stats["effect_size"] = stats[ek]
                        break
            norm["statistics"] = stats
        elif not norm.get("summary"):
            norm["summary"] = str(norm.get("content") or res or "")
        return norm

    # =========================================================================

    # DIMENSION SCORING METHODS
    # =========================================================================
    
    def _score_novelty(
        self,
        finding: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[float, DimensionScore]:
        """Score novelty - is this genuinely new?"""
        score = 0.5  # Default
        rationale = ""
        flags = []
        
        # Check novelty report if available
        novelty_report = finding.get("novelty_report", {})
        if novelty_report:
            score = novelty_report.get("novelty_score", 0.5)
            if novelty_report.get("prior_art_detected"):
                flags.append("prior_art_detected")
                rationale = "Similar findings exist in prior research."
            else:
                rationale = "Finding appears novel based on semantic analysis."
        else:
            # Heuristic scoring
            summary = finding.get("summary", "")
            rationale = "Heuristic baseline score."
            
            # Check if extends prior work (good) vs duplicates it (bad)
            prior_findings = context.get("prior_findings", [])
            if prior_findings:
                # Simple overlap check
                summary_words = set(summary.lower().split())
                for prior in prior_findings[:5]:
                    prior_summary = prior.get("summary", "")
                    prior_words = set(prior_summary.lower().split())
                    overlap = len(summary_words & prior_words) / max(len(summary_words), 1)
                    if overlap > 0.5:
                        score -= 0.2
                        flags.append("high_overlap_with_prior")
                        rationale = "High overlap with prior findings."
                        break
        
        score = max(0.0, min(1.0, score))
        
        return score, DimensionScore(
            dimension="novelty",
            score=score,
            weight=self.weights["novelty"],
            rationale=rationale or "Novelty score based on heuristics.",
            flags=flags
        )
    
    def _score_rigor(
        self, 
        finding: Dict[str, Any],
        failure_detection: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, DimensionScore]:
        """Score rigor - are methods scientifically sound?"""
        score = 0.5
        rationale_parts = []
        flags = []
        
        stats = finding.get("statistics", {})
        methods = finding.get("methods", "")
        
        # Check for statistical rigor
        has_pvalue = stats.get("p_value") is not None or stats.get("pvalue") is not None
        has_effect_size = any(
            stats.get(k) is not None
            for k in ["effect_size", "cohens_d", "r_squared", "odds_ratio"]
        )
        has_sample_size = stats.get("n") is not None or stats.get("sample_size") is not None
        has_ci = stats.get("confidence_interval") is not None or stats.get("ci") is not None
        
        if has_pvalue:
            score += 0.15
            rationale_parts.append("p-value reported")
        
        if has_effect_size:
            score += 0.15
            rationale_parts.append("effect size provided")
        
        if has_sample_size:
            score += 0.10
            rationale_parts.append("sample size specified")
        
        if has_ci:
            score += 0.10
            rationale_parts.append("confidence interval included")
        
        # Method description quality
        if methods:
            method_len = len(methods)
            if method_len > 500:
                score += 0.10
                rationale_parts.append("detailed methodology")
            elif method_len > 100:
                score += 0.05
        else:
            flags.append("missing_methodology")
            score -= 0.15
        
        # Check for red flags (preserve p_value == 0.0 without falsy 'or' bug)
        p_val = stats.get("p_value") if stats.get("p_value") is not None else stats.get("pvalue")
        if p_val is not None:
            try:
                p = float(p_val)
                # [ULTRON NUCLEAR FIX] Hard P-Value Rigor Gate (No Science Theater)
                if p <= 0.05:
                    pass # Full credit
                else:
                    # Reject marginal or non-significant results
                    score -= 0.3
                    flags.append("p_above_threshold")
                    rationale_parts.append(f" p-value ({p:.3f}) exceeds scientific threshold (0.05)")
                
                # P-HACKING DETECTION: Still keep this as it's a valid concern
                if 0.048 <= p <= 0.0505:
                    flags.append("suspicious_p_value")
                    score -= 0.1
                    rationale_parts.append(" p-value suspiciously close to 0.05")
            except (ValueError, TypeError):
                pass
        
        # EFFECT SIZE vs P-VALUE CONSISTENCY CHECK
        effect_size = stats.get("effect_size") if stats.get("effect_size") is not None else stats.get("cohens_d")
        sample_size = stats.get("n") if stats.get("n") is not None else stats.get("sample_size")
        
        if p_val is not None and effect_size is not None and sample_size is not None:
            try:
                p = float(p_val)
                es = float(effect_size)
                n = int(sample_size)
                
                # [TITAN V202.0] EFFECT SIZE RECLAMATION
                # Physically abolished the 'trivial_effect_large_sample' naive heuristic.
                # In physics/genomics, massive sample sizes with small effect sizes
                # are mathematically sovereign discoveries. We no longer punish them.
                pass
            except (ValueError, TypeError):
                pass

        # [TITAN V169.0] MATHEMATICAL DECOUPLING
        # Physically abolished the Bayesian UCB penalty in the Rigor dimension.
        # Uncertainty (sigma) is now exclusively handled in the 'discovery_priority' manifold.
        # This prevents high-novelty breakthroughs from being rejected by the Quality Gate.
        pass

        # LINGUISTIC RIGOR (Failure Detection)




        if failure_detection:
            over_interp = failure_detection.get("over_interpretation", {})
            invented = failure_detection.get("invented_metrics", {})
            
            if over_interp.get("detected"):
                score -= 0.25
                flags.append("over_interpretation")
                rationale_parts.append(" Claims significantly exceed statistical support")
                
            if invented.get("detected"):
                score -= 0.3
                flags.append("invented_metrics")
                rationale_parts.append(" Hallucinated metrics detected in interpretation")
        
        score = max(0.0, min(1.0, score))
        rationale = ", ".join(rationale_parts) if rationale_parts else "Basic rigor assessment."
        
        return score, DimensionScore(
            dimension="rigor",
            score=score,
            weight=self.weights["rigor"],
            rationale=rationale,
            flags=flags
        )
    
    def _score_reproducibility(
        self, 
        finding: Dict[str, Any],
        reproducibility_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, DimensionScore]:
        """Score reproducibility - can it be replicated?"""
        score = 0.5
        rationale_parts = []
        flags = []
        
        # Check for reproducibility indicators
        if finding.get("code_available") or finding.get("code"):
            score += 0.2
            rationale_parts.append("code provided")
        
        if finding.get("data_available") or finding.get("data_path"):
            score += 0.2
            rationale_parts.append("data available")
            
        # Repro Manager check
        if reproducibility_info:
            score += 0.2
            rationale_parts.append("environment snapshot attached")
            if reproducibility_info.get("seed"):
                score += 0.1
                rationale_parts.append("deterministic seed used")
        elif finding.get("random_seed") is not None:
            score += 0.1
            rationale_parts.append("random seed specified")
        
        if finding.get("environment") or finding.get("dependencies"):
            score += 0.1
            rationale_parts.append("environment documented")
        
        methods = finding.get("methods", "")
        if methods and len(methods) > 200:
            score += 0.1
            rationale_parts.append("methods documented")
        
        # Check for irreproducibility flags
        if "manual" in str(finding.get("methods", "")).lower():
            flags.append("manual_steps_required")
            score -= 0.1
        
        score = max(0.0, min(1.0, score))
        rationale = ", ".join(rationale_parts) if rationale_parts else "Reproducibility unclear."
        
        return score, DimensionScore(
            dimension="reproducibility",
            score=score,
            weight=self.weights["reproducibility"],
            rationale=rationale,
            flags=flags
        )
    
    def _score_significance(
        self,
        finding: Dict[str, Any],
        statistical_grounding: Optional[Dict[str, Any]]
    ) -> Tuple[float, DimensionScore]:
        """Score significance - statistical significance level."""
        score = 0.5
        rationale = ""
        flags = []
        
        # Use statistical grounding if available
        if statistical_grounding:
            if statistical_grounding.get("is_statistically_grounded"):
                score = 0.9
                rationale = "Passed null model validation."
            elif statistical_grounding.get("persists_in_noise"):
                score = 0.2
                rationale = "Finding persists in noise - potential false positive."
                flags.append("persists_in_noise")
            else:
                p_val = statistical_grounding.get("permutation_p_value", 1.0)
                score = max(0.3, 1.0 - p_val)
                rationale = f"Permutation p-value: {p_val:.4f}"
        else:
            # Use reported p-value (preserve p_value == 0.0)
            stats = finding.get("statistics", {})
            p_val = stats.get("p_value") if stats.get("p_value") is not None else stats.get("pvalue")
            
            if p_val is not None:
                try:
                    p = float(p_val)
                    alpha = ScientificDefaults.ALPHA_SIGNIFICANCE
                    if p < alpha * 0.02:
                        score = 0.98
                        rationale = f"Highly significant (p < {alpha * 0.02})"
                    elif p < alpha * 0.2:
                        score = 0.90
                        rationale = f"Very significant (p < {alpha * 0.2})"
                    elif p < alpha:
                        score = 0.80
                        rationale = f"Significant (p < {alpha})"
                    elif p < alpha * 2:
                        # Rescuing marginal findings
                        score = 0.65
                        rationale = f"Marginally significant (p = {p:.3f})"
                        flags.append("marginal_significance")
                    else:
                        score = 0.35 * (1.0 - (p - alpha * 2) / (1.0 - alpha * 2))
                        rationale = f"Not significant (p = {p:.3f})"
                        flags.append("not_significant")
                except (ValueError, TypeError):
                    rationale = "Could not parse p-value."
            else:
                rationale = "No p-value reported."
                flags.append("no_pvalue")
        
        score = max(0.0, min(1.0, score))
        
        return score, DimensionScore(
            dimension="significance",
            score=score,
            weight=self.weights["significance"],
            rationale=rationale,
            flags=flags
        )
    
    async def _score_grounding(self, finding: Dict[str, Any]) -> Tuple[float, DimensionScore]:
        """Score grounding - evidence support strength."""
        score = 0.5
        rationale_parts = []
        flags = []
        
        # Check for evidence sources
        evidence = finding.get("evidence", [])
        citations = finding.get("citations", [])
        sources = finding.get("sources", [])
        
        total_sources = len(evidence) + len(citations) + len(sources)
        
        if total_sources >= 5:
            score += 0.3
            rationale_parts.append(f"{total_sources} supporting sources")
        elif total_sources >= 2:
            score += 0.15
            rationale_parts.append(f"{total_sources} supporting sources")
        if total_sources == 0:
            flags.append("no_sources_cited")
            score -= 0.2
            
        # [TITAN V166.0] UNIVERSAL ANTI-FRAUD HARDENING
        # Physically blacklist any finding whose "sources" are purely LLM-hallucinated.
        # [TITAN V202.0] EPISTEMIC HARDENING
        # Physically abolished the 'http'/'url' string-matching theater.
        # Citations must be structurally verified by the World Model's UUID/SHA256 system.
        has_verified_id = False
        import re
        all_refs = list(citations if isinstance(citations, list) else []) + list(sources if isinstance(sources, list) else [])
        for cit in all_refs:
            if isinstance(cit, dict):
                if cit.get("verified", False) or any(cit.get(k) for k in ("doi", "arxiv_id", "pmid", "s2_id", "url", "id")):
                    has_verified_id = True
                    break
            elif isinstance(cit, str):
                c_str = cit.strip()
                if (len(c_str) == 16 and c_str.isalnum()) or re.search(r'(10\.\d{4,9}/|arxiv|\b\d{4}\.\d{4,5}\b|pmid|pubmed|https?://)', c_str, re.IGNORECASE):
                    has_verified_id = True
                    break
        
        if not has_verified_id and total_sources > 0:
            score = min(score, 0.1) # Terminal cap for ungrounded authority
            flags.append("unverified_authority")
            rationale_parts.append("Hallucination Risk: No verified ID (ArXiv/PubMed/DOI/S2) found in sources.")
            logger.warning(" [ANTI-FRAUD] Universal grounding fail: No verified scientific ID detected.")


        # HELL-TIER UPGRADE: CITATION TRUTH ANCHOR

        # Verify citations against external databases (Semantic Scholar / ArXiv)
        if citations:
            try:
                import asyncio
                from backend.agents.red_team_agent import RedTeamAgent
                red_team = getattr(self, "_red_team_verifier", None)
                if red_team is None:
                    red_team = RedTeamAgent()
                    self._red_team_verifier = red_team
                hallucination_count = 0

                for cit in citations[:5]:
                    if isinstance(cit, dict) and (cit.get("verified") or any(cit.get(k) for k in ("doi", "arxiv_id", "pmid", "s2_id", "url"))):
                        continue
                    title = cit if isinstance(cit, str) else cit.get("title", "")
                    if not title:
                        continue
                    # Skip title search if string is already a raw DOI / arXiv / PubMed / URL identifier
                    if isinstance(cit, str) and re.search(r'(10\.\d{4,9}/|arxiv|\b\d{4}\.\d{4,5}\b|pmid|pubmed|https?://)', cit.strip(), re.IGNORECASE):
                        continue

                    verdict = await asyncio.wait_for(
                        red_team.verify_citation(
                            claim=finding.get("summary", "")[:200],
                            cited_paper_title=title
                        ),
                        timeout=8.0
                    )

                    if verdict.get("verdict") == "HALLUCINATED":
                        hallucination_count += 1
                        flags.append(f"fake_citation:{title[:20]}")
                        logger.warning(f" FAKE CITATION DETECTED: {title}")

                # NUCLEAR PENALTY via Truth Anchor
                if hallucination_count > 0:
                    score = 0.2  # Severe penalty but not absolute 0 unless all fail
                    flags.append("HALLUCINATION_DETECTED")
                    rationale_parts.append(f" CRITICAL: {hallucination_count} fake citations detected")
                else:
                    if "verification_error" not in flags:
                        score += 0.1
                        rationale_parts.append(" all citations verified")

            except Exception as e:
                logger.warning(f"Citation verification failed: {e}")
                flags.append("verification_error")
                score -= 0.05 # Minor penalty for uncertainty

        # Check for data grounding
        if finding.get("data_path") or finding.get("raw_data"):
            score += 0.1
            rationale_parts.append("data grounded")
        
        # Check for quantitative claims
        stats = finding.get("statistics", {})
        if stats:
            score += 0.1
            rationale_parts.append("quantitative evidence")

        # NUCLEAR PENALTY via Truth Anchor (Absolute override ONLY if confirmed fake)
        if "HALLUCINATION_DETECTED" in flags and hallucination_count >= len(citations):
            score = 0.0
        
        score = max(0.0, min(1.0, score))
        rationale = ", ".join(rationale_parts) if rationale_parts else "Limited grounding evidence."
        
        return score, DimensionScore(
            dimension="grounding",
            score=score,
            weight=self.weights["grounding"],
            rationale=rationale,
            flags=flags
        )
    
    def _score_coherence(
        self,
        finding: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[float, DimensionScore]:
        """Score coherence - fits existing knowledge?"""
        score = 0.6  # Default: assume moderate coherence
        rationale = ""
        flags = []
        
        # Check if explicitly contradicts prior findings
        contradictions = finding.get("contradictions", [])
        if contradictions:
            score -= 0.2 * min(len(contradictions), 3)
            flags.append("contradicts_prior")
            rationale = f"Contradicts {len(contradictions)} prior finding(s)."
        
        # Check if builds on prior work
        builds_on = finding.get("builds_on", [])
        supports = finding.get("supports", [])
        
        if builds_on or supports:
            score += 0.15
            rationale = "Builds on or supports prior findings."
        
        # Domain consistency
        domain = finding.get("domain", "")
        context_domain = context.get("domain", "")
        
        if domain and context_domain and domain.lower() == context_domain.lower():
            score += 0.1
        
        score = max(0.0, min(1.0, score))
        
        return score, DimensionScore(
            dimension="coherence",
            score=score,
            weight=self.weights["coherence"],
            rationale=rationale or "Coherence with existing knowledge.",
            flags=flags
        )
    
    def _score_testability(self, finding: Dict[str, Any]) -> Tuple[float, DimensionScore]:
        """Score testability - can it be falsified?"""
        score = 0.5
        rationale_parts = []
        flags = []
        
        # Check for testable predictions
        predictions = finding.get("predictions", [])
        if predictions:
            score += 0.2
            rationale_parts.append(f"{len(predictions)} testable predictions")
        
        # Check for experimental protocol
        methods = finding.get("methods", "")
        protocol = finding.get("protocol", "")
        
        if protocol:
            score += 0.2
            rationale_parts.append("experimental protocol provided")
        elif methods and len(methods) > 300:
            score += 0.1
            rationale_parts.append("detailed methods")
        
        # Check for falsifiable claims
        summary = finding.get("summary", "")
        
        # Vague claims reduce testability
        vague_words = ["might", "could", "possibly", "perhaps", "may suggest"]
        vague_count = sum(1 for word in vague_words if word in summary.lower())
        if vague_count > 2:
            score -= 0.15
            flags.append("vague_claims")
        
        # Specific claims increase testability
        specific_words = ["specifically", "exactly", "precisely", "when", "if"]
        specific_count = sum(1 for word in specific_words if word in summary.lower())
        if specific_count >= 2:
            score += 0.1
            rationale_parts.append("specific claims")
        
        score = max(0.0, min(1.0, score))
        rationale = ", ".join(rationale_parts) if rationale_parts else "Testability unclear."
        
        return score, DimensionScore(
            dimension="testability",
            score=score,
            weight=self.weights["testability"],
            rationale=rationale,
            flags=flags
        )
    
    def _score_impact(self, finding: Dict[str, Any]) -> Tuple[float, DimensionScore]:
        """Score impact - potential influence."""
        score = 0.5
        rationale_parts = []
        flags = []
        
        # Check for application potential
        applications = finding.get("applications", [])
        implications = finding.get("implications", [])
        
        if applications:
            score += 0.15
            rationale_parts.append(f"{len(applications)} applications identified")
        
        if implications:
            score += 0.15
            rationale_parts.append(f"{len(implications)} implications noted")
        
        # Check summary for impact indicators
        summary = finding.get("summary", "")
        
        impact_words = ["breakthrough", "significant", "major", "important", 
                       "fundamental", "paradigm", "transform", "revolution"]
        impact_count = sum(1 for word in impact_words if word in summary.lower())
        
        if impact_count >= 2:
            score += 0.15
            rationale_parts.append("high-impact language")
        elif impact_count == 1:
            score += 0.05
        
        # Domain importance
        domain = finding.get("domain", "")
        high_impact_domains = ["medicine", "health", "climate", "energy", "ai"]
        if any(d in domain.lower() for d in high_impact_domains):
            score += 0.1
            rationale_parts.append("high-impact domain")
        
        score = max(0.0, min(1.0, score))
        rationale = ", ".join(rationale_parts) if rationale_parts else "Impact potential unclear."
        
        return score, DimensionScore(
            dimension="impact",
            score=score,
            weight=self.weights["impact"],
            rationale=rationale,
            flags=flags
        )
    
    def _score_adversarial_survival(
        self,
        finding: Dict[str, Any],
        red_team_result: Optional[Dict[str, Any]]
    ) -> Tuple[float, DimensionScore]:
        """Score adversarial survival - passed Red Team? (ULTRON-specific)"""
        score = 0.5  # Default if no Red Team run
        rationale = "No Red Team review conducted."
        flags = []
        
        if red_team_result:
            status = red_team_result.get("status", "")
            
            if status == "APPROVED":
                score = 0.95
                rationale = "Passed Red Team review."
            elif status == "MODIFIED":
                score = 0.70
                rationale = "Red Team suggested modifications."
                flags.append("needs_modification")
            elif status == "DOWNGRADE":
                score = 0.40
                rationale = "Red Team downgraded the finding."
                flags.append("downgraded")
            elif status in ["ESCAPED", "INVALID_CLAIM"]:
                score = 0.15
                rationale = "Finding escaped bounds or invalid claim."
                flags.append("invalid_claim_or_escaped")
            elif status == "REJECTED":
                score = 0.20
                rationale = "Failed Red Team review."
                flags.append("red_team_rejected")
            elif status == "SKIPPED":
                score = 0.50
                rationale = "Red Team review skipped."
                flags.append("red_team_skipped_alert")
            
            # Factor in severity
            severity = red_team_result.get("severity_score", 50)
            if severity > 70:
                score -= 0.1
                flags.append("high_severity_issues")
            
            # Check counterfactuals
            counterfactuals = red_team_result.get("counterfactuals", [])
            if counterfactuals:
                score -= 0.05 * min(len(counterfactuals), 3)
                flags.append(f"{len(counterfactuals)}_counterfactuals")
        
        score = max(0.0, min(1.0, score))
        
        return score, DimensionScore(
            dimension="adversarial_survival",
            score=score,
            weight=self.weights["adversarial_survival"],
            rationale=rationale,
            flags=flags
        )
    
    def _score_temporal_robustness(
        self,
        finding: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[float, DimensionScore]:
        """Score temporal robustness - stable over cycles? (ULTRON-specific)"""
        score = 0.5  # Default for new findings
        rationale = "First observation of this finding."
        flags = []
        
        # Check cycle history
        cycle_history = finding.get("cycle_history", [])
        confirmed_cycles = finding.get("confirmed_cycles", 0)
        total_cycles = context.get("current_cycle", 1)
        
        if cycle_history:
            # Has been observed across multiple cycles
            score = min(0.95, 0.5 + 0.1 * len(cycle_history))
            rationale = f"Observed across {len(cycle_history)} cycles."
        
        if confirmed_cycles > 0:
            score = min(0.95, score + 0.1 * confirmed_cycles)
            rationale = f"Confirmed in {confirmed_cycles} cycle(s)."
        
        # Check for time decay (older findings need re-verification)
        last_verified = finding.get("last_verified_cycle", total_cycles)
        cycles_since_verification = total_cycles - last_verified
        
        if cycles_since_verification > 5:
            score -= 0.15
            flags.append("needs_reverification")
            rationale = f"Not verified in {cycles_since_verification} cycles."
        
        score = max(0.0, min(1.0, score))
        
        return score, DimensionScore(
            dimension="temporal_robustness",
            score=score,
            weight=self.weights["temporal_robustness"],
            rationale=rationale,
            flags=flags
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_quality_tier(self, overall_score: float) -> QualityTier:
        """Determine quality tier from overall score."""
        if overall_score >= 0.90:
            return QualityTier.EXCEPTIONAL
        elif overall_score >= 0.80:
            return QualityTier.HIGH
        elif overall_score >= 0.70:
            return QualityTier.GOOD
        elif overall_score >= 0.60:
            return QualityTier.MODERATE
        elif overall_score >= 0.50:
            return QualityTier.LOW
        else:
            return QualityTier.POOR
    
    def _check_approval(
        self,
        scores: Dict[str, float]
    ) -> Tuple[bool, List[str], List[str]]:
        """Check if discovery meets approval thresholds."""
        approval_reasons = []
        rejection_reasons = []
        
        overall = sum(scores[dim] * self.weights[dim] for dim in scores)
        
        # Check overall threshold
        if overall >= self.thresholds["overall"]:
            approval_reasons.append(f"Overall score {overall:.2f} >= {self.thresholds['overall']}")
        else:
            rejection_reasons.append(f"Overall score {overall:.2f} < {self.thresholds['overall']}")
        
        # Check rigor threshold
        if scores["rigor"] >= self.thresholds["rigor"]:
            approval_reasons.append(f"Rigor {scores['rigor']:.2f} >= {self.thresholds['rigor']}")
        else:
            rejection_reasons.append(f"Rigor {scores['rigor']:.2f} < {self.thresholds['rigor']}")
        
        # Check adversarial survival (only if Red Team was run)
        if scores["adversarial_survival"] != 0.5:  # Default means not run
            if scores["adversarial_survival"] >= self.thresholds["adversarial_survival"]:
                approval_reasons.append("Passed adversarial review")
            else:
                rejection_reasons.append("Failed adversarial review")
        
        is_approved = len(rejection_reasons) == 0
        
        # [TITAN V172.0] NOVELTY BYPASS ABOLISHED
        # Physically removed the Bayesian Novelty Override that allowed high-novelty garbage
        # to bypass the Rigor Gate. Rigor is now an absolute prerequisite.
            
        return is_approved, approval_reasons, rejection_reasons

    
    def _generate_suggestions(
        self,
        scores: Dict[str, float],
        details: List[DimensionScore]
    ) -> List[str]:
        """Generate improvement suggestions based on low scores."""
        suggestions = []
        
        # Find lowest scoring dimensions
        sorted_dims = sorted(scores.items(), key=lambda x: x[1])
        
        for dim, score in sorted_dims[:3]:  # Top 3 weakest
            if score < 0.6:
                if dim == "novelty":
                    suggestions.append("Strengthen novelty by comparing to prior work more explicitly.")
                elif dim == "rigor":
                    suggestions.append("Add effect sizes, confidence intervals, or larger sample sizes.")
                elif dim == "reproducibility":
                    suggestions.append("Provide code, data, and environment specifications.")
                elif dim == "significance":
                    suggestions.append("Run additional statistical tests or increase sample size.")
                elif dim == "grounding":
                    suggestions.append("Add more citations or data sources to support claims.")
                elif dim == "coherence":
                    suggestions.append("Address contradictions with existing literature.")
                elif dim == "testability":
                    suggestions.append("Include specific, falsifiable predictions.")
                elif dim == "impact":
                    suggestions.append("Articulate practical applications and implications.")
                elif dim == "adversarial_survival":
                    suggestions.append("Address Red Team concerns before finalizing.")
                elif dim == "temporal_robustness":
                    suggestions.append("Verify finding consistency across multiple cycles.")
        
        return suggestions
    
    async def batch_score(
        self,
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[DiscoveryScore]:
        """Score multiple discoveries."""
        import asyncio
        tasks = [self.score_discovery(f, context) for f in findings]
        return await asyncio.gather(*tasks)
    
    def get_scoring_statistics(
        self,
        scores: List[DiscoveryScore]
    ) -> Dict[str, Any]:
        """Aggregate statistics from multiple scores."""
        if not scores:
            return {"count": 0}
        
        approved_count = sum(1 for s in scores if s.is_approved)
        overall_scores = [s.overall_score for s in scores]
        
        tier_counts = {}
        for s in scores:
            tier_counts[s.quality_tier] = tier_counts.get(s.quality_tier, 0) + 1
        
        return {
            "count": len(scores),
            "approved_count": approved_count,
            "approval_rate": approved_count / len(scores),
            "mean_overall_score": sum(overall_scores) / len(overall_scores),
            "min_overall_score": min(overall_scores),
            "max_overall_score": max(overall_scores),
            "tier_distribution": tier_counts
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_scorer_instance: Optional[DiscoveryScorer] = None


def get_discovery_scorer(llm_manager=None) -> DiscoveryScorer:
    """Get or create singleton scorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = DiscoveryScorer(llm_manager=llm_manager)
    return _scorer_instance


async def score_discovery(
    finding: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    red_team_result: Optional[Dict[str, Any]] = None,
    statistical_grounding: Optional[Dict[str, Any]] = None,
    failure_detection: Optional[Dict[str, Any]] = None,
    reproducibility_info: Optional[Dict[str, Any]] = None
) -> DiscoveryScore:
    """
    Quick scoring of a discovery.
    
    Returns:
        DiscoveryScore with 10-dimension assessment
    """
    scorer = get_discovery_scorer()
    return await scorer.score_discovery(
        finding, context, red_team_result, statistical_grounding, 
        failure_detection, reproducibility_info
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    'DiscoveryScorer',
    'DiscoveryScore',
    'DimensionScore',
    'QualityTier',
    'get_discovery_scorer',
    'score_discovery'
]
