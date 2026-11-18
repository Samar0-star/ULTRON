"""
ArXiv Academic Paper Tool
=========================
Search and download full papers from arXiv (CS, Physics, Math, etc.)
NO API KEY REQUIRED - Completely free.
"""

import os
import re
import logging
import tempfile
from typing import List, Dict, Any, Optional

logger = logging.getLogger("tools.arxiv")

# Lazy import to avoid startup issues
_arxiv = None
_fitz = None  # PyMuPDF

def _get_arxiv():
    global _arxiv
    if _arxiv is None:
        import arxiv
        _arxiv = arxiv
    return _arxiv

def _get_fitz():
    global _fitz
    if _fitz is None:
        import fitz  # PyMuPDF
        _fitz = fitz
    return _fitz


def search_arxiv(
    query: str,
    max_results: int = 50,
    sort_by: str = "relevance"  # "relevance", "lastUpdatedDate", "submittedDate"
) -> List[Dict[str, Any]]:
    """
    Search arXiv for academic papers.
    
    Args:
        query: Search query (supports arXiv query syntax)
        max_results: Maximum papers to return (default 5)
        sort_by: Sort order
        
    Returns:
        List of paper metadata dicts
    """
    arxiv = _get_arxiv()
    
    sort_map = {
        "relevance": arxiv.SortCriterion.Relevance,
        "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
        "submittedDate": arxiv.SortCriterion.SubmittedDate,
    }
    
    try:
        # Keep parentheses if they are balanced to allow logical grouping (e.g. AND / OR)
        if query.count('(') == query.count(')'):
            # [ULTRON BEAST FIX] Preserve ArXiv Range Brackets [ ]
            safe_query = re.sub(r'[^a-zA-Z0-9\s\-\.\:\"\'\*\+\(\)\[\]]', '', query)
        else:
            safe_query = re.sub(r'[^a-zA-Z0-9\s\-\.\:\"\'\*\+\[\]]', '', query)
        if len(safe_query) > 1000:
            safe_query = safe_query[:1000].rsplit(' ', 1)[0] # Cut cleanly
            
        # [GHOST-SHIP-FIX] Slash retries from 5→2 — 5 retries at 10s each = 50s wasted per 429.
        # ArXiv won't un-throttle in 50s anyway. Fail fast and let the jitter handle it.
        client = arxiv.Client(
            page_size=min(max_results, 30),
            delay_seconds=10.0,
            num_retries=2
        )
        
        search = arxiv.Search(
            query=safe_query,
            max_results=max_results,
            sort_by=sort_map.get(sort_by, arxiv.SortCriterion.Relevance)
        )
        
        results = []
        for paper in client.results(search):
            results.append({
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "abstract": paper.summary,
                "arxiv_id": paper.entry_id.split("/")[-1],
                "pdf_url": paper.pdf_url,
                "published": paper.published.isoformat() if paper.published else None,
                "updated": paper.updated.isoformat() if paper.updated else None,
                "categories": paper.categories,
                "primary_category": paper.primary_category,
                "doi": paper.doi,
                "journal_ref": paper.journal_ref,
            })
        
        logger.info(f"ArXiv search '{query}' returned {len(results)} papers")
        return results
        
    except Exception as e:
        logger.error(f"ArXiv search failed: {e}")
        return []


def download_and_extract_pdf(pdf_url: str, max_pages: int = 20) -> str:
    """
    Download PDF from URL and extract text content using in-memory stream.
    """
    import requests
    import io
    fitz = _get_fitz()
    
    try:
        # [GODZILLA FIX] ROBUST HEADERS: Add User-Agent to avoid blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        # Download PDF
        response = requests.get(pdf_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Open from stream - no temp files, no Windows lock issues
        stream = io.BytesIO(response.content)
        doc = fitz.open(stream=stream, filetype="pdf")
        
        text_parts = []
        num_pages = min(len(doc), max_pages)
        
        for page_num in range(num_pages):
            try:
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
            except Exception as page_err:
                logger.warning(f"Failed to extract page {page_num+1}: {page_err}")
        
        doc.close()
        
        full_text = "\n\n".join(text_parts)
        if not full_text.strip():
            return "[PDF extraction returned empty text]"
            
        logger.info(f"Extracted {len(full_text)} chars from PDF ({num_pages} pages)")
        return full_text
        
    except Exception as e:
        logger.error(f"PDF extraction failed for {pdf_url}: {e}")
        return f"[PDF extraction failed: {e}]"


def get_paper_full_text(arxiv_id: str, max_pages: int = 20) -> Dict[str, Any]:
    """
    Get full paper content by arXiv ID.
    
    Args:
        arxiv_id: ArXiv paper ID (e.g., "2301.07041")
        max_pages: Max pages to extract
        
    Returns:
        Dict with metadata and full text
    """
    arxiv = _get_arxiv()
    
    try:
        # Fetch paper metadata
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(search.results())
        
        # Download and extract PDF
        full_text = download_and_extract_pdf(paper.pdf_url, max_pages)
        
        return {
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "abstract": paper.summary,
            "full_text": full_text,
            "arxiv_id": arxiv_id,
            "pdf_url": paper.pdf_url,
            "categories": paper.categories,
        }
        
    except Exception as e:
        logger.error(f"Failed to get paper {arxiv_id}: {e}")
        return {"error": str(e), "arxiv_id": arxiv_id}


def search_and_summarize(query: str, max_papers: int = 3, max_pages_per_paper: int = 10) -> str:
    """
    Search arXiv and return summarized content from top papers.
    Designed for direct use by agents.
    
    Args:
        query: Search query
        max_papers: How many papers to read
        max_pages_per_paper: Pages to extract per paper
        
    Returns:
        Formatted string with paper summaries
    """
    papers = search_arxiv(query, max_results=max_papers)
    
    if not papers:
        return f"No arXiv papers found for: {query}"
    
    output_parts = [f"# ArXiv Research Results for: {query}\n"]
    output_parts.append(f"Found {len(papers)} papers\n")
    
    for i, paper in enumerate(papers, 1):
        output_parts.append(f"\n## Paper {i}: {paper['title']}\n")
        output_parts.append(f"**Authors:** {', '.join(paper['authors'][:5])}")
        if len(paper['authors']) > 5:
            output_parts.append(f" (+{len(paper['authors']) - 5} more)")
        output_parts.append(f"\n**ArXiv ID:** {paper['arxiv_id']}")
        output_parts.append(f"\n**Categories:** {', '.join(paper['categories'][:3])}")
        output_parts.append(f"\n**Published:** {paper['published'][:10] if paper['published'] else 'N/A'}")
        output_parts.append(f"\n\n**Abstract:**\n{paper['abstract'][:1500]}...")
        
        # Try to get first few pages of full text
        try:
            full_text = download_and_extract_pdf(paper['pdf_url'], max_pages=max_pages_per_paper)
            try:
                from backend.config import settings
                max_chars = settings.get_limit("max_context_chars", 100000)
            except Exception:
                max_chars = 100000
            if len(full_text) > max_chars:
                full_text = full_text[:max_chars] + "\n\n[... truncated at configured limit ...]"
            output_parts.append(f"\n\n**Full Text Preview:**\n{full_text}")
        except Exception as e:
            output_parts.append(f"\n\n[Could not extract full text: {e}]")
        
        output_parts.append("\n" + "-" * 50)
    
    return "\n".join(output_parts)
