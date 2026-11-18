# backend/memory/vectorstore.py
"""
ULTRON Vector Store - Mission Isolation Edition
===============================================
Isolated FAISS vector store for a single research mission.
Forces local embeddings to ensure absolute data privacy and zero API dependency.
"""

import os
import json
import logging
import hashlib
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
try:
    import faiss
except ImportError:
    faiss = None

logger = logging.getLogger("ultron.vectorstore")

# Configuration
VECTOR_DIR = Path("data/vector_memory")
# Embedding model — pulled from llm_manager (the single source of truth).
# Override via ULTRON_EMBEDDING_MODEL env var.
from backend.llm_manager import EMBEDDING_MODEL, EMBEDDING_DIM as _EMBEDDING_DIM

class VectorStore:
    """
    Mission-isolated vector store.
    Everything is stored locally under data/vector_memory/missions/<session_id>.
    """

    def __init__(self, session_id: Optional[str] = None):
        # Align with global session if provided
        self.session_id = session_id or os.environ.get("ULTRON_SESSION_ID", "local_run")
        self.persist_path = VECTOR_DIR / "missions" / self.session_id
        self.persist_path.mkdir(parents=True, exist_ok=True)
        
        self.dim = _EMBEDDING_DIM  # Sourced from llm_manager / ULTRON_EMBEDDING_DIM env var

        # Initialize Local Embedding Model via shared singleton (caches offline failure to prevent redundant HF Hub stalls)
        self._model = None
        try:
            from backend.core.world_model import get_shared_embedding_model
            self._model = get_shared_embedding_model()
            if self._model is not None:
                logger.info(f" [MEMORY] Local Vector Memory ACTIVE (Isolated Mission: {self.session_id})")
            else:
                logger.info(f" [MEMORY] Shared embedding model offline; using deterministic L2-normalized feature hashing.")
        except Exception as e:
            logger.warning(f" [MEMORY] SentenceTransformer unavailable offline ({e}); using deterministic L2-normalized feature hashing.")

        # FAISS Initialization
        self.index = faiss.IndexFlatL2(self.dim) if faiss else None
        self.doc_meta: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._unsaved_count = 0
        self._batch_size = 10

        if self.index:
            self._load_index()

    def _deterministic_hash_embed(self, text: str) -> List[float]:
        """Deterministic L2-normalized feature-hashing vector fallback when SentenceTransformer is offline."""
        import re
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = [w for w in re.findall(r"[a-z0-9_]+", (text or "").lower()) if len(w) >= 2]
        if not tokens:
            vec[0] = 1.0
            return vec.tolist()
        # Unigrams + bigrams with signed murmur-style SHA-256 projection
        features = list(tokens) + [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
        for feat in features:
            h = hashlib.sha256(feat.encode("utf-8")).digest()
            idx1 = int.from_bytes(h[:4], "little") % self.dim
            sign1 = 1.0 if (h[4] & 1) == 0 else -1.0
            idx2 = int.from_bytes(h[8:12], "little") % self.dim
            sign2 = 1.0 if (h[12] & 1) == 0 else -1.0
            vec[idx1] += sign1
            vec[idx2] += 0.5 * sign2
        norm = float(np.linalg.norm(vec))
        if norm > 1e-8:
            vec /= norm
        else:
            vec[0] = 1.0
        return vec.tolist()

    def _embed_text(self, texts: List[str]) -> List[List[float]]:
        """Compute high-fidelity local embeddings (with deterministic L2-normalized hash fallback)."""
        if self._model is not None:
            try:
                embeddings = self._model.encode(texts, show_progress_bar=False)
                arr = np.asarray(embeddings, dtype=np.float32)
                if arr.ndim == 2 and arr.shape[1] == self.dim and not np.allclose(arr, 0.0):
                    norms = np.linalg.norm(arr, axis=1, keepdims=True)
                    norms = np.where(norms > 1e-8, norms, 1.0)
                    return (arr / norms).tolist()
            except Exception as e:
                logger.debug(f"Local encoding fallback triggered: {e}")
        return [self._deterministic_hash_embed(t) for t in texts]

    def _load_index(self):
        index_file = self.persist_path / "faiss.index"
        meta_file = self.persist_path / "meta.json"
        
        if index_file.exists() and faiss:
            try:
                self.index = faiss.read_index(str(index_file))
                if meta_file.exists():
                     with open(meta_file, "r", encoding="utf-8") as f:
                        self.doc_meta = json.load(f)
                logger.info(f"Loaded mission vector index: {len(self.doc_meta)} documents.")
            except Exception as e:
                logger.warning(f"Failed to load mission index: {e}")

    def _save_index_unlocked(self):
        """Internal save - caller must hold self._lock."""
        if not faiss: return
        try:
            faiss.write_index(self.index, str(self.persist_path / "faiss.index"))
            with open(self.persist_path / "meta.json", "w", encoding="utf-8") as f:
                json.dump(self.doc_meta, f)
            self._unsaved_count = 0
        except Exception as e:
            logger.error(f"Failed to persist mission index: {e}")

    def _save_index(self):
        """Thread-safe save."""
        if not faiss: return
        with self._lock:
            self._save_index_unlocked()

    def add_document(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a single finding to the mission knowledge base."""
        if not self.index: return
        with self._lock:
            try:
                embedding = self._embed_text([content])
                emb = np.array(embedding, dtype=np.float32)
                self.index.add(emb)
                self.doc_meta.append({
                    "id": doc_id, 
                    "content": content, 
                    "metadata": metadata or {},
                    "timestamp": time.time()
                })
                self._unsaved_count += 1
                if self._unsaved_count >= self._batch_size:
                    self._save_index_unlocked()
            except Exception as e:
                logger.error(f"Failed to add mission document {doc_id}: {e}")

    def flush(self):
        """Force-save the index to disk."""
        if not self.index: return
        with self._lock:
            if self._unsaved_count > 0:
                self._save_index_unlocked()

    def query(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search current mission findings."""
        if not self.index or not self.doc_meta: return []
        try:
            embedding = self._embed_text([query])
            emb = np.array(embedding, dtype=np.float32)
            distances, indices = self.index.search(emb, top_k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(self.doc_meta):
                    res = self.doc_meta[idx].copy()
                    res["score"] = float(distances[0][i])
                    results.append(res)
            return results
        except Exception as e:
            logger.error(f"Mission vector search failed: {e}")
            return []

    def similarity_search(self, query: str, k: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Compatibility adapter for LangChain / QA engine similarity search."""
        return self.query(query=query, top_k=k)

# Singleton logic for the compute node (session-aware — refreshes when ULTRON_SESSION_ID changes)
_vs_instance: Optional[VectorStore] = None
_vs_session_id: Optional[str] = None

def get_vectorstore() -> VectorStore:
    global _vs_instance, _vs_session_id
    current_session = os.environ.get("ULTRON_SESSION_ID", "local_run")
    if _vs_instance is None or _vs_session_id != current_session:
        _vs_instance = VectorStore(session_id=current_session)
        _vs_session_id = current_session
    return _vs_instance


# Backward compatibility instance for tools (e.g. qa_engine, web_search)
class _LazyVectorStoreProxy:
    def __getattr__(self, name):
        return getattr(get_vectorstore(), name)

    def __bool__(self):
        return True


vectorstore_instance = _LazyVectorStoreProxy()

