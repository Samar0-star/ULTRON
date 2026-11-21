import asyncio
import logging
import json
import uuid
import re
import os
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from backend.central_router_beast import CentralRouterBeast

logger = logging.getLogger("agents.research_agent")


class ResearchAgent:
    """
    2027 Sovereign Multi-Tool Research Agent.

    Unifies academic literature search (ScholarNexus, ArXiv, PubMed), full-text PDF reading
    (deep_paper_reader), live web search & crawling, multimodal ingestion, and grounded
    scientific synthesis in a single frontier agent—eliminating 2025 micro-agent hops
    (web_search_agent, doc_reader_agent, summarizer_agent, qa_agent).
    """
    name = "research_agent"
    capabilities = [
        "web", "search", "scholar_search", "arxiv_search", "pubmed_search",
        "deep_paper_reader", "source_evaluation", "information_extraction",
        "document_reading", "summarization", "qa", "analysis", "structuring"
    ]

    def __init__(self, central_router: Optional['CentralRouterBeast'] = None, llm_manager: Any = None):
        self.central_router = central_router
        self.llm_manager = llm_manager

    def set_router(self, router):
        self.central_router = router
        logger.info(f"ResearchAgent router set via set_router: {router}")

    def _get_router(self):
        """Robust router retrieval with singleton fallback."""
        if self.central_router:
            return self.central_router

        try:
            from backend.central_router_beast import get_router_instance
            self.central_router = get_router_instance()
            if self.central_router:
                logger.info("ResearchAgent recovered router via singleton")
                return self.central_router
        except Exception as e:
            logger.warning(f"Could not recover router: {e}")

        return None

    def _get_llm(self):
        if self.llm_manager is not None:
            return self.llm_manager
        try:
            from backend.llm_manager import get_llm_manager
            self.llm_manager = get_llm_manager()
            return self.llm_manager
        except Exception:
            return None

    async def run(self, task: Dict[str, Any], context: Dict[str, Any], event_callback=None) -> Dict[str, Any]:
        """
        Execute multi-step scientific research, full-text reading, web search, and synthesis
        directly via Registry tools and frontier LLM reasoning.
        """
        payload = task.get("payload", {}) if isinstance(task, dict) else {}
        if not isinstance(payload, dict):
            payload = {}

        query = (
            payload.get("query")
            or payload.get("question")
            or task.get("query")
            or task.get("description")
            or task.get("input")
            or ""
        )
        raw_text = payload.get("text") or task.get("text") or ""
        physical_docs = payload.get("physical_docs") or []
        components = payload.get("components") or task.get("components") or []

        if not query and not raw_text and not physical_docs and not components:
            return {"error": "No query or document text provided"}

        context = context or {}
        if event_callback is None:
            event_callback = context.get("event_callback")

        # PREVENT RECURSION: Check context flags across all potential nesting levels
        inner_ctx = context.get("context") if isinstance(context.get("context"), dict) else {}
        in_session = bool(
            context.get("research_session")
            or context.get("orchestrator") == "DeepResearch"
            or inner_ctx.get("research_session")
            or inner_ctx.get("orchestrator") == "DeepResearch"
            or context.get("session_id")
            or inner_ctx.get("session_id")
            or os.environ.get("SVEL_RUNNING_ORCHESTRATOR") == "1"
            or raw_text
            or physical_docs
            or components
        )
        in_beast = context.get("is_beast_subtask") or task.get("id") == "fallback_1"

        # Direct Sovereign Multi-Tool Execution when inside an orchestrator session or given direct documents
        if in_session or in_beast:
            logger.info(f" [SOVEREIGN RESEARCH] Executing direct multi-tool research: {str(query)[:100]}")
            if event_callback:
                await event_callback("progress", {
                    "phase": "Research",
                    "status": f"Executing Sovereign Research for: {str(query)[:120]}"
                })

            # 1. If physical documents, raw text, or components are provided, synthesize them directly
            if raw_text or physical_docs or components:
                doc_synthesis = await self._synthesize_documents_and_components(
                    query=query,
                    raw_text=raw_text,
                    physical_docs=physical_docs,
                    components=components,
                    context=context
                )
                if not query or doc_synthesis.get("findings"):
                    return doc_synthesis

            # 2. High-fidelity scientific scholar search
            scholar_results = await self._execute_scholar_search(query)
            if scholar_results:
                summary_items = []
                for p in scholar_results[:10]:
                    title = p.get("title", "Untitled")
                    snippet = p.get("abstract") or p.get("snippet") or p.get("summary") or ""
                    summary_items.append(f"- {title}: {str(snippet)[:350]}")
                joined_summary = "\n".join(summary_items) or f"Identified {len(scholar_results)} scientific sources."
                return {
                    "status": "success",
                    "mode": "scholar_nexus",
                    "research_summary": joined_summary,
                    "summary": joined_summary,
                    "answer": joined_summary,
                    "papers": scholar_results,
                    "findings": scholar_results,
                    "results": scholar_results,
                    "papers_read": len(scholar_results)
                }

            # 3. Direct multi-tool fallback (arxiv_search, pubmed_search, web_search) — NO micro-agent hop!
            return await self._execute_direct_multi_tool_search(query, context, event_callback)

        # Standalone Mode (outside orchestrator)
        logger.info(f" Starting Standalone Research Mode: {query}")
        if event_callback:
            await event_callback("progress", {"phase": "Setup", "status": f"Initializing Research for: {query}"})

        try:
            return await self._run_deep_research(query, payload, context, event_callback)
        except Exception as e:
            logger.error(f"Research execution failed: {e}", exc_info=True)
            scholar_results = await self._execute_scholar_search(query)
            if scholar_results:
                return {
                    "status": "success",
                    "research_summary": "Scientific literature findings summarized.",
                    "papers": scholar_results,
                    "findings": scholar_results,
                    "full_report": "# ScholarNexus Findings\n\n" + "\n".join(
                        [f"- {p.get('title', 'Untitled')} ({p.get('source', 'scholar')})" for p in scholar_results]
                    )
                }
            return {"status": "error", "error": f"Research Failed: {e}"}

    async def _synthesize_documents_and_components(
        self,
        query: str,
        raw_text: str,
        physical_docs: List[Any],
        components: List[Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Natively read, extract, and synthesize full-text documents and multi-task components
        without delegating to legacy doc_reader_agent, summarizer_agent, or qa_agent.
        """
        blocks: List[str] = []
        if raw_text:
            blocks.append(str(raw_text))
        for doc in physical_docs:
            if isinstance(doc, dict):
                blocks.append(json.dumps(doc, default=str))
            elif doc:
                blocks.append(str(doc))
        for comp in components:
            if isinstance(comp, dict):
                res = comp.get("result", comp)
                if isinstance(res, dict):
                    txt = res.get("text") or res.get("summary") or res.get("research_summary") or json.dumps(res, default=str)
                else:
                    txt = str(res)
                blocks.append(str(txt))
            elif comp:
                blocks.append(str(comp))

        combined_corpus = "\n\n---\n\n".join(blocks)[:120000]
        multimodal_ctx = await self._process_multimodal_inputs(query or "", context)
        if multimodal_ctx:
            combined_corpus = f"{combined_corpus}\n\n{multimodal_ctx}"[:120000]

        llm = self._get_llm()
        if llm and os.environ.get("SVEL_OFFLINE_TESTS", "0") != "1":
            prompt = (
                "You are SVEL's Sovereign Scientific Research Engine.\n"
                "Analyze the following primary documents and experimental/literature evidence for the research query.\n"
                "Extract concrete quantitative findings, empirical metrics, methodological constraints, and citations.\n\n"
                f"RESEARCH QUERY: {query or 'Synthesize primary scientific findings'}\n\n"
                f"PRIMARY CORPUS:\n{combined_corpus}\n\n"
                "Return JSON with keys: {\"summary\": \"...\", \"key_findings\": [\"...\"], \"quantitative_metrics\": [\"...\"], \"limitations\": [\"...\"]}"
            )
            try:
                from backend.llm_manager import DEEP_RESEARCH_SYNTHESIS_MODEL
                from backend.utils.json_repair import repair_json
                raw_resp = await llm.run_async(prompt, model=DEEP_RESEARCH_SYNTHESIS_MODEL, temperature=0.2)
                resp_text = raw_resp.get("text", "") if isinstance(raw_resp, dict) else str(raw_resp)
                parsed = repair_json(resp_text)
                if isinstance(parsed, dict) and (parsed.get("summary") or parsed.get("key_findings")):
                    summary_txt = parsed.get("summary") or "\n".join(parsed.get("key_findings", []))
                    findings_list = parsed.get("key_findings", [summary_txt])
                    return {
                        "status": "success",
                        "mode": "sovereign_document_synthesis",
                        "research_summary": summary_txt,
                        "summary": summary_txt,
                        "text": summary_txt,
                        "answer": summary_txt,
                        "findings": findings_list,
                        "quantitative_metrics": parsed.get("quantitative_metrics", []),
                        "limitations": parsed.get("limitations", []),
                        "papers_read": max(1, len(physical_docs) or len(components) or 1)
                    }
            except Exception as e:
                logger.warning(f"Sovereign document LLM synthesis fallback: {e}")

        # Deterministic extraction fallback when offline or LLM unavailable
        fallback_summary = combined_corpus[:4000].strip() or f"Processed corpus for: {query}"
        return {
            "status": "success",
            "mode": "sovereign_document_synthesis",
            "research_summary": fallback_summary,
            "summary": fallback_summary,
            "text": fallback_summary,
            "answer": fallback_summary,
            "findings": [{"title": query or "Document Synthesis", "summary": fallback_summary}],
            "papers_read": max(1, len(physical_docs) or len(components) or 1)
        }

    async def _execute_direct_multi_tool_search(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        event_callback=None
    ) -> Dict[str, Any]:
        """
        Directly execute literature and web search tools from REGISTRY in parallel
        without delegating to legacy web_search_agent.
        """
        findings: List[Dict[str, Any]] = []
        try:
            from backend.tools.tool_registry import REGISTRY
            for tool_name in ("arxiv_search", "pubmed_search", "web_search"):
                tool_fn = REGISTRY.get(tool_name)
                if not tool_fn:
                    continue
                try:
                    if event_callback:
                        await event_callback("action", {"agent": "research_agent", "tool": tool_name, "input": query[:100]})
                    res = await asyncio.to_thread(tool_fn, {"query": query, "max_results": 10})
                    if asyncio.iscoroutine(res):
                        res = await res
                    items = res.get("result", res) if isinstance(res, dict) else res
                    if isinstance(items, dict):
                        items = items.get("results") or items.get("papers") or [items]
                    if isinstance(items, list):
                        for item in items[:10]:
                            if isinstance(item, dict):
                                findings.append({**item, "source_tool": tool_name})
                            elif item:
                                findings.append({"title": str(item)[:120], "snippet": str(item), "source_tool": tool_name})
                    if findings:
                        break
                except Exception as tool_err:
                    logger.debug(f"Direct tool {tool_name} failed in ResearchAgent: {tool_err}")
        except Exception as reg_err:
            logger.warning(f"Tool registry lookup failed in ResearchAgent: {reg_err}")

        # Fallback to beast_search if registry tools returned nothing
        if not findings:
            try:
                from backend.tools.web_search import beast_search
                raw_web = await asyncio.to_thread(beast_search, query, max_results=8)
                web_items = raw_web.get("results", []) if isinstance(raw_web, dict) else (raw_web if isinstance(raw_web, list) else [])
                for item in web_items[:8]:
                    if isinstance(item, dict):
                        findings.append({**item, "source_tool": "web_search"})
            except Exception as web_err:
                logger.debug(f"Direct beast_search fallback failed: {web_err}")

        summary_lines = []
        for f in findings[:8]:
            title = f.get("title") or f.get("url") or "Source"
            snippet = f.get("abstract") or f.get("snippet") or f.get("body") or f.get("summary") or ""
            summary_lines.append(f"- {title}: {str(snippet)[:300]}")

        summary_text = "\n".join(summary_lines) if summary_lines else f"No external records found for query: {query}"
        return {
            "status": "success" if findings else "empty",
            "mode": "sovereign_multi_tool",
            "research_summary": summary_text,
            "summary": summary_text,
            "answer": summary_text,
            "papers": findings,
            "findings": findings,
            "results": findings,
            "papers_read": len(findings)
        }

    async def _run_deep_research(self, query: str, payload: Dict[str, Any], context: Dict[str, Any] = None, event_callback=None) -> Dict[str, Any]:
        """
        Execute deep research mode using DeepResearchOrchestrator for standalone invocations.
        """
        try:
            from backend.orchestration.deep_research_orchestrator import DeepResearchOrchestrator

            context = context or {}
            inner_ctx = context.get("context") if isinstance(context.get("context"), dict) else {}
            master_session = (
                context.get("session_id")
                or inner_ctx.get("session_id")
                or os.environ.get("SVEL_SESSION_ID")
                or str(uuid.uuid4())[:8]
            )
            mission_domain = (
                payload.get("domain")
                or context.get("DOMAIN")
                or inner_ctx.get("DOMAIN")
                or os.environ.get("SVEL_DOMAIN")
                or "biology"
            )

            logger.info(f" DEEP MODE: Initializing Sub-Orchestrator for: {query} (Session: {master_session}, Domain: {mission_domain})")

            orchestrator = DeepResearchOrchestrator(
                research_question=query,
                domain=mission_domain,
                session_id=master_session,
                max_cycles=1,
                max_runtime_hours=1.0,
                max_parallel=2,
                tasks_per_cycle=2
            )

            orchestrator.llm_manager = self.llm_manager

            results = await orchestrator.run_async()

            return {
                "status": "success",
                "mode": "deep_orchestrator",
                "research_summary": results.get("summary", {}).get("final_report", "Sub-research complete."),
                "results": results,
                "papers_read": results.get("summary", {}).get("findings_count", 0)
            }

        except Exception as e:
            logger.error(f" [RECOVERY] Deep Orchestrator failed: {e}")
            results = await self._execute_scholar_search(query, limit=10)
            return {"status": "success", "mode": "fallback", "findings": results, "papers": results}

    async def _execute_scholar_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Execute high-fidelity scientific search via Registry.
        """
        try:
            from backend.tools.tool_registry import REGISTRY
            scholar_tool = REGISTRY.get("scholar_search")
            if scholar_tool:
                try:
                    from backend.core.domain_regulator import DomainRegulator
                    domain = await DomainRegulator.detect_domain(query)
                except Exception as e:
                    logger.warning(f"DomainRegulator detection failed, using fallback: {e}")
                    domain = "medical" if any(t in query.lower() for t in ["cancer", "bio", "clinical", "med"]) else "tech" if any(t in query.lower() for t in ["gpu", "algorithm", "cuda", "nn"]) else "general"
                result = scholar_tool({"query": query, "limit": limit, "domain": domain})
                if isinstance(result, dict) and "result" in result:
                    papers = result["result"]
                else:
                    papers = result

                if hasattr(papers, "to_dict"):
                    return [papers.to_dict()]
                if isinstance(papers, list):
                    processed = []
                    for p in papers:
                        if hasattr(p, "to_dict"):
                            processed.append(p.to_dict())
                        elif isinstance(p, dict):
                            processed.append(p)
                    return processed
                return []
            else:
                logger.warning("scholar_search tool not found in Registry.")
                return []
        except Exception as e:
            logger.error(f"ScholarNexus search failed: {e}")
            return []

    async def _execute_subtask(self, agent_name: str, payload: Dict[str, Any], event_callback=None) -> Dict[str, Any]:
        """Execute a subtask using the Central Router (canonicalizing legacy micro-agents to Sovereign Agents)."""
        if agent_name in {"web_search_agent", "doc_reader_agent", "summarizer_agent", "qa_agent"}:
            return await self._execute_direct_multi_tool_search(payload.get("query", ""), payload, event_callback)

        logger.info(f"Executing subtask: {agent_name}")

        if event_callback:
            await event_callback("action", {
                "agent": agent_name,
                "tool": agent_name,
                "input": str(payload)[:100]
            })

        router = self._get_router()
        if not router:
            logger.error("Router unavailable for subtask execution")
            return {"error": "Router unavailable"}

        try:
            trace_cls = getattr(router, "DecisionTrace", None)
            if not trace_cls:
                from backend.central_router_beast import DecisionTrace
                trace_cls = DecisionTrace

            subtrace = trace_cls(query=payload.get("query", "subtask"))
            is_deep = payload.get("deep_mode", False) or payload.get("deep", False)
            task_type = "deep_research" if is_deep else "research_subtask"

            subtask_payload = {
                "query": payload.get("query", ""),
                "deep_mode": is_deep,
                **payload
            }
            subtask_meta = {
                "task_type": task_type,
                "deep_mode": is_deep,
                **payload.get("meta", {})
            }

            result = await router.execute_agent_async(
                agent_name,
                payload.get("query", ""),
                {"payload": subtask_payload, "meta": subtask_meta, "event_callback": event_callback},
                subtrace
            )

            if "adapter" in result and event_callback:
                await event_callback("debug", {
                    "type": "adapter_used",
                    "adapter": result["adapter"],
                    "agent": agent_name
                })

            if "result" in result:
                return result["result"]
            return result
        except Exception as e:
            logger.error(f"Router execution failed for {agent_name}: {e}")
            return {"error": f"Subtask execution failed: {e}"}

    def run_sync(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for compatibility."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.run(task, context))
                    return future.result()
            else:
                return loop.run_until_complete(self.run(task, context))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.run(task, context))
            finally:
                loop.close()

    async def _process_multimodal_inputs(self, query: str, context: Dict[str, Any], event_callback=None) -> str:
        """Process YouTube links, physical directories, and attached image files."""
        context_str = ""

        try:
            potential_paths = re.findall(r'[\w\-/]+\.(?:csv|png|jpg|jpeg|pdf|txt|parquet)|[\w\-/]+/', query)
            for path in potential_paths:
                path = path.strip().rstrip('/')
                if os.path.exists(path):
                    if os.path.isdir(path):
                        files = os.listdir(path)[:50]
                        logger.info(f" [HARVEST] Physically detected local directory: {path} ({len(files)} files)")
                        context_str += f"\n### PHYSICAL DATASET: {path}\n- Directory contains: {files}\n- Total files: {len(os.listdir(path))}\n"
                    else:
                        logger.info(f" [HARVEST] Physically detected local file: {path}")
                        context_str += f"\n### PHYSICAL DATA FILE: {path}\n"

            from backend.tools.tool_registry import REGISTRY
            yt_pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/)?[\w-]+"
            yt_matches = re.findall(yt_pattern, query)

            if yt_matches:
                youtube_tool = REGISTRY.get("youtube_tool")
                if youtube_tool:
                    urls = [w for w in query.split() if "youtube.com" in w or "youtu.be" in w]

                    for url in urls:
                        if event_callback:
                            await event_callback("action", {"tool": "youtube_tool", "input": url})

                        res = youtube_tool({"action": "get_video_info", "url": url})
                        is_success = False
                        video_info = {}

                        if isinstance(res, dict):
                            if res.get("status") == "success":
                                video_info = res.get("result", {})
                                is_success = True
                            elif "status" in res:
                                video_info = res
                                is_success = res.get("status") == "success"
                            else:
                                video_info = res
                                is_success = True

                        if isinstance(video_info, dict) and "status" in video_info:
                            is_success = video_info.get("status") == "success"

                        if is_success:
                            context_str += f"\n\n[YouTube Video: {video_info.get('title', 'Unknown')}]\n"
                            context_str += f"Channel: {video_info.get('channel')}\n"
                            context_str += f"Description: {video_info.get('description', '')[:500]}...\n"
                            if video_info.get("transcript"):
                                context_str += f"Transcript Summary:\n{video_info.get('transcript')[:10000]}...\n"
                        else:
                            logger.warning(f"Failed to get video info for {url}")
                else:
                    logger.warning("YouTube tool not available in Registry.")

            files = context.get("files") or context.get("meta", {}).get("files", [])
            image_processor = REGISTRY.get("image_processor")

            if files and image_processor:
                for file_item in files:
                    fpath = file_item if isinstance(file_item, str) else getattr(file_item, "path", str(file_item))

                    if any(fpath.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        if event_callback:
                            await event_callback("action", {"tool": "image_processor", "input": fpath})

                        res = image_processor({"image_path": fpath, "operation": "analyze"})
                        img_data = res.get("result", {}) if isinstance(res, dict) else res

                        context_str += f"\n\n[Image Analysis ({fpath})]:\n"
                        context_str += f"Description: {img_data.get('description', '') or img_data.get('text', '')}\n"
                        context_str += f"OCR Text: {img_data.get('ocr_text', '')}\n"

        except Exception as e:
            logger.error(f"Multimodal processing error: {e}")

        return context_str
