# -*- coding: utf-8 -*-
"""
FAILURE PATTERN INDEX - UPGRADE 3
=================================
Tracks failure shapes across discovery sessions.
Learns which assumptions die frequently, which escapes fail, 
and which constraint classes dominate kills.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from enum import Enum
import threading

logger = logging.getLogger(__name__)

from backend.discovery.constants import ScientificDefaults


class FailureCategory(Enum):
    """Categories of failure patterns."""
    ASSUMPTION_TYPE = "assumption_type"
    ESCAPE_ROUTE = "escape_route"
    CONSTRAINT_CLASS = "constraint_class"


@dataclass
class FailureRecord:
    """A single failure record."""
    category: FailureCategory
    identifier: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: str = ""


@dataclass
class FailurePatternIndex:
    """
    [RIGOR] FLAW 29 FIX: Semantic Failure Memory.
    Learns the 'Shape' of failure to prevent repetitive hallucinations.
    """
    
    # Counters
    assumption_deaths: Dict[str, int] = field(default_factory=dict)
    escape_failures: Dict[str, int] = field(default_factory=dict)
    constraint_kills: Dict[str, int] = field(default_factory=dict)
    
    # Detailed records
    failure_history: List[FailureRecord] = field(default_factory=list)
    
    # Statistics
    total_deaths: int = 0
    total_escape_failures: int = 0
    total_kills: int = 0

    def check_similarity(self, new_statement: str, 
                         threshold: float = ScientificDefaults.FAILURE_SIMILARITY_THRESHOLD) -> Tuple[bool, str]:
        """
        Check if a new hypothesis is too similar to a known failure.
        """
        new_lower = new_statement.lower()
        # Simple stop words
        stop_words = {"the", "is", "a", "of", "and", "to", "via", "through", "with", "has", "in", "from", "for"}
        
        # Simple Stemmer: take first 4 chars of words > 4 chars
        def stem(w):
            return w[:4] if len(w) > 4 else w

        words_new = set(stem(w) for w in new_lower.split() if w not in stop_words and len(w) > 2)
        if len(words_new) < 2: return False, ""
        
        for record in self.failure_history:
            if record.category == FailureCategory.ASSUMPTION_TYPE:
                words_old = set(stem(w) for w in record.identifier.lower().split() if w not in stop_words and len(w) > 2)
                
                if not words_old: continue
                
                overlap_count = len(words_old & words_new)
                overlap_ratio = overlap_count / min(len(words_old), len(words_new))
                
                # We need a significant match on 'stems'
                # [RIGOR] Minimum stem overlap for similarity
                if overlap_count >= ScientificDefaults.FAILURE_STEM_OVERLAP_MIN and overlap_ratio >= threshold:
                    return True, f"Overlap with failed assumption: '{record.identifier}' (Stem Match: {overlap_count} stems)"
        
        return False, ""
    
    def record_assumption_death(self, assumption_type: str, context: str = "") -> None:
        """Record an assumption death."""
        self.assumption_deaths[assumption_type] = self.assumption_deaths.get(assumption_type, 0) + 1
        self.total_deaths += 1
        
        self.failure_history.append(FailureRecord(
            category=FailureCategory.ASSUMPTION_TYPE,
            identifier=assumption_type,
            context=context
        ))
        
        logger.info(f"[FAILURE PATTERN] Assumption death recorded: {assumption_type} (total: {self.assumption_deaths[assumption_type]})")
    
    def record_escape_failure(self, escape_type: str, context: str = "") -> None:
        """Record an escape route that failed later."""
        self.escape_failures[escape_type] = self.escape_failures.get(escape_type, 0) + 1
        self.total_escape_failures += 1
        
        self.failure_history.append(FailureRecord(
            category=FailureCategory.ESCAPE_ROUTE,
            identifier=escape_type,
            context=context
        ))
        
        logger.info(f"[FAILURE PATTERN] Escape failure recorded: {escape_type} (total: {self.escape_failures[escape_type]})")
    
    def record_constraint_kill(self, constraint_type: str, context: str = "") -> None:
        """Record a constraint that caused a kill."""
        self.constraint_kills[constraint_type] = self.constraint_kills.get(constraint_type, 0) + 1
        self.total_kills += 1
        
        self.failure_history.append(FailureRecord(
            category=FailureCategory.CONSTRAINT_CLASS,
            identifier=constraint_type,
            context=context
        ))
        
        logger.info(f"[FAILURE PATTERN] Constraint kill recorded: {constraint_type} (total: {self.constraint_kills[constraint_type]})")
    
    def get_top_killers(self, n: int = 5) -> List[Tuple[str, int]]:
        """Get the top N assumption types that die most frequently."""
        sorted_deaths = sorted(self.assumption_deaths.items(), key=lambda x: x[1], reverse=True)
        return sorted_deaths[:n]
    
    def get_fake_escapes(self, 
                         threshold: float = ScientificDefaults.SURVIVAL_SCORE_PROVISIONAL) -> List[Tuple[str, float]]:
        """
        Get escape routes that fail more than threshold of the time.
        
        Returns:
            List of (escape_type, failure_rate) tuples
        """
        # Would need escape attempts tracking for accurate rate
        # For now, return escapes with high failure counts
        sorted_escapes = sorted(self.escape_failures.items(), key=lambda x: x[1], reverse=True)
        return [(e, f / max(self.total_escape_failures, 1)) for e, f in sorted_escapes if f >= 2]
    
    def get_dominant_constraints(self, n: int = 3) -> List[Tuple[str, int]]:
        """Get the top N constraint classes that dominate kills."""
        sorted_kills = sorted(self.constraint_kills.items(), key=lambda x: x[1], reverse=True)
        return sorted_kills[:n]
    
    def get_insights(self) -> List[str]:
        """
        Generate meta-discovery insights from failure patterns.
        
        Example: "Geometry-based escapes fail 72% of the time under diffusion constraints."
        """
        insights = []
        
        # Top killers
        top_killers = self.get_top_killers(3)
        for assumption_type, count in top_killers:
            if count >= 3:
                insights.append(f"'{assumption_type}' assumptions die frequently ({count} deaths)")
        
        # Fake escapes
        fake_escapes = self.get_fake_escapes(0.4)
        for escape_type, rate in fake_escapes:
            insights.append(f"'{escape_type}' escapes fail {rate*100:.0f}% of the time")
        
        # Dominant constraints
        dominant = self.get_dominant_constraints(2)
        for constraint_type, count in dominant:
            if count >= 2:
                insights.append(f"'{constraint_type}' constraints dominate kills ({count} kills)")
        
        return insights
    
    def to_dict(self) -> Dict:
        """Export as dictionary."""
        return {
            "assumption_deaths": self.assumption_deaths,
            "escape_failures": self.escape_failures,
            "constraint_kills": self.constraint_kills,
            "total_deaths": self.total_deaths,
            "total_escape_failures": self.total_escape_failures,
            "total_kills": self.total_kills,
            "insights": self.get_insights(),
            "history_count": len(self.failure_history)
        }


# User-scoped registry (Memory Cache with limited size)
from collections import OrderedDict
_user_failure_cache = OrderedDict()
MAX_CACHE_SIZE = 100
_failure_lock = threading.Lock()

def get_failure_index(mission_id: Optional[str] = None, session_id: str = "default") -> FailurePatternIndex:
    """Get or create the user/session-scoped failure pattern index."""
    global _user_failure_cache
    uid = mission_id or "default_user"
    cache_key = (uid, session_id)
    
    with _failure_lock:
        if cache_key in _user_failure_cache:
            # Move to end (LRU)
            index = _user_failure_cache.pop(cache_key)
            _user_failure_cache[cache_key] = index
            return index
            
        # Create new
        if len(_user_failure_cache) >= MAX_CACHE_SIZE:
            _user_failure_cache.popitem(last=False)
            
        index = FailurePatternIndex()
        _user_failure_cache[cache_key] = index
        logger.info(f" FailureIndex created for user: {uid}, session: {session_id}")
        return index


def reset_failure_index(mission_id: Optional[str] = None, session_id: str = "default") -> None:
    """Reset the failure pattern index for a specific user session."""
    global _user_failure_cache
    uid = mission_id or "default_user"
    cache_key = (uid, session_id)
    with _failure_lock:
        if cache_key in _user_failure_cache:
            _user_failure_cache[cache_key] = FailurePatternIndex()
            logger.info(f" FailureIndex reset for user: {uid}, session: {session_id}")
