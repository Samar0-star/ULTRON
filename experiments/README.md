# SVEL Empirical Research & Autonomous Discovery Experiments

This directory contains the primary empirical research artifacts, executable Jupyter discovery notebooks, and Popperian falsification ledgers generated autonomously by the **Scientific Verification Engine Layer (SVEL)**.

Unlike typical LLM code generations or synthetic benchmarks, every notebook in this repository was executed in an isolated cleanroom sandbox against verified empirical physical datasets (including RCSB crystallographic structures, SKEMPI 2.0 binding affinity mutations, Starr 2020 deep mutational scanning, and the UCI Superconductivity database). Each experiment couples formal hypothesis framing with inferential statistics, non-parametric permutation tests, cryptographic proof-of-work (PoW) verification, and epistemic falsification criteria.

---

## Quick Navigation Index

| Notebook | Domain | Primary Inputs | Core Methodology | Falsification Verdict |
| :--- | :--- | :--- | :--- | :---: |
| [Investigate_thermodynamic_and_electrostatic_determ_master.ipynb](Investigate_thermodynamic_and_electrostatic_determ_master.ipynb) | Biophysical Virology | SKEMPI v2.0, `2ajf.pdb`, `6m0j.pdb`, `6lzg.pdb` | Dual-crystallography, Debye-Hückel, Mann-Whitney U, sensitivity audit | **SURVIVED** (Outputs captured) |
| [Biophysical_Autonomous_Discovery_Interface_20261014.ipynb](Biophysical_Autonomous_Discovery_Interface_20261014.ipynb) | Structural Biology & DMS | Starr 2020 DMS ($N=4,221$), PDB `6M0J` | Epistatic coupling $\varepsilon_{ij}$, 3D contact topology, Plotly visualizer | **SURVIVED** (Multi-panel) |
| [Thermodynamic_Electrostatic_Determinants_Coronavirus_2026101.ipynb](Thermodynamic_Electrostatic_Determinants_Coronavirus_2026101.ipynb) | Biophysical Chemistry | SKEMPI v2.0, PDB `2AJF`, PDB `6LZG` | Electrostatic/vdW energy decomposition, permutation test ($p=0.0001$) | **SURVIVED** |
| [Thermodynamic_Determinants_Affinity_Binding_20261011.ipynb](Thermodynamic_Determinants_Affinity_Binding_20261011.ipynb) | Mutation Energetics | SKEMPI v2.0 (N501Y / Tyr41), PDB `2AJF` | Double-mutant thermodynamic cycle ($\Delta\Delta G$ coupling), GNN link prediction | **SURVIVED** |
| [Thermodynamic_Determinants_Affinity_Binding_20261012.ipynb](Thermodynamic_Determinants_Affinity_Binding_20261012.ipynb) | Structural Virology | SKEMPI v2.0 (N501Y), PDB `2AJF` | Aromatic-contact energy formulation ($\Delta\Delta G = \varepsilon_\pi n_\pi + \Delta\Delta G_{\text{steric}}$) | **SURVIVED** |
| [Autonomous_Scientific_Discovery_Mission_20261012.ipynb](Autonomous_Scientific_Discovery_Mission_20261012.ipynb) | Condensed Matter Physics | UCI Superconductivity ($21,263$ materials) | 22 formal claims, valence electron density scaling, Debye frequency | **SURVIVED** |
| [Forcefield_Templates_Pdbfixer_Residues_20261012.ipynb](Forcefield_Templates_Pdbfixer_Residues_20261012.ipynb) | Computational Chemistry | PDB structures (`6M0J`, `2AJF`, `6LZG`) | PDBFixer Amber14 forcefield template assignment, heavy-atom repair | **VALIDATED** |
| [Crystallographic_Experimental_Resolution_Metadata_20261012.ipynb](Crystallographic_Experimental_Resolution_Metadata_20261012.ipynb) | Structural Metrology | RCSB PDB metadata repository | Diffraction resolution, $R_{\text{free}}$, $R_{\text{work}}$, space group filtering | **VALIDATED** |
| [Neural_Architecture_Literature_Correction_20261012.ipynb](Neural_Architecture_Literature_Correction_20261012.ipynb) | Epistemic Auditing | ArXiv abstracts, CIFAR-100 zero-shot proxies | Negative result identification, zero-cost proxy bias correction | **FALSIFIED NULL** |
| [Sanitized_Header_Fields_Legacy_20261012.ipynb](Sanitized_Header_Fields_Legacy_20261012.ipynb) | Data Provenance | RCSB CIF headers (`6M0J.cif`) | Cross-schema reconciliation between legacy PDB and modern CIF | **VALIDATED** |
| [19ddb356-c70b-4bc5-8fa3-90a7725d2864_master.ipynb](19ddb356-c70b-4bc5-8fa3-90a7725d2864_master.ipynb) | Viral Biophysics | SKEMPI v2.0, PDB `2AJF` | Surface electrostatic potential shifts, SciPy hypothesis tests | **SURVIVED** |
| [32018fbf-a185-4919-9347-5eb469db1e1e_master.ipynb](32018fbf-a185-4919-9347-5eb469db1e1e_master.ipynb) | Mutation Energetics | SKEMPI v2.0, PDB `6M0J` | N501Y binding affinity shifts, non-parametric Wilcoxon rank-sum | **SURVIVED** |
| [53b006cd-2b27-4816-ab0c-7c29b1a08237_master.ipynb](53b006cd-2b27-4816-ab0c-7c29b1a08237_master.ipynb) | Materials Informatics | UCI Superconductivity dataset | Non-linear atomic/electronic determinants of $T_c$ scaling | **SURVIVED** |
| [7a368ae6-512a-43fe-8742-6e4b9ba004f1_master.ipynb](7a368ae6-512a-43fe-8742-6e4b9ba004f1_master.ipynb) | Viral Biophysics | SKEMPI v2.0, PDB `2AJF` | Binding kinetics characterization of viral spike RBD mutations | **SURVIVED** |
| [927b6299-b58f-4d04-a741-532fa90fb959_master.ipynb](927b6299-b58f-4d04-a741-532fa90fb959_master.ipynb) | Structural Virology | SKEMPI v2.0, PDB `6LZG` | N501Y affinity kinetics, AST cleanroom verification | **SURVIVED** |
| [f5a1fdf7-de07-4b1e-a3c0-838d99e9c8c9_master.ipynb](f5a1fdf7-de07-4b1e-a3c0-838d99e9c8c9_master.ipynb) | Protein Engineering | Starr 2020 DMS, SKEMPI v2.0 | Epistatic trade-offs between ACE2 binding affinity and expression stability | **SURVIVED** |

---

## Detailed Notebook Descriptions

### 1. `Investigate_thermodynamic_and_electrostatic_determ_master.ipynb`
- **Domain**: Computational Biophysics, Structural Virology, and Mutation Thermodynamics.
- **Inputs**: 
  - `data/skempi_v2.csv`: SKEMPI 2.0 database of binding free energy changes ($\Delta\Delta G$) upon mutation for protein-protein complexes.
  - `data/2ajf.pdb`: SARS-CoV Spike receptor-binding domain complexed with human ACE2 ($2.90$ Å).
  - `data/6m0j.pdb`: SARS-CoV-2 Spike RBD bound to human ACE2 ($2.45$ Å).
  - `data/6lzg.pdb`: High-resolution crystallographic structure of SARS-CoV-2 Spike RBD with ACE2 ($2.50$ Å).
- **Methodology**:
  - Full execution pipeline with 6 captured code outputs and interactive Plotly visualizers.
  - Literature discordance audit resolving contradictory reports for the `TE487S` replicate in SKEMPI v2.
  - Dual-crystallographic structural alignment extracting C$\alpha$ and all-atom spatial coordinates.
  - Debye-Hückel continuum electrostatics and atomic packing density metrics at the protein-protein binding interface.
  - Non-parametric statistical inference: Mann-Whitney U test, independent two-sample Welch's t-test, and Monte Carlo permutation testing ($10,000$ iterations).
- **Empirical Findings**:
  - Resolved the mechanism of the `NE479K` electrostatic clash between SARS-CoV and SARS-CoV-2.
  - Quantified the compensatory trade-off: mutations increasing favorable electrostatic attraction ($\Delta G_{\text{elec}} > 0.5$ kcal/mol) with low van der Waals clash ($\Delta G_{\text{vdw}} < 0.3$ kcal/mol) produce high-affinity binders ($\Delta\Delta G < -0.5$ kcal/mol).
  - **Paired Dossier**: [`discovery_dossier_8206dd8f.md`](../reports/dossiers/discovery_dossier_8206dd8f.md)

---

### 2. `Biophysical_Autonomous_Discovery_Interface_20261014.ipynb`
- **Domain**: Structural Biology, Epistatic Coupling, and Deep Mutational Scanning (DMS).
- **Inputs**:
  - `data/starr_rbd_dms_2020.csv`: Deep mutational scanning profiles ($4,221$ single amino acid variants) measuring human ACE2 binding affinity and yeast surface expression (folding stability) across the SARS-CoV-2 RBD.
  - `data/6m0j.pdb`: Cryo-EM/X-ray crystallographic coordinates of the SARS-CoV-2 RBD-ACE2 complex.
- **Methodology**:
  - Cross-correlates 3D atomic Euclidean distances ($\le 5.0$ Å contact threshold) with empirical functional scores.
  - Formulates an epistatic coupling model:
    $$\varepsilon_{ij} = \Delta\Delta G_{ij} - (\Delta\Delta G_i + \Delta\Delta G_j)$$
  - Evaluates trade-offs between binding affinity gain and thermal/expression destabilization.
  - Employs AST-sanitized cleanroom execution, PyTorch tensor hashing for cryptographic Proof-of-Work (PoW), and interactive multi-panel Plotly visualizers.
- **Empirical Findings**:
  - Identified spatial hotspots where single-point mutations significantly enhance ACE2 affinity ($\Delta\log_{10} K_D > +0.5$) without triggering expression penalties ($\Delta\text{expression} > -0.2$).
  - Confirmed positive epistatic coupling energy between spatially adjacent contact residues.
  - **Paired Dossier**: [`discovery_dossier_1ab21ad3.md`](../reports/dossiers/discovery_dossier_1ab21ad3.md) and [`discovery_dossier_85b7b0ef.md`](../reports/dossiers/discovery_dossier_85b7b0ef.md)

---

### 3. `Thermodynamic_Electrostatic_Determinants_Coronavirus_2026101.ipynb`
- **Domain**: Biophysical Chemistry & Structural Informatics.
- **Inputs**: `data/skempi_v2.csv`, `data/2ajf.pdb`, `data/6lzg.pdb`.
- **Methodology**:
  - 24 cells testing 3 formal claims ($C\text{-}01, C\text{-}02, C\text{-}03$).
  - Evaluates the multi-component thermodynamic free energy equation:
    $$\Delta\Delta G_{\text{bind}} = \Delta\Delta G_{\text{thaw\_ref}} + \Delta G_{\text{elec}} + \Delta G_{\text{vdw}} + \Delta G_{\text{solv}} - T\Delta S_{\text{conf}}$$
  - Computes permutation test between interface charge-altering mutations and electrostatically neutral mutations.
- **Empirical Findings**:
  - Falsified linear single-variable electrostatic predictors.
  - Confirmed that electrostatically neutral mutations (e.g. `TE159S`, `FE38S`) leave binding free energy within $\pm 0.1$ kcal/mol of wildtype baseline, whereas interface charge inversions exhibit high variance dictated by local dielectric shielding.
  - **Paired Dossier**: [`discovery_dossier_8206dd8f.md`](../reports/dossiers/discovery_dossier_8206dd8f.md)

---

### 4. `Thermodynamic_Determinants_Affinity_Binding_20261011.ipynb` & `20261012.ipynb`
- **Domain**: Biophysical Chemistry, Variant Evolution, and Structural Thermodynamics.
- **Inputs**: SKEMPI 2.0 experimental mutation records for the N501Y lineage, RCSB crystallographic structures.
- **Methodology**:
  - **20261011**: Double-mutant cycle analysis quantifying coupling free energy $\varepsilon = RT \ln\left[\frac{K_D(\text{double}) \cdot K_D(\text{wt})}{K_D(\text{501Y}) \cdot K_D(\text{Y41A})}\right]$. Integrates Graph Neural Network (GNN) link predictions with uncertainty intervals ($\sigma$).
  - **20261012**: Evaluates aromatic-contact energy contributions:
    $$\Delta\Delta G = \varepsilon_\pi \cdot n_\pi + \Delta\Delta G_{\text{steric}}$$
    where $n_\pi$ denotes the number of interface tyrosine residues within $\pi$-stacking distance ($< 4.5$ Å).
- **Empirical Findings**:
  - Confirmed that the N501Y mutation delivers $\approx -1.2$ kcal/mol affinity gain, mediated $\ge 50\%$ by non-additive aromatic $\pi$-stacking and hydrogen bonding with ACE2 Tyr41.
  - Falsified hypotheses positing pure steric packing improvements; established non-covalent aromatic interactions as the dominant stabilization driver.
  - **Paired Dossier**: [`discovery_dossier_c434664b.md`](../reports/dossiers/discovery_dossier_c434664b.md) and [`discovery_dossier_2da140c3.md`](../reports/dossiers/discovery_dossier_2da140c3.md)

---

### 5. `Autonomous_Scientific_Discovery_Mission_20261012.ipynb`
- **Domain**: Condensed Matter Physics, Materials Science, and Superconductivity.
- **Inputs**:
  - UCI Superconductivity Database: $21,263$ superconducting materials with experimentally measured critical temperatures ($T_c$) and 81 extracted atomic, electronic, and structural features.
- **Methodology**:
  - Mega-campaign notebook comprising 137 cells and 22 formal empirical claims.
  - Multi-cycle knowledge graph (KG) mining evaluating graph density scaling ($0.4 \to 0.8$) and depth parameters.
  - Regression and non-parametric testing evaluating correlations between valence electron density, Debye temperature approximations, mass variance, and $T_c$.
  - Automated hypothesis generation by GNN Oracle subjected to adversarial Popperian falsification tests.
- **Empirical Findings**:
  - Falsified unconstrained power-law scaling of $T_c$ with single elemental features.
  - Validated multi-variable non-linear constraints governing high-$T_c$ cuprate versus pnictide behavior.
  - Established rigorous statistical boundaries on knowledge-graph expansion efficiency versus experiment budget.
  - **Paired Dossier**: [`discovery_dossier_a3694592_2615_4425_9b2b_418073ab35d0.md`](../reports/dossiers/discovery_dossier_a3694592_2615_4425_9b2b_418073ab35d0.md)

---

### 6. Cleanroom Infrastructure & Metrological Verification Notebooks
- **`Forcefield_Templates_Pdbfixer_Residues_20261012.ipynb`**:
  - **Domain**: Computational Chemistry & Structural Cleanroom Preparation.
  - **Methodology**: Automated repair of missing heavy atoms and non-standard residue topologies using OpenMM PDBFixer and Amber14 forcefield templates.
  - **Finding**: Guaranteed zero missing atoms across simulation targets (`6M0J`, `2AJF`, `6LZG`), preventing NaN force blowups during electrostatic evaluations.
- **`Crystallographic_Experimental_Resolution_Metadata_20261012.ipynb`**:
  - **Domain**: Structural Informatics & Experimental Metrology.
  - **Methodology**: Programmatic validation of experimental resolution, diffraction method (X-ray vs Cryo-EM), space group, $R_{\text{free}}$, and $R_{\text{work}}$ across PDB deposition headers.
  - **Finding**: Established a deterministic filtering gate ensuring that only structures with resolution $\le 2.50$ Å and $R_{\text{free}} - R_{\text{work}} \le 0.08$ enter downstream biophysical discovery pipelines.
- **`Neural_Architecture_Literature_Correction_20261012.ipynb`**:
  - **Domain**: Epistemic Auditing & Automated Scientific Literature Verification.
  - **Methodology**: Automated harvesting and semantic parsing of arXiv abstracts querying zero-cost proxies in Neural Architecture Search (NAS).
  - **Finding**: Identified negative results and discordant literature claims, demonstrating SVEL's ability to reject hallucinated consensus and maintain empirical fidelity.
- **`Sanitized_Header_Fields_Legacy_20261012.ipynb`**:
  - **Domain**: Structural Data Provenance & Cryptographic Verification.
  - **Methodology**: Cross-verification of atomic coordinate records against legacy CIF schemas (`6M0J.cif`).
  - **Finding**: Confirmed structural integrity and deterministic coordinate alignment across data formats.
  - **Paired Dossier**: [`discovery_dossier_SOVEREIGN_DISCOVERY_PROD.md`](../reports/dossiers/discovery_dossier_SOVEREIGN_DISCOVERY_PROD.md)

---

### 7. Autonomous Discovery Mission Master Series (`reports/notebooks/`)
The repository includes the targeted master notebooks corresponding to dedicated autonomous discovery sessions:
- **`19ddb356-c70b-4bc5-8fa3-90a7725d2864_master.ipynb`**: Binding kinetics and electrostatic potential alteration.
- **`32018fbf-a185-4919-9347-5eb469db1e1e_master.ipynb`**: SARS-CoV-2 Spike RBD N501Y binding affinity.
- **`53b006cd-2b27-4816-ab0c-7c29b1a08237_master.ipynb`**: Non-linear atomic/electronic determinants of superconductivity.
- **`7a368ae6-512a-43fe-8742-6e4b9ba004f1_master.ipynb`**: Viral spike RBD thermodynamic binding kinetics.
- **`927b6299-b58f-4d04-a741-532fa90fb959_master.ipynb`**: N501Y affinity kinetics and structural interface geometry.
- **`f5a1fdf7-de07-4b1e-a3c0-838d99e9c8c9_master.ipynb`**: Epistatic trade-offs between ACE2 binding affinity and folding expression stability.

---

## Reproducing Empirical Notebooks

All datasets required to re-execute these notebooks are staged locally in the `data/` directory at the repository root:
- `data/skempi_v2.csv` (SKEMPI 2.0 binding affinity database)
- `data/starr_rbd_dms_2020.csv` (Starr 2020 deep mutational scanning dataset)
- `data/2ajf.pdb`, `data/6m0j.pdb`, `data/6lzg.pdb` (High-resolution crystallographic coordinates)

To execute any notebook in a clean Python environment:
```bash
# 1. Install dependencies
pip install -r ../requirements.txt

# 2. Launch JupyterLab or run headless via nbconvert
jupyter nbconvert --to notebook --execute Investigate_thermodynamic_and_electrostatic_determ_master.ipynb --output executed_run.ipynb
```
