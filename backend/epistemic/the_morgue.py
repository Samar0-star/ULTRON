"""
The Morgue: Graveyard of Refuted Hypotheses
===========================================
Part of ULTRON Epistemic Governance & Red-Team Verification.

"Those who cannot remember the dead are condemned to repeat their experiments."

When a scientific hypothesis is killed by the Deterministic Verification Cage or
the Adversarial Red-Team Swarm, its full autopsy is permanently entombed in The Morgue.
Before generating new research plans, the discovery engine queries The Morgue to ensure
that swarms never cyclically propose already-refuted mechanisms.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("epistemic.the_morgue")


class KillGate(str, Enum):
    VALENCE_STOICHIOMETRY = "valence_stoichiometry"
    THERMODYNAMIC_HULL    = "thermodynamic_convex_hull"
    REALITY_CONSTRAINT    = "reality_constraint"
    ADVERSARIAL_RED_TEAM  = "adversarial_red_team"
    PERMUTATION_NOISE     = "permutation_noise_decay"
    STATISTICAL_NULL      = "statistical_null"
    MANUFACTURABILITY     = "manufacturability_limit"


@dataclass
class MorgueRecord:
    """Tombstone record for a permanently refuted hypothesis."""
    hypothesis_id: str
    statement: str
    domain: str
    kill_gate: KillGate
    kill_reason: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    evidence: Dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            raw = f"{self.domain}:{self.statement.strip().lower()}"
            self.fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kill_gate"] = self.kill_gate.value
        return d


class TheMorgue:
    """
    Persistent graveyard and autopsy archive for eliminated hypotheses.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else None
        self._graveyard: Dict[str, MorgueRecord] = {}

    def bury(
        self,
        hypothesis_id: str,
        statement: str,
        domain: str,
        kill_gate: KillGate,
        kill_reason: str,
        evidence: Optional[Dict[str, Any]] = None
    ) -> MorgueRecord:
        """Entomb a refuted hypothesis into The Morgue."""
        record = MorgueRecord(
            hypothesis_id=hypothesis_id,
            statement=statement,
            domain=domain,
            kill_gate=kill_gate,
            kill_reason=kill_reason,
            evidence=evidence or {}
        )
        self._graveyard[record.fingerprint] = record
        logger.info(f"⚰️ [THE MORGUE] Entombed dead hypothesis [{record.fingerprint}]: {statement[:60]}... (Killed by {kill_gate.value})")

        if self.storage_path:
            self._persist_record(record)

        return record

    def is_buried(self, statement: str, domain: str = "") -> bool:
        """Check if an exact or near-identical hypothesis has already been buried."""
        raw = f"{domain}:{statement.strip().lower()}"
        fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return fp in self._graveyard

    def query_autopsy(self, candidate_statement: str, token_threshold: float = 0.65) -> List[MorgueRecord]:
        """
        Query The Morgue for semantically similar failed hypotheses to prevent repetition.
        Uses Jaccard n-gram token similarity as a zero-dependency baseline.
        """
        candidate_tokens = set(candidate_statement.lower().split())
        if not candidate_tokens:
            return []

        matches = []
        for record in self._graveyard.values():
            target_tokens = set(record.statement.lower().split())
            intersection = len(candidate_tokens & target_tokens)
            union = len(candidate_tokens | target_tokens)
            similarity = intersection / union if union > 0 else 0.0

            if similarity >= token_threshold:
                matches.append(record)

        return matches

    def graveyard_census(self) -> Dict[str, Any]:
        """Returns mortality statistics across all kill gates."""
        breakdown: Dict[str, int] = {}
        for rec in self._graveyard.values():
            k = rec.kill_gate.value
            breakdown[k] = breakdown.get(k, 0) + 1

        return {
            "total_buried": len(self._graveyard),
            "mortality_by_gate": breakdown
        }

    def _persist_record(self, record: MorgueRecord) -> None:
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            log_file = self.storage_path / "morgue_records.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict()) + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist morgue record to disk: {e}")
