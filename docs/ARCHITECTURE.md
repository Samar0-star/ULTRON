# ULTRON System Architecture & Mathematical Verification Cage

ULTRON is an autonomous AI scientist system engineered to conduct 12–24 hour closed-loop scientific discovery campaigns without human intervention. 

Unlike standard "AI for science" implementations—which wrap frontier Large Language Models in conversational loops that hallucinate non-existent chemistry, fake math, and irreproducible data—ULTRON encloses neural models inside a **deterministic verification cage**.

```
                     ┌───────────────────────────────────────────────┐
                     │            SCIENTIFIC OBJECTIVE               │
                     └───────────────────────┬───────────────────────┘
                                             │
                                             ▼
                     ┌───────────────────────────────────────────────┐
                     │         HYPOTHESIS GENERATION ENGINE          │
                     │  - Frontier LLM (Hypothesis Proposer)         │
                     │  - Literature Context & GNN Intuition Oracle  │
                     └───────────────────────┬───────────────────────┘
                                             │
                                             ▼
                     ┌───────────────────────────────────────────────┐
                     │        DETERMINISTIC VERIFICATION CAGE        │
                     │  - Stoichiometry & Charge Balance Engines     │
                     │  - Crystal Symmetry & Space Group Checks      │
                     │  - Dimensional Analysis & Boundary Gates      │
                     │  - AST Syntax & Sandbox Sanitization          │
                     └───────┬───────────────────────────────┬───────┘
                             │ PASS                          │ FAIL
                             ▼                               ▼
     ┌───────────────────────────────────────────┐    ┌──────────────────────┐
     │           RED-TEAM FALSIFICATION          │    │      THE MORGUE      │
     │  - Adversarial Challenger Swarm           │    │  - Semantic Kill-    │
     │  - Permutation & Placebo Stress Tests     │    │    Chain Memory      │
     │  - Out-of-Family Generalization           │    │  - Prevents Cyclic   │
     └───────┬───────────────────────────┬───────┘    │    Rediscovery       │
             │ SURVIVES                  │ FALSIFIED  └──────────────────────┘
             ▼                           └───────────────────▲
     ┌───────────────────────────────────────────┐           │
     │        CLEANROOM EXPERIMENT EXECUTION     │           │
     │  - Sandboxed Python / Metal Simulation    │           │
     │  - Inferential Statistics & Power Checks  │           │
     │  - Cohen's d & Welch-Z Significance       │───────────┘
     └───────────────────────┬───────────────────┘
                             │ VERIFIED DISCOVERY
                             ▼
     ┌───────────────────────────────────────────┐
     │            CAUSAL WORLD MODEL             │
     │  - SQLite WAL Grounded Knowledge Graph    │
     │  - GNN Link Prediction Embedding Space    │
     │  - Autonomous Discovery Dossier Export    │
     └───────────────────────────────────────────┘
```

---

## 1. The 4-Tier Swarm Architecture

ULTRON distributes cognitive and verification labor across four specialized agent tiers:

### Tier 1: Executive Orchestrator (`Ultron-Core`)
* Manages the global scientific state machine and campaign timeline.
* Regulates context window allocation and enforces **Anti-Rot Context Compaction** to eliminate hydration drift and memory saturation during 16+ hour campaigns.
* Schedules parallel worker tasks using an isolated concurrency queue.

### Tier 2: Scholar-Prosecutor Dual Stream
* **The Scholar**: Ingests scientific literature (arXiv, PubMed, PDB, Materials Project), extracts empirical facts, and proposes formal mathematical hypotheses.
* **The Prosecutor (Red Team)**: Aggressively designs counter-experiments, searches for confounders, and attempts to mathematically destroy the Scholar's hypothesis.

### Tier 3: CodeEngineer & Simulation Runner
* Synthesizes isolated execution code in Python / C++ for molecular dynamics, biophysical calculations, and crystal graph evaluations.
* All generated code passes through an **Abstract Syntax Tree (AST) Security Sanitizer** before executing inside a locked-down Metal / Apple Silicon sandbox.

### Tier 4: Epistemic Scorer & Dossier Compiler
* Computes rigorous inferential statistics (Permutation tests, Welch-Z scores, Cohen's $d$, 95% BCa bootstrap confidence intervals).
* Generates publication-ready discovery dossiers with full cryptographic provenance.

---

## 2. Deterministic Verification Engines

Before any hypothesis reaches an experiment or simulation, it must pass through hard mathematical gates implemented in pure Python:

1. **Stoichiometric & Valence Balance**: Checks charge neutrality, oxidation states, and coordination numbers.
2. **Thermodynamic Boundary Checker**: Evaluates decomposition energies, convex hulls, and entropy penalties.
3. **Dimensional Consistency Gate**: Validates that physical units cancel cleanly across all proposed equations.
4. **Symmetry & Space-Group Validator**: Ensures proposed crystal structures satisfy 3D Euclidean space group symmetries without atomic clashes.
5. **AST Cleanroom Gate**: Analyzes code syntax before execution to block dangerous syscalls, file system corruption, and memory leaks.

---

## 3. Hardware Footprint & Scalability

ULTRON was specifically engineered to run efficiently on resource-constrained local hardware before scaling to cloud GPU clusters:

* **Baseline Development & Stress Testing**: Apple Silicon M-series Mac mini (16GB Unified Memory).
* **Continuous Campaign Record**: **16.2 hours** uninterrupted autonomous execution on 16GB local memory.
* **Cloud Target**: RunPod / NVIDIA H100 GPU clusters for large-scale multi-day discovery campaigns.
