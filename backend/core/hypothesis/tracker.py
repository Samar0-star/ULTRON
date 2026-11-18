"""Hypothesis Tracker for Avon-2 Deep Mode
=========================================

Manages hypothesis lifecycle across research sessions.
Persists hypotheses to disk and provides query capabilities.


"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

from backend.core.hypothesis.models import Hypothesis, HypothesisState

logger = logging.getLogger(__name__)

# Default storage location
DEFAULT_HYPOTHESIS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data", "hypotheses"
)

import re

def is_valid_scientific_hypothesis(statement: Optional[str]) -> bool:
    """Validate that statement represents a legitimate scientific claim rather than pipeline noise."""
    if not statement or not isinstance(statement, str):
        return False
    s = statement.strip()
    if len(s) < 10:
        return False
    if s.startswith(("{", "[", "#", "http://", "https://")):
        return False
    s_low = s.lower()
    toxic = [
        "'error'", '"error"', "no claim", "web search", "traceback",
        "system_rejected", "novelty check", "novelty check: redundant", "status: redundant",
        "finding_task", "finding_exp", "task_", "session_state", "research_session",
        "data-integrity hypothesis", "knowledge-graph mining depth",
        "hypothesis yield", "validated_discoveries_per_week",
        "document: {", "{'name':", '{"name":', "doc_"
    ]
    if any(t in s_low for t in toxic):
        return False
    if re.search(r'\bhypothesis\s+[a-f0-9]{4,}\b', s_low):
        return False
    if re.search(r'#\s+web\s+search', s_low):
        return False
    # Reject trivial generic stop-word interaction hypotheses
    stopwords = {"performance", "protocol", "approach", "method", "system", "time", "framework", "concept", "dataset", "model", "error", "literature_seed", "results"}
    m = re.search(r"interaction between '([^']+)' and '([^']+)'", s_low)
    if m:
        w1, w2 = m.group(1).strip().lower(), m.group(2).strip().lower()
        if w1 in stopwords or w2 in stopwords:
            return False
    return True


class HypothesisTracker:
    """
    Track and manage hypotheses across research sessions.
    
    Provides:
    - Persistent storage (JSON files)
    - Lifecycle state management
    - Query by state, domain, score
    - Session-based tracking
    
    Example:
        ```python
        tracker = HypothesisTracker(session_id="research_2024")
        
        # Add new hypothesis
        hyp = Hypothesis(
            statement="Transformer attention scales O(n)",
            rationale="Memory usage grows quadratically with sequence length"
        )
        tracker.add(hyp)
        
        # Query
        active = tracker.get_by_state(HypothesisState.PROPOSED)
        top = tracker.get_top_priority(n=5)
        ```
    """
    
    def __init__(
        self,
        session_id: str = "default",
        storage_dir: Optional[str] = None
    ):
        """
        Initialize hypothesis tracker.

        Args:
            session_id: Session identifier
            storage_dir: Custom storage root
        """
        self.session_id = session_id
        self.storage_dir = storage_dir or DEFAULT_HYPOTHESIS_DIR

        # In-memory cache
        self._hypotheses: Dict[str, Hypothesis] = {}
        self._lock = Lock()

        # Ensure storage directory exists
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)

        # Load existing hypotheses for this session
        self._load_session()

        status = "Rehydrated" if self._hypotheses else "Initialized"
        logger.info(f" HypothesisTracker {status} (session={session_id}, loaded={len(self._hypotheses)})")
    
    def _get_session_file(self) -> Path:
        """Get path to session's hypothesis file"""
        return Path(self.storage_dir) / f"session_{self.session_id}.json"
    
    def _load_session(self) -> None:
        """Load hypotheses from disk with backup recovery (FIX #11)"""
        session_file = self._get_session_file()
        backup_file = Path(str(session_file) + ".backup")
        
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for hyp_data in data.get("hypotheses", []):
                        hyp = Hypothesis.from_dict(hyp_data)
                        if not is_valid_scientific_hypothesis(hyp.statement):
                            logger.info(f" [PURGE] Stripped invalid/meta hypothesis {hyp.id} during rehydration.")
                            continue
                        self._hypotheses[hyp.id] = hyp
                logger.info(f"Loaded {len(self._hypotheses)} hypotheses from {session_file}")
            except Exception as e:
                logger.error(f"Error loading hypotheses: {e}")
                # FIX #11: Attempt recovery from backup
                if backup_file.exists():
                    try:
                        logger.warning(f"Attempting recovery from backup: {backup_file}")
                        with open(backup_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            for hyp_data in data.get("hypotheses", []):
                                hyp = Hypothesis.from_dict(hyp_data)
                                if not is_valid_scientific_hypothesis(hyp.statement):
                                    continue
                                self._hypotheses[hyp.id] = hyp
                        logger.info(f"RECOVERED {len(self._hypotheses)} hypotheses from backup!")
                    except Exception as e2:
                        logger.error(f"Backup recovery also failed: {e2}")
    
    def _save_session(self) -> None:
        """Persist hypotheses to disk with backup rotation (FIX #11)"""
        session_file = self._get_session_file()
        backup_file = Path(str(session_file) + ".backup")
        
        try:
            # FIX #11: Create backup of existing file before overwriting
            if session_file.exists():
                import shutil
                shutil.copy2(session_file, backup_file)
            
            data = {
                "session_id": self.session_id,
                "updated_at": datetime.now().isoformat(),
                "count": len(self._hypotheses),
                "hypotheses": [h.to_dict() for h in self._hypotheses.values()]
            }
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self._hypotheses)} hypotheses to {session_file}")
        except Exception as e:
            logger.error(f"Error saving hypotheses: {e}")
    
    # ========== CRUD Operations ==========
    
    def add(self, hypothesis: Hypothesis) -> Hypothesis:
        """
        Add a new hypothesis to tracking.
        
        Args:
            hypothesis: Hypothesis to add
            
        Returns:
            The added hypothesis (with ID assigned if not present)
        """
        if not is_valid_scientific_hypothesis(getattr(hypothesis, "statement", None)):
            logger.warning(f" [TRACKER-PURGE] Rejected non-scientific/meta hypothesis {hypothesis.id}: {getattr(hypothesis, 'statement', '')[:80]}")
            return hypothesis

        with self._lock:
            self._hypotheses[hypothesis.id] = hypothesis
            self._save_session()
            logger.info(f"Added hypothesis {hypothesis.id}: {hypothesis.statement[:50]}...")
            return hypothesis
    
    def get(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get hypothesis by ID"""
        return self._hypotheses.get(hypothesis_id)
    
    def update(self, hypothesis: Hypothesis) -> Hypothesis:
        """
        Update an existing hypothesis.
        
        Args:
            hypothesis: Hypothesis with updated fields
            
        Returns:
            Updated hypothesis
        """
        with self._lock:
            hypothesis.updated_at = datetime.now()
            self._hypotheses[hypothesis.id] = hypothesis
            self._save_session()
            return hypothesis
    
    def delete(self, hypothesis_id: str) -> bool:
        """
        Delete a hypothesis.
        
        Args:
            hypothesis_id: ID of hypothesis to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if hypothesis_id in self._hypotheses:
                del self._hypotheses[hypothesis_id]
                self._save_session()
                return True
            return False
    
    # ========== Query Methods ==========
    
    def get_all(self) -> List[Hypothesis]:
        """Get all tracked hypotheses"""
        return list(self._hypotheses.values())
    
    def get_by_state(self, state: HypothesisState) -> List[Hypothesis]:
        """
        Get hypotheses by lifecycle state.
        
        Args:
            state: State to filter by
            
        Returns:
            List of hypotheses in that state
        """
        return [h for h in self._hypotheses.values() if h.state == state]
    
    def get_by_domain(self, domain: str) -> List[Hypothesis]:
        """
        Get hypotheses by domain.
        
        Args:
            domain: Domain to filter by
            
        Returns:
            List of hypotheses in that domain
        """
        return [h for h in self._hypotheses.values() if h.domain == domain]
    
    def get_active(self) -> List[Hypothesis]:
        """Get all non-archived hypotheses"""
        return [
            h for h in self._hypotheses.values() 
            if h.state != HypothesisState.ARCHIVED
        ]
    
    def get_testable(self) -> List[Hypothesis]:
        """Get hypotheses ready for testing"""
        return [
            h for h in self._hypotheses.values()
            if h.state in (HypothesisState.PRIORITIZED, HypothesisState.NOVEL, HypothesisState.PROPOSED)
            and h.testability_score is not None and h.testability_score >= 0.5
        ]
    
    def get_top_priority(self, n: int = 5) -> List[Hypothesis]:
        """
        Get top N hypotheses by priority score.
        
        Args:
            n: Number of top hypotheses to return
            
        Returns:
            List sorted by priority (highest first)
        """
        scored = [h for h in self._hypotheses.values() if h.priority_score is not None]
        scored.sort(key=lambda h: h.priority_score or 0, reverse=True)
        return scored[:n]
    
    def get_unscored(self) -> List[Hypothesis]:
        """Get hypotheses that haven't been scored yet"""
        return [
            h for h in self._hypotheses.values()
            if h.novelty_score is None or h.priority_score is None
        ]
    
    # ========== State Transitions ==========
    
    def transition_state(
        self,
        hypothesis_id: str,
        new_state: HypothesisState,
        reason: Optional[str] = None,
        force: bool = False
    ) -> Optional[Hypothesis]:
        """
        Transition hypothesis to new state.
        
        Args:
            hypothesis_id: ID of hypothesis
            new_state: Target state
            reason: Optional reason for transition
            force: If True, bypass strict lifecycle transition validation
            
        Returns:
            Updated hypothesis or None if not found
        """
        with self._lock:
            hyp = self._hypotheses.get(hypothesis_id)
            if not hyp:
                return None
            
            old_state = hyp.state
            try:
                hyp.update_state(new_state, force=force)
            except ValueError as ve:
                if not force:
                    logger.warning(f"Transition validation failed ({ve}). Applying forced recovery to {new_state.value}.")
                    hyp.update_state(new_state, force=True)
                else:
                    raise
            
            if reason:
                hyp.add_evidence(
                    evidence_type="state_transition",
                    value={"from": old_state.value, "to": new_state.value, "reason": reason},
                    source="tracker"
                )
            
            self._save_session()
            logger.info(f"Hypothesis {hypothesis_id}: {old_state.value}  {new_state.value}")
            return hyp
    
    def mark_confirmed(self, hypothesis_id: str, evidence: Dict[str, Any]) -> Optional[Hypothesis]:
        """Mark hypothesis as confirmed with supporting evidence"""
        hyp = self.get(hypothesis_id)
        if hyp:
            hyp.add_evidence("confirmation", evidence, "experiment")
            return self.transition_state(hypothesis_id, HypothesisState.CONFIRMED, "Evidence supports hypothesis")
        return None
    
    def mark_refuted(self, hypothesis_id: str, evidence: Dict[str, Any]) -> Optional[Hypothesis]:
        """Mark hypothesis as refuted with contradicting evidence"""
        hyp = self.get(hypothesis_id)
        if hyp:
            hyp.add_evidence("refutation", evidence, "experiment")
            return self.transition_state(hypothesis_id, HypothesisState.REFUTED, "Evidence contradicts hypothesis")
        return None
    
    # ========== Utility Methods ==========
    
    def count(self) -> Dict[str, int]:
        """Get count of hypotheses by state"""
        counts = {"total": len(self._hypotheses)}
        for state in HypothesisState:
            counts[state.value] = len([h for h in self._hypotheses.values() if h.state == state])
        return counts
    
    def export_session(self) -> Dict[str, Any]:
        """Export session data for backup/transfer"""
        return {
            "session_id": self.session_id,
            "exported_at": datetime.now().isoformat(),
            "counts": self.count(),
            "hypotheses": [h.to_dict() for h in self._hypotheses.values()]
        }
    
    def clear_session(self) -> int:
        """Clear all hypotheses in current session"""
        with self._lock:
            count = len(self._hypotheses)
            self._hypotheses.clear()
            self._save_session()
            logger.warning(f"Cleared {count} hypotheses from session {self.session_id}")
            return count



# Global registry for session-based tracker reuse
_trackers: Dict[str, HypothesisTracker] = {}
_MAX_TRACKERS = 20  # Cap to prevent memory growth on long-running processes


def get_hypothesis_tracker(session_id: str = "default", **kwargs) -> HypothesisTracker:
    """
    Get or create a HypothesisTracker for this session.
    Caps registry at _MAX_TRACKERS to prevent memory leak.
    Extra kwargs (e.g. mission_id) silently ignored -- single-user system.
    """
    global _trackers

    if session_id not in _trackers:
        # Evict oldest if at cap
        if len(_trackers) >= _MAX_TRACKERS:
            oldest = next(iter(_trackers))
            logger.warning(f"HypothesisTracker registry full ({_MAX_TRACKERS}), evicting session '{oldest}'")
            del _trackers[oldest]

        logger.info(f"Initializing new HypothesisTracker for session '{session_id}'")
        _trackers[session_id] = HypothesisTracker(session_id=session_id)

    return _trackers[session_id]


def release_tracker(session_id: str) -> None:
    """Explicitly free tracker memory when a research session ends."""
    if session_id in _trackers:
        del _trackers[session_id]
        logger.info(f"Released HypothesisTracker for session '{session_id}'")
