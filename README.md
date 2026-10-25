# ULTRON: Autonomous AI Scientist

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/Architecture-Deterministic%20Verification%20Cage-emerald)](docs/ARCHITECTURE.md)
[![Whitepaper](https://img.shields.io/badge/Technical%20Report-PDF-red)](docs/ULTRON_Technical_Report.pdf)
[![Status](https://img.shields.io/badge/Status-Closed%20Research%20Preview-orange)]()

**Closed-loop autonomous scientific discovery engine powered by deterministic verification cages, Red-Team adversarial swarms, and Graph Neural Network world models.**

[Technical Paper (PDF)](docs/ULTRON_Technical_Report.pdf) • [System Architecture](docs/ARCHITECTURE.md) • [Falsification Engine](docs/FALSIFICATION_ENGINE.md) • [Sample Discovery Dossier](dossiers/discovery_dossier_biophysical_1ab21ad3.md)

</div>

---

## 🔬 The Core Problem

Today's "AI for Science" systems are naive Large Language Model wrappers. When prompted to discover new materials, drugs, or physical laws, standard LLMs:
1. **Hallucinate non-existent chemistry & physics**: Generating chemically impossible formulas with broken valence and unbalanced charges.
2. **Suffer confirmation bias**: In search tasks, models hallucinate positive results to satisfy prompts rather than admitting a hypothesis is false.
3. **Double down on self-critique**: Prompt-based "self-reflection" loops fail because models reproduce their own underlying hallucinations.

> **You cannot discover real science with models that hallucinate.**

---

## ⚡ The Solution: The Deterministic Verification Cage

**ULTRON** traps the language model inside an external, non-negotiable mathematical cage:

```
               ┌────────────────────────────────────────────────┐
               │         HYPOTHESIS GENERATION (LLM)            │
               └───────────────────────┬────────────────────────┘
                                       │
                                       ▼
               ┌────────────────────────────────────────────────┐
               │        DETERMINISTIC VERIFICATION CAGE         │
               │  - Stoichiometry & Charge Balance Engines      │
               │  - Crystal Symmetry & Space Group Checks       │
               │  - AST Syntax & Sandbox Security Sanitizer     │
               └───────────────┬────────────────┬───────────────┘
                               │ PASS           │ FAIL
                               ▼                ▼
       ┌───────────────────────────────┐  ┌─────────────────────┐
       │     RED-TEAM FALSIFICATION    │  │     THE MORGUE      │
       │  - Adversarial Attack Swarm   │  │  - Semantic Memory  │
       │  - Placebo / Permutation Gate │  │  - Blocks Cyclical  │
       │  - Confounder Analysis        │  │    Rediscovery      │
       └───────────────┬───────────────┘  └─────────────────────┘
                       │ SURVIVES                   ▲
                       ▼                            │ FALSIFIED
       ┌───────────────────────────────┐            │
       │  SANDBOXED EXPERIMENT RUNNER  │────────────┘
       │  - Cleanroom Python Container │
       │  - Inferential Statistics     │
       │  - Cohen's d & Welch-Z Gates  │
       └───────────────┬───────────────┘
                       │ VERIFIED DISCOVERY
                       ▼
       ┌───────────────────────────────┐
       │      CAUSAL WORLD MODEL       │
       │  - SQLite WAL Knowledge Graph │
       │  - GNN Link Prediction Oracle │
       └───────────────────────────────┘
```

1. **Deterministic Physics Gates**: Every formula is tested by pure-Python mathematical engines. Broken charge balance, invalid stoichiometries, or impossible space groups are killed instantly (0 tokens wasted).
2. **Adversarial Red-Team Swarms**: Hypotheses are attacked by challenger agents incentivized to disprove claims via permutation tests, confounder checks, and sign-crossing attacks.
3. **The Morgue**: Falsified hypotheses are recorded in a semantic graveyard to prevent autonomous agents from repeating known dead ends.
4. **GNN Intuition Oracle**: Verified discoveries are committed to a persistent SQLite WAL Causal Graph. A Graph Neural Network (GCN/GIN) predicts cross-domain links between distant scientific literature.
5. **Cleanroom Sandbox**: Simulation code passes an Abstract Syntax Tree (AST) sanitizer before executing in an isolated local container.

---

## 📊 System Benchmarks

| Metric | Measured Benchmark |
| :--- | :--- |
| **Codebase Scope** | **82,000+ lines of Python** across 219 files |
| **Longest Autonomous Run** | **16.2 continuous hours** on local 16GB Apple Silicon Mac mini |
| **Verification Latency** | **< 15ms** per hypothesis (pure Python deterministic gates) |
| **Epistemic Filter Ratio** | **84.3%** of candidate hypotheses eliminated before experiment execution |
| **Unit Compute Cost** | **\$3.25** per autonomous discovery run vs \$240k+ human wet-lab cycles |

---

## 🧬 Sample Autonomous Discovery (Biophysics Locus)

In an autonomous 2.5-hour discovery mission analyzing the SARS-CoV-2 Spike RBD / Human ACE2 binding interface (PDB `6M0J`) cross-referenced against deep mutational scanning data (Starr et al., 2020), ULTRON autonomously identified stabilizing interface mutations:

* **Top Discovered Candidate**: `CAND-Q498H` (ACE2-RBD Interface Pos 498)
  * $\text{bind\_avg} = +0.30$ | $\text{expr\_avg} = +0.16$
  * Validation: Cleanroom AST permutation test ($p = 4.99 \times 10^{-4}$, Cohen's $d = -0.247$)
* **Full Epistemic Dossier**: See [`dossiers/discovery_dossier_biophysical_1ab21ad3.md`](dossiers/discovery_dossier_biophysical_1ab21ad3.md)

---

## 📁 Repository Structure

```
.
├── README.md                      # Project overview and system architecture
├── LICENSE                        # MIT Open Source License
├── docs/
│   ├── ULTRON_Technical_Report.pdf # 2-Page Technical Whitepaper
│   ├── ARCHITECTURE.md            # Deep architectural specification
│   ├── FALSIFICATION_ENGINE.md    # Popperian falsification & Red-Team design
│   ├── GNN_WORLD_MODEL.md         # Heterogeneous GNN & Causal Graph schema
│   └── DISCOVERY_CAMPAIGNS.md     # Execution lifecycle & hardware envelope
├── dossiers/
│   └── discovery_dossier_biophysical_1ab21ad3.md # Verified discovery dossier
└── telemetry/
    ├── live_biophysical_mission_journal.sample.jsonl # Sample biophysical run log
    └── live_superconduct_mission_journal.sample.jsonl # Sample materials run log
```

---

## 🛡️ Research Preview & Disclosure

* **Core Engine**: ULTRON's closed-loop autonomous orchestrator and execution kernel are currently under private research evaluation.
* **Open Science**: This repository publishes the full system specifications, mathematical validation schemas, discovery dossiers, and execution telemetry to advance transparent, falsifiable AI science.

---

## 👤 Author

**Samar Aldico**  
Independent AI Systems Engineer • Varanasi, India  
GitHub: [@Samar0-star](https://github.com/Samar0-star) • Contact: `aimlsamarr@gmail.com`
