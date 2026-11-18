
import threading
import logging
import os
import psutil

logger = logging.getLogger("avon.capacity")

class CapacityManager:
    """
    Manages global system capacity and concurrency limits.
    Prevents system overload during massive parallel research runs.
    """
    def __init__(self, max_concurrent_runs: int = 50):
        self.max_concurrent_runs = max_concurrent_runs
        self._active_runs = set()
        self._lock = threading.Lock()
        
        # FIXED: Godzilla Scale Visibility
        logger.info(f" CapacityManager initialized at GODZILLA SCALE ({max_concurrent_runs} max concurrent runs)")
        
    def start_run(self, session_id: str) -> bool:
        """
        Attempt to register a new run.
        Returns True if capacity allows, False otherwise.
        """
        with self._lock:
            if len(self._active_runs) >= self.max_concurrent_runs:
                logger.warning(f" CAPACITY DEPLETED: {len(self._active_runs)}/{self.max_concurrent_runs} active. Throttling {session_id}.")
                return False
            self._active_runs.add(session_id)
            self._log_system_health()
            logger.info(f" [CAPACITY] Registered run {session_id}. Load: {len(self._active_runs)}/{self.max_concurrent_runs}")
            return True
            
    def end_run(self, session_id: str):
        """Deregister a run."""
        with self._lock:
            if session_id in self._active_runs:
                self._active_runs.remove(session_id)
                logger.info(f" [CAPACITY] Deregistered run {session_id}. Load: {len(self._active_runs)}/{self.max_concurrent_runs}")
            
    def get_active_count(self) -> int:
        return len(self._active_runs)

    def _log_system_health(self):
        """
        FIXED: Heartbeat log for resource monitoring.
        """
        try:
            mem = psutil.virtual_memory()
            threads = threading.active_count()
            logger.info(f" [HEARTBEAT] System Health - MEM: {mem.percent}% | Threads: {threads} | PIDs: {len(psutil.pids())}")
        except Exception:
            pass

# Global singleton
capacity_manager = CapacityManager(max_concurrent_runs=50) # Godzilla Scale
