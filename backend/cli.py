#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTRON AI SCIENTIST — PURE HEADLESS COMPUTE ENGINE & TERMINAL UI
================================================================
The primary command-line interface for autonomous scientific research.
Features:
- Vibrant, multi-pane real-time terminal dashboard (Rich Cyberpunk Theme)
- Live Thinking & Cognitive Reasoner display
- Swarm Fleet Monitoring with agent numbering (Agent #01, #02...)
- Epistemic Regulator Conscience Panel with Welch-Z tests & Logit slopes
- Dynamic hardware adaptation for Apple Silicon Mac mini 16GB RAM
- Dual-mode: Full-screen interactive dashboard or streaming stdout
- Graceful interrupt handling with emergency checkpointing
"""

import os
import sys
import asyncio
import argparse
import uuid
import logging
import signal
from typing import Optional, Dict, Any

# Ensure project root is in PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.orchestration.deep_research_orchestrator import DeepResearchOrchestrator
from backend.central_router_beast import get_router
from backend.llm_manager import LLMManager
from backend.core.events.event_bus import events
from backend.ui.terminal_dashboard import (
    UltronDashboardState,
    UltronTerminalDashboard,
    DashboardLogHandler
)

logger = logging.getLogger("ultron_cli")


def setup_cli_logging(dashboard: UltronTerminalDashboard, log_file: Optional[str] = None):
    """Configures logging to route through the dashboard while optionally saving to file."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Attach Dashboard Handler
    dash_handler = DashboardLogHandler(dashboard)
    dash_handler.setLevel(logging.INFO)
    root_logger.addHandler(dash_handler)

    # File logger if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        ))
        root_logger.addHandler(file_handler)


async def run_mission(
    prompt: str,
    domain: str,
    runtime_hours: float,
    mode: str,
    workers: int,
    cycles: int,
    resume_id: Optional[str] = None,
    stream_mode: bool = False,
    log_file: Optional[str] = None,
    dry_run: bool = False
):
    """Executes a single, isolated research mission with the live terminal dashboard."""
    mission_id = resume_id or str(uuid.uuid4())
    
    # Initialize Dashboard State & UI
    state = UltronDashboardState(
        mission_id=mission_id,
        prompt=prompt,
        domain=domain,
        mode=mode,
        runtime_hours=runtime_hours,
        max_parallel=workers
    )
    state.max_cycles = cycles
    dashboard = UltronTerminalDashboard(state, force_stream=stream_mode)

    # Setup Logging Bridge
    setup_cli_logging(dashboard, log_file)
    dashboard.start()

    # Graceful Shutdown Handler
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_sigint():
        dashboard.set_thinking("Interrupt received (SIGINT). Initiating emergency checkpoint...", "GRACEFUL_SHUTDOWN")
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, handle_sigint)
    except (NotImplementedError, RuntimeError):
        pass  # Windows or non-main thread fallback

    dashboard.set_thinking("Initializing Core Discovery Engines & SQLite WAL manifolds...", "BOOTING")

    try:
        # Dry-run check
        if dry_run:
            dashboard.state.current_cycle = 1
            dashboard.state.max_cycles = cycles or 25
            dashboard.set_thinking("Booting sovereign cognitive runtime & verifying SQLite manifolds...", "INITIALIZING", "OrchestratorKernel")
            await asyncio.sleep(0.6)
            
            # Phase 1: Bootstrapping & Knowledge Seed
            dashboard.set_active_stage(1, "KNOWLEDGE_SEED", "LiteratureHarvester")
            dashboard.set_thinking("LiteratureHarvester starting: Connecting to local research vault at data/...", "KNOWLEDGE_SEED", "LiteratureHarvester")
            await asyncio.sleep(0.5)
            dashboard.set_thinking("LiteratureHarvester harvesting: Ingesting skempi_v2.csv (1,420 Kd measurements) & 6lzg.pdb (SARS-CoV-2 RBD/ACE2)...", "KNOWLEDGE_SEED", "LiteratureHarvester")
            dashboard.state.facts_harvested = 42
            await asyncio.sleep(0.5)
            dashboard.set_thinking("DiscoveryPolicy arming: Validating thermodynamic reality constraints & derivation gates (PASS)...", "KNOWLEDGE_SEED", "DiscoveryPolicy")
            await asyncio.sleep(0.6)
            
            # Phase 2: Meta-Reasoning & Strategic Plan Creation
            dashboard.set_active_stage(2, "STRATEGIC_PLANNING", "PlanCreator")
            dashboard.set_thinking("MetaReasoner brainstorming: Reflecting on exploration temperature (T=0.82) & mission horizon (8.0h)...", "STRATEGIC_PLANNING", "MetaReasoner")
            await asyncio.sleep(0.6)
            dashboard.set_thinking("PlanCreator decomposing: Formulating 4 strategic workstream tasks with PlanReviewer feasibility check...", "STRATEGIC_PLANNING", "PlanCreator")
            dashboard.record_plan_task(
                task_id="TASK-01",
                title="Extract binding affinity measurements from skempi_v2.csv",
                assigned_agent="LiteratureHarvester",
                dependencies="None",
                status="COMPLETED",
                feasibility="APPROVED"
            )
            dashboard.record_plan_task(
                task_id="TASK-02",
                title="Derive electrostatic free energy surface Hamiltonian",
                assigned_agent="PlanCreator",
                dependencies="TASK-01",
                status="IN_PROGRESS",
                feasibility="APPROVED"
            )
            dashboard.record_plan_task(
                task_id="TASK-03",
                title="Compile PyTorch AST sandbox verification & compute stats",
                assigned_agent="ExperimentAgent",
                dependencies="TASK-02",
                status="QUEUED",
                feasibility="APPROVED"
            )
            dashboard.record_plan_task(
                task_id="TASK-04",
                title="Train GCN link prediction encoder on knowledge topology",
                assigned_agent="GNNOracle",
                dependencies="TASK-03",
                status="QUEUED",
                feasibility="APPROVED"
            )
            await asyncio.sleep(0.6)
            dashboard.set_thinking("PlanReviewer finalizing: All 4 workstreams approved for Apple Silicon Mac mini 16GB execution...", "STRATEGIC_PLANNING", "PlanReviewer")
            await asyncio.sleep(0.6)
            
            # Phase 3: Hypothesis Generation & SymPy Formalization
            dashboard.set_active_stage(3, "HYPOTHESIS_FORMATION", "HypothesisGenerator")
            dashboard.set_thinking("HypothesisGenerator brainstorming: Formulating biophysical electrostatic mechanism for Spike N501Y binding...", "HYPOTHESIS_FORMATION", "HypothesisGenerator")
            await asyncio.sleep(0.6)
            dashboard.set_thinking("HypothesisGenerator formalizing: Deriving SymPy Hamiltonian: dG = dH - T*dS + q1*q2/(4*pi*eps*r)...", "HYPOTHESIS_FORMATION", "HypothesisGenerator")
            dashboard.record_hypothesis(
                "H-DEMO-01",
                "Point mutations in binding domain alter electrostatic surface potential",
                confidence=0.78,
                status="IN_TESTING",
                equation="dG = dH - T*dS + q1*q2/(4*pi*eps*r)"
            )
            await asyncio.sleep(0.6)
            dashboard.set_thinking("EpistemicRegulator validating: Zero-token dimensional consistency check: Real Domain PASS", "HYPOTHESIS_FORMATION", "EpistemicRegulator")
            dashboard.record_epistemic_event(
                "SYMPY_CHECK_PASS",
                "H-DEMO-01",
                "Validated dimensional bounds: Real Domain PASS",
                welch_z=0.34
            )
            await asyncio.sleep(0.7)
            
            # Phase 4: Swarm Fleet Work & Physical Cleanroom Execution
            dashboard.set_active_stage(4, "SWARM_EXPERIMENTATION", "ExperimentAgent")
            dashboard.set_thinking("SwarmManager dispatching: Deploying Swarm Agents #01 and #02 for sandbox experimentation...", "SWARM_EXPERIMENTATION", "SwarmManager")
            a1 = dashboard.register_agent_spawn("Agent-001", "task_01", "Extracting binding affinity measurements from skempi_v2.csv")
            a2 = dashboard.register_agent_spawn("Agent-002", "task_02", "Compiling PyTorch tensor training in AST cleanroom sandbox")
            await asyncio.sleep(0.8)
            
            dashboard.update_agent_status("Agent-001", "COMPLETED", "Extracted 1,420 Kd measurements")
            dashboard.set_thinking("PoWRigorMonitor verifying: Calculating cryptographic tensor weight divergent hash (SHA-256)...", "SWARM_EXPERIMENTATION", "PoWRigorMonitor")
            await asyncio.sleep(0.6)
            dashboard.record_experiment(
                exp_id="EXP-992",
                hyp_id="H-DEMO-01",
                dataset="skempi_v2.csv",
                shape="(1420, 8)",
                ast_check="PASS",
                initial_hash="e3b0c44298fc",
                final_hash="8f434346648f",
                p_val=0.0034,
                cohens_d=0.82,
                ci="[0.40, 1.20]",
                status="STATS_COMPUTED"
            )
            dashboard.update_agent_status("Agent-002", "COMPLETED", "Cryptographic weight hash diverged (PASS)")
            await asyncio.sleep(0.8)

            # Phase 5: GNN Oracle Dream Phase & Multi-Agent Consensus Tribunal
            dashboard.set_active_stage(5, "GNN_TRIBUNAL_AUDIT", "GNNOracle")
            dashboard.set_thinking("GNNOracle training: Fitting GCN topology encoder across active graph (15,200 nodes, 48,300 edges)...", "GNN_TRIBUNAL_AUDIT", "GNNOracle")
            dashboard.update_gnn_oracle(
                nodes=15200,
                edges=48300,
                auc=0.915,
                predictions=["Link 892 -> 443 (causal electrostatic intervention)"]
            )
            await asyncio.sleep(0.7)

            dashboard.set_thinking("ConsensusTribunal auditing: 3-judge panel evaluating hypothesis against adversarial noise perturbation...", "GNN_TRIBUNAL_AUDIT", "ConsensusTribunal")
            dashboard.update_tribunal(
                hyp_id="H-DEMO-01",
                stat_vote="APPROVED",
                phys_vote="APPROVED",
                skeptic_vote="APPROVED",
                noise_survival=0.94,
                verdict="APPROVED"
            )
            dashboard.state.survivor_tier = "STRUCTURAL"
            dashboard.state.distinct_attack_axes = ["PARAMETER", "REGIME", "BOUNDARY"]
            await asyncio.sleep(0.8)

            # Phase 6: Epistemic Regulation & Cycle Synthesis
            dashboard.set_active_stage(6, "EPISTEMIC_SYNTHESIS", "EpistemicRegulator")
            dashboard.set_thinking("EpistemicRegulator synthesizing: Computing Welch-Z divergence test against prior empirical distribution (Z=2.75)...", "EPISTEMIC_SYNTHESIS", "EpistemicRegulator")
            dashboard.record_hypothesis(
                "H-DEMO-01",
                "Point mutations in binding domain alter electrostatic surface potential",
                confidence=0.91,
                status="FALSIFICATION_SURVIVED",
                welch_z=2.75,
                equation="dG = dH - T*dS + q1*q2/(4*pi*eps*r)"
            )
            dashboard.record_epistemic_event(
                "LOGIT_UPDATE",
                "H-DEMO-01",
                "Confidence slope positive; Falsification survived.",
                welch_z=2.75
            )
            await asyncio.sleep(0.6)

            dashboard.set_thinking("WorldModel committing: Cycle 1 complete. Synthesizing empirical findings into WorldModel SQLite WAL...", "EPISTEMIC_SYNTHESIS", "WorldModel")
            dashboard.state.pow_verifications += 1
            dashboard.state.experiments_executed += 1
            dashboard.state.causal_edges = 48300
            await asyncio.sleep(0.5)
            
            from backend.tools.jupyter_exporter import get_jupyter_exporter
            from backend.core.epistemic_dossier import generate_discovery_dossier

            nb_demo_path = f"reports/notebooks/{mission_id}_master.ipynb"
            demo_hyps = [{
                "id": "H-DEMO-01",
                "statement": "Point mutations in binding domain alter electrostatic surface potential",
                "equation": "dG = dH - T*dS + q1*q2/(4*pi*eps*r)",
                "confidence": 0.91,
                "status": "FALSIFICATION_SURVIVED",
                "welch_z": 2.75,
                "survivor_tier": "STRUCTURAL"
            }]
            demo_exps = [{
                "id": "EXP-DEMO-01",
                "hypothesis_id": "H-DEMO-01",
                "hypothesis": "Point mutations in binding domain alter electrostatic surface potential",
                "dataset": "skempi_v2.csv",
                "initial_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "final_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
                "p_val": 0.0034,
                "cohens_d": 0.82,
                "ci": "[0.40, 1.20]",
                "evidence_type": "FALSIFICATION_SURVIVED"
            }]

            exporter = get_jupyter_exporter()
            exporter.export_claim_mapped_notebook(
                title=prompt,
                claims=demo_hyps,
                experiments=demo_exps,
                output_path=nb_demo_path,
                metadata={
                    "session_id": mission_id,
                    "domain": domain,
                    "baseline_llm": "GPT-6 Astra",
                    "survivor_tier": "STRUCTURAL"
                },
                survivor_tier="STRUCTURAL"
            )

            dossier_res = generate_discovery_dossier(
                mission_id=mission_id,
                research_question=prompt,
                domain=domain,
                hypotheses=demo_hyps,
                experiments=demo_exps,
                survivor_tier="STRUCTURAL",
                baseline_llm="GPT-6 Astra",
                runtime_hours=0.25,
                notebook_path=nb_demo_path
            )

            dashboard.print_final_summary({
                "status": "dry_run_success",
                "dossier_path": dossier_res["markdown_path"],
                "notebook_path": nb_demo_path
            })
            return

        # Initialize Core Components
        router_inst = get_router()
        llm_manager = LLMManager()

        # Connect Event Bus to Dashboard
        async def on_bus_event(event):
            etype = getattr(event, "type", "")
            payload = getattr(event, "payload", {})
            if etype == "RESEARCH_CYCLE_STARTED":
                state.current_cycle = payload.get("cycle", state.current_cycle)
                state.max_cycles = payload.get("total_cycles", state.max_cycles)
                dashboard.set_thinking(f"Entering Research Cycle {state.current_cycle}/{state.max_cycles}...", "CYCLE_START")
            elif etype == "SWARM_TASK_COMPLETED":
                dashboard.update_agent_status(payload.get("worker_id", ""), "COMPLETED")
            elif etype == "FINDING_DISCOVERED":
                state.facts_harvested += 1
                dashboard.set_thinking(f"New empirical finding verified: {str(payload.get('finding', ''))[:50]}...", "DISCOVERY")

            elif etype == "SWARM_TASK_STARTED":
                wid = payload.get("worker_id", "")
                if wid not in dashboard.state.agents:
                    dashboard.register_agent_spawn(wid, payload.get("task_id", ""), payload.get("description", f"Task {payload.get('task_id', '')}"))

        for ev in ["RESEARCH_CYCLE_STARTED", "SWARM_TASK_STARTED", "SWARM_TASK_COMPLETED", "FINDING_DISCOVERED", "OVERMIND_DIRECTIVE_ISSUED"]:
            try:
                await events.subscribe(ev, on_bus_event)
            except Exception:
                pass

        # Instantiate Orchestrator with UI callbacks
        orchestrator = DeepResearchOrchestrator(
            research_question=prompt,
            domain=domain,
            mode=mode,
            runtime_hours=runtime_hours,
            router=router_inst,
            llm_manager=llm_manager,
            session_id=mission_id,
            on_progress=dashboard.on_progress,
            max_parallel=workers,
            max_cycles=cycles
        )

        # Execute deep research mission
        dashboard.set_thinking("Deep Research Orchestrator armed. Commencing knowledge harvest...", "ACTIVE_RESEARCH")
        
        # Run orchestrator task concurrently with stop_event
        run_task = asyncio.create_task(orchestrator.run_async(resume=bool(resume_id)))
        
        while not run_task.done():
            if stop_event.is_set():
                dashboard.set_thinking("Cancelling active swarm tasks and checkpointing session...", "TERMINATING")
                run_task.cancel()
                try:
                    await run_task
                except asyncio.CancelledError:
                    pass
                break
            await asyncio.sleep(0.25)
            dashboard.refresh()

        if run_task.done() and not run_task.cancelled():
            result = run_task.result()
            state.is_completed = True
            state.completion_result = result
            res_dict = result if isinstance(result, dict) else {}
            if hasattr(orchestrator, "session") and hasattr(orchestrator.session, "artifacts"):
                for art in orchestrator.session.artifacts:
                    if art.get("type") == "epistemic_discovery_dossier":
                        res_dict["dossier_path"] = art.get("markdown_path")
                    elif art.get("type") == "jupyter_notebook_master":
                        res_dict["notebook_path"] = art.get("path")
            dashboard.print_final_summary(res_dict)
        else:
            dashboard.stop()
            print("\n[!] Mission paused cleanly. State saved in PersistenceVault.")

    except Exception as e:
        dashboard.stop()
        logger.error(f"[CRITICAL_FAIL] Mission failed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)
    finally:
        dashboard.stop()


def main():
    parser = argparse.ArgumentParser(
        description="ULTRON AI Scientist (2026 Engine) — Autonomous Headless Discovery Compute Node",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 8-Hour Autonomous Campaign on Biophysics
  python3 backend/cli.py "Investigate thermodynamic determinants of spike-receptor mutations" --domain biology --runtime 8.0 --workers 6

  # Run Discovery Falsification Mode on CIFAR-100 Vision Models
  python3 backend/cli.py "Design structured attention pruning schedules for ViTs" --domain ml --runtime 6.0 --mode discovery

  # Run in Background Streaming Mode (Tail -f ready)
  nohup python3 backend/cli.py "Examine plasma stability thresholds" --domain physics --stream > run.log 2>&1 &

  # Test UI & Pipeline without Token Burn
  python3 backend/cli.py "Test Hypothesis Pipeline" --dry-run
        """
    )
    parser.add_argument("prompt", type=str, nargs="?", default="", help="The core scientific research question or hypothesis.")
    parser.add_argument("--domain", type=str, default="general", help="Scientific domain (e.g. biology, ml, physics, chemistry, general).")
    parser.add_argument("--runtime", type=float, default=8.0, help="Maximum campaign runtime in hours (default: 8.0).")
    parser.add_argument("--mode", type=str, choices=["research", "discovery"], default="discovery", help="Execution mode: discovery (with adversarial red team) or research.")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent swarm workers (default: 6, tuned for Mac mini 16GB RAM).")
    parser.add_argument("--cycles", type=int, default=25, help="Hard research cycle ceiling (default: 25).")
    parser.add_argument("--resume", type=str, default=None, help="Resume an existing mission session ID from PersistenceVault.")
    parser.add_argument("--stream", action="store_true", help="Force plain-text colorized streaming mode (recommended for pipes, logs, and nohup).")
    parser.add_argument("--log-file", type=str, default=None, help="Optional path to mirror full execution logs.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate discovery loop, agent spawning, and UI verification without API tokens.")

    args = parser.parse_args()

    # Validate Prompt
    if not args.prompt and not args.resume and not args.dry_run:
        parser.print_help()
        print("\n[ERROR] A research question prompt or --resume session_id is required.")
        sys.exit(1)

    effective_prompt = args.prompt or "Autonomous scientific discovery mission"

    # Execute async mission
    asyncio.run(run_mission(
        prompt=effective_prompt,
        domain=args.domain,
        runtime_hours=args.runtime,
        mode=args.mode,
        workers=args.workers,
        cycles=args.cycles,
        resume_id=args.resume,
        stream_mode=args.stream,
        log_file=args.log_file,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
