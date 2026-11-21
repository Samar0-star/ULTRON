# Exhaustive Audit: SVEL Surgical Skill & Mutation Engine

**Audit Scope:**
- `backend/core/skill_injector.py` (687 lines, ~36 KB)
- `backend/core/skill_mutator.py` (522 lines, ~18 KB)
- `backend/core/llm_skill_selector.py` (292 lines, ~9.5 KB)
- `backend/skills/` (51 active domain skill directories)

---

## 1. Executive Architectural Summary
SVEL’s skill system is structured as a **Sovereign Surgical Knowledge Injection Architecture (Godzilla/Titan V3)** designed to eliminate prompt bloat while providing Ph.D.-level technical grounding:
1. **Deterministic Bundles**: 18 hardwired agent roles to discrete skill clusters (e.g. `meta_cognitive`, `red_team`, `data_analyst`, `experiment_designer`).
2. **Keyword Overrides**: Regex word-boundary triggers for instantaneous domain skills matching (`genomics`, `stats`, `docking`, `ml`, `physics`).
3. **Hierarchical Descent**: Two-turn selection: Turn 1 routes catalog (1-line summaries); Turn 2 descends into specific technical sub-files (max 3 files across `references/`, `scripts/`, `assets/`, `configs/`).
4. **Dynamic Mutation**: Autonomous capability gap synthesis into a quarantined, AST-validated sandbox.
5. **Anti-Contamination Gating**: 53 domain-exclusive packages preventing cross-disciplinary pollution.

---

## 2. Domain Exclusion Mapping (Anti-Contamination Gate)
- **53 Exclusive Packages**:
  - Physics (6): `tokamak-pedestal-physics`, `mhd-modeling`, `grad-shafranov-solvers`, `fluidsim`, `astropy`, `simpy`
  - Biology (16): `biopython`, `pydeseq2`, `pysam`, `scanpy`, `anndata`, `scvi-tools`, `cobrapy`, `reactome-database`, etc.
  - Chemistry (14): `rdkit`, `datamol`, `deepchem`, `chembl-database`, `diffdock`, `torchdrug`, etc.
  - Structural Biology (5): `alphafold-database`, `pdb-database`, `uniprot-database`, `esm`, `pymatgen`
  - Clinical (9): `clinicaltrials-database`, `fda-database`, `gwas-database`, `opentargets-database`, etc.
  - Neuroscience (4): `pydicom`, `nibabel`, `pathml`, `histolab`
  - Lab Automation (5): `pylabrobot`, `opentrons-integration`, `benchling-integration`, etc.
- **ML Shield**: For ML/CS campaigns, 100% of these 53 packages are strictly forbidden from entering prompt contexts.
- **Symmetric Exclusions**: Physics blocks Biology/Chemistry/Clinical; Biology blocks Physics/Chemistry/Clinical; etc.
- Gated at 3 bottlenecks: `get_tool_catalog()`, `search_skills()`, and `agentic_inject()`.

---

## 3. Dynamic Skill Mutation Engine (`skill_mutator.py`)
- Synthesizes new skills dynamically when capability gaps are discovered.
- Enforces strict class contract: `{SkillName}Skill` with `analyze()` and `run_skill()`.
- **5-Stage Quarantine**:
  1. AST Security Scanner (bans `os`, `subprocess`, `sys`, `eval`, `exec`, `open`, `__builtins__`, `__dict__`, etc.).
  2. Bytecode compilation (`py_compile.compile(..., doraise=True)`).
  3. Size gate ($100\text{ B} \le \text{Size} \le 50\text{ KB}$).
  4. Quarantine isolation in `skills/mission_skills/_quarantine/{skill_name}.py` with SHA-256 hash.
  5. Promotion: `approve_skill` moves from `_quarantine/` to `active/`.

---

## 4. Prompt-Drowning Defense & Context Hygiene
1. Catalog compression: 1 line per skill in Turn 1.
2. Top-K cap: `max_skills` defaults to 3.
3. Universal sub-asset cap: Maximum 3 sub-files total across all skills.
4. Truncation ceilings: Sub-files capped at 2,000 to 4,000 characters.
5. Example restraint: Sliced to 1 code example per skill.
6. Density-weighted precision search filtering out stop words and short terms.

---

## 5. Critical Flaws Uncovered
1. **NameError in `skill_mutator.py:497`**: `get_skill_mutator()` checks `if mission_id not in _mutator_instances:`, but `mission_id` is not defined in the function scope!
2. **AttributeError in `llm_skill_selector.py:64-66`**: Accesses `self.expert_system.functional_skills` which does not exist on `SvelExpertSystem`.
3. **Missing Method in `task_decomposer.py:228`**: Calls `expert.list_skills()`, which is undefined, always triggering fallback.
