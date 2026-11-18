"""
ScholarNexus Models - Unified scientific data structures for Avon.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class ScholarSource(str, Enum):
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "s2"
    PUBMED = "pubmed"
    CROSSREF = "crossref"
    INTERNAL = "internal"


@dataclass
class ScholarAuthor:
    name: str
    id: Optional[str] = None
    affiliation: Optional[str] = None
    h_index: Optional[int] = None


@dataclass
class ScholarPaper:
    """
    Standardized scientific paper model for Avon's Nexus.
    Surpasses Ultron by tracking graph-specific metrics like citation velocity.
    """
    id: str = ""
    source: ScholarSource = ScholarSource.INTERNAL
    title: str = "Unknown"
    abstract: Optional[str] = ""

    # Identifiers
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None

    # Metadata
    authors: List[Any] = field(default_factory=list)
    venue: Optional[str] = None
    year: Optional[int] = None
    publication_date: Optional[datetime] = None

    # Research stats (superior to Ultron)
    citation_count: int = 0
    influential_citations: int = 0
    citation_velocity: float = 0.0  # Citations per year since pub

    # Content
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    full_text: Optional[str] = None

    # Enrichment
    fields: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = self.doi or self.arxiv_id or (self.title[:50] if self.title else "unknown")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value if hasattr(self.source, "value") else str(self.source),
            "title": self.title,
            "abstract": self.abstract,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "authors": [
                {"name": a.name, "id": getattr(a, "id", None)} if hasattr(a, "name") else {"name": str(a), "id": None}
                for a in (self.authors or [])
            ],
            "year": self.year,
            "citation_count": self.citation_count,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "fields": self.fields
        }
