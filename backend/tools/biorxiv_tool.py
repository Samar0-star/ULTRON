import requests
import urllib.parse
from typing import Any, Dict, List, Optional


def get_paper_full_text(doi: str, max_pages: int = 10) -> Optional[str]:
    """
    Fetches the full text of a paper from bioRxiv given its DOI.
    Uses the bioRxiv public API.
    """
    if not doi:
        return None

    encoded_doi = urllib.parse.quote(doi)
    url = f"https://api.biorxiv.org/details/biorxiv/{encoded_doi}"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        collection = data.get("collection", [])
        if not collection:
            return None

        abstract = collection[0].get("abstract", "")
        title = collection[0].get("title", "")

        return f"Title: {title}\n\nAbstract:\n{abstract}"
    except Exception as e:
        print(f"Error fetching bioRxiv full text for {doi}: {e}")
        return None


def search_papers(query: str, limit: int = 10, server: str = "biorxiv") -> List[Dict[str, Any]]:
    """
    Searches recent preprints on bioRxiv/medRxiv matching query keywords.
    Returns a list of normalized paper dictionaries.
    """
    if not query or not str(query).strip():
        return []

    url = f"https://api.biorxiv.org/details/{server}/2024-01-01/2026-12-31/0"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        collection = data.get("collection", []) or []
        terms = [t.lower() for t in str(query).split() if len(t) > 2]
        matches: List[Dict[str, Any]] = []
        for item in collection:
            title = str(item.get("title") or "")
            abstract = str(item.get("abstract") or "")
            haystack = f"{title} {abstract}".lower()
            if not terms or any(t in haystack for t in terms):
                doi = item.get("doi", "")
                matches.append({
                    "id": doi or title[:32],
                    "doi": doi,
                    "title": title,
                    "abstract": abstract,
                    "authors": [a.strip() for a in str(item.get("authors") or "").split(";") if a.strip()],
                    "published_date": item.get("date", ""),
                    "url": f"https://doi.org/{doi}" if doi else "",
                    "server": server,
                    "source": server,
                })
                if len(matches) >= limit:
                    break
        return matches
    except Exception:
        return []
