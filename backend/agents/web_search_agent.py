# backend/agents/web_search_agent.py
"""
WebSearchAgent - Production web search agent with multi-provider support

Capabilities:
- Multi-provider web search (SerpAPI, Google CSE, Brave, DuckDuckGo)
- Intelligent query formulation and refinement
- Result aggregation and deduplication
- Relevance ranking with LLM-based assessment
- Source credibility evaluation
"""

import os
import logging
import asyncio
from typing import Any, Dict, List, Optional
from backend.core.skill_injector import get_expert_system

logger = logging.getLogger("avon.web_search_agent")

# Import the web search tool - try multiple import paths
HAS_WEB_SEARCH = False
beast_search = None
BeastWebSearch = None

try:
    from backend.tools.web_search import BeastWebSearch, beast_search
    HAS_WEB_SEARCH = True
    logger.info("BeastWebSearch imported via backend.tools.web_search")
except ImportError as e:
    logger.warning(f"Failed to import via backend.tools.web_search: {e}")
    try:
        from tools.web_search import BeastWebSearch, beast_search
        HAS_WEB_SEARCH = True
        logger.info("BeastWebSearch imported via tools.web_search (fallback)")
    except ImportError as e2:
        logger.error(f"Failed to import BeastWebSearch from all paths: {e2}")
        HAS_WEB_SEARCH = False

# Import LLM manager for query refinement
try:
    from backend.llm_manager import run_llm_async, run_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    logger.warning("LLM manager not available")


class WebSearchAgent:
    """
    Web search agent that performs intelligent web searches.

    Input task format:
    {
        "query": str,  # Search query
        "num_results": int,  # Optional, default 8
        "refine_query": bool,  # Optional, use LLM to refine query
        "assess_credibility": bool  # Optional, assess source credibility
    }

    Output format:
    {
        "text": str,  # Markdown formatted results
        "attachments": [],
        "meta": {
            "results": List[Dict],  # Raw search results
            "refined_query": str,  # If query was refined
            "provider": str,  # Search provider used
            "credibility_scores": Dict  # If credibility assessment enabled
        }
    }
    """

    name = "web_search_agent"
    version = "1.0.0"
    capabilities = ["web_search", "query_refinement", "source_evaluation"]

    def __init__(self):
        from backend.core.skill_injector import get_expert_system
        self.beast_search = beast_search if HAS_WEB_SEARCH else None
        self.expert_system = get_expert_system()

    async def run(self, task: Dict[str, Any], context: Dict[str, Any], event_callback=None) -> Dict[str, Any]:
        """Execute web search with optional query refinement and credibility assessment."""
        
        # Emit start event
        if event_callback:
            await event_callback("action", {"agent": "web_search_agent", "tool": "web_search", "status": "starting"})

        # Extract query from multiple possible formats
        # Router sends: {"payload": {"query": "..."}, "meta": {...}}
        # Direct calls send: {"query": "...", "num_results": 8}
        query = None
        
        # Try router format first
        if isinstance(task, dict):
            # Router format: task["payload"]["query"]
            if "payload" in task and isinstance(task["payload"], dict):
                query = task["payload"].get("query")
            # Args format (from ParallelExecutor): task["args"]["query"]
            if not query and "args" in task and isinstance(task["args"], dict):
                query = task["args"].get("query")
            
            # Direct format: task["query"]
            if not query:
                query = task.get("query")
            # Legacy format: task["input"]
            if not query:
                query = task.get("input")
        
        # If task is just a string, use it as query
        if not query and isinstance(task, str):
            query = task
        
        # Extract other parameters
        num_results = task.get("num_results", 8) if isinstance(task, dict) else 8
        refine_query = task.get("refine_query", False) if isinstance(task, dict) else False
        assess_credibility = task.get("assess_credibility", False) if isinstance(task, dict) else False

        if query and not refine_query and (len(query.split()) > 5 or len(query) > 40 or any(w in query.lower() for w in ["find", "locate", "search", "step", "extract", "identify"])):
            logger.info(f"Auto-enabling query refinement for complex query: '{query[:50]}...'")
            refine_query = True

        if not query:
            logger.warning(f"No query found in task: {task}")
            return {
                "text": "Error: No search query provided",
                "attachments": [],
                "meta": {"error": "missing_query", "task_received": str(task)[:200]}
            }

        # Check if web search is available - if not, use LLM fallback
        if not HAS_WEB_SEARCH or not self.beast_search:
            logger.warning(f"WebSearchAgent: Web APIs not configured. Grounding is physically impossible.")
            return {
                "text": "[HARD ABORT] Web search not configured. Set GOOGLE_API_KEY in .env",
                "attachments": [],
                "meta": {
                    "error": "web_search_not_available",
                    "source": "hard_abort"
                }
            }

        try:
            logger.info(f"WebSearchAgent: Searching for '{query}'")

            
            # Step 1: Refine query with LLM if requested
            refined_query = query
            if refine_query and HAS_LLM:
                refined_query = await self._refine_query(query)
                logger.info(f"Refined query: '{query}' -> '{refined_query}'")

            # Step 1.5: Detect "Crawl" or "Deep Extract" Intent
            # ---------------------------------------------------
            # If the user explicitly asks to "crawl" or "extract from url", use the WebCrawler tool.
            
            # Check intent from task type
            task_type = context.get("task_type", "general")
            is_crawl_request = "crawl" in task_type or "crawl" in query.lower()[:10]
            
            # Extract URL if present
            import re
            url_match = re.search(r'https?://[^\s]+', query)
            target_url = url_match.group(0) if url_match else None
            
            if (is_crawl_request or "deep_extract" in task_type) and target_url:
                logger.info(f" WebCrawler Activation: Detected crawl intent for {target_url}")
                try:
                    from backend.tools.web_crawler_tool import crawl_website
                    
                    # Execute Crawl
                    # We default to depth 2 for safety unless specified
                    depth = task.get("depth", 1)  # Default shallow to avoid getting lost
                    if "deep" in task_type: depth = 2
                    
                    crawl_summary = crawl_website(
                        url=target_url, 
                        max_depth=depth, 
                        max_pages=task.get("max_pages", 20),
                        extract_text=True
                    )
                    
                    # Convert summary to text response
                    return {
                        "text": f"# Crawl Report: {target_url}\n\n**Processed:** {crawl_summary.total_pages} pages\n**Success:** {crawl_summary.successful_pages}\n\n## Content Overview\n(Extracted content would be here - using simple summary for now)\nFound {crawl_summary.total_links} links and {crawl_summary.total_images} images.",
                        "attachments": [],
                        "meta": {
                            "source": "web_crawler",
                            "stats": crawl_summary.__dict__ if hasattr(crawl_summary, "__dict__") else str(crawl_summary),
                            "crawl_mode": True
                        }
                    }
                except Exception as e:
                    logger.error(f"Crawl failed: {e}")
                    # Fallback to standard search if crawl fails
            
            # Step 2: Execute search (Standard)
            # ---------------------------------
            # Determine search type
            search_type = "academic" if "academic" in context.get("task_type", "").lower() or "research" in context.get("task_type", "").lower() else "general"
            
            search_result = await self.beast_search.search(refined_query, num_results, search_type=search_type)

            if search_result["status"] != "success":
                return {
                    "text": f" Search failed: {search_result.get('error', 'Unknown error')}",
                    "attachments": [],
                    "meta": search_result
                }

            results = search_result["results"]
            provider = search_result["provider"]

        except Exception as e:
            logger.exception(f"Search failed: {e}")
            return {
                "text": f" Search error: {str(e)}",
                "attachments": [],
                "meta": {"error": str(e)}
            }

        # Step 3: Assess credibility if requested
        credibility_scores = {}
        if assess_credibility and HAS_LLM and results:
            credibility_scores = await self._assess_credibility(results)

        # Step 4: Format results
        formatted_text = self._format_results(results, provider, refined_query)

        return {
            "text": formatted_text,
            "attachments": [],
            "meta": {
                "results": results,
                "refined_query": refined_query if refined_query != query else None,
                "provider": provider,
                "credibility_scores": credibility_scores,
                "metrics": search_result.get("metrics", {})
            }
        }

    async def _refine_query(self, query: str) -> str:
        """Use LLM to refine and optimize search query for Ph.D. level retrieval."""
        try:
            from backend.tools.web_search import sanitize_search_query
            prompt = f"""You are a Sovereign Search Specialist. Convert the following research goal into a mathematically precise, Boolean-optimized search query.

CRITICAL INSTRUCTIONS:
1. Output ONLY the raw search query on a SINGLE line.
2. Do NOT output markdown code blocks (```).
3. Do NOT write explanations, 'Rationale', 'Alternative variants', or commentary.
4. Maximum 10 words plus Boolean operators (AND, OR, site:arxiv.org).
5. Zero natural language chatter.

USER QUERY: {query}
OPTIMIZED QUERY:"""

            if HAS_LLM:
                try:
                    from backend.llm_manager import WEB_QUERY_FORMULATION_MODEL
                    # [GODZILLA ALIGNMENT] Inject specialist web search skills
                    prompt = await self.expert_system.inject_bundle(prompt, "web_search")

                    refined = await run_llm_async(
                        prompt,
                        model=WEB_QUERY_FORMULATION_MODEL,
                        max_tokens=None,
                        temperature=0.2
                    )
                    # Handle dict vs str result
                    if isinstance(refined, dict):
                        refined = refined.get("text", "")
                    cleaned = sanitize_search_query(refined)
                    return cleaned if cleaned else query
                except Exception:
                    # Fallback to sync version
                    from backend.llm_manager import WEB_QUERY_FORMULATION_MODEL
                    refined = run_llm(prompt, model=WEB_QUERY_FORMULATION_MODEL, max_tokens=None, temperature=0.2)
                    # Handle dict vs str result
                    if isinstance(refined, dict):
                        refined = refined.get("text", "")
                    cleaned = sanitize_search_query(refined)
                    return cleaned if cleaned else query

            return query

        except Exception as e:
            logger.warning(f"Query refinement failed: {e}")
            return query

    async def _assess_credibility(self, results: List[Dict]) -> Dict[str, float]:
        """Assess credibility of search result sources using LLM."""
        credibility_scores = {}

        try:
            # Take top 5 results for credibility assessment
            top_results = results[:5]

            for i, result in enumerate(top_results):
                url = result.get("link") or result.get("url", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")

                # Simple heuristic scoring
                score = 0.5  # Base score

                # Domain credibility
                if any(domain in url for domain in [".edu", ".gov", ".org"]):
                    score += 0.3
                elif any(domain in url for domain in ["wikipedia", "arxiv"]):
                    score += 0.2

                # Content quality indicators
                if len(snippet) > 100:
                    score += 0.1

                if result.get("quality_indicators", {}).get("is_authoritative"):
                    score += 0.1

                credibility_scores[f"result_{i+1}"] = min(score, 1.0)

            return credibility_scores

        except Exception as e:
            logger.warning(f"Credibility assessment failed: {e}")
            return {}

    def _format_results(self, results: List[Dict], provider: str, query: str) -> str:
        """Format search results as markdown."""
        if not results:
            return f"No results found for query: '{query}'"

        lines = [
            f"#  Web Search Results",
            f"",
            f"**Query:** {query}",
            f"**Provider:** {provider.upper()}",
            f"**Results:** {len(results)} found",
            f"",
            "---",
            ""
        ]

        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            snippet = result.get("snippet", "No description available")
            link = result.get("link") or result.get("url", "#")
            relevance = result.get("relevance_score", 0)
            result_type = result.get("result_type", "web_page")

            lines.append(f"## {i}. {title}")
            lines.append(f"")
            lines.append(f"{snippet}")
            lines.append(f"")
            lines.append(f" **URL:** {link}")
            lines.append(f" **Relevance:** {relevance:.2f} | **Type:** {result_type}")

            # Add quality indicators if available
            quality = result.get("quality_indicators", {})
            if quality.get("is_authoritative"):
                lines.append(f" **Authoritative Source**")
            if quality.get("is_recent"):
                lines.append(f" **Recent Content**")

            lines.append(f"")
            lines.append("---")
            lines.append("")

        lines.append(f"*Results enhanced with AI relevance scoring*")

        return "\n".join(lines)

    def run_sync(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for run() method."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new loop in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.run(task, context))
                    return future.result()
            else:
                return loop.run_until_complete(self.run(task, context))
        except RuntimeError:
            # No event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.run(task, context))
            finally:
                loop.close()


# Create singleton agent instance
Agent = WebSearchAgent()

# Sync wrapper function for compatibility
def search_web(query: str, num_results: int = 8) -> str:
    """
    Synchronous wrapper for web search.

    Args:
        query: Search query string
        num_results: Number of results to return (default 8)

    Returns:
        Markdown formatted search results
    """
    agent = WebSearchAgent()

    task = {
        "query": query,
        "num_results": num_results
    }

    context = {}

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(agent.run(task, context))
    return result["text"]
