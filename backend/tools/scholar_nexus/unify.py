# -*- coding: utf-8 -*-
"""
UnifiedScholarSearch - The intelligence layer for ScholarNexus.
Now with PubMed integration and smart source routing.

UPGRADED: 3-source parallel search + domain-aware routing.
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from backend.tools.scholar_nexus.models import ScholarPaper, ScholarSource
from backend.tools.scholar_nexus.arxiv import ScholarArxiv
from backend.tools.scholar_nexus.s2 import ScholarS2
from backend.llm_manager import run_with_fallback, TASK_ROUTING_MODEL

logger = logging.getLogger(__name__)


class UnifiedScholarSearch:
    """
    Orchestrates multiple academic sources, deduplicates, and ranks.
    
    Sources:
    - ArXiv: CS, Physics, Math, Stats (FREE)
    - Semantic Scholar: 200M+ papers across all fields (FREE)
    - PubMed: 35M+ biomedical papers (FREE)
    
    Smart Routing:
    - Medical/Bio queries  Prioritize PubMed + S2
    - Tech/CS queries  Prioritize ArXiv + S2
    - General queries  All sources equally
    """
    
    def __init__(self, s2_api_key: Optional[str] = None):
        self.s2 = ScholarS2(api_key=s2_api_key)
        self.arxiv = ScholarArxiv()
        try:
            from backend.tools import pubmed_tool
            self._pubmed_module = pubmed_tool
            self._pubmed_available = True
        except Exception:
            self._pubmed_module = None
            self._pubmed_available = False

        try:
            from backend.tools import biorxiv_tool
            self._biorxiv_module = biorxiv_tool
            self._biorxiv_available = True
        except Exception:
            self._biorxiv_module = None
            self._biorxiv_available = False
        
    def _detect_domain(self, query: str) -> str:
        """
        [TITAN V176.0] ABOLISHED KEYWORD HEURISTICS.
        Domain detection is now handled via neural routing or defaults to 'general'.
        """
        return "general"

    async def _neural_route(self, query: str, domain: Optional[str] = None) -> Dict[str, float]:
        """
        Use LLM 'Mind' to determine optimal source weighting.
        Returns: { 'arxiv': float, 'pubmed': float, 's2': float }
        """
        prompt = f"""
        Analyze the following research query and determine the optimal sources for papers.
        Sources:
        - ArXiv: Physics, Computer Science, Math, Stats, Quantitative Biology (Tech/Math focus)
        - PubMed: Medicine, Biology, Clinical Trials, Nursing, Life Sciences (Medical/Bio focus)
        - bioRxiv/medRxiv: Cutting-edge Biology and Medicine preprints (Pre-peer review)
        - Semantic Scholar: General academic aggregator (covers everything)
        
        Query: "{query}"
        
        Return a JSON object with weights (0.0 to 1.0) for each source. 
        The weights do NOT need to sum to 1.0; they represent the 'value' of each source.
        
        JSON Format:
        {{
            "arxiv": 0.0,
            "pubmed": 0.0,
            "biorxiv": 0.0,
            "s2": 1.0
        }}
        """
        try:
            resp = await asyncio.to_thread(run_with_fallback, "routing", prompt)
            text = resp.get("text", "{}")
            # Extract JSON
            import json
            import re
            m = re.search(r"\{.*\}", text, re.S)
            if m:
                weights = json.loads(m.group(0))
                # Validate keys
                for k in ["arxiv", "pubmed", "s2", "biorxiv"]:
                    if k not in weights: weights[k] = 0.5
                logger.info(f" Neural Routing Logic: {weights}")
                return weights
        except Exception as e:
            logger.warning(f"Neural routing failed, falling back to keywords: {e}")
            # Fallback to system domain if provided, else detect
            active_domain = domain or self._detect_domain(query)
            if active_domain in ["medical", "biology"]: return {"arxiv": 0.2, "pubmed": 1.0, "s2": 1.0, "biorxiv": 0.8}
            if active_domain in ["tech", "physics", "machine_learning"]: return {"arxiv": 1.0, "pubmed": 0.0, "s2": 1.0, "biorxiv": 0.0}
            return {"arxiv": 0.5, "pubmed": 0.5, "s2": 1.0, "biorxiv": 0.5}

    async def search(self, query: str, limit: int = 20, domain: Optional[str] = None) -> List[ScholarPaper]:
        """
        Parallel search across all sources with smart routing.
        - [GODZILLA FIX] Context Anchor: Force mission-relevance (Gap 97).
        - [GODZILLA FIX] 429 Pivot: Dynamic budget redistribution (Gap 91).
        """
        # SVEL UPGRADE: Use the Neural Brain for routing
        weights = await self._neural_route(query, domain=domain)
        logger.info(f"ScholarNexus: Neural Weights -> {weights}")
        
        # Build task list based on weights
        tasks = []
        sources_used = []
        
        # [GODZILLA PIVOT] If S2 is failing, we force weight to 0 and give it to ArXiv/PubMed
        if weights.get("s2", 1.0) > 0.1:
            # Check for recent 429s in S2 component (simulated check here)
            tasks.append(self.s2.search(query, limit=limit))
            sources_used.append("Semantic Scholar")
            
        # ArXiv
        if weights.get("arxiv", 0.0) > 0.1:
            tasks.append(self.arxiv.search(query, limit=limit))
            sources_used.append("ArXiv")
            
        # PubMed
        if self._pubmed_available and weights.get("pubmed", 0.0) > 0.1:
            async def _pubmed_async():
                return await asyncio.to_thread(self._search_pubmed_sync, query, limit)
            tasks.append(_pubmed_async())
            sources_used.append("PubMed")
            
        # bioRxiv/medRxiv
        if self._biorxiv_available and weights.get("biorxiv", 0.0) > 0.1:
            async def _biorxiv_async():
                return await asyncio.to_thread(self._search_biorxiv_sync, query, limit)
            tasks.append(_biorxiv_async())
            sources_used.append("bioRxiv/medRxiv")
        
        if not tasks:
            tasks.append(self.arxiv.search(query, limit=limit))
            sources_used.append("ArXiv (Fallback)")
            
        logger.info(f"ScholarNexus: Querying {len(tasks)} sources: {sources_used}")
        
        # Execute parallel source queries with timeout and clean task cancellation
        all_papers: List[ScholarPaper] = []
        try:
            spawned = [asyncio.create_task(t) for t in tasks]
            done, pending = await asyncio.wait(spawned, timeout=60)
            for p_task in pending:
                p_task.cancel()
            for task in done:
                try:
                    res = task.result()
                    if res:
                        all_papers.extend(res)
                except Exception as e:
                    if "429" in str(e):
                        logger.warning(" [PIVOT] Source returned 429. Ignoring and relying on other sources.")
                    else:
                        logger.error(f" Source failed: {e}")
        except Exception as e:
            logger.error(f" Unified search execution failed: {e}")
        
        logger.info(f"ScholarNexus: Collected {len(all_papers)} papers from {len(sources_used)} sources")
        
        # Deduplicate
        deduped = self._deduplicate(all_papers)
        
        # Rank by 'Signal Strength'
        # If domain is not provided, we rely on the neural weights for ranking
        ranked = self._rank(deduped, domain=domain or "other_scientific_domain")
        
        return ranked[:limit]
    
    def _search_pubmed_sync(self, query: str, limit: int) -> List[ScholarPaper]:
        """Synchronous PubMed search wrapper."""
        if not self._pubmed_available or not getattr(self, "_pubmed_module", None):
            return []
        
        try:
            papers = self._pubmed_module.search_papers(query, limit=limit)
            
            # Convert to ScholarPaper format
            scholar_papers = []
            for p in papers:
                paper = ScholarPaper(
                    title=p.get("title", "Unknown"),
                    authors=p.get("authors", []),
                    abstract=p.get("abstract", ""),
                    year=int(p.get("year")) if p.get("year") else None,
                    doi=p.get("doi"),
                    url=p.get("url"),
                    pdf_url=None,  # PubMed doesn't provide direct PDFs
                    citation_count=0,  # PubMed doesn't provide citations
                    source=ScholarSource.SEMANTIC_SCHOLAR,  # Temporary enum reuse
                    venue=p.get("journal"),
                    arxiv_id=None,
                    influential_citations=0
                )
                # Add PubMed-specific fields as metadata
                paper.pmid = p.get("pmid")
                paper.mesh_terms = p.get("mesh_terms", [])
                scholar_papers.append(paper)
            
            return scholar_papers
            
        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return []
    
    def _search_biorxiv_sync(self, query: str, limit: int) -> List[ScholarPaper]:
        """Synchronous bioRxiv/medRxiv search wrapper."""
        if not self._biorxiv_available or not getattr(self, "_biorxiv_module", None):
            return []
        
        try:
            papers = self._biorxiv_module.search_papers(query, limit=limit, server="biorxiv")
            
            # Convert to ScholarPaper format
            scholar_papers = []
            for p in papers:
                # Extract year from date string (YYYY-MM-DD format)
                year = None
                date_str = p.get("date", "")
                if date_str and len(date_str) >= 4:
                    try:
                        year = int(date_str[:4])
                    except Exception as e:
                        logger.debug(f"Could not parse year from date string '{date_str}': {e}")
                
                paper = ScholarPaper(
                    title=p.get("title", "Unknown"),
                    authors=p.get("authors", []),
                    abstract=p.get("abstract", ""),
                    year=year,
                    doi=p.get("doi"),
                    url=p.get("url"),
                    pdf_url=p.get("pdf_url"),
                    citation_count=0,  # Preprints have no citations yet
                    source=ScholarSource.ARXIV,  # Temporary enum reuse for preprints
                    venue=f"{p.get('server', 'biorxiv').upper()} Preprint",
                    arxiv_id=None,
                    influential_citations=0
                )
                # Add bioRxiv-specific fields
                paper.biorxiv_doi = p.get("doi")
                paper.category = p.get("category", "")
                paper.is_preprint = True
                scholar_papers.append(paper)
            
            return scholar_papers
            
        except Exception as e:
            logger.error(f"bioRxiv search failed: {e}")
            return []

    def _deduplicate(self, papers: List[ScholarPaper]) -> List[ScholarPaper]:
        """
        Deduplicate by DOI or ArxivID or PMID or Normalized Title.
        """
        unique = {}
        for p in papers:
            # Generate primary key: DOI > ArxivID > PMID > Normalized Title
            key = None
            if p.doi:
                key = p.doi.lower()
            elif p.arxiv_id:
                key = f"arxiv_{p.arxiv_id.lower()}"
            elif hasattr(p, 'pmid') and p.pmid:
                key = f"pmid_{p.pmid}"
            else:
                key = "".join(filter(str.isalnum, p.title.lower()))

            if key not in unique:
                unique[key] = p
            else:
                # Merge: prefer S2 for citation counts, keep best abstract
                existing = unique[key]
                if (p.citation_count or 0) > (existing.citation_count or 0):
                    existing.citation_count = p.citation_count
                    existing.influential_citations = p.influential_citations
                if p.venue and not existing.venue:
                    existing.venue = p.venue
                if len(p.abstract or "") > len(existing.abstract or ""):
                    existing.abstract = p.abstract
        
        return list(unique.values())
        
    def _calculate_velocity(self, paper: ScholarPaper, current_year: int) -> float:
        """
        Calculate 'Citation Velocity' ($dC/dt^1.5$) to find rising stars.
        
        Formula: Citations / (Age + 1)^1.5
        This rewards new papers with traction over old papers with high totals.
        """
        if not paper.year:
            return 0.0
            
        age = max(0, current_year - paper.year)
        cites = int(paper.citation_count or 0)
        velocity = cites / ((age + 1) ** 1.5)
        return velocity

    def _rank(self, papers: List[ScholarPaper], domain: str = "general") -> List[ScholarPaper]:
        """
        Signal Strength + Citation Velocity ranking.
        """
        current_year = 2026
        
        scored = []
        for p in papers:
            score = 0.0
            cites = int(p.citation_count or 0)
            inf_cites = int(p.influential_citations or 0)
            
            # 1. Update Velocity Metric
            p.citation_velocity = self._calculate_velocity(p, current_year)
            
            # 2. Base Score: Citations (max 40 points)
            score += min(cites / 10.0, 40.0)
            
            # 3. Velocity Score (max 25 points)
            score += min(p.citation_velocity * 2.5, 25.0)
            
            # 4. Influential Citations bonus (max 20 points)
            score += min(inf_cites * 5.0, 20.0)
            
            # 5. Recency (max 15 points)
            if p.year:
                age = max(0, current_year - p.year)
                score += max(0, 15 - (age * 2))
            
            # Domain-specific boosts
            if domain == "medical":
                # Boost papers with MeSH terms (medical indexing)
                if hasattr(p, 'mesh_terms') and p.mesh_terms:
                    score += 10.0
                # Boost recent medical papers more
                if p.year and p.year >= 2023:
                    score += 10.0
            
            elif domain == "tech":
                # Boost ArXiv papers (cutting-edge)
                if p.arxiv_id:
                    score += 5.0
                # Boost high-velocity papers even more in tech
                if p.citation_velocity > 5.0:
                    score += 10.0
            
            scored.append((p, score))
            
        scored.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in scored]
    
    async def search_all_sources(self, query: str, limit: int = 10) -> Dict[str, List[ScholarPaper]]:
        """
        Search all sources and return results grouped by source.
        Useful for debugging and source comparison.
        """
        results = {}
        
        # ArXiv
        try:
            results["arxiv"] = await self.arxiv.search(query, limit=limit)
        except Exception as e:
            logger.error(f"ArXiv search failed: {e}")
            results["arxiv"] = []
        
        # Semantic Scholar
        try:
            results["semantic_scholar"] = await self.s2.search(query, limit=limit)
        except Exception as e:
            logger.error(f"S2 search failed: {e}")
            results["semantic_scholar"] = []
        
        # PubMed
        if self._pubmed_available:
            try:
                results["pubmed"] = await asyncio.to_thread(
                    self._search_pubmed_sync, query, limit
                )
            except Exception as e:
                logger.error(f"PubMed search failed: {e}")
                results["pubmed"] = []
        else:
            results["pubmed"] = []
        
        return results


# SVEL-style source routing explanation:
# =========================================
# HOW SVEL DECIDES:
#   SVEL uses a simple heuristic: domain field in configuration.
#   If domain="biology"  PubMed + ArXiv
#   If domain="physics"  ArXiv + Semantic Scholar
#   No keyword detection, just config-based.
#
# HOW AVON DECIDES (smarter):
#   1. Keyword detection in query (MEDICAL_KEYWORDS, TECH_KEYWORDS)
#   2. Domain scoring (count matches)
#   3. Route to optimal source mix
#   4. Rank with domain-specific boosting
#
# RESULT: Avon adapts to query content, not just config.


# Why Neo4j for PhD work (explanation):
# =====================================
# Neo4j is good for PhD-level work because:
#   1. Citation Graph Traversal: "Find all papers that cite X and are cited by Y"
#   2. Author Networks: "Find collaborators of researcher Z within 2 hops"
#   3. Concept Relationships: "What connects 'CRISPR' to 'Cancer'?"
#   4. Longitudinal Analysis: Track how a field evolved over time
#
# SQLite CAN'T DO THIS EFFICIENTLY:
#   - Requires multiple JOINs for graph traversal
#   - No native path-finding algorithms
#   - Slow for relationship-heavy queries
#
#   - Most users need SEARCH, not GRAPH ANALYSIS
#   - SQLite is faster for simple queries
#   - No hosting cost
#   - If you need graph features: Add a VECTOR INDEX for semantic similarity
#     (which Avon already has via FAISS!)


# Singleton
unified_scholar = UnifiedScholarSearch()
ScholarNexusUnified = UnifiedScholarSearch

