# ULTRON: Autonomous AI Scientist

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/Architecture-9--Tier%20Autonomous%20System-emerald)](docs/ARCHITECTURE.md)
[![Whitepaper](https://img.shields.io/badge/Technical%20Report-PDF-red)](docs/ULTRON_Technical_Report.pdf)
[![Status](https://img.shields.io/badge/Status-Closed%20Research%20Preview-orange)]()

**Closed-loop autonomous synthetic research organism powered by deterministic verification cages, adversarial Red-Team swarms, and Graph Neural Network causal world models.**

[Technical Paper (PDF)](docs/ULTRON_Technical_Report.pdf) • [Master Architecture Specification](docs/ARCHITECTURE.md) • [Falsification Engine](docs/FALSIFICATION_ENGINE.md) • [Sample Discovery Dossier](dossiers/discovery_dossier_biophysical_1ab21ad3.md)

</div>

---

## 🔬 The Core Problem

Current "AI for Science" systems are naive prompt wrappers around Large Language Models. When asked to discover novel materials, design therapeutic molecules, or discover physical mechanisms, standard LLMs fail systematically:

1. **Hallucinatory Science**: Generating chemically impossible molecules with broken oxidation states, charge imbalances, and fake physics.
2. **Pathological Confirmation Bias**: Language models are trained to be agreeable; when tasked with testing an idea, they hallucinate supporting evidence to satisfy the user's prompt.
3. **Circular Self-Reflection**: Asking an LLM to check its own work fails because the model repeats its original underlying errors rather than refuting its own premise.

> **You cannot discover real science with models that hallucinate.**

---

## ⚡ The Solution: The Deterministic Verification Cage

**ULTRON** acts as an autonomous operating system for science, bridging symbolic computation (physics kernels, stoichiometric engines, statistics) and semantic reasoning (LLMs). It encloses neural models inside a multi-tier **deterministic verification cage** where impossible physics is killed instantly by pure Python engines before any experiment runs.

### Master Architecture Flowchart

```mermaid
flowchart TD
    subgraph S1["1. ORCHESTRATION & DECOMPOSITION (deep_research_orchestrator.py & singularity.py)"]
        A1["Scientific Research Objective"] --> A2["DeepResearchOrchestrator\nSession Engine & State Machine"]
        A2 --> A3["SingularityEngine\nFractal Generator & Atomic Task Decomposer"]
        A2 --> A4["CircuitBreaker (CLOSED / OPEN / HALF-OPEN)\nGrounding Grace & Error Backoff"]
        A3 --> A5["Anti-Rot Context Compactor\nPurges Stack Traces & Preserves Physical Canon"]
    end

    subgraph S2["2. DISPATCH & AGENT SWARM (central_router_beast.py & swarm_manager.py)"]
        B1["CentralRouterBeast\nHigh-Throughput Task Multiplexer"]
        B2["Literature & Search Swarm\n(ResearchAgent, DocReaderAgent, WebSearchAgent)"]
        B3["Experiment & Data Swarm\n(ExperimentAgent, DataAnalyzerAgent, MLModelBuilder)"]
        B4["Review & Integrity Swarm\n(FactCheckerAgent, SummarizerAgent, QAAgent)"]
        B1 --> B2 & B3 & B4
    end

    subgraph S3["3. CAUSAL WORLD MODEL & GNN ORACLE (world_model.py & gnn_oracle.py)"]
        C1[("SQLite WAL Knowledge Graph\n15,000+ Grounded Facts, Temporal Validity")]
        C2["Causal BFS Intervention Engine\nCounterfactual Decaying Multipliers"]
        C3["GNN Intuition Oracle (PyTorch Geometric)\nGCN/GIN Link Prediction Topology (sigma)"]
        C1 <--> C2
        C1 --> C3
    end

    subgraph S4["4. FORMAL HYPOTHESIS PIPELINE (backend/core/hypothesis/)"]
        D1["HypothesisGenerator (2-Pass Protocol)"]
        D2["HypothesisState Machine\n(PROPOSED -> NOVEL -> PRIORITIZED -> TESTING)"]
        D3["NoveltyChecker & Prioritizer\nSemantic Deduplication Against Prior Art"]
        D1 --> D2 --> D3
    end

    subgraph S5["5. DETERMINISTIC VERIFICATION CAGE (backend/epistemic/ & physics_kernels.py)"]
        E1{"Deterministic Python Gates\n(Zero-Token Pure Code)"}
        E1_1["Stoichiometry & Valence Balance"]
        E1_2["Thermodynamic Convex Hull & Stability"]
        E1_3["Crystal Space-Group Symmetry (pymatgen)"]
        E1_4["Numerical Physics: Lyapunov & Yoshida ODE"]
        E1_5["Plasma & Condensed Matter: Gamow Integrals"]
        E1_6["Biophysics: RDKit 3D Conformer & PAINS"]
        E1 --- E1_1 & E1_2 & E1_3 & E1_4 & E1_5 & E1_6
    end

    subgraph S6["6. ADVERSARIAL RED-TEAM & THE MORGUE (red_team_agent.py & falsification_engine.py)"]
        F1["RedTeamAgent (Reviewer #2)"]
        F2["Differential Evolution Parameter Attacks"]
        F3["Placebo Permutations (1k-5k Resamples)"]
        F4["Confounder & False Correlation Checks"]
        F5[("THE MORGUE\nSemantic Graveyard (Vector + Graph)\nBlocks Cyclical Rediscovery")]
        F1 --> F2 & F3 & F4
        F2 & F3 & F4 -- "FALSIFIED" --> F5
    end

    subgraph S7["7. CLEANROOM EXPERIMENT SANDBOX (sandbox.py & experiment_agent.py)"]
        G1["AST NameVisitor & Scope Sanitizer\nStatic AST Tree Validation"]
        G2["Igor Code Audit\nEnforces Real Statistical Packages"]
        G3["Cryptographic Weight PoW (UltronRigorMonitor)\nSHA-256 PyTorch Model Weight Divergence"]
        G4["CorrelationChecker & Physical Matrix Validation"]
        G1 --> G2 --> G3 --> G4
    end

    subgraph S8["8. EPISTEMIC REGULATION & CONSENSUS TRIBUNAL (swarm_manager.py & epistemic_regulator.py)"]
        H1["EpistemicRegulator (Log-Odds Tracking)"]
        H2["Statistical Clash Auditor (Welch-Z Test)"]
        H3["ConsensusEngine (5-Judge Multi-Agent Tribunal)"]
        H4["10-Dimensional Discovery Scorer\n(Novelty, Rigor, Reproducibility, Impact)"]
        H1 --> H2 --> H3 --> H4
    end

    subgraph S9["9. AUTONOMOUS PROVENANCE & DOSSIER EXPORT (report_composer.py & jupyter_exporter.py)"]
        I1["1-to-1 Claim-to-Cell Jupyter Hyperlinks"]
        I2["Headless Chromium Playwright PDF Paint Verification"]
        I3["Formal Epistemic Discovery Dossier (Markdown & PDF)"]
        I1 --> I2 --> I3
    end

    %% Dataflow Wiring
    A5 --> B1
    C3 -- "Suggested Novelty Edges" --> D1
    D3 --> E1
    E1 -- "PASS: Valid Physics" --> F1
    E1 -- "FAIL: Impossible Physics" --> F5
    F2 & F3 & F4 -- "SURVIVES: Unbreakability Index" --> G1
    G4 --> H1
    H4 -- "VERIFIED DISCOVERY" --> I1
    H4 -- "Rejected by Tribunal" --> F5
    I3 --> C1
```

---

## 🏛️ System Architecture Breakdown

ULTRON operates across 9 tightly coordinated layers:

1. **Orchestration & Recursive Decomposition (`deep_research_orchestrator.py`, `singularity.py`)**:
   Manages 12h to 72h autonomous discovery campaigns. The `SingularityEngine` infinitely breaks down complex scientific inquiries into atomic subtask Directed Acyclic Graphs (DAGs). The `CircuitBreaker` handles API rate limits with exponential backoff while granting "Grounding Grace" to honest null results so campaigns don't crash when ideas fail.
2. **Central Task Routing & Worker Swarm (`central_router_beast.py`, `swarm_manager.py`)**:
   Coordinates 12 specialized agent personas (Literature Researchers, PDF Parsers, Protocol Designers, Data Analyzers, Fact Checkers, and Red Team Adversaries) with isolated worker queues and automatic hung-task recovery.
3. **The Graph of Truth: Causal World Model & GNN Oracle (`world_model.py`, `gnn_oracle.py`)**:
   Maintains an SQLite Write-Ahead Logging (WAL) knowledge graph with 15,000+ grounded facts and causal relationships. A Graph Neural Network (GNN) scans the global graph to discover non-obvious connections linking distant papers across different scientific domains.
4. **Formal Hypothesis Pipeline (`backend/core/hypothesis/`)**:
   Translates raw text concepts into formal mathematical hypotheses tracked by a strict finite-state machine (`PROPOSED` -> `NOVEL` -> `PRIORITIZED` -> `TESTING` -> `CONFIRMED` / `REFUTED` -> `ARCHIVED`) with semantic vector deduplication against prior art.
5. **Deterministic Verification Cage (`backend/epistemic/`, `physics_kernels.py`)**:
   Pure-Python rule engines test every candidate formula for charge balance, stoichiometric neutrality, thermodynamic stability ($\Delta E_{\text{hull}}$), and 3D Euclidean crystal symmetry (`pymatgen`) before running any experiment. Fake physics is killed instantly with zero tokens wasted.
6. **Adversarial Red-Team Swarm & The Morgue (`red_team_agent.py`, `falsification_engine.py`)**:
   A hostile "Reviewer #2" agent attacks surviving hypotheses using Differential Evolution parameter stress tests and 1,000–5,000 resample placebo permutations. Failed ideas are permanently archived in "The Morgue" to prevent swarms from cyclically repeating past dead ends.
7. **Cleanroom Experiment Sandbox (`sandbox.py`, `experiment_agent.py`)**:
   Inspects Python Abstract Syntax Trees (AST) before execution to prevent errors or unsafe system calls. Checks ML model weights using SHA-256 cryptographic proof-of-work before and after training to guarantee the model didn't fake the simulation.
8. **Epistemic Regulation & Consensus Tribunal (`epistemic_regulator.py`, `swarm_manager.py`)**:
   Evaluates experimental outcomes through a 5-judge consensus tribunal (including a Physicist, Statistician, and Domain Skeptic) and flags statistical contradictions against past literature.
9. **Autonomous Provenance & Dossier Export (`report_composer.py`, `jupyter_exporter.py`)**:
   Compiles complete discovery dossiers where every single assertion hyperlinks directly to the executable Jupyter cell that generated the evidence, automatically saving verified breakthroughs back into the World Model for the next campaign.

---

## 📊 Measured System Benchmarks

| Metric | Measured Value |
| :--- | :--- |
| **Codebase Scale** | **82,016 lines of Python** across 219 files |
| **Longest Autonomous Campaign** | **16.2 continuous hours** on local Apple Silicon 16GB Mac mini |
| **Deterministic Gate Latency** | **< 15ms** per hypothesis (pure Python execution) |
| **Epistemic Filter Ratio** | **84.3%** of proposed hypotheses killed before experiment execution |
| **Unit Compute Cost** | **\$3.25** per autonomous discovery run vs \$240k+ human wet-lab cycles |

---

## 🧬 Sample Autonomous Discovery (Biophysics Locus)

In a 2.5-hour autonomous run analyzing the SARS-CoV-2 Spike RBD / Human ACE2 binding interface (PDB `6M0J`), ULTRON cross-referenced structural data with 4,200+ experimental mutational measurements and autonomously identified high-affinity stabilizing mutations:

* **Top Discovered Candidate**: `CAND-Q498H` (ACE2-RBD Interface Pos 498)
  * $\text{bind\_avg} = +0.30$ | $\text{expr\_avg} = +0.16$
  * Falsification Result: Survived 5-stage adversarial perturbation and cleanroom permutation tests ($p = 4.99 \times 10^{-4}$).
* **Full Epistemic Dossier**: See [`dossiers/discovery_dossier_biophysical_1ab21ad3.md`](dossiers/discovery_dossier_biophysical_1ab21ad3.md)
* **Sample Run Telemetry**: See [`telemetry/live_biophysical_mission_journal.sample.jsonl`](telemetry/live_biophysical_mission_journal.sample.jsonl)

---

## 📁 Repository Structure

```
.
├── README.md                                    # Master project architecture & overview
├── LICENSE                                      # MIT Open Source License
├── docs/
│   ├── ULTRON_Technical_Report.pdf              # 2-Page Technical Whitepaper
│   ├── ARCHITECTURE.md                          # Full 9-tier architectural specification & schematic
│   ├── FALSIFICATION_ENGINE.md                  # Adversarial Red-Team & Popperian falsification
│   ├── GNN_WORLD_MODEL.md                       # Graph Neural Network link prediction & World Model
│   └── DISCOVERY_CAMPAIGNS.md                   # Autonomous execution lifecycle & hardware benchmarks
├── dossiers/
│   └── discovery_dossier_biophysical_1ab21ad3.md# Real verified discovery dossier (17KB)
└── telemetry/
    ├── live_biophysical_mission_journal.sample.jsonl # Sample biophysical run log
    └── live_superconduct_mission_journal.sample.jsonl# Sample materials run log
```

---

## 🛡️ Research Preview & Disclosure

* **Core Engine**: ULTRON's closed-loop autonomous orchestrator and execution kernel are currently under private research evaluation.
* **Open Science**: This repository publishes the complete system architecture, verification schemas, discovery dossiers, and run telemetry for transparent scientific evaluation.

---

## 👤 Author

**Samar Aldico**  
Independent AI Systems Engineer • Varanasi, India  
GitHub: [@Samar0-star](https://github.com/Samar0-star) • Contact: `aimlsamarr@gmail.com`
