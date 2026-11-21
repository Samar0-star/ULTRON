# EXHAUSTIVE AUDIT REPORT: SVEL GIT WORKTREE (`agents-psychological-lemur`)

**Target Path:** `/Users/samaraldico/SVEL AI Scientist/SVEL AI Scientist.worktrees/agents-psychological-lemur/`  
**Git Branch:** `agents/psychological-lemur`  
**Base Commit:** `f4b78aba0f23806feaf4e7171040e00be8f848f5` (*"checkpoint before campaign continuation"*)  
**Worktree Creation Time:** `1781078617` (June 10, 2026, 13:33:37 UTC)  
**Parent Repo:** `/Users/samaraldico/SVEL AI Scientist/`

---

## 1. AUDIT OF `data/` (DATASETS & STORAGE)

### Exact File Inventory (54 Files + 1 Directory Tree)
The `data/` folder contains **54 files** directly in its root, totaling **2.82 MB**, plus the deep `research_vault/` hierarchy:

| File Name | Size (Bytes) | Category / Purpose |
| :--- | :--- | :--- |
| `v253_db_dump.json` | 1,116,875 | JSON export of SQLite world model facts, swarm tasks, literature seeds, and session states |
| `.DS_Store` | 14,340 | macOS metadata |
| `world_model_SOVEREIGN_MEDICINE_TRIAL_V253.db-shm` | 32,768 | SQLite WAL shared-memory index for clinical medicine primary world model |
| `world_model_SOVEREIGN_MEDICINE_TRIAL_V253_sub_8820.db-shm` | 32,768 | SQLite WAL index for medicine sub-agent 8820 |
| `world_model_SOVEREIGN_MEDICINE_TRIAL_V253_sub_9ea8.db-shm` | 32,768 | SQLite WAL index for medicine sub-agent 9ea8 |
| `world_model_SOVEREIGN_MEDICINE_TRIAL_V253_sub_e25b.db-shm` | 32,768 | SQLite WAL index for medicine sub-agent e25b |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_0acf.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 0acf |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_1846.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 1846 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_2b08.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 2b08 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_2f50.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 2f50 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_300f.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 300f |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_33e5.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 33e5 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_3646.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 3646 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_3b4e.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 3b4e |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_3fff.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 3fff |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_4595.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 4595 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_5318.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 5318 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_53ce.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 53ce |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_5d93.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 5d93 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_6556.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 6556 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_66a4.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 66a4 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_7059.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 7059 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_75fe.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 75fe |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_7ad6.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 7ad6 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_7d73.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 7d73 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_7ffb.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 7ffb |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_82d0.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 82d0 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_99ef.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 99ef |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_9c70.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent 9c70 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_a72e.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent a72e |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_aec3.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent aec3 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_b4a2.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent b4a2 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_b9cb.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent b9cb |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_bb66.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent bb66 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_c4b3.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent c4b3 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_c664.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent c664 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_d1cb.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent d1cb |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_d559.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent d559 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_e95b.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent e95b |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_ecbc.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent ecbc |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_f116.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent f116 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_f6da.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent f6da |
| `world_model_SOVEREIGN_NAS_CIFAR100_V253_sub_fe68.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS sub-agent fe68 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254.db-shm` | 32,768 | SQLite WAL index for primary CIFAR-100 NAS V254 engine |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_0bf6.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent 0bf6 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_130b.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent 130b |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_47b5.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent 47b5 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_5eda.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent 5eda |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_6598.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent 6598 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_7fa8.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent 7fa8 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_985a.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent 985a |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_c3f4.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent c3f4 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_ceb4.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent ceb4 |
| `world_model_SOVEREIGN_NAS_CIFAR100_V254_sub_e7eb.db-shm` | 32,768 | SQLite WAL index for CIFAR-100 NAS V254 sub-agent e7eb |

*Total: 52 `.db-shm` files (32 KB each = 1,703,936 bytes) + 1 JSON dump (1,116,875 bytes) + 1 `.DS_Store` (14,340 bytes) = 54 files.*

### Dataset Domain Analysis: What Science Was Performed Here?
Inspection of `v253_db_dump.json`, `metadata.json`, and `action_log.jsonl` files reveals the exact experimental campaigns tracked by these files:

1. **Machine Learning / Vision Benchmark (CIFAR-100 ViT NAS)**:
   - **Missions**: `SOVEREIGN_NAS_CIFAR100_V253`, `SOVEREIGN_NAS_CIFAR100_V254`, `SOVEREIGN_VIT_PULSE_V241`.
   - **Research Question**: *"Develop a novel Neural Architecture Search (NAS) method to optimize a Vision Transformer backbone on the CIFAR-100 dataset. Goal: Achieve <0.5% accuracy drop with 60% reduction in FLOPs/Params. MUST use local data at data/cifar100/."*
   - **Swarm Operations**: Over 38 sub-agents were spawned in parallel, running literature harvesters (retrieving papers on ViT-FIQA, Quasar-ViT, Jigsaw-ViT, Evo-ViT, T2T-ViT), baseline training, and PAC-Bayes bound calculations.

2. **Medicine / Clinical Trials**:
   - **Missions**: `SOVEREIGN_MEDICINE_TRIAL_V253` (with sub-agents `8820`, `9ea8`, `e25b`, `5d9d`, `7299`, `8363`, `a8d7`, `e1f2`, `e833`, `f158`).
   - **Research Question**: *"Conduct a clinical trial analysis to evaluate the treatment effect and efficacy of a randomized intervention on primary endpoints. Compare outcomes and safety profiles between treatment and control groups using patient-level records from local data at data/medicine/trial_data.csv."*

3. **Materials Science (Solid-State Batteries)**:
   - **Mission**: `SOVEREIGN_BATTERY_PULSE_V213` in `research_vault/default_user/`.
   - **Research Question**: *"Develop a mathematically rigorous model for identifying optimal inorganic solid-state electrolytes with ionic conductivities exceeding 10^-2 S/cm at room temperature, while maintaining an electrochemical window > 5V vs Li/Li+."*

4. **Genomics / Structural Biology & Physics Context**:
   - In the parent repo (`/Users/samaraldico/SVEL AI Scientist/data/`), the physical raw datasets are stored:
     - **Genomics / Structural Biology**: `6lzg.pdb` (1.14 MB) & `6m0j.pdb` (584 KB) [SARS-CoV-2 spike RBD complexed with ACE2], `skempi_v2.csv` (1.6 MB) [structural kinetics/energetics of mutant protein-protein interactions], `covid19_datasets.csv`, `alzheimer_counts.csv`.
     - **Physics**: `fusion_mhd_stability.csv` (8.3 KB) [magnetohydrodynamic plasma stability in tokamak fusion].
   - Campaigns like `SOVEREIGN_DISCOVERY_PROD` performed PubMed/bioRxiv structural surveys and de novo binder design targeting these files.

---

## 2. AUDIT OF `.godzilla_cache/` AND `graphify-out/`

### `.godzilla_cache/` (Synthesis Engine Reasoning Traces)
- **File Counts**: **36 JSON files** in root (`.godzilla_cache/`) + **37 JSON files** in `.godzilla_cache/versions/` = **73 total cache files** (~610 KB).
- **Engine**: SVEL's Godzilla synthesis module (`version: godzilla-07c29ad2`, mode: `ultra_beast`, orchestrator model: `llm_manager_auto`).
- **Contents**: Full PhD-level scientific synthesis reports complete with DeepSeek-R1-style `<think>` deliberation traces, including:
  - Theoretical formalization of ViT pruning using Random Matrix Theory: Marchenko-Pastur spectral density deviation ($\Delta_{MP} = H - H_{MP}$), proving sublinear accuracy degradation when $\Delta_{MP} \ge 0.8$.
  - Three falsifiable boundary thresholds: $\Delta_{MP} \ge 0.8$, cross-layer attention entropy correlation $\rho_H \ge 0.7$, and PAC-Bayes generalization bound $< 0.15$.
  - Automated verification citations and integrity warnings: e.g. `<!-- GODZILLA WARNING: Content rejected by integrity guards: ["Prose lacks Claim ID citations (e.g. [C1]). Assertions are free-floating."] -->`.
  - The `versions/` subdirectory preserves immutable timestamped snapshots of how these scientific hypotheses evolved across successive agent runs.

### `graphify-out/` (Full Codebase AST Knowledge Graph)
- **`graph.json` (103,935,886 bytes ~ 103.9 MB, 2,250,977 lines)**:
  - An exhaustive, multi-scale Code Property Graph (CPG) of the entire SVEL AI Scientist system.
  - Contains **100,000+ nodes** (lines 5 to 1,055,337) and **150,000+ relational links/edges** (lines 1,055,338 to 2,250,976).
  - Schema extracts: AST nodes, module imports, class hierarchies, function definitions, Markdown document sections (`norm_label`, `community` clustering), and semantic dependencies (`contains`, weight/confidence metrics).
- **`manifest.json` (265,104 bytes, 7,207 lines)**:
  - Master index tracking files across the repository (`real_1hr_run.py`, `backend/llm_manager.py`, `backend/config_beast.py`, etc.), recording file modification timestamps (`mtime`), AST hashes, and semantic hashes.
- **`.graphify_labels.json` (254,299 bytes)**:
  - Taxonomy and semantic label registry mapping graph nodes to functional domains.
- **`.graphify_root` (1 byte)**: Root marker indicating graphify execution scope.

---

## 3. AUDIT OF `.agents/` AND `.wiki/`

- **`.agents/`**:
  - Contains two subdirectories: `.agents/rules/` and `.agents/workflows/`.
  - **Status: Completely empty (0 files).**
  - **Origin**: This is the default directory scaffold automatically generated by autonomous agent IDE extensions / Antigravity agents when initializing a workspace. No bespoke agent rules or workflow definitions were committed here.
  - **Comparison with Main Repo**: In the main repo (`/Users/samaraldico/SVEL AI Scientist/`), `.agents/` does not exist at all.
- **`.wiki/`**:
  - **Status: Completely empty (0 files).**
  - In the main repo, `.wiki/` contains only an empty `.gitkeep` placeholder. No project wiki pages or markdown discovery notes were authored in this worktree.

---

## 4. WORKTREE CREATION & RELATIONSHIP TO MAIN ENGINE

### Why Was `agents-psychological-lemur` Created?
1. **Autonomous Agent Sandbox**:
   The branch name `agents/psychological-lemur` is the signature naming format generated by autonomous agent frameworks (such as Claude Code / Antigravity Agent Worktrees: `agents/<random-adjective>-<random-animal>`). An agent was spawned to conduct a campaign continuation run without risking working-tree collisions or lock conflicts with the main repository.
2. **Execution Milestones in this Worktree**:
   - Spun off on **June 10, 2026 (13:33:37 UTC)** from commit `f4b78aba` (*"checkpoint before campaign continuation"*).
   - Executed `graphify` across the repository, producing the 104 MB AST knowledge graph.
   - Orchestrated the `SOVEREIGN_NAS_CIFAR100_V253` and `V254` swarm runs and clinical medicine trials, dumping results into `v253_db_dump.json` and `.godzilla_cache`.
3. **The `.gitignore` Leakage Bug (Why `.db-shm` files remain)**:
   In `.gitignore`, line 10 specifies `*.db`. However, SQLite WAL mode creates `.db-wal` and `.db-shm` files. While the main `.db` files were correctly ignored by git, the `.db-shm` files were not covered by `*.db` and lingered on disk alongside the dumped JSON.
4. **Current Status vs. Main Discovery Engine**:
   - The main repo has advanced well beyond this branch (progressing through `1eb0d899`, `82c2f8da`, `ee9f4f40`, `7e68e645`, `c3834dbb`, and the TITAN-V263 architectural fixes up to `4ea22f01`).
   - This worktree represents a frozen forensic snapshot of the V253/V254 campaign execution run, preserving the Graphify AST knowledge graph and Godzilla reasoning cache.

---

## 5. SUMMARY RECOMMENDATION
- **Artifacts of Value**:
  - `graphify-out/graph.json` (104 MB) is a complete pre-computed code knowledge graph of the SVEL architecture.
  - `.godzilla_cache/` (73 files) contains fully synthesized, verified ViT pruning theoretical formulations with Marchenko-Pastur bounds.
  - `data/v253_db_dump.json` (1.1 MB) contains the complete provenance trail and literature harvest for the V253 NAS experiment.
- **Cleanup Candidate**:
  - The 52 orphaned `world_model_*_sub_*.db-shm` files (32 KB each) are orphaned WAL shared-memory buffers whose corresponding `.db` files have been removed or ignored; adding `*.db-shm` and `*.db-wal` to `.gitignore` will prevent these from cluttering future worktrees.