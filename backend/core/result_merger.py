"""
Result Merger - Multi-Agent Output Reconciliation
==================================================

Combines outputs from multiple agents into coherent, synthesized results.

Strategies:
- Concatenation: Simple append for diverse info
- Voting: Majority selection for classification
- Synthesis: LLM-powered narrative merging (Nature/Science Standard)
- Structured: Deep JSON object reconciliation
"""

import logging
import json
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict


# from backend.llm_manager import get_llm_manager, get_model (Moved to local imports to avoid circular dependency)

logger = logging.getLogger(__name__)

@dataclass
class MergeResult:
    """Consolidated result of multiple agent outputs."""
    text: str
    confidence: float
    sources: List[str]
    strategy_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)


class ResultMerger:
    """
    Synthesizes multiple agent responses into a single 'World Truth'.
    """

    def __init__(self, llm_manager=None):
        if llm_manager is None:
            from backend.llm_manager import get_llm_manager
            self.llm_manager = get_llm_manager()
        else:
            self.llm_manager = llm_manager
            
        self._stats = {
            "merges_performed": 0,
            "strategy_usage": Counter(),
            "conflicts_resolved": 0
        }

    async def merge(
        self,
        results: List[Dict[str, Any]],
        strategy: str = "auto",
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MergeResult:
        """
        Merge multiple agent results.

        Args:
            results: List of agent results, each with:
                - text: Output text
                - confidence: Confidence score (0-1)
                - agent: Source agent name
                - metadata: Optional additional data
            strategy: Merge strategy:
                - "auto": Automatically select best strategy
                - "concat": Simple concatenation
                - "vote": Majority voting
                - "synthesis": LLM-powered merge
                - "structured": JSON reconciliation
            query: Original query (for synthesis)
            context: Optional context

        Returns:
            MergeResult with merged output
        """
        if not results:
            return MergeResult(
                text="No results to merge",
                confidence=0.0,
                sources=[],
                strategy_used="none"
            )

        # [RIGOR GATE] FLAW 19 FIX: Prune software errors and tracebacks
        valid_results = []
        for r in results:
            if not isinstance(r, dict):
                continue
            text = (
                r.get("text")
                or r.get("summary")
                or r.get("research_summary")
                or (r.get("result", {}).get("text") if isinstance(r.get("result"), dict) else None)
                or (r.get("result", {}).get("summary") if isinstance(r.get("result"), dict) else None)
                or ""
            )
            if self._is_scientifically_valid(text):
                r_norm = dict(r)
                r_norm["text"] = text
                valid_results.append(r_norm)
            else:
                logger.warning(f" [RIGOR] Pruned result from {r.get('agent', 'unknown')} due to software error content.")
        
        results = valid_results

        if not results:
            return MergeResult(
                text="All agent outputs were rejected due to software errors. No scientific synthesis possible.",
                confidence=0.0,
                sources=[],
                strategy_used="rigor_gate_failure"
            )

        if len(results) == 1:
            # Single result, no merging needed
            r = results[0]
            return MergeResult(
                text=r.get("text", ""),
                confidence=r.get("confidence", 1.0),
                sources=[r.get("agent", "unknown")],
                strategy_used="single",
                metadata=r.get("metadata", {})
            )

        # Update stats
        self._stats["merges_performed"] += 1
        
        # Selection logic
        if strategy == "auto":
            strategy = self._select_strategy(results)
        
        self._stats["strategy_usage"][strategy] += 1

        # Execute strategy
        if strategy == "concat":
            return self._merge_concat(results)
        elif strategy == "vote":
            return self._merge_vote(results)
        elif strategy == "synthesis":
            return await self._merge_synthesis(results, query, context)
        elif strategy == "structured":
            return self._merge_structured(results)
        else:
            return self._merge_concat(results)

    def _select_strategy(self, results: List[Dict[str, Any]]) -> str:
        """Heuristically select the best merge strategy."""
        
        # If all results are small non-empty classification labels -> vote
        if all(0 < len(str(r.get("text", "")).strip()) < 50 for r in results):
            return "vote"
            
        # If results contain complex JSON -> structured
        if any(self._is_json(r.get("text", "")) for r in results):
            return "structured"
            
        # If long form research -> synthesis
        return "synthesis"

    def _merge_concat(self, results: List[Dict[str, Any]]) -> MergeResult:
        """Simple concatenation of results."""
        text_blocks = []
        sources = []
        total_conf = 0.0

        for r in results:
            agent = r.get("agent", "unknown")
            text = r.get("text", "")
            conf = r.get("confidence", 1.0)
            
            text_blocks.append(f"### Report from {agent}\n{text}")
            sources.append(agent)
            total_conf += conf

        return MergeResult(
            text="\n\n".join(text_blocks),
            confidence=total_conf / len(results),
            sources=sources,
            strategy_used="concat"
        )

    def _merge_vote(self, results: List[Dict[str, Any]]) -> MergeResult:
        """Majority voting for classification tasks."""
        votes = Counter()
        conf_map = {}
        sources_map = defaultdict(list)

        for r in results:
            val = str(r.get("text", "")).strip().lower()
            agent = r.get("agent", "unknown")
            conf = r.get("confidence", 1.0)
            
            votes[val] += 1
            conf_map[val] = max(conf_map.get(val, 0), conf)
            sources_map[val].append(agent)

        winner, count = votes.most_common(1)[0]
        
        return MergeResult(
            text=winner,
            confidence=conf_map[winner] * (count / len(results)),
            sources=sources_map[winner],
            strategy_used="vote"
        )

    async def _merge_synthesis(
        self,
        results: List[Dict[str, Any]],
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MergeResult:
        """LLM-powered narrative synthesis."""
        
        if not self.llm_manager:
            return self._merge_concat(results)

        # Prepare evidence blocks
        evidence = []
        for r in results:
            evidence.append(f"SOURCE: {r.get('agent', 'unknown')}\nCONFIDENCE: {r.get('confidence', 1.0)}\nCONTENT: {r.get('text')}\n---")

        prompt = f"""You are a Lead Research Scientist.
Synthesize the following agent reports into a single, high-fidelity scientific consensus.

GOAL: {query or "Synthesize recent findings"}
CONTEXT: {json.dumps(context or {}, default=str)}

REPORTS:
{chr(10).join(evidence)}

INSTRUCTIONS:
1. Preserve all hard numerical data and statistical markers (p-values, etc.).
2. If agents DISAGREE, state the contradiction explicitly. Do not smooth over conflicts.
3. Write in a formal, high-prestige academic tone (Nature/Science style).
4. Use Markdown for structure.

OUTPUT:
Provide the synthesized text followed by a 'Consensus Verdict' (Supported/Refuted/Inconclusive).
"""
        try:
            # Use high-tier model for synthesis
            from backend.llm_manager import get_model
            model = get_model("deep_synthesis")
            response = await self.llm_manager.run_async(prompt, model=model)
            text = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # Detect conflicts from text
            conflicts = self._detect_conflicts_from_synthesis(text, results)
            if conflicts:
                self._stats["conflicts_resolved"] += 1

            return MergeResult(
                text=text,
                confidence=sum(r.get("confidence", 1.0) for r in results) / len(results),
                sources=[r.get("agent", "unknown") for r in results],
                strategy_used="synthesis",
                conflicts=conflicts
            )
        except Exception as e:
            logger.error(f" Synthesis merge failed: {e}")
            return self._merge_concat(results)

    def _merge_structured(self, results: List[Dict[str, Any]]) -> MergeResult:
        """Deep JSON reconciliation."""
        # Simple implementation: take the one with highest confidence that is valid JSON
        valid_json_results = []
        for r in results:
            if self._is_json(r.get("text", "")):
                valid_json_results.append(r)
        
        if not valid_json_results:
            return self._merge_concat(results)
            
        # Pick winner by confidence
        winner = max(valid_json_results, key=lambda x: x.get("confidence", 0.0))
        
        return MergeResult(
            text=winner.get("text", ""),
            confidence=winner.get("confidence", 1.0),
            sources=[winner.get("agent", "unknown")],
            strategy_used="structured"
        )

    def _detect_conflicts_from_synthesis(
        self,
        synthesized_text: str,
        original_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect conflicts mentioned in synthesized text"""

        conflict_keywords = [
            "however", "but", "although", "while", "whereas",
            "conflict", "disagree", "contradiction", "discrepancy"
        ]

        text_lower = synthesized_text.lower()

        if any(kw in text_lower for kw in conflict_keywords):
            # Potential conflict mentioned
            return [{
                "type": "mentioned_in_synthesis",
                "indicators": [kw for kw in conflict_keywords if kw in text_lower],
                "sources": [r.get("agent", "unknown") for r in original_results]
            }]

        return []

    def _is_scientifically_valid(self, text: str) -> bool:
        """[RIGOR] FLAW 19 FIX: Detect software errors or tracebacks"""
        if not isinstance(text, str):
            text = str(text)
            
        error_indicators = [
            "Traceback (most recent call last):",
            "AttributeError:",
            "TypeError:",
            "ValueError:",
            "SyntaxError:",
            "ImportError:",
            "JSONDecodeError:",
            "CRITICAL SECURITY ERROR",
            "Security Violation",
            "Network access disabled",
            "RetryError",
            "Exception:",
            "Internal Server Error",
            "HTTP 429",
            "Rate limit exceeded"
        ]
        
        text_lower = text.lower()
        for indicator in error_indicators:
            if indicator.lower() in text_lower:
                # Special case: if it mentions 'Exception' but also 'p_value', it might be a valid scientific discussion of an outlier
                if "exception" in indicator.lower() and "p_value" in text_lower:
                    continue
                return False
        return True

    def _is_json(self, text: str) -> bool:
        """Check if text is valid JSON"""
        try:
            json.loads(text.strip())
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get merger statistics"""
        return {
            "merges_performed": self._stats["merges_performed"],
            "strategy_usage": dict(self._stats["strategy_usage"]),
            "conflicts_resolved": self._stats["conflicts_resolved"]
        }

    def reset_stats(self):
        """Reset statistics"""
        self._stats = {
            "merges_performed": 0,
            "strategy_usage": Counter(),
            "conflicts_resolved": 0
        }
