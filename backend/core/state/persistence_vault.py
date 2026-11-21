import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger("persistence_vault")

class PersistenceVault:
    def __init__(self, base_path: str = "data/research_vault"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _sanitize_path(self, identifier: str) -> str:
        """Sanitize identifiers to prevent path traversal."""
        return re.sub(r"[^a-zA-Z0-9_\-]", "_", identifier)

    def log_action(self, session_id: str, source: str, action_type: str, payload: Dict[str, Any]):
        """Log an event or action to the session history."""
        s_id = self._sanitize_path(session_id)
        
        log_dir = self.base_path / "missions" / s_id / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "action_log.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "type": action_type,
            "payload": payload
        }
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to log action for session {session_id}: {e}")

    def register_session(self, session_id: str, metadata: Dict[str, Any]):
        s_id = self._sanitize_path(session_id)
        
        session_path = self.base_path / "missions" / s_id
        session_path.mkdir(parents=True, exist_ok=True)
        try:
            with open(session_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to register session {session_id}: {e}")

    def save_checkpoint(self, session_id: str, cycle: int, state: Dict[str, Any]):
        """
        [TITAN V211.0] HARDENED PERSISTENCE (ATOMIC UPGRADE)
        Physically abolished dangerous pickle serialization.
        All checkpoints are now saved using an atomic write-rename pattern to prevent corruption.
        """
        import os
        s_id = self._sanitize_path(session_id)
        
        checkpoint_dir = self.base_path / "missions" / s_id / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_path = checkpoint_dir / f"cycle_{cycle}.json"
        checkpoint_tmp = checkpoint_dir / f"cycle_{cycle}.json.tmp"
        latest_path = checkpoint_dir / "latest.json"
        latest_tmp = checkpoint_dir / "latest.json.tmp"
        
        try:
            # [SVEL BEAST FIX] Atomic Write Pattern
            # 1. Write to specific cycle .tmp
            with open(checkpoint_tmp, "w") as f:
                json.dump(state, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(checkpoint_tmp, checkpoint_path)
            
            # 2. Write to latest .tmp
            with open(latest_tmp, "w") as f:
                json.dump(state, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(latest_tmp, latest_path)
                
            logger.info(f"Saved ATOMIC JSON checkpoint for session {session_id}, cycle {cycle}")
        except Exception as e:
            logger.error(f"Failed to save atomic checkpoint for session {session_id}: {e}")

    def get_latest_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        s_id = self._sanitize_path(session_id)
        
        latest_path = self.base_path / "missions" / s_id / "checkpoints" / "latest.json"
        
        # Backward compatibility check for legacy pickle files during transition
        legacy_path = self.base_path / "missions" / s_id / "checkpoints" / "latest.pkl"
        
        if latest_path.exists():
            try:
                with open(latest_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load JSON checkpoint for session {session_id}: {e}")
                return None
        elif legacy_path.exists():
            logger.warning(f" [SECURITY] Detected legacy pickle checkpoint for session {session_id}. Handover will require migration to JSON.")
            # We explicitly do NOT load pickle files in production mode anymore.
            # return pickle.load(f) # REMOVED FOR SECURITY
            return None
            
        return None

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        # Search for session_id in user subdirectories
        if not self.base_path.exists():
            return None
        for user_dir in self.base_path.iterdir():
            if user_dir.is_dir():
                s_id = self._sanitize_path(session_id)
                session_path = user_dir / s_id
                metadata_path = session_path / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, "r") as f:
                            return json.load(f)
                    except Exception:
                        continue
        return None

vault = PersistenceVault()
