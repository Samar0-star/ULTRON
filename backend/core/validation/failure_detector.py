# -*- coding: utf-8 -*-
"""
Failure Detector - ULTRON Ultra-Upgrade
========================================

Detects linguistic and logical failure modes in research findings:
1. Over-interpretation - Claims exceed statistical support
2. Invented Metrics - Metrics don't exist in data or standards
3. Rabbit Hole - Research drifted from original question

Ported and enhanced from Ultron Metascience Pillar.
"""

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set

from backend.discovery.constants import ScientificDefaults

logger = logging.getLogger(__name__)


@dataclass
class FailureModeScore:
    """Score for a single failure mode detection."""
    score: float       # 0.0 - 1.0 (1.0 = severe failure)
    detected: bool     # True if score > threshold
    confidence: float  # 0.0 - 1.0
    evidence: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class FailureDetectionResult:
    """Aggregated results for failure mode detection."""
    over_interpretation: FailureModeScore
    invented_metrics: FailureModeScore
    rabbit_hole: FailureModeScore
    overall_score: float
    passes_validation: bool
    finding_id: str
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    computation_time_seconds: float = 0.0


class FailureDetector:
    """
    Failure Detector for ULTRON.
    
    Audits the 'interpretation' and 'summary' of a finding against its 'statistics'
    to ensure the AI isn't hallucinating significance or metrics.
    """

    # Linguistic markers for over-interpretation
    STRONG_CLAIM_WORDS = {
        'proves', 'prove', 'proven', 'proof', 'demonstrates', 'demonstrate',
        'confirms', 'confirm', 'confirmed', 'establishes', 'establish',
        'definitively', 'conclusively', 'clearly', 'obvious', 'obviously',
        'undoubtedly', 'certainly', 'surely', 'reveals', 'identifies'
    }

    HEDGED_CLAIM_WORDS = {
        'suggests', 'suggest', 'indicates', 'indicate', 'may', 'might',
        'could', 'potentially', 'possibly', 'appears', 'seems', 'likely',
        'unlikely', 'tends', 'hints', 'implies', 'preliminary', 'tentative',
        'exploratory', 'consistent', 'associated', 'correlates'
    }

    # Standard statistical and scientific metrics (to prevent flagging standard terms or prose labels as invented)
    STANDARD_METRICS = {
        'p_value', 'p', 'pvalue', 'p_permutation', 'p_adj', 'adjusted_p_value', 'mann_whitney_p',
        'effect_size', 'cohens_d', 'cohen_d', 'd', 'observed_diff', 'r_squared', 'r2',
        'correlation', 'rho', 'tau', 't_statistic', 't_stat', 't', 'f_statistic', 'f',
        'chi2', 'z_score', 'welch_z', 'n', 'sample_size', 'df', 'mean', 'median', 'std',
        'variance', 'se', 'standard_error', 'ci', 'confidence_interval',
        'accuracy', 'precision', 'recall', 'f1', 'auc', 'roc_auc', 'logfc', 'coefficient',
        'alpha', 'power', 'beta', 'mse', 'rmse', 'mae', 'mape', 'loss', 'val_loss', 'train_loss',
        'score', 'confidence', 'uncertainty', 'sigma', 'robustness_score', 'survival_rate',
        'unbreakability_index', 'cycle', 'step', 'status', 'verdict', 'supported', 'note',
        'result', 'count', 'total', 'ratio', 'threshold', 'baseline', 'temperature', 'pressure'
    }

    def __init__(
        self,
        over_interp_threshold: float = 0.6,
        invented_metrics_threshold: float = 0.5,
        rabbit_hole_threshold: float = 0.7
    ):
        self.over_interp_threshold = over_interp_threshold
        self.invented_metrics_threshold = invented_metrics_threshold
        self.rabbit_hole_threshold = rabbit_hole_threshold

    def _extract_stats_and_text(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """P0-39: Unwrap nested Orchestrator/Router/ExperimentAgent finding dicts."""
        if not isinstance(finding, dict):
            return {"stats": {}, "text": str(finding)}
        stats = dict(finding.get("statistics") or {})
        res = finding.get("result", {})
        if isinstance(res, dict) and "result" in res and isinstance(res["result"], dict):
            res = res["result"]
        if isinstance(res, dict):
            inner_res = res.get("result", {}) if isinstance(res.get("result"), dict) else {}
            meta = res.get("metadata", {}) if isinstance(res.get("metadata"), dict) else {}
            inner_meta = inner_res.get("metadata", {}) if isinstance(inner_res.get("metadata"), dict) else {}
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
                    for k, v in cand.items():
                        if v is not None and k not in stats:
                            stats[k] = v
        summary = finding.get("summary") or (res.get("summary") if isinstance(res, dict) else "") or (res.get("text") if isinstance(res, dict) else "") or finding.get("content") or ""
        interp = finding.get("interpretation") or ""
        return {"stats": stats, "text": f"{interp} {summary}".strip()}

    def detect_failures(
        self,
        finding: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> FailureDetectionResult:
        """
        Run complete failure detection suite on a finding.
        """
        start_time = time.time()
        context = context or {}
        
        over_interp = self._detect_over_interpretation(finding)
        invented = self._detect_invented_metrics(finding, context)
        rabbit_hole = self._detect_rabbit_hole(finding, context)
        
        # Calculate overall score (weighted average)
        overall = (
            0.4 * over_interp.score +
            0.3 * invented.score +
            0.3 * rabbit_hole.score
        )
        
        warnings = []
        if over_interp.detected: warnings.append("Over-interpretation detected")
        if invented.detected: warnings.append("Invented metrics detected")
        if rabbit_hole.detected: warnings.append("Rabbit hole detected")
        
        recommendations = list(dict.fromkeys(
            over_interp.recommendations +
            invented.recommendations +
            rabbit_hole.recommendations
        ))
        
        passes = not any([over_interp.detected, invented.detected, rabbit_hole.detected])
        
        return FailureDetectionResult(
            over_interpretation=over_interp,
            invented_metrics=invented,
            rabbit_hole=rabbit_hole,
            overall_score=overall,
            passes_validation=passes,
            finding_id=finding.get('finding_id', finding.get('task_id', 'unknown')),
            warnings=warnings,
            recommendations=recommendations,
            computation_time_seconds=time.time() - start_time
        )

    def _detect_over_interpretation(self, finding: Dict[str, Any]) -> FailureModeScore:
        """
        [TITAN V202.0] MATHEMATICAL OVER-INTERPRETATION DETECTION
        Physically abolished naive word-counting heuristics.
        Over-interpretation is now defined strictly as mathematical contradiction 
        (e.g., claiming a discovery when empirical p-value > alpha).
        """
        extracted = self._extract_stats_and_text(finding)
        stats = extracted["stats"]
        
        # 1. Statistical Reality (preserve p_value == 0.0 without falsy 'or' bug)
        p_val = None
        for pk in ('p_value', 'p', 'pvalue', 'p_permutation'):
            if stats.get(pk) is not None:
                p_val = stats.get(pk)
                break
        
        score = 0.0
        reason = ""
        
        if p_val is not None:
            try:
                p = float(p_val)
                alpha = ScientificDefaults.ALPHA_SIGNIFICANCE
                # If the system tries to commit a supportive finding but p >= alpha, that is over-interpretation.
                supported = stats.get("supported")
                ev_type = str(stats.get("evidence_type", "")).lower()
                if p >= alpha and supported is not False and ev_type != "refute":
                    score = 0.95
                    reason = f"Mathematical contradiction: Claiming finding with p={p:.4f} >= {alpha}"
            except (ValueError, TypeError):
                pass
            
        evidence = [reason] if reason else []
        recs = ["Reject finding: fails strict p-value check."] if score > self.over_interp_threshold else []
            
        return FailureModeScore(
            score=min(1.0, score),
            detected=score > self.over_interp_threshold,
            confidence=0.8 if p_val is not None else 0.5,
            evidence=evidence,
            recommendations=recs
        )

    def _detect_invented_metrics(
        self, 
        finding: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> FailureModeScore:
        """
        Detect mentions of metrics not present in data or headers.
        """
        extracted = self._extract_stats_and_text(finding)
        text = extracted["text"].lower()
        stats_keys = {str(k).lower() for k in extracted["stats"].keys()}
        dataset_schema = context.get('dataset_schema', [])
        
        # Extract potential metric names only when explicitly assigned a numeric value (metric = 0.5)
        pattern1 = r'\b([a-z_][a-z0-9_]{3,})\s*=\s*[-+]?[0-9]*\.?[0-9]+'
        pattern2 = r'(?:the\s+)?\b([a-z_][a-z0-9_]{3,})\s+(?:was|is)\s+[-+]?[0-9]+\.[0-9]+'
        
        potential_metrics = set(re.findall(pattern1, text))
        potential_metrics.update(re.findall(pattern2, text))
        
        known_metrics = self.STANDARD_METRICS.union(set(m.lower() for m in dataset_schema)).union(stats_keys)
        
        invented = [m for m in potential_metrics if m not in known_metrics]
        
        score = 0.0
        if potential_metrics:
            score = len(invented) / len(potential_metrics)
            
        evidence = [f"Metrics audited: {len(potential_metrics)}"]
        if invented:
            evidence.append(f"Potentially invented metrics: {', '.join(invented)}")
            
        recs = []
        if score > self.invented_metrics_threshold:
            recs.append(f"Define or remove undefined metrics: {', '.join(invented)}")
            
        return FailureModeScore(
            score=min(1.0, score),
            detected=score > self.invented_metrics_threshold,
            confidence=0.7,
            evidence=evidence,
            recommendations=recs
        )

    def _detect_rabbit_hole(
        self, 
        finding: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> FailureModeScore:
        """
        Detect if the finding has drifted from the original research question.
        Uses semantic overlap with the research question.
        """
        rq = context.get('research_question', '').lower()
        if not rq:
            return FailureModeScore(0.0, False, 0.0, ["No research question in context"])
            
        text = f"{finding.get('summary', '')} {finding.get('interpretation', '')}".lower()
        
        # Naive keyword overlap for rabbit hole detection
        rq_words = set(re.findall(r'\w{4,}', rq))
        text_words = set(re.findall(r'\w{4,}', text))
        
        if not rq_words:
            return FailureModeScore(0.0, False, 0.5)
            
        overlap = len(rq_words.intersection(text_words)) / len(rq_words)
        
        # Low overlap = high rabbit hole score
        score = 1.0 - overlap
        
        evidence = [f"Research Question overlap: {overlap:.2f}"]
        recs = []
        if score > self.rabbit_hole_threshold:
            recs.append("Finding appears drifted from original research question")
            
        return FailureModeScore(
            score=min(1.0, score),
            detected=score > self.rabbit_hole_threshold,
            confidence=0.6,
            evidence=evidence,
            recommendations=recs
        )

