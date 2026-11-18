import logging
import time
import threading
from typing import Tuple, Dict

logger = logging.getLogger("avon.capacity.memory")

class MemoryTokenBucket:
    """
    In-Memory implementation of Token Bucket for Dev/Test environments where Redis is unavailable.
    NOT FOR PRODUCTION SCALING - Does not share state across processes.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        # Storage: key -> {tokens: float, last_refill: float}
        self._keys: Dict[str, Dict] = {}
        # Concurrency: key -> int
        self._concurrency: Dict[str, int] = {}
        
    def acquire(self, key_base: str, cost: int, rpm: int, tpm: int, concurrency: int) -> Tuple[bool, str]:
        with self._lock:
            now = time.time()
            
            # 1. Check Concurrency
            conc_key = f"{key_base}:conc"
            current_conc = self._concurrency.get(conc_key, 0)
            if current_conc >= concurrency:
                return False, f"concurrency_limit ({current_conc}/{concurrency})"
            
            # 2. Check RPM (Simple Minute Window) & prune stale minute buckets
            current_min = int(now / 60)
            stale_keys = [k for k in self._keys if not k.endswith(f":{current_min}")]
            for sk in stale_keys:
                self._keys.pop(sk, None)

            rpm_key = f"{key_base}:rpm:{current_min}"
            current_rpm = self._keys.get(rpm_key, {}).get("count", 0)
            if current_rpm >= rpm:
                return False, f"rpm_limit ({current_rpm}/{rpm})"
                
            # 3. Check TPM (Simple Minute Window)
            tpm_key = f"{key_base}:tpm:{current_min}"
            current_tpm = self._keys.get(tpm_key, {}).get("count", 0)
            if current_tpm + cost > tpm:
                return False, f"tpm_limit ({current_tpm}/{tpm})"
            
            # Update State
            self._concurrency[conc_key] = current_conc + 1
            
            # Update RPM
            if rpm_key not in self._keys: self._keys[rpm_key] = {"count": 0}
            self._keys[rpm_key]["count"] += 1
            
            # Update TPM
            if tpm_key not in self._keys: self._keys[tpm_key] = {"count": 0}
            self._keys[tpm_key]["count"] += cost
            
            return True, "ok"

    def release(self, key_base: str):
        with self._lock:
            conc_key = f"{key_base}:conc"
            if conc_key in self._concurrency:
                self._concurrency[conc_key] = max(0, self._concurrency[conc_key] - 1)
