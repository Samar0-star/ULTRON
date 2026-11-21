# backend/memory/provenance_db.py
"""
SVEL Provenance Database - Isolated Compute Edition
=====================================================
Tracks full execution provenance for a single mission run.
SQLite-based for absolute portability and isolation.
"""

import os
import json
import sqlite3
import threading
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("svel.provenance_db")

# In isolated mission mode, the DB path is aligned with the session
PROVENANCE_DIR = Path("data/provenance")

class ProvenanceDB:
    """
    Provenance tracking database for a single mission.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or os.environ.get("SVEL_SESSION_ID", "local_run")
        self.db_path = PROVENANCE_DIR / f"provenance_{self.session_id}.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()

        self._init_schema()
        logger.info(f"ProvenanceDB initialized for mission: {self.session_id}")

    def _init_schema(self):
        """Create mission database schema."""
        with self.lock, self.conn:
            # Task graph (execution nodes)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS task_graph (
                    id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    parent_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_s REAL,
                    metadata TEXT
                )
            """)

            # Agent executions (detailed records)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    input_text TEXT,
                    output_text TEXT,
                    created_at TEXT NOT NULL,
                    duration_s REAL,
                    FOREIGN KEY (task_id) REFERENCES task_graph(id)
                )
            """)

            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_task_parent ON task_graph(parent_id)")

    def create_task(self, task_id: str, agent_name: str, parent_id: Optional[str] = None, metadata: Optional[Dict] = None):
        now = datetime.utcnow().isoformat()
        def _db_op():
            with self.lock, self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO task_graph (id, agent_name, parent_id, status, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (task_id, agent_name, parent_id, "running", now, json.dumps(metadata or {})))
        
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            asyncio.create_task(asyncio.to_thread(_db_op))
        except RuntimeError:
            _db_op()

    def complete_task(self, task_id: str, status: str, duration_s: Optional[float] = None):
        now = datetime.utcnow().isoformat()
        def _db_op():
            with self.lock, self.conn:
                self.conn.execute("""
                    UPDATE task_graph SET status = ?, completed_at = ?, duration_s = ?
                    WHERE id = ?
                """, (status, now, duration_s, task_id))
        
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            asyncio.create_task(asyncio.to_thread(_db_op))
        except RuntimeError:
            _db_op()

    def log_agent_execution(self, execution_id: str, task_id: str, agent_name: str, input_text: str, output_text: str, duration_s: float):
        now = datetime.utcnow().isoformat()
        def _db_op():
            with self.lock, self.conn:
                self.conn.execute("""
                    INSERT OR IGNORE INTO task_graph (id, agent_name, parent_id, status, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (task_id, agent_name, None, "running", now, "{}"))
                self.conn.execute("""
                    INSERT OR REPLACE INTO agent_executions (id, task_id, agent_name, input_text, output_text, created_at, duration_s)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (execution_id, task_id, agent_name, str(input_text)[:50000], str(output_text)[:50000], now, duration_s))
        
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            asyncio.create_task(asyncio.to_thread(_db_op))
        except RuntimeError:
            _db_op()

    def close(self):
        with self.lock:
            if self.conn:
                self.conn.close()
                self.conn = None

# Singleton logic for compute node
_db_instance: Optional[ProvenanceDB] = None

def get_provenance_db() -> ProvenanceDB:
    global _db_instance
    current_session = os.environ.get("SVEL_SESSION_ID", "local_run")
    if _db_instance is not None and _db_instance.session_id != current_session:
        try:
            _db_instance.close()
        except Exception as e:
            logger.warning(f"Error closing old ProvenanceDB connection: {e}")
        _db_instance = None

    if _db_instance is None:
        _db_instance = ProvenanceDB(current_session)
    return _db_instance
