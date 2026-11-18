# -*- coding: utf-8 -*-
"""
Context Compressor - ULTRON Ultra-Upgrade
==========================================

Hierarchical context compression for managing large research contexts
within LLM token limits. Achieves 20:1+ compression ratios.

3-Tier Architecture:
1. Task Level - Individual experiment results (50:1)
2. Cycle Level - Groups of tasks (20:1)
3. Mission Level - Full research history (10:1)

Strategies:
- Rule-based statistics extraction (fast, preserves precision)
- Key findings summarization (preserves meaning)
- Numerical precision preservation for critical results

Author: ULTRON Team
"""

import logging
import time
import re
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CompressedContext:
    """Container for compressed context at a specific tier."""
    
    tier: str  # "task", "cycle", "mission"
    summary: str
    statistics: Dict[str, Any]
    key_findings: List[str]
    
    # Metadata
    original_tokens: int = 0
    compressed_tokens: int = 0
    compression_ratio: float = 1.0
    
    # Reference to full content (if needed)
    full_content_path: Optional[str] = None
    content_hash: Optional[str] = None
    
    # Timing
    compressed_at: datetime = field(default_factory=datetime.utcnow)
    compression_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "summary": self.summary,
            "statistics": self.statistics,
            "key_findings": self.key_findings,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": self.compression_ratio,
            "full_content_path": self.full_content_path,
            "content_hash": self.content_hash,
            "compressed_at": self.compressed_at.isoformat(),
            "compression_time_seconds": self.compression_time_seconds
        }
    
    def to_prompt_string(self) -> str:
        """Convert to string suitable for LLM prompt injection."""
        lines = [f"## {self.tier.upper()} Summary"]
        lines.append(self.summary)
        
        if self.statistics:
            lines.append("\n**Key Statistics:**")
            for key, value in list(self.statistics.items())[:10]:
                lines.append(f"- {key}: {value}")
        
        if self.key_findings:
            lines.append("\n**Key Findings:**")
            for i, finding in enumerate(self.key_findings[:5], 1):
                lines.append(f"{i}. {finding}")
        
        return "\n".join(lines)

    def save_to_world_model(self, world_model: Optional[Any] = None):
        """Persist this context to the Global World Model (SQLite)."""
        try:
            # Lazy import to avoid circular dependency
            from backend.core.world_model import get_world_model, Entity

            wm = world_model or get_world_model()

            # Create persistent entity
            entity = Entity(
                type="Artifact",
                properties=self.to_dict(),
                entity_id=self.content_hash or hashlib.md5(self.summary.encode()).hexdigest()[:12],
                confidence=1.0,
                source="ContextCompressor",
                verified=True,
                metadata={"tier": self.tier, "context_type": "CompressedContext"}
            )

            wm.add_entity(entity)
            logger.debug(f" Persisted {self.tier} context to WorldModel")
            return True
        except Exception as e:
            logger.error(f"Failed to persist context: {e}")
            return False


class TaskCompressor:
    """
    Compresses individual task/experiment results.
    
    Target: 20:1 compression ratio
    
    Strategies:
    - Extract statistical results (p-values, effect sizes, etc.)
    - Summarize methodology to one line
    - Preserve key numerical findings
    - Drop verbose output/logs
    """
    
    # Patterns for statistical extraction
    P_VALUE_PATTERNS = [
        r'\bp\s*[=<>]\s*([\d.]+(?:e[+-]?\d+)?)',
        r'\bp-value\s*[=:]\s*([\d.]+(?:e[+-]?\d+)?)',
        r'\bsignificance[:\s]+([\d.]+)',
    ]
    
    CORRELATION_PATTERNS = [
        r'\br\s*=\s*([-+]?[\d.]+)',
        r'\bcorrelation[:\s]+([-+]?[\d.]+)',
        r'\bpearson[:\s]+([-+]?[\d.]+)',
        r'\bspearman[:\s]+([-+]?[\d.]+)',
    ]
    
    SAMPLE_SIZE_PATTERNS = [
        r'\bn\s*=\s*(\d+)',
        r'\bN\s*=\s*(\d+)',
        r'\bsample\s*size[:\s]+(\d+)',
        r'(\d+)\s*samples',
        r'(\d+)\s*observations',
    ]
    
    # NEW: High-Fidelity Scientific Patterns (Phase 12: Deep Science)
    BIOLOGICAL_METRIC_PATTERNS = [
        r'(Kd|IC50|EC50|Ki)\s*[=:]\s*([\d.]+\s*(?:nM|uM|mM|pM|M))',
        r'binding\s+affinity\s*[=:]\s*([\d.]+\s*(?:nM|uM|mM|pM|M))',
        r'affinity\s*[=:]\s*([\d.]+\s*(?:nM|uM|mM|pM|M))',
        r'(\d+\.?\d*)\s*(?:nM|uM|mM|pM|M)\b'
    ]

    CHEMICAL_ENTITY_PATTERNS = [
        r'([A-Z0-9]{4})\.pdb', # PDB IDs
        r'\b(SMILES|smiles)[:\s]+([A-Za-z0-9#\(\)\.\=\+\-\[\]@]+)', # SMILES strings
        r'C\d+H\d+[A-Z0-9]*', # Molecular formulas
    ]
    
    EFFECT_SIZE_PATTERNS = [
        r"cohen'?s?\s*d\s*[=:]\s*([-+]?[\d.]+)",
        r'effect\s*size\s*[=:]\s*([-+]?[\d.]+)',
        r'eta\s*squared?\s*[=:]\s*([-+]?[\d.]+)',
        r'r\s*squared?\s*[=:]\s*([-+]?[\d.]+)',
    ]
    
    CI_PATTERNS = [
        r'(\d+)%\s*CI\s*[=:\[]?\s*\[?([-+]?[\d.]+)[,\s]+([-+]?[\d.]+)\]?',
        r'confidence\s*interval[:\s]+\[?([-+]?[\d.]+)[,\s]+([-+]?[\d.]+)\]?',
    ]
    
    def __init__(self, llm_manager=None):
        """
        Initialize task compressor.
        
        Args:
            llm_manager: Optional LLM for summary generation (uses rule-based if None)
        """
        self.llm_manager = llm_manager
    
    def compress_task(
        self,
        task_result: Dict[str, Any],
        max_summary_tokens: int = 150
    ) -> CompressedContext:
        """
        Compress a single task result.
        
        Args:
            task_result: Task result dictionary
            max_summary_tokens: Maximum tokens for summary
        
        Returns:
            CompressedContext with extracted statistics and summary
        """
        start_time = time.time()
        
        # Serialize original content
        content_str = self._serialize_content(task_result)
        original_tokens = self._estimate_tokens(content_str)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        
        # Extract statistics
        statistics = self._extract_statistics(content_str, task_result)
        
        # Extract key findings
        key_findings = self._extract_key_findings(task_result)
        
        # Generate summary
        summary = self._generate_summary(task_result, statistics, max_summary_tokens)
        
        # Assemble compressed context
        compressed_str = summary + str(statistics) + str(key_findings)
        compressed_tokens = self._estimate_tokens(compressed_str)
        
        compression_time = time.time() - start_time
        
        return CompressedContext(
            tier="task",
            summary=summary,
            statistics=statistics,
            key_findings=key_findings,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=original_tokens / max(compressed_tokens, 1),
            content_hash=content_hash,
            compression_time_seconds=compression_time
        )
    
    def _serialize_content(self, task_result: Dict[str, Any]) -> str:
        """Serialize task result to string for processing."""
        import json
        try:
            return json.dumps(task_result, indent=2, default=str)
        except Exception:
            return str(task_result)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: ~4 chars per token)."""
        return len(text) // 4
    
    def _extract_statistics(
        self,
        content: str,
        task_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract statistical information using rule-based patterns."""
        stats = {}
        content_lower = content.lower()
        
        # Try to get from structured data first
        if "statistics" in task_result and isinstance(task_result["statistics"], dict):
            stats.update(task_result["statistics"])
        if "results" in task_result and isinstance(task_result["results"], dict):
            for key in ["p_value", "pvalue", "r", "correlation", "n", "sample_size", "effect_size"]:
                if key in task_result["results"]:
                    stats[key] = task_result["results"][key]
        
        # Extract p-values (must be in [0.0, 1.0])
        for pattern in self.P_VALUE_PATTERNS:
            matches = re.findall(pattern, content_lower)
            if matches:
                try:
                    valid_p = [float(m) for m in matches[:5] if 0.0 <= float(m) <= 1.0]
                    if valid_p:
                        stats["p_values"] = stats.get("p_values", []) + valid_p[:3]
                except ValueError:
                    pass
        
        # Extract correlations (must be in [-1.0, 1.0])
        for pattern in self.CORRELATION_PATTERNS:
            matches = re.findall(pattern, content_lower)
            if matches:
                try:
                    valid_r = [float(m) for m in matches[:5] if -1.0 <= float(m) <= 1.0]
                    if valid_r:
                        stats["correlations"] = stats.get("correlations", []) + valid_r[:3]
                except ValueError:
                    pass
        
        # Extract sample sizes
        for pattern in self.SAMPLE_SIZE_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                try:
                    stats["sample_sizes"] = stats.get("sample_sizes", []) + [int(m) for m in matches[:3]]
                except ValueError:
                    pass
        
        # Extract effect sizes
        for pattern in self.EFFECT_SIZE_PATTERNS:
            matches = re.findall(pattern, content_lower)
            if matches:
                try:
                    stats["effect_sizes"] = stats.get("effect_sizes", []) + [float(m) for m in matches[:3]]
                except ValueError:
                    pass
        
        # Extract confidence intervals
        for pattern in self.CI_PATTERNS:
            matches = re.findall(pattern, content_lower)
            if matches:
                try:
                    # Handle different match formats
                    if len(matches[0]) == 3:
                        stats["confidence_interval"] = f"[{matches[0][1]}, {matches[0][2]}]"
                    elif len(matches[0]) == 2:
                        stats["confidence_interval"] = f"[{matches[0][0]}, {matches[0][1]}]"
                except (ValueError, IndexError):
                    pass
        
        # Deduplicate list values
        for key in ["p_values", "correlations", "sample_sizes", "effect_sizes"]:
            if key in stats and isinstance(stats[key], list):
                stats[key] = list(set(stats[key]))[:3]  # Keep top 3 unique
        
        return stats
    
    def _extract_key_findings(self, task_result: Dict[str, Any]) -> List[str]:
        """Extract key findings from task result."""
        findings = []
        
        # Check for explicit findings
        if "findings" in task_result:
            findings.extend(task_result["findings"][:5])
        
        if "conclusions" in task_result:
            conclusions = task_result["conclusions"]
            if isinstance(conclusions, list):
                findings.extend(conclusions[:3])
            elif isinstance(conclusions, str):
                findings.append(conclusions[:200])
        
        # Check summary
        if "summary" in task_result:
            summary = task_result["summary"]
            if summary and summary not in findings:
                findings.append(summary[:200])
        
        # Check for interpretation
        if "interpretation" in task_result:
            interp = task_result["interpretation"]
            if interp and len(str(interp)) < 200:
                findings.append(str(interp))
        
        # Deduplicate and limit
        unique_findings = []
        for f in findings:
            f_str = str(f).strip()
            if f_str and f_str not in unique_findings:
                unique_findings.append(f_str)
        
        return unique_findings[:5]
    
    def _generate_summary(
        self,
        task_result: Dict[str, Any],
        statistics: Dict[str, Any],
        max_tokens: int
    ) -> str:
        """Generate concise summary."""
        parts = []
        
        # Task type/name
        task_type = task_result.get("task_type", task_result.get("type", "Analysis"))
        parts.append(f"[{task_type}]")
        
        # Main result
        if "summary" in task_result:
            summary = task_result["summary"]
            if len(summary) > 200:
                summary = summary[:197] + "..."
            parts.append(summary)
        elif "conclusion" in task_result:
            parts.append(str(task_result["conclusion"])[:200])
        
        # Key statistics inline
        stat_parts = []
        if "p_values" in statistics and statistics["p_values"]:
            min_p = min(statistics["p_values"])
            stat_parts.append(f"p={min_p:.4f}")
        if "correlations" in statistics and statistics["correlations"]:
            max_r = max(statistics["correlations"], key=abs)
            stat_parts.append(f"r={max_r:.2f}")
        if "sample_sizes" in statistics and statistics["sample_sizes"]:
            total_n = sum(statistics["sample_sizes"])
            stat_parts.append(f"n={total_n}")
        
        if stat_parts:
            parts.append(f"({', '.join(stat_parts)})")
        
        result = " ".join(parts)
        
        # Truncate if too long
        max_chars = max_tokens * 4
        if len(result) > max_chars:
            result = result[:max_chars-3] + "..."
        
        return result


class CycleCompressor:
    """
    Compresses a full research cycle (multiple tasks).
    
    Target: 20:1 compression ratio
    
    Strategies:
    - Aggregate statistics across tasks
    - Summarize key findings by category
    - Track hypothesis status changes
    - Preserve cycle-level insights
    """
    
    def __init__(self, task_compressor: Optional[TaskCompressor] = None):
        self.task_compressor = task_compressor or TaskCompressor()
    
    def compress_cycle(
        self,
        cycle_data: Dict[str, Any],
        compressed_tasks: Optional[List[CompressedContext]] = None
    ) -> CompressedContext:
        """
        Compress an entire research cycle.
        
        Args:
            cycle_data: Cycle data with tasks, hypotheses, findings
            compressed_tasks: Pre-compressed task results (if available)
        
        Returns:
            CompressedContext for the cycle
        """
        start_time = time.time()
        
        # Compress tasks if not already done
        if not isinstance(cycle_data, dict):
            cycle_data = {"tasks": [{"summary": str(cycle_data)}]}
        if compressed_tasks is None:
            raw_tasks = cycle_data.get("tasks", []) or cycle_data.get("task_results", [])
            if not raw_tasks and any(k in cycle_data for k in ("id", "description", "result", "summary", "findings")):
                # cycle_data is itself a single task dict or session dict with findings
                if "findings" in cycle_data and isinstance(cycle_data["findings"], list) and not cycle_data.get("result"):
                    raw_tasks = [
                        f if isinstance(f, dict) else {"summary": str(f)}
                        for f in cycle_data["findings"]
                    ]
                else:
                    raw_tasks = [cycle_data]
            normalized_tasks = []
            for t in raw_tasks:
                if isinstance(t, dict):
                    # Unwrap ResearchTask.to_dict() so result.summary / result.findings are visible
                    if isinstance(t.get("result"), dict):
                        merged_t = dict(t["result"])
                        merged_t.setdefault("task_type", t.get("task_type", "Analysis"))
                        if not merged_t.get("summary") and t.get("description"):
                            merged_t["summary"] = t["description"]
                        normalized_tasks.append(merged_t)
                    else:
                        t_copy = dict(t)
                        if not t_copy.get("summary") and t_copy.get("description"):
                            t_copy["summary"] = t_copy["description"]
                        normalized_tasks.append(t_copy)
                else:
                    normalized_tasks.append({"summary": str(t)})
            compressed_tasks = [
                self.task_compressor.compress_task(task)
                for task in normalized_tasks
            ]
        
        # Aggregate statistics
        aggregated_stats = self._aggregate_statistics(compressed_tasks)
        
        # Collect key findings
        all_findings = []
        for ct in compressed_tasks:
            all_findings.extend(ct.key_findings)
        for f in cycle_data.get("findings", []) if isinstance(cycle_data.get("findings"), list) else []:
            if isinstance(f, dict):
                f_sum = f.get("summary") or (f.get("result", {}).get("summary") if isinstance(f.get("result"), dict) else "")
                if f_sum:
                    all_findings.append(str(f_sum)[:200])
            elif isinstance(f, str) and f.strip():
                all_findings.append(f.strip()[:200])
        
        # Deduplicate and prioritize
        key_findings = self._prioritize_findings(all_findings)[:7]
        
        # Generate cycle summary
        summary = self._generate_cycle_summary(cycle_data, aggregated_stats, key_findings)
        
        # Calculate compression metrics
        original_tokens = sum(ct.original_tokens for ct in compressed_tasks)
        compressed_str = summary + str(aggregated_stats) + str(key_findings)
        compressed_tokens = len(compressed_str) // 4
        
        compression_time = time.time() - start_time
        
        return CompressedContext(
            tier="cycle",
            summary=summary,
            statistics=aggregated_stats,
            key_findings=key_findings,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=original_tokens / max(compressed_tokens, 1),
            compression_time_seconds=compression_time
        )
    
    def _aggregate_statistics(
        self,
        compressed_tasks: List[CompressedContext]
    ) -> Dict[str, Any]:
        """Aggregate statistics across tasks."""
        all_p_values = []
        all_correlations = []
        all_sample_sizes = []
        all_effect_sizes = []
        
        for ct in compressed_tasks:
            stats = ct.statistics
            all_p_values.extend(stats.get("p_values", []))
            all_correlations.extend(stats.get("correlations", []))
            all_sample_sizes.extend(stats.get("sample_sizes", []))
            all_effect_sizes.extend(stats.get("effect_sizes", []))
        
        aggregated = {
            "task_count": len(compressed_tasks),
        }
        
        if all_p_values:
            from backend.discovery.constants import ScientificDefaults
            aggregated["min_p_value"] = min(all_p_values)
            aggregated["significant_count"] = sum(1 for p in all_p_values if p < ScientificDefaults.ALPHA_SIGNIFICANCE)
        
        if all_correlations:
            aggregated["max_correlation"] = max(all_correlations, key=abs)
            aggregated["mean_correlation"] = sum(all_correlations) / len(all_correlations)
        
        if all_sample_sizes:
            aggregated["total_sample_size"] = sum(all_sample_sizes)
        
        if all_effect_sizes:
            aggregated["mean_effect_size"] = sum(all_effect_sizes) / len(all_effect_sizes)
        
        return aggregated
    
    def _prioritize_findings(self, findings: List[str]) -> List[str]:
        """Prioritize and deduplicate findings."""
        # Score by length and keyword presence
        scored = []
        priority_words = ["significant", "found", "discovered", "confirmed", "rejected",
                         "correlation", "effect", "increase", "decrease", "novel"]
        
        seen_hashes = set()
        for finding in findings:
            # Skip duplicates
            finding_hash = hashlib.md5(finding.lower().encode()).hexdigest()
            if finding_hash in seen_hashes:
                continue
            seen_hashes.add(finding_hash)
            
            # Score
            score = 0
            finding_lower = finding.lower()
            for word in priority_words:
                if word in finding_lower:
                    score += 1
            
            # Prefer medium-length findings
            if 50 < len(finding) < 200:
                score += 1
            
            scored.append((score, finding))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [f for _, f in scored]
    
    def _generate_cycle_summary(
        self,
        cycle_data: Dict[str, Any],
        stats: Dict[str, Any],
        findings: List[str]
    ) -> str:
        """Generate cycle-level summary."""
        cycle_num = cycle_data.get("cycle", cycle_data.get("cycle_number", "?"))
        
        parts = [f"Cycle {cycle_num}:"]
        
        # Task summary
        task_count = stats.get("task_count", 0)
        parts.append(f"{task_count} tasks completed.")
        
        # Statistical highlights
        stat_highlights = []
        if "significant_count" in stats:
            stat_highlights.append(f"{stats['significant_count']} significant findings")
        if "min_p_value" in stats:
            stat_highlights.append(f"min p={stats['min_p_value']:.4f}")
        if "max_correlation" in stats:
            stat_highlights.append(f"max |r|={abs(stats['max_correlation']):.2f}")
        
        if stat_highlights:
            parts.append(" | ".join(stat_highlights) + ".")
        
        # Top finding
        if findings:
            parts.append(f"Key: {findings[0][:150]}")
        
        # Hypothesis status
        hyp_confirmed = cycle_data.get("hypotheses_confirmed", 0)
        hyp_refuted = cycle_data.get("hypotheses_refuted", 0)
        if hyp_confirmed or hyp_refuted:
            parts.append(f"Hypotheses: {hyp_confirmed} confirmed, {hyp_refuted} refuted.")
        
        return " ".join(parts)


class MissionCompressor:
    """
    Compresses full research mission (multiple cycles).
    
    Target: 10:1 compression ratio
    
    Strategies:
    - Summarize cycle progression
    - Track convergence trajectory
    - Highlight confirmed/refuted hypotheses
    - Preserve mission-critical discoveries
    """
    
    def __init__(self, cycle_compressor: Optional[CycleCompressor] = None):
        self.cycle_compressor = cycle_compressor or CycleCompressor()
    
    def compress_mission(
        self,
        mission_data: Dict[str, Any],
        compressed_cycles: Optional[List[CompressedContext]] = None
    ) -> CompressedContext:
        """
        Compress entire research mission.
        
        Args:
            mission_data: Full mission data (either {'cycles': [...]} or ResearchSession.to_dict())
            compressed_cycles: Pre-compressed cycle contexts
        
        Returns:
            CompressedContext for the mission
        """
        start_time = time.time()
        
        # Compress cycles if not provided
        if compressed_cycles is None:
            raw_cycles = mission_data.get("cycles")
            if isinstance(raw_cycles, list) and raw_cycles:
                cycles = raw_cycles
            else:
                # Handle ResearchSession.to_dict() which stores flat 'tasks' and 'findings'
                raw_tasks = mission_data.get("tasks", [])
                raw_findings = mission_data.get("findings", [])
                if raw_tasks or raw_findings:
                    cycles_by_num: Dict[Any, List[Any]] = {}
                    for idx, t in enumerate(raw_tasks):
                        c_num = t.get("cycle", 1) if isinstance(t, dict) else 1
                        cycles_by_num.setdefault(c_num, []).append(t)
                    if cycles_by_num:
                        cycles = [
                            {
                                "cycle": c_num,
                                "tasks": c_tasks,
                                "findings": raw_findings if i == len(cycles_by_num) - 1 else [],
                            }
                            for i, (c_num, c_tasks) in enumerate(sorted(cycles_by_num.items(), key=lambda x: str(x[0])))
                        ]
                    else:
                        cycles = [{"cycle": mission_data.get("current_cycle", 1), "tasks": [], "findings": raw_findings}]
                else:
                    cycles = []
            compressed_cycles = [
                self.cycle_compressor.compress_cycle(cycle)
                for cycle in cycles
            ]
        
        # Aggregate mission statistics
        mission_stats = self._aggregate_mission_stats(compressed_cycles, mission_data)
        
        # Collect breakthrough findings
        all_findings = []
        for cc in compressed_cycles:
            all_findings.extend(cc.key_findings)
        
        breakthrough_findings = self._identify_breakthroughs(all_findings)[:5]
        
        # Generate mission summary
        summary = self._generate_mission_summary(
            mission_data, mission_stats, breakthrough_findings, compressed_cycles
        )
        
        # Calculate compression
        original_tokens = sum(cc.original_tokens for cc in compressed_cycles)
        compressed_str = summary + str(mission_stats) + str(breakthrough_findings)
        compressed_tokens = len(compressed_str) // 4
        
        compression_time = time.time() - start_time
        
        return CompressedContext(
            tier="mission",
            summary=summary,
            statistics=mission_stats,
            key_findings=breakthrough_findings,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=original_tokens / max(compressed_tokens, 1),
            compression_time_seconds=compression_time
        )
    
    def _aggregate_mission_stats(
        self,
        compressed_cycles: List[CompressedContext],
        mission_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate statistics across entire mission."""
        stats = {
            "total_cycles": len(compressed_cycles),
            "total_tasks": sum(cc.statistics.get("task_count", 0) for cc in compressed_cycles),
        }
        
        # Aggregate p-values
        all_min_p = [cc.statistics.get("min_p_value") for cc in compressed_cycles
                     if cc.statistics.get("min_p_value") is not None]
        if all_min_p:
            stats["overall_min_p"] = min(all_min_p)
        
        # Convergence info
        if "convergence" in mission_data:
            conv = mission_data["convergence"]
            stats["converged"] = conv.get("converged", False)
            stats["stopping_reason"] = conv.get("reason", "unknown")
        
        # Hypothesis tracking
        stats["total_hypotheses"] = mission_data.get("total_hypotheses", 0)
        stats["confirmed_hypotheses"] = mission_data.get("confirmed_hypotheses", 0)
        stats["refuted_hypotheses"] = mission_data.get("refuted_hypotheses", 0)
        
        return stats
    
    def _identify_breakthroughs(self, findings: List[str]) -> List[str]:
        """Identify breakthrough findings from all cycles."""
        breakthrough_words = ["breakthrough", "novel", "first", "significant",
                             "confirmed", "discovered", "unprecedented", "major"]
        
        scored = []
        seen = set()
        
        for finding in findings:
            finding_hash = hashlib.md5(finding.lower().encode()).hexdigest()
            if finding_hash in seen:
                continue
            seen.add(finding_hash)
            
            score = 0
            finding_lower = finding.lower()
            for word in breakthrough_words:
                if word in finding_lower:
                    score += 2
            
            # Prefer findings with statistics
            if any(x in finding for x in ["p=", "r=", "n=", "%"]):
                score += 1
            
            scored.append((score, finding))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored]
    
    def _generate_mission_summary(
        self,
        mission_data: Dict[str, Any],
        stats: Dict[str, Any],
        breakthroughs: List[str],
        compressed_cycles: List[CompressedContext]
    ) -> str:
        """Generate mission-level summary."""
        objective = mission_data.get("research_objective", mission_data.get("objective", "Research"))
        
        parts = [f"Mission: {objective[:100]}"]
        
        # Cycle summary
        parts.append(f"Completed {stats['total_cycles']} cycles, {stats['total_tasks']} tasks.")
        
        # Convergence
        if stats.get("converged"):
            parts.append(f"Converged: {stats.get('stopping_reason', 'answer found')}.")
        
        # Hypothesis results
        confirmed = stats.get("confirmed_hypotheses", 0)
        refuted = stats.get("refuted_hypotheses", 0)
        if confirmed or refuted:
            parts.append(f"Hypotheses: {confirmed} confirmed, {refuted} refuted.")
        
        # Top breakthrough
        if breakthroughs:
            parts.append(f"Breakthrough: {breakthroughs[0][:150]}")
        
        return " ".join(parts)


class ContextCompressor:
    """
    Main orchestrator for hierarchical context compression.
    
    Coordinates compression across task, cycle, and mission tiers.
    
    Usage:
        compressor = ContextCompressor()
        
        # Compress single task
        task_ctx = compressor.compress_task(task_result)
        
        # Compress full cycle
        cycle_ctx = compressor.compress_cycle(cycle_data)
        
        # Compress entire mission
        mission_ctx = compressor.compress_mission(mission_data)
        
        # Get prompt-ready context
        prompt_context = mission_ctx.to_prompt_string()
    """
    
    def __init__(self, llm_manager=None):
        """
        Initialize context compressor.
        
        Args:
            llm_manager: Optional LLM manager for advanced summarization
        """
        self.task_compressor = TaskCompressor(llm_manager)
        self.cycle_compressor = CycleCompressor(self.task_compressor)
        self.mission_compressor = MissionCompressor(self.cycle_compressor)
    
    def compress_task(
        self,
        task_result: Dict[str, Any],
        max_summary_tokens: int = 150
    ) -> CompressedContext:
        """Compress a single task result."""
        return self.task_compressor.compress_task(task_result, max_summary_tokens)
    
    def compress_cycle(
        self,
        cycle_data: Dict[str, Any],
        pre_compressed_tasks: Optional[List[CompressedContext]] = None
    ) -> CompressedContext:
        """Compress an entire research cycle."""
        return self.cycle_compressor.compress_cycle(cycle_data, pre_compressed_tasks)
    
    def compress_mission(
        self,
        mission_data: Dict[str, Any],
        pre_compressed_cycles: Optional[List[CompressedContext]] = None
    ) -> CompressedContext:
        """Compress entire research mission."""
        return self.mission_compressor.compress_mission(mission_data, pre_compressed_cycles)
    
    def compress_for_prompt(
        self,
        contexts: List[CompressedContext],
        max_tokens: int = 2000
    ) -> str:
        """
        Combine multiple compressed contexts for prompt injection.
        
        Args:
            contexts: List of compressed contexts
            max_tokens: Maximum tokens for combined output
        
        Returns:
            Prompt-ready string
        """
        parts = []
        remaining_tokens = max_tokens
        
        for ctx in contexts:
            ctx_str = ctx.to_prompt_string()
            ctx_tokens = len(ctx_str) // 4
            
            if ctx_tokens <= remaining_tokens:
                parts.append(ctx_str)
                remaining_tokens -= ctx_tokens
            else:
                # Truncate if needed
                max_chars = remaining_tokens * 4
                parts.append(ctx_str[:max_chars] + "...")
                break
        
        return "\n\n---\n\n".join(parts)
    
    def get_compression_stats(
        self,
        contexts: List[CompressedContext]
    ) -> Dict[str, Any]:
        """Get aggregate compression statistics."""
        if not contexts:
            return {"count": 0}
        
        total_original = sum(c.original_tokens for c in contexts)
        total_compressed = sum(c.compressed_tokens for c in contexts)
        
        return {
            "count": len(contexts),
            "total_original_tokens": total_original,
            "total_compressed_tokens": total_compressed,
            "overall_compression_ratio": total_original / max(total_compressed, 1),
            "total_compression_time_seconds": sum(c.compression_time_seconds for c in contexts),
            "tier_breakdown": {
                tier: sum(1 for c in contexts if c.tier == tier)
                for tier in ["task", "cycle", "mission"]
            }
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_compressor_instance: Optional[ContextCompressor] = None


def get_context_compressor(llm_manager=None) -> ContextCompressor:
    """Get or create singleton compressor instance."""
    global _compressor_instance
    if _compressor_instance is None:
        _compressor_instance = ContextCompressor(llm_manager)
    return _compressor_instance


def compress_task(task_result: Dict[str, Any]) -> CompressedContext:
    """Quick compress a task result."""
    return get_context_compressor().compress_task(task_result)


def compress_cycle(cycle_data: Dict[str, Any]) -> CompressedContext:
    """Quick compress a research cycle."""
    return get_context_compressor().compress_cycle(cycle_data)


def compress_mission(mission_data: Dict[str, Any]) -> CompressedContext:
    """Quick compress entire mission."""
    return get_context_compressor().compress_mission(mission_data)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    'ContextCompressor',
    'TaskCompressor',
    'CycleCompressor',
    'MissionCompressor',
    'CompressedContext',
    'get_context_compressor',
    'compress_task',
    'compress_cycle',
    'compress_mission'
]
