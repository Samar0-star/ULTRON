# ULTRON: Autonomous AI Scientist

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/Architecture-8--Tier%20Deterministic%20Verification%20Cage-emerald)](docs/ARCHITECTURE.md)
[![Whitepaper](https://img.shields.io/badge/Technical%20Report-PDF-red)](docs/ULTRON_Technical_Report.pdf)
[![Status](https://img.shields.io/badge/Status-Closed%20Research%20Preview-orange)]()

**Closed-loop autonomous scientific research organism powered by deterministic verification cages, adversarial Red-Team swarms, and Graph Neural Network world models.**

[Technical Paper (PDF)](docs/ULTRON_Technical_Report.pdf) • [System Architecture](docs/ARCHITECTURE.md) • [Falsification Engine](docs/FALSIFICATION_ENGINE.md) • [Sample Discovery Dossier](dossiers/discovery_dossier_biophysical_1ab21ad3.md)

</div>

---

## 🔬 The Core Problem

Current "AI for Science" tools are mostly simple prompt wrappers around Large Language Models. When asked to discover new materials, design molecules, or test physical laws, standard LLMs fail consistently:

1. **Hallucinating Science**: Generating impossible chemistry, broken oxidation states, and fake formulas.
2. **Confirmation Bias**: Telling you what you want to hear instead of admitting an idea doesn't work.
3. **Circular Self-Reflection**: Asking an LLM to check its own work fails because it repeats its original mistakes.

> **You cannot discover real science with models that hallucinate.**

---

## ⚡ The Solution: The Deterministic Verification Cage

**ULTRON** traps the language model inside an external, non-negotiable **verification cage**:

### Master Architecture Flowchart

```mermaid
flowchart TD
    subgraph S1["1. ORCHESTRATION & TASK DECOMPOSITION"]
        A1["Scientific Research Objective"] --> A2["Global Scheduler (Dynamic Traffic Backoff)"]
        A2 --> A3["Task Decomposer (Atomic Subtasks)"]
        A3 --> A4["Temperature Scheduler (Exploration to Precision)"]
        A4 --> A5["Anti-Rot Context Compactor"]
    end

    subgraph S2["2. CAUSAL WORLD MODEL & GNN ORACLE"]
        B1[("SQLite WAL Knowledge Graph\n(15,000+ Grounded Facts & Entities)")]
        B2["Causal Graph Engine\n(Downstream Effect Simulator)"]
        B3["GNN Intuition Oracle (PyTorch Geometric)\n(Link Prediction Over Distant Papers)"]
        B1 <--> B2
        B1 --> B3
    end

    subgraph S3["3. COGNITIVE DUAL-STREAM SWARM"]
        C1["Literature Scholar Agent\n(arXiv, PubMed, PDB, Materials Project)"]
        C2["Hypothesis Generator\n(Formal Testable Hypotheses)"]
        C1 --> C2
    end

    subgraph S4["4. DETERMINISTIC VERIFICATION CAGE (Pure Python)"]
        D1{"Deterministic Physical Gates"}
        D1_1["Stoichiometry & Charge Balance Checks"]
        D1_2["Thermodynamic Stability & Decomposition Checks"]
        D1_3["Crystal Space-Group Symmetry Checks"]
        D1_4["Physical Dimensional & Unit Consistency"]
        D1_5["Molecular 3D Conformer & PAINS Filters"]
        D1 --- D1_1 & D1_2 & D1_3 & D1_4 & D1_5
    end

    subgraph S5["5. ADVERSARIAL RED-TEAM SWARM & THE MORGUE"]
        E1["Prosecutor Agent (Hostile Challenger)"]
        E2["Parameter Perturbation Attacks"]
        E3["Statistical Placebo & Permutation Tests"]
        E4["Confounder & False Correlation Checks"]
        E5[("THE MORGUE\nSemantic Graveyard of Dead Hypotheses\n(Prevents Repeating Failures)")]
        E1 --> E2 & E3 & E4
        E2 & E3 & E4 -- "FALSIFIED" --> E5
    end

    subgraph S6["6. CLEANROOM EXPERIMENT SANDBOX"]
        F1["AST Code Syntax & Security Sanitizer"]
        F2["Weight Hashing Proof-of-Work (Detects Fake Training)"]
        F3["Automated ML & Simulation Runner"]
        F4["Outlier-Resistant Loss Filter"]
        F1 --> F2 --> F3 --> F4
    end

    subgraph S7["7. EPISTEMIC REGULATOR & TRIBUNAL"]
        G1["Epistemic Regulator (Confidence Tracking)"]
        G2["Literature Contradiction Detector"]
        G3["Multi-Agent Consensus Tribunal (Skeptic, Physicist, Stats)"]
        G4["10-Dimensional Discovery Evaluation"]
        G1 --> G2 --> G3 --> G4
    end

    subgraph S8["8. AUTONOMOUS PROVENANCE & DOSSIER EXPORT"]
        H1["1-to-1 Code Cell Hyperlink Trace"]
        H2["Verified Discovery Dossier (Markdown & PDF)"]
        H1 --> H2
    end

    %% Dataflow Connections
    A5 --> C1
    B3 -- "Suggested Novel Links" --> C2
    C2 --> D1
    D1 -- "PASS: Valid Physics" --> E1
    D1 -- "FAIL: Impossible Physics" --> E5
    E2 & E3 & E4 -- "SURVIVES: Strong Hypothesis" --> F1
    F4 --> G1
    G4 -- "Verified Discovery" --> H1
    G4 -- "Rejected by Tribunal" --> E5
    H2 --> B1
```

---

## 🏛️ How the 8 Subsystems Work

1. **Orchestration & Task Decomposition**: Breaks complex scientific goals down into atomic tasks and manages agent traffic so long multi-hour runs don't hit API rate limits or choke on memory.
2. **Causal World Model & GNN Intuition Oracle**: Saves every verified fact into an SQLite graph database. A Graph Neural Network (GNN) trains on this graph to spot novel links connecting distant papers across different fields.
3. **Cognitive Dual-Stream Swarm**: A Scholar agent reads literature to formulate hypotheses, while an opposing Prosecutor agent aggressively tries to poke holes in every idea.
4. **Deterministic Verification Cage**: Pure-Python rule engines check every formula for charge balance, physical stability, and symmetry before any experiment runs. Fake physics is killed instantly with zero tokens wasted.
5. **Adversarial Red-Team Swarm & The Morgue**: Tests surviving hypotheses with label-shuffling placebo tests and parameter stress tests. Failed ideas are permanently archived in "The Morgue" so the system never repeats past mistakes.
6. **Cleanroom Experiment Sandbox**: Analyzes code syntax before execution to prevent errors, and hashes ML model weights before and after training to guarantee the model didn't fake the simulation.
7. **Epistemic Regulation & Consensus Tribunal**: Reviews experiment outputs using a 5-judge tribunal of simulated peer reviewers (including a Physicist, Statistician, and Domain Skeptic).
8. **Autonomous Provenance & Dossier Export**: Assembles a complete discovery dossier where every claim hyperlinks directly to the notebook code cell that proved it.

---

## 📊 Measured System Benchmarks

| Metric | Measured Value |
| :--- | :--- |
| **Codebase Scale** | **82,016 lines of Python** across 219 files |
| **Longest Autonomous Run** | **16.2 continuous hours** on local Apple Silicon 16GB Mac mini |
| **Deterministic Gate Latency** | **< 15ms** per hypothesis (pure Python execution) |
| **Epistemic Filter Ratio** | **84.3%** of proposed hypotheses killed before experiment execution |
| **Unit Compute Cost** | **\$3.25** per autonomous discovery run vs \$240k+ human wet-lab cycles |

---

## 🧬 Sample Autonomous Discovery (Biophysics Locus)

In a 2.5-hour autonomous run analyzing the SARS-CoV-2 Spike RBD / Human ACE2 binding interface (PDB `6M0J`), ULTRON cross-referenced structural data with 4,200+ experimental mutational measurements and autonomously identified high-affinity stabilizing mutations:

* **Top Discovered Candidate**: `CAND-Q498H` (ACE2-RBD Interface Pos 498)
  * $\text{bind\_avg} = +0.30$ | $\text{expr\_avg} = +0.16$
  * Validation: Survived 5-stage adversarial perturbation and cleanroom permutation tests ($p = 4.99 \times 10^{-4}$).
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
│   ├── ARCHITECTURE.md                          # Full 8-tier architectural specification
│   ├── FALSIFICATION_ENGINE.md                  # Adversarial Red-Team & Popperian falsification
│   ├── GNN_WORLD_MODEL.md                       # Graph Neural Network link prediction & World Model
│   └── DISCOVERY_CAMPAIGNS.md                   # Execution lifecycle & hardware benchmarks
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
