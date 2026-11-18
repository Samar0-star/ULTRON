# backend/memory/result_store.py
"""
Aetherix Avon-1  Result Store (Godzilla Edition)

Persistence layer for CentralRouter & ToolRegistry.
Supports:
- InMemoryResultStore (default, dev/test)
- RedisResultStore (distributed, scale)
- SQLiteResultStore (persistent, fallback)
"""

import os
import json
import time
import sqlite3
import threading
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("result_store")
logger.addHandler(logging.NullHandler())

try:
    from backend.utils.redis_lock import DistributedLock
except Exception:
    from contextlib import contextmanager
    @contextmanager
    def DistributedLock(name: str, timeout: int = 10, **kwargs):
        yield


# Try Redis
try:
    import redis
    HAVE_REDIS = True
except Exception:
    HAVE_REDIS = False


# ----------------------------
# Base class
# ----------------------------
class BaseResultStore:
    def save(self, key: str, value: Any): ...
    def append(self, key: str, value: Any): ...
    def get(self, key: str) -> Optional[Any]: ...
    def list_keys(self, prefix: Optional[str] = None) -> List[str]: ...
    def increment(self, key: str, delta: int = 1) -> int: ...


# ----------------------------
# In-memory store
# ----------------------------
class InMemoryResultStore(BaseResultStore):
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def save(self, key: str, value: Any):
        with self._lock:
            self._store[key] = value
        logger.debug(f"[InMemory] Saved key={key}")

    def append(self, key: str, value: Any):
        with self._lock:
            if key not in self._store:
                self._store[key] = []
            if not isinstance(self._store[key], list):
                self._store[key] = [self._store[key]]
            self._store[key].append(value)
        logger.debug(f"[InMemory] Appended key={key}")

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._store.get(key)

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        with self._lock:
            keys = list(self._store.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    def increment(self, key: str, delta: int = 1) -> int:
        with self._lock:
            cur = self._store.get(key)
            val = 0
            try:
                if isinstance(cur, (int, float)):
                    val = int(cur)
                elif isinstance(cur, dict) and "value" in cur:
                    v = cur.get("value")
                    val = int(v) if isinstance(v, (int, float)) else 0
                elif cur is not None:
                    val = int(cur)
            except Exception:
                val = 0
            new_val = val + delta
            self._store[key] = new_val
            return new_val


# ----------------------------
# Redis store (with connection pooling)
# ----------------------------
class RedisResultStore(BaseResultStore):
    def __init__(self, url: str = "redis://localhost:6379/0"):
        if not HAVE_REDIS:
            raise RuntimeError("Redis not installed")

        #  PERFORMANCE: Connection pooling configuration
        max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))

        # Create connection pool
        pool = redis.ConnectionPool.from_url(
            url,
            decode_responses=True,
            max_connections=max_connections,
            socket_connect_timeout=2,
            socket_timeout=2,
            socket_keepalive=True,
            health_check_interval=30,  # Check connection health every 30s
        )

        # Create client with connection pool
        self.client = redis.Redis(connection_pool=pool)

        # Verify connectivity
        try:
            self.client.ping()
            logger.info(f"Redis connected with connection pool (max_connections={max_connections})")
        except Exception as e:
            raise RuntimeError(f"Redis connection failed: {e}")


    def save(self, key: str, value: Any):
        self.client.set(key, json.dumps(value))
        logger.debug(f"[Redis] Saved key={key}")

    def append(self, key: str, value: Any):
        self.client.rpush(key, json.dumps(value))
        logger.debug(f"[Redis] Appended key={key}")

    def get(self, key: str) -> Optional[Any]:
        raw = self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        if prefix:
            return self.client.keys(f"{prefix}*")
        return self.client.keys("*")

    def increment(self, key: str, delta: int = 1) -> int:
        # Use distributed lock to prevent race conditions during read-modify-write
        # Note: Redis INCRBY is atomic, but we are storing JSON blobs, so we need the lock.
        # If we just stored raw ints, we could use self.client.incrby(key, delta).
        # But we support "value" dicts.
        
        lock_key = f"result_store:{key}"
        with DistributedLock(lock_key, timeout=5):
            try:
                raw = self.client.get(key)
                cur = 0
                if raw is not None:
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict) and "value" in parsed:
                            v = parsed.get("value")
                            cur = int(v) if isinstance(v, (int, float)) else 0
                        elif isinstance(parsed, (int, float)):
                            cur = int(parsed)
                        else:
                            cur = int(parsed)
                    except Exception:
                        try:
                            cur = int(raw)
                        except Exception:
                            cur = 0
                new_val = cur + delta
                self.client.set(key, json.dumps(new_val))
                return new_val
            except Exception:
                # best-effort
                return delta


# ----------------------------
# SQLite store
# ----------------------------
class SQLiteResultStore(BaseResultStore):
    def __init__(self, db_path: str = "data/result_store.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")

    def _resolve_key(self, key: str) -> str:
        mission_id = os.getenv("ULTRON_SESSION_ID") or os.getenv("ULTRON_MISSION_ID")
        if mission_id and not key.startswith(f"{mission_id}:") and not key.startswith("global:"):
            return f"{mission_id}:{key}"
        return key

    def save(self, key: str, value: Any):
        resolved_key = self._resolve_key(key)
        with self._lock, self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                (resolved_key, json.dumps(value)),
            )
        logger.debug(f"[SQLite] Saved key={resolved_key}")

    def append(self, key: str, value: Any):
        resolved_key = self._resolve_key(key)
        with self._lock, self.conn:
            cur = self.conn.execute("SELECT value FROM kv WHERE key=? OR key=?", (resolved_key, key))
            row = cur.fetchone()
            arr = []
            if row:
                try:
                    arr = json.loads(row[0])
                except Exception:
                    arr = [row[0]]
            if not isinstance(arr, list):
                arr = [arr]
            arr.append(value)
            self.conn.execute(
                "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                (resolved_key, json.dumps(arr)),
            )
        logger.debug(f"[SQLite] Appended key={resolved_key}")

    def get(self, key: str) -> Optional[Any]:
        resolved_key = self._resolve_key(key)
        with self._lock:
            cur = self.conn.execute("SELECT value FROM kv WHERE key=? OR key=?", (resolved_key, key))
            row = cur.fetchone()
            if not row:
                return None
            try:
                return json.loads(row[0])
            except Exception:
                return row[0]

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        with self._lock:
            if prefix:
                resolved_prefix = self._resolve_key(prefix)
                cur = self.conn.execute(
                    "SELECT key FROM kv WHERE key LIKE ? OR key LIKE ?",
                    (f"{resolved_prefix}%", f"{prefix}%"),
                )
            else:
                cur = self.conn.execute("SELECT key FROM kv")
            return [row[0] for row in cur.fetchall()]

    def increment(self, key: str, delta: int = 1) -> int:
        resolved_key = self._resolve_key(key)
        with self._lock, self.conn:
            cur = self.conn.execute("SELECT value FROM kv WHERE key=? OR key=?", (resolved_key, key))
            row = cur.fetchone()
            base = 0
            if row:
                try:
                    parsed = json.loads(row[0])
                    if isinstance(parsed, dict) and "value" in parsed:
                        v = parsed.get("value")
                        base = int(v) if isinstance(v, (int, float)) else 0
                    elif isinstance(parsed, (int, float)):
                        base = int(parsed)
                    else:
                        base = int(parsed)
                except Exception:
                    try:
                        base = int(row[0])
                    except Exception:
                        base = 0
            new_val = base + delta
            self.conn.execute(
                "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                (resolved_key, json.dumps(new_val)),
            )
            return new_val


# ----------------------------
# Factory
# ----------------------------
def get_result_store() -> BaseResultStore:
    """
    Factory: prefer Redis -> SQLite -> InMemory
    """
    # Redis first
    if HAVE_REDIS:
        try:
            store = RedisResultStore()
            store.save("health:startup", {"ts": time.time()})
            logger.info("Using RedisResultStore")
            return store
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")

    # SQLite fallback
    try:
        store = SQLiteResultStore()
        store.save("health:startup", {"ts": time.time()})
        logger.info("Using SQLiteResultStore")
        return store
    except Exception as e:
        logger.warning(f"SQLite unavailable: {e}")

    # InMemory last
    store = InMemoryResultStore()
    store.save("health:startup", {"ts": time.time()})
    logger.info("Using InMemoryResultStore")
    return store
