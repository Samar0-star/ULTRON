# Autonomous Discovery Campaigns & Execution Telemetry

ULTRON is engineered for continuous 12 to 24-hour autonomous scientific campaigns.

---

## 1. Execution Lifecycle

A typical autonomous discovery campaign follows this progression:

```
Step 1: Domain Ingestion
└── Read benchmark dataset / literature corpus (e.g., Starr 2020 DMS, Materials Project, Superconductivity data)
└── Extract grounded empirical facts into SQLite WAL Knowledge Graph

Step 2: GNN Link Prediction & Hypothesis Formulation
└── Identify topological voids and high-confidence candidate links
└── Propose formal mathematical functional forms

Step 3: Deterministic Gate Verification
└── 12 pure-Python physics engines check charge, valence, symmetry, units
└── Eliminate mathematically invalid candidates instantly (0 tokens wasted)

Step 4: Red-Team Adversarial Assault
└── 5 orthogonal falsification attacks (sign-crossing, confounders, placebo permutations)
└── Falsified hypotheses are archived into The Morgue

Step 5: Sandboxed Cleanroom Execution
└── Generate self-contained Python / C++ simulation code
└── Execute inside sandboxed Metal / Apple Silicon container
└── Compute Welch-Z, Cohen's d, and 95% BCa confidence intervals

Step 6: Dossier Compilation & Provenance
└── Generate structured Epistemic Discovery Dossier with full audit trail
```

---

## 2. Real Telemetry Data

Sample event from autonomous biophysical discovery campaign (`telemetry/live_biophysical_mission_journal.sample.jsonl`):

```json
{
  "timestamp": "2026-10-13T22:17:46.444243",
  "elapsed_sec": 7045.1,
  "event_type": "PROGRESS_PLAN_CREATED",
  "data": {
    "phase": "plan_created",
    "plan": {
      "id": "fe5f2d44",
      "cycle": 2,
      "tasks": [
        {
          "id": "task_2_1",
          "description": "DMS EXTRACTION OR DEATH: Load starr_rbd_dms_2020.csv with explicit schema validation... Mutually exclusive outcomes: (A) KILL hypothesis f993056d if double-mutant data unobtainable; (B) SURVIVE if at least one single mutant shows Kd <= 50 nM.",
          "required_tools": ["code_executor", "table_extractor", "doc_reader"],
          "priority": 10
        }
      ]
    }
  }
}
```

---

## 3. Verified Discovery Dossiers

Sample discovery candidates identified autonomously and validated against empirical ground truth (`dossiers/discovery_dossier_biophysical_1ab21ad3.md`):

| Candidate ID | Target Locus | Discovered Mutation | Predicted Effect | Validation Basis |
| :--- | :--- | :--- | :--- | :--- |
| `CAND-Q498H` | ACE2-RBD Interface (498) | `Q498H` | `bind_avg=+0.30, expr_avg=+0.16` | Starr DMS + 6M0J PDB |
| `CAND-Q498Y` | ACE2-RBD Interface (498) | `Q498Y` | `bind_avg=+0.16, expr_avg=+0.06` | Starr DMS + 6M0J PDB |
| `CAND-411K`  | ACE2-RBD Interface (411) | `411K`  | `log2_enrich=+0.86, expr=+1.64`  | AST Cleanroom Permutation |
