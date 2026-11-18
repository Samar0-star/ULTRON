#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live NVIDIA NIM Manager & Orchestrator Runner for ULTRON AI Scientist
Uses strictly NVIDIA NIM API with z-ai/glm-5.3-flash (or z-ai/glm-5.3).
Provides rate-limiting, reasoning-token extraction, and failure auditing.
"""

import os
import sys
import time
import json
import ast
import asyncio
import logging
import threading
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import dotenv
dotenv.load_dotenv(ROOT_DIR / "backend" / ".env")

logger = logging.getLogger("ultron.nvidia_live")

def get_nvidia_keys() -> List[str]:
    keys: List[str] = []
    
    # Check process environment first
    raw_env = os.getenv("NVIDIA_API_KEYS")
    if raw_env:
        try:
            parsed = ast.literal_eval(raw_env)
            if parsed and isinstance(parsed, list):
                for k in parsed:
                    k_str = str(k).strip()
                    if k_str not in keys:
                        keys.append(k_str)
        except Exception:
            for k in raw_env.split(","):
                k_str = k.strip().strip("'\"")
                if k_str.startswith("nvapi-") and k_str not in keys:
                    keys.append(k_str)

    single = os.getenv("NVIDIA_API_KEY")
    if single and single.strip() not in keys:
        keys.append(single.strip())

    # Check .env files in standard locations
    possible_env_paths = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / "backend" / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in possible_env_paths:
        if env_path.exists():
            cfg = dotenv.dotenv_values(str(env_path))
            raw_keys = cfg.get("NVIDIA_API_KEYS")
            if raw_keys:
                try:
                    parsed = ast.literal_eval(raw_keys)
                    if parsed and isinstance(parsed, list):
                        for k in parsed:
                            k_str = str(k).strip()
                            if k_str not in keys:
                                keys.append(k_str)
                except Exception:
                    for k in str(raw_keys).split(","):
                        k_str = k.strip().strip("'\"")
                        if k_str.startswith("nvapi-") and k_str not in keys:
                            keys.append(k_str)
            single_cfg = cfg.get("NVIDIA_API_KEY")
            if single_cfg and str(single_cfg).strip() not in keys:
                keys.append(str(single_cfg).strip())

    # Filter out known invalid keys (e.g. 403 authorization failures on chat completions)
    forbidden_keys = {
        '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',
    }
    valid_keys = [
        k for k in keys 
        if k and k.startswith("nvapi-") and len(k) >= 60 and k not in forbidden_keys
    ]

    if valid_keys:
        return valid_keys

    raise RuntimeError("Valid NVIDIA API Keys not found in backend/.env")

def get_nvidia_key() -> str:
    return get_nvidia_keys()[0]

class NvidiaNIMManager:
    """
    Sovereign LLM Manager communicating exclusively with NVIDIA NIM API.
    Routes all queries to z-ai/glm-5.3-flash with robust multi-key round-robin pooling,
    automatic failover on 429 / 403 / timeout, and reasoning extraction.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_keys: Optional[List[str]] = None,
        model: str = "z-ai/glm-5.3-flash"
    ):
        if api_keys:
            self.api_keys = [k for k in api_keys if k and k.startswith("nvapi-")]
        elif api_key:
            all_discovered = get_nvidia_keys()
            self.api_keys = [api_key] + [k for k in all_discovered if k != api_key]
        else:
            self.api_keys = get_nvidia_keys()

        self.model_name = model
        self.fallback_model = "deepseek-ai/deepseek-v4.1-flash" if model == "z-ai/glm-5.3-flash" else "z-ai/glm-5.3-flash"
        self.endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
        self._pool_lock = threading.Lock()
        self._key_index = 0
        self._key_last_used: Dict[str, float] = {k: 0.0 for k in self.api_keys}
        self._key_cooldowns: Dict[str, float] = {k: 0.0 for k in self.api_keys}
        self._model_cooldowns: Dict[str, float] = {}
        self._min_key_delay = 1.0  # Per-key throttle: 1.0s delay between calls on identical key
        self.total_calls = 0
        self.total_reasoning_chars = 0
        self.call_audit_log: List[Dict[str, Any]] = []

    @property
    def model(self) -> str:
        return self.model_name

    @property
    def api_key(self) -> str:
        return self.api_keys[self._key_index % len(self.api_keys)]

    def _mark_model_cooldown(self, model_name: str, seconds: float = 300.0):
        with self._pool_lock:
            self._model_cooldowns[model_name] = time.time() + seconds
            logger.warning(f"[MODEL_COOLDOWN] Model {model_name} marked on cooldown for {seconds:.1f}s")

    def _acquire_key(self) -> str:
        with self._pool_lock:
            now = time.time()
            available = [k for k in self.api_keys if self._key_cooldowns.get(k, 0.0) <= now]
            if not available:
                earliest_k = min(self.api_keys, key=lambda k: self._key_cooldowns.get(k, 0.0))
                wait_t = max(0.0, self._key_cooldowns.get(earliest_k, 0.0) - now)
                if wait_t > 0:
                    logger.warning(f"[POOL_COOLDOWN] All keys in pool cooling down. Waiting {wait_t:.1f}s...")
                    time.sleep(wait_t)
                selected_key = earliest_k
            else:
                selected_key = available[self._key_index % len(available)]
                self._key_index = (self._key_index + 1) % len(available)

            last_used = self._key_last_used.get(selected_key, 0.0)
            elapsed = time.time() - last_used
            if elapsed < self._min_key_delay:
                time.sleep(self._min_key_delay - elapsed)

            self._key_last_used[selected_key] = time.time()
            return selected_key

    def _mark_key_cooldown(self, key: str, seconds: float = 20.0):
        with self._pool_lock:
            self._key_cooldowns[key] = time.time() + seconds
            logger.warning(f"[KEY_COOLDOWN] Key {key[:14]}... marked on cooldown for {seconds:.1f}s")

    def run(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        raw_req_model = model or self.model_name
        # Sanitize legacy cross-provider default routing constants while allowing explicit model overrides to participate in failover
        _cross_provider_defaults = {
            "gpt-6-astra", "claude-fable-5.1", "claude-sonnet-5",
            "gemini-4-carbon", "gemini-4-argon", "gemini-4-flash", "mythos-5.1"
        }
        if raw_req_model and raw_req_model.lower().strip() not in _cross_provider_defaults:
            req_model = raw_req_model
        else:
            req_model = self.model_name
        override_tok = kwargs.get("max_tokens_override")
        
        try:
            from backend.llm_manager import resolve_dynamic_token_budget
            eff_max_tokens = resolve_dynamic_token_budget(
                prompt=prompt,
                model=req_model,
                requested_tokens=max_tokens,
                override_tokens=override_tok,
                task_hint=kwargs.get("task")
            )
        except Exception:
            eff_max_tokens = max(int(override_tok or 0), int(max_tokens or 0), 32768)

        eff_temp = float(temperature if temperature is not None else 0.2)

        # Check if the prompt requests JSON or schema extraction
        if kwargs.get("is_json") is False or kwargs.get("response_format") == "text":
            is_json = False
        else:
            is_json = (
                kwargs.get("response_format") in ["json_object", {"type": "json_object"}]
                or kwargs.get("expected_key") is not None
                or kwargs.get("is_json") is True
                or (
                    ("json" in prompt.lower() and "{" in prompt)
                    and not any(k in prompt.lower() for k in ["python code", "executable python", "```python", "def run_", "def main", "import numpy"])
                )
            )

        # Format system & user messages
        if is_json:
            system_content = (
                "You are ULTRON Autonomous AI Scientist operating as a mathematical formalization kernel. "
                "You must output strictly valid, parseable JSON ONLY conforming to the requested schema. "
                "Think concisely and emit the valid JSON schema directly without lengthy preambles."
            )
        else:
            system_content = kwargs.get("system_prompt") or (
                "You are ULTRON Autonomous AI Scientist operating as a sovereign computational researcher. "
                "Perform exhaustive, first-principles mathematical and empirical reasoning without artificial token or length constraints. "
                "Output the complete executable Python script or scientific derivation in the final output block. Never use emojis."
            )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]

        # Determine candidate models with intelligent cooldown failover
        now = time.time()
        candidate_models = []
        if self._model_cooldowns.get(req_model, 0.0) <= now:
            candidate_models.append(req_model)
        else:
            remaining = self._model_cooldowns.get(req_model, 0.0) - now
            logger.info(f"[MODEL_COOLDOWN_ACTIVE] {req_model} on cooldown ({remaining:.1f}s remaining). Routing to failover model.")

        fallback = self.fallback_model if req_model == self.model_name else ("deepseek-ai/deepseek-v4.1-flash" if req_model == "z-ai/glm-5.3-flash" else "z-ai/glm-5.3-flash")
        if fallback not in candidate_models:
            candidate_models.append(fallback)
        for safe_m in ("z-ai/glm-5.3-flash", "deepseek-ai/deepseek-v4.1-flash", "z-ai/glm-5.3"):
            if safe_m not in candidate_models:
                candidate_models.append(safe_m)
        if not candidate_models:
            candidate_models.append(req_model)

        t0 = time.time()
        last_err = None

        for target_model in candidate_models:
            payload = {
                "model": target_model,
                "messages": messages,
                "max_tokens": eff_max_tokens,
                "temperature": eff_temp,
                "reasoning_effort": kwargs.get("reasoning_effort") or "high",
                "stream": False
            }

            if is_json:
                payload["response_format"] = {"type": "json_object"}

            max_attempts = len(self.api_keys)
            all_exhausted = True
            model_not_found = False

            for attempt in range(max_attempts):
                active_key = self._acquire_key()
                headers = {
                    "Authorization": f"Bearer {active_key}",
                    "Content-Type": "application/json"
                }
                try:
                    logger.info(f"[NVIDIA_NIM] Dispatching {target_model} via key {active_key[:14]}... (tokens={eff_max_tokens}, temp={eff_temp:.2f}, json={is_json}, stream=False)...")
                    req_timeout = max(300, min(3600, int(eff_max_tokens * 0.005) + 300))
                    resp = requests.post(
                        self.endpoint,
                        headers=headers,
                        json=payload,
                        stream=False,
                        timeout=req_timeout
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        choice = data.get("choices", [{}])[0]
                        message = choice.get("message", {})
                        content = message.get("content", "") or ""
                        reasoning = message.get("reasoning_content", "") or ""

                        duration = time.time() - t0
                        logger.info(f"[NVIDIA_NIM] Response in {duration:.2f}s | Reasoning: {len(reasoning)} chars | Content: {len(content)} chars")

                        # If content is empty because reasoning consumed all tokens, fall back to reasoning text
                        if not content and reasoning:
                            content = reasoning

                        with self._pool_lock:
                            self.total_calls += 1
                            self.total_reasoning_chars += len(reasoning)

                        audit_entry = {
                            "timestamp": time.time(),
                            "model": target_model,
                            "key_used": active_key[:14] + "...",
                            "duration_sec": duration,
                            "reasoning_len": len(reasoning),
                            "content_len": len(content),
                            "status": "success",
                            "attempt": attempt + 1
                        }
                        with self._pool_lock:
                            self.call_audit_log.append(audit_entry)

                        return {
                            "text": content,
                            "content": content,
                            "thinking": reasoning,
                            "reasoning_content": reasoning,
                            "model_used": target_model,
                            "key_used": active_key[:14] + "...",
                            "elapsed": duration,
                            "provider": "nvidia_nim"
                        }
                    elif resp.status_code == 429:
                        self._mark_key_cooldown(active_key, seconds=10.0 * (attempt + 1))
                        logger.warning(f"[RATE_LIMIT] 429 on key {active_key[:14]}... Failover to next key in pool (Attempt {attempt+1}/{max_attempts})...")
                        time.sleep(1.5 * (attempt + 1))
                    elif resp.status_code in (502, 503, 504):
                        self._mark_key_cooldown(active_key, seconds=15.0 * (attempt + 1))
                        logger.warning(f"[SERVER_TIMEOUT] NVIDIA NIM status {resp.status_code} on key {active_key[:14]}... (Attempt {attempt+1}/{max_attempts})")
                        if resp.status_code == 504:
                            logger.warning(f"[MODEL_TIMEOUT_504] Model {target_model} returned 504 Gateway Timeout (upstream latency >300s). Failing over to next candidate model immediately.")
                            self._mark_model_cooldown(target_model, seconds=300.0)
                            break
                        time.sleep(2.0)
                    elif resp.status_code == 404:
                        all_exhausted = False
                        model_not_found = True
                        self._mark_model_cooldown(target_model, seconds=3600.0)
                        logger.warning(f"[MODEL_NOT_FOUND] Model {target_model} returned 404 on NVIDIA NIM. Failing over immediately to next candidate...")
                        break
                    elif resp.status_code in (400, 422):
                        all_exhausted = False
                        try:
                            from backend.llm_manager import _extract_server_max_tokens_from_error
                            cur_tok = int(payload.get("max_tokens", eff_max_tokens))
                            adapted = _extract_server_max_tokens_from_error(resp.text, cur_tok)
                            if adapted and adapted < cur_tok:
                                logger.info(f"[TOKEN_ADAPT] Endpoint capped max_tokens ({cur_tok} -> {adapted}) for {target_model}. Retrying immediately.")
                                payload["max_tokens"] = adapted
                                eff_max_tokens = adapted
                                continue
                        except Exception:
                            pass
                        logger.warning(f"[API_STATUS] NVIDIA NIM status {resp.status_code} on key {active_key[:14]}...: {resp.text[:200]}")
                        time.sleep(1.0)
                    else:
                        all_exhausted = False
                        logger.warning(f"[API_STATUS] NVIDIA NIM status {resp.status_code} on key {active_key[:14]}...: {resp.text[:200]}")
                        if resp.status_code in (401, 403):
                            self._mark_key_cooldown(active_key, seconds=300.0)
                        time.sleep(2.0 * (attempt + 1))
                except requests.exceptions.Timeout:
                    logger.warning(f"[TIMEOUT] NVIDIA NIM request timed out after {req_timeout}s on key {active_key[:14]}... (Attempt {attempt+1}/{max_attempts})")
                    self._mark_key_cooldown(active_key, seconds=15.0)
                    if attempt >= 1:
                        logger.warning(f"[MODEL_TIMEOUT] Model {target_model} timed out consecutively. Failing over to next candidate model.")
                        self._mark_model_cooldown(target_model, seconds=300.0)
                        break
                    time.sleep(1.0)
                except Exception as e:
                    all_exhausted = False
                    last_err = e
                    logger.warning(f"[REQ_ERROR] Request failed on key {active_key[:14]}...: {e} (Attempt {attempt+1}/{max_attempts})")
                    time.sleep(1.0)

            # If all attempts for this model were 429 rate limits or server timeouts, put this model on cooldown and try next candidate
            if all_exhausted:
                cd_sec = 30.0 if "flash" in target_model.lower() else 120.0
                self._mark_model_cooldown(target_model, seconds=cd_sec)
                logger.warning(f"[MODEL_FAILOVER] Rate limit or server timeout across all pooled keys for {target_model}. Attempting failover model (cooldown {cd_sec:.0f}s)...")
            elif model_not_found:
                continue

        # Fallback if all attempts failed
        duration = time.time() - t0
        with self._pool_lock:
            self.call_audit_log.append({
                "timestamp": time.time(),
                "model": req_model,
                "duration_sec": duration,
                "status": "failed",
                "error": str(last_err)
            })
        return {
            "text": f"Error: All {max_attempts} NVIDIA NIM requests failed. Last error: {last_err}",
            "error": str(last_err),
            "elapsed": duration,
            "provider": "nvidia_nim"
        }

    def run_sync(self, *args, **kwargs) -> Dict[str, Any]:
        return self.run(*args, **kwargs)

    async def run_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        return await asyncio.to_thread(self.run, prompt=prompt, **kwargs)

    def run_structured(self, prompt: str, response_model: Any, **kwargs) -> Any:
        schema_desc = ""
        try:
            if hasattr(response_model, "model_json_schema"):
                schema_desc = json.dumps(response_model.model_json_schema(), indent=2)
            elif hasattr(response_model, "schema"):
                schema_desc = json.dumps(response_model.schema(), indent=2)
        except Exception:
            pass

        full_prompt = f"{prompt}\n\nStrict requirement: Output a JSON object adhering to this schema:\n{schema_desc}"
        res = self.run(full_prompt, **kwargs)
        raw_text = res.get("text", "")

        # Extract JSON substring
        cleaned = raw_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1:
            cleaned = cleaned[start:end+1]

        try:
            if hasattr(response_model, "model_validate_json"):
                return response_model.model_validate_json(cleaned)
            elif hasattr(response_model, "parse_raw"):
                return response_model.parse_raw(cleaned)
            elif hasattr(response_model, "model_validate"):
                return response_model.model_validate(json.loads(cleaned))
            else:
                return json.loads(cleaned)
        except Exception:
            # Fallback to loose dict
            try:
                return json.loads(cleaned)
            except Exception:
                return {"error": "Failed to parse JSON", "raw": raw_text}

    async def run_structured_async(self, prompt: str, response_model: Any, **kwargs) -> Any:
        return await asyncio.to_thread(self.run_structured, prompt=prompt, response_model=response_model, **kwargs)

    async def stream_async(self, prompt: str, **kwargs):
        res = await self.run_async(prompt, **kwargs)
        if res.get("thinking"):
            yield {"type": "thinking", "content": res["thinking"]}
        yield {"type": "text", "content": res.get("text", "")}

if __name__ == "__main__":
    key = get_nvidia_key()
    mgr = NvidiaNIMManager(api_key=key)
    print("Testing NvidiaNIMManager with max_tokens=2048...")
    out = mgr.run("In 15 words: state the thermodynamic effect of Spike N501Y mutation.")
    print("Elapsed:", out.get("elapsed"))
    print("Thinking len:", len(out.get("thinking", "")))
    print("Text:", out.get("text"))
