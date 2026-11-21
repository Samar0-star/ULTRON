# -*- coding: utf-8 -*-
"""
PubMed Medical Literature Tool
==============================
Search biomedical and life science literature from PubMed/MEDLINE.
100% FREE - NIH Public Access.

No API key required for basic usage (rate limited to 3 requests/second).
With API key (free from NCBI): 10 requests/second.
"""

import os
import logging
import time
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree
import urllib.request
import urllib.parse

logger = logging.getLogger("tools.pubmed")

# Optional API key for higher rate limits (free from NCBI)
PUBMED_API_KEY = os.getenv("NCBI_API_KEY", "").strip()

# Rate limiting
_last_request_time = 0
_rate_limit = 0.35 if PUBMED_API_KEY else 1.0  # seconds between requests

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _rate_limit_wait():
    """Ensure we don't exceed rate limits."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _rate_limit:
        time.sleep(_rate_limit - elapsed)
    _last_request_time = time.time()


def _make_request(url: str, retries: int = 3) -> str:
    """Make HTTP request with error handling and exponential backoff."""
    for attempt in range(retries):
        _rate_limit_wait()
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            logger.warning(f"PubMed request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"PubMed request ultimately failed after {retries} attempts: {e}")
                return ""
    return ""


def search_pubmed(
    query: str,
    max_results: int = 10,
    sort: str = "relevance"  # "relevance" or "date"
) -> List[str]:
    """
    Search PubMed for article IDs.
    
    Args:
        query: Search query (supports PubMed query syntax)
        max_results: Maximum results to return
        sort: Sort order ("relevance" or "date")
        
    Returns:
        List of PubMed IDs (PMIDs)
    """
    # [GODZILLA FIX] Truncate query to prevent HTTP 414: Request-URI Too Long
    if len(query) > 500:
        logger.warning(f" [PUBMED] Query too long ({len(query)} chars). Truncating to 500.")
        query = query[:500]

    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": sort,
        "retmode": "json"
    }
    
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    
    url = f"{BASE_URL}/esearch.fcgi?" + urllib.parse.urlencode(params)
    
    try:
        import json
        response = _make_request(url)
        if not response:
            return []
        
        data = json.loads(response)
        id_list = data.get("esearchresult", {}).get("idlist", [])
        logger.info(f"PubMed search '{query}' returned {len(id_list)} IDs")
        return id_list
        
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return []


def fetch_article_details(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch full article details for given PMIDs.
    
    Args:
        pmids: List of PubMed IDs
        
    Returns:
        List of article metadata dicts
    """
    if not pmids:
        return []
    
    # [TITAN V141.4] CHUNKED FETCHING
    # Prevent HTTP 414 Request-URI Too Long by chunking PMIDs into batches of 100.
    all_articles = []
    chunk_size = 100
    for i in range(0, len(pmids), chunk_size):
        chunk = pmids[i:i + chunk_size]
        params = {
            "db": "pubmed",
            "id": ",".join(chunk),
            "retmode": "xml"
        }
        
        if PUBMED_API_KEY:
            params["api_key"] = PUBMED_API_KEY
        
        url = f"{BASE_URL}/efetch.fcgi?" + urllib.parse.urlencode(params)
        
        try:
            response = _make_request(url)
            if not response:
                continue
            
            # Parse XML
            root = ElementTree.fromstring(response)
            
            for article_elem in root.findall(".//PubmedArticle"):
                article = _parse_article(article_elem)
                if article:
                    all_articles.append(article)
            
        except Exception as e:
            logger.error(f"PubMed fetch failed for chunk: {e}")
            continue
            
    logger.info(f"Fetched details for {len(all_articles)} PubMed articles")
    return all_articles


def _parse_article(article_elem) -> Optional[Dict[str, Any]]:
    """Parse a single PubMed article from XML."""
    try:
        medline = article_elem.find(".//MedlineCitation")
        if medline is None:
            return None
        
        article = medline.find(".//Article")
        if article is None:
            return None
        
        # Extract PMID
        pmid_elem = medline.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else None
        
        # Extract title (SVEL BEAST FIX: Preserve nested tags)
        title_elem = article.find(".//ArticleTitle")
        title = "".join(title_elem.itertext()) if title_elem is not None else "Unknown Title"
        
        # Extract abstract (SVEL BEAST FIX: Preserve nested tags)
        abstract_parts = []
        for abs_text in article.findall(".//AbstractText"):
            label = abs_text.get("Label", "")
            text = "".join(abs_text.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = " ".join(abstract_parts) if abstract_parts else None
        
        # Extract authors
        authors = []
        for author in article.findall(".//Author"):
            last_name = author.findtext("LastName", "")
            first_name = author.findtext("ForeName", "")
            if last_name:
                authors.append(f"{first_name} {last_name}".strip())
        
        # Extract publication date
        pub_date = article.find(".//PubDate")
        year = pub_date.findtext("Year") if pub_date is not None else None
        month = pub_date.findtext("Month") if pub_date is not None else None
        
        # Extract journal
        journal_elem = article.find(".//Journal")
        journal = journal_elem.findtext(".//Title") if journal_elem is not None else None
        
        # Extract DOI
        doi = None
        for id_elem in article_elem.findall(".//ArticleId"):
            if id_elem.get("IdType") == "doi":
                doi = id_elem.text
                break
        
        # Extract MeSH terms (medical subject headings)
        mesh_terms = []
        for mesh in medline.findall(".//MeshHeading/DescriptorName"):
            if mesh.text:
                mesh_terms.append(mesh.text)
        
        # Extract keywords
        keywords = []
        for kw in article.findall(".//Keyword"):
            if kw.text:
                keywords.append(kw.text)
        
        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors[:10],  # Limit authors
            "year": year,
            "month": month,
            "journal": journal,
            "doi": doi,
            "mesh_terms": mesh_terms[:10],
            "keywords": keywords[:10],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse article: {e}")
        return None


def search_papers(
    query: str,
    limit: int = 10,
    sort: str = "relevance"
) -> List[Dict[str, Any]]:
    """
    Search PubMed and return full article details.
    
    Args:
        query: Search query
        limit: Max results
        sort: Sort order
        
    Returns:
        List of article metadata
    """
    pmids = search_pubmed(query, max_results=limit, sort=sort)
    return fetch_article_details(pmids)


def search_and_format(query: str, max_papers: int = 50) -> str:
    """
    Search PubMed and format results for agents.
    
    Args:
        query: Search query
        max_papers: Max papers to return
        
    Returns:
        Formatted string with paper info
    """
    papers = search_papers(query, limit=max_papers)
    
    if not papers:
        return f"No PubMed articles found for: {query}"
    
    output = [f"# PubMed Results for: {query}\n"]
    output.append(f"Found {len(papers)} articles\n")
    
    for i, paper in enumerate(papers, 1):
        output.append(f"\n## {i}. {paper['title']}")
        output.append(f"\n**PMID:** {paper.get('pmid', 'N/A')}")
        output.append(f"\n**Year:** {paper.get('year', 'N/A')} | **Journal:** {paper.get('journal', 'N/A')}")
        output.append(f"\n**Authors:** {', '.join(paper.get('authors', [])[:5])}")
        
        if paper.get('mesh_terms'):
            output.append(f"\n**MeSH Terms:** {', '.join(paper['mesh_terms'][:5])}")
        
        if paper.get('abstract'):
            abstract = paper['abstract'][:10000] + "..." if len(paper.get('abstract', '')) > 10000 else paper.get('abstract', '')
            output.append(f"\n**Abstract:** {abstract}")
        
        if paper.get('doi'):
            output.append(f"\n**DOI:** https://doi.org/{paper['doi']}")
        
        if paper.get('url'):
            output.append(f"\n**PubMed Link:** {paper['url']}")
        
        output.append("\n" + "-" * 40)
    
    return "\n".join(output)


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = search_and_format("CRISPR gene editing cancer", max_papers=3)
    print(result)
