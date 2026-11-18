"""
Aetherix Avon-1  Web Search Tool (Godzilla Edition)

Performs powerful multi-engine searches (Google, Bing, DuckDuckGo, SerpAPI if configured),
parses results into structured objects, supports async batch search, result ranking,
search suggestions, statistics, caching, and vector memory integration.
"""

import logging
import time
import json
import re
import random
import requests
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse, quote_plus

# Optional extras
try:
    from bs4 import BeautifulSoup
    HAVE_BS4 = True
except Exception:
    HAVE_BS4 = False

try:
    import aiohttp
    import asyncio
    HAVE_AIOHTTP = True
except Exception:
    HAVE_AIOHTTP = False

#  Optional API support (SerpAPI / Google API)
import os
from dotenv import load_dotenv

# Load .env file BEFORE reading API keys
load_dotenv()


SERPAPI_KEY = os.environ.get("SERPAPI_KEY") or os.environ.get("SERP_API_KEY", None)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", None)
GOOGLE_CX = os.environ.get("GOOGLE_CX", None)


#  Aetherix Vectorstore Integration (memory for past queries)
try:
    from ..memory.vectorstore import vectorstore_instance
    # vectorstore_instance imported
except Exception as e:
    logging.getLogger("WebSearchTool").debug(f"vectorstore import failed: {e}")
    vectorstore_instance = None


#  LLM Manager (for summarization / reasoning)
try:
    from ..llm_manager import LLMManager
    # LLMManager imported
except Exception as e:
    logging.getLogger("WebSearchTool").debug(f"llm_manager import failed: {e}")
    LLMManager = None


#  BaseTool for standardized interface
try:
    from .base_tool import BaseTool, AsyncBaseTool
except Exception:
    # Fallback if base_tool not available
    class BaseTool:
        def format_output(self, result, **meta):
            return {"status": "success", "result": result, "meta": meta}
        def format_error(self, error, **meta):
            return {"status": "error", "result": None, "error": error, "meta": meta}
    AsyncBaseTool = BaseTool


# ----------------------------
# Data Models
# ----------------------------
class SearchType(Enum):
    GENERAL = "general"
    NEWS = "news"
    IMAGES = "images"
    VIDEOS = "videos"
    SHOPPING = "shopping"
    ACADEMIC = "academic"
    BOOKS = "books"
    PATENTS = "patents"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    rank: int
    search_type: SearchType
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class SearchResponse:
    query: str
    search_type: SearchType
    results: List[SearchResult]
    total_results: int
    search_time: float
    metadata: Dict[str, Any]
    timestamp: datetime



def sanitize_search_query(raw_query: str) -> str:
    """Sanitize and unwrap raw LLM queries into clean, single-line search queries.
    Strips Markdown code blocks, preamble labels, bullet points, and multi-line bloat.
    """
    if not raw_query or not isinstance(raw_query, str):
        return ""
    
    text = raw_query.strip()
    
    # 1. Check for fenced code blocks
    code_blocks = re.findall(r'```(?:python|bash|text)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_blocks:
        candidate = code_blocks[0].strip()
        # Handle python assignment query = ...
        m_triple = re.search(r'query\s*=\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', candidate, re.DOTALL)
        if m_triple:
            candidate = m_triple.group(1).strip()
        else:
            m_single = re.search(r'query\s*=\s*([\'"])(.*?)\1', candidate, re.DOTALL)
            if m_single:
                candidate = m_single.group(2).strip()
        lines = [line.strip() for line in candidate.splitlines() if line.strip()]
        text = lines[0] if lines else candidate
    else:
        # 2. Extract after standard LLM preamble headers
        m = re.search(r'(?:OPTIMIZED ARCHITECTURAL QUERY|Optimized Query|OPTIMIZED QUERY|QUERY):\s*(.+)', text, re.IGNORECASE)
        if m:
            text = m.group(1).strip()

    # 3. Strip markdown decorators, quotes, bold tags
    text = text.replace('`', '').replace('**', '').replace('__', '')
    
    # 4. If multi-line, take the first valid line that is not a heading, comment, or bullet
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_lines = []
    for line in lines:
        if line.startswith(('#', '*', '-', '>', '|')):
            continue
        if any(line.lower().startswith(prefix) for prefix in [
            'rationale:', 'component', 'word count:', 'recommended execution:', 'alternative', 'compact form'
        ]):
            break
        clean_lines.append(line)
        
    if clean_lines:
        text = clean_lines[0]

    # 5. Clean leading/trailing quotes and normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip(' "\'')
    
    # 6. Hard limit length to 250 characters for search engines
    if len(text) > 250:
        text = text[:250].rsplit(' ', 1)[0]
        
    return text.strip()


# ----------------------------
# Main Tool
# ----------------------------
class WebSearchTool(BaseTool):
    """Web search tool with multi-engine support."""
    
    name = "web_search"
    description = "Multi-engine web search (Google, Bing, DuckDuckGo, SerpAPI)"
    version = "2.0.0"
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("WebSearchTool")
        self.llm_manager = LLMManager() if LLMManager else None
        self.cache: Dict[str, SearchResponse] = {}

        # Engines
        self.search_engines = self._init_engines()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/114.0",
        ]
        self.last_search_time = 0
        self.min_interval = 1.0  # seconds
    
    def run(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standard interface for web search.
        
        Args:
            input: {
                "query": str (required),
                "max_results": int (default: 10),
                "engine": str (default: "google"),
                "search_type": str (default: "general")
            }
        
        Returns:
            {
                "status": "success" | "error",
                "result": List[Dict],  # Search results
                "meta": {"query": str, "provider": str, "total": int, "duration_ms": float}
            }
        """
        query = input.get("query")
        if not query:
            return self.format_error("Missing required field: query")
        
        max_results = input.get("max_results", 10)
        engine = input.get("engine", "google")
        search_type_str = input.get("search_type", "general")
        
        try:
            search_type = SearchType(search_type_str)
        except ValueError:
            search_type = SearchType.GENERAL
        
        try:
            start_time = time.time()
            response = self.search(query, search_type, max_results, engine)
            duration_ms = (time.time() - start_time) * 1000
            
            # Convert SearchResult objects to dicts
            results = [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                    "rank": r.rank
                }
                for r in response.results
            ]
            
            return self.format_output(
                result=results,
                query=query,
                provider=engine,
                total=response.total_results,
                duration_ms=duration_ms
            )
        except Exception as e:
            self.logger.exception(f"Search failed: {e}")
            return self.format_error(str(e), query=query, provider=engine)

    def _init_engines(self) -> Dict[str, Dict[str, Any]]:
        return {
            "google": {"base_url": "https://www.google.com/search", "enabled": True, "rate": 2.0},
            "bing": {"base_url": "https://www.bing.com/search", "enabled": True, "rate": 1.5},
            "duckduckgo": {"base_url": "https://duckduckgo.com/html", "enabled": True, "rate": 1.0},
            "serpapi": {"enabled": SERPAPI_KEY is not None},
            "google_api": {"enabled": GOOGLE_API_KEY and GOOGLE_CX},
            "google_scholar": {"enabled": True, "rate": 2.0},  # Academic search
            "arxiv": {"enabled": True, "rate": 1.0},  # arXiv API
        }


    def _rate_limit(self):
        delta = time.time() - self.last_search_time
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self.last_search_time = time.time()

    def _get_ua(self) -> str:
        return random.choice(self.user_agents)

    # ----------------------------
    # Main search entry
    # ----------------------------
    def search(
        self, query: str, search_type: SearchType = SearchType.GENERAL,
        max_results: int = 10, engine: str = "google"
    ) -> SearchResponse:
        query = sanitize_search_query(query)
        start = datetime.now()
        self._rate_limit()

        # Cache check
        cache_key = hashlib.md5(f"{engine}-{search_type.value}-{query}".encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]

        results: List[SearchResult] = []
        if engine == "serpapi" and SERPAPI_KEY:
            results = self._search_serpapi(query, search_type, max_results)
        elif engine == "google_api" and GOOGLE_API_KEY and GOOGLE_CX:
            results = self._search_google_api(query, max_results)
        elif engine.lower() == "google_scholar":
            results = self._search_google_scholar(query, search_type, max_results)
        elif engine.lower() == "arxiv":
            results = self._search_arxiv(query, search_type, max_results)
        elif engine.lower() == "pubmed":
            results = self._search_pubmed(query, search_type, max_results)
        elif engine.lower() == "semantic_scholar":
            results = self._search_semantic_scholar(query, search_type, max_results)
        elif engine.lower() == "google":
            results = self._search_google_html(query, search_type, max_results)
        elif engine.lower() == "bing":
            results = self._search_bing_html(query, search_type, max_results)
        elif engine.lower() == "duckduckgo":
            results = self._search_ddg_html(query, search_type, max_results)


        resp = SearchResponse(
            query=query,
            search_type=search_type,
            results=results,
            total_results=len(results),
            search_time=(datetime.now() - start).total_seconds(),
            metadata={"engine": engine, "max_results": max_results},
            timestamp=datetime.now(),
        )
        self.cache[cache_key] = resp

        # Push to vector memory
        if vectorstore_instance and results:
            combined_text = "\n".join([r.title + " " + r.snippet for r in results])
            try:
                vectorstore_instance.add_document(f"search:{cache_key}", combined_text)
            except Exception:
                pass

        return resp

    # ----------------------------
    # Engine Implementations
    # ----------------------------
    def _search_serpapi(self, query: str, search_type: SearchType, max_results: int) -> List[SearchResult]:
        """Search using SerpAPI via direct HTTP request (more reliable than serpapi library)."""
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": SERPAPI_KEY,
                "num": min(max_results, 10),
                "engine": "google"
            }
            res = requests.get(url, params=params, timeout=30)
            if res.status_code != 200:
                logger.warning(f"SerpAPI HTTP error: {res.status_code}")
                return []
            
            data = res.json()
            out = []
            for i, item in enumerate(data.get("organic_results", [])[:max_results]):
                out.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=self._domain(item.get("link", "")),
                    rank=i+1,
                    search_type=search_type,
                    metadata=item,
                    timestamp=datetime.now()
                ))
            return out
        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")
            return []

    def _search_google_api(self, query: str, max_results: int) -> List[SearchResult]:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"q": query, "key": GOOGLE_API_KEY, "cx": GOOGLE_CX, "num": min(max_results, 10)}
        res = requests.get(url, params=params, timeout=10)
        out = []
        if res.status_code == 200:
            data = res.json()
            for i, item in enumerate(data.get("items", [])):
                out.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=self._domain(item.get("link", "")),
                    rank=i+1,
                    search_type=SearchType.GENERAL,
                    metadata=item,
                    timestamp=datetime.now()
                ))
        return out

    def _search_google_html(self, query: str, search_type: SearchType, max_results: int) -> List[SearchResult]:
        headers = {"User-Agent": self._get_ua()}
        params = {"q": query, "num": min(max_results, 10), "hl": "en"}
        res = requests.get(self.search_engines["google"]["base_url"], params=params, headers=headers, timeout=10)
        if res.status_code != 200:
            return []
        return self._parse_google(res.text, search_type, max_results)

    def _parse_google(self, html: str, stype: SearchType, k: int) -> List[SearchResult]:
        results = []
        if HAVE_BS4:
            soup = BeautifulSoup(html, "html.parser")
            for i, g in enumerate(soup.select("div.g")[:k]):
                a = g.find("a", href=True)
                title = g.get_text(" ", strip=True)[:200]
                snippet = g.text[:300]
                url = a["href"] if a else "#"
                results.append(SearchResult(
                    title=title, url=url, snippet=snippet,
                    source=self._domain(url), rank=i+1,
                    search_type=stype, metadata={}, timestamp=datetime.now()
                ))
        return results

    def _search_bing_html(self, query: str, stype: SearchType, max_results: int) -> List[SearchResult]:
        headers = {"User-Agent": self._get_ua()}
        params = {"q": query, "count": min(max_results, 10)}
        res = requests.get(self.search_engines["bing"]["base_url"], params=params, headers=headers, timeout=10)
        if res.status_code != 200:
            return []
        return self._parse_bing(res.text, stype, max_results)

    def _parse_bing(self, html: str, stype: SearchType, k: int) -> List[SearchResult]:
        results = []
        if HAVE_BS4:
            soup = BeautifulSoup(html, "html.parser")
            for i, li in enumerate(soup.select("li.b_algo")[:k]):
                a = li.find("a", href=True)
                title = a.get_text(strip=True) if a else f"Bing Result {i+1}"
                snippet = li.get_text(" ", strip=True)[:300]
                url = a["href"] if a else "#"
                results.append(SearchResult(
                    title=title, url=url, snippet=snippet,
                    source=self._domain(url), rank=i+1,
                    search_type=stype, metadata={}, timestamp=datetime.now()
                ))
        return results

    def _search_ddg_html(self, query: str, stype: SearchType, max_results: int) -> List[SearchResult]:
        """DuckDuckGo search using their instant answer API + HTML fallback."""
        results = []
        
        # Method 1: Try DuckDuckGo Instant Answer API (fast but limited)
        try:
            api_url = "https://api.duckduckgo.com/"
            params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
            # Reduced timeout to avoid blocking
            res = requests.get(api_url, params=params, timeout=3)
            if res.status_code == 200:
                data = res.json()
                
                # Get abstract if available
                if data.get("Abstract"):
                    results.append(SearchResult(
                        title=data.get("Heading", query),
                        url=data.get("AbstractURL", "https://duckduckgo.com"),
                        snippet=data.get("Abstract", "")[:500],
                        source=data.get("AbstractSource", "DuckDuckGo"),
                        rank=1,
                        search_type=stype,
                        metadata={"type": "instant_answer"},
                        timestamp=datetime.now()
                    ))
                
                # Get related topics
                for i, topic in enumerate(data.get("RelatedTopics", [])[:max_results-1]):
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(SearchResult(
                            title=topic.get("Text", "")[:100],
                            url=topic.get("FirstURL", "#"),
                            snippet=topic.get("Text", "")[:300],
                            source="DuckDuckGo",
                            rank=len(results)+1,
                            search_type=stype,
                            metadata=topic,
                            timestamp=datetime.now()
                        ))
                
                if results:
                    self.logger.info(f"DDG API returned {len(results)} results")
                    return results[:max_results]
        except Exception as e:
            self.logger.warning(f"DDG API failed: {e}")
        
        # Method 2: Fallback to HTML scraping (Correct endpoint + Headers)
        # Use html.duckduckgo.com for the non-JS version
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://html.duckduckgo.com/",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://html.duckduckgo.com",
            "Upgrade-Insecure-Requests": "1"
        }
        params = {"q": query}
        
        try:
            self.logger.info(f"Scraping DDG HTML for: {query}")
            res = requests.post(url, data=params, headers=headers, timeout=10)
            
            if res.status_code == 200 and HAVE_BS4:
                soup = BeautifulSoup(res.text, "html.parser")
                
                # DDG HTML selectors often change, look for result classes
                for i, result_div in enumerate(soup.select(".result")[:max_results]):
                    a = result_div.select_one("a.result__a")
                    snippet_div = result_div.select_one("a.result__snippet")
                    
                    if a:
                        url_hit = a.get("href", "#")
                        title = a.get_text(strip=True)
                        snippet = snippet_div.get_text(strip=True) if snippet_div else ""
                        
                        results.append(SearchResult(
                            title=title, url=url_hit, snippet=snippet,
                            source=self._domain(url_hit), rank=len(results)+1,
                            search_type=stype, metadata={}, timestamp=datetime.now()
                        ))
                
                if results:
                    self.logger.info(f"DDG HTML returned {len(results)} results")
        except Exception as e:
            self.logger.warning(f"DDG HTML scraping failed: {e}")
        
        return results

    def _search_google_scholar(self, query: str, stype: SearchType, max_results: int) -> List[SearchResult]:
        """Search Google Scholar for academic papers with citation metadata."""
        results = []
        try:
            # Use SerpAPI for Google Scholar if available (more reliable)
            if SERPAPI_KEY:
                url = "https://serpapi.com/search"
                params = {
                    "q": query,
                    "api_key": SERPAPI_KEY,
                    "engine": "google_scholar",
                    "num": min(max_results, 20)
                }
                res = requests.get(url, params=params, timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    for i, item in enumerate(data.get("organic_results", [])[:max_results]):
                        # Extract citation metadata
                        pub_info = item.get("publication_info", {})
                        authors = pub_info.get("authors", [])
                        author_str = ", ".join([a.get("name", "") for a in authors[:3]])
                        if len(authors) > 3:
                            author_str += " et al."
                        
                        results.append(SearchResult(
                            title=item.get("title", ""),
                            url=item.get("link", ""),
                            snippet=item.get("snippet", ""),
                            source="Google Scholar",
                            rank=i + 1,
                            search_type=SearchType.ACADEMIC,
                            metadata={
                                "authors": author_str,
                                "year": pub_info.get("summary", "").split(" - ")[0] if pub_info.get("summary") else "",
                                "cited_by": item.get("inline_links", {}).get("cited_by", {}).get("total", 0),
                                "doi": self._extract_doi(item.get("link", "")),
                                "publication": pub_info.get("summary", ""),
                                "type": "academic"
                            },
                            timestamp=datetime.now()
                        ))
                    self.logger.info(f"Google Scholar (SerpAPI) returned {len(results)} results")
                    return results
            
            # Fallback: Scrape Google Scholar HTML (less reliable, may get blocked)
            headers = {"User-Agent": self._get_ua()}
            url = "https://scholar.google.com/scholar"
            params = {"q": query, "hl": "en", "num": min(max_results, 10)}
            
            res = requests.get(url, params=params, headers=headers, timeout=15)
            if res.status_code == 200 and HAVE_BS4:
                soup = BeautifulSoup(res.text, "html.parser")
                for i, result in enumerate(soup.select(".gs_r.gs_or.gs_scl")[:max_results]):
                    title_elem = result.select_one("h3.gs_rt a")
                    snippet_elem = result.select_one(".gs_rs")
                    info_elem = result.select_one(".gs_a")
                    
                    if title_elem:
                        url_hit = title_elem.get("href", "#")
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        info = info_elem.get_text(strip=True) if info_elem else ""
                        
                        # Parse author/year from info string (e.g., "JD Smith, AB Jones - Nature, 2023")
                        authors = ""
                        year = ""
                        if " - " in info:
                            parts = info.split(" - ")
                            authors = parts[0].strip()
                            if len(parts) > 1:
                                year_match = re.search(r'\d{4}', parts[-1])
                                year = year_match.group() if year_match else ""
                        
                        results.append(SearchResult(
                            title=title, url=url_hit, snippet=snippet,
                            source="Google Scholar",
                            rank=i + 1,
                            search_type=SearchType.ACADEMIC,
                            metadata={
                                "authors": authors,
                                "year": year,
                                "doi": self._extract_doi(url_hit),
                                "type": "academic"
                            },
                            timestamp=datetime.now()
                        ))
                
                if results:
                    self.logger.info(f"Google Scholar HTML returned {len(results)} results")
        except Exception as e:
            self.logger.warning(f"Google Scholar search failed: {e}")
        
        return results

    def _search_arxiv(self, query: str, stype: SearchType, max_results: int) -> List[SearchResult]:
        """Search arXiv API for physics/CS/math preprints with full metadata."""
        results = []
        try:
            import xml.etree.ElementTree as ET
            
            # arXiv API endpoint
            url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": min(max_results, 50),
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            
            res = requests.get(url, params=params, timeout=20)
            if res.status_code == 200:
                # Parse Atom XML response
                root = ET.fromstring(res.content)
                ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
                
                for i, entry in enumerate(root.findall("atom:entry", ns)[:max_results]):
                    title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                    summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:500]
                    arxiv_id = entry.find("atom:id", ns).text.strip()
                    
                    # Extract arXiv ID from URL
                    arxiv_id_short = arxiv_id.split("/abs/")[-1] if "/abs/" in arxiv_id else arxiv_id
                    
                    # Get authors
                    authors = []
                    for author in entry.findall("atom:author", ns):
                        name = author.find("atom:name", ns)
                        if name is not None:
                            authors.append(name.text.strip())
                    author_str = ", ".join(authors[:3])
                    if len(authors) > 3:
                        author_str += " et al."
                    
                    # Get publication date
                    published = entry.find("atom:published", ns)
                    year = published.text[:4] if published is not None else ""
                    
                    # Get PDF link
                    pdf_link = f"https://arxiv.org/pdf/{arxiv_id_short}"
                    abs_link = f"https://arxiv.org/abs/{arxiv_id_short}"
                    
                    # Get categories
                    categories = []
                    for cat in entry.findall("arxiv:primary_category", ns):
                        categories.append(cat.get("term", ""))
                    
                    # Get DOI if available
                    doi_elem = entry.find("arxiv:doi", ns)
                    doi = doi_elem.text if doi_elem is not None else f"arXiv:{arxiv_id_short}"
                    
                    results.append(SearchResult(
                        title=title,
                        url=abs_link,
                        snippet=summary,
                        source="arXiv",
                        rank=i + 1,
                        search_type=SearchType.ACADEMIC,
                        metadata={
                            "authors": author_str,
                            "year": year,
                            "arxiv_id": arxiv_id_short,
                            "doi": doi,
                            "pdf_url": pdf_link,
                            "categories": categories,
                            "type": "preprint"
                        },
                        timestamp=datetime.now()
                    ))
                
                self.logger.info(f"arXiv returned {len(results)} results")
        except Exception as e:
            self.logger.warning(f"arXiv search failed: {e}")
        
        return results

    def _extract_doi(self, url: str) -> str:
        """Extract DOI from URL if present."""
        try:
            # Common DOI patterns in URLs
            doi_patterns = [
                r'doi\.org/(10\.\d{4,}/[^\s]+)',
                r'doi=(10\.\d{4,}/[^\s&]+)',
                r'(10\.\d{4,}/[^\s]+)'
            ]
            for pattern in doi_patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1).rstrip('/')
        except Exception:
            pass
        return ""

    def _search_pubmed(self, query: str, stype: SearchType, max_results: int) -> List[SearchResult]:
        """Search PubMed/NCBI for biomedical and life sciences literature."""
        results = []
        try:
            # PubMed E-utilities API (free, no key required for moderate use)
            # Step 1: Search for PMIDs
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": min(max_results, 100),
                "retmode": "json",
                "sort": "relevance"
            }
            
            search_res = requests.get(search_url, params=search_params, timeout=20)
            if search_res.status_code != 200:
                return results
            
            search_data = search_res.json()
            pmids = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                return results
            
            # Step 2: Fetch article details
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids[:max_results]),
                "retmode": "json"
            }
            
            fetch_res = requests.get(fetch_url, params=fetch_params, timeout=20)
            if fetch_res.status_code != 200:
                return results
            
            fetch_data = fetch_res.json()
            articles = fetch_data.get("result", {})
            
            for i, pmid in enumerate(pmids[:max_results]):
                if pmid not in articles:
                    continue
                    
                article = articles[pmid]
                title = article.get("title", "")
                
                # Extract authors
                authors_list = article.get("authors", [])
                if authors_list:
                    author_names = [a.get("name", "") for a in authors_list[:3]]
                    author_str = ", ".join(author_names)
                    if len(authors_list) > 3:
                        author_str += " et al."
                else:
                    author_str = "Unknown"
                
                # Extract year
                pubdate = article.get("pubdate", "")
                year = pubdate[:4] if pubdate else ""
                
                # Get DOI if available
                doi = ""
                elocation = article.get("elocationid", "")
                if "doi:" in elocation:
                    doi = elocation.replace("doi:", "").strip()
                
                results.append(SearchResult(
                    title=title,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    snippet=article.get("sorttitle", title)[:500],
                    source="PubMed",
                    rank=i + 1,
                    search_type=SearchType.ACADEMIC,
                    metadata={
                        "authors": author_str,
                        "year": year,
                        "pmid": pmid,
                        "doi": doi,
                        "journal": article.get("source", ""),
                        "type": "peer-reviewed"
                    },
                    timestamp=datetime.now()
                ))
            
            self.logger.info(f"PubMed returned {len(results)} results")
        except Exception as e:
            self.logger.warning(f"PubMed search failed: {e}")
        
        return results

    def _search_semantic_scholar(self, query: str, stype: SearchType, max_results: int) -> List[SearchResult]:
        """Search Semantic Scholar for CS/AI/ML papers with citation metrics."""
        results = []
        try:
            # Semantic Scholar API (free, generous limits)
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": min(max_results, 100),
                "fields": "title,abstract,authors,year,citationCount,openAccessPdf,externalIds,venue"
            }
            
            headers = {"Accept": "application/json"}
            res = requests.get(url, params=params, headers=headers, timeout=30)
            
            if res.status_code != 200:
                self.logger.warning(f"Semantic Scholar HTTP {res.status_code}")
                return results
            
            data = res.json()
            papers = data.get("data", [])
            
            for i, paper in enumerate(papers[:max_results]):
                title = paper.get("title", "")
                abstract = paper.get("abstract", "") or ""
                
                # Extract authors
                authors_list = paper.get("authors", [])
                if authors_list:
                    author_names = [a.get("name", "") for a in authors_list[:3]]
                    author_str = ", ".join(author_names)
                    if len(authors_list) > 3:
                        author_str += " et al."
                else:
                    author_str = "Unknown"
                
                year = paper.get("year", "")
                citations = paper.get("citationCount", 0)
                
                # Get DOI
                external_ids = paper.get("externalIds", {}) or {}
                doi = external_ids.get("DOI", "")
                arxiv_id = external_ids.get("ArXiv", "")
                
                # Get PDF URL if available
                pdf_info = paper.get("openAccessPdf", {}) or {}
                pdf_url = pdf_info.get("url", "")
                
                # Build URL
                paper_url = f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}"
                if doi:
                    paper_url = f"https://doi.org/{doi}"
                
                results.append(SearchResult(
                    title=title,
                    url=paper_url,
                    snippet=abstract[:500] if abstract else title,
                    source="Semantic Scholar",
                    rank=i + 1,
                    search_type=SearchType.ACADEMIC,
                    metadata={
                        "authors": author_str,
                        "year": str(year) if year else "",
                        "doi": doi,
                        "arxiv_id": arxiv_id,
                        "citations": citations,
                        "venue": paper.get("venue", ""),
                        "pdf_url": pdf_url,
                        "type": "peer-reviewed"
                    },
                    timestamp=datetime.now()
                ))
            
            self.logger.info(f"Semantic Scholar returned {len(results)} results")
        except Exception as e:
            self.logger.warning(f"Semantic Scholar search failed: {e}")
        
        return results


    # ----------------------------
    # Utilities
    # ----------------------------
    def _domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc
        except Exception:
            return "unknown"

    def search_suggestions(self, query: str, n: int = 5) -> List[str]:
        url = "https://suggestqueries.google.com/complete/search"
        params = {"q": query, "client": "firefox"}
        try:
            res = requests.get(url, params=params, headers={"User-Agent": self._get_ua()}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                return data[1][:n]
        except Exception as e:
            self.logger.error(f"suggestions error: {e}")
        return []

    async def search_async(self, queries: List[str], engine: str = "google") -> Dict[str, SearchResponse]:
        if not HAVE_AIOHTTP:
            return {q: self.search(q, engine=engine) for q in queries}

        async def fetch(session, q):
            try:
                return self.search(q, engine=engine)
            except Exception as e:
                return {"error": str(e)}

        async with aiohttp.ClientSession() as session:
            tasks = [fetch(session, q) for q in queries]
            results = await asyncio.gather(*tasks)
            return {q: r for q, r in zip(queries, results)}


# ----------------------------
# Beast Web Search Wrapper (Async)
# ----------------------------
class BeastWebSearch(AsyncBaseTool):
    """Async and sync callable web search tool with academic and multi-engine fallback."""
    
    name = "beast_web_search"
    description = "Async web search with SerpAPI/HTML scraping fallback"
    version = "2.0.0"

    def __init__(self):
        super().__init__()
        self.tool = WebSearchTool()
        self.logger = logging.getLogger("BeastWebSearch")

    def __call__(self, query_or_input: Any, max_results: int = 8, **kwargs) -> Dict[str, Any]:
        """Allow direct synchronous invocation: beast_search(query, max_results=8)."""
        if isinstance(query_or_input, dict):
            query = query_or_input.get("query", "")
            max_results = int(query_or_input.get("max_results") or query_or_input.get("num_results") or max_results)
        else:
            query = str(query_or_input)
        if not query:
            return {"status": "error", "error": "Missing query", "results": []}
        resp = self.tool.search(query, SearchType.GENERAL, max_results=max_results)
        return self._format_response(resp, "web_search_sync")
    
    async def run(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standard async interface for web search.
        
        Args:
            input: {"query": str, "num_results": int}
        
        Returns:
            Standard format: {"status": ..., "result": [...], "meta": {...}}
        """
        query = input.get("query")
        if not query:
            return self.format_error("Missing required field: query")
        
        num_results = input.get("num_results", 8)
        domain = input.get("domain") or input.get("DOMAIN")
        
        try:
            start_time = time.time()
            search_result = await self.search(query, num_results, domain=domain)
            duration_ms = (time.time() - start_time) * 1000
            
            if search_result.get("status") == "success":
                return self.format_output(
                    result=search_result.get("results", []),
                    query=query,
                    provider=search_result.get("provider"),
                    total=search_result.get("total_results", 0),
                    duration_ms=duration_ms
                )
            else:
                return self.format_error(
                    search_result.get("error", "Unknown error"),
                    query=query,
                    provider=search_result.get("provider", "unknown")
                )
        except Exception as e:
            self.logger.exception(f"Search failed: {e}")
            return self.format_error(str(e), query=query)

    async def search(self, query: str, num_results: int = 8, search_type: str = "general", domain: str = None) -> Dict[str, Any]:
        """
        Async search method with simplified interface.
        Returns: {"status": "success", "results": [...], "provider": "..."}
        """
        query = sanitize_search_query(query)
        try:
            stype = SearchType(search_type)
        except ValueError:
            stype = SearchType.GENERAL

        # Dynamic Academic intent detection (PCD Pillar 11)
        # Avoid redundant classification if domain is already known
        is_academic_query = (domain and domain != "general") or stype == SearchType.ACADEMIC or any(k in query.lower() for k in ["paper", "study", "analysis", "doi", "preprint", "experiment"])

        try:
            # 1. Academic Engines if requested/detected
            if is_academic_query:
                self.logger.info(f"Academic intent detected for: {query}")
                
                # TITAN UPGRADE: Parallel multi-source academic search
                academic_tasks = []
                
                # ArXiv
                academic_tasks.append(asyncio.to_thread(self.tool.search, query, SearchType.ACADEMIC, num_results, "arxiv"))
                
                # PubMed
                academic_tasks.append(asyncio.to_thread(self.tool.search, query, SearchType.ACADEMIC, num_results, "pubmed"))
                
                # bioRxiv (via ScholarNexus internal or direct if available)
                # For now, we'll try to use the ToolRegistry to get biorxiv if it exists
                try:
                    from backend.tools.tool_registry import REGISTRY
                    biorxiv_tool = REGISTRY.get("biorxiv_search")
                    if biorxiv_tool:
                        academic_tasks.append(asyncio.to_thread(biorxiv_tool, {"query": query, "limit": num_results}))
                except Exception:
                    pass

                self.logger.info(f"Launching parallel academic search across {len(academic_tasks)} sources")
                academic_results = await asyncio.gather(*academic_tasks, return_exceptions=True)
                
                all_academic_results = []
                providers_used = []
                
                for i, res in enumerate(academic_results):
                    if isinstance(res, Exception):
                        self.logger.warning(f"Academic source {i} failed: {res}")
                        continue
                    
                    # Handle different result formats (SearchResponse vs Registry dict)
                    if hasattr(res, 'results') and res.results:
                        all_academic_results.extend(res.results)
                        providers_used.append(getattr(res, 'metadata', {}).get('engine', 'unknown'))
                    elif isinstance(res, (dict, list)):
                        raw_results = res.get("result", []) if isinstance(res, dict) else res
                        if isinstance(raw_results, list) and raw_results:
                            for r in raw_results:
                                if isinstance(r, dict):
                                    all_academic_results.append(SearchResult(
                                        title=r.get("title", ""),
                                        url=r.get("url") or r.get("link", "#"),
                                        snippet=r.get("snippet") or r.get("abstract", ""),
                                        source=r.get("source", "biorxiv"),
                                        rank=r.get("rank", 0),
                                        search_type=SearchType.ACADEMIC,
                                        metadata=r,
                                        timestamp=datetime.now()
                                    ))
                            providers_used.append("biorxiv")

                if all_academic_results:
                    # Create a composite SearchResponse for formatting
                    composite_resp = SearchResponse(
                        query=query,
                        search_type=SearchType.ACADEMIC,
                        results=all_academic_results[:num_results*2], # Take a bit more for the composite
                        total_results=len(all_academic_results),
                        search_time=0.0,
                        metadata={"engines": providers_used},
                        timestamp=datetime.now()
                    )
                    return self._format_response(composite_resp, f"academic_ensemble({','.join(providers_used)})")

            # 2. Premium Search (SerpAPI)
            if SERPAPI_KEY:
                self.logger.info(f"Using SerpAPI for query: {query}")
                try:
                    result = await self._search_serpapi(query, num_results)
                    if result.get("status") == "success" and result.get("results"):
                        return result
                    self.logger.warning("SerpAPI returned no results, falling back")
                except Exception as e:
                    self.logger.error(f"SerpAPI failed: {e}, falling back")

            # 3. Fallback to HTML scraping
            self.logger.info(f"Falling back to DuckDuckGo for: {query}")
            response = await asyncio.to_thread(
                self.tool.search, query, SearchType.GENERAL, num_results, "duckduckgo"
            )
            
            if response.results:
                return self._format_response(response, "duckduckgo")
            
            # Final resort: Google HTML
            self.logger.info(f"Trying Google HTML for: {query}")
            response = await asyncio.to_thread(
                self.tool.search, query, SearchType.GENERAL, num_results, "google"
            )

            return self._format_response(response, "google_html")
        except Exception as e:
            self.logger.exception(f"Search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "provider": "none"
            }

    def _format_response(self, response: SearchResponse, provider: str) -> Dict[str, Any]:
        """Helper to format tool response to API dict."""
        return {
            "status": "success",
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                    "rank": r.rank,
                    "metadata": getattr(r, 'metadata', {})
                }
                for r in response.results
            ],
            "provider": provider,
            "total_results": response.total_results
        }

    async def _search_serpapi(self, query: str, num_results: int) -> Dict[str, Any]:
        """Search using SerpAPI."""
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": SERPAPI_KEY,
                "num": num_results,
                "engine": "google"
            }

            # Make async request
            if HAVE_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        data = await response.json()
            else:
                # Fallback to sync request in thread
                data = await asyncio.to_thread(
                    lambda: requests.get(url, params=params, timeout=30).json()
                )

            # Parse SerpAPI results
            results = []
            for i, item in enumerate(data.get("organic_results", [])[:num_results]):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("source", urlparse(item.get("link", "")).netloc),
                    "rank": i + 1
                })

            return {
                "status": "success",
                "results": results,
                "provider": "serpapi",
                "total_results": len(results)
            }
        except Exception as e:
            self.logger.exception(f"SerpAPI search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "provider": "serpapi"
            }

    async def search_images(self, query: str, num_results: int = 8) -> Dict[str, Any]:
        """
        Search for images related to the query.
        Returns list of image URLs with metadata.
        """
        try:
            # Try SerpAPI images endpoint first
            if SERPAPI_KEY:
                result = await self._search_images_serpapi(query, num_results)
                if result.get("status") == "success" and result.get("images"):
                    return result
            
            # Fallback: Use Google Images via HTML (limited)
            self.logger.info(f"Using Google Images HTML scraping for: {query}")
            images = await self._scrape_google_images(query, num_results)
            
            return {
                "status": "success",
                "images": images,
                "provider": "google_images_html",
                "query": query
            }
        except Exception as e:
            self.logger.exception(f"Image search failed: {e}")
            return {"status": "error", "error": str(e), "images": []}
    
    async def _search_images_serpapi(self, query: str, num_results: int) -> Dict[str, Any]:
        """Search images using SerpAPI."""
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": SERPAPI_KEY,
                "engine": "google_images",
                "num": num_results
            }
            
            if HAVE_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        data = await response.json()
            else:
                data = await asyncio.to_thread(
                    lambda: requests.get(url, params=params, timeout=30).json()
                )
            
            images = []
            for item in data.get("images_results", [])[:num_results]:
                images.append({
                    "url": item.get("original") or item.get("thumbnail"),
                    "thumbnail": item.get("thumbnail"),
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "link": item.get("link", ""),
                    "width": item.get("original_width"),
                    "height": item.get("original_height")
                })
            
            return {
                "status": "success",
                "images": images,
                "provider": "serpapi_images",
                "query": query
            }
        except Exception as e:
            self.logger.error(f"SerpAPI images failed: {e}")
            return {"status": "error", "error": str(e), "images": []}
    
    async def _scrape_google_images(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Fallback: Scrape Google Images HTML (limited results)."""
        images = []
        try:
            url = "https://www.google.com/search"
            params = {"q": query, "tbm": "isch", "hl": "en"}
            headers = {"User-Agent": self.tool._get_ua()}
            
            response = await asyncio.to_thread(
                lambda: requests.get(url, params=params, headers=headers, timeout=10)
            )
            
            if response.status_code == 200 and HAVE_BS4:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract image URLs from data attributes or img tags
                for img in soup.select("img[data-src]")[:num_results]:
                    src = img.get("data-src") or img.get("src")
                    if src and src.startswith("http"):
                        images.append({
                            "url": src,
                            "thumbnail": src,
                            "title": img.get("alt", ""),
                            "source": "Google Images"
                        })
                
                # Also try extracting from <a> tags with image links
                if len(images) < num_results:
                    for a in soup.select("a[href*='imgurl=']")[:num_results - len(images)]:
                        href = a.get("href", "")
                        # Extract imgurl parameter
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if "imgurl" in parsed:
                            img_url = parsed["imgurl"][0]
                            images.append({
                                "url": img_url,
                                "thumbnail": img_url,
                                "title": "",
                                "source": "Google Images"
                            })
                            
        except Exception as e:
            self.logger.warning(f"Google Images scraping failed: {e}")
        
        return images


# ----------------------------
# Globals / Convenience
# ----------------------------
web_search_tool = WebSearchTool()
beast_search = BeastWebSearch()

def search_web(query: str, search_type: str = "general", max_results: int = 50, engine: str = None) -> SearchResponse:
    """Search the web. Auto-selects SerpAPI if key is available, otherwise falls back to DDG/Google HTML."""
    # Auto-select best engine if not specified
    if engine is None:
        if SERPAPI_KEY:
            engine = "serpapi"
        else:
            engine = "duckduckgo"  # More reliable than Google HTML
    return web_search_tool.search(query, SearchType(search_type), max_results, engine)

def multi_engine_search(query: str, engines: List[str] = None, max_results: int = 10) -> Dict[str, SearchResponse]:
    engines = engines or ["google", "bing", "duckduckgo"]
    return {e: web_search_tool.search(query, SearchType.GENERAL, max_results, e) for e in engines}

def get_search_suggestions(query: str, n: int = 5) -> List[str]:
    return web_search_tool.search_suggestions(query, n)
