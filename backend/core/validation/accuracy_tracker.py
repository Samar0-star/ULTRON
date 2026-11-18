"""
Accuracy Tracker for Avon-2 Deep Mode
=======================================

Tracks prediction accuracy over time for model calibration.
Provides metrics for evaluating research quality.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

# Storage location
DEFAULT_TRACKER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data", "accuracy"
)


@dataclass
class PredictionRecord:
    """A single prediction record"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    prediction_type: str = ""  # hypothesis_confirmation, model_accuracy, etc.
    predicted_value: Any = None
    actual_value: Optional[Any] = None
    confidence: float = 0.5
    is_correct: Optional[bool] = None
    
    # Context
    session_id: str = ""
    hypothesis_id: str = ""
    
    # Timing
    predicted_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prediction_type": self.prediction_type,
            "predicted_value": str(self.predicted_value),
            "actual_value": str(self.actual_value) if self.actual_value is not None else None,
            "confidence": self.confidence,
            "is_correct": self.is_correct,
            "session_id": self.session_id,
            "hypothesis_id": self.hypothesis_id,
            "predicted_at": self.predicted_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionRecord":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            prediction_type=data.get("prediction_type", ""),
            predicted_value=data.get("predicted_value"),
            actual_value=data.get("actual_value"),
            confidence=data.get("confidence", 0.5),
            is_correct=data.get("is_correct"),
            session_id=data.get("session_id", ""),
            hypothesis_id=data.get("hypothesis_id", ""),
            predicted_at=datetime.fromisoformat(data["predicted_at"]) if "predicted_at" in data else datetime.now(),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None
        )


class AccuracyTracker:
    """
    Track prediction accuracy over time.
    
    Uses for:
    - Hypothesis confirmation rates
    - Model prediction accuracy
    - Research quality metrics
    - Confidence calibration
    
    Example:
        ```python
        tracker = AccuracyTracker()
        
        # Record a prediction
        record = tracker.record_prediction(
            prediction_type="hypothesis_confirmation",
            predicted_value=True,
            confidence=0.8,
            hypothesis_id="hyp_123"
        )
        
        # Later, resolve the prediction
        tracker.resolve(
            record.id,
            actual_value=True,
            is_correct=True
        )
        
        # Get accuracy
        metrics = tracker.get_accuracy_metrics()
        print(f"Overall accuracy: {metrics['overall_accuracy']:.2%}")
        ```
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        auto_persist: bool = True
    ):
        """
        Initialize Accuracy Tracker.
        
        Args:
            storage_dir: Directory for persistent storage
            auto_persist: Auto-save after each operation
        """
        self.storage_dir = storage_dir or DEFAULT_TRACKER_DIR
        self.auto_persist = auto_persist
        
        self._records: Dict[str, PredictionRecord] = {}
        self._lock = Lock()
        
        # Ensure directory exists
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        
        # Load existing records
        self._load()
        
        logger.info(f"AccuracyTracker initialized (loaded {len(self._records)} records)")
    
    def _get_storage_file(self) -> Path:
        """Get path to storage file"""
        return Path(self.storage_dir) / "predictions.json"
    
    def _load(self) -> None:
        """Load records from disk"""
        storage_file = self._get_storage_file()
        if storage_file.exists():
            try:
                with open(storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for record_data in data.get("records", []):
                        record = PredictionRecord.from_dict(record_data)
                        self._records[record.id] = record
            except Exception as e:
                logger.error(f"Error loading records: {e}")
    
    def _save(self) -> None:
        """Persist records to disk"""
        if not self.auto_persist:
            return
        
        storage_file = self._get_storage_file()
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "count": len(self._records),
                "records": [r.to_dict() for r in self._records.values()]
            }
            with open(storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving records: {e}")
    
    def record_prediction(
        self,
        prediction_type: str,
        predicted_value: Any,
        confidence: float = 0.5,
        session_id: str = "",
        hypothesis_id: str = ""
    ) -> PredictionRecord:
        """
        Record a new prediction.
        
        Args:
            prediction_type: Type of prediction
            predicted_value: What was predicted
            confidence: Confidence level (0.0-1.0)
            session_id: Associated session
            hypothesis_id: Associated hypothesis
            
        Returns:
            PredictionRecord
        """
        with self._lock:
            record = PredictionRecord(
                prediction_type=prediction_type,
                predicted_value=predicted_value,
                confidence=confidence,
                session_id=session_id,
                hypothesis_id=hypothesis_id
            )
            self._records[record.id] = record
            self._save()
            
            logger.debug(f"Recorded prediction {record.id}: {prediction_type}")
            return record
    
    def resolve(
        self,
        record_id: str,
        actual_value: Any,
        is_correct: Optional[bool] = None
    ) -> Optional[PredictionRecord]:
        """
        Resolve a prediction with actual outcome.
        
        Args:
            record_id: ID of the prediction
            actual_value: What actually happened
            is_correct: Whether prediction was correct (auto-computed if None)
            
        Returns:
            Updated record or None if not found
        """
        with self._lock:
            if record_id not in self._records:
                return None
            
            record = self._records[record_id]
            record.actual_value = actual_value
            record.resolved_at = datetime.now()
            
            # Auto-compute correctness if not provided
            if is_correct is None:
                record.is_correct = self._compute_correctness(
                    record.predicted_value,
                    actual_value
                )
            else:
                record.is_correct = is_correct
            
            self._save()
            
            logger.debug(
                f"Resolved prediction {record_id}: "
                f"{'correct' if record.is_correct else 'incorrect'}"
            )
            return record
    
    def _compute_correctness(self, predicted: Any, actual: Any) -> bool:
        """Compute if prediction was correct"""
        # Handle different types
        if isinstance(predicted, bool) and isinstance(actual, bool):
            return predicted == actual
        
        if isinstance(predicted, (int, float)) and isinstance(actual, (int, float)):
            # Allow 10% tolerance for numeric predictions
            if actual == 0:
                return abs(predicted) < 0.1
            return abs(predicted - actual) / abs(actual) < 0.1
        
        # String comparison
        return str(predicted).lower() == str(actual).lower()
    
    def get_accuracy_metrics(
        self,
        prediction_type: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get accuracy metrics.
        
        Args:
            prediction_type: Filter by type
            session_id: Filter by session
            
        Returns:
            Dict with accuracy metrics
        """
        records = list(self._records.values())
        
        # Apply filters
        if prediction_type:
            records = [r for r in records if r.prediction_type == prediction_type]
        if session_id:
            records = [r for r in records if r.session_id == session_id]
        
        # Resolved records only
        resolved = [r for r in records if r.is_correct is not None]
        correct = [r for r in resolved if r.is_correct]
        
        if not resolved:
            return {
                "overall_accuracy": None,
                "total_predictions": len(records),
                "resolved_predictions": 0,
                "pending_predictions": len(records),
                "message": "No resolved predictions yet"
            }
        
        accuracy = len(correct) / len(resolved)
        
        # Confidence calibration (average confidence for correct vs incorrect)
        correct_confidence = sum(r.confidence for r in correct) / len(correct) if correct else 0
        incorrect = [r for r in resolved if not r.is_correct]
        incorrect_confidence = sum(r.confidence for r in incorrect) / len(incorrect) if incorrect else 0
        
        return {
            "overall_accuracy": accuracy,
            "total_predictions": len(records),
            "resolved_predictions": len(resolved),
            "pending_predictions": len(records) - len(resolved),
            "correct_predictions": len(correct),
            "incorrect_predictions": len(incorrect),
            "average_confidence": sum(r.confidence for r in resolved) / len(resolved),
            "calibration": {
                "correct_avg_confidence": correct_confidence,
                "incorrect_avg_confidence": incorrect_confidence,
                "overconfidence": (sum(r.confidence for r in resolved) / len(resolved)) - accuracy,
                "brier_score": sum((r.confidence - (1.0 if r.is_correct else 0.0)) ** 2 for r in resolved) / len(resolved)
            }
        }
    
    def get_by_type(self, prediction_type: str) -> List[PredictionRecord]:
        """Get all records of a specific type"""
        return [r for r in self._records.values() if r.prediction_type == prediction_type]
    
    def get_pending(self) -> List[PredictionRecord]:
        """Get unresolved predictions"""
        return [r for r in self._records.values() if r.is_correct is None]
    
    def self_heal_code(self, code: str, error_msg: str, llm_manager: Any = None) -> str:
        """
        [GODZILLA UPGRADE] Autonomously refactor broken code.
        If no LLM provided, attempts heuristic fixes (e.g. closing parentheses).
        """
        logger.warning(f" [HEAL] Attempting autonomous repair for: {error_msg[:100]}...")
        
        # 1. Tokenize-safe Unmatched Delimiter Closer (ignores comments and string literals)
        if "unexpected EOF" in error_msg or "was never closed" in error_msg:
            import io, tokenize
            stack = []
            pairs = {'(': ')', '[': ']', '{': '}'}
            closing = {')': '(', ']': '[', '}': '{'}
            try:
                for tok in tokenize.generate_tokens(io.StringIO(code).readline):
                    if tok.type == tokenize.OP:
                        if tok.string in pairs:
                            stack.append(pairs[tok.string])
                        elif tok.string in closing and stack and stack[-1] == tok.string:
                            stack.pop()
            except tokenize.TokenError:
                pass
            if stack:
                suffix = "".join(reversed(stack))
                code += suffix
                logger.info(f" [HEAL] Token-safely closed {len(stack)} delimiters: {suffix}")
        
        # 2. Neural Repair (if LLM available)
        if llm_manager:
            try:
                prompt = f"You are a PRINCIPAL ENGINEER. Fix this Syntax Error.\nERROR: {error_msg}\nCODE:\n{code}\nReturn ONLY the fixed code block."
                res = llm_manager.run(prompt)
                fixed = res.get("text", code) if isinstance(res, dict) else str(res)
                if "```python" in fixed:
                    fixed = fixed.split("```python")[1].split("```")[0].strip()
                return fixed
            except Exception as e:
                logger.error(f" [HEAL] Neural repair failed: {e}")
        
        return code

    def export(self) -> Dict[str, Any]:
        """Export all data"""
        return {
            "exported_at": datetime.now().isoformat(),
            "metrics": self.get_accuracy_metrics(),
            "records": [r.to_dict() for r in self._records.values()]
        }


# Global instance
_global_tracker: Optional[AccuracyTracker] = None


def get_accuracy_tracker() -> AccuracyTracker:
    """Get or create global accuracy tracker"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = AccuracyTracker()
    return _global_tracker
