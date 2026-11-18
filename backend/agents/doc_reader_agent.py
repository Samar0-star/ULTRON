from __future__ import annotations

# backend/agents/doc_reader_agent.py
"""
Production-ready Document Reader Agent (async first).
Uses llm_manager for all LLM interactions and specialized document parsing tools.
"""

import os
import json
import time
import logging
import asyncio
import hashlib
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass

import sys
import os

# STABILIZATION: Add project root and backend dir to path for direct execution
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if os.path.join(_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "backend"))

# Import model from llm_manager
from backend.llm_manager import run_llm, run_llm_async
from backend.core.api.models import Provider
from backend.utils.json_repair import repair_json
from backend.core.skill_injector import get_expert_system
DOC_READ_MODEL = None  # Lazy load to avoid circular import

# Logging
logger = logging.getLogger("avon.doc_reader_agent")
logger.setLevel(os.getenv("AVON_LOG_LEVEL", "INFO"))
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)

# Config
TEMPERATURE = float(os.getenv("DOC_READER_TEMPERATURE", "0.1"))
try:
    from backend.config import settings
    _DEFAULT_DOC_CHARS = str(settings.get_limit("max_context_chars", 120000))
except Exception:
    _DEFAULT_DOC_CHARS = "120000"
MAX_DOC_CHARS = int(os.getenv("DOC_READER_MAX_CHARS", _DEFAULT_DOC_CHARS))
RETRY_ATTEMPTS = int(os.getenv("DOC_READER_RETRIES", "2"))
REQUEST_TIMEOUT = float(os.getenv("DOC_READER_TIMEOUT", "600"))  # seconds
CONCURRENCY_LIMIT = int(os.getenv("DOC_READER_CONCURRENCY", "4"))

_PROMPT_TXT = """You are a PHD-grade Scientific Document Analyst.
Your mission is to extract EXPLICIT, GROUNDED scientific facts from the provided text.

### **WARNING: ZERO TOLERANCE FOR FABRICATION.**
Previous iterations of this system failed because the AI was "helpful" and invented technical details, variables, or constants not present in the text. This is **SCIENTIFIC FRAUD**.

**STRICT RULES:**
1. **NO SYNTHESIS**: Do NOT use your general knowledge to fill in gaps.
2. **NO INVENTED VARIABLES**: If a variable or constant is not explicitly mentioned in the text, you MUST NOT include it in `key_variables`.
3. **HARD ABORT**: If the text does not contain enough information to answer the query, you MUST state "NO_EVIDENCE_FOUND" in the `answer` field.
4. **FAITHFUL QUOTES**: Every fact MUST be supported by a direct, unedited quote in `relevant_snippets`.

Produce JSON ONLY with keys:
- answer: string (Detailed technical answer. MUST be "NO_EVIDENCE_FOUND" if not in text.)
- relevant_snippets: list of strings (Direct quotes supporting the answer)
- key_variables: list of {"name": "...", "value": "...", "unit": "...", "context": "..."}
- methodology_grade: string ("A" thru "F" based on rigor described in doc)
- limitations_noted: list of strings
- markdown_render: string (A human-readable markdown rendering of the above)

Return ONLY the JSON object. No preamble. No chatter.
"""

def _hash_input(query: str, doc_text: str) -> str:
    h = hashlib.sha256()
    h.update(query.encode("utf-8"))
    h.update(b"\n")
    h.update(doc_text.encode("utf-8"))
    return h.hexdigest()

def _safe_json_load(text: str) -> Tuple[Optional[dict], Optional[str]]:
    import re
    text = text.strip()
    code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        text = match.group(1)
    try:
        return json.loads(text), None
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = text[start:end+1]
            try:
                return json.loads(snippet), None
            except Exception as e:
                return None, f"extraction failed: {e}"
        return None, "no JSON found"
_semaphore: Optional[asyncio.Semaphore] = None

def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        try:
            _semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop_policy().get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            _semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    return _semaphore

class DocReaderAgent:
    name = "doc_reader_agent"

    def __init__(self, temperature: Optional[float] = None):
        self.temperature = TEMPERATURE if temperature is None else temperature
        self.expert_system = get_expert_system()

    async def _call_llm_async(self, query: str, doc_text: str, strategic_goal: str = "") -> str:
        try:
            from backend.llm_manager import run_llm, DEEP_RESEARCH_SYNTHESIS_MODEL
        except ImportError:
            from llm_manager import run_llm
            DEEP_RESEARCH_SYNTHESIS_MODEL = "sonnet-4.5"

        goal_block = f"\nPRIMARY MISSION OBJECTIVE: {strategic_goal}\n" if strategic_goal else ""
        prompt_text = f"{_PROMPT_TXT}\n{goal_block}\nRESEARCH QUERY: {query}\n\nDOCUMENT CONTEXT:\n{doc_text[:MAX_DOC_CHARS]}"
        
        # [GODZILLA ALIGNMENT] Inject specialist document skills
        prompt_text = await self.expert_system.inject_bundle(prompt_text, "doc_reader")

        logger.info(f"Calling LLM for deep document reading (Goal: {strategic_goal[:50]}...)")
        resp = await asyncio.to_thread(run_llm, prompt_text, model=DEEP_RESEARCH_SYNTHESIS_MODEL, temperature=self.temperature)
        
        if isinstance(resp, dict):
            return resp.get("text", "") or str(resp)
        return str(resp)

    async def run(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        payload = task.get("payload") or {}
        query = payload.get("query") or task.get("query") or ""
        doc_text = payload.get("text") or payload.get("content") or ""
        scientific_seeds = payload.get("scientific_seeds") or []
        
        # [DISK FILE RESOLUTION] If no in-memory text, attempt to load from disk path
        if not doc_text:
            file_path = payload.get("file_path") or payload.get("path") or task.get("file_path")
            if not file_path:
                # Scan query, description, and payload for existing dataset or document paths
                combined_desc = f"{query} {task.get('description', '')} {str(payload)}"
                data_dir = os.path.join(os.getcwd(), "data")
                dynamic_candidates = [os.path.join("data", fn) for fn in os.listdir(data_dir)] if os.path.exists(data_dir) else []
                for candidate in dynamic_candidates:
                    if candidate in combined_desc or os.path.basename(candidate) in combined_desc:
                        if os.path.exists(candidate) and os.path.isfile(candidate):
                            file_path = candidate
                            break
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        doc_text = f.read(MAX_DOC_CHARS)
                    logger.info(f" [DOC_READER] Loaded {len(doc_text)} chars directly from disk: {file_path}")
                except Exception as read_err:
                    logger.warning(f" [DOC_READER] Could not read disk file {file_path}: {read_err}")

        # [GODZILLA] Context Bridge: If no specific text provided, use the cached knowledge seeds
        if not doc_text and scientific_seeds:
            logger.info(f" [BRIDGE] DocReaderAgent: No primary text. Using {len(scientific_seeds)} scientific seeds as context.")
            doc_text = "\n\n---\n\n".join(scientific_seeds)

        strategic_goal = payload.get("STRATEGIC_GOAL", context.get("STRATEGIC_GOAL", ""))
        
        if not doc_text:
            return {"status": "failed", "error": "EXTRACTION FAILED - NO SOURCE DOCUMENT PROVIDED"}

        async with _get_semaphore():
            for attempt in range(1, RETRY_ATTEMPTS + 2):
                try:
                    content = await asyncio.wait_for(self._call_llm_async(query, doc_text, strategic_goal), timeout=REQUEST_TIMEOUT)
                    structured, err = _safe_json_load(content)
                    if structured:
                        markdown = structured.get("markdown_render") or self._fallback_render(structured)
                        return {
                            "text": markdown,
                            "attachments": [],
                            "meta": {"structured": structured}
                        }
                    else:
                        if attempt <= RETRY_ATTEMPTS: continue
                        return {"text": content, "error": "JSON parse failure"}
                except Exception as e:
                    logger.error(f"DocReaderAgent attempt {attempt} failed: {e}")
                    if attempt <= RETRY_ATTEMPTS:
                        await asyncio.sleep(attempt * 2)
                        continue
                    return {"error": str(e)}

    def _fallback_render(self, s: dict) -> str:
        return f"### Doc Analysis\n\n**Answer:** {s.get('answer')}\n\n**Variables:** {s.get('key_variables')}"

# Compatibility exports
Agent = DocReaderAgent
# [TITAN V196.0] ASYNC SOVEREIGNTY FIX
# Physically abolished the illegal asyncio.run() nested loop violation.
# Agents now return coroutines or are called within the unified swarm manifold.
async def run_doc_reader_agent(state):
    return await DocReaderAgent().run({"payload": {"query": getattr(state, "query", ""), "text": getattr(state, "text", "")}}, {})
