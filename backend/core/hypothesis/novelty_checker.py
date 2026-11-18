from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import numpy as np
import os
import asyncio
from backend.core.hypothesis.models import Hypothesis, NoveltyReport

logger = logging.getLogger(__name__)

def get_st_model(model_name: str):
    """Bridge to the global shared embedding model singleton."""
    try:
        from backend.core.world_model import get_shared_embedding_model
        return get_shared_embedding_model()
    except Exception as e:
        logger.error(f"Failed to load SentenceTransformer for NoveltyChecker: {e}")
        return None

class NoveltyChecker:
    """
    Detects if a new thought/hypothesis is too similar to previous ones.
    Uses local embeddings (SentenceTransformers) for privacy and speed.
    """
    def __init__(self, model_name: str = None, threshold: float = 0.85, llm_manager=None, world_model=None):
        from backend.llm_manager import EMBEDDING_MODEL as _DEFAULT_EMB
        self.base_threshold = threshold
        self.model_name = model_name or _DEFAULT_EMB
        self.history_embeddings = []
        self.history_texts = []
        self.llm_manager = llm_manager
        self.world_model = world_model
        
        # Embedding Cache: Prevent O(N^2) embedding re-calculations
        self._embedding_cache = {}
        
        # Load via singleton
        self.model = get_st_model(self.model_name)

    def _get_cached_embedding(self, h: Hypothesis) -> np.ndarray:
        """Fetch or compute embedding for a hypothesis."""
        h_text = f"{h.statement} {h.rationale}"
        cache_key = (h.id, h_text)
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
            
        h_emb = self.model.encode(h_text)
        self._embedding_cache[cache_key] = h_emb
        return h_emb

    def check_novelty(self, hypothesis: Hypothesis, existing_hypotheses: List[Hypothesis] = []) -> NoveltyReport:
        """
        Check novelty of a hypothesis against history and existing pool.
        Returns NoveltyReport.
        """
        text = f"{hypothesis.statement} {hypothesis.rationale}"
        
        # [RIGOR FIX] Domain Purity Pre-Filter
        import re
        system_leakage_substrings = [
            "/Users/", "traceback", "Traceback", "Exception:", "node_modules", 
            "pip install", "search query", "logical operator", "virtual environment", 
            "stdout", "stderr", "syntax error"
        ]
        system_leakage_words = [
            "npm", "pip", "venv", 
            "docker", "colima", "sqlite", "neo4j"
        ]
        words_pattern = r"\b(" + "|".join(re.escape(w) for w in system_leakage_words) + r")\b"
        has_leak = any(x in text for x in system_leakage_substrings) or bool(re.search(words_pattern, text, re.IGNORECASE))
        if has_leak:
            logger.warning(f" [NOVELTY_CHECKER] Rejected hypothesis due to domain impurity (OS/API leak detected): {text[:50]}...")
            return NoveltyReport(
                hypothesis_id=hypothesis.id, novelty_score=0.0, is_novel=False,
                prior_art_detected=True, max_similarity=1.0,
                summary="Rejected: Contains OS/API logs or meta-reasoning."
            )
        
        # Adaptive Novelty Threshold: Relax threshold in dense research spaces
        adaptive_threshold = self.base_threshold
        if len(existing_hypotheses) > 10:
            adaptive_threshold = min(0.92, self.base_threshold + 0.05)
            logger.debug(f" [ADAPTIVE] Relaxing novelty threshold to {adaptive_threshold:.2f} due to pool density.")

        if not self.model:
            # Fallback: Jaccard Similarity (Set overlap)
            current_words = set(text.lower().split())
            max_sim = 0.0
            most_similar_text = ""
            
            # Check history & active pool
            all_prev = self.history_texts + [f"{h.statement} {h.rationale}" for h in existing_hypotheses if h.id != hypothesis.id]
            
            for prev_text in all_prev:
                prev_words = set(prev_text.lower().split())
                intersection = len(current_words.intersection(prev_words))
                union = len(current_words.union(prev_words))
                sim = intersection / union if union > 0 else 0.0
                if sim > max_sim:
                    max_sim = sim
                    most_similar_text = prev_text

            is_novel = max_sim < (adaptive_threshold - 0.2) # Jaccard is naturally lower
            if is_novel:
                self._update_history(text, None)
            
            return NoveltyReport(
                hypothesis_id=hypothesis.id,
                novelty_score=1.0 - max_sim,
                is_novel=is_novel,
                prior_art_detected=not is_novel,
                max_similarity=max_sim,
                summary=f"Jaccard Similarity: {max_sim:.2f}. {'Too similar' if not is_novel else 'Novel'}."
            )

        # Embed current text
        current_embedding = self.model.encode(text)

        # Collect comparisons
        comparisons = []
        for i, hist_emb in enumerate(self.history_embeddings):
            if hist_emb is not None:
                comparisons.append({"text": self.history_texts[i], "embedding": hist_emb})
            
        for h in existing_hypotheses:
            if h.id != hypothesis.id:
                h_text = f"{h.statement} {h.rationale}"
                h_emb = self._get_cached_embedding(h)
                comparisons.append({"text": h_text, "embedding": h_emb})

        if not comparisons:
            self._update_history(text, current_embedding)
            return NoveltyReport(
                hypothesis_id=hypothesis.id, novelty_score=1.0, is_novel=True,
                prior_art_detected=False, max_similarity=0.0,
                summary="First hypothesis in session."
            )

        # Calculate similarities
        max_sim = 0.0
        most_similar_item = None
        norm_curr = float(np.linalg.norm(current_embedding))
        
        for item in comparisons:
            # Cosine similarity
            norm_other = float(np.linalg.norm(item["embedding"]))
            if norm_curr <= 1e-12 or norm_other <= 1e-12:
                sim = 0.0
            else:
                sim = float(np.dot(current_embedding, item["embedding"])) / (norm_curr * norm_other)
                sim = max(-1.0, min(1.0, sim))
            if sim > max_sim:
                max_sim = float(sim)
                most_similar_item = item

        is_novel = max_sim < adaptive_threshold
        novelty_score = max(0.0, min(1.0, 1.0 - max_sim))
        summary = f"Similarity: {max_sim:.2f}."

        # Logical Differentiation Analysis (LLM Fallback for highly similar texts)
        if not is_novel and self.llm_manager and most_similar_item:
            logger.info("Semantic similarity threshold exceeded. Initiating logical differentiation analysis.")
            prompt = f"""You are a principal investigator evaluating the novelty of a scientific hypothesis for a top‑tier journal.
Two hypotheses have been flagged as semantically similar by an embedding model, but that may be superficial.
Your job is to determine whether they are **scientifically distinct** — i.e., whether they propose fundamentally different causal mechanisms, mathematical relationships, operational estimands, or falsification regimes.

You must ground your judgment in the scientific content, not the wording.

Hypothesis A (New):
{text}

Hypothesis B (Prior Art):
{most_similar_item['text']}

────────────────────────────────────────────────────────
COMPARISON PROTOCOL (execute internally):
────────────────────────────────────────────────────────

1. **Core Mechanism**:
   - Identify the proposed causal chain in each hypothesis.
   - Do they share the same causal graph (nodes and edges)? If the graphs are isomorphic but only the variable names differ, they are not distinct.

2. **Mathematical Formalism**:
   - Extract or infer the core functional relationship (equation) from each.
   - Are the equations structurally different (e.g., linear vs. non‑linear, additive vs. multiplicative, different powers or interaction terms)? If the equations are algebraically equivalent, they are not distinct.

3. **Estimand and Falsification**:
   - What quantity does each hypothesis claim to estimate or predict?
   - How would each be falsified? If both predict the same outcome under the same experimental conditions and are killed by the same negative result, they are not distinct.

4. **Domain of Applicability / Regime**:
   - Do the hypotheses apply to different physical regimes, scales, or boundary conditions that would lead to qualitatively different predictions? If so, they may be distinct even if the mathematics appears similar.

5. **Novelty of Insight**:
   - Does Hypothesis A introduce a new interaction, a hidden variable, a previously overlooked feedback loop, or a non‑trivial coupling that is absent from Hypothesis B?

────────────────────────────────────────────────────────
OUTPUT FORMAT (strict JSON only, no prose):
────────────────────────────────────────────────────────

{{
  "is_distinct": true/false,
  "divergence_score": 0.0 to 1.0,
  "reasoning": "Concise but specific justification citing the mechanisms, equations, or falsification conditions that differ or coincide.",
  "shared_elements": ["list", "of", "elements", "that", "are", "identical"],
  "distinct_elements": ["list", "of", "elements", "that", "differ", "fundamentally"]
}}

Rules:
- If both hypotheses are too vague to extract a mechanism or equation, set is_distinct=false, divergence_score=0.0, and explain why.
- Do not invent content that isn’t implied by the text.
- Return ONLY the JSON.
"""
            try:
                from backend.llm_manager import TASK_ROUTING_MODEL
                model_str = TASK_ROUTING_MODEL[0] if isinstance(TASK_ROUTING_MODEL, tuple) else TASK_ROUTING_MODEL
                response = self.llm_manager.run(prompt=prompt, model=model_str, temperature=0.0)
                content = response if isinstance(response, str) else response.get("text", "{}")
                from backend.utils.json_repair import repair_json
                parsed = repair_json(content)
                if isinstance(parsed, dict):
                    if parsed.get("is_distinct", False):
                        is_novel = True
                        div_score = float(parsed.get("divergence_score", 0.5))
                        novelty_score = 1.0 - (max_sim * (1.0 - div_score))
                        summary += f" Logical distinction verified: {parsed.get('reasoning', 'Distinct mechanisms identified.')}"
                    else:
                        summary += f" Logical overlap verified: {parsed.get('reasoning', 'No distinct mechanisms identified.')}"
                else:
                    logger.warning("Logical differentiation returned unparseable JSON response")
                    summary += " Too similar to prior work (Unverified distinction)."
            except Exception as e:
                logger.error(f"Logical differentiation failed: {e}")
                summary += " Too similar to prior work (Semantic match)."
        elif not is_novel:
            summary += " Too similar to prior work."
        else:
            summary += " Novelty confirmed."

        if is_novel:
            self._update_history(text, current_embedding)

        report = NoveltyReport(
            hypothesis_id=hypothesis.id,
            novelty_score=novelty_score,
            is_novel=is_novel,
            prior_art_detected=not is_novel,
            max_similarity=max_sim,
            summary=summary
        )

        # [TITAN V240.0] EPISTEMIC BINDING
        # Physically save the novelty finding to the World Model.
        if self.world_model and os.environ.get("ULTRON_LOG_NOVELTY_FACTS", "false").lower() == "true":
            try:
                import hashlib
                fact_id = hashlib.sha256(f"novelty_{hypothesis.id}".encode()).hexdigest()[:16]
                self.world_model.commit_verified_fact(
                    key="novelty_check",
                    value=f"Hypothesis {hypothesis.id} novelty check: {'NOVEL' if is_novel else 'REDUNDANT'}",
                    source="novelty_checker",
                    confidence=1.0 if is_novel else max_sim,
                    metadata={
                        "fact_id": fact_id,
                        "hypothesis_id": hypothesis.id,
                        "novelty_score": novelty_score,
                        "max_similarity": max_sim,
                        "summary": summary
                    }
                )
                logger.info(f" [NOVELTY_CHECKER] Committed novelty verdict for {hypothesis.id} to World Model.")
            except Exception as wm_err:
                logger.error(f" [NOVELTY_CHECKER] Failed to commit to World Model: {wm_err}")
        return report

    def _update_history(self, text, embedding):
        MAX_HISTORY = 1000
        self.history_embeddings.append(embedding)
        self.history_texts.append(text)
        if len(self.history_embeddings) > MAX_HISTORY:
            self.history_embeddings = self.history_embeddings[-MAX_HISTORY:]
            self.history_texts = self.history_texts[-MAX_HISTORY:]

    def clear(self):
        self.history_embeddings = []
        self.history_texts = []
        self._embedding_cache.clear()
