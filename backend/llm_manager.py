from __future__ import annotations
"""
Ultra-upgraded LLM Manager for ULTRON
Strict 3-Provider Architecture (Google, OpenAI, Anthropic).
Late-2026 Frontier Models.
"""

import os
import time
import json
import hashlib
import traceback
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, Generator, List, Tuple
import logging
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_not_exception_type

logger = logging.getLogger("ultron.llm_manager")

class GlobalQuotaExceededError(Exception):
    pass

class RedactingFilter(logging.Filter):
    def filter(self, record):
        if not isinstance(record.msg, str): return True
        for key in ["key", "api_key", "token", "password", "secret"]:
            if key in record.msg.lower():
                record.msg = "REDACTED sensitive data for F-50"
                break
        return True

logger.addFilter(RedactingFilter())

# Load .env if available
try:
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
except Exception:
    pass

# --- Embedding Model (single source of truth for all SentenceTransformer usage) ---
# Override via ULTRON_EMBEDDING_MODEL env var to swap in a different model with zero code changes.
EMBEDDING_MODEL = os.getenv("ULTRON_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
# Embedding output dimension — must match EMBEDDING_MODEL. Override via ULTRON_EMBEDDING_DIM.
EMBEDDING_DIM = int(os.getenv("ULTRON_EMBEDDING_DIM", "384"))

# =============================================================================
# CAPACITY MANAGEMENT STUBS (Preserving imports & usage)
# =============================================================================
def _acquire_capacity(provider: str, token_estimate: int, priority: int = 10, timeout: int = 600):
    try:
        from backend.core.scheduler import get_scheduler, JobContext
        import uuid
        scheduler = get_scheduler()
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        context = JobContext(job_id=job_id, priority=priority, max_wait=timeout, created_at=time.time())
        start_time = time.time()
        while True:
            status, reason = scheduler.acquire_non_blocking(provider, token_estimate, context)
            if status.value == "granted":
                return True
            if time.time() - start_time > timeout:
                return False
            time.sleep(0.1)
    except:
        return True

def _release_capacity(provider: str, tokens_used: int):
    try:
        from backend.core.scheduler import get_scheduler
        get_scheduler().release(provider, tokens_used)
    except:
        pass

# =============================================================================
# CONFIGURATION (Strict Multi-Provider)
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")).strip()
GOOGLE_API_KEY = GEMINI_API_KEY
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
if not NVIDIA_API_KEY:
    try:
        from backend.nvidia_nim_manager import get_nvidia_key
        NVIDIA_API_KEY = get_nvidia_key()
    except Exception:
        pass

MODEL_CONFIG = {
    "routing":              ("gpt-6-astra", "gemini-4-flash"),
    "decomposition":        ("gpt-6-astra", "claude-fable-5.1"),
    "hypothesis_generation": ("gpt-6-astra", "claude-fable-5.1"),
    "hypothesis_validation": ("gpt-6-astra", "mythos-5.1"),
    "novelty_check":        ("gpt-6-astra", "gemini-4-thinking"),
    "priority_scoring":     ("gpt-6-astra", "gemini-4-flash"),
    "deep_synthesis":       ("gpt-6-astra", "mythos-5.1"),
    "meta_reasoning":       ("gpt-6-astra", "claude-fable-5.1"),
    "consensus":            ("gpt-6-astra", "mythos-5.1"),
    "report_draft":         ("gpt-6-astra", "claude-fable-5.1"),
    "report_final":         ("gpt-6-astra", "mythos-5.1"),
    "summarization":        ("gpt-6-astra", "gemini-4-flash"),
    "fact_checking":        ("gpt-6-astra", "gemini-4-flash"),
    "qa":                   ("gpt-6-astra", "gemini-4-flash"),
    "search_query":         ("gpt-6-astra", "gemini-4-flash"),
    "document_extraction":  ("gpt-6-astra", "gemini-4-flash"),
    "code_generation":      ("gpt-6-astra", "claude-fable-5.1"),
    "vision":               ("gpt-6-astra", "gemini-4-pro"),
    "image_analysis":       ("gpt-6-astra", "gemini-4-pro"),
    "deep_paper_reading":   ("gpt-6-astra", "gemini-4-thinking"),
}

def _sync_with_settings_yaml():
    try:
        from backend.config import settings
        yaml_models = settings.models
        if yaml_models:
            for task, model_spec in yaml_models.items():
                if task in MODEL_CONFIG:
                    if isinstance(model_spec, str):
                        fallback = MODEL_CONFIG[task][1] if len(MODEL_CONFIG[task]) > 1 else "gpt-6-astra"
                        MODEL_CONFIG[task] = (model_spec, fallback)
                    elif isinstance(model_spec, (list, tuple)) and len(model_spec) >= 1:
                        fallback = model_spec[1] if len(model_spec) > 1 else "gpt-6-astra"
                        MODEL_CONFIG[task] = (model_spec[0], fallback)
    except Exception:
        pass

_sync_with_settings_yaml()

FORCE_NVIDIA = os.getenv("FORCE_NVIDIA", "false").lower() in ("true", "1", "yes")
if FORCE_NVIDIA and NVIDIA_API_KEY:
    for task in list(MODEL_CONFIG.keys()):
        MODEL_CONFIG[task] = ("z-ai/glm-5.3-flash", "z-ai/glm-5.3-flash")

ROUTING_MODEL = MODEL_CONFIG["routing"][0]
FACT_CHECKING_MODEL = MODEL_CONFIG["fact_checking"][0]
CODE_GENERATION_MODEL = MODEL_CONFIG["code_generation"][0]
REPORT_DRAFT_MODEL = MODEL_CONFIG["report_draft"][0]
REPORT_FINAL_MODEL = MODEL_CONFIG["report_final"][0]
SUMMARIZATION_MODEL = MODEL_CONFIG["summarization"][0]
VISION_MODEL = MODEL_CONFIG["vision"][0]
DEEP_PAPER_MODEL = MODEL_CONFIG["deep_paper_reading"][0]

# Preserve aliases
TASK_ROUTING_MODEL = MODEL_CONFIG["routing"][0]
TASK_DECOMPOSITION_MODEL = MODEL_CONFIG["decomposition"][0]
HYPOTHESIS_GENERATION_MODEL = MODEL_CONFIG["hypothesis_generation"][0]
HYPOTHESIS_VALIDATION_MODEL = MODEL_CONFIG["hypothesis_validation"][0]
NOVELTY_CHECKING_MODEL = MODEL_CONFIG["novelty_check"][0]
PRIORITY_SCORING_MODEL = MODEL_CONFIG["priority_scoring"][0]
DEEP_RESEARCH_SYNTHESIS_MODEL = MODEL_CONFIG["deep_synthesis"][0]
META_REASONING_MODEL = MODEL_CONFIG["meta_reasoning"][0]
CONSENSUS_VERIFICATION_MODEL = MODEL_CONFIG["consensus"][0]
QUESTION_ANSWERING_MODEL = MODEL_CONFIG["qa"][0]
WEB_QUERY_FORMULATION_MODEL = MODEL_CONFIG["search_query"][0]
DOCUMENT_EXTRACTION_MODEL = MODEL_CONFIG["document_extraction"][0]
VISUAL_INTERPRETATION_MODEL = MODEL_CONFIG["vision"][0]
IMAGE_VIDEO_ANALYSIS_MODEL = MODEL_CONFIG["image_analysis"][0]
DEEP_PAPER_READING_MODEL = MODEL_CONFIG["deep_paper_reading"][0]


MODEL_PROVIDERS = {
    "gemini":    "gemini",
    "claude":    "anthropic",
    "sonnet":    "anthropic",
    "opus":      "anthropic",
    "fable":     "anthropic",
    "mythos":    "anthropic",
    "gpt":       "openai",
    "astra":     "openai",
    "o1":        "openai",
    "o3":        "openai",
    "o4":        "openai",
    "glm":       "nvidia",
    "z-ai":      "nvidia",
    "nim":       "nvidia",
    "nvidia":    "nvidia",
}

def resolve_provider(model_name: str) -> str:
    if FORCE_NVIDIA and NVIDIA_API_KEY:
        return "nvidia"
    name = (model_name or "").lower()
    detected = None
    for prefix, provider in MODEL_PROVIDERS.items():
        if prefix in name:
            detected = provider
            break
    if detected == "openai" and (OPENAI_API_KEY and openai_client):
        return "openai"
    if detected == "anthropic" and (ANTHROPIC_API_KEY and anthropic_client):
        return "anthropic"
    if detected == "gemini" and GEMINI_API_KEY:
        return "gemini"
    if detected == "nvidia":
        return "nvidia"
    # Smart fallback: if the configured provider has no API key set, use whichever provider key IS available
    if OPENAI_API_KEY and openai_client:
        return "openai"
    if ANTHROPIC_API_KEY and anthropic_client:
        return "anthropic"
    if GEMINI_API_KEY:
        return "gemini"
    if NVIDIA_API_KEY:
        return "nvidia"
    return detected or "openai"

def get_model(task: str) -> str:
    return MODEL_CONFIG.get(task, ("gpt-6-astra", "claude-fable-5.1"))[0]

def get_fallback(task: str) -> str:
    return MODEL_CONFIG.get(task, ("gpt-6-astra", "claude-fable-5.1"))[1]

def get_model_with_fallback(task: str) -> tuple:
    return MODEL_CONFIG.get(task, ("gpt-6-astra", "claude-fable-5.1"))

# =============================================================================
# DYNAMIC FRONTIER MODEL CAPACITIES (OPUS 5.5, CLAUDE 3.7, GPT-6, GEMINI 2.0, GLM-5.3)
# =============================================================================
# =============================================================================
# UN-CHOKED FRONTIER MODEL CAPACITIES (1M+ TOKEN CEILING & AUTO-SURVIVAL)
# =============================================================================
DEFAULT_FRONTIER_MAX_TOKENS = int(os.getenv("ULTRON_MAX_OUTPUT_TOKENS", "65536"))

MODEL_MAX_OUTPUT_TOKENS = {
    # Google Gemini 4 Carbon / Argon / Gemini Frontier
    "gemini-4-carbon": 128000,
    "gemini-4-argon": 128000,
    "gemini-4-pro": 128000,
    "gemini-4-flash": 65536,
    "gemini-4": 128000,
    "gemini-2.5": 65536,
    "gemini-2.0-flash": 65536,
    "gemini-2.0-pro": 65536,
    "gemini-2.0": 65536,
    "gemini-1.5": 32768,
    # Anthropic Frontier
    "opus-5.5": 128000,
    "opus-5": 128000,
    "claude-opus-5": 128000,
    "claude-fable-5.1": 64000,
    "claude-sonnet-5": 64000,
    "claude-3-7-sonnet": 64000,
    # OpenAI Frontier
    "gpt-6-astra": 128000,
    "gpt-6.1-sol": 100000,
    "gpt-5.6-sol": 100000,
    "gpt-6": 65536,
    "gpt-5.5": 65536,
    "gpt-5": 65536,
    "o1": 100000,
    "o3": 100000,
    "o4": 100000,
    # Open / NVIDIA NIM Frontier
    "z-ai/glm-5.3-flash": 32768,
    "z-ai/glm-5.3": 32768,
    "deepseek-ai/deepseek-v4.1-flash": 16384,
    "deepseek-ai/deepseek-r1": 16384,
    "deepseek-ai/deepseek-v3": 16384,
}

def get_model_max_output_tokens(model_name: Optional[str]) -> int:
    """Return the architectural frontier token capacity for the target model."""
    if not model_name:
        return DEFAULT_FRONTIER_MAX_TOKENS
    m = model_name.lower().strip()
    if m in MODEL_MAX_OUTPUT_TOKENS:
        return MODEL_MAX_OUTPUT_TOKENS[m]
    for pattern, limit in MODEL_MAX_OUTPUT_TOKENS.items():
        if pattern in m:
            return limit
    return DEFAULT_FRONTIER_MAX_TOKENS

_DEEP_TASK_HINTS = {
    "code_generation", "deep_synthesis", "hypothesis_generation",
    "experiment_design", "manuscript", "paper_writing", "reasoning",
    "math", "synthesis", "report", "experiment", "discovery"
}

_DEEP_PROMPT_KEYWORDS = (
    "executable python", "python code", "calculate", "calculating",
    "synthesize", "manuscript", "formulate", "hypothesis", "hypotheses",
    "sympy", "design an experiment", "experiment protocol", "derivation",
    "simulation", "buried sasa", "coulombic", "```python"
)

def resolve_dynamic_token_budget(
    prompt: str,
    model: Optional[str] = None,
    requested_tokens: Optional[int] = None,
    override_tokens: Optional[int] = None,
    task_hint: Optional[str] = None
) -> int:
    """
    Dynamic token budget resolver:
    - Deep scientific tasks (or deep task_hints) unlock the model's full architectural ceiling.
    - Short, non-deep tasks with an explicit small token limit (e.g. 50 or 250 tokens) honor the caller's explicit constraint.
    """
    model_ceiling = get_model_max_output_tokens(model)
    caller_req = max(int(override_tokens or 0), int(requested_tokens or 0))
    p_lower = (prompt or "").lower()
    hint_lower = (task_hint or "").lower().strip()

    is_deep = (
        hint_lower in _DEEP_TASK_HINTS
        or any(k in p_lower for k in _DEEP_PROMPT_KEYWORDS)
        or len(p_lower) > 800
    )
    if is_deep or caller_req <= 0:
        return max(caller_req, model_ceiling)
    if caller_req < 1024:
        return min(caller_req, model_ceiling)
    return max(caller_req, model_ceiling)

def _extract_server_max_tokens_from_error(err_str: str, current_tokens: int) -> Optional[int]:
    """If an API endpoint rejects a 1M max_tokens value, extract its exact supported ceiling from the error message."""
    import re
    patterns = [
        r"(?:<=|less than or equal to|maximum[^0-9]*|at most|exceeds[^0-9]*|up to|max_tokens[^0-9]*|range\s*\[\s*\d+\s*,\s*)(\d{3,7})",
        r"(\d{4,7})\s*(?:tokens|is the maximum)"
    ]
    for pat in patterns:
        for m in re.finditer(pat, err_str, re.IGNORECASE):
            val = int(m.group(1))
            if 512 <= val < current_tokens:
                return val
    if any(k in err_str.lower() for k in ["max_tokens", "max_completion_tokens", "max_output_tokens", "token limit", "context_length_exceeded", "too many tokens", "invalid_request_error", "400", "422", "streaming is required", "10 minutes"]):
        for step in [262144, 131072, 65536, 32768, 16384, 8192, 4096]:
            if step < current_tokens:
                return step
    return None

# =============================================================================
# FRONTIER REASONING SANITIZER
# =============================================================================
def is_reasoning_model(model: Optional[str]) -> bool:
    if not model: return False
    m = model.lower().strip()
    import re
    if re.search(r'\b(o1|o3|o4|r1|qwq)\b', m) or re.search(r'^(o1|o3|o4|astra|mythos)', m):
        return True
    indicators = [
        "gpt-6", "gpt-5.6", "gpt-5.5", "gpt-5", "astra", "sol", "mythos", "fable", "opus-5", "fable-5", "sonnet-5",
        "gemini-4", "carbon", "argon", "thinking", "reasoning", "o1-", "o3-", "o4-", "r1-"
    ]
    return any(ind in m for ind in indicators)

def sanitize_payload(provider: str, model: str, payload: Dict[str, Any], thinking_enabled: bool = False) -> Dict[str, Any]:
    sanitized = dict(payload)
    reasoning = is_reasoning_model(model) or thinking_enabled
    model_ceiling = get_model_max_output_tokens(model)

    if reasoning:
        for k in ["temperature", "top_p", "presence_penalty", "frequency_penalty", "logit_bias", "top_k"]:
            sanitized.pop(k, None)

    if sanitized.get("temperature") is None:
        sanitized.pop("temperature", None)

    omit_cap = os.getenv("ULTRON_OMIT_MAX_TOKENS", "false").lower() == "true"

    if provider == "openai":
        tok = sanitized.pop("max_tokens", None)
        if omit_cap:
            sanitized.pop("max_completion_tokens", None)
        elif reasoning:
            if "max_completion_tokens" not in sanitized:
                sanitized["max_completion_tokens"] = int(tok) if tok else model_ceiling
        else:
            if "max_completion_tokens" not in sanitized:
                sanitized["max_tokens"] = int(tok) if tok else model_ceiling
    elif provider == "anthropic":
        if reasoning or "thinking" in sanitized:
            sanitized.pop("temperature", None)
            sanitized.pop("top_p", None)
            cur_max = sanitized.get("max_tokens") or model_ceiling
            sanitized["max_tokens"] = max(cur_max, model_ceiling)
        else:
            if "max_tokens" not in sanitized:
                sanitized["max_tokens"] = model_ceiling
    elif provider == "gemini":
        if reasoning:
            sanitized.pop("temperature", None)
            sanitized.pop("top_p", None)
            sanitized.pop("top_k", None)
        if omit_cap:
            sanitized.pop("max_output_tokens", None)
        elif "max_output_tokens" not in sanitized:
            sanitized["max_output_tokens"] = model_ceiling

    return sanitized

# =============================================================================
# RESPONSE CACHE
# =============================================================================
class ResponseCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._memory_cache = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _hash_key(self, model: str, messages: List[Dict], temperature: Optional[float] = None) -> str:
        temp_val = "none" if (temperature is None or is_reasoning_model(model)) else str(temperature)
        content = f"system_shared:{model}:{temp_val}:{json.dumps(messages, sort_keys=True)}"
        return f"llm_cache:{hashlib.md5(content.encode()).hexdigest()}"

    def get(self, model: str, messages: List[Dict], temperature: Optional[float] = None) -> Optional[str]:
        key = self._hash_key(model, messages, temperature)
        if key in self._memory_cache:
            response, timestamp = self._memory_cache[key]
            if time.time() - timestamp < self._ttl:
                return response
            else:
                del self._memory_cache[key]
        return None

    def set(self, model: str, messages: List[Dict], temperature: Optional[float] = None, response: str = ""):
        key = self._hash_key(model, messages, temperature)
        if len(self._memory_cache) >= self._max_size:
            oldest_key = min(self._memory_cache.keys(), key=lambda k: self._memory_cache[k][1])
            del self._memory_cache[oldest_key]
        self._memory_cache[key] = (response, time.time())

_response_cache = None
def get_response_cache() -> ResponseCache:
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache()
    return _response_cache

# =============================================================================
# CLIENTS
# =============================================================================
openai_client = None
async_openai_client = None
anthropic_client = None
gemini_client = None

try:
    from openai import OpenAI, AsyncOpenAI
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        async_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
except Exception: pass

try:
    import anthropic
    if ANTHROPIC_API_KEY:
        anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
except Exception: pass

if GOOGLE_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_client = genai
    except Exception: pass

def _estimate_provider_tokens(text: str) -> int:
    return max(1, int(len(text) / 3.5)) if text else 1

# =============================================================================
# CALL WRAPPERS (WITH AUTO-SURVIVAL TOKEN ADAPTATION FOR 1M+ FRONTIER MODELS)
# =============================================================================
@retry(wait=wait_exponential(multiplier=1, min=2, max=60), stop=stop_after_attempt(5), retry=retry_if_not_exception_type(AttributeError))
def _call_anthropic(prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None, model: str = None, **kwargs) -> Dict[str, Any]:
    target_model = model or get_model("deep_research")
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY", "dummy")
    client = anthropic.Anthropic(api_key=api_key)
    
    eff_tokens = resolve_dynamic_token_budget(prompt=prompt, model=target_model, requested_tokens=max_tokens, task_hint=kwargs.get("task"))
    params = {"model": target_model, "max_tokens": eff_tokens, "messages": [{"role": "user", "content": prompt}]}
    if temperature is not None: params["temperature"] = temperature
    params.update(kwargs)
    params = sanitize_payload("anthropic", target_model, params)
    
    for _adapt_attempt in range(3):
        try:
            resp = client.messages.create(**params)
            break
        except Exception as e:
            cur_tok = params.get("max_tokens", eff_tokens)
            adapted = _extract_server_max_tokens_from_error(str(e), cur_tok)
            if adapted and adapted < cur_tok:
                MODEL_MAX_OUTPUT_TOKENS[target_model.lower()] = adapted
                params["max_tokens"] = adapted
                continue
            raise
    text = getattr(resp.content[0], "text", str(resp.content[0])) if hasattr(resp, "content") and resp.content else str(resp)
    
    provider_tokens = _estimate_provider_tokens(prompt) + _estimate_provider_tokens(text)
    return {"text": text, "model": target_model, "provider_tokens": provider_tokens}

@retry(wait=wait_exponential(multiplier=1, min=2, max=60), stop=stop_after_attempt(5), retry=retry_if_not_exception_type(AttributeError))
def _call_openai(prompt: str, model: str = None, max_tokens: Optional[int] = None, temperature: Optional[float] = None, **kwargs) -> Dict[str, Any]:
    target_model = model or get_model("code_generation")
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    client = OpenAI(api_key=api_key)
    
    eff_tokens = resolve_dynamic_token_budget(prompt=prompt, model=target_model, requested_tokens=max_tokens, task_hint=kwargs.get("task"))
    params = {"model": target_model, "max_tokens": eff_tokens, "messages": [{"role": "user", "content": prompt}]}
    if temperature is not None: params["temperature"] = temperature
    params.update(kwargs)
    params = sanitize_payload("openai", target_model, params)
    
    for _adapt_attempt in range(3):
        try:
            resp = client.chat.completions.create(**params)
            break
        except Exception as e:
            tok_key = "max_completion_tokens" if "max_completion_tokens" in params else "max_tokens"
            cur_tok = params.get(tok_key, eff_tokens)
            adapted = _extract_server_max_tokens_from_error(str(e), cur_tok)
            if adapted and adapted < cur_tok:
                MODEL_MAX_OUTPUT_TOKENS[target_model.lower()] = adapted
                params[tok_key] = adapted
                continue
            elif tok_key in params and any(k in str(e).lower() for k in ["max_tokens", "max_completion_tokens"]):
                params.pop(tok_key, None)
                continue
            raise
    text = resp.choices[0].message.content or ""
    thinking = getattr(resp.choices[0].message, "reasoning_content", None)
    
    provider_tokens = _estimate_provider_tokens(prompt) + _estimate_provider_tokens(text)
    return {"text": text, "thinking": thinking, "model": target_model, "provider_tokens": provider_tokens}

@retry(wait=wait_exponential(multiplier=1, min=2, max=60), stop=stop_after_attempt(5), retry=retry_if_not_exception_type((AttributeError, ValueError)))
def _call_gemini(prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None, model: str = None, **kwargs) -> Dict[str, Any]:
    target_model = model or get_model("document_extraction")
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "dummy")
    genai.configure(api_key=api_key)
    
    eff_tokens = resolve_dynamic_token_budget(prompt=prompt, model=target_model, requested_tokens=max_tokens, task_hint=kwargs.get("task"))
    gen_config = {"max_output_tokens": eff_tokens}
    if temperature is not None: gen_config["temperature"] = temperature
    gen_config.update(kwargs)
    gen_config = sanitize_payload("gemini", target_model, gen_config)
    
    for _adapt_attempt in range(3):
        try:
            generation_config = genai.types.GenerationConfig(**gen_config) if hasattr(genai, "types") and hasattr(genai.types, "GenerationConfig") else gen_config
            m = genai.GenerativeModel(model_name=target_model, generation_config=generation_config)
            resp = m.generate_content([prompt])
            break
        except Exception as e:
            cur_tok = gen_config.get("max_output_tokens", eff_tokens)
            adapted = _extract_server_max_tokens_from_error(str(e), cur_tok)
            if adapted and adapted < cur_tok:
                MODEL_MAX_OUTPUT_TOKENS[target_model.lower()] = adapted
                gen_config["max_output_tokens"] = adapted
                continue
            elif "max_output_tokens" in gen_config and "token" in str(e).lower():
                gen_config.pop("max_output_tokens", None)
                continue
            raise
    text = resp.text if hasattr(resp, "text") else str(resp)
    
    provider_tokens = _estimate_provider_tokens(prompt) + _estimate_provider_tokens(text)
    return {"text": text, "model": target_model, "provider_tokens": provider_tokens}

_NVIDIA_MGR = None

def _get_nvidia_manager():
    global _NVIDIA_MGR
    if _NVIDIA_MGR is None:
        from backend.nvidia_nim_manager import NvidiaNIMManager, get_nvidia_key
        key = NVIDIA_API_KEY or get_nvidia_key()
        _NVIDIA_MGR = NvidiaNIMManager(api_key=key, model="z-ai/glm-5.3-flash")
    return _NVIDIA_MGR

def _call_nvidia(prompt: str, model: str = None, max_tokens: Optional[int] = None, temperature: Optional[float] = None, **kwargs) -> Dict[str, Any]:
    mgr = _get_nvidia_manager()
    return mgr.run(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature, **kwargs)


# =============================================================================
# MANAGER
# =============================================================================
class LLMManager:
    def __init__(self):
        self._pool = ThreadPoolExecutor(max_workers=32)
        if FORCE_NVIDIA and NVIDIA_API_KEY:
            self.provider = "nvidia"
            self.model_name = "z-ai/glm-5.3-flash"
        elif openai_client:
            self.provider = "openai"
            self.model_name = CODE_GENERATION_MODEL
        elif anthropic_client:
            self.provider = "anthropic"
            self.model_name = DEEP_RESEARCH_SYNTHESIS_MODEL
        elif gemini_client:
            self.provider = "gemini"
            self.model_name = DOCUMENT_EXTRACTION_MODEL
        elif NVIDIA_API_KEY:
            self.provider = "nvidia"
            self.model_name = "z-ai/glm-5.3-flash"
        else:
            self.provider = "none"
            self.model_name = "unknown"

    @property
    def model(self) -> str:
        return self.model_name

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "providers": {
                "nvidia": "ok" if NVIDIA_API_KEY else "not_configured",
                "openai": "ok" if openai_client else "not_configured",
                "anthropic": "ok" if anthropic_client else "not_configured",
                "gemini": "ok" if (gemini_client or GOOGLE_API_KEY) else "not_configured"
            }
        }

    def run(self, prompt: str, use_cache: bool = True, temperature: Optional[float] = None, max_tokens: Optional[int] = None, max_tokens_override: Optional[int] = None, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        start = time.time()
        target_model = model or kwargs.get("model") or self.model_name
        eff_max_tokens = resolve_dynamic_token_budget(
            prompt=prompt,
            model=target_model,
            requested_tokens=max_tokens,
            override_tokens=max_tokens_override,
            task_hint=kwargs.get("task")
        )
        eff_temp = None if is_reasoning_model(target_model) else temperature
        
        cache = get_response_cache()
        messages = [{"role": "user", "content": prompt}]
        if use_cache:
            cached = cache.get(target_model, messages, eff_temp)
            if cached: return {"text": cached, "model_used": target_model, "cached": True, "elapsed": time.time() - start}

        primary_provider = resolve_provider(target_model)
        provider_order = [primary_provider]
        for cand_p, has_key in [("openai", bool(OPENAI_API_KEY and openai_client)), ("anthropic", bool(ANTHROPIC_API_KEY and anthropic_client)), ("gemini", bool(GEMINI_API_KEY)), ("nvidia", bool(NVIDIA_API_KEY))]:
            if has_key and cand_p not in provider_order:
                provider_order.append(cand_p)

        last_err = None
        for provider in provider_order:
            try:
                if provider == "nvidia":
                    nv_model = target_model if any(k in (target_model or "").lower() for k in ["glm", "deepseek", "nvidia", "meta/", "mistral", "qwen"]) else None
                    out = _call_nvidia(prompt, model=nv_model, max_tokens=eff_max_tokens, temperature=eff_temp, **kwargs)
                elif provider == "anthropic":
                    ant_model = target_model if any(k in (target_model or "").lower() for k in ["claude", "opus", "sonnet", "haiku", "fable", "mythos"]) else "claude-fable-5.1"
                    out = _call_anthropic(prompt, max_tokens=eff_max_tokens, temperature=eff_temp, model=ant_model, **kwargs)
                elif provider == "gemini":
                    gem_model = target_model if any(k in (target_model or "").lower() for k in ["gemini", "carbon", "argon"]) else "gemini-4-flash"
                    out = _call_gemini(prompt, max_tokens=eff_max_tokens, temperature=eff_temp, model=gem_model, **kwargs)
                else:
                    oa_model = target_model if any(k in (target_model or "").lower() for k in ["gpt", "astra", "sol", "o1", "o3", "o4"]) else "gpt-6-astra"
                    out = _call_openai(prompt, model=oa_model, max_tokens=eff_max_tokens, temperature=eff_temp, **kwargs)

                if isinstance(out, dict) and out.get("text") and not out.get("error"):
                    if use_cache:
                        cache.set(target_model, messages, eff_temp, out["text"])
                    out["elapsed"] = time.time() - start
                    out["provider"] = provider
                    return out
                last_err = out.get("error") if isinstance(out, dict) else "Empty response"
            except Exception as e:
                last_err = e
                continue
        return {"error": str(last_err), "trace": traceback.format_exc(), "elapsed": time.time() - start}

    def run_sync(self, *args, **kwargs) -> Dict[str, Any]:
        return self.run(*args, **kwargs)

    async def run_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        target_model = kwargs.get("model") or self.model_name
        provider = resolve_provider(target_model)
        if provider == "nvidia":
            mgr = _get_nvidia_manager()
            return await mgr.run_async(prompt, **kwargs)
        return await asyncio.to_thread(self.run, prompt=prompt, **kwargs)

    def run_structured(self, prompt: str, response_model: Any, model: Optional[str] = None, **kwargs) -> Any:
        """
        Execute LLM call with guaranteed structured output adhering to a Pydantic model.
        Leverages native provider schema enforcement (OpenAI response_format, Anthropic tool use, or Gemini response_schema)
        with automatic Pydantic validation.
        """
        target_model = model or kwargs.get("model") or CODE_GENERATION_MODEL
        provider = resolve_provider(target_model)
        
        schema_json = ""
        try:
            if hasattr(response_model, "model_json_schema"):
                schema_json = json.dumps(response_model.model_json_schema(), indent=2)
            elif hasattr(response_model, "schema"):
                schema_json = json.dumps(response_model.schema(), indent=2)
        except Exception:
            pass

        structured_prompt = prompt
        if schema_json and "JSON" not in prompt:
            structured_prompt = f"{prompt}\n\nRespond strictly with a JSON object conforming to this schema:\n{schema_json}"

        if provider == "openai" and openai_client and hasattr(openai_client, "beta"):
            try:
                eff_temp = None if is_reasoning_model(target_model) else kwargs.get("temperature", 0.2)
                params = {
                    "model": target_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": response_model,
                }
                if eff_temp is not None:
                    params["temperature"] = eff_temp
                completion = openai_client.beta.chat.completions.parse(**params)
                if completion.choices and completion.choices[0].message.parsed:
                    return completion.choices[0].message.parsed
            except Exception as e:
                logger.warning(f"OpenAI beta.parse fallback: {e}")

        raw_res = self.run(prompt=structured_prompt, model=target_model, **kwargs)
        raw_text = raw_res.get("text", "") if isinstance(raw_res, dict) else str(raw_res)

        cleaned = raw_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        if hasattr(response_model, "model_validate_json"):
            return response_model.model_validate_json(cleaned)
        elif hasattr(response_model, "parse_raw"):
            return response_model.parse_raw(cleaned)
        elif hasattr(response_model, "model_validate"):
            return response_model.model_validate(json.loads(cleaned))
        else:
            return json.loads(cleaned)

    async def run_structured_async(self, prompt: str, response_model: Any, **kwargs) -> Any:
        return await asyncio.to_thread(self.run_structured, prompt=prompt, response_model=response_model, **kwargs)

    async def stream_async(self, prompt: str, **kwargs):
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self._pool, lambda: self.run(prompt=prompt, **kwargs))
            if result.get("thinking"):
                yield {"type": "thinking", "content": result["thinking"]}
            yield {"type": "text", "content": result.get("text", "")}
        except Exception as e:
            yield {"type": "error", "content": str(e)}

_SINGLETON_LLM = None
_SINGLETON_LOCK = threading.Lock()
def get_llm_manager() -> LLMManager:
    global _SINGLETON_LLM
    if _SINGLETON_LLM is None:
        with _SINGLETON_LOCK:
            if _SINGLETON_LLM is None:
                _SINGLETON_LLM = LLMManager()
    return _SINGLETON_LLM

llm_manager = get_llm_manager()

def run_llm(prompt: str, **kwargs) -> Any:
    out = llm_manager.run(prompt=prompt, **kwargs)
    if isinstance(out, dict):
        if kwargs.get("return_full_object") or "error" in out:
            return out
        return out.get("text", "")
    return str(out)

async def run_llm_async(prompt: str, **kwargs) -> Dict[str, Any]:
    return await llm_manager.run_async(prompt=prompt, **kwargs)

def run_structured(prompt: str, response_model: Any, **kwargs) -> Any:
    return llm_manager.run_structured(prompt, response_model, **kwargs)

async def run_structured_async(prompt: str, response_model: Any, **kwargs) -> Any:
    return await llm_manager.run_structured_async(prompt, response_model, **kwargs)

def run_llm_stream(prompt: str, **kwargs) -> Generator[str, None, None]:
    gen = llm_manager.stream_async(prompt=prompt, **kwargs)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            def _collect():
                new_loop = asyncio.new_event_loop()
                try:
                    items = []
                    while True:
                        try:
                            chunk = new_loop.run_until_complete(anext(gen))
                            if isinstance(chunk, dict) and chunk.get("type") == "text":
                                items.append(chunk["content"])
                        except StopAsyncIteration:
                            break
                    return items
                finally:
                    new_loop.close()
            for item in pool.submit(_collect).result():
                yield item
    else:
        own_loop = asyncio.new_event_loop()
        try:
            while True:
                try:
                    chunk = own_loop.run_until_complete(anext(gen))
                    if isinstance(chunk, dict) and chunk.get("type") == "text":
                        yield chunk["content"]
                except StopAsyncIteration:
                    break
        finally:
            own_loop.close()

def run_with_fallback(task: str, prompt: str, **kwargs) -> dict:
    primary, fallback = get_model_with_fallback(task)
    temperature = kwargs.pop("temperature", 0.2)
    cache = get_response_cache()
    cached = cache.get(primary, [{"role": "user", "content": prompt}], temperature)
    if cached:
        return {"text": cached, "model_used": primary, "fallback_used": False, "cached": True}
        
    candidates = [primary, fallback] if primary != fallback else [primary]
    errors = []
    
    for model in candidates:
        try:
            res = llm_manager.run(prompt, model=model, temperature=temperature, **kwargs)
            if "error" not in res and res.get("text"):
                cache.set(primary, [{"role": "user", "content": prompt}], temperature, res["text"])
                return {"text": res["text"], "model_used": model, "fallback_used": model != primary, "cached": False, "raw": res}
            errors.append(res.get("error", "Empty response"))
        except Exception as e:
            errors.append(str(e))
            
    raise GlobalQuotaExceededError(f"All providers failed. Errors: {errors}")
