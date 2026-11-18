"""
ScholarNexus Base Client - Abstract interface for scientific APIs.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from backend.tools.scholar_nexus.models import ScholarPaper

class BaseScholarClient(ABC):
    """
    Blueprint for all ScholarNexus integration clients.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[ScholarPaper]:
        """Search papers matching query."""
        pass

    @abstractmethod
    async def get_details(self, paper_id: str) -> Optional[ScholarPaper]:
        """Fetch full details for a specific paper."""
        pass

    @abstractmethod
    async def get_citations(self, paper_id: str) -> List[ScholarPaper]:
        """Fetch papers citing this paper."""
        pass
