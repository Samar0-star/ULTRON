"""
Ultra-upgraded summarizer utility for long text.

Features:
- Async/sync API 
- Pure Python chunking (no LangChain)
- Direct LLM integration (no wrapper classes)
- File-based cache (sha256 of input + params)
- Progress logging and optional streaming callback
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import logging
from typing import Optional, Callable, Dict, Any, List
import asyncio
from backend.llm_manager import run_llm, run_llm_async

logger = logging.getLogger("ultron.summarizer")
logger.setLevel(os.getenv("SUMMARIZER_LOG_LEVEL", "INFO"))
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(ch)

# Simple file cache dir
CACHE_DIR = os.getenv("SUMMARIZER_CACHE_DIR", os.path.join(os.getcwd(), "data", "cache", ".gen_summary_cache"))
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_key(text: str, params: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    h.update(b"\n")
    h.update(json.dumps(params, sort_keys=True).encode("utf-8"))
    return h.hexdigest()

def _write_cache(key: str, obj: Any):
    try:
        path = os.path.join(CACHE_DIR, f"{key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, default=str)
    except Exception as e:
        logger.debug("Cache write error: %s", e)

def _read_cache(key: str):
    try:
        path = os.path.join(CACHE_DIR, f"{key}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.debug("Cache read error: %s", e)
    return None

def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Pure python overlapping chunk generator with positive step guard."""
    if not text:
        return []
    eff_size = max(1, int(chunk_size or 15000))
    eff_overlap = max(0, int(chunk_overlap or 0))
    step = max(1, eff_size - eff_overlap)
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + eff_size
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start += step
    return chunks

# Core async implementation
async def generate_summary_async(
    text: str,
    *,
    map_model: Optional[str] = None,
    reduce_model: Optional[str] = None,
    temperature: float = 0.2,
    chunk_size: int = 15000,
    chunk_overlap: int = 500,
    chain_type: str = "map_reduce",
    attempts: int = 3,
    timeout_seconds: Optional[float] = 120,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    force_reload: bool = False,
) -> Dict[str, Any]:
    """Generate summary using direct LLM routing (async)."""
    params = dict(map_model=map_model, reduce_model=reduce_model, temperature=temperature,
                  chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    cache_key = _cache_key(text, params)
    
    if not force_reload:
        cached = _read_cache(cache_key)
        if cached:
            logger.info("Cache hit for summary")
            if progress_callback:
                progress_callback("cache_hit", {"info": "from disk"})
            return cached

    chunks = _chunk_text(text, chunk_size, chunk_overlap)
    n_chunks = len(chunks)
    logger.info("Split text into %d chunks", n_chunks)
    if progress_callback:
        progress_callback("chunked", {"n_chunks": n_chunks})

    start_ts = time.time()
    
    try:
        partials: List[str] = []
        for i, chunk_text in enumerate(chunks):
            try:
                res = await run_llm_async(
                    prompt=f"Summarize the following text concisely, extracting key facts:\n\n{chunk_text}",
                    model=map_model or "auto",
                    temperature=temperature,
                    timeout=int(timeout_seconds or 120)
                )
                partials.append(res.get("text", chunk_text[:1000]))
            except Exception as e:
                logger.warning(f"Chunk {i} summary failed: {e}")
                partials.append(chunk_text[:1000])
                
            if progress_callback:
                progress_callback("map_progress", {"done": i+1, "total": n_chunks})
                
        combined = "\n\n".join(partials)
        
        # Final reduce
        if n_chunks > 1:
            final_res = await run_llm_async(
                prompt=f"Combine the following partial summaries into a comprehensive final summary:\n\n{combined}",
                model=reduce_model or "auto",
                temperature=temperature,
                timeout=int(timeout_seconds or 120)
            )
            final_summary = final_res.get("text", combined[:2000])
        else:
            final_summary = combined
            
        elapsed = time.time() - start_ts
        if progress_callback:
            progress_callback("reduce_done", {"elapsed": elapsed})
            
        result = {"summary": final_summary, "meta": {"method": "pure_python_map_reduce", "chunks": n_chunks, "elapsed": elapsed}}
        _write_cache(cache_key, result)
        return result
        
    except Exception as e:
        logger.exception("Summarization failed: %s", e)
        return {"summary": text[:2000], "meta": {"method": "failure_truncate", "error": str(e)}}


def generate_summary(text: str, **kwargs) -> Dict[str, Any]:
    """Synchronous wrapper around generate_summary_async (safe inside or outside running event loops)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(generate_summary_async(text, **kwargs))).result()

    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(generate_summary_async(text, **kwargs))
    finally:
        try:
            new_loop.close()
        except Exception:
            pass

def summarize_text(text: str, **kwargs) -> Dict[str, Any]:
    """Alias for generate_summary for backward compatibility."""
    return generate_summary(text, **kwargs)

class Summarizer:
    """Wrapper class for summarizer functions to match expected interface."""
    @staticmethod
    def generate_summary(*args, **kwargs):
        return generate_summary(*args, **kwargs)
