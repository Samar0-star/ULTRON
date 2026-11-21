# -*- coding: utf-8 -*-
from __future__ import annotations

"""
SVEL Sovereign Tool Registry
- Defensive imports and instantiated tool bindings.
- Registers real technical tools (Literature Search, Full-Text PDF Extraction, Code Sandbox, Table/Image Processing).
"""

import logging
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger("tool_registry")


def _safe_import_callable(module_path: str, names: List[str]) -> Optional[Callable]:
    try:
        module = __import__(module_path, fromlist=["*"])
    except Exception:
        return None
    for n in names:
        if hasattr(module, n):
            attr = getattr(module, n)
            if callable(attr):
                return attr
    return None


def _scholar_search_wrapper(query_or_payload: Any, limit: int = 10, **kwargs) -> Any:
    """Unified callable wrapper for scholar_search / semantic_scholar."""
    if isinstance(query_or_payload, dict):
        query = query_or_payload.get("query") or query_or_payload.get("input") or ""
        limit = int(query_or_payload.get("limit") or query_or_payload.get("max_results") or limit)
    else:
        query = str(query_or_payload)
    try:
        from backend.tools.semantic_scholar_tool import SemanticScholarTool
        tool = SemanticScholarTool()
        return tool.search_papers(query, limit=limit)
    except Exception as e:
        logger.warning(f"scholar_search wrapper failed: {e}")
        return []


def _arxiv_search_wrapper(query_or_payload: Any, max_results: int = 20, **kwargs) -> Any:
    if isinstance(query_or_payload, dict):
        query = query_or_payload.get("query") or query_or_payload.get("input") or ""
        max_results = int(query_or_payload.get("max_results") or query_or_payload.get("limit") or max_results)
        as_envelope = True
    else:
        query = str(query_or_payload)
        as_envelope = False
    try:
        from backend.tools.arxiv_tool import search_arxiv
        papers = search_arxiv(query, max_results=max_results)
        return {"status": "success", "result": papers} if as_envelope else papers
    except Exception as e:
        logger.warning(f"arxiv_search wrapper failed: {e}")
        return {"status": "error", "error": str(e), "result": []} if as_envelope else []


def _pubmed_search_wrapper(query_or_payload: Any, limit: int = 20, **kwargs) -> Any:
    if isinstance(query_or_payload, dict):
        query = query_or_payload.get("query") or query_or_payload.get("input") or ""
        limit = int(query_or_payload.get("limit") or query_or_payload.get("max_results") or limit)
        as_envelope = True
    else:
        query = str(query_or_payload)
        as_envelope = False
    try:
        from backend.tools.pubmed_tool import search_papers
        papers = search_papers(query, limit=limit)
        return {"status": "success", "result": papers} if as_envelope else papers
    except Exception as e:
        logger.warning(f"pubmed_search wrapper failed: {e}")
        return {"status": "error", "error": str(e), "result": []} if as_envelope else []


def _biorxiv_search_wrapper(query_or_payload: Any, limit: int = 10, **kwargs) -> Any:
    if isinstance(query_or_payload, dict):
        query = query_or_payload.get("query") or query_or_payload.get("input") or ""
        limit = int(query_or_payload.get("limit") or query_or_payload.get("max_results") or limit)
        as_envelope = True
    else:
        query = str(query_or_payload)
        as_envelope = False
    try:
        from backend.tools.biorxiv_tool import search_papers
        papers = search_papers(query, limit=limit)
        return {"status": "success", "result": papers} if as_envelope else papers
    except Exception as e:
        logger.warning(f"biorxiv_search wrapper failed: {e}")
        return {"status": "error", "error": str(e), "result": []} if as_envelope else []


def _web_search_wrapper(query_or_payload: Any, max_results: int = 10, **kwargs) -> Any:
    if isinstance(query_or_payload, dict):
        try:
            from backend.tools.web_search import web_search_tool
            return web_search_tool.run(query_or_payload)
        except Exception as e:
            return {"status": "error", "error": str(e), "result": []}
    try:
        from backend.tools.web_search import search_web
        return search_web(str(query_or_payload), max_results=max_results)
    except Exception as e:
        logger.warning(f"web_search wrapper failed: {e}")
        return {"status": "error", "error": str(e), "result": []}


def _deep_paper_reader_wrapper(query_or_payload: Any, max_papers: int = 20, **kwargs) -> Any:
    if isinstance(query_or_payload, dict):
        query = query_or_payload.get("query") or query_or_payload.get("input") or ""
        max_papers = int(query_or_payload.get("max_papers") or query_or_payload.get("max_results") or max_papers)
        as_envelope = True
    else:
        query = str(query_or_payload)
        as_envelope = False
    try:
        from backend.tools.deep_paper_reader import deep_read_for_research
        papers = deep_read_for_research(query, max_papers=max_papers)
        return {"status": "success", "result": papers} if as_envelope else papers
    except Exception as e:
        logger.warning(f"deep_paper_reader wrapper failed: {e}")
        return {"status": "error", "error": str(e), "result": []} if as_envelope else []


def _doc_reader_wrapper(input_spec: Any, **kwargs) -> Dict[str, Any]:
    try:
        from backend.tools.doc_reader import DocReaderTool
        tool = DocReaderTool()
        spec = input_spec if isinstance(input_spec, dict) else {"path": str(input_spec)}
        return tool.run(spec)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _pdf_reader_wrapper(input_spec: Any, **kwargs) -> Dict[str, Any]:
    try:
        from backend.tools.pdf_reader import GodLevelPDFProcessor
        proc = GodLevelPDFProcessor(max_workers=2, enable_advanced_features=True)
        path = input_spec.get("path") or input_spec.get("query") if isinstance(input_spec, dict) else str(input_spec)
        res = proc.process_single_pdf(path)
        return {"status": "success" if "error" not in res else "error", "result": res, "text": res.get("content", {}).get("text", "")}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _image_processor_wrapper(input_spec: Any, **kwargs) -> Dict[str, Any]:
    try:
        from backend.tools.image_processor import image_processor
        path = input_spec.get("image_path") or input_spec.get("path") if isinstance(input_spec, dict) else input_spec
        res = image_processor.process_image(path)
        return {
            "status": "success",
            "result": {
                "text": res.text,
                "ocr_text": res.text,
                "description": res.text,
                "metadata": res.metadata,
                "image_shape": res.image_shape,
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "result": {}}


summarize_fn = _safe_import_callable("backend.tools.summarizer", ["summarize_text", "generate_summary", "summarize"])
qa_fn = _safe_import_callable("backend.tools.qa_engine", ["ask_question", "run_qa"])
table_extractor_fn = _safe_import_callable("backend.tools.table_extractor", ["extract_tables"])
code_executor_fn = _safe_import_callable("backend.tools.code_executor_tool", ["run_python_code"])
pdb_fetcher_fn = _safe_import_callable("backend.tools.pdb_fetcher", ["fetch_pdb"])
ml_builder_fn = _safe_import_callable("backend.tools.ml_model_builder_tool", ["build_model", "train_model"])
report_gen_fn = _safe_import_callable("backend.tools.report_generator_tool", ["generate_report"])


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def register(self, name: str, func: Any):
        if func is not None:
            self._tools[name] = func

    def list_tools(self):
        return sorted(self._tools.keys())

    def get(self, name: str):
        return self._tools.get(name)


REGISTRY = ToolRegistry()

# CORE REGISTRATION (INSTANTIATED CALLABLE TOOLS)
REGISTRY.register("summarizer", summarize_fn)
REGISTRY.register("qa_engine", qa_fn)
REGISTRY.register("pdf_reader", _pdf_reader_wrapper)
REGISTRY.register("table_extractor", table_extractor_fn)
REGISTRY.register("web_search", _web_search_wrapper)
REGISTRY.register("code_executor", code_executor_fn)
REGISTRY.register("pdb_fetcher", pdb_fetcher_fn)
REGISTRY.register("ml_model_builder", ml_builder_fn)
REGISTRY.register("arxiv_search", _arxiv_search_wrapper)
REGISTRY.register("pubmed_search", _pubmed_search_wrapper)
REGISTRY.register("biorxiv_search", _biorxiv_search_wrapper)
REGISTRY.register("semantic_scholar", _scholar_search_wrapper)
REGISTRY.register("scholar_search", _scholar_search_wrapper)
REGISTRY.register("deep_paper_reader", _deep_paper_reader_wrapper)
REGISTRY.register("report_generator", report_gen_fn)
REGISTRY.register("doc_reader", _doc_reader_wrapper)
REGISTRY.register("image_processor", _image_processor_wrapper)

TOOL_REGISTRY = REGISTRY
