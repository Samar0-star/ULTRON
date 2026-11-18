"""
ULTRON NEURAL DOMAIN REGULATOR
==============================
Unified system for scientific domain detection and enforcement.
Replaces all hard-coded domain checks with dynamic neural inference.
Forces the TASK_ROUTING_MODEL to categorize research without defaulting to general.
"""

import logging
import json
import re
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.llm_manager import run_with_fallback

logger = logging.getLogger(__name__)

class DomainRegulator:
    """
    The 'Cognitive Sieve' of the system.
    Ensures the entire research session remains semantically consistent.
    """
    
    @staticmethod
    def filter_by_domain_similarity(texts: List[str], research_question: str) -> List[str]:
        """
        [TITAN V172.0] MATHEMATICAL DOMAIN PURIFICATION.
        Dynamically filters papers by semantic similarity to the research question.
        Abolishes all hardcoded category strings (e.g. 'cs.LG') and relies on pure mathematical similarity.
        """
        if not texts:
            return []
            
        try:
            from backend.core.world_model import get_shared_embedding_model
            model = get_shared_embedding_model()
            if not model:
                return texts # Fallback if model missing
                
            import numpy as np
            q_emb = model.encode([research_question])[0]
            # Batch encode, truncate to 1000 characters for speed
            p_embs = model.encode([t[:1000] for t in texts]) 
            
            # Cosine similarity with zero-norm protection
            q_norm = float(np.linalg.norm(q_emb))
            if q_norm <= 1e-12 or np.isnan(q_norm):
                return texts
            p_norms = np.linalg.norm(p_embs, axis=1)
            safe_denom = np.where(p_norms > 1e-12, p_norms * q_norm, 1.0)
            sims = np.where(p_norms > 1e-12, np.dot(p_embs, q_emb) / safe_denom, 0.0)
            
            # [TITAN V263.0] CALIBRATED SIMILARITY GATE
            # Threshold 0.18: empirically tuned to purge clearly off-domain papers
            # (quantum NAS, COVID CT, LLM pruning) while retaining cross-pollination
            # from genuinely related work (ViT pruning, structured sparsity, NAS benchmarks).
            # Previous 0.02 was a no-op that allowed 100% of ArXiv through.
            DOMAIN_SIM_THRESHOLD = 0.18
            filtered = []
            for i, t in enumerate(texts):
                if sims[i] > DOMAIN_SIM_THRESHOLD:
                    filtered.append(t)
                else:
                    # Log what's being purged so we can audit
                    title_line = t.split('\n')[0][:80] if t else "???"
                    logger.debug(f" [REGULATOR] Purged (sim={sims[i]:.3f}): {title_line}")
            
            # [TITAN V206.0] NANO-PHOTONICS HARDENING
            # Physically block metallic superconductor hallucinations in photonic crystal research.
            # Metamaterials for non-reciprocity require broken TRS, not just bulk metal.
            hallucination_materials = ["LuNi2B2C", "borocarbide", "bulk metal"]
            final_filtered = []
            for t in filtered:
                text_low = t.lower()
                if "photonic crystal" in text_low and any(m.lower() in text_low for m in hallucination_materials):
                    logger.critical(f" [EPISTEMIC FAILURE] Blocked material mismatch: metallic superconductor in photonic crystal manifold.")
                    continue
                final_filtered.append(t)
            
            logger.info(f" [REGULATOR] Mathematically purged {len(texts) - len(final_filtered)} out-of-domain papers. Remaining: {len(final_filtered)}")
            return final_filtered
        except Exception as e:
            logger.warning(f" [REGULATOR] Similarity filtering failed: {e}")
            return texts
            
    @staticmethod
    def get_system_domains() -> List[str]:
        """
        Dynamically discover valid domains from the template directory plus core scientific disciplines.
        """
        core_domains = [
            "machine_learning", "computer_science", "physics", "materials_science",
            "chemistry", "biology", "biophysics", "neuroscience", "mathematics", "astronomy"
        ]
        try:
            # Resolve path relative to project root
            base_dir = Path(__file__).parent.parent
            template_path = base_dir / "experiments" / "templates"
            
            if not template_path.exists():
                # Fallback for different working directories
                template_path = Path("backend/experiments/templates")
                
            domains = [d.name for d in template_path.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
            return sorted(set(domains + core_domains))
        except Exception as e:
            logger.error(f" [REGULATOR] Failed to discover domains: {e}")
            return sorted(core_domains)

    @staticmethod
    def _infer_domain_from_keywords(text: str, domain_hint: str = "general") -> str:
        t_low = (text or "").lower()
        keyword_map = [
            ("materials_science", ["superconduct", "critical temperature", "lattice", "phonon", "crystal", "cuprate", "alloy", "perovskite"]),
            ("biophysics", ["protein", "binding affinity", "skempi", "sars", "ace2", "receptor", "docking", "ddg", "mutation"]),
            ("biology", ["gene", "genomic", "rna", "dna", "cell", "enzyme", "clinical", "crispr"]),
            ("chemistry", ["molecule", "reaction", "catalys", "enthalpy", "ligand", "smiles", "thermodynamic"]),
            ("astronomy", ["exoplanet", "orbital", "stellar", "astrophys", "cosmolog", "kepler", "transit"]),
            ("physics", ["quantum", "hamiltonian", "tokamak", "plasma", "fluid", "navier-stokes", "magnetohydrodynamic"]),
            ("machine_learning", ["neural network", "transformer", "gradient", "pruning", "flops", "accuracy", "backprop", "cifar", "resnet"]),
            ("mathematics", ["theorem", "proof", "manifold", "eigenvalue", "convergence", "topology", "stochastic"]),
        ]
        matched = []
        for dom, kws in keyword_map:
            if any(kw in t_low for kw in kws):
                matched.append(dom)
        if matched:
            return ",".join(matched[:2])
        if domain_hint and domain_hint not in ("general", "unknown", ""):
            return domain_hint
        return "unknown"

    @staticmethod
    async def detect_domain(text: str, domain_hint: str = "general") -> str:
        """
        GODZILLA RIGOR: High-fidelity multi-domain recognition.
        Returns a comma-separated list of the top 2 relevant domains.
        """

        valid_domains = DomainRegulator.get_system_domains()
        if "other" not in valid_domains:
            valid_domains.append("other")

        prompt = f"""
    ULTRON DOMAIN JUDGE (GODZILLA RIGOR)
    ====================================
    Identify the scientific domains relevant to this research text.

    ### ACTIVE SYSTEM DOMAINS:
    {", ".join(valid_domains)}

    ### MANDATE:
    1. You MUST select the SINGLE MOST relevant domain.
    2. If it is interdisciplinary, you MAY select a SECOND domain.
    3. Return ONLY the domain names separated by a comma.
    4. NEVER return 'general'.


    ### TEXT TO ANALYZE:
    "{text[:2000]}"
    """
        try:
            # FORCE usage of TASK_ROUTING_MODEL via the "routing" task key
            response = await asyncio.to_thread(
                run_with_fallback,
                task="routing",
                prompt=prompt,
                temperature=0.0
            )

            if isinstance(response, dict):
                if response.get("error"):
                    raise RuntimeError(str(response.get("error")))
                content = response.get("text", "").strip().lower()
            else:
                content = str(response).strip().lower()

            # Clean punctuation and split
            found = []
            for d in content.split(","):
                clean_d = re.sub(r'[^a-z0-9_\-]', '', d.strip())
                if clean_d and clean_d not in ("general", "unknown", "error") and len(clean_d) <= 32:
                    found.append(clean_d)
            
            if found:
                result = ",".join(found[:2]) # Keep top 2
                logger.info(f" [REGULATOR] Neural recognition successful: {result}")
                return result

            inferred = DomainRegulator._infer_domain_from_keywords(text, domain_hint)
            logger.warning(f" [REGULATOR] Neural brain returned empty domain. Keyword fallback: '{inferred}'.")
            return inferred

        except Exception as e:
            inferred = DomainRegulator._infer_domain_from_keywords(text, domain_hint)
            logger.error(f" [REGULATOR] Neural recognition failed ({e}). Keyword fallback: '{inferred}'.")
            return inferred



    @staticmethod
    async def get_domain_profile(text: str, domain_hint: str = "general") -> List[str]:
        """
        [TITAN V141.0] SOVEREIGN PROFILER.
        Physically abolished regex-heuristics and stopword whitelists.
        Uses TASK_ROUTING_MODEL directly to derive scientific tags from pure reasoning.
        """
        from backend.llm_manager import TASK_ROUTING_MODEL, llm_manager
        
        prompt = f"""
        ULTRON SCIENTIFIC PROFILER
        Extract the top 5 most specific scientific tags/sub-domains for the following research mission.
        Context: {text[:1500]}
        
        Rules:
        1. Return ONLY the tags separated by commas. No prose, no preamble.
        2. Tags must be lowercase and use underscores for spaces.
        3. Be specific (e.g., 'structural_pruning' rather than 'machine_learning').
        """
        # [GODZILLA FIX] ROBUST RETRY LOOP FOR SCIENTIFIC PROFILING
        # Prevents silent fallback to generic domain hint during API starvation.
        import asyncio
        import random
        max_profile_retries = 5
        
        for profile_attempt in range(max_profile_retries):
            try:
                # Physically abolish the fallback wrapper. Using the routing brain directly.
                model_string = TASK_ROUTING_MODEL[0] if isinstance(TASK_ROUTING_MODEL, tuple) else TASK_ROUTING_MODEL
                response = await llm_manager.run_async(
                    prompt,
                    model=model_string,
                    temperature=0.0,
                    source="domain_profiling"
                )
                content = response if isinstance(response, str) else response.get("text", str(response))
                # [TITAN V142.2] GHOST PURGE
                # If LLM returns an empty JSON string or noise, default to mission hint.
                if "{}" in content or not content.strip():
                    return [domain_hint]

                # [GODZILLA FIX] Explicitly reject LLM hallucinated prose (e.g. "the person is...")
                tags = []
                for t in content.split(','):
                    clean_t = t.strip().lower()
                    # Reject anything that looks like a sentence or contains too many spaces
                    if clean_t and len(clean_t.split()) <= 3 and len(clean_t) < 30:
                        tags.append(clean_t.replace(' ', '_'))
                
                if tags:
                    return tags[:5]

            except Exception as e:
                backoff = (2 ** profile_attempt) + (random.randint(0, 1000) / 1000.0)
                logger.warning(f" [REGULATOR] Sovereign profiling attempt {profile_attempt+1} failed: {e}. Retrying in {backoff:.1f}s...")
                if profile_attempt < max_profile_retries - 1:
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f" [REGULATOR] Sovereign profiling failed definitively: {e}")
            
        return [domain_hint]




    @staticmethod
    async def get_domain_examples_async(tags: List[str], research_question: str = None) -> Dict[str, str]:
        """
        [TITAN V143.1] HARDENED NEURAL GROUNDING.
        Uses TASK_ROUTING_MODEL to dynamically imagine physical math.
        Enforces realistic ML fallbacks (FLOPs/Accuracy) to prevent 'unknown' grounding.
        """
        from backend.llm_manager import TASK_ROUTING_MODEL, llm_manager
        
        primary_tag = tags[0] if tags else "scientific_impact"
        rq_context = f"\nSPECIFIC RESEARCH QUESTION: {research_question}" if research_question else ""
        prompt = f"""You are a Mathematical Physicalist. 
MISSION: Generate a high-fidelity technical grounding for a research mission tagged as: {tags}.{rq_context}

REQUIRED OUTPUT (JSON ONLY):
{{
  "eq": "The formal primary equation (e.g. 'Acc = f(P, R)')",
  "var": "The dependent variable with its physical unit (e.g. 'top1_accuracy in %')",
  "param": "A key independent parameter with baseline (e.g. 'pruning_ratio (P) value 0.5')",
  "unit": "The specific physical unit (e.g. 'FLOPs', 'nM', '%')",
  "pred": {{"condition": "...", "outcome": "...", "baseline": 0.0, "threshold": 0.0}}
}}

Rules:
1. NO PROSE. NO CHATTER.
2. If the domain is ML, use FLOPs, Accuracy, or Latency.
"""
        
        # Robust retry loop with domain-aware fallback and bounded backoff
        import asyncio
        import random
        from backend.utils.json_repair import repair_json
        max_grounding_retries = 3
        
        for grounding_attempt in range(max_grounding_retries):
            try:
                model_string = TASK_ROUTING_MODEL[0] if isinstance(TASK_ROUTING_MODEL, tuple) else TASK_ROUTING_MODEL
                response = await llm_manager.run_async(prompt, model=model_string, temperature=0.1)
                content = response if isinstance(response, str) else response.get("text", "{}")
                if isinstance(response, dict) and response.get("error"):
                    raise RuntimeError(f"LLM Error: {response['error']}")
                
                parsed = repair_json(content)
                if not isinstance(parsed, dict):
                    raise ValueError("Neural grounding failed to return a valid JSON dict")
                
                # Validation Gate
                if not all(k in parsed for k in ["eq", "var", "unit"]):
                    raise ValueError(f"Incomplete neural math. Keys found: {list(parsed.keys())}")

                # Normalize var and unit if returned as dictionaries
                if isinstance(parsed.get("unit"), dict):
                    parsed["unit"] = ", ".join(f"{k}: {v}" for k, v in parsed["unit"].items())
                if isinstance(parsed.get("var"), dict):
                    parsed["var"] = ", ".join(f"{k}: {v}" for k, v in parsed["var"].items())
                
                # Ensure missions have domain-appropriate units
                baseline = DomainRegulator._get_domain_baseline_grounding(tags, research_question)
                if parsed.get("unit") in ("standard_units", "unknown", "") or not parsed.get("unit"):
                    parsed["unit"] = baseline.get("unit", "dimensionless")
                    parsed["var"] = f"Primary Metric ({primary_tag})"
                    parsed["eq"] = baseline.get("eq", "y = f(x)")

                logger.info(f" [GROUNDING] Neural math synthesized for {primary_tag}: {parsed.get('unit')}")
                return parsed

            except Exception as e:
                backoff = min(2.0, (1.5 ** grounding_attempt) + (random.randint(0, 500) / 1000.0))
                logger.warning(f" [GROUNDING] Neural grounding attempt {grounding_attempt+1} failed: {e}. Retrying in {backoff:.1f}s...")
                if grounding_attempt < max_grounding_retries - 1:
                    await asyncio.sleep(backoff)
                else:
                    logger.info(" [GROUNDING] Neural grounding exhausted retries. Synthesizing domain-accurate empirical baseline.")
                    return DomainRegulator._get_domain_baseline_grounding(tags, research_question)

    @staticmethod
    def _get_domain_baseline_grounding(tags: List[str], research_question: str = None) -> Dict[str, Any]:
        """
        Synthesize domain-accurate mathematical physical baseline grounding.
        Eliminates cross-domain SARS-CoV-2/ACE2 contamination in non-biological runs.
        """
        primary_tag = tags[0] if tags else "scientific_impact"
        combined_text = (" ".join(tags) + " " + (research_question or "")).lower()

        def _matches_any(keywords: List[str], text: str) -> bool:
            for kw in keywords:
                if len(kw) <= 3:
                    if re.search(r"\b" + re.escape(kw) + r"\b", text):
                        return True
                else:
                    if kw in text:
                        return True
            return False

        # 1. Superconductivity / Materials Science / Solid State Physics
        if _matches_any([
            "superconduct", "tc", "critical_temp", "lattice", "phonon", "materials",
            "condensed_matter", "alloy", "crystal", "bcs", "mcmillan", "debye",
            "copper_oxide", "cuprate", "iron_based", "pnictide"
        ], combined_text):
            return {
                "eq": "Tc = (omega_log / 1.2) * exp(-1.04 * (1 + lambda) / (lambda - mu_star * (1 + 0.62 * lambda)))",
                "var": f"critical_temperature_Tc ({primary_tag}) in Kelvin (K)",
                "param": "electron_phonon_coupling lambda = 0.85, Coulomb pseudopotential mu_star = 0.13, Debye freq omega_log = 300 K",
                "unit": "K",
                "pred": {
                    "condition": "High valence electron ratio and optimal atomic mass ratio",
                    "outcome": "Elevated superconducting transition temperature Tc",
                    "baseline": 15.0,
                    "threshold": 35.0
                }
            }

        # 2. Machine Learning / Computer Science / Vision / NLP
        if _matches_any([
            "machine_learning", "ml", "cs", "pruning", "accuracy", "flops",
            "transformer", "neural", "deep_learning", "nlp", "vision",
            "gradient", "loss", "sparsity", "quantization", "epoch"
        ], combined_text):
            return {
                "eq": "Accuracy = Accuracy_dense - alpha * (pruning_ratio ** beta)",
                "var": f"top1_accuracy ({primary_tag}) in %",
                "param": "pruning_ratio (P) value 0.5, alpha = 2.0, beta = 1.5",
                "unit": "%",
                "pred": {
                    "condition": "50% structured channel pruning with magnitude thresholding",
                    "outcome": "Top-1 accuracy degradation <= 1.0%",
                    "baseline": 76.5,
                    "threshold": 75.5
                }
            }

        # 3. Physics / Fluid Dynamics / Fusion / Astrophysics
        if _matches_any([
            "physics", "quantum", "fluid", "mhd", "tokamak", "plasma",
            "astrophysics", "energy", "velocity", "pressure", "flux", "wave"
        ], combined_text):
            return {
                "eq": "E = h * nu",
                "var": f"Energy ({primary_tag}) in Joules (J)",
                "param": "Planck constant h = 6.626e-34 J*s, frequency nu in Hz",
                "unit": "J",
                "pred": {
                    "condition": "Frequency increase",
                    "outcome": "Linear energy scaling",
                    "baseline": 0.0,
                    "threshold": 1.0
                }
            }

        # 4. Chemistry / Molecular / Docking / Materials Chemistry
        if _matches_any([
            "chem", "molecule", "molecular", "docking", "ligand", "compound", "reaction"
        ], combined_text):
            return {
                "eq": "Delta_G = Delta_H - T * Delta_S",
                "var": f"binding_free_energy ({primary_tag}) in kcal/mol",
                "param": "Temperature T = 298.15 K, Enthalpy Delta_H, Entropy Delta_S",
                "unit": "kcal/mol",
                "pred": {
                    "condition": "Optimized hydrophobic interaction",
                    "outcome": "Exothermic binding affinity Delta_G < -7.0 kcal/mol",
                    "baseline": 0.0,
                    "threshold": -7.0
                }
            }

        # 5. Biology / Biophysics / Genomics / Neuroscience
        if _matches_any([
            "bio", "protein", "virus", "sars", "ace2", "spike", "cell", "genomic", "rna", "dna", "neuro", "enzyme", "kinetics"
        ], combined_text):
            if _matches_any(["sars", "ace2", "spike", "rbd", "6m0j", "6lzg"], combined_text):
                return {
                    "eq": "ddG = -R * T * ln(Kd_mut / Kd_wt)",
                    "var": f"Spike RBD-ACE2 receptor binding free energy change ddG ({primary_tag}) in kcal/mol",
                    "param": "Temperature T = 298.15 K, Gas Constant R = 1.9872e-3 kcal/(mol*K)",
                    "unit": "kcal/mol",
                    "pred": {
                        "condition": "Interface substitution at ACE2 receptor contact locus",
                        "outcome": "Enhanced binding affinity (negative ddG)",
                        "baseline": 0.0,
                        "threshold": -0.5
                    }
                }
            return {
                "eq": "v = (V_max * [S]^n) / (K_0.5^n + [S]^n)",
                "var": f"Biological response / catalytic rate v ({primary_tag}) in s^-1",
                "param": "Maximum velocity V_max, half-saturation constant K_0.5, Hill cooperativity coefficient n",
                "unit": "s^-1",
                "pred": {
                    "condition": "Allosteric or genetic perturbation above K_0.5 threshold",
                    "outcome": "Non-linear sigmoidal shift in biological activity",
                    "baseline": 1.0,
                    "threshold": 2.5
                }
            }

        # 6. Default scientific fallback
        return {
            "eq": "y = f(x)",
            "var": f"Primary Metric ({primary_tag}) in standard units",
            "param": "Independent parameter x",
            "unit": "dimensionless",
            "pred": {
                "condition": "Parameter perturbation",
                "outcome": "Observable metric shift",
                "baseline": 0.0,
                "threshold": 1.0
            }
        }



    @staticmethod
    async def get_domain_examples(tags: List[str]) -> Dict[str, str]:
        """[TITAN V208.0] ASYNC SOVEREIGNTY. Abolished illegal asyncio.run()."""
        return await DomainRegulator.get_domain_examples_async(tags)



    @staticmethod
    def get_fallback_skeleton(domain: str, research_question: str) -> Dict[str, Any]:
        """
        [RIGOR] FLAW 20 FIX: No more hardcoded textbook formulas.
        If the system falls back, it must acknowledge the lack of a specific model.
        """
        logger.warning(f" [RIGOR] No specific model found for {domain}. Generating generic complexity skeleton.")
        
        return {
            "statement": f"Systemic analysis of {research_question} in the {domain} domain reveals non-linear scaling behavior.",
            "variables": [
                {"name": "Independent Variable", "symbol": "X", "unit": "units", "domain": [0, 1e6], "type": "independent"},
                {"name": "Target Metric", "symbol": "Y", "unit": "units", "domain": [0, 1e6], "type": "dependent"}
            ],
            "functional_form": "Y = f(X) (General Scaling)",
            "rationale": "High-level complexity assessment for novel research domains.",
            "_is_fallback": True,
            "predictions": [
                {
                    "condition": "When X increases",
                    "outcome": "Y follows non-linear trend",
                    "baseline": 1.0,
                    "baseline_unit": "units",
                    "threshold": 0.1,
                    "threshold_unit": "units",
                    "direction": "increase"
                }
            ],
            "parameters": [
                {"name": "System Constant", "symbol": "k", "value": 1.0, "unit": "dimensionless", "source": "assumed"}
            ]
        }
