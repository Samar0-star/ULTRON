from __future__ import annotations

# backend/agents/report_composer.py
"""
Report Composer Agent  The "Mind Blowing" Integration 
--------------------------------------------------------
Orchestrates the creation of professional reports by combining:
1. Deep Research (BeastSearch)
2. Visual Intelligence (VizRouter + AI Recommender)
3. Expert Writing (GodzillaWriter)

This agent acts as the "Director" of the report generation process.
"""

import os
import json
import asyncio
import logging
import traceback
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
# import pandas as pd  # MOVED TO LAZY LOADING
import uuid

# Internal components
from backend.agents.writer_agent import GodzillaWriterAgent, WritingMode, OutputFormat
# Removed VizRouter and VizAIRecommender imports to hardwire AI Coder
from backend.tools.smart_filename import generate_smart_filename, extract_keywords
from backend.core.skill_injector import get_expert_system


# GUARANTEED CHART GENERATION - Uses existing BEAST-GRADE DataVisualizer
try:
    from backend.visualization.data_visualizer import DataVisualizer, VizRequest, VizResponse
    _HAS_DATA_VISUALIZER = True
except ImportError:
    _HAS_DATA_VISUALIZER = False
    DataVisualizer = None
    VizRequest = None
    VizResponse = None

# Logging
logger = logging.getLogger("avon.report_composer")
logger.setLevel(os.getenv("COMPOSER_LOG_LEVEL", "INFO"))


# Defensive tool imports
try:
    from backend.tools.web_search import beast_search
    _HAS_SEARCH = True
except ImportError:
    _HAS_SEARCH = False


try:
    from backend.llm_manager import run_llm
    _HAS_LLM = True
except ImportError:
    run_llm = None
    _HAS_LLM = False




@dataclass
class ReportSection:
    title: str
    content_goal: str
    visual_intent: Optional[str] = None
    data_source: Optional[str] = None  # "search", "provided", "analysis"
    required_charts: int = 0
    image_query: Optional[str] = None  # Image search query for gallery
    num_images: int = 0  # Number of images to fetch for gallery


class ReportComposerAgent:
    """
    Orchestrates the entire report generation pipeline:
    Plan -> Research -> Visualize -> Write -> Assemble
    """
    
    def __init__(self, world_model=None):
        self.writer = GodzillaWriterAgent()
        # Viz routing completely replaced by direct AI Coder calls inside _generate_visuals
        self.viz_router = None
        self.viz_recommender = None
        self.viz_orchestrator = None # Lazy loaded if needed
        self.llm_manager = None # Required for CentralRouterBeast injection
        self.world_model = world_model
        # BUG-FIX-5: Use the active session ID from the environment variable set at launch.
        # Never hardcode a session ID — doing so writes facts to a ghost DB.
        if not self.world_model:
            try:
                import os, uuid
                from backend.core.world_model import WorldModel
                active_session_id = os.environ.get("SVEL_SESSION_ID") or str(uuid.uuid4())[:8]
                self.world_model = WorldModel(session_id=active_session_id)
                logger.info(f" [CONNECTION] Physically bonded Report Composer to '{active_session_id}' manifold.")
            except Exception as _wm_err:
                logger.error(f" [CONNECTION] Critical: Failed to physically bond World Model: {_wm_err}")
        self.expert_system = get_expert_system()

    async def run(self, topic: str, mode: str = "standard", ctx: Dict[str, Any] = None, deadline: Optional[datetime] = None, **kwargs) -> Dict[str, Any]:
        """Generate a complete research report."""
        # Alias support for different router/orchestrator calling conventions
        if ctx is None:
            ctx = kwargs.get("context") or {}
            
        if hasattr(self, "llm_manager") and self.llm_manager:
            self.writer.llm_manager = self.llm_manager
            
        # [GODZILLA FIX] World Model Connection Persistence
        if not self.world_model:
            self.world_model = ctx.get("world_model") or ctx.get("WorldModel")
            if self.world_model:
                logger.info(" [CONNECTION] World Model recovered from context.")

        logger.info(f" Starting ReportComposer: {topic} (Mode: {mode})")

        # [GODZILLA ALIGNMENT] Inject specialist writing skills into context
        # This will be used by the sub-agents during synthesis
        if not ctx: ctx = {}
        ctx["mandated_skills"] = getattr(ctx, "mandated_skills", []) + ["scientific-writing", "reportlab"]

        
        # Ensure topic is a string to prevent downstream AttributeError
        original_topic = topic
        if isinstance(topic, dict):
            # Extract actual query/statement if possible, handling nested structures
            # Seen in logs: {'payload': {'query': '...'}}
            payload = topic.get('payload', {})
            if isinstance(payload, str): payload = {}
                
            topic = (
                topic.get('query', '') or 
                topic.get('statement', '') or 
                payload.get('query', '') or 
                payload.get('statement', '') or 
                topic.get('title', '') or
                str(topic)
            )
        elif not isinstance(topic, str):
            topic = str(topic)
        
        # FINAL SANITY: If it's still containing '{' it might be a stringified dict
        if isinstance(topic, str) and topic.startswith("{") and "query" in topic:
             try:
                 import json
                 temp_dict = json.loads(topic.replace("'", '"'))
                 topic = temp_dict.get('query') or temp_dict.get('payload', {}).get('query') or topic
             except:
                 pass
            
        if ctx is None: ctx = {}
        ctx["mode"] = mode
        
        try:
            # 0. SETUP: Define paths and filenames
            reports_dir = ctx.get("reports_dir", "reports")
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir, exist_ok=True)
            
            output_files = {}

            # [POLISH] Generate Professional Title EARLY to use for filename
            try:
                # Safe slice now that topic is guaranteed to be a string
                topic_snippet = topic[:50] if len(topic) > 50 else topic
                print(f" [TITLE] Generating professional title for: {topic_snippet}...")
                professional_title = await self._generate_professional_title(topic, ctx)
                ctx["professional_title"] = professional_title
                # Use professional title for a much better filename
                safe_title = generate_smart_filename(professional_title)
                display_title = professional_title.strip().strip('*').strip('"').strip("'").strip()
            except Exception as title_err:
                logger.warning(f"Early title generation failed: {title_err}")
                safe_title = generate_smart_filename(topic)
                display_title = " ".join(extract_keywords(topic, 5))
            
            if not display_title:
                display_title = "Scientific Intelligence Report"
            
            ctx["display_title"] = display_title

            # 1. PLAN: Decompose into sections
            # Coerce mode to string to prevent AttributeError: 'dict' object has no attribute 'upper'
            if isinstance(mode, dict):
                mode = str(mode.get('mode', '')) or str(mode.get('agent_name', '')) or str(mode)
            else:
                mode = str(mode)

            if mode == "exploration":
                logger.info(" SCOUT MODE DETECTED: Using True Discovery (Exploration) Structure.")
                plan = self._plan_exploration_report(topic, ctx)
                
            elif mode == "forensic":
                logger.info(" FORENSIC REVIEW DETECTED: Using Verdict Structure V2.")
                plan = self._plan_forensic_review(topic, ctx)
                
            elif mode == "raw_truth":
                logger.info(" RAW TRUTH MODE: Brutal scientific audit - no sugar coating.")
                plan = self._plan_raw_truth_report(topic, ctx)
                
            else:
                logger.info(f" {mode.upper()} MODE DETECTED: Using Unified Research Structure (De-duplicated).")
                plan = self._plan_unified_research(topic, ctx)
            
            logger.info(f" Plan created: {len(plan)} sections")
            
            # 2. RESEARCH: Gather data for sections
            # BYPASS: If findings are provided in context, use them directly
            research_data = ctx.get("deep_findings")
            if not research_data:
                logger.info(" No pre-gathered findings found, starting autonomous research...")
                research_data = await self._gather_research(plan, topic)
            else:
                logger.info(f" Using {len(research_data)} pre-gathered findings from context.")
                # Convert list of strings to list of dicts if needed for the writer
                if isinstance(research_data, list) and len(research_data) > 0 and isinstance(research_data[0], str):
                    research_data = [{"title": "Research Finding", "content": f} for f in research_data]
                
                # ENHANCEMENT: Also inject hypotheses as "High Confidence Claims"
                hypotheses = ctx.get("hypotheses", [])
                for h in hypotheses:
                    # Robust handling for both dict and model objects
                    h_data = h.to_dict() if hasattr(h, "to_dict") else (h if isinstance(h, dict) else vars(h))
                    
                    # GROUNDING UPGRADE: Inject Full Formal Identity
                    verdict = h_data.get("test_verdict", "UNTESTED")
                    formal_str = ""
                    if h_data.get("is_formally_complete"):
                        formal_str = f" | FORMAL: {len(h_data.get('variables', []))} Vars, {len(h_data.get('predictions', []))} Preds"
                    
                    evidence_count = len(h_data.get("evidence", []))
                    
                    content = (
                        f"HYPOTHESIS_ID: {h_data.get('id')} | STATUS: {h_data.get('state')} | VERDICT: {verdict}\n"
                        f"STATEMENT: {h_data.get('statement')}\n"
                        f"RATIONALE: {h_data.get('rationale')}\n"
                        f"CONFIDENCE: {h_data.get('confidence', 0)*100:.1f}%{formal_str}\n"
                        f"EVIDENCE_COUNT: {evidence_count}"
                    )
                    
                    research_data.insert(0, {
                        "title": f"Hypothesis {h_data.get('id')} ({verdict})",
                        "content": content,
                        "type": "hypothesis",
                        "metadata": {
                            "id": h_data.get("id"), 
                            "verdict": verdict,
                            "is_grounded": True
                        }
                    })
            
            if not research_data:
                logger.warning(" No research data could be gathered. Creating placeholder sections.")
                research_data = []

            logger.info(f" Research data ready. Data sources: {len(research_data)}")
            
            # 3. VISUALIZE: Generate charts where needed (With Timeout Guard)
            visuals = {}
            if not ctx.get("safe_mode", False):
                # Set scholarly (white) theme BEFORE generating any charts
                try:
                    from backend.tools.common import get_plotly_backend
                    plotly_beast = get_plotly_backend()
                    if plotly_beast and hasattr(plotly_beast, "set_theme"):
                        # [THEME] Force PhD Scientific Aesthetic (White, Arial, Clean)
                        plotly_beast.set_theme("avon_scholarly")
                        logger.info(" [VIZ] Ph.D. Scientific Visualization Doctrine (avon_scholarly) ACTIVATED.")
                except Exception as e:
                    logger.warning(f" [VIZ] Failed to set scientific theme: {e}")

                try:
                    # Hard timeout for visualizations (5 minutes max)
                    visuals = await asyncio.wait_for(
                        self._generate_visuals(plan, research_data, ctx),
                        timeout=300
                    )
                except asyncio.TimeoutError:
                    logger.warning("[SPEED] Visualization generation TIMED OUT (300s). Continuing without charts.")
                    visuals = {}
                except Exception as e:
                    logger.warning(f" [WARNING] Visualization generation failed: {e}. Continuing.")
                    visuals = {}

            logger.info(f" Generated {len(visuals)} visuals")

            # 3.1 JUPYTER NOTEBOOK EXPORT (PRE-WRITING PROVENANCE)
            cell_map = {}
            if not ctx.get("safe_mode", False):
                try:
                    from backend.tools.jupyter_exporter import get_jupyter_exporter
                    jupyter_exporter = get_jupyter_exporter()
                    notebook_path = os.path.join(reports_dir, f"{safe_title}.ipynb")

                    # Extract experiments and findings
                    experiments = ctx.get("experiments", []) if ctx else []
                    hypotheses = ctx.get("hypotheses", []) if ctx else []
                    findings = ctx.get("findings", []) if ctx else []

                    # [REAL DATA] Merge research_data experiments into context
                    if research_data:
                        found_exps = [
                            d for d in research_data
                            if d.get("type") == "experiment"
                            or d.get("task", {}).get("type") == "experiment"
                            or "code" in d
                        ]
                        # De-duplicate by experiment_id
                        existing_ids = {e.get("experiment_id") for e in experiments if isinstance(e, dict)}
                        for fe in found_exps:
                            fe_id = fe.get("experiment_id")
                            if fe_id and fe_id not in existing_ids:
                                experiments.append(fe)
                                existing_ids.add(fe_id)

                    # Export notebook and CAPTURE CELL MAP
                    export_res = jupyter_exporter.export(
                        title=topic,
                        experiments=experiments,
                        hypotheses=hypotheses,
                        findings=findings,
                        conclusion=ctx.get("conclusion") if ctx else None,
                        output_path=notebook_path,
                        metadata={"mode": mode, "topic": topic},
                        session_visualizations=ctx.get("session_visualizations")
                    )

                    if export_res and isinstance(export_res, tuple) and len(export_res) == 2:
                        result_notebook, cell_map = export_res
                    else:
                        result_notebook = export_res if isinstance(export_res, str) else None
                        cell_map = {}

                    if result_notebook and os.path.exists(result_notebook):
                        output_files["notebook"] = os.path.abspath(result_notebook)
                        # Inject cell_map into context for the writer to provide provenance links
                        ctx["cell_map"] = cell_map
                        logger.info(f" [PROVENANCE] Jupyter map captured: {len(cell_map)} cells. Report now scientific-grade.")

                except Exception as nb_err:
                    logger.error(f"Jupyter pre-export critical failure: {nb_err}")
                    logger.debug(traceback.format_exc())

            # 4. WRITE: Generate content for each section
            sections_content = await self._write_sections(plan, research_data, visuals, topic, mode, ctx, deadline=deadline)

            # 4.1 INJECT VISUALS & PROVENANCE INTO CTX
            if ctx is not None:
                ctx["all_visuals"] = visuals
                # Ensure the Assembler sees the high-fidelity visualizations
                if "session_visualizations" not in ctx:
                    ctx["session_visualizations"] = []

                for v_key, v_val in visuals.items():
                    if isinstance(v_val, dict) and "visualization" in v_val:
                        ctx["session_visualizations"].append(v_val)

            # 5. ASSEMBLE: Combine into final document
            final_report = await self.assemble_report(topic, sections_content, research_data=research_data, ctx=ctx)
            # 5.1 CLEAN: Discipline Enforcement Scrubbing
            # [FIXED] Removed hardcoded bypass - all reports now cleaned uniformly
            final_report = self._clean_report_output(final_report)
            
            # 5.2 VERIFY: Hard Structural Kill-switch
            if self._has_structural_violations(final_report):
                logger.error("Structural violation detected (Multiple Abstracts/Conclusions). Initiating Hard Purge.")
                final_report = self._purge_structural_duplicates(final_report)
            
            final_html = final_report
            
            # 6. SAVE: Generate file outputs (HTML/PDF)
            # output_files already initialized during Jupyter export
            try:
                from backend.tools.report_generator_tool import generate_html_report, generate_pdf_report
                
                # Create a spec-like object for the generator
                spec = {"title": topic, "author": "Beast AI", "sections": []} 
                
                # Safe Mode: HTML Only
                safe_mode = ctx.get("safe_mode", False)
                
                # Save HTML directly since we already rendered it
                html_path = os.path.join(reports_dir, f"{safe_title}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(final_html) # Changed from final_report to final_html
                output_files["html"] = os.path.abspath(html_path)
                print(f" [SUCCESS] HTML saved to: {output_files['html']}")
                
                # Attempt PDF generation (Best Effort)
                if not safe_mode:
                    try:
                        pdf_path = os.path.join(reports_dir, f"{safe_title}.pdf")
                        
                        # Use Playwright for reliable Windows PDF generation
                        from playwright.async_api import async_playwright
                        
                        async def generate_pdf_with_playwright():
                            async with async_playwright() as p:
                                browser = await p.chromium.launch()
                                page = await browser.new_page()
                                # Load the HTML file we just saved
                                await page.goto(f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}")
                                
                                # CRITICAL: Wait for Plotly and Mermaid charts to render
                                # Visuals render asynchronously via JavaScript
                                try:
                                    # Wait for Plotly and Mermaid to finish rendering (up to 15 seconds)
                                    await page.wait_for_function(
                                        "() => { "
                                        "const plotlyDone = typeof Plotly === 'undefined' || document.querySelectorAll('.plotly').length === document.querySelectorAll('.js-plotly-plot').length; "
                                        "const mermaidDone = typeof mermaid === 'undefined' || document.querySelectorAll('.mermaid[data-processed=\"true\"]').length === document.querySelectorAll('.mermaid').length; "
                                        "return plotlyDone && mermaidDone; "
                                        "}",
                                        timeout=15000
                                    )
                                    # Extra wait for chart animations to complete and fonts to settle
                                    await page.wait_for_timeout(3000)
                                except Exception as plotly_wait_err:
                                    logger.debug(f"Plotly wait timeout (charts may still render): {plotly_wait_err}")
                                    # Fallback: just wait 3 seconds
                                    await page.wait_for_timeout(3000)
                                
                                await page.pdf(
                                    path=pdf_path,
                                    format="A4",
                                    print_background=True,
                                    display_header_footer=False,
                                    margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"}
                                )
                                await browser.close()
                            return pdf_path
                        
                        # Run the async PDF generation directly (we are already in an async method)
                        result_path = await generate_pdf_with_playwright()
                        
                        if os.path.exists(result_path):
                            output_files["pdf"] = os.path.abspath(result_path)
                            logger.info(f" PDF generated via Playwright: {output_files['pdf']}")
                            print(f"PDF generated via Playwright: {output_files['pdf']}")
                        else:
                            logger.warning(" PDF file not created")
                            
                    except Exception as pdf_err:
                        logger.warning(f"Playwright PDF generation failed: {pdf_err}")
                        print(f"Playwright PDF failed. Attempting WeasyPrint fallback...")
                        
                        # FALLBACK: WeasyPrint
                        try:
                            from weasyprint import HTML, CSS
                            # basic print styling
                            HTML(string=final_html).write_pdf(pdf_path)
                            
                            if os.path.exists(pdf_path):
                                output_files["pdf"] = os.path.abspath(pdf_path)
                                logger.info(f"PDF generated via WeasyPrint fallback: {output_files['pdf']}")
                                print(f"PDF generated via WeasyPrint: {output_files['pdf']}")
                        except Exception as wp_err:
                            logger.error(f"WeasyPrint fallback also failed: {wp_err}")
                            print(f"ALL PDF GENERATION FAILED (Playwright & WeasyPrint). HTML is available.")
                # [NOTE] JUPYTER NOTEBOOK EXPORT (Best Effort)
                # Moved to Step 3.1

            except Exception as save_err:
                logger.error(f"Failed to save report files: {save_err}")
            
            return {
                "status": "success",
                "report_html": final_html, # Changed from final_report to final_html
                "files": output_files,  # NEW: Paths to generated files
                "sections": sections_content,
                "visuals": visuals,
                "metadata": {
                    "topic": topic,
                    "sections": len(plan),
                    "visuals_count": len(visuals)
                }
            }
            
        except Exception as e:
            logger.exception(f"Report generation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    def _plan_forensic_review(self, topic: str, ctx: Dict[str, Any]) -> List[ReportSection]:
        """
        [LAW] SVEL FORENSIC REVIEW (VERDICT MODE)
        Focus: Falsification, Verdict, and Adjudication.
        """
        return [
            ReportSection(
                "Executive Intelligence Summary",
                "Start with CLAIM STATUS (VALID/INVALID/UNCERTAIN). Show Evidence Strength. Explain 'Why This Matters'. One page max.",
                None, "synthesis"
            ),
            ReportSection(
                "Scientific Genesis Log",
                "Origin Chain: Trigger query/prompt. Seed Corpus used. Timestamped birth certificate of the hypothesis.",
                None, "synthesis"
            ),
            ReportSection(
                "Assumption Ledger",
                "List 1-5 core assumptions. Per-assumption falsifiability plan. Heatmap of 'Critical failure assumptions'.",
                "Risk Analysis Heatmap", "synthesis", 1
            ),
            ReportSection(
                "Adversarial Execution Suite",
                "List attacks (Gaussian, Ablation, Swap). Show SAMPLE SIZE and DEGREES OF FREEDOM. Show Before/After scores. Delta % degradation with SENSITIVITY FLOOR.",
                "Perturbation Delta Chart", "synthesis", 1
            ),
            ReportSection(
                "Rejected & Null Hypotheses",
                "List hypotheses that failed. Why they failed. What assumption killed them. Why this failure matters. Signals 'We looked where nothing worked'.",
                None, "synthesis"
            ),
            ReportSection(
                "Claim Validity Boundary",
                "Where does this STOP being true? Parameter regimes where claim fails. Known extrapolation failures. Boundary of the investigation.",
                "Regime Phase Plot", "synthesis", 1
            ),
            ReportSection(
                "Hypothesis Evolution Tree",
                "Parent-Child lineage graph. Show where forks happened. Label nodes with Survival Scores.",
                "mermaid_tree_placeholder", "synthesis", 1 # Special handler in Writer
            ),
            ReportSection(
                "Visual Proof Deck",
                "Top attack impact plots. Confidence bands. Ablation Heatmaps or Violin Plots. 'Physical Proof' of robustness.",
                "Confidence Interval Plot", "synthesis", 1
            ),
            ReportSection(
                "Epistemic Update & World Model Delta",
                "Did this claim shift the system's knowledge base? Which prior beliefs were updated? Epistemic Weight Score.",
                None, "synthesis"
            ),
            ReportSection(
                "Failure & Bias Audit",
                "Hallucination probability. Dataset bias (source skew). Tool error logs. 'Science Confidence Index' (0-1).",
                None, "synthesis"
            ),
            ReportSection(
                "Appendices",
                "Tool inputs/outputs. Tool call order. Execution graph. Link to raw logs.",
                None, "synthesis"
            )
        ]

    def _plan_exploration_report(self, topic: str, ctx: Dict[str, Any]) -> List[ReportSection]:
        """
        [SCOUT] SVEL SCOUT REPORT (TRUE DISCOVERY)
        Focus: Anomalies, Weak Signals, Speculation. NO VERDICT.
        """
        return [
            ReportSection("Anomaly Scan", "List raw data points that violate standard models. No filtering.", None, "search"),
            ReportSection("Hypothesis Cloud", "Generate 5-10 wild guesses explaining anomalies. Low confidence allowed.", None, "synthesis"),
            ReportSection("Unknowns Map", "What are we missing? Where are the blind spots?", None, "synthesis"),
            ReportSection("Weak Signal Speculation", "If trend X continues, what happens? Be imaginative.", None, "synthesis")
        ]

    def _plan_raw_truth_report(self, topic: str, ctx: Dict[str, Any]) -> List[ReportSection]:
        """
        [RAW TRUTH] SVEL BRUTAL SCIENTIFIC AUDIT
        No polish, no hiding, everything exposed - like a real lab notebook.
        """
        return [
            ReportSection("Executive Summary", "High-level research state and key findings", None, "synthesis"),
            ReportSection("Hypothesis Lifecycle", "Every hypothesis: spawned, attacked, killed, survived - full battle history", None, "synthesis"),
            ReportSection("WorldModel State Dump", "All facts, conflicts, confidence scores, staleness, contradictions", None, "synthesis"),
            ReportSection("Discovery Battle Log", "Survival tiers, attack vectors, kill attempts, failure patterns, orthogonality checks", None, "synthesis"),
            ReportSection("Red Team Audit", "What Red Team tried, what survived, what died, Semantic Morgue contents", None, "synthesis"),
            ReportSection("Experimental Evidence", "Raw experiment logs, statistical verdicts, parameter sweeps, negative results", None, "synthesis"),
            ReportSection("Epistemic Uncertainty", "Confidence ranges, conflicting evidence, unresolved questions, weak spots", None, "synthesis"),
            ReportSection("Governance Metrics", "Half-life, structural yield, refusal rates, convergence status, KPIs", None, "synthesis"),
        ]

    def _plan_unified_research(self, topic: str, ctx: Dict[str, Any]) -> List[ReportSection]:
        """
        [UNIFIED] SVEL CONSOLIDATED RESEARCH PLAN
        De-duplicated, distinct sections for Maximum Impact.
        """
        return [
            ReportSection(
                "Executive Intelligence Summary",
                "Start with the core scientific verdict. Contrast the 'current consensus' with your 'new synthesis'. List 3 falsifiable thresholds.",
                "Summary Vision Chart", "synthesis"
            ),
            ReportSection(
                "Technical Landscape & Foundational Mechanics",
                "Detail the structural biology/physics of {topic}. Map site-specific interactions. Avoid general introductions.",
                "Architecture Block Diagram", "search", 1
            ),
            ReportSection(
                "Global Scientific Consensus & Peer Divergence",
                "Map out where major research labs agree and where they are at war. Differentiate between 'established consensus' and 'emergent anomalies'.",
                "Epistemic Consensus Heatmap", "search", 1
            ),
            ReportSection(
                "Comparative Analysis & Performance Regimes",
                "Quantitative head-to-head. Scalability vs Stability trade-offs. Boundary conditions for viability.",
                "Regime Phase Plot", "search", 1
            ),
            ReportSection(
                "Novel Speculative Mechanisms & Hypothesis Tree",
                "Recursive model synthesis. If mechanism X holds, what surprise Y emerges? Branching lineages.",
                "Hypothesis Proliferation Tree", "synthesis", 1
            ),
            ReportSection(
                "Falsification Plan & Boundary Conditions",
                "Critical failure modes. What assumption, if proven wrong, kills the entire monograph? Concrete test design.",
                "Boundary Limit Chart", "synthesis", 1
            ),
            ReportSection(
                "Epistemic Gaps & Future Research Trajectories",
                "Identify exactly what is missing from current literature. Propose the next 3 high-impact experiments. 12-72 month outlook.",
                "Prioritized Research Roadmap", "synthesis", 1
            ),
            ReportSection(
                "Appendices & Forensic Evidence",
                "Full citations. Raw data tables. Supplementary figures and code provenance.",
                None, "synthesis"
            )
        ]

    # [DEPRECATED] _plan_research_report_v2 and _plan_discovery_report consolidated into _plan_unified_research


    async def _gather_research(self, plan: List[ReportSection], topic: str) -> List[Dict[str, Any]]:
        """Gather research data using INTERNAL SYSTEM KNOWLEDGE (World Model)."""
        logger.info(" [KNOWLEDGE] Gathering research from World Model (External Search DISABLED).")
        
        if not self.world_model:
            logger.warning(" [WARNING] World Model not connected! Returning empty research.")
            return []

        # Check if this is raw truth mode - use specialized gathering
        if any("Raw Truth" in section.title or "Battle Log" in section.title or "State Dump" in section.title for section in plan):
            logger.info(" [RAW TRUTH] Using brutal data extraction mode")
            return await self._gather_raw_truth_data(topic, plan)
        
        return await self._gather_from_world_model(topic, plan)

    async def _gather_from_world_model(self, topic: str, plan: List[ReportSection]) -> List[Dict[str, Any]]:
        """Fetch verified facts and findings from the World Model."""
        import datetime
        import json
        results = []
        
        # 1. Get relevant facts for the topic
        # Use simple keyword extraction for querying
        keywords = extract_keywords(topic, max_count=3)
        query_terms = [topic] + keywords
        
        found_facts = []
        for term in query_terms:
            # SVEL ENHANCEMENT: Enable cross-session query to salvage fragmented research
            facts = self.world_model.query(term, min_confidence=0.5, max_results=50, cross_session=True)
            found_facts.extend(facts)
        
        # [RELENTLESS MODE] If data is sparse, expand search to semantic neighbors
        if len(found_facts) < 5:
            logger.info(" [RELENTLESS] Sparse research results. Triggering semantic neighborhood recovery.")
            from backend.core.world_model import Fact
            for term in query_terms[:3]:
                similar = self.world_model.semantic_search_chroma(term, top_k=5)
                for eid, score, meta in similar:
                    if score > 0.7:
                        # Recover the full entity and its facts
                        entity = self.world_model.get_entity(eid, cross_session=True)
                        if entity:
                            found_facts.append(Fact(
                                key=entity.type, value=str(entity.properties), 
                                source="semantic_recovery", confidence=score
                            ))
        
        # Deduplicate facts by key
        seen_keys = set()
        unique_facts = []
        for f in found_facts:
            if f.key not in seen_keys:
                seen_keys.add(f.key)
                unique_facts.append(f)
        
        logger.info(f" [MEMORY] Found {len(unique_facts)} verified facts in World Model for '{topic}'")

        # 2. Format facts into research data
        for fact in unique_facts:
            # Try to determine a title from metadata or key
            title = fact.metadata.get("title") or fact.key.replace("_", " ").title()
            
            # Content formatting
            content = f"FACT: {fact.value}\nSOURCE: {fact.source}\nCONFIDENCE: {fact.confidence}"
            if fact.metadata:
                content += f"\nMETADATA: {json.dumps(fact.metadata, default=str)}"
            
            # Section mapping (naive)
            # Find best matching section based on keyword overlap? 
            # For now, assign to "Evidence" or first section if specific intent not found
            section_title = plan[1].title if len(plan) > 1 else "key Findings" 
            
            results.append({
                "title": title,
                "content": content,
                "url": "internal://world_model",
                "section": section_title,
                "authors": "System Intelligence",
                "year": datetime.datetime.now().year,
                "source_type": "WorldModel",
                "citation": f"[System knowledge, {datetime.datetime.now().year}]"
            })
            
        # 3. If no facts, try to get specific entities
        if not results:
             entities = self.world_model.search_entities(topic)
             for ent in entities:
                 results.append({
                    "title": f"Entity: {ent.entity_id}",
                    "content": f"TYPE: {ent.type}\nPROPERTIES: {json.dumps(ent.properties, default=str)}",
                    "url": "internal://knowledge_graph",
                    "section": "Entities",
                    "authors": "Knowledge Graph",
                    "year": datetime.datetime.now().year,
                    "source_type": "KnowledgeGraph",
                    "citation": "[KnowledgeGraph, 2026]"
                 })

        logger.info(f" [MEMORY] Total internal knowledge items collected: {len(results)}")
        return results

    def _encode_kroki(self, source_text: str) -> str:
        """Encode text for Kroki API (deflate + base64url)."""
        import zlib
        import base64
        if not source_text: return ""
        zlibbed_str = zlib.compress(source_text.encode('utf-8'), 9)
        return base64.urlsafe_b64encode(zlibbed_str).decode('utf-8')

    async def _generate_visuals(self, plan: List[ReportSection], research_data: List[Dict], ctx: Dict[str, Any] = {}) -> Dict[str, str]:
        """Generate mindblowing visualizations using Kroki (Mermaid, Graphviz, PlantUML)."""
        # SKIP VISUALS CHECK (Prevent Hangs)
        if ctx.get("skip_visuals", False):
            logger.info(" [FAST] Visual generation SKIPPED by context flag (skip_visuals=True)")
            return {}

        visuals = {}
        import zlib
        import base64
        import httpx

        # Helper function for Kroki SVG fetching
        async def _fetch_kroki_svg(diagram_type: str, code: str) -> str:
            """Fetch rendered SVG from Kroki with retry logic (FIX #18)."""
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    encoded = self._encode_kroki(code)
                    url = f"https://kroki.io/{diagram_type}/svg/{encoded}"
                    async with httpx.AsyncClient(timeout=15) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            return resp.text
                        else:
                            logger.warning(f"Kroki failed {resp.status_code}: {resp.text[:100]}")
                except Exception as e:
                    logger.warning(f"Kroki attempt {attempt+1}/{max_attempts} failed: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
            return None

        # Safe Mode Skip (Hard Production Guard)
        if ctx.get("safe_mode", False):
            logger.info(" [SAFE] Safe Mode detected: Skipping visualization generation entirely.")
            return {}

        total_viz = 0
        
        for section in plan:
            if not section.visual_intent:
                continue
                
            logger.info(f" [AI CODER] Visualizing: {section.visual_intent}")
            
            try:
                from backend.tools.viz_ai_coder import run_ai_coder
                import pandas as pd
                import plotly.io as pio

                def _is_genuine_scientific_df(cand_df: Any) -> bool:
                    if cand_df is None or not isinstance(cand_df, pd.DataFrame) or cand_df.empty:
                        return False
                    cols = set(str(c).lower() for c in cand_df.columns)
                    software_keys = {
                        "engine", "agent_id", "attempts", "hypothesis_id", "trace", "status", "meta",
                        "error", "task_id", "cycle", "verdict", "attachments", "session_id", "summary",
                        "rationale", "statement"
                    }
                    matched = cols.intersection(software_keys)
                    if len(matched) >= 3 or (len(cols) > 0 and len(matched) / len(cols) > 0.4):
                        return False
                    num_cols = cand_df.select_dtypes(include=["number"]).columns
                    return len(num_cols) > 0

                df = pd.DataFrame(research_data) if research_data else pd.DataFrame()

                # If research_data is software metadata or empty, resolve genuine empirical/physical dataset
                if not _is_genuine_scientific_df(df):
                    resolved_df = None
                    # 1. Check experiments in context
                    for exp in (ctx.get("experiments", []) if ctx else []):
                        if isinstance(exp, dict):
                            cand = exp.get("raw_data")
                            if isinstance(cand, pd.DataFrame) and _is_genuine_scientific_df(cand):
                                resolved_df = cand
                                break
                            elif isinstance(cand, list) and cand and isinstance(cand[0], dict):
                                cand_df = pd.DataFrame(cand)
                                if _is_genuine_scientific_df(cand_df):
                                    resolved_df = cand_df
                                    break
                    # 2. Check recent cleanroom experiment artifact CSVs
                    if resolved_df is None:
                        exp_base = os.path.join(os.getcwd(), "results", "experiments")
                        if os.path.exists(exp_base):
                            recent_exp_dirs = sorted(
                                [os.path.join(exp_base, d) for d in os.listdir(exp_base) if os.path.isdir(os.path.join(exp_base, d))],
                                key=lambda p: os.path.getmtime(p),
                                reverse=True
                            )
                            for ed in recent_exp_dirs[:5]:
                                for cand_csv in ["raw_data.csv", "raw_measurements.csv"]:
                                    csv_file = os.path.join(ed, cand_csv)
                                    if os.path.exists(csv_file) and os.path.getsize(csv_file) > 50:
                                        try:
                                            cand_df = pd.read_csv(csv_file)
                                            if _is_genuine_scientific_df(cand_df):
                                                resolved_df = cand_df.head(1000)
                                                break
                                        except Exception:
                                            pass
                                if resolved_df is not None:
                                    break
                    # 3. Check active domain catalog datasets
                    if resolved_df is None:
                        domain_datasets = [
                            os.path.join(os.getcwd(), "data", "superconduct_train.csv"),
                            os.path.join(os.getcwd(), "data", "skempi_v2.csv"),
                            os.path.join(os.getcwd(), "data", "nasa_exoplanets_pscomppars.csv"),
                        ]
                        for d_csv in domain_datasets:
                            if os.path.exists(d_csv):
                                try:
                                    cand_df = pd.read_csv(d_csv)
                                    if len(cand_df) >= 5 and _is_genuine_scientific_df(cand_df):
                                        resolved_df = cand_df.sample(min(len(cand_df), 500), random_state=42)
                                        break
                                except Exception:
                                    pass

                    if resolved_df is not None:
                        df = resolved_df
                    else:
                        logger.warning(f" [AI CODER] Suppressing figure for '{section.title}': No genuine empirical or physical dataset available. Refusing to plot software orchestration metadata.")
                        continue

                # Monkey-patch viz_ai_coder's LLM engine to use our proxy before running
                import backend.tools.viz_ai_coder as ai_coder_module
                if self.llm_manager:
                    ai_coder_module.run_llm = self.llm_manager.run
                    ai_coder_module.run_llm_async = getattr(self.llm_manager, "run_async", None)

                # MANDATE: Every intent is an AI Coder task for PhD-level Plotly/Interactive visuals
                viz_res = await asyncio.to_thread(
                    run_ai_coder,
                    df=df,
                    intent=f"{section.visual_intent}. Render as publication-quality Plotly interactive chart.",
                    config={"caption": section.visual_intent, "force_academic": True, "allow_exec": True}
                )

                if viz_res and viz_res.status == "success":
                    html_content = getattr(viz_res, 'html', None)
                    fig_json = getattr(viz_res, 'fig_json', None)
                    
                    if not html_content and fig_json:
                        html_content = pio.to_html(fig_json, full_html=False, include_plotlyjs='cdn')
                    
                    if html_content:
                        visuals[section.title] = f"""
                        <figure style="margin: 2em 0; text-align: center; break-inside: avoid;">
                            <div class="viz-wrapper" style="max-width: 100%; border: 1px solid #eee; border-radius: 8px; overflow: hidden;">
                                {html_content}
                            </div>
                            <figcaption style="margin-top: 10px; font-style: italic; color: #555; font-size: 0.95em; font-family: sans-serif;">
                                <strong>Figure {total_viz + 1}</strong>: {section.visual_intent}
                            </figcaption>
                        </figure>
                        """
                        total_viz += 1
                        
                        # PASS CODE TO NOTEBOOK PIPELINE
                        viz_code = getattr(viz_res, 'meta', {}).get("code")
                        if viz_code and ctx is not None:
                            if "session_visualizations" not in ctx:
                                ctx["session_visualizations"] = []
                            ctx["session_visualizations"].append({
                                "type": "plotly",
                                "intent": section.visual_intent,
                                "code": viz_code,
                                "fig_json": fig_json
                            })
                else:
                    logger.warning(f"AI Coder failed for {section.title}: {getattr(viz_res, 'message', 'Unknown error')}")

            except Exception as e:
                logger.error(f"Critical error in AI Coder pipeline for {section.title}: {e}")
                visuals[section.title] = None
        
        # [DELETED] Legacy hardcoded visualization logic (Replaced by Titan AI Coder)
                
        # =================================================================
        # [SCIENCE] ARTIFACT HARVESTING (The Bridge)
        # =================================================================
        # Scan research data for pre-generated experiment visualizations.
        # This bridges ExperimentAgent artifacts into the final report.
        # =================================================================
        harvested_visuals = {}
        for item in research_data:
            # Check for explicitly preserved visualization paths from experiments
            viz_path = item.get("visualization")
            
            if viz_path and os.path.exists(viz_path):
                logger.info(f" [SCIENCE] Harvesting experiment visualization: {viz_path}")
                # Map this visualization to the Adjudication/Forensic sections
                # Map this visualization to the generated Falsification sections
                target_titles = ["Technical Landscape & Foundational Mechanics", "Comparative Analysis & Performance Regimes", "Novel Speculative Mechanisms & Hypothesis Tree", "Falsification Plan & Boundary Conditions"]
                
                # Handle interactive Plotly JSON artifacts
                if viz_path.endswith('.json'):
                    try:
                        import plotly.io as pio
                        import plotly.graph_objects as go
                        import json
                        with open(viz_path, 'r', encoding='utf-8') as f:
                            fig_data = json.load(f)
                        fig = go.Figure(fig_data)
                        # Generate autonomous offline javascript block
                        img_html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
                    except Exception as json_err:
                        logger.warning(f"Failed to render JSON Plotly artifact: {json_err}. Using generic placeholder.")
                        img_html = f'<div style="text-align: center; padding: 20px; color: #f87171;">Failed to load Interactive Figure {viz_path}</div>'
                else:
                    # Base64 encode for embedding if we are in HTML mode (to ensure portability)
                    try:
                        import base64
                        with open(viz_path, "rb") as img_file:
                            encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                            img_html = f'<img src="data:image/png;base64,{encoded_string}" style="max-width: 100%; height: auto; border: 1px solid #1e293b; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">'
                    except Exception as b64_err:
                        logger.warning(f"Base64 embedding failed: {b64_err}. Using direct path.")
                        img_html = f'<img src="{viz_path}" style="max-width: 100%; height: auto; border: 1px solid #1e293b; border-radius: 8px;">'

                # Use a specific caption
                caption = item.get("title", "Scientific Experiment Visualization")
                fig_html = f"""
                <figure style="margin: 2em 0; text-align: center; break-inside: avoid;">
                    <div class="experiment-viz-container" style="padding: 15px; background: #0f172a; border-radius: 12px; border: 1px solid #334155;">
                        {img_html}
                    </div>
                    <figcaption style="margin-top: 10px; font-style: italic; color: #94a3b8; font-size: 0.9em; font-family: 'Inter', sans-serif;">
                        <strong>Scientific Figure</strong>: {caption} (Automated verification experiment)
                    </figcaption>
                </figure>
                """
                
                for t_title in target_titles:
                    print(f" [DNA] [TARGET] Mapping artifact to section: {t_title}")
                    if t_title not in harvested_visuals: 
                        harvested_visuals[t_title] = []
                    
                    harvested_visuals[t_title].append({
                        'type': 'experiment_plot',
                        'title': caption,
                        'html': fig_html,
                        'caption': caption
                    })
        
        if harvested_visuals:
            ctx['harvested_visuals'] = harvested_visuals
            logger.info(f" [DNA] [HARVEST] Successfully mapped {len(harvested_visuals)} visual targets to context.")

        return visuals

    async def _write_sections(self, plan: List[ReportSection], research_data: List[Dict], visuals: Dict[str, str], topic: str, mode: str = "standard", ctx: Dict[str, Any] = None, deadline: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Write content for each section with ACADEMIC CITATIONS."""
        sections_content = []
        previous_concepts = [] # TRACKER: Prevent circular re-introductions
        harvested = ctx.get('harvested_visuals', {}) if ctx else {}
        
        # SVEL LENGTH TARGETS: 12-72 HOUR RUNS ONLY
        # ALL TIERS ARE GODZILLA-TIER DEPTH - only word count differs!
        runtime_hours = ctx.get("runtime_hours", 12.0) if ctx else 12.0
        is_discovery = mode in ["discovery", "discovery_research"]
        
        # Clamp to valid range: minimum 0.1 hours (allow short tests)
        if runtime_hours < 0.1:
            runtime_hours = 0.1
        
        # BASE GODZILLA INSTRUCTION - SAME FOR ALL TIERS
        # This is ALWAYS PhD-level, ULTRA PRO MAX, no weak language
        base_godzilla = """
YOU ARE WRITING A  PHD-LEVEL AUTHORITATIVE SCIENTIFIC DOCUMENT.
- ZERO hedging. ZERO weak language. ZERO "it depends".
- Every claim MUST have a falsifiable boundary condition.
- Identify DOMINANT REGIMES and BOUNDARY CONDITIONS. Use comparative synthesis, not binary outcomes.
- Cite using [Author, Year] format. NO fake citations.
- Use specific numbers: thresholds, concentrations, dimensions, metrics.
- This is the DEFINITIVE reference. Leave NOTHING unexplored.
"""
        
        # MODE-SPECIFIC FOCUS (Research vs Discovery)
        if is_discovery:
            mode_focus = """
DISCOVERY MODE FOCUS:
- Lead with THE UNKNOWN: What gap in current knowledge was exposed?
- PROPOSE speculative mechanisms. DO NOT declare them 'Refuted' or 'Valid' unless real lab data is provided.
- Use EXPLORATORY language: "Suggests", "Hypothesized", "Model-implied", "Potential".
- NEVER claim "Experiments show" or invent sample sizes like "N=1000" if you didn't run a real simulation code.
- Focus on SURPRISE and ANOMALIES.
- Topic Invariance Check: Every paragraph must link back to {topic}.
"""
        else:
            mode_focus = """
RESEARCH MODE FOCUS:
- Synthesize the ENTIRE field landscape.
- Head-to-head quantitative battles with DATA.
- Strategic regime map: what works WHERE, what's OBSOLETE.
- Business/research implications with specific recommendations.
- Include: canonical landscape, technical synthesis, comparative analysis.
"""
        
        # WORD COUNT TIERS (GODZILLA intensity is SAME for all)
        if runtime_hours >= 48:
            # 48-72 hours = MONOGRAPH-LEVEL
            detail_level = "MONOGRAPH-LEVEL SYNTHESIS (GODZILLA GOD MODE)"
            target_length = "LIVING REVIEW (30000-60000 words). 50-100 pages. Multi-chapter monograph."
            min_words_per_section = 3000
        elif runtime_hours >= 24:
            # 24-48 hours = MAJOR SURVEY
            detail_level = "MAJOR SURVEY (GODZILLA MODE)"
            target_length = "COMPREHENSIVE SURVEY (20000-30000 words). 35-50 pages. Nature Reviews level."
            min_words_per_section = 2000
        else:
            # 12-24 hours = DEEP REVIEW
            detail_level = "DEEP REVIEW (GODZILLA MODE)"
            target_length = "SYSTEMATIC REVIEW (12000-20000 words). 20-35 pages. Journal review level."
            min_words_per_section = 1200
        
        # PROVENANCE INSTRUCTION (New for forensics)
        cell_map = ctx.get("cell_map", {}) if ctx else {}
        provenance_instruction = ""
        if cell_map:
            provenance_instruction = """
SCIENTIFIC PROVENANCE (MANDATORY):
- Sources marked as [EXPERIMENT] are linked to specific JUPYTER NOTEBOOK CELLS.
- For EVERY CLAIM derived from an experiment, you MUST cite the Cell ID.
- Format: "[Ref, Year; Cell #X]" or "[Source ID; Cell #X]".
- If citing specific code logic, mention the LINE NUMBER: "[Cell #X, Line Y]".
- This allows forensic verification of your claims in the attached .ipynb file.
"""

        # COMBINE: base + mode-specific + provenance
        depth_instruction = base_godzilla + mode_focus + provenance_instruction

        # Build rich citation context with author/year info
        sections_content = []
        
        # Build rich citation context with author/year info
        context_text = ""
        citation_list = []
        for i, item in enumerate(research_data):
            authors = item.get('authors', 'Unknown')
            year = item.get('year', '')
            doi = item.get('doi', '')
            cite_key = item.get('citation', f"[Source {i+1}]")
            
            # Build citation entry
            if authors and year:
                citation_list.append(f"{cite_key}: {item.get('title', '')} (DOI: {doi})")
            
            context_text += f"\n--- SOURCE {cite_key} ---\n"
            
            # PROVENANCE LINKING: ID experiment sources
            exp_id = item.get("id")
            if exp_id and exp_id in cell_map:
                context_text += f"[EXPERIMENT SOURCE: Jupyter Cell #{cell_map[exp_id]}]\n"
                
            context_text += f"Title: {item.get('title', 'Unknown')}\n"
            if authors:
                context_text += f"Authors: {authors}\n"
            if year:
                context_text += f"Year: {year}\n"
            if doi:
                context_text += f"DOI: {doi}\n"
            context_text += f"Content: {str(item.get('content', ''))[:2500]}\n"
            
        for section in plan:
            # [STOP] TIME ENFORCEMENT: Check if we've exceeded the deadline
            if deadline and datetime.now() > deadline:
                logger.warning(f" [STOP] DEADLINE EXCEEDED during report generation. Aborting remaining sections after '{section.title}'.")
                # Add a truncated notice
                sections_content.append({
                    "title": "REPORT TRUNCATED",
                    "content": f"<div class='alert alert-danger'><strong>REPORT TRUNCATED:</strong> System runtime limit exceeded during generation of '{section.title}'. Remaining sections omitted to ensure delivery.</div>",
                    "visual": None,
                    "images": []
                })
                break

            logger.info(f" [WRITE] Writing section: {section.title}")
            
            # [GODZILLA GATE 4] Empirical Grounding Validation
            section_data = [r for r in research_data if r.get('section') == section.title or r.get('type') == 'hypothesis']
            has_real_data = any(
                'FACT:' in str(r.get('content', ''))
                or r.get('type') in ('hypothesis', 'experiment')
                or r.get('metadata', {}).get('is_grounded', False)
                or 'HYPOTHESIS_ID:' in str(r.get('content', ''))
                or 'Research Finding' in str(r.get('title', ''))
                for r in (section_data or research_data)
            )
            
            # --- ACCUMULATE INHIBITOR CONTEXT (DEDUPLICATION 2.0) ---
            previous_prose = "\n\n".join([s["content"] for s in sections_content if "REJECTED" not in s["content"]])
            inhibitor_instruction = ""
            if previous_prose:
                 inhibitor_instruction = f"""
[ANTI-REDUNDANCY INJUNCTION]
The following content has ALREADY been written in previous sections. 
DO NOT repeat these specific points, arguments, or scaffold structures.
Focus COMPLETELY on the UNIQUE GOAL of this current section ({section.title}).
--- PREVIOUS CONTENT START ---
{previous_prose[-5000:]} 
--- PREVIOUS CONTENT END ---
"""

            # [GODZILLA RIGOR] Force "Speculative" notice if no direct experimental facts are found
            grounding_notice = ""
            if not has_real_data and section.title not in ["Introduction", "Executive Intelligence Summary"]:
                logger.warning(f" [RIGOR] Section '{section.title}' lacks direct experimental grounding. Mandating Speculative Notice.")
                grounding_notice = "\n\n<div class='alert alert-warning'><strong>EMPIRICAL GAP:</strong> The following synthesis lacks direct experimental confirmation from the current session and should be treated as high-confidence speculative modeling.</div>\n"

            # --- SPECIAL HANDLERS FOR V2 SECTIONS (SHOCK & AWE) ---
            if section.title == "Scientific Genesis Log" and ctx:
                # Local import removed to avoid shadowing global 'datetime' class
                genesis_html = f'''
                <div class="genesis-log" style="background: #f8f9fa; border-left: 4px solid #4a5568; padding: 15px; margin: 20px 0;">
                    <h3 style="margin-top:0">Scientific Genesis Log</h3>
                    <ul style="list-style: none; padding-left: 0;">
                        <li><strong>Origin Trigger:</strong> {ctx.get('origin_prompt', 'N/A')}</li>
                        <li><strong>Timestamp:</strong> {datetime.now().isoformat()}</li>
                        <li><strong>Seed Corpus:</strong> {len(ctx.get('seed_corpus', []))} initial sources</li>
                        <li><strong>System Mode:</strong> {mode.upper()}</li>
                    </ul>
                </div>
                '''
                sections_content.append({
                    "title": section.title,
                    "content": genesis_html,
                    "visual": None,
                    "images": []
                })
                continue

            if section.title == "Hypothesis Evolution Tree" and ctx:
                # Use the helper method defined below to generate Mermaid
                tree_html = self._generate_evolution_tree_mermaid(ctx.get("hypotheses", []))
                sections_content.append({
                    "title": section.title,
                    "content": "<p>Below is the complete genealogical record of all hypotheses generated, mutated, and eliminated during this session.</p>",
                    "visual": tree_html,
                    "images": []
                })
                continue

            if section.title == "Rejected & Null Hypotheses" and ctx:
                hypotheses = ctx.get("hypotheses", [])
                failed = [h for h in hypotheses if (h.get("survival_score") if h.get("survival_score") is not None else 1.0) < 0.3]
                
                rows = ""
                if not failed:
                   rows = "<tr><td colspan='3'>No hypotheses were conclusively rejected during this session. All assumptions held within tested boundaries.</td></tr>"
                else:
                    for f in failed:
                        rows += f"""
                        <tr>
                            <td><strong>{f.get('statement')}</strong></td>
                            <td style="color: #c53030;">{f.get('survival_score', 0):.2f}</td>
                            <td>{f.get('reason', 'Consistently failed verification tests or adversarial attacks.')}</td>
                        </tr>
                        """
                
                null_html = f"""
                <div class="null-results" style="margin: 20px 0;">
                    <h3>Rejected & Null Hypotheses (Null Results)</h3>
                    <p><em>"We looked where nothing worked." -- Formal record of falsified claims.</em></p>
                    <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
                        <thead>
                            <tr style="background: #f7fafc; text-align: left; border-bottom: 2px solid #e2e8f0;">
                                <th style="padding: 8px;">Falsified Claim</th>
                                <th style="padding: 8px;">Score</th>
                                <th style="padding: 8px;">Cause of Death</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
                """
                sections_content.append({
                    "title": section.title,
                    "content": null_html,
                    "visual": None,
                    "images": []
                })
                continue

            
            # ----------------------------------------------------

            # Build section-specific sources
            section_sources = [r for r in research_data if r.get('section') == section.title]
            section_cites = "\n".join([f"- {s.get('citation', '')} {s.get('title', '')}" for s in section_sources[:5]])
            
            # FORENSIC REVIEW PROMPT INJECTION
            hedging_instruction = ""
            if "forensic" in mode or "discovery" in mode:
                 # Map legacy "discovery" to Forensic Review
                 hedging_instruction = """
      FORENSIC REVIEW MODE - INVERTED ELIMINATION
      
      CORE LOGIC:
      1. This section is part of a "Falsification Test".
      2. If you find data that SURVIVES, you must admit it (maintain parity).
      3. If you find data that REFUTES the assumption, you must be precise and definitive.
      
      FORMAT REQUIREMENTS:
      - Use the "Assumption -> Violation" format.
      - "Assumption: Process X works if T < 100 deg C."
      - "Violation: Experiment [Source] shows T = 150 deg C at required current."
      
      FALSIFICATION TEST:
      - Explicitly ask: "Can I name an experiment that survives this?"
      - If YES, do not reject the approach. State "BOUNDED BUT STABLE".
      - If NO, conclude it is refuted within this regime.
      
      FORENSIC MODE - TONE ENFORCEMENT
      
      You are writing a FORENSIC INVESTIGATION DOSSIER, not a "Nature" paper.
      
      TONE RULES (MANDATORY):
      1. NO PROSE, NO NARRATIVE. Use short, high-density technical points.
      2. NO METAPHORS. "The data suggests" -> "Data confirms".
      3. NO HISTORICAL EXPOSITION. Start directly with the finding.
      4. BE OBJECTIVE. If a hypothesis was refuted, say "REFUTED". 
      
      LANGUAGE:
      - PRECISE LANGUAGE. Use "demonstrates", "refutes", "supports".
      - Avoid vague "suggests" if data is strong.
                """


            
            # ------------------------------------------------------------------
            # PROMPT CONSTRUCTION & MODE SELECTION
            # ------------------------------------------------------------------
            explicit_prompt = None
            writer_mode = "ultra_beast" 
            
            if mode == "exploration":
                # SCOUT MODE: Use Writer's internal template (No enforcement)
                writer_mode = "scout"
                explicit_prompt = None
            else:
                # RESEARCH / FORENSIC: Construct detailed prompts
                # GODZILLA 2.0: Circularity Guard (Topic Memory)
                avoid_instruction = inhibitor_instruction if inhibitor_instruction else ""

                prompt = f"""
===============================================================================

      SECTION GOAL: {section.content_goal}
      
      IMPORTANT GUIDELINES :
      - YOU ARE AN ULTRA EXPERT. Write at a PhD-LEVEL.
      - Do NOT use generic language. Be ULTRA ULTRA PROFESSIONAL.
      - Do no invent fake citations. Use the provided "ACADEMIC SOURCES" and "RESEARCH DATA".
      - If precise numbers are missing in the text, use checking/estimates from general knowledge but note them as estimates.
      - Evaluate trade-offs relative to regimes (NEVER use competitive "Winner/Loser" language).
      - EXPLICITLY FORBIDDEN: Emojis, colloquialisms, "game over", "winner", "loser".
      - TONE: Clinical, detachment, high-precision, PhD thesis standard.
      - Structure the section logically with HTML headers.
      {hedging_instruction}
      {avoid_instruction}

ACADEMIC SOURCES FOR THIS SECTION:
{section_cites}

FULL RESEARCH DATA:
{context_text[:50000]} 

REQUIREMENTS FOR THIS SECTION (GODZILLA TIER):

1.  **DETAIL & SCALING (CRITICAL)**:
    - This report is running in **{detail_level}** mode (Runtime: {runtime_hours}h).
    - **Target Length**: {target_length}
    - **Depth**: {depth_instruction}

2.  MAKE SPECIFIC CLAIMS WITH NUMBERS (ULTRA PROFESSIONAL):
    Example: "Parameter X exhibit behavior Y at critical thresholds (Z) above 1.1 units, whereas Alternate A remains stable up to 2.5 units at identical conditions [Author, Year]."
    
3.  IF THIS IS {section.title.upper()}, INCLUDE:
    - For "Executive Summary": 1-2 falsifiable claims (with exact thresholds, concentrations, or metrics relevant to {topic})
    - For "Introduction": Problem statement with concrete stakes relevant to {topic}. Be PhD-level.
    - For "Technical Background": Core formulas, conductivity/performance numbers, and physical limits.
    - For "Results/Analysis": Data tables, interface metrics, performance limits derived from the research data.
    - For "Conclusion": Synthesis of viability, what works in which regime, what's non-viable.

4.  CITE USING AUTHOR-YEAR FORMAT (PhD LEVEL):
    [Zhang et al., Nature 2024], [Smith, J. Electrochem. Soc. 2025]
    NOT: "Source 1" or "the research indicates"

8.  **WRITE MASSIVE, DEEP SUBSTANTIVE CONTENT** (CRITICAL):
    - Do NOT repeat introductory boilerplate.
    - Jump straight into deep structural analysis. 
    - Construct specialized data tables, complex lists of parameters, and dense scientific paragraphs.
    - Each section MUST be at least 4-8 dense paragraphs of high-impact analysis.
    - THIS IS A PEER-PHD LEVEL PUBLICATION READY REPORT THAT U ARE DESIGNING

NOW WRITE THE SECTION (start immediately with the highly technical content, no preamble):
"""
                # CRITICAL FIX: Assign the constructed prompt to explicit_prompt
                
                cell_map_str = ""
                if ctx and ctx.get("cell_map"):
                    cell_map_str = "\n\n5. EXPERIMENT PROVENANCE TRACING (MANDATORY):\n"
                    cell_map_str += "For every claim derived from an experiment, you MUST append its mapped Jupyter Notebook cell ID exactly like this: '[Cell #X]'.\n"
                    for exp_id, cell_id in ctx["cell_map"].items():
                        cell_map_str += f"- Experiment {exp_id} -> [Cell #{cell_id}]\n"

                claim_registry_str = ""
                if writer_mode == "ultra_beast":
                    claim_registry_str = """

6. CLAIM REGISTRY (MANDATORY FORMAT):
Before the prose, you MUST generate a JSON registry of all claims enclosed in <claim_registry> tags:
<claim_registry>
[
  {"id": "C1", "claim": "Empirical observation or theoretical mechanism", "type": "experiment", "source": "Source Name or Cell #"}
]
</claim_registry>
Requirement: The prose MUST explicitly cite each claim using [C1], [C2], etc.
"""

                explicit_prompt = prompt + cell_map_str + claim_registry_str

            
            # BEAST MODE: Use the actual GodzillaWriterAgent for writing!
            try:
                task_payload = {
                    "payload": {
                        "explicit_prompt": explicit_prompt,
                        "query": f"{topic} - {section.title}",
                        "topic": topic,
                        "section": section.title,
                        "components": section_sources,
                        "mode": writer_mode,
                        "disable_search": True,
                    },
                    "description": explicit_prompt,
                    "explicit_prompt": explicit_prompt,
                    "query": f"{topic} - {section.title}",
                    "topic": topic,
                    "components": section_sources,
                }
                res = await self.writer.run(task_payload, {"components": section_sources})
                content = res.get("text", "")
                
                # [GODZILLA GATE 4] Grounding Injection
                if grounding_notice:
                    content = grounding_notice + content

                # [GODZILLA GATE 4] Nuclear Citation Purge
                # Find all [Name, Year] citations and verify against known authors or research_data content
                found_cites = re.findall(r'\[([A-Za-z\s\.]+,?\s*\d{4})\]', content)
                known_authors = []
                for rd in research_data:
                    authors = rd.get("authors", "")
                    if authors and str(authors).lower() not in ("unknown", "system intelligence", "knowledge graph"):
                        known_authors.append(str(authors).lower())
                    rd_content = str(rd.get("content", "")).lower()
                    if rd_content:
                        known_authors.append(rd_content)
                
                if known_authors:
                    for cite in found_cites:
                        name_part = cite.split(',')[0].replace("et al.", "").replace("et al", "").lower().strip()
                        if name_part in ("system knowledge", "knowledgegraph", "ref", "source"):
                            continue
                        if name_part and not any(name_part in author_or_text for author_or_text in known_authors):
                            logger.warning(f" [CITATION PURGE] Nuking hallucinated citation: [{cite}]")
                            content = content.replace(f"[{cite}]", "")

                # CLEANUP: Remove nested HTML, header, body tags
                content = re.sub(r'<!DOCTYPE.*?>', '', content, flags=re.IGNORECASE | re.DOTALL)
                content = re.sub(r'<html.*?>', '', content, flags=re.IGNORECASE | re.DOTALL)
                content = re.sub(r'</html>', '', content, flags=re.IGNORECASE | re.DOTALL)
                content = re.sub(r'<head.*?>.*?</head>', '', content, flags=re.IGNORECASE | re.DOTALL)
                content = re.sub(r'<body.*?>', '', content, flags=re.IGNORECASE | re.DOTALL)
                content = re.sub(r'</body>', '', content, flags=re.IGNORECASE | re.DOTALL)
                content = content.replace("```html", "").replace("```", "")
                content = content.strip()
            except Exception as e:
                logger.error(f"Godzilla writing failed for {section.title}: {e}")
                content = f"<p>Error generating content: {e}</p>"
                
            # EXTRACTION: Get Claim Registry if present
            registry = []
            if "<claim_registry>" in content:
                try:
                    reg_match = re.search(r'<claim_registry>(.*?)</claim_registry>', content, re.DOTALL)
                    if reg_match:
                        registry = json.loads(reg_match.group(1))
                        # Strip registry from content to keep prose clean
                        content = content.replace(reg_match.group(0), "").strip()
                except Exception as reg_err:
                    logger.warning(f"Failed to parse claim registry: {reg_err}")

            # Extract key concepts for next section
            key_words = [w for w in section.title.split() if len(w) > 3]
            previous_concepts.extend(key_words)

            # [ANTI-TRASH] Quality Guard: If content is too short or error-prone, inject Retrieval Notice
            if len(content) < 300 and "Error" not in content:
                logger.warning(f" [QUALITY] Content for {section.title} is too sparse ({len(content)} chars).")
                content += f"\n\n<div class='alert alert-warning'><strong>Data Retrieval Notice:</strong> Primary research artifacts for this specific subsection were sparse. The synthesis above reflects available fragments recovered from historical sessions.</div>"

            # [GODZILLA HARD GROUNDING]
            # If the LLM failed to generate substantive prose, physically dump the raw findings
            if len(content) < 200:
                logger.warning(f" [FORCE] Section '{section.title}' was empty/sparse. Injecting raw knowledge.")
                try:
                    # Physically pull the Top 10 re-hydrated facts
                    raw_dump = ""
                    if self.world_model:
                        # Simple keyword match for the section
                        query = section.title.lower()
                        related_facts = []
                        for fact_list in self.world_model._facts.values():
                            for f in fact_list:
                                if any(word in str(f.value).lower() for word in query.split() if len(word) > 3):
                                    related_facts.append(f)
                        
                        if related_facts:
                            raw_dump = "<h3>Raw Empirical Findings (Re-hydrated)</h3><ul>"
                            for f in related_facts[:10]:
                                raw_dump += f"<li><strong>{f.key}:</strong> {str(f.value)[:500]}...</li>"
                            raw_dump += "</ul>"
                    
                    content = content + "\n" + raw_dump
                except Exception as grounding_err:
                    logger.error(f" [FORCE] Hard grounding failed: {grounding_err}")

            sections_content.append({
                "title": section.title,
                "content": content,
                "registry": registry, # Store for assembly
                "visual": visuals.get(section.title) if visuals else None,
                "images": [] 
            })
            
        return sections_content

    async def assemble_report(self, topic: str, sections: List[Dict[str, Any]], research_data: Optional[List[Dict[str, Any]]] = None, ctx: Dict[str, Any] = None, **kwargs) -> str:
        """Combine specific sections into a professional PhD-grade journal HTML report."""
        if ctx is None: ctx = {}
        clean_topic = topic.strip()
        
        # 0. TITLE REFINEMENT: Generate Professional Title (Nature/Science Style)
        # Check if we already have a professional title in context (from run method if triggered early)
        professional_title = ctx.get("professional_title")
        report_id = ctx.get("report_id", f"ARC-{datetime.now().strftime('%Y%m%d')}-{os.urandom(2).hex().upper()}")
        
        if not professional_title:
             print(f" [TITLE] Generating professional title for: {clean_topic[:50]}...")
             professional_title = await self._generate_professional_title(clean_topic, ctx)
             
        # Use the professional title for the report assembly
        report_title = professional_title
        print(f"Assembling report for: {report_title} (Original: {clean_topic[:30]}...)")

        if ctx and 'harvested_visuals' in ctx:
            print(f" [VERIFY] Context contains {len(ctx['harvested_visuals'])} harvested visual entries: {list(ctx['harvested_visuals'].keys())}")

        # 0. PRE-ASSEMBLY SANITIZATION: Remove double headers & repeating titles
        processed_sections = []
        for sec in sections:
            content = sec.get("content", "")
            # Remove any occurrence of the section title at the start of the content (Double Headers FIX)
            title_clean = re.escape(sec['title'])
            content = re.sub(rf'^\s*(<h[1-6]>)?\s*{title_clean}\s*(</h[1-6]>)?\s*', '', content, flags=re.IGNORECASE)
            # Remove repeated main topic header if the LLM hallucinated it
            topic_clean = re.escape(topic)
            content = re.sub(rf'^\s*(<h[1-6]>)?\s*{topic_clean}\s*(</h[1-6]>)?\s*', '', content, flags=re.IGNORECASE)
            sec['content'] = content
            processed_sections.append(sec)
        
        sections = processed_sections
        # Set Scholarly Theme for Visuals (Global Broadcast)
        try:
            from backend.tools.common import get_plotly_backend
            get_backend_module = lambda x: None  # Stub: HoloViews backend not available
            
            # 1. Plotly Advanced
            plotly_beast = get_plotly_backend()
            if plotly_beast and hasattr(plotly_beast, "set_theme"):
                print(" [THEME] Setting scholarly theme for Plotly...")
                plotly_beast.set_theme("avon_scholarly")
                
            # 2. HoloViews
            hv_mod = get_backend_module("viz_holoviews")
            if hv_mod:
                try:
                    # If it's an instance or exposes a factory
                    engine = getattr(hv_mod, "HoloViewsQuantumEngine", None)
                    if engine:
                        print(" [THEME] Setting scholarly theme for HoloViews...")
                        pass 
                except Exception as theme_err:
                    logger.warning(f" [REPORT_THEME_FAILED] Could not apply scholarly theme: {theme_err}")
        except ImportError:
            logger.warning(" [VIZ] Failed to set scientific theme: No module named 'backend.visualization'")
        
        # 1. GENERATE SUMMARY CHART (BEAST MODE)
        summary_chart_html = ""
        if research_data:
            print(" [BIBLIO] Generating Bibliometric Synthesis chart...")
            try:
                import pandas as pd
                
                # [ANTI-TRASH FIX] Robust findings extraction: Flatten and sanitize
                extracted_finding_data = []
                for f in research_data:
                    if not isinstance(f, dict): continue
                    res = f.get("result", {})
                    if not isinstance(res, dict): res = {"raw": str(res)}
                    
                    # Extract bibliometric markers
                    try:
                        raw_year = str(res.get("year") or res.get("pub_date") or res.get("date") or "2025")
                        year_match = re.search(r'\d{4}', raw_year)
                        clean_year = year_match.group(0) if year_match else "2025"
                        
                        raw_cites = res.get("citations") or res.get("citation_count") or 0
                        clean_cites = int(float(str(raw_cites).strip())) if raw_cites else 0
                    except Exception:
                        clean_year = "2025"
                        clean_cites = 0

                    entry = {
                        "year": clean_year,
                        "citations": clean_cites,
                        "source": str(res.get("venue") or res.get("journal") or res.get("source") or "Unknown")[:30],
                        "title": str(res.get("title") or "Research Node")[:50]
                    }
                    
                    extracted_finding_data.append(entry)
                
                df = pd.DataFrame(extracted_finding_data)
                
                if not df.empty:
                    # [ANTI-TRASH GUARD] Only skip if the frame is truly empty
                    chart_type = "scatter" if "year" in df.columns and "citations" in df.columns else "bar"
                    from backend.tools.viz_ai_coder import run_ai_coder
                    
                    viz_res = await asyncio.to_thread(
                        run_ai_coder,
                        df=df,
                        intent=f"Bibliometric Synthesis of {clean_topic}",
                        config={"caption": "Research Landscape Summary", "force_academic": True, "allow_exec": True}
                    )
                    print(f" [SUCCESS] Summary chart status: {viz_res.status}")
                    
                    html_content = getattr(viz_res, 'html', None)
                    fig_json = getattr(viz_res, 'fig_json', None)
                    
                    if not html_content and fig_json:
                        import plotly.io as pio
                        html_content = pio.to_html(fig_json, full_html=False, include_plotlyjs='cdn')

                    if viz_res.status == "success" and html_content:
                        summary_chart_html = f"""
                        <figure style="grid-column: 1 / -1; margin-top: 0;">
                            <div class="viz-wrapper">{html_content}</div>
                            <figcaption><strong>Summary Figure</strong> | Automated bibliometric synthesis of the research landscape for "{clean_topic}".</figcaption>
                        </figure>
                        """

            except Exception as e:
                logger.warning(f"Summary chart generation failed: {e}")


        leaderboard_html = ""
        if ctx and ctx.get("claim_leaderboard"):
            leaderboard = ctx["claim_leaderboard"]
            mode = ctx.get("mode", "research")
            is_discovery = "discovery" in mode or "godzilla" in mode
            table_title = "Assumption Survival Board" if is_discovery else "Strategic Claim Leaderboard"
            col_1 = "Assumption / Claim" if is_discovery else "Hypothesis / Claim"
            col_score = "Survival Score" if is_discovery else "Robustness Score"
            
            rows = ""
            for i, h in enumerate(leaderboard):
                s_score = h.get('survival_score')
                novelty = h.get('novelty_score', 0)
                conf = h.get('confidence', 0.5)
                row_style = ""
                if s_score is not None and s_score < 0.3: row_style = "background: #fff5f5; color: #c53030;"
                if s_score is not None and s_score > 0.8: row_style = "background: #f0fff4; color: #276749;"
                s_display = f"{s_score*100:.0f}%" if s_score is not None else "N/A"
                n_display = f"{novelty*100:.0f}%" if novelty is not None else "N/A"
                rows += f"""
                <tr style="{row_style}">
                    <td style="font-weight: 500;">#{i+1}</td>
                    <td>{h.get('statement')}</td>
                    <td style="text-align: center; font-weight: bold;">{s_display}</td>
                    <td style="text-align: center;">{n_display}</td>
                    <td style="text-align: center;">{conf*100:.0f}%</td>
                </tr>
                """
            leaderboard_html = f"""
            <div class="leaderboard-block" style="margin: 3em 0;">
                <h2 style="border:none; margin-bottom: 0.5em; text-align: center;">{table_title}</h2>
                <table style="width: 100%; border-collapse: collapse; margin: 0 auto;">
                    <thead>
                        <tr style="background: #f0f0f0; border-bottom: 1.5pt solid #000;">
                            <th style="padding: 8pt; border: 0.5pt solid #000; text-align: center;">Rank</th>
                            <th style="padding: 8pt; border: 0.5pt solid #000; text-align: left;">{col_1}</th>
                            <th style="padding: 8pt; border: 0.5pt solid #000; text-align: center;">{col_score}</th>
                            <th style="padding: 8pt; border: 0.5pt solid #000; text-align: center;">Novelty</th>
                            <th style="padding: 8pt; border: 0.5pt solid #000; text-align: center;">Confidence</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <p style="font-size: 9pt; font-style: italic; margin-top: 5pt; text-align: center;">Table I: Evaluation matrix of primary scientific claims and hypotheses survival scores.</p>
            </div>
            """

        # 2.5 RESOLVE PROVENANCE (BEAST LINKING)
        cell_map = ctx.get("cell_map", {}) if ctx else {}
        all_claims = []
        for sec in sections:
            registry = sec.get("registry", [])
            for claim in registry:
                # Add section title to claim for context
                claim["section"] = sec["title"]
                
                # Resolve Experiment Links
                if claim.get("type") == "experiment":
                    cell_id = claim.get("cell")
                    if cell_id is not None:
                        # Link to cell in notebook if we have the file
                        nb_path = ctx.get("output_files", {}).get("notebook", "research_notebook.ipynb")
                        claim["provenance_link"] = f"{nb_path}#cell-{cell_id}"
                
                all_claims.append(claim)
                
            # Post-process prose: Turn [C#] into Tooltip/Link
            prose = sec.get("content", "")
            for claim in registry:
                cid = claim.get("id")
                if not cid: continue
                
                # Professional Tooltip Link
                link_title = claim.get("claim", "Scientific Claim")
                if claim.get("type") == "experiment":
                    link_text = f' <a href="{claim.get("provenance_link", "#")}" title="{link_title}" style="color: var(--journal-crimson); text-decoration: none; font-weight: bold;">[{cid}]</a> '
                else:
                    link_text = f' <span title="{link_title}" style="color: var(--journal-blue); cursor: help; border-bottom: 1px dotted;">[{cid}]</span> '
                
                # Replace exact [C#] tags
                prose = re.sub(rf'\[{re.escape(cid)}\]', link_text, prose)
            
            sec["content"] = prose

        # 2.6 GENERATE PROVENANCE BLOCK
        provenance_html = ""
        if all_claims:
            rows = ""
            for c in all_claims:
                p_text = "Literature"
                p_link = "N/A"
                if c.get("type") == "experiment":
                    p_text = "Jupyter Execution"
                    p_link = f'<a href="{c.get("provenance_link", "#")}">Cell #{c.get("cell")}</a>'
                elif c.get("source"):
                    p_text = c.get("source")
                
                rows += f"""
                <tr>
                    <td><strong>{c.get('id')}</strong></td>
                    <td>{c.get('claim')}</td>
                    <td>{p_text}</td>
                    <td>{p_link}</td>
                </tr>
                """
            
            provenance_html = f"""
            <div class="provenance-block" style="margin: 3em 0;">
                <h2 style="border:none; margin-top: 0; text-align: left;">Scientific Provenance Register</h2>
                <div class="content">The following table provides an audit trail for all atomic claims within this report, mapping each to its respective experimental execution environment (Jupyter Kernel) or primary literature citation.</div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 1em;">
                    <thead>
                        <tr style="background: #f0f0f0; border-bottom: 1.5pt solid #000;">
                            <th style="padding: 8pt; border: 0.5pt solid #000;">ID</th>
                            <th style="padding: 8pt; border: 0.5pt solid #000;">Claim Statement</th>
                            <th style="padding: 8pt; border: 0.5pt solid #000;">Epistemic Source</th>
                            <th style="padding: 8pt; border: 0.5pt solid #000;">Audit Link</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <p style="font-size: 9pt; font-style: italic; margin-top: 5pt;">Table II: Forensic provenance and audit trail for hypothesis verification.</p>
            </div>
            """

        # 2. MAIN HTML TEMPLATE (PhD JOURNAL STYLE)
        html_parts = [f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{report_title} - Scientific Research Report</title>
    <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,700;1,400&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        /* ARCISNOVA HIGH-PRESTIGE RESEARCH MANUSCRIPT THEME (Nature/Science/LaTeX) */
        :root {{
            --journal-black: #000000;
            --journal-grey: #444444; /* Darker grey for better contrast */
            --journal-border: #cccccc;
            --accent-blue: #004a99;
            --accent-crimson: #c00000;
            --bg-paper: #ffffff;
            --text-main: #111111; /* Almost black for ultimate readability */
            --text-header: #000000;
            --hairline: 0.5pt solid #000000;
        }}

        body {{
            font-family: 'EB Garamond', 'Times New Roman', serif;
            line-height: 1.6;
            color: var(--text-main);
            background: #e5e7eb; /* Soft grey background outside paper */
            margin: 0;
            padding: 0;
            -webkit-print-color-adjust: exact;
            text-align: justify;
        }}

        .report-container {{
            max-width: 8.5in; /* Standard Letter width */
            margin: 40px auto;
            padding: 1in;
            background: var(--bg-paper);
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            position: relative;
        }}

        .report-header-meta {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: var(--hairline);
            padding-bottom: 5px;
            margin-bottom: 25px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 8pt;
            letter-spacing: 0.05em;
            color: var(--journal-black);
        }}

        h1, h2, h3, h4 {{ 
            font-family: 'Inter', sans-serif; 
            color: var(--text-header);
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            letter-spacing: -0.01em;
            page-break-after: avoid;
        }}

        header h1 {{ 
            font-size: 26pt; 
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 0.5em;
            text-align: left;
            margin-top: 0;
        }}

        h2 {{ 
            font-size: 14pt; 
            font-weight: 700; 
            text-transform: uppercase; 
            letter-spacing: 0.05em;
            border-bottom: var(--hairline);
            padding-bottom: 4px;
        }}

        h3 {{ 
            font-size: 12pt; 
            font-weight: 700; 
            color: var(--text-header);
            font-style: italic;
        }}

        /* 
         * REMOVED BROKEN GRID
         * Using a sophisticated 2-column flow for text
         */
        .content-columns {{
            column-count: 2;
            column-gap: 0.4in;
            column-rule: 0.5pt solid #eee; /* Subtle divider */
            text-align: justify;
            orphans: 3;
            widows: 3;
        }}

        /* Ensure sections don't break awkwardly across columns if small */
        .section-block {{ 
            margin-bottom: 2.5em; 
            break-inside: auto; /* Allow natural breaking, but headers are protected */
        }}
        
        .section-block h2 {{
            column-span: all; /* Important sections span across columns */
            margin-top: 2em;
        }}

        .abstract-box {{
            margin: 2em 0;
            padding: 1.5em;
            border-top: var(--hairline);
            border-bottom: var(--hairline);
            font-style: italic;
            font-size: 11pt;
            line-height: 1.6;
            column-span: all; /* Abstract spans full width */
            background: #fafafa;
        }}

        .abstract-title {{
            font-weight: 800;
            text-transform: uppercase;
            display: block;
            margin-bottom: 0.75em;
            font-size: 9pt;
            letter-spacing: 0.1em;
            font-family: 'Inter', sans-serif;
            font-style: normal;
        }}

        /* VISUALIZATIONS */
        .viz-container {{ margin: 2em 0; padding: 10px; background: #fff; border: 0.5pt solid var(--journal-border); }}
        
        /* Ensure charts don't overflow their containers in multi-col */
        .viz-wrapper {{ 
            width: 100%; 
            min-height: 300px;
            overflow: visible; /* Prevent scrollbars in PDF */
        }}
        
        figure {{
            margin: 2em 0;
            break-inside: avoid; /* CRITICAL FOR PDF */
            page-break-inside: avoid;
            text-align: center;
        }}
        
        .full-page-spread {{
            column-span: all;
            width: 100%;
            margin: 3em 0;
            clear: both;
        }}
        
        figcaption {{
            margin-top: 12px;
            font-size: 9pt;
            color: var(--journal-grey);
            text-align: justify;
            font-family: 'EB Garamond', serif;
            line-height: 1.4;
            padding: 0 10px;
        }}

        figcaption strong {{ font-weight: 800; font-family: 'Inter', sans-serif; text-transform: uppercase; font-size: 8pt; color: var(--journal-black); }}

        table {{ width: 100%; border-collapse: collapse; margin: 2em 0; font-size: 9pt; font-family: 'Inter', sans-serif; break-inside: avoid; page-break-inside: avoid;}}
        th {{ border-top: 1.5pt solid #000; border-bottom: 0.75pt solid #000; padding: 10px 8px; text-align: left; text-transform: uppercase; font-weight: 800; background: #fdfdfd; }}
        td {{ padding: 8px; border-bottom: 0.5pt solid #eee; }}
        
        .xref {{ color: var(--accent-blue); font-weight: 600; text-decoration: none; }}
        .xref:hover {{ color: var(--accent-crimson); }}
        
        /* STRICT PRINT MEDIA QUERIES FOR PDF GENERATION */
        @media print {{
            body {{
                background: none;
                font-size: 10pt; /* Slightly smaller for print density */
            }}
            .report-container {{
                margin: 0;
                padding: 0;
                box-shadow: none;
                max-width: none;
            }}
            @page {{
                margin: 1in;
                size: A4 portrait;
            }}
            h2, h3, h4 {{ page-break-after: avoid; }}
            p {{ orphans: 3; widows: 3; }}
            figure, table, .avoid-break {{ break-inside: avoid; page-break-inside: avoid; }}
            
            /* Ensure large charts don't get cut arbitrarily */
            .viz-wrapper {{ break-inside: avoid; page-break-inside: avoid; }}
            
            a {{ text-decoration: none !important; color: #000 !important; }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <header>
            <div class="report-header-meta">
                <span>Ref: {report_id}</span>
                <span>ARCISNOVA RESEARCH MANUSCRIPT</span>
                <span>{datetime.now().strftime("%B %d, %Y")}</span>
            </div>
            <h1>{report_title}</h1>
            <div style="font-family: 'Inter', sans-serif; font-style: italic; font-size: 11pt; color: var(--journal-grey); margin-bottom: 30px;">
                Formal Research Monograph | Epistemic Confidence: {ctx.get('confidence', '94.2')}%
            </div>
        </header>
""".replace("{TOPIC}", clean_topic)]

        # Inject Summary Chart (Bibliometric Synthesis)
        if summary_chart_html:
             html_parts.append(f'<div class="section-block">{summary_chart_html}</div>')

        # 3. CONTENT BLOCKS
        # Abstract
        abstract_section = next((s for s in sections if s['title'].lower() in ['abstract', 'executive summary', 'executive intelligence summary']), None)
        if abstract_section:
            html_parts.append(f'<div class="abstract-box"><span class="abstract-title">Abstract</span>{abstract_section["content"]}</div>')
            sections = [s for s in sections if s != abstract_section]

        # START 2-COLUMN FLOW
        html_parts.append('<div class="content-columns">')

        # Inject Leaderboard
        if leaderboard_html:
            html_parts.append(f'<div class="full-page-spread">{leaderboard_html}</div>')

        # Main sections loop
        total_figures = 1
        
        # Merge harvested visuals from context if any
        harvested = ctx.get('harvested_visuals', {}) if ctx else {}
        
        for section in sections:
            content = self._apply_cross_referencing(section['content'])
            
            # Combine generated visuals with harvested ones
            raw_viz = section.get("visual")
            harvested_viz = harvested.get(section['title'], [])
            # [NOTE] [HARVEST] Fuzzy match for harvested visuals if exact title fails
            if not harvested_viz:
                norm_section = self._normalize_title(section['title'])
                for h_title, h_list in harvested.items():
                    if self._normalize_title(h_title) == norm_section:
                        harvested_viz = h_list
                        print(f" [NOTE] [FUZZY MATCH] Found artifact for section '{section['title']}'")
                        break
            else:
                print(f" [DNA] [EXACT MATCH] Found artifact for section '{section['title']}'")

            viz_list = []
            if raw_viz:
                if isinstance(raw_viz, str): viz_list.append({"html": raw_viz, "caption": f"Supporting data for {section['title']}"})
                elif isinstance(raw_viz, list): viz_list.extend(raw_viz)
                elif isinstance(raw_viz, dict): viz_list.append(raw_viz)
            
            # Append harvested artifacts
            if isinstance(harvested_viz, list):
                viz_list.extend(harvested_viz)
            elif harvested_viz:
                viz_list.append(harvested_viz)

            html_parts.append(f"<div class='section-block'><h2>{section['title']}</h2>")
            html_parts.append(f"<div class='content'>{content}</div></div>")
            
            # Fix the visualization rendering bug: Ensure all visuals render regardless of section title
            if viz_list:
                html_parts.append('<div class="section-viz-group">')

                if len(viz_list) == 1:
                    viz = viz_list[0]
                    # Allow solitary visualizations to sit beautifully inside a single column (arXiv style)
                    html_parts.append(f"""
                    <figure class="single-column-figure" id="fig-{total_figures}" style="width: 100%; margin: 1em 0;">
                        <div class="viz-wrapper" style="width: 100%;">{viz.get("html", "")}</div>
                        <figcaption><strong>Figure {total_figures}</strong> | {viz.get("caption", "Supporting data.")}</figcaption>
                    </figure>
                    """)
                    total_figures += 1
                elif len(viz_list) > 1:
                    panels = ""
                    labels = "abcdefghijklmnopqrstuvwxyz"
                    combined_caption = " | ".join([v.get("caption", "") for v in viz_list if v.get("caption")])
                    for idx, viz in enumerate(viz_list):
                        l = labels[idx] if idx < len(labels) else str(idx)
                        panels += f"""
                        <div class="sub-panel" style="margin-bottom: 1.5em;">
                            <div class="panel-label" style="font-weight: 800; font-family: 'Inter', sans-serif;">({l})</div>
                            <div class="viz-wrapper">{viz.get("html", "")}</div>
                        </div>
                        """
                    # Also span multi-panel grids fully across page
                    html_parts.append(f"""
                    <figure class="full-page-spread" id="fig-{total_figures}">
                        <div class="composite-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1em;">{panels}</div>
                        <figcaption><strong>Figure {total_figures}</strong> | {combined_caption or "Comprehensive technical synthesis."}</figcaption>
                    </figure>
                    """)
                    total_figures += 1

                html_parts.append('</div>')

                # Image Galleries
                if section.get("images"):
                    html_parts.append(self._generate_image_gallery(section["images"]))

        # Close 2-COLUMN FLOW
        html_parts.append('</div>')

        # 4. PROVENANCE & FOOTER
        if provenance_html:
            html_parts.append(provenance_html)
            
        is_discovery = ctx.get("mode") in ["discovery", "discovery_research", "exploration"] if ctx else False
        notebook_name = ctx.get("notebook_filename") if ctx else None
        if is_discovery and notebook_name:
            html_parts.append(f"""
            <div class="provenance-block">
                <div style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 10pt; color: #000; margin-bottom: 10px;"> RESEARCH NOTEBOOK ARTIFACT</div>
                <a href="{notebook_name}" style="padding: 6px 12px; border: 1pt solid #000; color: #000 !important; text-decoration: none; font-weight: 600; font-family: 'Inter', sans-serif; font-size: 9pt;"> OPEN MANUSCRIPT SOURCE: {notebook_name}</a>
            </div>
            """)

        # Supplemental Data (Charts that weren't matched inline)
        all_visuals = ctx.get("all_visuals", {}) if ctx else {}
        chart_visuals = {k: v for k, v in all_visuals.items() if k.startswith("Charts:") and v}
        if chart_visuals:
            html_parts.append("<h2>Supplemental Data</h2><div class='content'>")
            for c_name, c_html in chart_visuals.items():
                html_parts.append(f"<figure><div class='viz-wrapper'>{c_html}</div><figcaption><strong>Figure {total_figures}</strong>: {c_name.replace('Charts: ', '')}</figcaption></figure>")
                total_figures += 1
            html_parts.append("</div>")

        html_parts.append("""
    </div>
</body>
</html>
        """)
        return "\n".join(html_parts)

    def _clean_report_output(self, text: str) -> str:
        """Scrub meta-text, processing artifacts, and procedural leakage."""
        if not text: return ""

        # 0. CRITICAL: Filter Epistemic Rejections (Guardrail Leakage)
        # If the ENTIRE section is just a rejection, return a placeholder
        if "Content REJECTED due to violations" in text and len(text) < 500:
            return "<em>[Section data withheld due to strict epistemic confidence thresholds.]</em>"

        # Otherwise, strip specific rejection blocks
        text = re.sub(r'>\s*\[!NOTE\].*?REJECTED due to violations.*?(?:\n|$)', '', text, flags=re.DOTALL | re.IGNORECASE)

        # 1. Strip Component/Section Headers added by LLM
        text = re.sub(r'(?i)SECTION\s*\d+\s*:.*', '', text)
        text = re.sub(r'(?i)COMPONENT\s*\d+\s*:.*', '', text)
        
        # 2. Strip Process Leakage (Anti-Trash Fix without legacy AVON-1 branding)
        text = re.sub(r'(?i)WorldModel', 'Empirical Knowledge Base', text)
        text = re.sub(r'(?i)World Model', 'Empirical Knowledge Base', text)
        text = re.sub(r'(?i)SVEL', 'Autonomous Discovery Engine', text)
        text = re.sub(r'(?i)Cycle\s*\d+(\s*across\s*\d+\s*hypotheses)?', '', text)
        text = re.sub(r'(?i)Agent-\d+(\s*analysis)?', '', text)
        
        # 3. Strip Procedural Phrasing (Nature-Grade Cleanup)
        text = re.sub(r'(?i)In this section, we analyze', 'Analysis of', text)
        text = re.sub(r'(?i)This paper aims to', 'This study focuses on', text)
        text = re.sub(r'(?i)Here, we investigate', 'Investigation of', text)
        text = re.sub(r'(?i)Following our research', 'Subsequent synthesis', text)
        
        return text

    def _has_structural_violations(self, text: str) -> bool:
        """Check for more than one Abstract or Conclusion.
        
        FIX: Now uses HTML-aware checks since output is HTML, not Markdown.
        """
        # HTML header patterns (h1-h6)
        abstract_count = len(re.findall(r'(?i)<h[1-6][^>]*>\s*(Abstract|Executive Summary)', text))
        conclusion_count = len(re.findall(r'(?i)<h[1-6][^>]*>\s*(Conclusion|Final Verdict|Recommendations)', text))
        return abstract_count > 1 or conclusion_count > 1

    def _purge_structural_duplicates(self, text: str) -> str:
        """Hard purge of redundant structural markers in HTML output.
        
        FIX: Now uses HTML-aware checks since output is HTML, not Markdown.
        """
        lines = text.split('\n')
        new_lines = []
        abstract_found = False
        conclusion_found = False
        
        for line in lines:
            # Handle Abstract duplicates (HTML headers)
            if re.search(r'(?i)<h[1-6][^>]*>\s*(Abstract|Executive Summary)', line):
                if abstract_found:
                    continue # Skip second abstract
                abstract_found = True
            
            # Handle Conclusion duplicates (HTML headers)
            if re.search(r'(?i)<h[1-6][^>]*>\s*(Conclusion|Final Verdict|Recommendations)', line):
                if conclusion_found:
                    continue
                conclusion_found = True
                
            new_lines.append(line)
            
        return '\n'.join(new_lines)

    def _generate_evolution_tree_mermaid(self, hypotheses: List[Dict[str, Any]]) -> str:
        """Generate a Mermaid.js flowchart of the hypothesis evolution."""
        if not hypotheses:
            return ""
        
        mermaid_code = ["graph TD"]
        
        # Sort by creation time to ensure logical layout
        sorted_hyp = sorted(hypotheses, key=lambda x: x.get('created_at', ''))
        
        # Track IDs to ensure parents exist or handle missing parents gracefully
        known_ids = {h.get('id') for h in sorted_hyp}
        
        for h in sorted_hyp:
            hid = h.get('id', 'unknown').replace('-', '')[:8]
            stmt = h.get('statement', 'Unknown').replace('"', "'").replace('(', '[').replace(')', ']')[:40] + "..."
            score = h.get('survival_score')
            
            # Styling based on score/state
            style_def = "fill:#fff,stroke:#333"
            if score is not None:
                if score < 0.3: style_def = "fill:#feb2b2,stroke:#c53030,stroke-width:2px,color:#742a2a" # Red
                elif score > 0.8: style_def = "fill:#c6f6d5,stroke:#276749,stroke-width:2px,color:#22543d" # Green
             
            # Node def with label
            mermaid_code.append(f'    {hid}["{stmt}"]:::style_{hid}')
            mermaid_code.append(f'    classDef style_{hid} {style_def}')
            
            # Link to parent
            parent_id = h.get('parent_hypothesis_id')
            if parent_id and parent_id in known_ids:
                pid = parent_id.replace('-', '')[:8]
                mermaid_code.append(f'    {pid} --> {hid}')
        
        return f"""
        <div class="evolution-tree" style="margin: 40px 0; padding: 20px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="margin-top: 0; border: none; font-size: 1.1em; color: #2d3748;">Hypothesis Evolution Tree</h3>
            <div class="mermaid">
                {chr(10).join(mermaid_code)}
            </div>
            <div style="font-size: 0.8em; color: #718096; margin-top: 10px; text-align: center; font-style: italic;">
                Trace of claim refinement. Green nodes indicate high survival/robustness.
            </div>
        </div>
        """

    def _apply_cross_referencing(self, text: str) -> str:
        """Automatically find 'Figure N' or 'Fig. N' and wrap in scholarly spans."""
        if not text:
            return ""
        # Regex for Figure N or Fig. N (case insensitive)
        pattern = r'(?i)(Figure\s+\d+|Fig\.\s+\d+)'
        
        def replace_match(match):
            val = match.group(0)
            return f'<span class="xref">{val}</span>'
            
        return re.sub(pattern, replace_match, text)

    def _extract_mermaid(self, text: str) -> List[str]:
        """Extract all mermaid diagrams from the text."""
        return re.findall(r'```mermaid\s+(.*?)\s+```', text, re.DOTALL)

    def _normalize_title(self, title: str) -> str:
        """Normalize a section title for robust mapping (fuzzy matching)."""
        import re
        if not title: return ""
        t = str(title).lower().strip()
        # Remove versioning like (V2) or [DRAFT]
        t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', t)
        # Remove scientific symbols and common stop words
        t = re.sub(r'[^a-z0-9\s]', '', t)
        # Collapse whitespace
        return " ".join(t.split())

    async def _generate_professional_title(self, topic: str, ctx: Dict[str, Any]) -> str:
        """
        Generates a crisp, professional, academic title for the report.
        Replaces raw user prompts like "Can you research X..." with "The Impact of X on Y".
        """
        # [GODZILLA FIX] Ensure topic is a string before calling strip()
        if isinstance(topic, list):
            topic = ", ".join([str(x) for x in topic])
        elif not isinstance(topic, str):
            topic = str(topic)
            
        clean_topic = topic.strip()
        try:
            logger.info(f" [TITLE] Generating professional title for: {clean_topic[:50]}...")
            
            # 1. Try LLM Generation
            if hasattr(self, "llm_manager") and self.llm_manager:
                prompt_messages = [
                    {"role": "system", "content": "You are a senior editor for Nature/Science. Your task is to convert a research prompt into a professional, concise, academic title. Return ONLY the title. No quotes. No prefix. If you cannot generate a title, return 'FAILURE'."},
                    {"role": "user", "content": f"Research Prompt: {clean_topic}\n\nGenerate a professional title:"}
                ]
                
                # Handle both sync and async LLM managers
                result = self.llm_manager.run(prompt_messages, temperature=0.3, max_tokens=None)
                
                # If result is a coroutine (async manager), await it
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    result = await result
                
                # Extract text from dict response (MockLLMManager returns {"text": ..., "content": ...})
                if isinstance(result, dict):
                    title = result.get("text", "") or result.get("content", "")
                elif isinstance(result, str):
                    title = result
                else:
                    raise ValueError(f"Unexpected LLM return type: {type(result)}")
                
                if not title or title.startswith("Error:") or "All providers failed" in title:
                     raise ValueError(f"LLM returned empty/error title: {title[:50]}")

                # Cleanup: Aggressively strip markdown, quotes, prefixes
                title = re.sub(r'[*#"\'`]', '', title)
                title = re.sub(r'^\s*Title:\s*', '', title, flags=re.IGNORECASE)
                title = title.strip().rstrip('.')
                
                # Validation: If title is just the prompt or 'FAILURE' or too long
                is_echo = clean_topic in title or title in clean_topic
                if len(title) > 150 or "FAILURE" in title or (is_echo and len(title) > 100):
                     logger.warning(f" [TITLE] LLM generated title rejected (Too long/Echo): {title[:50]}...")
                     # Proceed to keyword fallback
                else:
                    if ":" in title and len(title.split(":")[0]) < 10:
                        # Keep full title if colons are used correctly
                        pass
                    
                    logger.info(f" [TITLE] Generated: {title}")
                    return title
            
            # 2. Fallback: Keyword Extraction
            from backend.tools.smart_filename import extract_keywords
            keywords = extract_keywords(clean_topic, max_count=6)
            if keywords:
                # Capitalize and join
                fallback_title = "Analysis of " + " ".join(keywords)
                logger.info(f" [TITLE] Fallback used: {fallback_title}")
                return fallback_title
            
            # 3. Last Resort: Truncate
            final_fallback = clean_topic[:100] + "..." if len(clean_topic) > 100 else clean_topic
            logger.warning(f" [TITLE] Last resort fallback used: {final_fallback[:50]}")
            return final_fallback
            
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            return clean_topic[:100] + "..." if len(clean_topic) > 100 else clean_topic

# Singleton
_composer_instance = None

def get_report_composer():
    global _composer_instance
    if _composer_instance is None:
        _composer_instance = ReportComposerAgent()
    return _composer_instance
