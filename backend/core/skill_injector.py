"""
ULTRON SURGICAL SKILL LOADER (SOVEREIGN EDITION V3)
==================================================
1. Deterministic Bundles (Agent-specific)
2. Keyword Overrides (Scientific triggers)
3. Sovereign Selection (LLM-driven catalog selection)

V3: Surgical deep recall to prevent prompt-drowning.
"""

import logging
import os
import re
import asyncio
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Resolve project root
_CORE_DIR = Path(__file__).parent
_BACKEND_DIR = _CORE_DIR.parent
_ROOT = _BACKEND_DIR.parent

# [V256] DOMAIN EXCLUSION MAP: Skills that must NEVER appear in ML/CS campaigns
DOMAIN_EXCLUSIVE_SKILLS = {
    # Physics-only skills
    "tokamak-pedestal-physics", "mhd-modeling", "grad-shafranov-solvers",
    "fluidsim", "astropy", "simpy",
    # Biology-only skills
    "biopython", "pydeseq2", "pysam", "ensembl-database", "scanpy", "anndata",
    "scvi-tools", "cobrapy", "gget", "deeptools", "scikit-bio", "ena-database",
    "gene-database", "geo-database", "reactome-database", "string-database",
    # Chemistry-only skills
    "rdkit", "datamol", "deepchem", "chembl-database", "pubchem-database",
    "zinc-database", "drugbank-database", "diffdock", "molfeat", "matchms",
    "pyopenms", "pytdc", "torchdrug", "medchem",
    # Structural biology-only
    "alphafold-database", "pdb-database", "uniprot-database", "esm", "pymatgen",
    # Clinical-only
    "clinicaltrials-database", "fda-database", "gwas-database", "clinvar-database",
    "cosmic-database", "hmdb-database", "opentargets-database", "pyhealth",
    "scikit-survival",
    # Neuroscience imaging
    "pydicom", "nibabel", "pathml", "histolab",
    # Lab automation (physical wet-lab)
    "pylabrobot", "opentrons-integration", "benchling-integration",
    "protocolsio-integration", "labarchive-integration",
}

ML_DOMAINS = {"machine_learning", "ml", "cs", "computer_science", "deep_learning",
              "computer_vision", "nlp", "artificial_intelligence"}

# Group mapping for helper get_skill_domain
_SKILL_DOMAIN_MAP = {
    # Physics
    "tokamak-pedestal-physics": "physics", "mhd-modeling": "physics", "grad-shafranov-solvers": "physics",
    "fluidsim": "physics", "astropy": "physics", "simpy": "physics",
    # Biology
    "biopython": "biology", "pydeseq2": "biology", "pysam": "biology", "ensembl-database": "biology",
    "scanpy": "biology", "anndata": "biology", "scvi-tools": "biology", "cobrapy": "biology",
    "gget": "biology", "deeptools": "biology", "scikit-bio": "biology", "ena-database": "biology",
    "gene-database": "biology", "geo-database": "biology", "reactome-database": "biology", "string-database": "biology",
    # Chemistry
    "rdkit": "chemistry", "datamol": "chemistry", "deepchem": "chemistry", "chembl-database": "chemistry",
    "pubchem-database": "chemistry", "zinc-database": "chemistry", "drugbank-database": "chemistry",
    "diffdock": "chemistry", "molfeat": "chemistry", "matchms": "chemistry", "pyopenms": "chemistry",
    "pytdc": "chemistry", "torchdrug": "chemistry", "medchem": "chemistry",
    # Structural biology
    "alphafold-database": "structural_biology", "pdb-database": "structural_biology",
    "uniprot-database": "structural_biology", "esm": "structural_biology", "pymatgen": "structural_biology",
    # Clinical
    "clinicaltrials-database": "clinical", "fda-database": "clinical", "gwas-database": "clinical",
    "clinvar-database": "clinical", "cosmic-database": "clinical", "hmdb-database": "clinical",
    "opentargets-database": "clinical", "pyhealth": "clinical", "scikit-survival": "clinical",
    # Neuroscience
    "pydicom": "neuroscience", "nibabel": "neuroscience", "pathml": "neuroscience", "histolab": "neuroscience",
    # Lab automation
    "pylabrobot": "lab_automation", "opentrons-integration": "lab_automation",
    "benchling-integration": "lab_automation", "protocolsio-integration": "lab_automation",
    "labarchive-integration": "lab_automation"
}

def get_skill_domain(skill_name: str) -> str:
    """Return the domain for a given skill name."""
    skill_lower = skill_name.lower().strip()
    if skill_lower in _SKILL_DOMAIN_MAP:
        return _SKILL_DOMAIN_MAP[skill_lower]
    return "general"

def is_skill_blocked_for_domain(skill_name: str, campaign_domain: str) -> bool:
    """Check if a skill is blocked for a given campaign domain to prevent cross-domain contamination."""
    cd_lower = campaign_domain.lower().strip()
    skill_lower = skill_name.lower().strip()
    
    # 1. Determine campaign domain group
    is_ml = cd_lower in ML_DOMAINS
    is_physics = cd_lower in {"physics", "physical_sim", "astrophysics", "fusion"}
    is_biology = cd_lower in {"biology", "genomics", "bio", "bioinformatics"}
    is_chemistry = cd_lower in {"chemistry", "chem", "medchem"}
    is_structural = cd_lower in {"structural_biology", "structural-biology", "biophysics", "computational_biophysics"}
    is_clinical = cd_lower in {"clinical", "medicine", "health", "clinicaltrials"}
    is_neuro = cd_lower in {"neuroscience", "brain"}
    is_lab_auto = cd_lower in {"lab_automation", "automation"}
    
    # 2. Get skill domain
    skill_domain = get_skill_domain(skill_lower)
    
    if skill_domain == "general":
        return False
        
    # 3. Apply symmetric exclusion rules
    if is_ml:
        return skill_lower in DOMAIN_EXCLUSIVE_SKILLS
        
    if is_physics:
        return skill_domain in {"biology", "chemistry", "structural_biology", "clinical", "neuroscience", "lab_automation"}
        
    if is_biology:
        return skill_domain in {"physics", "chemistry", "clinical", "neuroscience", "lab_automation"}

    if is_structural:
        return skill_domain in {"physics", "clinical", "neuroscience", "lab_automation"}
        
    if is_chemistry:
        return skill_domain in {"physics", "biology", "clinical", "neuroscience", "lab_automation"}
        
    if is_clinical:
        return skill_domain in {"physics", "chemistry", "biology", "neuroscience", "lab_automation"}
        
    if is_neuro:
        return skill_domain in {"physics", "chemistry", "biology", "clinical", "lab_automation"}
        
    if is_lab_auto:
        return skill_domain in {"physics", "chemistry", "biology", "clinical", "neuroscience"}
        
    return False


@dataclass
class Skill:
    """Represents a domain-specific capability."""
    name: str
    folder_path: Path
    description: str
    content: str
    code_examples: List[str] = field(default_factory=list)
    reference_materials: Dict[str, str] = field(default_factory=dict)
    assets: Dict[str, str] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)
    configs: Dict[str, str] = field(default_factory=dict)
    tier: str = "T2"
    domain: str = "general"
    usage_count: int = 0
    
    def to_prompt_block(self, query: str = "", include_examples: bool = False, include_deep: bool = False, domain: Optional[str] = None) -> str:
        """
        Domain-agnostic smart routing.
        Fuses the core SKILL.md and selectively pulls in deep references as needed.
        """
        # 1. Start with the Core Specification (The Map)
        block = f"\n### SCIENTIFIC SPECIFICATION: {self.name.upper()}\n"
        block += f"#### CORE DOCUMENTATION (SKILL.md):\n{self.content}\n"
        
        # 2. Modern Frontier Retrieval: Full un-truncated technical assets
        if include_deep:
            # Modern frontier context support (200K - 2M tokens)
            truncation_limit = 200000
            
            # Scan SKILL.md for referenced resources (references/, scripts/, assets/, configs/)
            resolved_resources = self._resolve_surgical_resources(query)
            
            if resolved_resources:
                block += "\n#### SURGICALLY RETRIEVED TECHNICAL ASSETS:\n"
                for sub_dir, file_name in resolved_resources:
                    content = ""
                    header = f"##### {sub_dir.upper().rstrip('/')}: {file_name}\n"
                    
                    # Pull from the appropriate internal dictionary
                    if sub_dir == "references/":
                        content = self.reference_materials.get(file_name, "")
                    elif sub_dir == "scripts/":
                        content = self.scripts.get(file_name, "")
                    elif sub_dir == "assets/":
                        content = self.assets.get(file_name, "")
                    elif sub_dir == "configs/":
                        content = self.configs.get(file_name, "")
                    
                    if content:
                        logger.info(f" [SMART ROUTING] Injected {sub_dir}{file_name} for skill '{self.name}'")
                        block += header + f"{content[:truncation_limit]}\n"
                        if len(content) > truncation_limit:
                            block += f"[... {file_name} truncated at {truncation_limit} chars ...]\n"

        if include_examples and self.code_examples:
            block += "#### RIGOROUS USAGE EXAMPLES:\n"
            for ex in self.code_examples[:5]:
                block += f"```python\n{ex.strip()}\n```\n"
        
        block += "--- END SPECIFICATION ---\n"
        return block

    def _resolve_surgical_resources(self, query: str) -> List[Tuple[str, str]]:
        """
        Global smart resource router.
        Scans SKILL.md index for subdirectory paths (references/, scripts/, etc.)
        Returns a list of (subdirectory, filename) tuples.
        """
        resolved = [] # List[Tuple[subdirectory, filename]]
        q = query.lower()
        
        # Regex to catch: - `subdirectory/filename.ext` - Description
        # Subdirectories: references/, scripts/, assets/, configs/
        path_pattern = r"-\s+[`\"'](references/|scripts/|assets/|configs/)(.*?\.(?:md|py|txt|json|csv|pdb|yaml|yml))[`\"']\s+-\s+(.*?)(?:\n|$)"
        matches = re.findall(path_pattern, self.content)
        
        # Also catch the legacy bold pattern: - **`filename`** - Description (assumed reference)
        legacy_pattern = r"-\s+\*\*`(.*?)`\*\*\s+-\s+(.*?)(?:\n|$)"
        legacy_matches = re.findall(legacy_pattern, self.content)
        for f_name, desc in legacy_matches:
            matches.append(("references/", f_name, desc))
        
        IGNORE_RESOURCE_TERMS = {"model", "data", "train", "test", "setup", "config", "runs", "experiment", "analysis", "result", "results", "file", "files", "code", "script", "scripts", "dataset", "datasets"}
        for sub_dir, file_name, description in matches:
            desc_terms = {term for term in re.findall(r"\w+", description.lower()) if term not in IGNORE_RESOURCE_TERMS}
            query_terms = {term for term in re.findall(r"\w+", q) if term not in IGNORE_RESOURCE_TERMS}
            
            # Smart Match: If file name is in query OR description terms are in query
            if file_name.lower() in q or any(term in query_terms for term in desc_terms if len(term) > 3):
                resolved.append((sub_dir, file_name))
                
        # Deduplicate while preserving order
        seen = set()
        deduped = [x for x in resolved if not (x in seen or seen.add(x))]
        
        # Relaxed limit of up to 10 subfiles per skill to prevent token bloat
        return deduped[:10]

class UltronExpertSystem:
    """Surgical knowledge injection system for ULTRON agents."""

    SKILL_BUNDLES = {
        "meta_cognitive": ["scientific-critical-thinking", "scientific-brainstorming", "strategy-optimization", "peer-review", "scholar-evaluation"],
        "hypothesis_generator": ["hypothesis-generation", "scientific-brainstorming", "hypogenic"],
        "red_team": ["peer-review", "scientific-critical-thinking", "scholar-evaluation"],
        "fact_checker": ["peer-review", "scientific-critical-thinking", "scholar-evaluation", "literature-review"],
        "summarizer": ["literature-review"],
        "report_composer": ["scientific-writing", "reportlab", "scientific-visualization", "matplotlib", "seaborn"],
        "doc_reader": ["document-skills", "literature-review", "markitdown"],
        "web_search": ["perplexity-search", "paper-2-web"],
        "data_analyst": ["statistical-analysis", "scientific-visualization", "statsmodels", "exploratory-data-analysis", "pandas", "scipy", "numpy", "matplotlib", "seaborn", "polars", "vaex", "dask", "umap-learn"],
        "experiment_designer": ["scientific-brainstorming", "biomni", "pylabrobot", "opentrons-integration", "benchling-integration", "protocolsio-integration", "labarchive-integration"],
        "genomics": ["biopython", "pydeseq2", "pysam", "ensembl-database", "scanpy", "anndata", "scvi-tools", "cobrapy", "gget", "deeptools", "scikit-bio", "ena-database", "gene-database", "geo-database", "reactome-database", "string-database"],
        "chemistry": ["rdkit", "datamol", "deepchem", "chembl-database", "pubchem-database", "zinc-database", "drugbank-database", "diffdock", "molfeat", "matchms", "pyopenms", "pytdc", "torchdrug", "medchem"],
        "structural_biology": ["biopython", "alphafold-database", "pdb-database", "uniprot-database", "diffdock", "esm", "molfeat", "pymatgen"],
        "biophysics": ["biopython", "alphafold-database", "pdb-database", "uniprot-database", "diffdock", "esm", "scipy", "sympy", "matplotlib", "seaborn"],
        "clinical": ["clinicaltrials-database", "fda-database", "gwas-database", "clinvar-database", "cosmic-database", "hmdb-database", "openalex-database", "opentargets-database", "pubmed-database", "biorxiv-database", "pyhealth", "scikit-survival"],
        "machine_learning": ["scikit-learn", "pytorch-lightning", "transformers", "shap", "umap-learn", "torch_geometric", "optuna"],
        "physics": ["scipy", "sympy", "astropy", "grad-shafranov-solvers", "mhd-modeling", "tokamak-pedestal-physics", "fluidsim", "simpy"],
        "neuroscience": ["pydicom", "nibabel", "pathml", "histolab"],
        "physical_sim": ["scipy", "sympy", "grad-shafranov-solvers", "mhd-modeling", "tokamak-pedestal-physics"]
    }

    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = Path(skills_dir) if skills_dir else _BACKEND_DIR / "skills"
        self.skills_cache: Dict[str, Skill] = {}
        self.meta_skills: Dict[str, Skill] = {}
        self._discover_skills()
        logger.info(f"UltronExpertSystem: Sovereign Loader ready with {len(self.skills_cache)} skills.")

    async def inject_functional_skills(self, prompt: str, query: str = "", max_skills: int = 3, domain: str = "general", include_examples: bool = False) -> str:
        """
        Dynamic Skill Injection.
        Fuses prompt with the Top-K relevant scientific skills.
        """
        skills = self.find_relevant_skills(query, max_skills=max_skills, domain=domain)
        if not skills:
            return prompt
            
        injection_block = "\n### INJECTED Ph.D. SCIENTIFIC SKILLS:\n"
        for skill in skills:
            injection_block += skill.to_prompt_block(include_examples=include_examples, include_deep=True, domain=domain)
            
        return prompt + "\n" + injection_block + "\n"


    def _discover_skills(self):
        if not self.skills_dir.exists(): return
        import os
        for root, dirs, files in os.walk(self.skills_dir):
            if "SKILL.md" in files:
                folder = Path(root)
                skill_file = folder / "SKILL.md"
                skill = self._load_atomic_skill(folder, skill_file)
                if skill:
                    self.skills_cache[skill.name] = skill
                    if skill.tier == "T1":
                        self.meta_skills[skill.name] = skill

    def _load_atomic_skill(self, folder: Path, skill_file: Path) -> Optional[Skill]:
        try:
            content = skill_file.read_text(encoding="utf-8")
            subfolders = {"references": {}, "assets": {}, "scripts": {}, "configs": {}}
            for sub in subfolders.keys():
                path = folder / sub
                if path.exists():
                    for f in path.iterdir():
                        if f.is_file() and not f.name.startswith("."):
                            try: subfolders[sub][f.name] = f.read_text(encoding="utf-8", errors="ignore")
                            except Exception as e: logger.error(f" [SKILL_INJECTOR] Failed to read subfile {f.name}: {e}")
            
            code_examples = re.findall(r"```python(.*?)```", content, re.DOTALL)
            description = folder.name
            desc_match = re.search(r"description:\s*\"(.*?)\"", content)
            if desc_match: description = desc_match.group(1)

            return Skill(
                name=folder.name,
                folder_path=folder,
                description=description,
                content=content,
                code_examples=[c.strip() for c in code_examples],
                reference_materials=subfolders["references"],
                assets=subfolders["assets"],
                scripts=subfolders["scripts"],
                configs=subfolders["configs"],
                tier="T1" if "meta" in str(folder) or folder.name in ["scientific-critical-thinking", "peer-review"] else "T2",
                domain=get_skill_domain(folder.name)
            )
        except Exception as e:
            logger.error(f"Failed to load atomic skill from {folder}: {e}")
            return None

    def find_relevant_skills(self, query: str, max_skills: int = 5, domain: str = "other") -> List[Skill]:
        """Alias for search_skills to support ExperimentAgent discovery."""
        return self.search_skills(query, top_k=max_skills, domain=domain)

    def search_skills(self, query: str, top_k: int = 5, domain: str = "other") -> List[Skill]:
        """
        Density-Weighted Precision Search.
        Replaces simple word counting to prevent long-file bias.
        [V256+] Domain-gating: Prevents cross-domain skill contamination.
        """
        found = []
        query_lower = query.lower()
        query_terms = set(re.findall(r"\w+", query_lower))

        # Keyword Overrides first (Precision)
        overrides = self._check_keyword_overrides(query)
        for s in overrides:
            if is_skill_blocked_for_domain(s.name, domain):
                continue  # Block cross-domain contamination
            found.append(s)

        scored_skills = []
        for name, skill in self.skills_cache.items():
            # DOMAIN GATE: Skip skills that are blocked for this domain
            if is_skill_blocked_for_domain(name, domain):
                continue

            score = 0
            # 1. NAME MATCH (The 'Sniper' bonus)
            if skill.name.lower() in query_lower:
                score += 50

            # 2. UNIQUE TERM DENSITY (The 'Specialist' bonus)
            skill_terms = set(re.findall(r"\w+", (skill.description + " " + skill.content).lower()))
            overlap = query_terms.intersection(skill_terms)

            # Weigh overlap by uniqueness (shorter matches = higher density)
            for term in overlap:
                if len(term) < 4: continue
                # Unique term bonus
                score += 10
                # Density bonus: how frequent is this term in THIS skill vs others?
                # (Simplified TF-IDF for speed)
                score += 5

            if score > 0:
                scored_skills.append((score, skill))

        # Sort by score descending
        scored_skills.sort(key=lambda x: x[0], reverse=True)

        for _, skill in scored_skills:
            if skill not in found:
                found.append(skill)
            if len(found) >= top_k:
                break

        return found


    def get_tool_catalog(self, domain: str = "other") -> str:
        """Concise catalog for LLM Sovereign selection."""
        catalog = "### ULTRON SCIENTIFIC TOOL CATALOG\n"
        for name, skill in self.skills_cache.items():
            if is_skill_blocked_for_domain(name, domain):
                continue
            catalog += f"- {name}: {skill.description}\n"
        return catalog

    async def _agentic_subfile_retrieve(self, valid_skills: List[Skill], query: str, llm_manager) -> List[Dict[str, str]]:
        if not llm_manager or not valid_skills:
            return []
        
        skill_docs = ""
        for skill in valid_skills:
            # Provide the SKILL.md map to the LLM
            skill_docs += f"### SKILL: {skill.name}\n{skill.content}\n\n"
        subfile_prompt = f"""You are a Ph.D. Technical Architect.
You are preparing an experimental protocol for:
{query}

You have selected these parent skills. Read their documentation (SKILL.md) to find specific sub-assets (references, scripts, assets).
{skill_docs}

[HIERARCHICAL DESCENT RULE]
Identify exactly which sub-files you need to read to implement the math or code for this task.
UNIVERSAL LIMIT: You can select a MAXIMUM of 10 sub-files TOTAL across all selected skills.
Valid sub-asset directories are typically: references/, scripts/, assets/, configs/.

Output ONLY a JSON list of objects using the exact skill name and subfile path.
Example: [{{"skill": "<skill_name>", "subfile": "<directory>/<filename.ext>"}}]
Do not add any other prose.
"""
        try:
            logger.info(f" [HIERARCHY] Requesting sub-assets for {len(valid_skills)} skills...")
            subfile_response = await llm_manager.run_async(
                subfile_prompt,
                system="You are a JSON-only hierarchical asset selector.",
                source="expert_subfile_selector",
                temperature=0.1
            )
            if isinstance(subfile_response, dict):
                subfile_text = subfile_response.get("text", "[]")
            elif isinstance(subfile_response, str):
                subfile_text = subfile_response
            else:
                subfile_text = "[]"
            # Strip markdown fences if present
            clean_text = subfile_text.strip()
            if "```" in clean_text:
                import re
                fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
                if fence_match:
                    clean_text = fence_match.group(1).strip()

            # Attempt 1: Direct JSON parse of whole text or dict
            try:
                parsed_obj = json.loads(clean_text)
                if isinstance(parsed_obj, list):
                    return parsed_obj[:10]
                elif isinstance(parsed_obj, dict):
                    for k in ["selected", "subfiles", "selected_subfiles", "skills", "files"]:
                        if k in parsed_obj and isinstance(parsed_obj[k], list):
                            return parsed_obj[k][:10]
            except Exception:
                pass

            # Attempt 2: Extract JSON array with raw_decode
            start_bracket = clean_text.find("[")
            if start_bracket != -1:
                try:
                    decoder = json.JSONDecoder()
                    selected, _ = decoder.raw_decode(clean_text[start_bracket:])
                    if isinstance(selected, list):
                        return selected[:10]
                except Exception as parse_err:
                    # Attempt 3: Look for dict with raw_decode
                    start_brace = clean_text.find("{")
                    if start_brace != -1:
                        try:
                            decoder = json.JSONDecoder()
                            selected_dict, _ = decoder.raw_decode(clean_text[start_brace:])
                            if isinstance(selected_dict, dict):
                                for k in ["selected", "subfiles", "selected_subfiles", "skills", "files"]:
                                    if k in selected_dict and isinstance(selected_dict[k], list):
                                        return selected_dict[k][:10]
                        except Exception:
                            pass
                    logger.debug(f"Subfile JSON decode fallback bypassed: {parse_err}")
        except Exception as e:
            logger.error(f" [HIERARCHY] Subfile selection failed: {e}")
        return []

    def _build_injection_text(self, valid_skills: List[Skill], selected_subfiles: List[Dict[str, str]], include_examples: bool = True) -> str:
        injection_text = ""
        # Track total subfiles injected to ensure universal limit
        total_injected = 0
        
        for skill in valid_skills:
            injection_text += f"\n### SCIENTIFIC SPECIFICATION: {skill.name.upper()}\n"
            skill_doc = (skill.content[:4000] + "\n[...truncated...]") if len(skill.content) > 4000 else skill.content
            injection_text += f"#### CORE DOCUMENTATION (SKILL.md):\n{skill_doc}\n"
            
            # Map subfiles for this specific skill
            requested_for_this_skill = [
                s["subfile"] for s in selected_subfiles 
                if isinstance(s, dict) and s.get("skill") == skill.name and "subfile" in s
            ]
            
            if requested_for_this_skill:
                injection_text += "\n#### SURGICALLY RETRIEVED SUB-ASSETS:\n"
                for subfile in requested_for_this_skill:
                    if total_injected >= 3: break # Universal Stop (max 3 files across skills)
                    
                    content = ""
                    # Normalize path and check internal dictionaries
                    clean_path = subfile.split("/")[-1]
                    if "references/" in subfile: content = skill.reference_materials.get(clean_path, "")
                    elif "scripts/" in subfile: content = skill.scripts.get(clean_path, "")
                    elif "assets/" in subfile: content = skill.assets.get(clean_path, "")
                    elif "configs/" in subfile: content = skill.configs.get(clean_path, "")
                    
                    if content:
                        logger.info(f" [GUIDED DESCENT] Injected {subfile} for skill '{skill.name}'")
                        truncation_limit = 4000
                        trimmed = content[:truncation_limit]
                        if len(content) > truncation_limit:
                            trimmed += "\n[...remaining subfile truncated for prompt brevity...]"
                        injection_text += f"##### FILE: {subfile}\n{trimmed}\n"
                        total_injected += 1

            if include_examples and skill.code_examples:
                injection_text += "#### RIGOROUS USAGE EXAMPLES:\n"
                for ex in skill.code_examples[:5]:
                    injection_text += f"```python\n{ex.strip()}\n```\n"
            injection_text += "--- END SPECIFICATION ---\n"
        return injection_text

    async def inject_bundle(self, base_prompt: str, bundle_name: str, include_deep: bool = False, include_examples: bool = True, domain: Optional[str] = None, query: str = '', llm_manager=None) -> str:
        """Inject hard-wired neural bundle with optional Agentic Exploration."""
        if bundle_name not in self.SKILL_BUNDLES: return base_prompt
        skill_names = self.SKILL_BUNDLES[bundle_name]
        valid_skills = [self.skills_cache[name] for name in skill_names if name in self.skills_cache]
        
        selected_subfiles = []
        if llm_manager and include_deep:
            selected_subfiles = await self._agentic_subfile_retrieve(valid_skills, query or bundle_name, llm_manager)
            
        injection = f"\n\n### MANDATORY {bundle_name.upper()} PROTOCOLS\n"
        if llm_manager and include_deep:
            injection += self._build_injection_text(valid_skills, selected_subfiles, include_examples)
        else:
            for skill in valid_skills:
                injection += skill.to_prompt_block(query=query, include_deep=include_deep, include_examples=include_examples, domain=domain)
        return base_prompt + injection

    async def inject_dynamic_skills(self, base_prompt: str, selected_tools: List[str], include_deep: bool = True, include_examples: bool = True, query: str = "", domain: Optional[str] = None, llm_manager=None) -> str:
        """Inject tools chosen specifically by the LLM."""
        valid_skills = [self.skills_cache[name.strip().lower()] for name in selected_tools if name.strip().lower() in self.skills_cache]
        selected_subfiles = []
        if llm_manager and include_deep:
            selected_subfiles = await self._agentic_subfile_retrieve(valid_skills, query, llm_manager)

        injection = "\n\n### MANDATORY TECHNICAL ASSETS (LLM SELECTED)\n"
        if llm_manager and include_deep:
            injection += self._build_injection_text(valid_skills, selected_subfiles, include_examples)
        else:
            for skill in valid_skills:
                injection += skill.to_prompt_block(query=query, include_deep=include_deep, include_examples=include_examples, domain=domain)
        return base_prompt + injection

    async def inject_skills(self, base_prompt: str, query: str, max_skills: int = 3, domain: str = "other", include_deep: bool = False, include_examples: bool = True, llm_manager=None) -> str:
        """Hybrid injection: Keyword Overrides + Context Search."""
        if any(kw in query.lower() for kw in ["design", "protocol", "architecture", "rigor"]):
            base_prompt = await self.inject_bundle(base_prompt, "meta_cognitive", include_deep=include_deep, include_examples=include_examples, domain=domain, llm_manager=llm_manager)
        matches = self.search_skills(query, top_k=max_skills, domain=domain)
        if not matches: return base_prompt
        
        selected_subfiles = []
        if llm_manager and include_deep:
            selected_subfiles = await self._agentic_subfile_retrieve(matches, query, llm_manager)
            
        injection = "\n\n### INJECTED TECHNICAL CAPABILITIES\n"
        if llm_manager and include_deep:
            injection += self._build_injection_text(matches, selected_subfiles, include_examples)
        else:
            for s in matches: injection += s.to_prompt_block(include_deep=include_deep, include_examples=include_examples, domain=domain)
        return base_prompt + injection

    async def inject_meta_skills(self, base_prompt: str, query: str, max_skills: int = 3, domain: str = "other", include_deep: bool = False, include_examples: bool = True, llm_manager=None) -> str:
        """Inject higher-order cognitive protocols (T1)."""
        base_prompt = await self.inject_bundle(base_prompt, "meta_cognitive", include_deep=include_deep, include_examples=include_examples, domain=domain, llm_manager=llm_manager)
        matches = self.search_skills(query, top_k=max_skills, domain=domain)
        t1_matches = [s for s in matches if getattr(s, "tier", "T2") == "T1"]
        if not t1_matches: return base_prompt
        
        selected_subfiles = []
        if llm_manager and include_deep:
            selected_subfiles = await self._agentic_subfile_retrieve(t1_matches, query, llm_manager)
            
        injection = "\n\n### INJECTED COGNITIVE PROTOCOLS (META)\n"
        if llm_manager and include_deep:
            injection += self._build_injection_text(t1_matches, selected_subfiles, include_examples)
        else:
            for s in t1_matches: injection += s.to_prompt_block(include_deep=include_deep, include_examples=include_examples, domain=domain)
        return base_prompt + injection

    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        return self.skills_cache.get(name)

    async def agentic_inject(self, base_prompt: str, query: str, llm_manager, max_skills: int = 3, domain: Optional[str] = None) -> str:
        """
        Agentic Skill Injection.
        Turn 1: LLM reads catalog and selects Top-K skills.
        Turn 2: LLM reads the SKILL.md of selected skills and autonomously requests specific subfiles to read.
        """
        if not llm_manager:
            return base_prompt

        # Turn 1: Sovereign Skill Selection
        catalog = self.get_tool_catalog(domain=domain or "other")
        selection_prompt = f"""You are an Expert Scientific skill Router.
Review the following research objective/task:
{query}

Review the available ULTRON scientific skills:
{catalog}

Task: Choose up to {max_skills} most critical skills to fulfill the objective.
Output ONLY a JSON list of strings matching the skill names exactly. Example: ["skill-name1", "skill-name2"]
Do not add any other prose.
"""
        try:
            logger.info(" [SOVEREIGN] Triggering LLM-driven Skill Selection...")
            selection_response = await llm_manager.run_async(
                selection_prompt, 
                system="You are a JSON-only tool selector.",
                source="expert_skill_selector", 
                temperature=0.1
            )
            if isinstance(selection_response, dict):
                raw_text = selection_response.get("text", "[]")
            elif isinstance(selection_response, str):
                raw_text = selection_response
            else:
                raw_text = "[]"
            selected_tools = []
            from backend.utils.json_repair import repair_json
            parsed_repair = repair_json(raw_text)
            if isinstance(parsed_repair, list):
                selected_tools = parsed_repair
            elif isinstance(parsed_repair, dict):
                for k in ["skills", "selected", "tools", "selected_skills", "skill_names"]:
                    if k in parsed_repair and isinstance(parsed_repair[k], list):
                        selected_tools = parsed_repair[k]
                        break

            if not selected_tools:
                start_bracket = raw_text.find("[")
                if start_bracket != -1:
                    try:
                        decoder = json.JSONDecoder()
                        decoded, _ = decoder.raw_decode(raw_text[start_bracket:])
                        if isinstance(decoded, list):
                            selected_tools = decoded
                    except Exception as parse_err:
                        try:
                            depth = 0
                            end_pos = -1
                            for idx in range(start_bracket, len(raw_text)):
                                if raw_text[idx] == '[':
                                    depth += 1
                                elif raw_text[idx] == ']':
                                    depth -= 1
                                    if depth == 0:
                                        end_pos = idx + 1
                                        break
                            if end_pos != -1:
                                decoded = json.loads(raw_text[start_bracket:end_pos])
                                if isinstance(decoded, list):
                                    selected_tools = decoded
                        except Exception:
                            pass
                        if not selected_tools:
                            logger.warning(f"Failed to parse tool injection JSON: {parse_err}")
        except Exception as e:
            logger.error(f" [SOVEREIGN] Smart skill selection failed: {e}")
            selected_tools = []

        if not selected_tools:
            return base_prompt

        # Prepare for Turn 2
        valid_skills = []
        skill_docs = ""
        campaign_domain = domain or "other"
        for name in selected_tools[:max_skills]:
            if not isinstance(name, str): continue
            skill_name = name.strip().lower()
            if is_skill_blocked_for_domain(skill_name, campaign_domain):
                logger.info(f" [DOMAIN GATE] Blocking LLM-selected skill '{skill_name}' in domain '{campaign_domain}'.")
                continue
            skill = self.get_skill_by_name(skill_name)
            if skill:
                valid_skills.append(skill)
        
        if not valid_skills:
            return base_prompt

        # Turn 2: Agentic Subfile Retrieval (HIERARCHICAL DESCENT)
        selected_subfiles = await self._agentic_subfile_retrieve(valid_skills, query, llm_manager)

        # Construction of the final prompt injection
        injection_text = f"\n\n### INJECTED Ph.D. SCIENTIFIC SKILLS (AGENTIC SELECTION):\n"
        injection_text += self._build_injection_text(valid_skills, selected_subfiles, include_examples=True)
            
        return base_prompt + injection_text

    def _check_keyword_overrides(self, query: str, tier: Optional[str] = None) -> List[Skill]:
        """Exhaustive Keyword Map (RESTORED)."""
        overrides = {
            "genomics": ["biopython", "ensembl-database", "gget", "pysam", "pydeseq2", "scanpy"],
            "transcriptomics": ["scanpy", "anndata", "scvi-tools", "arboreto"],
            "proteomics": ["uniprot-database", "alphafold-database", "matchms", "pyopenms"],
            "stats": ["statistical-analysis", "statsmodels", "pingouin", "scipy", "pymc"],
            "statistics": ["statistical-analysis", "statsmodels", "pingouin", "scipy", "pymc"],
            "statistical": ["statistical-analysis", "statsmodels", "pingouin", "scipy", "pymc"],
            "protein": ["biopython", "alphafold-database", "pdb-database", "uniprot-database", "diffdock"],
            "proteins": ["biopython", "alphafold-database", "pdb-database", "uniprot-database", "diffdock"],
            "docking": ["diffdock", "gnina", "autodock-vina", "open-babel"],
            "ml": ["scikit-learn", "pytorch-lightning", "transformers", "shap", "torch_geometric"],
            "physics": ["scipy", "sympy", "astropy", "grad-shafranov-solvers", "mhd-modeling"],
            "clinical": ["clinicaltrials-database", "fda-database", "gwas-database", "clinvar-database"],
            "viz": ["scientific-visualization", "plotly-scientific", "seaborn", "matplotlib"],
            "visualization": ["scientific-visualization", "plotly-scientific", "seaborn", "matplotlib"],
            "visualize": ["scientific-visualization", "plotly-scientific", "seaborn", "matplotlib"],
            "critical": ["scientific-critical-thinking"],
            "critique": ["scientific-critical-thinking", "peer-review"],
            "adversarial": ["scientific-critical-thinking", "peer-review"],
            "scholar": ["scholar-evaluation"],
            "scholarly": ["scholar-evaluation"],
            "grade": ["scholar-evaluation"],
            "grading": ["scholar-evaluation"],
            "write": ["scientific-writing"],
            "writer": ["scientific-writing"],
            "writing": ["scientific-writing"],
        }
        found = []
        query_lower = query.lower().replace("_", " ").replace("-", " ")
        for kw, skill_list in overrides.items():
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, query_lower):
                for s_name in skill_list:
                    skill = self.get_skill_by_name(s_name)
                    if skill and skill not in found:
                        if tier is None or getattr(skill, "tier", "T2") == tier:
                            found.append(skill)
        return found

_expert_system_instance = None
def get_expert_system() -> UltronExpertSystem:
    global _expert_system_instance
    if _expert_system_instance is None:
        _expert_system_instance = UltronExpertSystem()
    return _expert_system_instance
