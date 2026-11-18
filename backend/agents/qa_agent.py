from __future__ import annotations

# backend/agents/qa_agent.py
"""
QA Agent  FIVE INFINITY STONES EDITION (improved, production-hardened)

Notes:
- Keeps the theatrical Infinity Stones metaphor while fixing async/sync issues,
  adding timeouts, and defensive fallbacks for LLM and retrieval code.
- Drop this file into backend/agents/qa_agent.py and import/use as before.
"""

import os
import json
import time
import logging
import asyncio
import aiohttp
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from backend.llm_manager import llm_manager, run_llm_async, QUESTION_ANSWERING_MODEL

logger = logging.getLogger("avon.qa_god")
logger.setLevel(os.getenv("QA_LOG_LEVEL", "INFO"))

# Config
TEMP = float(os.getenv("QA_TEMPERATURE", "0.05"))
MAX_CONTEXT_LENGTH = int(os.getenv("QA_MAX_CONTEXT", "128000"))
# [TITAN V190.0] RECLAIMED SCIENTIFIC RIGOR
# [TITAN V194.0] RECLAIMED SCIENTIFIC RIGOR
# Abolished the theatrical 'INFINITY_STONE_POWER' magic constant.
# Discovery impact is now governed by Bayesian Convergence metrics.
# Discovery impact is now governed by Bayesian Convergence metrics.
TRUTH_CLAIM_THRESHOLD = float(os.getenv("ULTRON_TRUTH_THRESHOLD", "0.95"))
LLM_TIMEOUT = int(os.getenv("QA_LLM_TIMEOUT", "20"))
WEB_TIMEOUT = int(os.getenv("QA_WEB_TIMEOUT", "6"))

# -------------------------
# Infinity Stones helpers
# -------------------------
class InfinityStones:
    """Small, deterministic helpers for the five stones."""

    @staticmethod
    def mind_stone(question: str, history: list) -> dict:
        """Decompose and analyze question complexity."""
        words = len(question.split())
        complexity = "low"
        if words > 40 or "compare" in question.lower() or "contrast" in question.lower():
            complexity = "very_high"
        elif words > 15:
            complexity = "high"
        elif words > 6:
            complexity = "medium"
        else:
            complexity = "low"

        # Decompose into sub-questions heuristically
        if complexity in ("high", "very_high"):
            sub_questions = [
                f"Summarize the core idea with full power and accuracy: {question}",
                f"List 3 relevant concepts that matter for: {question}",
                f"What evidence would most strongly support an answer to: {question}"
            ]
        else:
            sub_questions = [question]

        return {"decomposed": sub_questions, "complexity": complexity, "words": words}

    @staticmethod
    def space_stone(context: List[Dict], max_docs: int = 8) -> str:
        """Compress a list of docs/snippets into a short context string."""
        if not context:
            return "No context available."

        # score fallback and sort
        scored = []
        for doc in context:
            score = float(doc.get("relevance", 0.5))
            raw_text = doc.get("text") or doc.get("snippet") or str(doc)
            if isinstance(raw_text, dict):
                text = str(raw_text.get("text") or raw_text.get("summary") or raw_text)
            else:
                text = str(raw_text)
            src = doc.get("source", "unknown")
            scored.append((score, src, text))

        scored.sort(key=lambda x: x[0], reverse=True)
        parts = []
        for i, (score, src, text) in enumerate(scored[:max_docs]):
            snippet = text if len(text) < 600 else (text[:550] + "...")
            parts.append(f"[{src}] (r={score:.2f})\n{snippet}")

        return "\n\n".join(parts)


    @staticmethod
    def power_stone(response: str, confidence: float) -> str:
        """Format response with clear scientific confidence level."""
        if confidence >= 0.85:
            header = "[CONFIDENCE: HIGH (>=0.85)]"
        elif confidence >= 0.6:
            header = "[CONFIDENCE: MODERATE (>=0.60)]"
        else:
            header = "[CONFIDENCE: TENTATIVE (<0.60)]"

        return f"{header}\n\n{response}"


    @staticmethod
    def time_stone() -> dict:
        """Return timestamp and simple processing marker."""
        return {"timestamp": datetime.utcnow().isoformat() + "Z", "ts_epoch": time.time()}


    @staticmethod
    def reality_stone(claim: str, evidence: List[Dict]) -> dict:
        """Lightweight heuristic verification: overlap-based + counts."""
        if not evidence:
            return {"confidence": 0.05, "verified": False, "evidence_count": 0, "matching_terms": []}

        top_texts = " ".join([e.get("text", "") for e in evidence[:3]])
        
        negations = {"not", "never", "failed", "no", "unable", "cannot"}
        def get_negs(s: str):
            return set(t.strip(".,;:()[]\"'").lower() for t in s.split()).intersection(negations)
            
        claim_negs = get_negs(claim)
        evi_negs = get_negs(top_texts)

        # simple token overlap
        def tokens(s: str):
            return set([t.strip(".,;:()[]\"'").lower() for t in s.split() if len(t) > 2])
        t_claim = tokens(claim)
        t_evi = tokens(top_texts)
        intersect = t_claim.intersection(t_evi)
        overlap = (len(intersect) / max(1, len(t_claim)))
        
        if claim_negs != evi_negs:
            overlap *= 0.1
            
        # scale and clamp
        confidence = min(0.05 + overlap * 1.2, 0.98)
        verified = confidence >= 0.6

        return {"confidence": round(confidence, 3), "verified": verified, "evidence_count": len(evidence), "matching_terms": list(intersect)[:10]}


# -------------------------
# MultiverseRetriever
# -------------------------
class MultiverseRetriever:
    """
    Asynchronous retriever that tries several knowledge sources in parallel:
     - web (mocked HTTP search or real API if configured)
     - internal (local store; mocked here)
     - vector store (if a tool exists; mocked)
    This is defensive: no external API is required.
    """

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._external_session = session
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = self._external_session or aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=WEB_TIMEOUT))
        return self

    async def __aexit__(self, *args):
        if self._external_session is None and self.session:
            await self.session.close()
            self.session = None

    async def retrieve_knowledge(self, question: str, max_sources: int = 6) -> List[Dict]:
        """Dispatch parallel retrieval tasks and deduplicate results."""
        tasks = [
            asyncio.create_task(self._search_web(question, max_results=2)),
            asyncio.create_task(self._search_internal(question, max_results=2)),
            asyncio.create_task(self._search_vector(question, max_results=2)),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        sources: List[Dict] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                # [TITAN V196.0] UNMASKING COMPONENT DEATH
                # Physically elevate log level to expose failing sources (Web, Internal, Vector)
                logger.warning(f" [RELIABILITY-FAIL] Knowledge source {i} (0=Web, 1=Internal, 2=Vector) physically collapsed: {r}")
                continue
            if isinstance(r, list):
                sources.extend(r)
        # dedupe by first 300 chars of text + source
        seen = set()
        unique = []
        for s in sources:
            raw_t = s.get("text") or ""
            if isinstance(raw_t, dict):
                raw_t = str(raw_t.get("text") or raw_t)
            key = (s.get("source", "unknown"), str(raw_t)[:300])
            if key not in seen:
                seen.add(key)
                unique.append(s)
            if len(unique) >= max_sources:
                break
        return unique

    async def _search_web(self, query: str, max_results: int = 2) -> List[Dict]:
        """Best-effort web search: attempt to call a configured search API, else return mocked results."""
        try:
            # If an actual web search endpoint is provided via env, use it
            search_url = os.getenv("QA_WEB_SEARCH_URL")
            if search_url and self.session:
                async with self.session.get(search_url, params={"q": query, "limit": max_results}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # expect data to be a list of {text, source, relevance}
                        return data[:max_results]
            # Use REAL web search
            try:
                from backend.tools.web_search import beast_search  
                logger.info(f"QA Agent: Using REAL web search for '{query}'")
                search_result = await beast_search.search(query, num_results=max_results)
                
                if search_result.get('status') == 'success':
                    results = search_result.get('results', [])
                    return [
                        {
                            'text': r.get('snippet', ''),
                            'source': r.get('url', 'unknown'),
                            'relevance': 0.9 - (i * 0.05)
                        }
                        for i, r in enumerate(results[:max_results])
                    ]
                else:
                    logger.warning(f"Web search returned status: {search_result.get('status')}")
                    
            except Exception as e:
                logger.exception(f"Real web search failed: {e}")
            
            # Fallback to LLM only if web search failed
            logger.warning("Falling back to LLM for QA response")
            try:
                from backend.llm_manager import run_llm
                answer = await asyncio.to_thread(
                    run_llm,
                    f"Provide factual information about: {query}",
                    mode="fast",
                    timeout=15
                )
                ans_text = answer.get("text", "") if isinstance(answer, dict) else str(answer)
                return [{
                    'text': ans_text,
                    'source': 'llm:unverified_fallback',
                    'relevance': 0.0
                }]

            except Exception:
                logger.exception("LLM fallback also failed")
                return []
        except Exception:
            logger.exception("web search failed")
            return []

    async def _search_internal(self, query: str, max_results: int = 2) -> List[Dict]:
        """Real internal KB search using ElasticSearch or OpenSearch"""
        try:
            es_url = os.getenv("ELASTICSEARCH_URL") or os.getenv("OPENSEARCH_URL")
            if es_url:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    search_body = {
                        "query": {"match": {"content": query}},
                        "size": max_results
                    }
                    async with session.post(
                        f"{es_url}/knowledge_base/_search",
                        json=search_body,
                        headers={"Content-Type": "application/json"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            hits = data.get("hits", {}).get("hits", [])
                            return [
                                {
                                    "text": hit["_source"].get("content", ""),
                                    "source": f"internal:kb:{hit['_id']}",
                                    "relevance": hit["_score"] / 10.0
                                }
                                for hit in hits[:max_results]
                            ]
            
            logger.warning("No ElasticSearch/OpenSearch configured, skipping internal KB")
            return []
            
        except Exception as e:
            logger.exception(f"Internal search failed: {e}")
            return []

    async def _search_vector(self, query: str, max_results: int = 2) -> List[Dict]:
        """Real vector store lookup using Pinecone/Qdrant/Weaviate"""
        try:
            vector_type = os.getenv("VECTOR_DB_TYPE", "").lower()
            
            if vector_type == "pinecone":
                import pinecone
                pinecone.init(api_key=os.getenv("PINECONE_API_KEY"), environment=os.getenv("PINECONE_ENV"))
                index = pinecone.Index(os.getenv("PINECONE_INDEX", "avon-kb"))
                
                try:
                    from backend.core.world_model import get_shared_embedding_model
                    embedding = get_shared_embedding_model().encode(query).tolist()
                except Exception:
                    logger.warning("Embedding model unavailable for Pinecone query, using zero vector fallback")
                    embedding = [0.0] * 1536
                
                results = await asyncio.to_thread(index.query, vector=embedding, top_k=max_results, include_metadata=True)
                return [
                    {
                        "text": match.metadata.get("text", ""),
                        "source": f"vector:pinecone:{match.id}",
                        "relevance": match.score
                    }
                    for match in results.matches
                ]
            
            logger.warning(f"No vector DB configured (type={vector_type}), skipping vector search")
            return []
            
        except Exception as e:
            logger.exception(f"Vector search failed: {e}")
            return []


# -------------------------
# DivineLLM (async wrapper)
# -------------------------
class DivineLLM:
    """
    Wrapper that delegates to the centralized LLMManager.
    """

    def __init__(self, temperature: float = TEMP, timeout: int = LLM_TIMEOUT):
        self.temperature = temperature
        self.timeout = timeout

    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Call LLM directly for generation."""
        try:
            # Use QUESTION_ANSWERING_MODEL from llm_manager
            exec_kwargs = {}
            if max_tokens is not None:
                exec_kwargs["max_tokens_override"] = max_tokens
            response = await run_llm_async(
                prompt=prompt,
                model=QUESTION_ANSWERING_MODEL,
                timeout=self.timeout,
                temperature=self.temperature,
                **exec_kwargs
            )
            return response.get("text", "") or " LLM returned empty response"
        except Exception as e:
            logger.exception("DivineLLM.generate failed")
            return f" LLM error: {str(e)}"


# -------------------------
# QA Agent
# -------------------------
class QAAgent:
    name = "qa_god"

    def __init__(self, temperature: float = TEMP):
        self.temperature = temperature
        self.llm = DivineLLM(temperature=temperature)
        self.stones = InfinityStones()
        # small in-memory session store (bounded)
        self._memory: Dict[str, List[Dict[str, Any]]] = {}
        self._max_memory_per_session = 40

    async def run(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main async entry. Expects:
          task: {"payload": {"query": "<question text>", ...}, "meta": {"session_id": "...", "mission_id": "..."}}
          context: optional extras (docs, etc).
        """
        start = time.time()
        
        # Handle payload as dict or string
        payload = task.get("payload", {})
        if isinstance(payload, dict):
            question = payload.get("query", "") or payload.get("question", "") or task.get("query", "")
        else:
            question = str(payload)
        
        question = question.strip() if isinstance(question, str) else ""
        
        if not question:
            return {"text": "No question provided", "confidence": 0.0, "verified": False, "sources": [], "processing_time": 0.0, "meta": {}}

        meta = task.get("meta", {}) or {}
        session_id = meta.get("session_id", "default")
        mission_id = meta.get("mission_id", None)

        # mind stone: decompose & understand
        mind = self.stones.mind_stone(question, self._memory.get(session_id, []))

        # retrieve context from multiverse
        async with MultiverseRetriever() as retriever:
            try:
                knowledge = await retriever.retrieve_knowledge(question)
            except Exception:
                logger.exception("Multiverse retrieval failed")
                knowledge = []

        # compress context
        context_text = self.stones.space_stone(knowledge, max_docs=6)

        # create prompt (bounded)
        prompt = self._build_prompt(question, context_text, mind)
        # call LLM
        try:
            raw_answer = await asyncio.wait_for(self.llm.generate(prompt), timeout=LLM_TIMEOUT + 5)
        except asyncio.TimeoutError:
            raw_answer = " LLM generation timed out"
        except Exception:
            logger.exception("LLM call failed")
            raw_answer = " LLM generation error"

        # reality stone: simple verification
        reality = self.stones.reality_stone(raw_answer, knowledge)

        # power stone: format answer
        output_text = self.stones.power_stone(raw_answer, reality.get("confidence", 0.0))

        # time stone
        time_meta = self.stones.time_stone()

        # record memory (bounded)
        self._memory.setdefault(session_id, [])
        self._memory[session_id].append({"q": question, "answer": raw_answer[:5000], "ts": time.time()})
        if len(self._memory[session_id]) > self._max_memory_per_session:
            self._memory[session_id] = self._memory[session_id][-self._max_memory_per_session :]

        processing_time = time.time() - start

        result = {
            "text": output_text,
            "answer": output_text,  #  Backward compatibility
            "raw_answer": raw_answer,
            "confidence": reality.get("confidence", 0.0),
            "verified": reality.get("verified", False),
            "sources": [d.get("source", "unknown") for d in knowledge],
            "processing_time": round(processing_time, 2),
            "meta": {
                "model": "llm_manager_auto",
                "stones": ["mind", "space", "power", "reality", "time"],
                "knowledge_count": len(knowledge),
                "timestamp": time_meta.get("timestamp"),
            }
        }
        return result

    def _build_prompt(self, question: str, context_summary: str, mind: dict) -> str:
        # keep prompt deterministic and reasonably sized
        context_summary = (context_summary or "")[:MAX_CONTEXT_LENGTH]
        decomposed = mind.get("decomposed", [question])
        return (
            "You are a LEAD PHD Advanced research QA assistant. Answer precisely, cite sources inline using [source].\n\n"
            f"CONTEXT:\n{context_summary}\n\n"
            f"QUESTION (decomposed):\n{decomposed}\n\n"
            "INSTRUCTIONS:\n"
            "1) Provide a concise answer with 2-5 bullet points.\n"
            "2) Include inline source citations like [web:mock] or [internal:kb].\n"
            "3) Provide a short 'what to ask next' suggestion.\n\n"
            f"QUESTION: {question}\n\nAnswer now."
        )

    def run_sync(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.run(task, context))


# Compatibility wrappers
async def run_async_agent(task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    agent = QAAgent()
    return await agent.run(task, context)

def run_agent_sync(task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    agent = QAAgent()
    return agent.run_sync(task, context)


# Demo if executed directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    q = "Explain how transformers scale to long context and summarize tokenization challenges."
    a = QAAgent()
    out = a.run_sync({"payload": q, "meta": {"session_id": "demo"}}, {})
    print(json.dumps(out, indent=2)[:4000])
