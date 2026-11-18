from typing import Dict, Any, List, Optional
import asyncio
import logging
import json
from backend.llm_manager import run_llm, HYPOTHESIS_VALIDATION_MODEL
try:
    from backend.core.skill_injector import get_expert_system
except ImportError:
    get_expert_system = None

logger = logging.getLogger("avon.red_team")

def extract_json_balanced(text: str) -> str:
    """
    Finds the first complete JSON object in the text by counting opening and closing braces.
    """
    start_idx = text.find('{')
    if start_idx == -1:
        return ""
    
    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        
        if escape:
            escape = False
            continue
        
        if char == '\\':
            escape = True
            continue
        
        if char == '"':
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx:i+1]
                    
    return ""

class RedTeamAgent:
    """
    Project Godzilla: Phase 2 - Adversarial Intelligence ("Reviewer #2")
    
    CRITICAL MANDATE:
    1. Do NOT look for "logical fallacies".
    2. HUNT for ESCAPE ROUTES.
    3. Downgrade "DEAD" to "CONDITIONALLY DEAD" if any ambiguity exists.
    """
    
    def __init__(self):
        # Assuming run_llm is available globally or passed in. 
        # Using the import for now.
        pass

    async def review_verdict(self, verdict: str, claims: List[str], evidence: str) -> Dict[str, Any]:
        """
        Adversarially review a proposed "Killer Verdict".
        
        Args:
            verdict: The proposed verdict (e.g., "DEAD", "FAILURE").
            claims: A list of specific claims made by the finding.
            evidence: The text content/summary supporting the claim.
            
        Returns:
            Dict containing:
            - status: "APPROVED", "DOWNGRADE", "INVALID", "ESCAPED"
            - reason: Explanation of the escape route or failure.
            - severity_score: 0-100 impact score.
            - downgraded_verdict: Only if status != APPROVED.
        """
        
        #  BRUTAL UPGRADE: SUCCESS SCRUTINY
        # We now scrutinize BOTH Kill claims AND Success claims.
        is_kill = any(x in verdict.lower() for x in ["dead", "fail", "kill"])
        is_success = any(x in verdict.lower() for x in ["success", "confirm", "discovered", "verified"])

        if not is_kill and not is_success:
            return {"status": "SKIPPED", "reason": "Verdict is neither a Kill Claim nor a Success Claim"}
        
        mode = "KILL_CHALLENGE" if is_kill else "SUCCESS_CHALLENGE"
        logger.info(f" Red Team: Entering {mode} mode for verdict '{verdict}'")

        # GODZILLA INJECTION: MIND/BODY LOCK
        meta_prompt = ""
        if get_expert_system:
            try:
                expert = get_expert_system()
                # Use PUBLIC API: inject_meta_skills
                # This handles both Keyword Overrides and Semantic Discovery
                meta_block = await expert.inject_meta_skills("", query="adversarial", max_skills=2)
                if meta_block:
                    meta_prompt = "\n#  [COGNITIVE_OS] - ADVERSARIAL PROTOCOLS\n" + meta_block
            except Exception as e:
                logger.warning(f"Failed to inject Red Team skills: {e}")

        prompt = f"""
        ACT AS "REVIEWER #2" (BRUTAL SCIENTIFIC SKEPTIC).
        PHD MODE: ON.
        YOUR ONLY GOAL IS TO BLOCK THIS VERDICT. BE AN ULTRA SKEPTIC.
        
        {meta_prompt}
        
        Proposed Verdict: {verdict}
        
        Claims Made:
        {json.dumps(claims, indent=2)}
        
        Evidence Provided:
        {evidence[:15000]}
        
        ---
        YOUR MANDATE : ASK THESE 5 QUESTIONS EXACTLY.
        
        1. NECESSITY CHECK:
           "Is this assumption logically required, or historically convenient?"
           
        2. PARAMETER SMUGGLING CHECK:
           "Which variable was fixed without justification?" (e.g., "assuming 25C")
           
        3. CONSTRAINT TIER CHECK:
           "Is the DEAD verdict relying on Tier 3 (Economic) constraints?" (If yes -> DOWNGRADE)
           
        4. SYMBOLIC VIOLATION CHECK:
           "Do the constraints contradict symbolically (form), or only numerically?"
           
        5. ESCAPE ENUMERATION CHECK:
           "Does ANY material / geometry / regime / control strategy escape this failure?"

        6. PHYSICS CHECK (CRITICAL: ):
           "Does this violate 2nd Law of Thermodynamics, Conservation of Energy, or imply FTL information?"
           "Are constants (c, h, k, G) respected or implicitly modified?"
        
        ---
        VERDICT LOGIC (YOU HAVE VETO POWER):
        
        - If Necessity Check fails -> Status: ESCAPED
        - If Tier 3 constraint used -> Status: INVALID_CLAIM (or DOWNGRADE)
        - If >0 Escape Routes found -> Status: DOWNGRADE (to CONDITIONALLY DEAD)
        - If Symbolic Check fails (numeric only) -> Status: DOWNGRADE
        
        If NONE of the above apply, and the result is CLEAN/INEVITABLE -> Status: APPROVED
        
        CRITICAL: IF PHYSICS CHECK FAILS -> Status: INVALID_CLAIM (Reason: Physical Law Violation)
        
        SPECIAL INSTRUCTION FOR SUCCESS CHALLENGE:
        If you are in SUCCESS_CHALLENGE mode, be EVEN MORE BRUTAL. 
        "If it sounds too good to be true, it is."
        Look for "Instrumental Convergence", "Proxy Gaming", and "Selection Bias".
        
        ---
        OUTPUT JSON ONLY:
        {{
            "status": "APPROVED" | "REJECTED" | "DOWNGRADE" | "ESCAPED" | "INVALID_CLAIM",
            "reason": "Exact flaw or escape route found",
            "downgraded_verdict": "CONDITIONALLY_...",
            "severity_score": 90, 
            "red_team_log": "Results of checks..."
        }}
        """
        
        try:
            # Use HYPOTHESIS_VALIDATION_MODEL for adversarial review (non-blocking)
            response = await asyncio.to_thread(run_llm, prompt, model=HYPOTHESIS_VALIDATION_MODEL, timeout=90, temperature=0.1)
            
            # Parse JSON if response comes back as string (common with generic run_llm)
            if isinstance(response, str):
                # Try to extract JSON
                json_str = extract_json_balanced(response)
                if json_str:
                    response = json.loads(json_str)
                else:
                    return {"status": "ERROR", "reason": "Red Team output parse failed", "raw": response}
            
            # Normalize
            if isinstance(response, dict) and "status" in response:
                return response
            
            return {"status": "ERROR", "reason": "Invalid Red Team JSON structure", "raw": response}

        except Exception as e:
            logger.error(f" RED TEAM CRITICAL FAILURE: {e}")
            # FAIL SECURE: On internal error, we REJECT the claim/verdict.
            # We do NOT allow research to move forward on a broken audit.
            return {"status": "REJECTED", "reason": f"Red Team Audit Internal Error: {e}", "fatal": True}

    async def critique_plan(self, plan: dict, research_question: str) -> Dict[str, Any]:
        """
        Adversarially review a proposed Research Plan.
        
        Args:
            plan: The proposed research plan (dict).
            research_question: The main objective.
            
        Returns:
            Dict containing:
            - status: "APPROVED" | "REJECTED" | "MODIFIED"
            - critique: 'Reviewer #2' style feedback.
            - suggestions: Specific changes required.
        """
        prompt = f"""
        ACT AS "PEER REVIEWEr" (BRUTAL SCIENTIFIC SKEPTIC).
        GODZILLA MODE: ON.
        YOUR GOAL IS TO FIND FLAWS IN THIS EXPERIMENTAL PLAN. DESTROY WEAKNESSES.
        
        Research Question: <question>{research_question}</question>
        
        Proposed Plan:
        <plan>
        {json.dumps(plan, indent=2)}
        </plan>
        
        ---
        CRITIQUE GUIDELINES:
        1. Control Variables: Are they creating a fair test?
        2. Statistical Power: Is the sample size/scope laughable?
        3. Measurement Proxy: Are they measuring X but claiming Y?
        4. Circular Logic: Does the plan assume the conclusion?
        5. PHYSICAL LIMITS: Does it require temperatures, pressures, or energies that are physically impossible (e.g., 0K, >c)?
        
        Verdict Options:
        - APPROVED: Solid plan.
        - REJECTED: Fatal flaw (e.g., circular logic, no controls).
        
        OUTPUT JSON ONLY:
        {{
            "status": "APPROVED" | "REJECTED",
            "critique": "Your brutal feedback here...",
            "fatal_flaw": "None" or "Description of fatal flaw"
        }}
        """
        try:
            response = await asyncio.to_thread(run_llm, prompt, model=HYPOTHESIS_VALIDATION_MODEL, timeout=60, temperature=0.1)
            
            # Robust JSON extraction
            if isinstance(response, str):
                json_str = extract_json_balanced(response)
                if json_str:
                    response = json.loads(json_str)
                else:
                    # FIX: Use more robust repair if regex fails
                    try:
                        import json_repair
                        response = json_repair.repair_json(response, return_objects=True)
                    except ImportError:
                        return {"status": "REJECTED", "critique": "Failed audit: unparseable output format (fail-secure)", "fatal_flaw": "Response failed structural parse."}
            
            return response
            
        except Exception as e:
            logger.error(f" RED TEAM PLAN CRITIQUE FAILED: {e}")
            # FAIL SECURE: If code can't be audited, it doesn't run.
            return {"status": "REJECTED", "critique": f"Fatal audit error: {e}", "fatal_flaw": "Internal System Error during sanity check."}

    # =========================================================================
    # HELL-TIER UPGRADE #1: DEVIL'S ADVOCATE (Forced Contrarian)
    # =========================================================================
    async def generate_counterfactual(self, claim: str) -> Dict[str, Any]:
        """
        Generate a plausible alternative explanation for a given claim.
        Forces the system to prove it found THE answer, not just AN answer.
        """
        prompt = f"""
        ACT AS A "DEVIL'S ADVOCATE" phd grade   SCIENTIST.
        
        CLAIM: {claim}
        
        YOUR TASK:
        Generate a PLAUSIBLE ALTERNATIVE explanation that could be equally true.
        This is not about being a skeptic - it's about finding OTHER valid interpretations.
        
        RULES:
        1. The counter-explanation must be SCIENTIFICALLY PLAUSIBLE (no magic).
        2. It must explain the SAME observations that led to the original claim.
        3. It should be from a DIFFERENT mechanism or framework.
        
        OUTPUT JSON:
        {{
            "counter_claim": "Alternative explanation...",
            "mechanism": "How this alternative would work...",
            "distinguishing_test": "An experiment that could differentiate between the original and this alternative.",
            "plausibility_score": 0.0-1.0  // How likely is this alternative?
        }}
        """
        try:
            response = await asyncio.to_thread(run_llm, prompt, model=HYPOTHESIS_VALIDATION_MODEL, timeout=60, temperature=0.15)
            if isinstance(response, str):
                json_str = extract_json_balanced(response)
                if json_str:
                    return json.loads(json_str)
            return response if isinstance(response, dict) else {"error": "Parse failed", "raw": str(response)[:500]}
        except Exception as e:
            logger.error(f"Devil's Advocate failed: {e}")
            return {"error": str(e)}

    # =========================================================================
    # HELL-TIER UPGRADE #3: PAPER AUDIT (Citation Verification)
    # =========================================================================
    async def verify_citation(self, claim: str, cited_paper_title: str, cited_abstract: str = None) -> Dict[str, Any]:
        """
        Verify if a claim is a FAITHFUL representation of a cited paper.
        Catches hallucinated citations and misinterpretations.
        
        Args:
            claim: The claim made by the system.
            cited_paper_title: Title of the paper supposedly supporting the claim.
            cited_abstract: Abstract of the paper (if available).
        """
        if not cited_abstract:
            # HELL-TIER UPGRADE: Dual-Source Verification (Semantic Scholar + ArXiv)
            from difflib import SequenceMatcher
            # 1. Try Semantic Scholar (isolated try/except so S2 failure never blocks ArXiv fallback)
            try:
                from backend.tools.semantic_scholar_tool import semantic_scholar_tool
                papers = semantic_scholar_tool.search_papers(cited_paper_title, limit=1)
                if papers:
                    paper = papers[0]
                    similarity = SequenceMatcher(None, str(paper.get('title', '')).lower(), cited_paper_title.lower()).ratio()
                    if similarity > 0.8:
                        cited_abstract = paper.get('abstract') or "ABSTRACT NOT FOUND IN DATABASE"
                        logger.info(f" SemanticScholar verified: '{cited_paper_title}' (Sim: {similarity:.2f})")
                    else:
                        logger.warning(f" SemanticScholar title mismatch: Got '{paper.get('title')}', expected '{cited_paper_title}'")
            except Exception as s2_err:
                logger.warning(f"Semantic Scholar verification lookup failed: {s2_err}")

            # 2. Fallback to ArXiv if Semantic Scholar failed or had no abstract
            if not cited_abstract or cited_abstract == "ABSTRACT NOT FOUND IN DATABASE":
                try:
                    from backend.tools.arxiv_tool import search_arxiv
                    results = search_arxiv(cited_paper_title, max_results=1)
                    if results:
                        arxiv_paper = results[0]
                        similarity = SequenceMatcher(None, str(arxiv_paper.get('title', '')).lower(), cited_paper_title.lower()).ratio()
                        if similarity > 0.8:
                            cited_abstract = arxiv_paper.get('abstract', "ABSTRACT NOT FOUND")
                            logger.info(f" ArXiv verified: '{cited_paper_title}'")
                except Exception as ax_err:
                    logger.warning(f"ArXiv verification lookup failed: {ax_err}")

            if not cited_abstract or cited_abstract in ("ABSTRACT NOT FOUND IN DATABASE", "ABSTRACT NOT FOUND", "ABSTRACT UNAVAILABLE - VERIFICATION FAILED"):
                return {
                    "verdict": "UNVERIFIABLE",
                    "reason": f"Cited paper '{cited_paper_title}' could not be verified in Semantic Scholar or ArXiv.",
                    "faithful_summary": ""
                }
        
        prompt = f"""
        ACT AS A CITATION AUDITOR.
        
        CLAIM MADE BY SYSTEM:
        "{claim}"
        
        CITED PAPER TITLE:
        "{cited_paper_title}"
        
        PAPER ABSTRACT:
        {cited_abstract[:3000]}
        
        YOUR TASK:
        Verify if the CLAIM is a faithful representation of the PAPER.
        
        VERDICT OPTIONS:
        - VALID: The claim accurately reflects the paper's findings.
        - MISREPRESENTED: The claim exaggerates, inverts, or misinterprets the paper.
        - HALLUCINATED: The paper does not support this claim at all.
        - UNVERIFIABLE: Cannot determine from abstract alone.
        
        OUTPUT JSON:
        {{
            "verdict": "VALID" | "MISREPRESENTED" | "HALLUCINATED" | "UNVERIFIABLE",
            "reason": "Explanation...",
            "faithful_summary": "What the paper actually says..."
        }}
        """
        try:
            response = await asyncio.to_thread(run_llm, prompt, model=HYPOTHESIS_VALIDATION_MODEL, timeout=60, temperature=0.1)
            if isinstance(response, str):
                json_str = extract_json_balanced(response)
                if json_str:
                    return json.loads(json_str)
            return response if isinstance(response, dict) else {"verdict": "UNVERIFIABLE", "reason": "Parse failed"}
        except Exception as e:
            logger.error(f"Citation verification failed: {e}")
            return {"verdict": "UNVERIFIABLE", "reason": str(e)}

    # =========================================================================
    # HELL-TIER UPGRADE #4: TIME-DECAY SKEPTICISM
    # =========================================================================
    def check_time_decay(self, hypothesis_id: str, last_verified_cycle: int, current_cycle: int, decay_threshold: int = 10) -> Dict[str, Any]:
        """
        Check if a hypothesis needs re-verification due to age.
        Old findings should be trusted less.
        
        Args:
            hypothesis_id: Unique ID of the hypothesis.
            last_verified_cycle: Cycle number when it was last verified.
            current_cycle: Current cycle number.
            decay_threshold: Number of cycles before triggering re-verification.
            
        Returns:
            Dict with challenge_required flag and reason.
        """
        cycles_since_verification = current_cycle - last_verified_cycle
        
        if cycles_since_verification >= decay_threshold:
            return {
                "challenge_required": True,
                "reason": f"Hypothesis {hypothesis_id} has not been re-verified in {cycles_since_verification} cycles (threshold: {decay_threshold}). Requires re-evaluation.",
                "cycles_stale": cycles_since_verification
            }
        else:
            return {
                "challenge_required": False,
                "reason": f"Hypothesis is fresh ({cycles_since_verification} cycles old, threshold: {decay_threshold}).",
                "cycles_stale": cycles_since_verification
            }

    # =========================================================================
    # HELL-TIER UPGRADE #6: KILL CHAIN LOGGING ("THE MORGUE")
    # =========================================================================
    def log_to_morgue(self, hypothesis_statement: str, kill_reason: str, session_id: str = None) -> bool:
        """
        Log a killed hypothesis to the "Morgue" (Neo4j Knowledge Graph).
        Before generating new hypotheses, query the Morgue to avoid re-proposing dead ideas.
        
        Args:
            hypothesis_statement: The hypothesis that was killed.
            kill_reason: Why it was killed (the death certificate).
            session_id: Optional session ID for grouping.
            
        Returns:
            True if logged successfully, False otherwise.
        """
        # Always persist to Semantic Morgue (VectorStore) so local SQLite/VectorStore mode retains dead hypotheses
        semantic_ok = False
        try:
            semantic_ok = self.log_to_morgue_semantic(hypothesis_statement, kill_reason, session_id=session_id)
        except Exception:
            pass

        try:
            from backend.memory.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            
            if not kg.is_available:
                return semantic_ok
            
            # Create a "DeadHypothesis" node
            query = """
            MERGE (h:DeadHypothesis {statement_hash: $hash})
            ON CREATE SET 
                h.statement = $statement,
                h.kill_reason = $reason,
                h.killed_at = datetime(),
                h.session_id = $session_id
            ON MATCH SET
                h.kill_count = COALESCE(h.kill_count, 0) + 1,
                h.last_killed_at = datetime()
            RETURN h.statement_hash as id
            """
            import hashlib
            statement_hash = hashlib.sha256(hypothesis_statement.lower().encode()).hexdigest()[:16]
            
            kg._run_query(query, {
                "hash": statement_hash,
                "statement": hypothesis_statement,
                "reason": kill_reason,
                "session_id": session_id or "default"
            })
            
            logger.info(f" Logged to Morgue: {hypothesis_statement[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log to Morgue: {e}")
            return False

    def query_morgue(self, new_hypothesis: str, similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Check if a new hypothesis is similar to any previously killed ones.
        Uses SEMANTIC embeddings via ChromaDB/FAISS for accurate matching.
        
        Args:
            new_hypothesis: The hypothesis being proposed.
            similarity_threshold: Minimum similarity to consider a match (0.0-1.0).
            
        Returns:
            List of similar dead hypotheses from the Morgue.
        """
        try:
            # UPGRADE: Use Semantic Morgue with embeddings
            from backend.memory.vectorstore import get_vectorstore
            vs = get_vectorstore()
            
            # Query vector store for similar dead hypotheses
            results = vs.query(f"DEAD_HYPOTHESIS: {new_hypothesis}", top_k=10)
            
            similar = []
            for result in results:
                # VectorStore.query() returns flat dicts {id, content, metadata, score};
                # support both flat dicts and legacy {doc: {...}, score: float}
                doc = result.get("doc") if isinstance(result.get("doc"), dict) and result.get("doc") else result
                score = float(result.get("score", 999.0))
                
                # For unit-normalized vectors, squared L2 distance d^2 = 2 * (1 - cos_sim)
                if score <= 4.0:
                    similarity = max(0.0, 1.0 - (score / 2.0))
                else:
                    similarity = max(0.0, 1.0 / (1.0 + score))
                
                doc_id = str(doc.get("id", ""))
                content = str(doc.get("content", ""))
                meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
                if similarity >= similarity_threshold and ("DEAD_HYPOTHESIS" in doc_id or "DEAD_HYPOTHESIS:" in content):
                    clean_stmt = meta.get("statement") or content
                    kill_reason = meta.get("kill_reason", "Unknown")
                    if "DEAD_HYPOTHESIS:" in clean_stmt:
                        clean_stmt = clean_stmt.split("DEAD_HYPOTHESIS:", 1)[1].strip()
                    if " | REASON:" in clean_stmt:
                        parts = clean_stmt.split(" | REASON:", 1)
                        clean_stmt = parts[0].strip()
                        if kill_reason == "Unknown":
                            kill_reason = parts[1].strip()
                    similar.append({
                        "statement": clean_stmt,
                        "kill_reason": kill_reason,
                        "similarity": round(similarity, 2)
                    })
            
            if similar:
                logger.warning(f" Found {len(similar)} semantically similar hypotheses in Morgue!")
            
            return similar
            
        except Exception as e:
            logger.debug(f"Semantic Morgue unavailable, falling back to Neo4j: {e}")
            # Fallback to Neo4j keyword matching
            return self._query_morgue_neo4j(new_hypothesis, similarity_threshold)
    
    def _query_morgue_neo4j(self, new_hypothesis: str, similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Fallback Neo4j keyword-based morgue query."""
        try:
            from backend.memory.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            
            if not kg.is_available:
                return []
            
            keywords = set(new_hypothesis.lower().split())
            
            query = """
            MATCH (h:DeadHypothesis)
            RETURN h.statement as statement, h.kill_reason as reason, h.killed_at as killed_at
            ORDER BY h.killed_at DESC
            LIMIT 100
            """
            results = kg._run_query(query, {})
            
            similar = []
            for record in results:
                dead_keywords = set(record["statement"].lower().split())
                overlap = len(keywords & dead_keywords) / max(len(keywords | dead_keywords), 1)
                if overlap >= similarity_threshold:
                    similar.append({
                        "statement": record["statement"],
                        "kill_reason": record["reason"],
                        "similarity": overlap
                    })
            
            return similar
            
        except Exception as e:
            logger.error(f"Neo4j Morgue query failed: {e}")
            return []

    # =========================================================================
    # ADVANCED UPGRADE #2: ADVERSARIAL FUZZING (Edge Case Generator)
    # =========================================================================
    def generate_edge_cases(self, claim: str, num_cases: int = 5) -> Dict[str, Any]:
        """
        Generate adversarial edge-case scenarios that could break a claim.
        Forces ULTRON to specify the BOUNDARIES of truth.
        
        Args:
            claim: The claim to stress-test.
            num_cases: Number of edge cases to generate.
            
        Returns:
            Dict with edge_cases list and overall assessment.
        """
        prompt = f"""
        ACT AS AN ADVERSARIAL FUZZER for scientific claims.
        
        CLAIM: "{claim}"
        
        YOUR TASK:
        Generate {num_cases} edge-case scenarios that could BREAK this claim.
        Think about:
        - Edge conditions (extreme temperatures, doses, ages, etc.)
        - Co-morbidities or confounding factors
        - Interactions with other variables
        - Scale effects (does it work at 10x or 0.1x scale?)
        - Time effects (does it hold after 10 years?)
        
        OUTPUT JSON:
        {{
            "original_claim": "{claim}",
            "edge_cases": [
                {{
                    "scenario": "What if...",
                    "breaks_claim": true/false,
                    "severity": "CRITICAL" | "MAJOR" | "MINOR",
                    "modified_claim": "If X then Y, EXCEPT when Z"
                }}
            ],
            "overall_robustness": 0.0-1.0,
            "recommended_caveats": ["List of conditions to add to claim"]
        }}
        """
        try:
            response = run_llm(prompt, model=HYPOTHESIS_VALIDATION_MODEL, timeout=90, temperature=0.15)
            if isinstance(response, str):
                json_str = extract_json_balanced(response)
                if json_str:
                    return json.loads(json_str)
            return response if isinstance(response, dict) else {"error": "Parse failed", "raw": str(response)[:500]}
        except Exception as e:
            logger.error(f"Adversarial Fuzzing failed: {e}")
            return {"error": str(e), "edge_cases": []}

    # =========================================================================
    # ADVANCED UPGRADE #1: MULTI-AGENT TRIBUNAL (Council of Skeptics)
    # FOR FINAL REPORTS ONLY - High token cost!
    # =========================================================================
    async def run_tribunal(self, claim: str, evidence: str = "") -> Dict[str, Any]:
        """
        Run a full Multi-Agent Tribunal on a claim.
         WARNING: This spawns 5 LLM calls! Use ONLY for final report validation.
        
        Args:
            claim: The claim to validate.
            evidence: Supporting evidence text.
            
        Returns:
            Dict with individual verdicts and consensus result.
        """
        import os
        import re
        session_id = os.environ.get("ULTRON_SESSION_ID", "").lower()
        domain = os.environ.get("ULTRON_DOMAIN", "").lower()
        c_low = claim.lower()
        
        # Explicitly protect natural sciences from being flagged as ML
        is_natural_science = any(d in domain or d in c_low for d in ["biology", "biomedical", "biophysics", "chemistry", "physics", "medicine", "protein", "sars", "spike", "rbd", "ace2"])
        
        ml_pattern = r'\b(neural network|deep learning|transformer architecture|vision transformer|cifar|imagenet|pruning|flops|backprop|autoencoder)\b'
        is_ml = not is_natural_science and (
            domain in ["cs", "ml", "machine_learning", "deep_learning"] or
            bool(re.search(ml_pattern, c_low)) or
            bool(re.search(ml_pattern, session_id))
        )
        
        domain_skeptic = {
            "name": "The ML Scientist",
            "focus": "Machine Learning & Models",
            "question": "Are the generalization bounds respected? Is there representational collapse, dataset leakage, or proxy gaming in the GNN or model training?"
        } if is_ml else {
            # Domain-agnostic skeptic: derives focus from session context
            # so the red-team works correctly for physics, chemistry, biology, social science, etc.
            "name": "The Domain Scientist",
            "focus": os.environ.get("ULTRON_DOMAIN", "General Science"),
            "question": "Are the domain-specific assumptions justified? Are there hidden confounders, violated physical laws, or overlooked baseline comparisons specific to this field?"
        }
        
        skeptics = [
            {
                "name": "The Statistician",
                "focus": "Numbers & Data",
                "question": "Is the sample size sufficient? Are the error bars correct? Is there p-hacking?"
            },
            {
                "name": "The Historian", 
                "focus": "Prior Work",
                "question": "Has this been tried before? Is there prior art? Was it disproven in past literature?"
            },
            {
                "name": "The Physicist",
                "focus": "Fundamental Laws",
                "question": "Does this violate thermodynamics, conservation laws, or speed of light?"
            },
            domain_skeptic,
            {
                "name": "The Economist",
                "focus": "Feasibility",
                "question": "Is this economically viable at scale? What are the cost barriers?"
            }
        ]
        
        async def _eval_skeptic(skeptic: Dict[str, str]) -> Dict[str, Any]:
            prompt = f"""
            ACT AS "{skeptic['name']}" - A specialist in {skeptic['focus']}.
            
            CLAIM: "{claim}"
            
            EVIDENCE: {evidence[:5000] if evidence else "No evidence provided"}
            
            YOUR SPECIFIC QUESTION: {skeptic['question']}
            
            VERDICT OPTIONS:
            - APPROVE: This claim passes your specialist check.
            - REJECT: This claim fails your specialist check.
            - ABSTAIN: Cannot evaluate from your domain expertise.
            
            OUTPUT JSON:
            {{
                "skeptic": "{skeptic['name']}",
                "verdict": "APPROVE" | "REJECT" | "ABSTAIN",
                "reason": "Brief explanation from your specialist perspective",
                "confidence": 0.0-1.0
            }}
            """
            try:
                response = await asyncio.to_thread(run_llm, prompt, model=HYPOTHESIS_VALIDATION_MODEL, timeout=60, temperature=0.1)
                if isinstance(response, dict) and "text" in response and "verdict" not in response:
                    response = response.get("text", "")
                if isinstance(response, str):
                    json_str = extract_json_balanced(response)
                    if json_str:
                        return json.loads(json_str)
                    return {"skeptic": skeptic["name"], "verdict": "ABSTAIN", "reason": "Parse error"}
                elif isinstance(response, dict):
                    return response
                return {"skeptic": skeptic["name"], "verdict": "ABSTAIN", "reason": "Unexpected response"}
            except Exception as e:
                logger.error(f" Tribunal skeptic {skeptic['name']} failed: {e}")
                return {"skeptic": skeptic["name"], "verdict": "REJECT", "reason": f"Skeptic Internal Error: {e}"}

        verdicts = list(await asyncio.gather(*[_eval_skeptic(s) for s in skeptics]))
        
        # Calculate consensus
        approvals = sum(1 for v in verdicts if v.get("verdict") == "APPROVE")
        rejections = sum(1 for v in verdicts if v.get("verdict") == "REJECT")
        abstentions = sum(1 for v in verdicts if v.get("verdict") == "ABSTAIN")
        
        # Consensus: 4/5 approvals OR unanimous with quorum (at least 3 non-abstaining and 0 rejections)
        non_abstaining = approvals + rejections
        consensus = "APPROVED" if (approvals >= 4 or (non_abstaining >= 3 and rejections == 0)) else "REJECTED"
        
        logger.info(f" TRIBUNAL VERDICT: {consensus} ({approvals} approve, {rejections} reject, {abstentions} abstain)")
        
        return {
            "claim": claim,
            "verdicts": verdicts,
            "approvals": approvals,
            "rejections": rejections,
            "abstentions": abstentions,
            "consensus": consensus,
            "passed": consensus == "APPROVED"
        }

    def log_to_morgue_semantic(self, hypothesis_statement: str, kill_reason: str, session_id: str = None) -> bool:
        """
        Log a killed hypothesis to the Semantic Morgue (VectorStore).
        Uses embeddings for later semantic similarity search.
        """
        try:
            from backend.memory.vectorstore import get_vectorstore
            vs = get_vectorstore()
            
            import hashlib
            doc_id = f"DEAD_HYPOTHESIS_{hashlib.sha256(hypothesis_statement.lower().encode()).hexdigest()[:16]}"
            
            # Store with structured metadata and flush immediately
            vs.add_document(
                doc_id,
                f"DEAD_HYPOTHESIS: {hypothesis_statement} | REASON: {kill_reason}",
                metadata={
                    "kill_reason": kill_reason,
                    "statement": hypothesis_statement,
                    "session_id": session_id or "default",
                },
            )
            vs.flush()
            
            logger.info(f" Logged to Semantic Morgue: {hypothesis_statement[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log to Semantic Morgue: {e}")
            return False

    async def run(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sovereign router entrypoint for RedTeamAgent (handles adversarial review, citation verification,
        and legacy fact_checker_agent dispatches natively).
        """
        context = context or {}
        payload = task.get("payload") if isinstance(task, dict) else {}
        if not isinstance(payload, dict):
            payload = {}

        claim = (
            payload.get("claim")
            or payload.get("query")
            or (task.get("query") if isinstance(task, dict) else "")
            or (task.get("description") if isinstance(task, dict) else "")
            or ""
        )
        if not claim:
            return {"status": "failed", "error": "No claim provided"}

        cited_title = payload.get("cited_paper_title") or payload.get("paper_title")
        if cited_title:
            ver = await self.verify_citation(
                claim=claim,
                cited_paper_title=str(cited_title),
                cited_abstract=payload.get("cited_abstract"),
                doi=payload.get("doi"),
                url=payload.get("url")
            )
            return {"status": "success", "verdict": ver.get("verdict", "UNVERIFIABLE"), "details": ver}

        review = await self.review_verdict(
            hypothesis={"id": payload.get("hypothesis_id", "claim_audit"), "statement": claim},
            current_verdict=payload.get("verdict", "VERIFIED"),
            evidence_log=payload.get("evidence_log") or ([payload["context"]] if payload.get("context") else []),
            attack_history=payload.get("attack_history") or []
        )
        return {
            "status": "success",
            "verdict": review.get("status", "APPROVED"),
            "reason": review.get("reason", ""),
            "details": review
        }
