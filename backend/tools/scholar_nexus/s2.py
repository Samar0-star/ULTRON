"""
ScholarS2 - Async Semantic Scholar API Client for ScholarNexus.
"""
import logging
import aiohttp
from typing import List, Optional, Dict, Any
from backend.tools.scholar_nexus.base import BaseScholarClient
from backend.tools.scholar_nexus.models import ScholarPaper, ScholarAuthor, ScholarSource

logger = logging.getLogger(__name__)

class ScholarS2(BaseScholarClient):
    """
    Integration for Semantic Scholar API.
    Docs: https://api.semanticscholar.org/api-docs/graph
    """
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    # Fields to fetch for papers
    PAPER_FIELDS = "paperId,externalIds,url,title,abstract,venue,year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,authors"

    async def search(self, query: str, limit: int = 10) -> List[ScholarPaper]:
        """
        Search Semantic Scholar for papers with 'Godzilla-Tier' exponential backoff for 429s.
        """
        import asyncio
        import random
        import os
        
        # [GODZILLA FIX] Automatic Downscaling for Free-Tier
        api_key = os.environ.get("S2_API_KEY") or self.api_key
        if not api_key:
            # Free tier is extremely limited (1 request/sec). 
            # We force a small limit to reduce payload size and collision risk.
            original_limit = limit
            limit = min(limit, 5)
            if limit < original_limit:
                logger.info(f" [S2] Free-tier detected. Downscaling limit from {original_limit} -> {limit} to avoid 429.")

        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": self.PAPER_FIELDS
        }
        
        headers = {
            "User-Agent": "SVELResearchBot/2.0 (SVEL_CORE_MISSION Swarm; contact: admin@svel.ai)"
        }
        if api_key:
            headers["x-api-key"] = api_key

        # [STABILIZATION] High-Rigor Backoff
        max_retries = 5
        base_delay = 5.0
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status == 429:
                            # Calculate jittered exponential backoff: 5s, 10s, 20s, 40s...
                            delay = base_delay * (2 ** attempt) + random.uniform(1, 5)
                            logger.warning(f" [S2] Rate limited (429). Retrying in {delay:.2f}s... (Attempt {attempt+1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                            
                        if response.status != 200:
                            err_text = await response.text()
                            logger.error(f" [S2] API error {response.status}: {err_text[:200]}")
                            return []
                        
                        data = await response.json()
                        papers = []
                        for item in data.get("data", []):
                            papers.append(self._to_model(item))
                        
                        logger.info(f" [S2] Success: Found {len(papers)} papers for query.")
                        return papers
            except Exception as e:
                logger.error(f" [S2] Critical failure during search: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay)
                    continue
                return []
        
        logger.error(f" [S2] FAILED: Exhausted all {max_retries} retries for query: {query[:50]}...")
        return []

    def _to_model(self, data: Dict[str, Any]) -> ScholarPaper:
        """
        Convert S2 JSON to ScholarPaper model.
        """
        ext_ids = data.get("externalIds", {})
        
        authors = []
        for a in data.get("authors", []):
            authors.append(ScholarAuthor(
                name=a.get("name", "Unknown"),
                id=a.get("authorId")
            ))

        pdf_url = data.get("openAccessPdf", {}).get("url") if data.get("openAccessPdf") else None

        return ScholarPaper(
            id=f"s2:{data.get('paperId')}",
            source=ScholarSource.SEMANTIC_SCHOLAR,
            title=data.get("title", ""),
            abstract=data.get("abstract", "") or "",
            doi=ext_ids.get("DOI"),
            arxiv_id=ext_ids.get("ArXiv"),
            authors=authors,
            venue=data.get("venue"),
            year=data.get("year"),
            citation_count=data.get("citationCount", 0),
            influential_citations=data.get("influentialCitationCount", 0),
            url=data.get("url"),
            pdf_url=pdf_url,
            fields=data.get("fieldsOfStudy") or []
        )

    async def get_details(self, paper_id: str) -> Optional[ScholarPaper]:
        """Fetch full details by ID."""
        clean_id = paper_id.split(":")[-1]
        url = f"{self.BASE_URL}/paper/{clean_id}"
        params = {"fields": self.PAPER_FIELDS}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._to_model(data)
        except Exception:
            pass
        return None

    async def get_citations(self, paper_id: str) -> List[ScholarPaper]:
        """Fetch papers citing this paper."""
        clean_id = paper_id.split(":")[-1]
        url = f"{self.BASE_URL}/paper/{clean_id}/citations"
        params = {"fields": f"citingPaper({self.PAPER_FIELDS})", "limit": 20}
        
        papers = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("data", []):
                            if item.get("citingPaper"):
                                papers.append(self._to_model(item["citingPaper"]))
        except Exception:
            pass
        return papers
