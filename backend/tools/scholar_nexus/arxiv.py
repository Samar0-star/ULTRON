"""
ScholarArxiv - Async Arxiv API Client for ScholarNexus.
"""
import logging
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.tools.scholar_nexus.base import BaseScholarClient
from backend.tools.scholar_nexus.models import ScholarPaper, ScholarAuthor, ScholarSource

logger = logging.getLogger(__name__)

class ScholarArxiv(BaseScholarClient):
    """
    Integration for Arxiv API. Uses Atom feed format.
    """
    BASE_URL = "http://export.arxiv.org/api/query"

    async def search(self, query: str, limit: int = 10) -> List[ScholarPaper]:
        """
        Search Arxiv for papers.
        """
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        papers = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Arxiv API error: {response.status}")
                        return []
                    
                    xml_data = await response.text()
                    papers = self._parse_feed(xml_data)
        except Exception as e:
            logger.error(f"Failed to search Arxiv: {e}")
        
        return papers

    def _parse_feed(self, xml_data: str) -> List[ScholarPaper]:
        """
        Parse Arxiv Atom feed using ElementTree.
        """
        root = ET.fromstring(xml_data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.findall('atom:entry', namespace):
            try:
                # Basic info
                arxiv_id_full = entry.find('atom:id', namespace).text
                arxiv_id = arxiv_id_full.split('/abs/')[-1]
                title = entry.find('atom:title', namespace).text.replace('\n', ' ').strip()
                summary = entry.find('atom:summary', namespace).text.strip()
                published_str = entry.find('atom:published', namespace).text
                published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))

                # Authors
                authors = []
                for author_node in entry.findall('atom:author', namespace):
                    name = author_node.find('atom:name', namespace).text
                    authors.append(ScholarAuthor(name=name))

                # Links
                pdf_url = ""
                for link in entry.findall('atom:link', namespace):
                    if link.attrib.get('title') == 'pdf':
                        pdf_url = link.attrib.get('href')

                papers.append(ScholarPaper(
                    id=f"arxiv:{arxiv_id}",
                    source=ScholarSource.ARXIV,
                    title=title,
                    abstract=summary,
                    arxiv_id=arxiv_id,
                    authors=authors,
                    publication_date=published_dt,
                    year=published_dt.year,
                    pdf_url=pdf_url,
                    url=arxiv_id_full
                ))
            except Exception as e:
                logger.warning(f"Error parsing Arxiv entry: {e}")
                continue
        
        return papers

    async def get_details(self, paper_id: str) -> Optional[ScholarPaper]:
        """Fetch details by ID (id_list param)."""
        clean_id = paper_id.replace("arxiv:", "")
        params = {"id_list": clean_id}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    xml_data = await response.text()
                    results = self._parse_feed(xml_data)
                    return results[0] if results else None
        except Exception:
            return None

    async def get_citations(self, paper_id: str) -> List[ScholarPaper]:
        """
        Arxiv doesn't natively support citation lookup. 
        Will return empty list; ScholarS2 should handle this.
        """
        return []
