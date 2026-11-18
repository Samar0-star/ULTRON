# backend/memory/memory_manager.py
"""
ULTRON Memory Manager - Headless Edition
========================================
Unified API for mission-local short-term and long-term memory.
Designed for isolated, single-tenant compute nodes.
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime

from backend.memory.vectorstore import get_vectorstore
from backend.memory.provenance_db import get_provenance_db

logger = logging.getLogger("ultron.memory_manager")

# Configuration
SHORT_TERM_MAX_ITEMS = int(os.getenv("SHORT_TERM_MAX_ITEMS", "100"))
LONG_TERM_THRESHOLD = int(os.getenv("LONG_TERM_THRESHOLD", "20"))


class MemoryManager:
    """
    Unified memory management for a single research mission.
    """

    def __init__(self):
        # Store current session ID to detect switches
        self.session_id = os.environ.get("ULTRON_SESSION_ID", "local_run")

        # Short-term memory (mission-local)
        self.short_term: deque = deque(maxlen=SHORT_TERM_MAX_ITEMS)
        
        # Long-term memory (mission-local FAISS)
        self.vectorstore = get_vectorstore()

        # Provenance database (mission-local SQLite)
        self.provenance_db = get_provenance_db()

        # Campaign-specific tracking (for internal task sharding)
        self.task_memory: Dict[str, List[str]] = {}

        logger.info(f"MemoryManager initialized (Single-Mission Mode) for session: {self.session_id}")

    def add_short(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        role: str = "assistant"
    ) -> Dict[str, Any]:
        """Add item to mission short-term memory."""
        item = {
            "content": content,
            "role": role,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.short_term.append(item)

        # Auto-consolidate to long-term if threshold reached
        if len(self.short_term) >= LONG_TERM_THRESHOLD:
            self._consolidate_to_long_term()

        return item

    def query_short(
        self,
        max_items: Optional[int] = None,
        role_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query mission short-term memory."""
        items = list(self.short_term)
        if role_filter:
            items = [item for item in items if item.get("role") == role_filter]
        
        items.reverse() # Most recent first
        return items[:max_items] if max_items else items

    def _consolidate_to_long_term(self):
        """Move old short-term items to vector store."""
        if not self.short_term:
            return
        
        # Take the oldest half of short-term memory
        n_to_move = len(self.short_term) // 2
        items_to_move = []
        for _ in range(n_to_move):
            items_to_move.append(self.short_term.popleft())  # Pop from left (oldest)

        for item in items_to_move:
            doc_id = f"st_{int(time.time())}_{hash(item['content']) % 10000}"
            self.vectorstore.add_document(doc_id, item['content'], item['metadata'])
            
        logger.info(f"Consolidated {len(items_to_move)} items to long-term memory")

    def store_long(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Store item directly in mission vector store."""
        doc_id = f"lt_{int(time.time() * 1000)}"
        self.vectorstore.add_document(doc_id, content, metadata or {})

    def query_long(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search on mission knowledge base."""
        return self.vectorstore.query(query, top_k=top_k)

    def get_stats(self) -> Dict[str, Any]:
        """Get mission memory statistics."""
        return {
            "short_term_count": len(self.short_term),
            "vector_store": self.vectorstore.stats() if hasattr(self.vectorstore, 'stats') else "active"
        }

    def health(self) -> Dict[str, Any]:
        """Health check for startup_checks and system diagnostics."""
        return {
            "status": "ok",
            "session_id": self.session_id,
            "short_term_count": len(self.short_term),
            "vector_store": "active" if self.vectorstore is not None else "unavailable",
            "provenance_db": "active" if self.provenance_db is not None else "unavailable"
        }

# Singleton
_instance: Optional[MemoryManager] = None

def get_memory_manager() -> MemoryManager:
    global _instance
    current_session = os.environ.get("ULTRON_SESSION_ID", "local_run")
    if _instance is not None and getattr(_instance, "session_id", None) != current_session:
        logger.info(f"Session ID changed from {getattr(_instance, 'session_id', None)} to {current_session}. Reinitializing MemoryManager.")
        _instance = None

    if _instance is None:
        _instance = MemoryManager()
    return _instance
