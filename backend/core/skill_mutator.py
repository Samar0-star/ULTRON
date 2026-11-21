"""
Dynamic Skill Mutation ("The Evolve")
=====================================
When the swarm encounters a problem that requires a skill SVEL doesn't have,
it generates a new skill file and adds it to the skill library.

SAFETY FEATURES:
1. Quarantine Directory: New skills go to `skills/_quarantine/`, NOT active skills
2. Syntax Linting: All generated code is validated via py_compile
3. Security Scanning: Blocks dangerous imports (os.system, subprocess, eval, exec)
4. Manual Approval: Skills stay quarantined until explicitly approved
5. Version Control: Each skill has metadata for tracking and rollback
"""

import os
import re
import json
import logging
import hashlib
import py_compile
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("avon.skill_mutator")

import ast

# Dangerous modules/functions blacklist
BLACKLIST_MODULES = {
    'os', 'subprocess', 'sys', 'shutil', 'pickle', 
    'socket', 'urllib', 'requests', 'http', 'ftplib',
    'telnetlib', 'xmlrpc', 'importlib', 'code'
}

BLACKLIST_FUNCTIONS = {
    'eval', 'exec', 'compile', 'open', 'input', 
    '__import__', 'globals', 'locals', 'vars',
    'breakpoint', 'help', 'exit', 'quit'
}

BLACKLIST_ATTRIBUTES = {
    '__builtins__', '__dict__', '__class__', '__bases__',
    '__subclasses__', '__import__', '__loader__'
}

class SecurityValidator(ast.NodeVisitor):
    """
    AST-based security validator.
    Inspects code structure to ensure no blacklist items are used.
    """
    def __init__(self):
        self.errors = []
        self.safe_modules = {'math', 'json', 'datetime', 'random', 're', 'collections', 'itertools', 'functools', 'typing', 'logging'}

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split('.')[0] in BLACKLIST_MODULES:
                self.errors.append(f"SECURITY: Import of forbidden module '{alias.name}' detected on line {node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split('.')[0] in BLACKLIST_MODULES:
            self.errors.append(f"SECURITY: From-import of forbidden module '{node.module}' detected on line {node.lineno}")
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check function calls like eval(), exec(), open()
        if isinstance(node.func, ast.Name):
            if node.func.id in BLACKLIST_FUNCTIONS:
                self.errors.append(f"SECURITY: Call to forbidden function '{node.func.id}()' detected on line {node.lineno}")
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        # Check attribute access like obj.__class__ or os.system
        if node.attr in BLACKLIST_ATTRIBUTES:
             self.errors.append(f"SECURITY: Access to forbidden attribute '{node.attr}' detected on line {node.lineno}")
        self.generic_visit(node)

# Base paths
SKILLS_ROOT = Path(__file__).parent.parent.parent / "skills"
QUARANTINE_DIR = SKILLS_ROOT / "_quarantine"
ACTIVE_DIR = SKILLS_ROOT / "active"
METADATA_FILE = QUARANTINE_DIR / "_manifest.json"


class SkillMutator:
    """
    Generates new skills dynamically when the swarm encounters gaps.
    All generated skills go through a safety validation pipeline.
    """
    
    def __init__(self, llm_manager=None):
        """
        Initialize the SkillMutator.
        
        Args:
            mission_id: ID for the user (for directory sharding)
            llm_manager: Optional LLM manager for generating skill code.
        """
        
        self.llm_manager = llm_manager
        
        # Isolated Mission Paths
        self.user_root = SKILLS_ROOT / "mission_skills"
        self.quarantine_dir = self.user_root / "_quarantine"
        self.active_dir = self.user_root / "active"
        self.manifest_path = self.user_root / "_manifest.json"
        
        # Ensure directories exist
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create manifest
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load the quarantine manifest."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load manifest: {e}")
        return {"skills": [], "version": 1}
    
    def _save_manifest(self):
        """Save the quarantine manifest."""
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(self.manifest, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
    
    def generate_skill(self, skill_name: str, description: str, domain: str = "general") -> Dict[str, Any]:
        """
        Generate a new skill based on description.
        
        Args:
            skill_name: Name for the new skill (e.g., "mass_spec_analyzer")
            description: What the skill should do
            domain: Domain category (e.g., "chemistry", "biology", "physics")
            
        Returns:
            Dict with status, path, and any errors.
        """
        logger.info(f" Generating new skill: {skill_name}")
        
        # Normalize skill name
        skill_name = re.sub(r'[^a-z0-9_]', '_', skill_name.lower())
        
        # Generate code via LLM
        prompt = f"""
You are a Python skill generator for a scientific AI research system.

TASK: Generate a Python skill module for: {description}

DOMAIN: {domain}

REQUIREMENTS:
1. Create a single Python file with a main class or functions
2. Include comprehensive docstrings
3. Use type hints
4. Include example usage in if __name__ == "__main__":
5. DO NOT use any dangerous operations (no os.system, subprocess, eval, exec)
6. DO NOT make network requests
7. DO NOT write to files outside of explicit parameters
8. Focus on DATA ANALYSIS and COMPUTATION only

TEMPLATE:
```python
\"\"\"
{skill_name.replace('_', ' ').title()} Skill
Generated by SVEL SkillMutator
Domain: {domain}
Description: {description}
\"\"\"

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("avon.skills.{skill_name}")


class {skill_name.title().replace('_', '')}Skill:
    \"\"\"
    [Your docstring here]
    \"\"\"
    
    def __init__(self):
        pass
    
    def analyze(self, data: Any) -> Dict[str, Any]:
        \"\"\"Main analysis method.\"\"\"
        # Your implementation here
        pass


def run_skill(input_data: Any) -> Dict[str, Any]:
    \"\"\"Entry point for skill execution.\"\"\"
    skill = {skill_name.title().replace('_', '')}Skill()
    return skill.analyze(input_data)


if __name__ == "__main__":
    # Example usage
    result = run_skill({{}})
    print(result)
```

OUTPUT: Return ONLY the Python code, no markdown.
"""
        
        try:
            if self.llm_manager:
                response = self.llm_manager.run(prompt, temperature=0.3, max_tokens_override=None)
                code = response.get("text", "")
            else:
                # Use module-level run_llm
                from backend.llm_manager import run_llm, CODE_GENERATION_MODEL
                response = run_llm(prompt, model=CODE_GENERATION_MODEL, timeout=120)
                code = response if isinstance(response, str) else response.get("text", "")
            
            # Clean up code (remove markdown fences if present)
            code = re.sub(r'^```python\s*', '', code, flags=re.MULTILINE)
            code = re.sub(r'^```\s*$', '', code, flags=re.MULTILINE)
            code = code.strip()
            
            if not code:
                return {"status": "ERROR", "reason": "LLM returned empty code"}
            
            # Validate the generated code
            validation = self.validate_skill(code, skill_name)
            
            if not validation["valid"]:
                return {
                    "status": "REJECTED",
                    "reason": validation["errors"],
                    "code_preview": code[:500]
                }
            
            # Save to quarantine
            skill_path = self.quarantine_dir / f"{skill_name}.py"
            with open(skill_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Add to manifest
            skill_entry = {
                "name": skill_name,
                "domain": domain,
                "description": description,
                "path": str(skill_path),
                "created_at": datetime.now().isoformat(),
                "status": "QUARANTINED",
                "hash": hashlib.sha256(code.encode()).hexdigest()[:16],
                "validation": validation
            }
            self.manifest["skills"].append(skill_entry)
            self._save_manifest()
            
            logger.info(f" Skill generated and quarantined: {skill_path}")
            
            return {
                "status": "QUARANTINED",
                "path": str(skill_path),
                "skill_name": skill_name,
                "validation": validation,
                "message": f"Skill '{skill_name}' generated and awaiting approval in quarantine."
            }
            
        except Exception as e:
            logger.error(f"Skill generation failed: {e}")
            return {"status": "ERROR", "reason": str(e)}
    
    def validate_skill(self, code: str, skill_name: str) -> Dict[str, Any]:
        """
        Validate generated skill code for safety and correctness.
        Uses AST static analysis to block dangerous operations.
        
        Args:
            code: The Python code to validate
            skill_name: Name of the skill
            
        Returns:
            Dict with valid flag, errors, and warnings.
        """
        errors = []
        warnings = []
        
        # 1. AST Security Scan: Check for dangerous imports and calls
        try:
            tree = ast.parse(code)
            validator = SecurityValidator()
            validator.visit(tree)
            if validator.errors:
                errors.extend(validator.errors)
        except SyntaxError as e:
            errors.append(f"SYNTAX: Code contains syntax errors: {e}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "code_length": len(code)
            }
        except Exception as e:
            errors.append(f"VALIDATION ERROR: Failed to parse code: {e}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "code_length": len(code)
            }
        
        # 2. Syntax Check: Try to compile (Double check)
        temp_path = self.quarantine_dir / f"_temp_{skill_name}.py"
        try:
            # Write to temp file for compilation
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            py_compile.compile(str(temp_path), doraise=True)
            
        except py_compile.PyCompileError as e:
            errors.append(f"SYNTAX: {str(e)}")
        except Exception as e:
            warnings.append(f"Could not verify syntax: {e}")
        finally:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
        
        # 3. Structure Check: Must have docstring
        if '"""' not in code and "'''" not in code:
            warnings.append("STYLE: No docstring found")
        
        # 4. Size Check: Reasonable file size
        if len(code) < 100:
            warnings.append("SIZE: Code is suspiciously short")
        if len(code) > 50000:
            errors.append("SIZE: Code is too large (>50KB)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "code_length": len(code)
        }
    
    def approve_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        Approve a quarantined skill and move it to active directory.
        
        Args:
            skill_name: Name of the skill to approve
            
        Returns:
            Dict with status and new path.
        """
        # Find skill in manifest
        skill_entry = None
        for skill in self.manifest["skills"]:
            if skill["name"] == skill_name:
                skill_entry = skill
                break
        
        if not skill_entry:
            return {"status": "ERROR", "reason": f"Skill '{skill_name}' not found in quarantine"}
        
        if skill_entry["status"] != "QUARANTINED":
            return {"status": "ERROR", "reason": f"Skill is not in QUARANTINED status"}
        
        # Move to active
        src = Path(skill_entry["path"])
        dst = self.active_dir / f"{skill_name}.py"
        
        if not src.exists():
            return {"status": "ERROR", "reason": "Source file missing"}
        
        try:
            # Read and write (move)
            with open(src, "r", encoding="utf-8") as f:
                code = f.read()
            with open(dst, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Remove from quarantine
            src.unlink()
            
            # Update manifest
            skill_entry["status"] = "ACTIVE"
            skill_entry["path"] = str(dst)
            skill_entry["approved_at"] = datetime.now().isoformat()
            self._save_manifest()
            
            logger.info(f" Skill approved and activated: {skill_name}")
            
            return {
                "status": "ACTIVE",
                "path": str(dst),
                "message": f"Skill '{skill_name}' is now active!"
            }
            
        except Exception as e:
            return {"status": "ERROR", "reason": str(e)}
    
    def reject_skill(self, skill_name: str, reason: str = "") -> Dict[str, Any]:
        """
        Reject and delete a quarantined skill.
        
        Args:
            skill_name: Name of the skill to reject
            reason: Reason for rejection
            
        Returns:
            Dict with status.
        """
        # Find skill in manifest
        skill_entry = None
        for i, skill in enumerate(self.manifest["skills"]):
            if skill["name"] == skill_name:
                skill_entry = skill
                skill_index = i
                break
        
        if not skill_entry:
            return {"status": "ERROR", "reason": f"Skill '{skill_name}' not found"}
        
        # Delete file
        src = Path(skill_entry["path"])
        if src.exists():
            src.unlink()
        
        # Remove from manifest
        self.manifest["skills"].pop(skill_index)
        self._save_manifest()
        
        logger.info(f" Skill rejected and deleted: {skill_name}")
        
        return {
            "status": "REJECTED",
            "message": f"Skill '{skill_name}' rejected: {reason}"
        }
    
    def list_quarantined(self) -> List[Dict[str, Any]]:
        """List all skills in quarantine."""
        return [s for s in self.manifest["skills"] if s.get("status") == "QUARANTINED"]
    
    def list_active(self) -> List[Dict[str, Any]]:
        """List all active skills."""
        return [s for s in self.manifest["skills"] if s.get("status") == "ACTIVE"]
    
    def request_skill(self, problem_description: str) -> Dict[str, Any]:
        """
        High-level method: Called when the swarm encounters a skill gap.
        Generates a skill name and description, then generates the skill.
        
        Args:
            problem_description: What the swarm couldn't do
            
        Returns:
            Generation result.
        """
        # Extract skill name from problem
        skill_name = re.sub(r'[^a-z0-9]', '_', problem_description.lower())[:30]
        skill_name = re.sub(r'_+', '_', skill_name).strip('_')
        
        if not skill_name:
            skill_name = f"custom_skill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Determine domain (simple heuristics)
        domain = "other_scientific_domain"
        domain_keywords = {
            "chemistry": ["chemical", "molecule", "reaction", "compound", "synthesis", "atom"],
            "biology": ["gene", "protein", "cell", "organism", "dna", "rna", "enzyme", "pdb", "binding"],
            "physics": ["quantum", "particle", "wave", "energy", "force", "field", "dynamics", "equation"],
            "medicine": ["drug", "disease", "patient", "treatment", "clinical", "pharmacology"],
            "machine_learning": ["data", "analysis", "statistics", "neural", "model", "training", "epoch"],
        }
        
        for d, keywords in domain_keywords.items():
            if any(kw in problem_description.lower() for kw in keywords):
                domain = d
                break
        
        logger.info(f" Skill gap detected: {problem_description}")
        logger.info(f" Generating skill: {skill_name} (Domain: {domain})")
        
        return self.generate_skill(skill_name, problem_description, domain)


# Singleton instances per user
_mutator_instances: Dict[str, SkillMutator] = {}


def get_skill_mutator(mission_id: str = "default") -> SkillMutator:
    """Get or create the user-scoped SkillMutator instance."""
    global _mutator_instances
    if mission_id not in _mutator_instances:
        _mutator_instances[mission_id] = SkillMutator()
    return _mutator_instances[mission_id]


if __name__ == "__main__":
    # Test the SkillMutator
    print("=" * 50)
    print("SKILL MUTATOR TEST")
    print("=" * 50)
    
    mutator = SkillMutator()
    
    # Test validation
    test_code = '''
"""Test skill."""
def hello():
    return "Hello"
'''
    
    validation = mutator.validate_skill(test_code, "test_skill")
    print(f"Validation: {validation}")
    
    print("\nQuarantined skills:", mutator.list_quarantined())
    print("Active skills:", mutator.list_active())
