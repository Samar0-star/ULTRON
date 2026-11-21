# -*- coding: utf-8 -*-
"""
Deep Paper Reader for Autonomous Research Cycles
=================================================
Reads FULL PAPER CONTENT from academic sources (not just snippets).
Designed for 12-24 hour research runs to match SVEL-level paper reading.

Capabilities:
- arXiv: Full PDF extraction (up to 20 pages)
- PubMed: Full abstracts + methods extraction  
- Semantic Scholar: Full abstracts + PDF when available
- PDF caching to avoid re-downloads
"""

import os
import logging
import hashlib
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from backend.llm_manager import run_llm, DEEP_PAPER_READING_MODEL
except ImportError:
    run_llm = None
    DEEP_PAPER_READING_MODEL = None

logger = logging.getLogger("tools.deep_paper_reader")

# Cache directory for downloaded PDFs
CACHE_DIR = os.path.join(os.getcwd(), ".paper_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Rate limiting
_last_request_time = 0
_min_request_interval = 0.5  # seconds


async def _rate_limit():
    """Respect API rate limits (ASYNC)."""
    global _last_request_time
    import asyncio
    elapsed = time.time() - _last_request_time
    if elapsed < _min_request_interval:
        await asyncio.sleep(_min_request_interval - elapsed)
    _last_request_time = time.time()


def _get_cache_key(paper_id: str, source: str) -> str:
    """Generate unique cache key for paper."""
    return hashlib.md5(f"{source}:{paper_id}".encode()).hexdigest()


def _load_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Load paper from cache if available."""
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_to_cache(cache_key: str, data: Dict[str, Any]):
    """Save paper to cache."""
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to cache paper: {e}")


async def _read_arxiv_paper_async(arxiv_id: str, max_pages: int = 15) -> Dict[str, Any]:
    """Internal async implementation of arXiv reader."""
    cache_key = _get_cache_key(arxiv_id, "arxiv")
    cached = _load_from_cache(cache_key)
    if cached:
        logger.debug(f"Cache hit for arXiv:{arxiv_id}")
        return cached
    
    await _rate_limit()
    
    try:
        from backend.tools.arxiv_tool import get_paper_full_text
        result = get_paper_full_text(arxiv_id, max_pages=max_pages)
        
        if result and "error" not in result:
            full_text_raw = result.get("full_text", "")
            if len(full_text_raw) > 200000 and run_llm:
                logger.info(f" [DOC] Large paper detected ({len(full_text_raw)/1024:.1f}KB). Synthesizing...")
                full_text = await synthesize_full_text(full_text_raw, result.get("title", "Unknown"))
            else:
                full_text = full_text_raw[:200000]

            paper = {
                "id": arxiv_id,
                "source": "arXiv",
                "title": result.get("title", ""),
                "authors": ", ".join(result.get("authors", [])[:5]),
                "abstract": result.get("abstract", ""),
                "full_text": full_text,
                "pdf_url": result.get("pdf_url", ""),
                "categories": result.get("categories", []),
                "word_count": len(result.get("full_text", "").split()),
                "read_status": "full_pdf"
            }
            _save_to_cache(cache_key, paper)
            logger.info(f" Read arXiv paper: {paper['title'][:50]}... ({paper['word_count']} words)")
            return paper
    except Exception as e:
        logger.warning(f"Failed to read arXiv paper {arxiv_id}: {e}")
    
    return {"id": arxiv_id, "source": "arXiv", "error": "Failed to extract", "read_status": "failed"}

def _run_sync(coro):
    """[TITAN V225.0] THREAD-SAFE SYNC WRAPPER
    Physically abolished nest_asyncio and asyncio.run() deadlocks.
    Routes execution to a dedicated background loop to prevent starvation.
    """
    import threading
    result = []
    error = []

    def _thread_worker():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result.append(loop.run_until_complete(coro))
            loop.close()
        except Exception as e:
            error.append(e)

    t = threading.Thread(target=_thread_worker)
    t.start()
    t.join()

    if error:
        logger.error(f" [READER] Sync execution failed: {error[0]}")
        return None
    return result[0] if result else None

def read_arxiv_paper(arxiv_id: str, max_pages: int = 15) -> Dict[str, Any]:
    """Synchronous entry point for ToolRegistry."""
    return _run_sync(_read_arxiv_paper_async(arxiv_id, max_pages))


async def _read_semantic_scholar_paper_async(paper_id: str) -> Dict[str, Any]:
    """Internal async implementation."""
    cache_key = _get_cache_key(paper_id, "semantic_scholar")
    cached = _load_from_cache(cache_key)
    if cached:
        logger.debug(f"Cache hit for S2:{paper_id}")
        return cached
    
    await _rate_limit()
    
    try:
        from backend.tools.semantic_scholar_tool import get_paper_details
        result = get_paper_details(paper_id)
        
        if result and "error" not in result:
            paper = {
                "id": paper_id,
                "source": "Semantic Scholar",
                "title": result.get("title", ""),
                "authors": ", ".join(result.get("authors", [])[:5]),
                "abstract": result.get("abstract", ""),
                "tldr": result.get("tldr", ""),
                "citation_count": result.get("citation_count", 0),
                "pdf_url": result.get("pdf_url", ""),
                "word_count": len((result.get("abstract") or "").split()),
                "read_status": "abstract"
            }
            
            # Try to get full PDF if available
            if paper.get("pdf_url"):
                try:
                    from backend.tools.arxiv_tool import download_and_extract_pdf
                    # Use a smaller page limit for initial details, but full reader will use more
                    full_text = download_and_extract_pdf(paper["pdf_url"], max_pages=10)
                    if full_text and "[PDF extraction failed" not in full_text:
                        if len(full_text) > 200000 and run_llm:
                            paper["full_text"] = await synthesize_full_text(full_text, paper["title"])
                        else:
                            paper["full_text"] = full_text[:200000]
                        paper["word_count"] = len(str(paper.get("full_text", "")).split())
                        paper["read_status"] = "full_pdf"
                except Exception:
                    pass
            
            _save_to_cache(cache_key, paper)
            logger.info(f" Read S2 paper: {paper['title'][:50]}... ({paper['read_status']})")
            return paper
    except Exception as e:
        logger.warning(f"Failed to read S2 paper {paper_id}: {e}")
    
    return {"id": paper_id, "source": "Semantic Scholar", "error": "Failed to extract", "read_status": "failed"}

def read_semantic_scholar_paper(paper_id: str) -> Dict[str, Any]:
    """Sync entry point."""
    return _run_sync(_read_semantic_scholar_paper_async(paper_id))


async def _read_pubmed_paper_async(pmid: str) -> Dict[str, Any]:
    """Internal async implementation."""
    cache_key = _get_cache_key(pmid, "pubmed")
    cached = _load_from_cache(cache_key)
    if cached:
        logger.debug(f"Cache hit for PMID:{pmid}")
        return cached
    
    await _rate_limit()
    
    try:
        from backend.tools.pubmed_tool import fetch_article_details
        results = fetch_article_details([pmid])
        
        if results:
            article = results[0]
            abstract_text = article.get("abstract") or ""
            paper = {
                "id": pmid,
                "source": "PubMed",
                "title": article.get("title") or "",
                "authors": ", ".join((article.get("authors") or [])[:5]),
                "abstract": abstract_text,
                "journal": article.get("journal") or "",
                "year": article.get("year") or "",
                "doi": article.get("doi") or "",
                "mesh_terms": article.get("mesh_terms") or [],
                "word_count": len(abstract_text.split()),
                "read_status": "abstract"
            }
            _save_to_cache(cache_key, paper)
            logger.info(f" Read PubMed paper: {paper['title'][:50]}... (abstract)")
            return paper
    except Exception as e:
        logger.warning(f"Failed to read PubMed paper {pmid}: {e}")
    
    return {"id": pmid, "source": "PubMed", "error": "Failed to extract", "read_status": "failed"}

def read_pubmed_paper(pmid: str) -> Dict[str, Any]:
    """Sync entry point."""
    return _run_sync(_read_pubmed_paper_async(pmid))


async def _read_biorxiv_paper_async(doi: str, max_pages: int = 15) -> Dict[str, Any]:
    """Internal async implementation."""
    cache_key = _get_cache_key(doi, "biorxiv")
    cached = _load_from_cache(cache_key)
    if cached:
        return cached
        
    try:
        from backend.tools.biorxiv_tool import get_paper_full_text
        result = get_paper_full_text(doi, max_pages=max_pages)
        if isinstance(result, str) and result.strip():
            title = doi
            if result.startswith("Title:"):
                first_line = result.splitlines()[0]
                title = first_line.replace("Title:", "", 1).strip() or doi
            result = {
                "id": doi,
                "doi": doi,
                "source": "biorxiv",
                "title": title,
                "full_text": result,
                "word_count": len(result.split()),
                "read_status": "full_text",
            }
        if isinstance(result, dict) and "error" not in result:
            # [UPGRADE] Recursive synthesis for preprints
            full_text_raw = result.get("full_text") or ""
            if len(full_text_raw) > 50000 and run_llm:
                result["full_text"] = await synthesize_full_text(full_text_raw, result.get("title", "Unknown"))
            
            _save_to_cache(cache_key, result)
            return result
    except Exception as e:
        logger.warning(f"Failed to read BioRxiv paper {doi}: {e}")
        
    return {"id": doi, "source": "biorxiv", "error": "Failed to extract", "read_status": "failed"}

def read_biorxiv_paper(doi: str, max_pages: int = 15) -> Dict[str, Any]:
    """Sync entry point."""
    return _run_sync(_read_biorxiv_paper_async(doi, max_pages))


def read_papers_parallel(
    paper_ids: List[Dict[str, str]], 
    max_workers: int = 5,
    max_pages: int = 10
) -> List[Dict[str, Any]]:
    """
    Read multiple papers in parallel via internal asyncio loop.
    This remains synchronous to the ToolRegistry.
    Uses a Semaphore to limit concurrent downloads and prevent OOM.
    Uses _run_sync to avoid RuntimeError when called from a running event loop.
    """
    async def _internal_gather():
        sem = asyncio.Semaphore(max_workers)

        async def _throttled(coro):
            async with sem:
                return await coro

        tasks = []
        for p in paper_ids:
            source = p.get("source", "").lower()
            paper_id = p.get("id", "")
            if source == "arxiv":
                tasks.append(_throttled(_read_arxiv_paper_async(paper_id, max_pages)))
            elif source in ["semantic_scholar", "s2"]:
                tasks.append(_throttled(_read_semantic_scholar_paper_async(paper_id)))
            elif source == "pubmed":
                tasks.append(_throttled(_read_pubmed_paper_async(paper_id)))
            elif source in ["biorxiv", "medrxiv"]:
                tasks.append(_throttled(_read_biorxiv_paper_async(doi=paper_id, max_pages=max_pages)))
            else:
                tasks.append(asyncio.sleep(0)) # No-op
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    result = _run_sync(_internal_gather())
    if result is None:
        logger.error("Parallel paper reading loop failed")
        return []
    
    # Process results
    processed_results = []
    for i, res in enumerate(result):
        if isinstance(res, Exception):
            processed_results.append({
                "id": paper_ids[i].get("id", ""),
                "source": paper_ids[i].get("source", ""),
                "error": str(res),
                "read_status": "failed"
            })
        elif res is not None:
            processed_results.append(res)
            
    return processed_results


def get_paper_reading_stats() -> Dict[str, Any]:
    """Get statistics on cached papers."""
    cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
    
    total_papers = len(cache_files)
    total_words = 0
    by_source = {"arXiv": 0, "Semantic Scholar": 0, "PubMed": 0}
    
    for cf in cache_files:
        try:
            with open(os.path.join(CACHE_DIR, cf), "r", encoding="utf-8") as f:
                paper = json.load(f)
                total_words += paper.get("word_count", 0)
                source = paper.get("source", "Unknown")
                if source in by_source:
                    by_source[source] += 1
        except Exception:
            pass
    
    return {
        "total_papers": total_papers,
        "total_words": total_words,
        "by_source": by_source,
        "cache_dir": CACHE_DIR
    }


# Convenience function for research cycles
async def _deep_read_for_research_async(query: Any, max_papers: int = 50, domain: Optional[str] = None, weights: Optional[Dict[str, float]] = None, use_neural: bool = False) -> List[Dict[str, Any]]:
    """Internal async research cycle engine."""
    # [GODZILLA FIX] Robust Unpacking: Extract string from dict if needed
    if isinstance(query, dict):
        query = query.get("query") or query.get("input") or str(query)
    
    clean_query = str(query)
    papers_to_read = []
    
    # Invoke the 'Mind' (Neural Routing)
    try:
        from backend.tools.scholar_nexus.unify import unified_scholar
        logger.info(f" Consulting the Mind (Neural Routing) for: '{clean_query[:50]}'")
        weights = await unified_scholar._neural_route(clean_query)
        logger.info(f" Mind Decision (Weights): {weights}")
    except Exception as e:
        logger.warning(f"Neural routing failed, using safety default: {e}")
        weights = {"arxiv": 0.5, "pubmed": 0.5, "s2": 0.5}
    
    if not weights:
        weights = {"arxiv": 0.5, "pubmed": 0.5, "s2": 0.5}

    total_weight = sum(weights.values()) or 1.0
    budget = {
        "arxiv": int(max_papers * (weights.get("arxiv", 0) / total_weight)),
        "pubmed": int(max_papers * (weights.get("pubmed", 0) / total_weight)),
        "semantic_scholar": int(max_papers * (weights.get("s2", 0) / total_weight))
    }
    
    for k in budget:
        weight_key = "s2" if k == "semantic_scholar" else k
        if weights.get(weight_key, 0) > 0.25 and budget[k] == 0:
            budget[k] = 1

    logger.info(f" Neural Budget Allocation: {budget}")

    # 1. Search ArXiv
    if budget.get("arxiv", 0) > 0:
        try:
            from backend.tools.arxiv_tool import search_arxiv
            arxiv_results = search_arxiv(clean_query, max_results=budget["arxiv"])
            for paper in arxiv_results:
                papers_to_read.append({"id": paper.get("arxiv_id", ""), "source": "arxiv"})
        except Exception as e:
            logger.warning(f"arxiv search failed: {e}")
    
    # 2. Search Semantic Scholar
    if budget.get("semantic_scholar", 0) > 0:
        try:
            from backend.tools.semantic_scholar_tool import search_papers
            s2_results = search_papers(clean_query, limit=budget["semantic_scholar"])
            for paper in s2_results:
                paper_id = paper.get("doi") or paper.get("arxiv_id") or ""
                if paper_id:
                    papers_to_read.append({"id": paper_id, "source": "semantic_scholar"})
        except Exception as e:
            logger.warning(f"Semantic Scholar search failed: {e}")
    
    # 3. Search PubMed and BioRxiv/MedRxiv
    if budget.get("pubmed", 0) > 0:
        try:
            from backend.tools.pubmed_tool import search_pubmed
            pmids = search_pubmed(clean_query, max_results=budget["pubmed"])
            for pmid in pmids:
                if pmid:
                    papers_to_read.append({"id": str(pmid), "source": "pubmed"})
        except Exception as e:
            logger.warning(f"PubMed search failed: {e}")

    if budget.get("pubmed", 0) > 0 or domain in ["medical", "biology"]:
        try:
            from backend.tools.biorxiv_tool import search_papers as search_biorxiv
            b_limit = max(3, budget.get("pubmed", 0) // 2)
            bio_results = search_biorxiv(clean_query, limit=b_limit)
            for paper in bio_results:
                if paper.get("doi"):
                    papers_to_read.append({"id": paper["doi"], "source": paper.get("server", "biorxiv")})
        except Exception as e:
            logger.warning(f"BioRxiv search failed: {e}")
            
    # Finally call parallel reader
    if papers_to_read:
        return await _read_papers_parallel_internal(papers_to_read)
    return []

async def _read_papers_parallel_internal(paper_ids: List[Dict[str, str]], max_pages: int = 15, max_workers: int = 8) -> List[Dict[str, Any]]:
    """Internal parallel reader for async use with semaphore throttling."""
    sem = asyncio.Semaphore(max_workers)

    async def _throttled(coro):
        async with sem:
            return await coro

    tasks = []
    for p in paper_ids:
        source = p.get("source", "").lower()
        id_val = p.get("id", "")
        if source == "arxiv":
            tasks.append(_throttled(_read_arxiv_paper_async(id_val, max_pages)))
        elif source in ["semantic_scholar", "s2"]:
            tasks.append(_throttled(_read_semantic_scholar_paper_async(id_val)))
        elif source == "pubmed":
            tasks.append(_throttled(_read_pubmed_paper_async(id_val)))
        elif source in ["biorxiv", "medrxiv"]:
            tasks.append(_throttled(_read_biorxiv_paper_async(id_val, max_pages)))
            
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in raw_results if isinstance(r, dict)]

def deep_read_for_research(query: str, max_papers: int = 50, domain: Optional[str] = None, weights: Optional[Dict[str, float]] = None, use_neural: bool = False) -> List[Dict[str, Any]]:
    """Synchronous entry point for research cycles.
    Uses _run_sync to avoid RuntimeError deadlock when called from inside
    an already-running event loop.
    """
    result = _run_sync(_deep_read_for_research_async(query, max_papers, domain, weights, use_neural))
    if result is None:
        logger.error("Deep read failed (returned None from sync wrapper)")
        return []
    return result

    
 

# Quick test
async def synthesize_full_text(content: str, title: str = "") -> str:
    """Synthesize full paper content using recursive micro-chunking."""
    if not run_llm:
        return content[:50000] + "\n\n[TRUNCATED: LLM NOT AVAILABLE]"
        
    CHUNK_SIZE = 40000
    OVERLAP = 2000
    
    if len(content) <= CHUNK_SIZE:
        return content
        
    logger.debug(f" [DOC] Synthesizing {len(content)} chars via micro-chunks...")
    chunks = []
    for i in range(0, len(content), CHUNK_SIZE - OVERLAP):
        chunks.append(content[i:i + CHUNK_SIZE])
    
    # Process up to 10 chunks to avoid extreme token burn
    partial_findings = []
    for idx, chunk in enumerate(chunks[:10]):
        prompt = f"""Extract ALL key scientific findings, data points, and mechanisms from this paper CHUNK.
Paper Title: '{title}'

CRITICAL: 
- Capture every reported p-value, effect size, and sample size.
- Do NOT summarize numeric data; extract it exactly.
- Identify the specific methodology used in this section.

CONTENT:
{chunk}"""
        try:
            resp = await asyncio.to_thread(run_llm, prompt, model=DEEP_PAPER_READING_MODEL)
            if isinstance(resp, dict):
                resp = resp.get("text", "")
            partial_findings.append(str(resp))
        except Exception as e:
            logger.warning(f"Chunk {idx} synthesis failed: {e}")
            
    # Final Synthesis
    synthesis_prompt = f"""Generate a comprehensive Ph.D.-level synthesis of the paper '{title}' based on these partial findings. 

STRICT REQUIREMENTS:
1. Preserve ALL statistical data (p-values, effect sizes, N numbers).
2. Detail the mechanisms and causal links identified.
3. Organize by Methodology, Results, and Significance.
4. Maintain a formal, academic tone.

PARTIAL FINDINGS:
{chr(10).join(partial_findings)}
"""
    try:
        final_resp = await asyncio.to_thread(run_llm, synthesis_prompt, model=DEEP_PAPER_READING_MODEL)
        if isinstance(final_resp, dict):
            return str(final_resp.get("text") or "")
        return str(final_resp or "")
    except Exception as e:
        logger.error(f"Final synthesis failed: {e}")
        return content[:50000] + "\n\n[FALLBACK: Synthesis failed]"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test single paper read
    paper = read_arxiv_paper("2301.07041", max_pages=5)
    print(f"\nRead paper: {paper.get('title', 'N/A')}")
    print(f"Words: {paper.get('word_count', 0)}")
    print(f"Status: {paper.get('read_status', 'unknown')}")
    
    # Show stats
    stats = get_paper_reading_stats()
    print(f"\nCache stats: {stats}")

