"""
Semantic Scholar Academic Paper Tool
=====================================
Search academic papers across all disciplines.
API KEY OPTIONAL - Works without key but with rate limits.
"""

import os
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from functools import wraps

logger = logging.getLogger("tools.semantic_scholar")

def retry_with_backoff(retries=3, backoff_in_seconds=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    result = func(*args, **kwargs)
                    if x > 0:
                        logger.info(f"Semantic Scholar retry successful after {x} attempts.")
                    return result
                except Exception as e:
                    # Check for 429 or rate limit in error message
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        if x >= retries:
                            logger.error(f"Semantic Scholar rate limit hit. Max retries ({retries}) reached: {e}")
                            raise e
                        
                        sleep = min(30, backoff_in_seconds * (2 ** x))
                        logger.warning(f"Semantic Scholar 429 hit. Retrying in {sleep}s... (Attempt {x+1}/{retries})")
                        time.sleep(sleep)
                        x += 1
                    else:
                        raise e
        return wrapper
    return decorator

# Optional API key for higher rate limits
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()

# Lazy import
_sch = None

def _get_client():
    global _sch
    if _sch is None:
        from semanticscholar import SemanticScholar
        if SEMANTIC_SCHOLAR_API_KEY:
            _sch = SemanticScholar(api_key=SEMANTIC_SCHOLAR_API_KEY, timeout=15, retry=True)
            logger.info("Semantic Scholar initialized with API key")
        else:
            _sch = SemanticScholar(timeout=10, retry=False)
            logger.info("Semantic Scholar initialized without API key (fail-fast on rate limits)")
    return _sch


def search_papers(
    query: Any,
    limit: int = 10,
    fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar for academic papers.
    
    Args:
        query: Search query (str or dict)
        limit: Max results (default 10)
        fields: Optional list of fields to return
        
    Returns:
        List of paper metadata
    """
    # [GODZILLA FIX] Robust Unpacking: Extract string from dict if needed
    if isinstance(query, dict):
        query = query.get("query") or query.get("input") or str(query)
    
    clean_query = str(query)
    sch = _get_client()
    
    if fields is None:
        fields = [
            "title", "abstract", "year", "authors", 
            "citationCount", "url", "openAccessPdf",
            "fieldsOfStudy", "publicationVenue", "externalIds"
        ]
    
    max_retries = 3 if SEMANTIC_SCHOLAR_API_KEY else 1
    backoff = 10 if SEMANTIC_SCHOLAR_API_KEY else 1

    @retry_with_backoff(retries=max_retries, backoff_in_seconds=backoff)
    def _do_search():
        return sch.search_paper(clean_query, limit=limit, fields=fields)
    
    try:
        results = _do_search()
        
        papers = []
        for paper in results:
            paper_dict = {
                "title": getattr(paper, 'title', 'Unknown'),
                "abstract": getattr(paper, 'abstract', None),
                "year": getattr(paper, 'year', None),
                "citation_count": getattr(paper, 'citationCount', 0),
                "url": getattr(paper, 'url', None),
                "fields_of_study": getattr(paper, 'fieldsOfStudy', []),
            }
            
            # Extract authors
            authors = getattr(paper, 'authors', [])
            paper_dict['authors'] = [a.get('name', 'Unknown') if isinstance(a, dict) else getattr(a, 'name', 'Unknown') for a in authors[:10]]
            
            # Check for open access PDF
            oa_pdf = getattr(paper, 'openAccessPdf', None)
            if oa_pdf:
                paper_dict['pdf_url'] = oa_pdf.get('url') if isinstance(oa_pdf, dict) else getattr(oa_pdf, 'url', None)
            else:
                paper_dict['pdf_url'] = None
            
            # External IDs (DOI, ArXiv, etc.)
            ext_ids = getattr(paper, 'externalIds', {})
            if ext_ids:
                paper_dict['doi'] = ext_ids.get('DOI') if isinstance(ext_ids, dict) else getattr(ext_ids, 'DOI', None)
                paper_dict['arxiv_id'] = ext_ids.get('ArXiv') if isinstance(ext_ids, dict) else getattr(ext_ids, 'ArXiv', None)
            
            papers.append(paper_dict)
        
        logger.info(f"Semantic Scholar search '{query}' returned {len(papers)} papers")
        return papers
        
    except Exception as e:
        logger.error(f"Semantic Scholar search failed: {e}")
        return []


def get_paper_details(paper_id: str) -> Dict[str, Any]:
    """
    Get detailed info about a specific paper.
    
    Args:
        paper_id: Semantic Scholar paper ID, DOI, or ArXiv ID
        
    Returns:
        Paper details dict
    """
    sch = _get_client()
    
    @retry_with_backoff(retries=5, backoff_in_seconds=5)
    def _do_get():
        return sch.get_paper(
            paper_id,
            fields=[
                "title", "abstract", "year", "authors", 
                "citationCount", "referenceCount", "url",
                "openAccessPdf", "fieldsOfStudy", "tldr",
                "publicationVenue", "citations", "references"
            ]
        )
    
    try:
        paper = _do_get()
        
        result = {
            "title": getattr(paper, 'title', 'Unknown'),
            "abstract": getattr(paper, 'abstract', None),
            "year": getattr(paper, 'year', None),
            "citation_count": getattr(paper, 'citationCount', 0),
            "reference_count": getattr(paper, 'referenceCount', 0),
            "url": getattr(paper, 'url', None),
            "fields_of_study": getattr(paper, 'fieldsOfStudy', []),
        }
        
        # TLDR (AI-generated summary)
        tldr = getattr(paper, 'tldr', None)
        if tldr:
            result['tldr'] = tldr.get('text') if isinstance(tldr, dict) else getattr(tldr, 'text', None)
        
        # Authors
        authors = getattr(paper, 'authors', [])
        result['authors'] = [a.get('name', 'Unknown') if isinstance(a, dict) else getattr(a, 'name', 'Unknown') for a in authors[:20]]
        
        # Open access PDF
        oa_pdf = getattr(paper, 'openAccessPdf', None)
        if oa_pdf:
            result['pdf_url'] = oa_pdf.get('url') if isinstance(oa_pdf, dict) else getattr(oa_pdf, 'url', None)
        
        # Top citations and references
        citations = getattr(paper, 'citations', [])
        result['top_citations'] = [
            {"title": getattr(c, 'title', 'Unknown'), "year": getattr(c, 'year', None)}
            for c in citations[:5]
        ]
        
        references = getattr(paper, 'references', [])
        result['top_references'] = [
            {"title": getattr(r, 'title', 'Unknown'), "year": getattr(r, 'year', None)}
            for r in references[:5]
        ]
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get paper {paper_id}: {e}")
        return {"error": str(e), "paper_id": paper_id}


def search_and_format(query: str, max_papers: int = 50) -> str:
    """
    Search and format results for agents.
    
    Args:
        query: Search query
        max_papers: Max papers to return
        
    Returns:
        Formatted string with paper info
    """
    papers = search_papers(query, limit=max_papers)
    
    if not papers:
        return f"No papers found on Semantic Scholar for: {query}"
    
    output = [f"# Semantic Scholar Results for: {query}\n"]
    output.append(f"Found {len(papers)} papers\n")
    
    for i, paper in enumerate(papers, 1):
        output.append(f"\n## {i}. {paper['title']}")
        output.append(f"\n**Year:** {paper.get('year', 'N/A')} | **Citations:** {paper.get('citation_count', 0)}")
        output.append(f"\n**Authors:** {', '.join(paper.get('authors', [])[:5])}")
        
        if paper.get('fields_of_study'):
            output.append(f"\n**Fields:** {', '.join(paper['fields_of_study'][:3])}")
        
        if paper.get('abstract'):
            abstract = paper['abstract'][:800] + "..." if len(paper.get('abstract', '')) > 800 else paper.get('abstract', '')
            output.append(f"\n**Abstract:** {abstract}")
        
        if paper.get('pdf_url'):
            output.append(f"\n**Open Access PDF:** {paper['pdf_url']}")
        elif paper.get('arxiv_id'):
            output.append(f"\n**ArXiv:** https://arxiv.org/abs/{paper['arxiv_id']}")
        
        if paper.get('doi'):
            output.append(f"\n**DOI:** {paper['doi']}")
        
        output.append("\n" + "-" * 40)
    
    return "\n".join(output)


# CrewAI-compatible tool class
class SemanticScholarTool:
    """CrewAI-compatible Semantic Scholar search tool."""
    
    name = "semantic_scholar_search"
    description = "Search Semantic Scholar for academic papers across all disciplines. Returns paper titles, abstracts, citation counts, and links to PDFs when available."
    
    def search_papers(self, query: Any, limit: int = 10, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Structured paper search returning list of paper dicts (used by RedTeamAgent.verify_citation)."""
        return search_papers(query, limit=limit, fields=fields)

    def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """Structured paper details lookup."""
        return get_paper_details(paper_id)

    def run(self, query: str) -> str:
        """Execute search."""
        return search_and_format(query, max_papers=5)
    
    def _run(self, query: str) -> str:
        """Alias for CrewAI compatibility."""
        return self.run(query)


# Singleton instance
semantic_scholar_tool = SemanticScholarTool()
