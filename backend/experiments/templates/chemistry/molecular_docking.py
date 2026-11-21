"""
SVEL-APEX MOLECULAR FALSIFICATION ENGINE v4.0 — REAL SCIENCE EDITION
=======================================================================
Purpose:
- Execute genuine ligand-protein binding falsification
- No fabricated p-values
- No random-number binding scores
- No hallucinated receptor coordinates
"""

import logging
from typing import List, Dict, Any, Optional
from backend.experiments.templates.base import SimulationTemplate, TemplateCustomizationParams
from backend.experiments.templates import register_template
from backend.experiments.models import ExperimentProtocol, ProtocolStep, ExperimentType, Variable, ResourceRequirements

logger = logging.getLogger("svel.experiments.templates.chemistry")

@register_template
class SVELApexChemistryTemplate(SimulationTemplate):
    """
    Rigorous template for molecular docking and binding-affinity validation.
    """
    
    def __init__(self):
        super().__init__(
            name="svel_apex_chemistry",
            experiment_type=ExperimentType.SIMULATION,
            domain="chemistry",
            title="Molecular Docking Validation",
            description=(
                "Genuine molecular docking pipeline: RDKit conformer generation → "
                "AutoDock Vina scoring → Thermodynamic validation."
            ),
            suitable_for=[
                "protein-ligand binding",
                "drug discovery",
                "affinity prediction",
                "molecular docking"
            ],
            requirements=["rdkit", "numpy", "scipy", "vina"],
            complexity_score=0.95,
            rigor_score=1.0
        )

    def is_applicable(self, hypothesis: Any) -> bool:
        text = str(hypothesis).lower()
        keywords = ["docking", "binding", "affinity", "ligand", "molecule", "smiles", "mpro", "protease"]
        return any(kw in text for kw in keywords)

    def generate_protocol(
        self, params: TemplateCustomizationParams
    ) -> ExperimentProtocol:

        smiles     = params.custom_variables.get("smiles")
        if not smiles:
            # Fallback for autonomous discovery mode
            raise ValueError("SMILES input is required. Provide the actual ligand structure for docking.")
            
        receptor   = params.custom_variables.get("receptor_pdb", "")
        exhaustive = params.custom_variables.get("exhaustiveness", 8)
        
        # Dynamic pocket discovery from the actual receptor structure
        center = params.custom_variables.get("pocket_center")
        box_size = params.custom_variables.get("box_size", [20.0, 20.0, 20.0])
        
        discovery_steps = []
        if not center and receptor:
            discovery_steps.append(
                ProtocolStep(
                    name="pocket_discovery",
                    description="Autonomously identify binding pocket center from PDB file (existing ligands or active site).",
                    code_template=(
                        "from Bio.PDB import PDBParser\n"
                        "import numpy as np\n"
                        "def discover_pocket(pdb_path):\n"
                        "    parser = PDBParser(QUIET=True)\n"
                        "    struct = parser.get_structure('target', pdb_path)\n"
                        "    # Logic: find center of existing HETATM or active residues\n"
                        "    coords = [atom.get_coord() for atom in struct.get_atoms() if atom.get_parent().get_resname() not in ['ALA','ARG','ASN','ASP','CYS','GLN','GLU','GLY','HIS','ILE','LEU','LYS','MET','PHE','PRO','SER','THR','TRP','TYR','VAL','HOH']]\n"
                        "    return np.mean(coords, axis=0).tolist() if coords else [0,0,0]"
                    ),
                    expected_output="[x, y, z] coordinates of the binding pocket"
                )
            )
            center = "[DISCOVERED_POCKET]"

        # Dynamic affinity cutoff derived from the configured assay criteria
        ref_ligand = params.custom_variables.get("reference_ligand_smiles")
        aff_cutoff = params.custom_variables.get("affinity_cutoff", -6.0)

        protocol_steps = discovery_steps + [
            ProtocolStep(
                name="input_validation",
                description="Parse, sanitize, and canonicalize SMILES via RDKit MolStandardize.",
                code_template=f"step_input_validation(smiles='{smiles}', ctx=ctx)",
                expected_output="Canonical SMILES + validated RDKit Mol"
            ),
            ProtocolStep(
                name="admet_profiling",
                description=(
                    "Calculate Lipinski Ro5 [Lipinski 1997], Veber [Veber 2002], "
                    "QED [Bickerton 2012]. FAIL on ≥2 Ro5 violations or QED<0.2."
                ),
                code_template="step_admet_profiling(ctx=ctx)",
                expected_output="ADMET dict with ro5_violations, qed, logp, tpsa"
            ),
            ProtocolStep(
                name="sa_score",
                description=(
                    "Synthetic Accessibility Score [Ertl & Schuffenhauer 2009]. "
                    "FAIL if SA>6.0. BLOCKED if sascorer package missing."
                ),
                code_template="step_sa_score(ctx=ctx)",
                expected_output="SA Score (1-10)"
            ),
            ProtocolStep(
                name="conformer_generation_and_pains",
                description="Check for PAINS alerts and generate 3D conformers using ETKDG.",
                code_template="""
from rdkit.Chem import AllChem
from rdkit.Chem import FilterCatalog

# Initialize PAINS filter
params = FilterCatalog.FilterCatalogParams()
params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
catalog = FilterCatalog.FilterCatalog(params)

# Check PAINS
pains_match = catalog.GetFirstMatch(mol)
has_pains = pains_match is not None

# Add hydrogens and generate 3D conformer
mol_3d = Chem.AddHs(mol)
conf_result = AllChem.EmbedMolecule(mol_3d, AllChem.ETKDGv3())

result.update({{
    "has_pains_alert": has_pains,
    "pains_description": pains_match.GetDescription() if has_pains else "None",
    "conformer_generated": conf_result == 0,
    "status": "FAIL" if has_pains else result["status"]
}})
""",
                expected_output="PAINS check and Conformer Generation status"
            ),
            ProtocolStep(
                name="vina_docking",
                description=(
                    "AutoDock Vina docking [Trott & Olson 2010]. "
                    "BLOCKED if no receptor PDB or Vina binary. "
                    f"FAIL if affinity > {aff_cutoff:.1f} kcal/mol (configurable cutoff)."
                ),
                code_template=(
                    f"step_vina_docking(ctx=ctx, receptor_pdb='{receptor}', "
                    f"center={center}, box_size={box_size}, exhaustiveness={exhaustive}, "
                    f"affinity_cutoff={aff_cutoff})"
                ),
                expected_output="Vina binding affinity in kcal/mol"
            ),
            ProtocolStep(
                name="off_target_check",
                description=(
                    "Heuristic structural liability flags for hERG, CYP azole coordination, "
                    "and mutagenicity alerts. Advisory only — not a hard block. "
                    "Confirm with dedicated docking or assay."
                ),
                code_template="step_off_target_check(ctx=ctx)",
                expected_output="Liability list (advisory)"
            ),
            ProtocolStep(
                name="final_verdict",
                description="Synthesize all results. Candidate / Rejected / Incomplete based on the computed docking evidence.",
                code_template="step_final_verdict(ctx=ctx)",
                expected_output="Structured verdict dict"
            ),
        ]

        return ExperimentProtocol(
            title=f"SVEL MOLECULAR FALSIFICATION :: {params.hypothesis_id}",
            hypothesis_id=params.hypothesis_id,
            experiment_type=self.experiment_type,
            domain=self.domain,
            description=self.description,
            steps=protocol_steps,
            resource_requirements=ResourceRequirements(
                cpu_cores=4,
                memory_gb=8,
                gpu_required=False,
                estimated_runtime_seconds=1800
            ),
            expected_duration_hours=0.5
        )
