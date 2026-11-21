import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from backend.experiments.templates.base import TemplateBase
from backend.llm_manager import run_with_fallback, DEEP_RESEARCH_SYNTHESIS_MODEL

logger = logging.getLogger(__name__)

# Registry of all available templates
TEMPLATE_REGISTRY: Dict[str, TemplateBase] = {}

# Templates grouped by domain
DOMAIN_BUNDLES: Dict[str, List[TemplateBase]] = {
    "physics": [],
    "biology": [],
    "chemistry": [],
    "machine_learning": [],
    "computer_science": [],
    "neuroscience": [],
    "medicine": []
}

def register_template(cls: Type[TemplateBase]):
    """Decorator to register a template class."""
    instance = cls()
    TEMPLATE_REGISTRY[instance.name] = instance
    
    domain = instance.domain.lower()
    if domain not in DOMAIN_BUNDLES:
        DOMAIN_BUNDLES[domain] = []
    DOMAIN_BUNDLES[domain].append(instance)
    
    return cls

def get_template(name: str) -> Optional[TemplateBase]:
    """Get a template instance by name."""
    return TEMPLATE_REGISTRY.get(name)

get_template_by_name = get_template

def get_all_templates() -> List[TemplateBase]:
    """Get instances of all registered templates."""
    return list(TEMPLATE_REGISTRY.values())

def get_templates_by_domain(domain: str) -> List[TemplateBase]:
    """Get all templates for a specific domain. Includes comprehensive aliases and cross-compatible bundles."""
    if not domain:
        return []
    d = domain.lower().strip()
    
    # Canonical mapping
    if d in {"biology", "biomedical", "biophysics", "biochemistry", "bio", "genomics", "virology", "protein", "sars", "spike"}:
        canonical = "biology"
    elif d in {"chemistry", "chemical", "cheminformatics"}:
        canonical = "chemistry"
    elif d in {"medicine", "clinical", "pharmacology", "medical"}:
        canonical = "medicine"
    elif d in {"physics", "quantum", "astrophysics", "fluid_dynamics", "omniversal_physics"}:
        canonical = "physics"
    elif d in {"ml", "machine_learning", "ai", "deep_learning"}:
        canonical = "machine_learning"
    elif d in {"cs", "computer_science", "software"}:
        canonical = "computer_science"
    elif d in {"neuroscience", "neuro", "bci"}:
        canonical = "neuroscience"
    elif d in {"materials", "superconductivity"}:
        canonical = "materials"
    elif d in {"climate", "meteorology"}:
        canonical = "climate"
    elif d in {"social_science", "social"}:
        canonical = "social_science"
    else:
        canonical = d

    matched = list(DOMAIN_BUNDLES.get(canonical, []))
    
    # Synergistic domain pairings for empirical sciences
    if canonical == "biology":
        # Include chemistry molecular docking / binding affinity templates if available
        chem_templates = [t for t in DOMAIN_BUNDLES.get("chemistry", []) if "docking" in t.name or "affinity" in t.name or "kinetic" in t.name]
        for t in chem_templates:
            if t not in matched:
                matched.append(t)
    elif canonical == "chemistry":
        bio_templates = [t for t in DOMAIN_BUNDLES.get("biology", []) if "binding" in t.name or "docking" in t.name]
        for t in bio_templates:
            if t not in matched:
                matched.append(t)

    return matched


def find_applicable_templates(hypothesis: Any, top_k: int = 3, use_llm: bool = True, domain: str = None) -> List[TemplateBase]:
    """
    Find templates applicable to a given hypothesis.
    
    Args:
        hypothesis: The hypothesis object or statement
        top_k: Number of templates to return
        use_llm: Whether to use LLM for semantic matching
        domain: Optional domain filter
        
    Returns:
        List of matching templates
    """
    hypothesis_str = str(hypothesis.statement) if hasattr(hypothesis, "statement") else str(hypothesis)
    
    natural_science_domains = {
        "biology", "biomedical", "biophysics", "biochemistry", "bio", "genomics", "virology",
        "protein", "sars", "spike", "chemistry", "chemical", "cheminformatics",
        "physics", "astrophysics", "quantum", "medicine", "clinical", "pharmacology",
        "neuroscience", "materials", "climate"
    }
    computational_domains = {"machine_learning", "ml", "ai", "deep_learning", "computer_science", "cs", "software"}
    
    # Universal general empirical templates (t-test, correlation, regression)
    general_templates = DOMAIN_BUNDLES.get("general", [])

    if domain:
        norm_domain = domain.lower().strip()
        logger.info(f" [TEMPLATES] Applying strict domain filter: {domain}")
        domain_templates = get_templates_by_domain(norm_domain)
        
        # If domain is natural science, strictly block ML and CS
        if norm_domain in natural_science_domains or any(k in norm_domain for k in ["bio", "chem", "phys", "med", "spike", "sars"]):
            # Allowed candidates: domain templates + other natural science templates + general statistical templates
            allowed = list(domain_templates)
            for t in general_templates:
                if t not in allowed:
                    allowed.append(t)
            if not allowed:
                # Fallback to other natural science templates
                allowed = [t for t in get_all_templates() if t.domain.lower() not in computational_domains]
            all_templates = allowed
        elif norm_domain in computational_domains:
            allowed = list(domain_templates)
            for t in general_templates:
                if t not in allowed:
                    allowed.append(t)
            if not allowed:
                allowed = [t for t in get_all_templates() if t.domain.lower() in computational_domains or t.domain.lower() == "general"]
            all_templates = allowed
        else:
            all_templates = domain_templates if domain_templates else get_all_templates()
    else:
        all_templates = get_all_templates()
        
    if not all_templates:
        return []

    # --- TIER 1: HEURISTIC MATCHING ---
    candidates = []
    for template in all_templates:
        score = template.matches_query(hypothesis_str)
        if score > 0.3:
            candidates.append((template, score))
            
    candidates.sort(key=lambda x: x[1], reverse=True)
    candidates = [c[0] for c in candidates]

    # If we don't want to burn LLM tokens, return heuristic matches (even if empty)
    if not use_llm:
        return candidates[:top_k]

    # --- TIER 2: SEMANTIC LLM SELECTION ---
    logger.info(f"Triggering Semantic Template Selection for hypothesis: {hypothesis_str[:100]}...")
    
    # Prepare metadata manifest
    manifest = ""
    for i, t in enumerate(all_templates):
        manifest += f"[{i}] {t.get_metadata_summary()}\n"

    prompt = f"""
+------------------------------------------------------------------------------+
|  SVEL-APEX METHODOLOGY SELECTOR                                            |
+------------------------------------------------------------------------------+

You are the SUPREME SCIENTIFIC ORCHESTRATOR. 
Your task is to select the BEST Ph.D.-level methodology to falsify the following hypothesis.

HYPOTHESIS:
{hypothesis_str}

AVAILABLE TEMPLATES:
{manifest}

### SELECTION CRITERIA:
1. **Domain Alignment**: Does the methodology belong to the correct scientific field?
2. **First-Principles Attack**: Which methodology provides the most aggressive "Annihilation" path?
3. **Data/Resource Fit**: Does the hypothesis provide the variables required by the template?
4. **Complexity vs Rigor**: Prefer high-rigor engines (Apex Sovereign tier).

### OUTPUT FORMAT:
Return ONLY a JSON list of indices in order of relevance (best first).
Example: [4, 1, 12]
"""
    try:
        response = run_with_fallback(
            task="routing",
            prompt=prompt,
            temperature=0.1
        )
        
        from backend.utils.json_repair import repair_json
        indices = repair_json(response.get("text", "[]"))
        
        if isinstance(indices, list):
            selected = []
            for idx in indices:
                if 0 <= idx < len(all_templates):
                    selected.append(all_templates[idx])
            
            if selected:
                logger.info(f"Semantic Gateway selected {len(selected)} templates: {[s.name for s in selected]}")
                return selected[:top_k]
    except Exception as e:
        logger.error(f"Semantic Gateway failed: {e}")

    # Fallback to heuristic if LLM fails
    return candidates[:top_k]

def _build_template_selection_prompt(hypothesis: str, templates: List[TemplateBase]) -> str:
    """Construct the 'Judge' prompt for selecting the best template."""
    
    template_list = ""
    for t in templates:
        template_list += f"""
---
ID: {t.name}
TITLE: {t.title}
DOMAIN: {t.domain}
DESCRIPTION: {t.description}
SUITABLE FOR: {', '.join(t.suitable_for)}
---
"""

    return f"""
+------------------------------------------------------------------------------+
|  SVEL TEMPLATE JUDGE (RELENTLESS DISCOVERY MODE)                           |
+------------------------------------------------------------------------------+

You are an ELITE SCIENTIFIC ADJUDICATOR. Your task is to select the SINGLE BEST scientific experiment template for the given hypothesis.

# RESEARCH OBJECTIVE / HYPOTHESIS:
"{hypothesis}"

# AVAILABLE TEMPLATES:
{template_list}

# SELECTION RULES:
1. **Match the DNA**: Look for templates whose "SUITABLE FOR" or "DESCRIPTION" matches the core variables of the hypothesis.
2. **Prefer Specificity**: If a hypothesis is about "optimizers" or "gradients", prefer a Machine Learning template over a general Computer Science one.
3. **Discovery Mandate**: In DISCOVERY mode, we seek to FALSIFY. Select templates that offer rigorous, adversarial testing.
4. **Fallback**: If NO template is even 20% relevant, you MUST output "NONE".

# OUTPUT:
Output ONLY the ID of the selected template. Example: "ml_annihilator_apex"
If no template fits, output: "NONE"

You must be PRECISE. Do not select a template if it is not a strong fit.
"""

def search_templates(query: str, top_k: int = 5) -> List[TemplateBase]:
    """Search templates by query string."""
    scored = []
    for template in get_all_templates():
        score = template.matches_query(query)
        if score > 0.1:
            scored.append((template, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in scored[:top_k]]

def get_registry_stats() -> Dict[str, Any]:
    """Get statistics about the template registry."""
    return {
        "total_templates": len(TEMPLATE_REGISTRY),
        "domains": list(DOMAIN_BUNDLES.keys()),
        "templates_per_domain": {k: len(v) for k, v in DOMAIN_BUNDLES.items() if v},
        "template_names": list(TEMPLATE_REGISTRY.keys())
    }

def _discover_templates():
    """Auto-discover templates from top-level modules and subdirectories."""
    templates_dir = Path(__file__).parent
    
    # 1. Discover top-level template modules (e.g., data_analysis.py)
    for py_file in templates_dir.glob("*.py"):
        if py_file.name.startswith("_") or py_file.stem in {"base", "base_template", "falsification_kernel_base"}:
            continue
        try:
            module_name = f"backend.experiments.templates.{py_file.stem}"
            importlib.import_module(module_name)
            logger.info(f"Loaded top-level template module: {py_file.stem}")
        except Exception as e:
            logger.critical(f"FATAL TEMPLATE LOAD ERROR in {py_file.stem}: {e}")
            import traceback
            logger.critical(traceback.format_exc())

    # 2. Discover domain subdirectories and all their Python modules
    for domain_dir in templates_dir.iterdir():
        if domain_dir.is_dir() and not domain_dir.name.startswith("_") and not domain_dir.name.startswith("."):
            try:
                module_name = f"backend.experiments.templates.{domain_dir.name}"
                importlib.import_module(module_name)
                logger.info(f"Loaded templates from domain package: {domain_dir.name}")
            except Exception as e:
                logger.critical(f"FATAL TEMPLATE LOAD ERROR in domain {domain_dir.name}: {e}")
                import traceback
                logger.critical(traceback.format_exc())

            for sub_file in domain_dir.glob("*.py"):
                if sub_file.name.startswith("_"):
                    continue
                try:
                    sub_module_name = f"backend.experiments.templates.{domain_dir.name}.{sub_file.stem}"
                    importlib.import_module(sub_module_name)
                except Exception as e:
                    logger.warning(f"Template sub-module load warning in {sub_module_name}: {e}")

# Auto-discover on import
try:
    _discover_templates()
except Exception as e:
    logger.warning(f"Template auto-discovery failed: {e}")
