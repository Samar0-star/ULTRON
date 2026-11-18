from __future__ import annotations

# backend/agents/summarizer_agent.py
"""
Production-ready Summarizer Agent (async first).
Uses llm_manager for all LLM interactions.
"""

import os
import json
import time
import logging
import asyncio
import hashlib
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from backend.core.skill_injector import get_expert_system

# Import model from llm_manager - will be used in _call_llm_async
SUMMARIZATION_MODEL = None  # Lazy load to avoid circular import

# Logging
logger = logging.getLogger("avon.summarizer")
logger.setLevel(os.getenv("AVON_LOG_LEVEL", "INFO"))
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)

# Config
TEMPERATURE = float(os.getenv("SUMMARIZER_TEMPERATURE", "0.0"))
MAX_CONTEXT_CHARS = int(os.getenv("SUMMARIZER_MAX_CONTEXT_CHARS", "120000"))
RETRY_ATTEMPTS = int(os.getenv("SUMMARIZER_RETRIES", "2"))
REQUEST_TIMEOUT = float(os.getenv("SUMMARIZER_TIMEOUT", "600"))  # seconds: increased to 10m for deep research
CONCURRENCY_LIMIT = int(os.getenv("SUMMARIZER_CONCURRENCY", "4"))

CACHE_DIR = os.getenv("SUMMARIZER_CACHE_DIR", os.path.join(os.getcwd(), ".summarizer_cache"))

if not os.path.exists(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception:
        logger.debug("Could not create cache dir; proceeding without disk cache.")
        CACHE_DIR = None

# Basic prompt (structured JSON + markdown_render)
_PROMPT_TXT = """
You are a Ph.D.-grade scientific evidence synthesizer and parameter extractor.
Your goal is to extract GROUND TRUTH from the provided components.

Produce JSON ONLY with keys:
- tl_dr: string (1-2 sentences)
- extracted_parameters: list of {"name": "...", "symbol": "...", "value": float, "unit": "...", "source": "Citation (Author, Year)"}
- key_findings: list of {"claim": "...", "confidence": "low|medium|high", "notes":"...", "sources":[...] }
- evidence: list of {"source":"", "snippet":"", "link":""}
- methods_and_limitations: string
- recommended_next_steps: list of strings
- markdown_render: string (a human-readable markdown rendering of the above)

### CRITICAL MANDATES:
1. NO PROSE PARAMETERS: If a value is missing, do not invent it. Only extract real numbers from text.
2. CITATION LOCK: Every finding and parameter MUST be linked to one of the provided components.
3. NO FAKE CITATIONS: Do NOT invent authors (e.g., no "Zhang et al. 2024" if not in the input).
Return only the JSON object.
"""

# Helpers
def _hash_input(query: str, components_text: str, extra: Optional[dict] = None) -> str:
    h = hashlib.sha256()
    h.update(query.encode("utf-8"))
    h.update(b"\n")
    h.update(components_text.encode("utf-8"))
    if extra:
        h.update(json.dumps(extra, sort_keys=True).encode("utf-8"))
    return h.hexdigest()

def _write_cache(key: str, obj: Any):
    if not CACHE_DIR:
        return
    try:
        path = os.path.join(CACHE_DIR, f"{key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, default=str)
    except Exception as e:
        logger.debug("Cache write failed: %s", e)

def _read_cache(key: str) -> Optional[Any]:
    if not CACHE_DIR:
        return None
    try:
        path = os.path.join(CACHE_DIR, f"{key}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.debug("Cache read failed: %s", e)
    return None

def _safe_json_load(text: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Try to extract a JSON object from text robustly.
    Returns (dict_or_none, error_message_or_none)
    """
    # First try to strip markdown code blocks
    import re
    text = text.strip()
    # Pattern to match ```json ... ``` or just ``` ... ```
    code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        text = match.group(1)

    try:
        # try direct parse
        return json.loads(text), None
    except Exception:
        # try to find last {...} block
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = text[start:end+1]
            try:
                return json.loads(snippet), None
            except Exception as e:
                return None, f"extraction failed: {e}"
        return None, "no JSON found"

def _components_to_text(components: Optional[List[Dict[str, Any]]]) -> str:
    if not components:
        return ""
    parts = []
    for i, c in enumerate(components):
        task = c.get("task", {})
        res = c.get("result", {})
        header = f"--- Component #{i+1}: task={task.get('type')}\n"
        text = res.get("text", "") or ""
        attachments = res.get("attachments", [])
        attach_summary = ""
        if attachments:
            attach_summary = "\nAttachments:\n" + "\n".join(
                [a.get("title", str(a)) if isinstance(a, dict) else str(a) for a in attachments]
            )
        parts.append(header + text + attach_summary)
    joined = "\n\n".join(parts)
    if len(joined) > MAX_CONTEXT_CHARS:
        return joined[:MAX_CONTEXT_CHARS]
    return joined

# Concurrency control (keyed per event loop to prevent cross-loop RuntimeError)
_semaphores: Dict[int, asyncio.Semaphore] = {}

def _get_semaphore() -> asyncio.Semaphore:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop_policy().get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    loop_id = id(loop)
    if loop_id not in _semaphores:
        _semaphores[loop_id] = asyncio.Semaphore(CONCURRENCY_LIMIT)
    return _semaphores[loop_id]

@dataclass
class SummarizerResult:
    text: str
    attachments: List[Any]
    meta: Dict[str, Any]

class Agent:
    name = "summarizer"

    def __init__(self,
                 temperature: Optional[float] = None):
        self.temperature = TEMPERATURE if temperature is None else temperature
        self.expert_system = get_expert_system()

        # No local LLM init - we use llm_manager dynamically

    async def _call_llm_async(self, prompt_inputs: Dict[str, Any]) -> str:
        """
        Primary async call path: Uses LLM Manager for all requests.
        `prompt_inputs` for chain: {"query":..., "components_text":...}
        """
        # Import llm_manager
        try:
            try:
                from backend.llm_manager import run_llm, SUMMARIZATION_MODEL
            except ImportError:
                from llm_manager import run_llm
                SUMMARIZATION_MODEL = "sonnet-4.5"  # Fallback
        except ImportError:
            raise RuntimeError("LLM Manager not available")

        query = prompt_inputs.get("query", "")
        components_text = prompt_inputs.get("components_text", "")

        # Build prompt text
        prompt_text = _PROMPT_TXT + "\n\nQuery:\n" + query + "\n\nComponents:\n" + components_text[:MAX_CONTEXT_CHARS]

        # [GODZILLA ALIGNMENT] Inject specialist summarization skills
        prompt_text = await self.expert_system.inject_bundle(prompt_text, "summarizer")

        # Use SUMMARIZATION_MODEL for summarization tasks
        logger.info(f"Calling LLM Manager for summarization with model={SUMMARIZATION_MODEL}")
        resp = await asyncio.to_thread(run_llm, prompt_text, model=SUMMARIZATION_MODEL, temperature=self.temperature)
        
        # Extract text from response dict (run_llm returns {"text": "...", ...})
        if isinstance(resp, dict):
            return resp.get("text", "") or str(resp)
        return str(resp)

    async def run(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async entrypoint:
        task: {"payload": {"query":..., "components":[...]}} OR string payload OR {"query": "...", "instruction": "..."}
        Returns JSON-like dict: {"text": markdown, "attachments": [], "meta": {...}}
        """
        # Handle different input formats
        payload = task.get("payload") or {}

        # If no payload, treat the whole task as the input
        if not payload:
            query = task.get("query") or task.get("instruction") or ""
            # [FIXED] No synthetic components
            components = []
            components = [{"task": {"type": "text"}, "result": {"text": query, "attachments": []}}]
        elif isinstance(payload, str):
            query = task.get("meta", {}).get("query") or ""
            components = [{"task": {"type": "text"}, "result": {"text": payload, "attachments": []}}]
        else:
            query = payload.get("query") or task.get("meta", {}).get("query") or task.get("query") or ""
            components = payload.get("components") or []

            if not components and query:
                components = [{"task": {"type": "text"}, "result": {"text": query, "attachments": []}}]
            elif not components:
                return {'error': '[HARD ABORT] No real components for summarization'}
        components_text = _components_to_text(components)
        cache_key = _hash_input(query, components_text, {"model": "llm_manager_auto"})

        # Use cache if available
        cached = _read_cache(cache_key)
        if cached:
            logger.debug("Cache hit summarizer")
            return {"text": cached.get("markdown_render"), "attachments": [], "meta": {"structured": cached}}

        # Acquire concurrency slot
        async with _get_semaphore():
            last_err = None
            for attempt in range(1, RETRY_ATTEMPTS + 2):
                try:
                    # timeout guard
                    coro = self._call_llm_async({"query": query, "components_text": components_text})
                    content = await asyncio.wait_for(coro, timeout=REQUEST_TIMEOUT)
                    structured, err = _safe_json_load(content)
                    if structured:
                        # [GODZILLA GATE] Validate Data Binding
                        extracted = structured.get("extracted_parameters", [])
                        key_findings = structured.get("key_findings", [])
                        if not extracted and not key_findings:
                            logger.warning(f" [RIGOR VIOLATION] Summarizer found 0 parameters and 0 findings in components. Blocking slop.")
                            if attempt <= RETRY_ATTEMPTS:
                                await asyncio.sleep(1 + attempt)
                                continue

                        # ensure markdown_render exists
                        markdown = structured.get("markdown_render") or _structured_to_markdown(structured)
                        result = {"tl_dr": structured.get("tl_dr", ""),
                                  "extracted_parameters": extracted,
                                  "key_findings": structured.get("key_findings", []),
                                  "evidence": structured.get("evidence", []),
                                  "methods_and_limitations": structured.get("methods_and_limitations", ""),
                                  "recommended_next_steps": structured.get("recommended_next_steps", []),
                                  "markdown_render": markdown}
                        _write_cache(cache_key, result)
                        return {"text": markdown, "attachments": [], "meta": {"structured": result}}
                    else:
                        last_err = err or "unknown parse error"
                        logger.warning("LLM returned non-JSON. Attempt %s/%s parse error: %s", attempt, RETRY_ATTEMPTS+1, last_err)
                        # If LLM returned something close, return fallback markdown
                        fallback_md = _fallback_markdown(query, components, raw_text=content)
                        # Try once more if attempts remain
                        if attempt <= RETRY_ATTEMPTS:
                            await asyncio.sleep(1 + attempt)
                            continue
                        return {"text": fallback_md, "attachments": [], "meta": {"error": f"parse_failed: {last_err}", "raw": content}}
                except asyncio.TimeoutError:
                    last_err = "timeout"
                    logger.warning("LLM call timed out on attempt %s", attempt)
                    if attempt <= RETRY_ATTEMPTS:
                        await asyncio.sleep(1 + attempt)
                        continue
                    return {"text": _fallback_markdown(query, components), "attachments": [], "meta": {"error": "timeout"}}
                except Exception as e:
                    last_err = str(e)
                    logger.exception("LLM call failed on attempt %s: %s", attempt, e)
                    if attempt <= RETRY_ATTEMPTS:
                        await asyncio.sleep(1 + attempt)
                        continue
                    return {"text": _fallback_markdown(query, components), "attachments": [], "meta": {"error": last_err}}

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

# Sync wrapper for compatibility
def run_summarizer_agent(state) -> Dict[str, Any]:
    """
    Synchronous wrapper for code expecting a blocking call.
    state: object with attributes user_input (str), components (list) (opt)
    """
    agent = Agent()
    payload = {"query": getattr(state, "user_input", ""), "components": getattr(state, "components", None)}
    task = {"payload": payload, "meta": {"mission_id": getattr(state, "mission_id", None)}}
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    # run the async run via run_until_complete; handle nest_asyncio if needed
    try:
        return loop.run_until_complete(agent.run(task, {}))
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply(loop)
        return loop.run_until_complete(agent.run(task, {}))

# ----- Utility rendering functions -----
def _structured_to_markdown(s: Dict[str, Any]) -> str:
    lines = []
    lines.append("## TL;DR\n")
    lines.append(s.get("tl_dr", "") + "\n")
    lines.append("\n## Key Findings\n")
    for k in s.get("key_findings", []):
        claim = k.get("claim", "")
        conf = k.get("confidence", "")
        notes = k.get("notes", "")
        sources = k.get("sources", [])
        srcs = ", ".join([f"[{i+1}] {ss}" for i, ss in enumerate(sources)]) if sources else ""
        lines.append(f"- **{claim}** (confidence: {conf})  {notes} {srcs}\n")
    lines.append("\n## Evidence\n")
    for e in s.get("evidence", []):
        lines.append(f"- {e.get('source','')}  {e.get('snippet','')} ({e.get('link','')})")
    lines.append("\n## Methods & Limitations\n")
    lines.append(s.get("methods_and_limitations", "") + "\n")
    lines.append("\n## Recommended Next Steps\n")
    for step in s.get("recommended_next_steps", []):
        lines.append(f"- {step}")
    return "\n".join(lines)

def _fallback_markdown(query: str, components: List[Dict[str, Any]], raw_text: Optional[str] = None) -> str:
    header = f"# Summary for: {query}\n\n"
    if raw_text:
        header += "### Raw LLM Output (could not parse as JSON)\n\n"
        header += raw_text + "\n\n"
    for i, c in enumerate(components):
        header += f"### Component {i+1}  {c.get('task',{}).get('type')}\n"
        header += (c.get("result", {}).get("text", "") or "")[:2000] + "\n\n"
    return header

# Self-test
if __name__ == "__main__":

    agent = Agent()
    import asyncio
    out = asyncio.get_event_loop().run_until_complete(agent.run({"payload": {"query": "prime editing efficiency summary", "components": demo_components}}, {}))
    print(json.dumps(out, indent=2))

# Backward compatibility alias
SummarizerAgent = Agent
