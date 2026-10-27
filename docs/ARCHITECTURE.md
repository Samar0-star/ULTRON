# ULTRON System Architecture: 8-Tier Autonomous AI Scientist

ULTRON is an 82,000-line autonomous AI scientist system built across 219 Python files, engineered to run continuous 12 to 24-hour closed-loop discovery campaigns without human intervention.

Rather than acting as a standard conversational wrapper around Large Language Models, ULTRON encloses neural models inside a multi-tier **deterministic verification cage** where hypotheses are proposed, checked against hard physics and math rules, attacked by adversarial red-team agents, and grounded in a persistent graph memory.

---

## 1. Master System Flowchart

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

## 2. System Architecture Schematic

```
========================================================================================================
                                      ULTRON ARCHITECTURAL SCHEMATIC
========================================================================================================

 [ SCIENTIFIC RESEARCH OBJECTIVE ]
                 │
                 ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 1. ORCHESTRATION & TASK DECOMPOSITION                                                              │
 │  ├── Global Scheduler: Manages API limits with automatic traffic backoff to prevent timeouts       │
 │  ├── Task Decomposer: Splits big research questions into small atomic subtasks                     │
 │  ├── Temperature Scheduler: Starts with high creative exploration, cools to precise execution      │
 │  └── Anti-Rot Context Compactor: Purges terminal noise and error logs, keeping memory sharp       │
 └───────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 2. CAUSAL WORLD MODEL & GNN INTUITION ORACLE                                                       │
 │  ├── SQLite WAL Knowledge Graph: Stores 15,000+ grounded facts, paper citations, and molecules      │
 │  ├── Causal Engine: Tracks cause-and-effect relationships between variables                        │
 │  └── GNN Intuition Oracle: Neural network trained on the graph to link distant, disconnected papers│
 └───────────────────┬────────────────────────────────────────────────────────────▲───────────────────┘
                     │ High-Novelty Candidate Links                               │ Verified Discoveries
                     ▼                                                            │
 ┌────────────────────────────────────────────────────────────────────────┐       │
 │ 3. COGNITIVE DUAL-STREAM SWARM                                         │       │
 │  ├── Literature Scholar Agent: Reads papers from arXiv, PubMed, PDB    │       │
 │  └── Hypothesis Generator: Formulates testable, formal hypotheses      │       │
 └───────────────────┬────────────────────────────────────────────────────┘       │
                     │ Candidate Hypotheses                                       │
                     ▼                                                            │
 ┌────────────────────────────────────────────────────────────────────────┐       │
 │ 4. DETERMINISTIC VERIFICATION CAGE (Pure Python, Zero LLM)             │       │
 │  ├── Stoichiometry & Valence Balance: Kills impossible chemical bonds  │       │
 │  ├── Thermodynamic Stability: Checks if materials decompose into rust  │       │
 │  ├── Space-Group Symmetry: Ensures 3D crystals obey Euclidean geometry │       │
 │  ├── Physical Units Checker: Enforces dimensional consistency          │       │
 │  └── Molecular Structure Filters: Eliminates false-positive assay data │       │
 └─────────┬────────────────────────────────────────────────────┬─────────┘       │
           │ PASS (Valid Physics)                               │ FAIL (Fake Physics)
           ▼                                                    ▼                 │
 ┌──────────────────────────────────────────────────┐   ┌───────────────────────┐ │
 │ 5. ADVERSARIAL RED-TEAM SWARM & THE MORGUE       │   │ THE MORGUE            │ │
 │  ├── Prosecutor Agent: Actively attacks the claim│   │ (Semantic Graveyard)  │ │
 │  ├── Parameter Stress Tests: Finds edge-case bugs│   │ ├── Stored in vector  │ │
 │  ├── Placebo Permutations: Tests vs random data  ├──►│ │   and graph memory  │ │
 │  └── Confounder Checks: Catches fake correlations│   │ └── Stops system from │ │
 └─────────┬────────────────────────────────────────┘   │     repeating failures│ │
           │ SURVIVES (Passed All Attacks)              └───────────────▲───────┘ │
           ▼                                                            │         │
 ┌──────────────────────────────────────────────────────────────────┐   │         │
 │ 6. CLEANROOM EXPERIMENT SANDBOX                                  │   │         │
 │  ├── AST Code Sanitizer: Analyzes code structure before running  │   │         │
 │  ├── Weight Hashing Proof-of-Work: Catches faked training loops  │   │         │
 │  ├── Automated ML & Simulation: Runs real Python experiment code │   │         │
 │  └── Outlier-Resistant Loss: Drops bad data points automatically │   │         │
 └─────────┬────────────────────────────────────────────────────────┘   │         │
           │ Real Experiment Results & Telemetry                        │         │
           ▼                                                            │         │
 ┌──────────────────────────────────────────────────────────────────┐   │         │
 │ 7. EPISTEMIC REGULATION & CONSENSUS TRIBUNAL                     │   │         │
 │  ├── Confidence Tracker: Demands more evidence as certainty rises│   │         │
 │  ├── Contradiction Detector: Catches conflicts with past papers  ├───┘ (Reject)│
 │  ├── 5-Judge Tribunal: Consensus vote by specialized reviewers   │             │
 │  └── 10-Dimensional Scorer: Grades novelty, rigor, and impact    │             │
 └─────────┬────────────────────────────────────────────────────────┘             │
           │ VERIFIED DISCOVERY                                                   │
           ▼                                                                      │
 ┌────────────────────────────────────────────────────────────────────────────────┴───────────────────┐
 │ 8. AUTONOMOUS PROVENANCE & DISCOVERY DOSSIER EXPORT                                                │
 │  ├── Code-to-Claim Traceability: Every conclusion hyperlinks directly to the notebook code cell   │
 │  ├── Full Automated Dossier: Compiles clean Markdown, Jupyter notebook, and PDF reports           │
 │  └── Persistent Commit: Saves new verified facts back into the World Model for the next campaign   │
 └────────────────────────────────────────────────────────────────────────────────────────────────────┘
========================================================================================================
```

---

## 3. How the 8 Subsystems Work (In Plain English)

### 1. Orchestration & Task Decomposition
Takes a large, open-ended scientific problem (e.g., *"Find stabilizing mutations at the viral spike interface"*) and breaks it down into small, atomic subtasks. A global scheduler manages worker agents, automatically backing off traffic if API rate limits hit, and smoothly transitions from creative brainstorming at the start to strict precision during experiment runs.

### 2. Causal World Model & GNN Intuition Oracle
All facts, paper summaries, chemical formulas, and test results are stored in an SQLite graph database. A Graph Neural Network (GNN) continuously learns from this knowledge graph to spot non-obvious connections between papers in completely different fields. This allows ULTRON to propose hypotheses that humans wouldn't think to connect.

### 3. Cognitive Dual-Stream Swarm
Two opposing agent streams work in parallel:
* **The Scholar**: Gathers literature, extracts real experimental data, and writes formal hypotheses.
* **The Prosecutor (Red Team)**: A hostile adversarial agent whose sole job is to prove the Scholar's hypothesis wrong.

### 4. Deterministic Verification Cage
Before any experiment code is generated, the candidate hypothesis must pass through hardcoded Python math and physics checks. If a formula violates charge balance, proposes an unstable crystal structure, or breaks conservation laws, it is killed instantly. Zero tokens and zero compute are wasted on impossible science.

### 5. Adversarial Red-Team Swarm & The Morgue
Hypotheses that pass basic physics are aggressively stress-tested:
* **Perturbation attacks**: Tests whether small changes in parameters break the entire result.
* **Placebo tests**: Shuffles dataset labels 1,000+ times to make sure the result isn't just random luck.
* **The Morgue**: Any idea that fails is permanently logged into a semantic graveyard so the system never wastes time re-testing dead ends in future cycles.

### 6. Cleanroom Experiment Sandbox
When simulation or machine learning code is written:
* **AST Security Check**: Inspects the code syntax tree to prevent system errors or memory leaks before execution.
* **Weight Hashing Proof-of-Work**: Checks the internal weights of ML models before and after training. If the weights didn't change, the model faked the training loop, and the run is rejected.
* **Outlier Filtering**: Drops corrupt data points so noise doesn't ruin the experiment.

### 7. Epistemic Regulation & Consensus Tribunal
Evaluates the final experimental results through a 5-judge panel of simulated peer reviewers (including a Statistician, Physicist, and Domain Skeptic). Contradictions with established literature are flagged immediately, and the hypothesis must win a consensus vote to pass.

### 8. Provenance & Discovery Dossier Export
Once a hypothesis survives the entire gauntlet, ULTRON automatically compiles a complete Epistemic Discovery Dossier. Every claim is linked directly to the exact Jupyter notebook code cell that proved it, accompanied by full execution logs and verifiable data files.
