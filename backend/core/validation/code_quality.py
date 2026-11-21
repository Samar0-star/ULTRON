"""
SVEL Code Quality Validator - Runtime Bug Prevention
=====================================================
Pre-execution validation to catch common LLM coding errors.
"""

import ast
import re
from typing import Tuple, List


class CodeQualityValidator:
    """
    [GODZILLA V62] Code Quality Gate
    Catches common LLM coding errors before execution.
    """
    
    COMMON_BUGS = [
        # Pattern: np.in1d with boolean indexing issues
        {
            'pattern': r'\[~\s*np\.in1d',
            'message': 'BUG: np.in1d with ~ operator often causes boolean indexing mismatches. Use np.isin() with proper shape handling.',
            'severity': 'error'
        },
        # Pattern: Boolean index size mismatch
        {
            'pattern': r'\[.*~~.*\]',
            'message': 'WARNING: Double negation ~~ in indexing may cause issues.',
            'severity': 'warning'
        },
        # Pattern: Deprecated numpy functions
        {
            'pattern': r'np\.in1d\s*\(',
            'message': 'DEPRECATED: np.in1d is deprecated. Use np.isin() instead.',
            'severity': 'error'
        },
        # Pattern: Concatenation without axis
        {
            'pattern': r'np\.concatenate\s*\([^)]*\)\s*\[',
            'message': 'WARNING: Using concatenate result directly in indexing without storing in variable is error-prone.',
            'severity': 'warning'
        },
        # Pattern: Random choice with potential size mismatch
        {
            'pattern': r'np\.random\.choice\s*\([^)]*replace=False[^)]*\)',
            'message': 'CHECK: np.random.choice with replace=False and size > population will fail.',
            'severity': 'warning'
        },
        # Pattern: Division by zero risk
        {
            'pattern': r'/\s*len\s*\(',
            'message': 'WARNING: Division by len() without zero check may cause ZeroDivisionError.',
            'severity': 'warning'
        },
        # Pattern: Unclosed file (common LLM error)
        {
            'pattern': r'open\s*\([^)]+\)\s*\.',
            'message': 'WARNING: Using open() without context manager (with statement) may leak file handles.',
            'severity': 'warning'
        },
        # Pattern: Mutable default arguments
        {
            'pattern': r'def\s+\w+\s*\([^)]*=\s*\[\s*\]',
            'message': 'BUG: Mutable default argument (list) will persist across calls. Use None default.',
            'severity': 'error'
        },
        # Pattern: Bare except
        {
            'pattern': r'except\s*:\s*$',
            'message': 'WARNING: Bare except catches SystemExit and KeyboardInterrupt. Use except Exception:.',
            'severity': 'warning'
        },
        # Pattern: == None instead of is None
        {
            'pattern': r'==\s*None',
            'message': 'STYLE: Use "is None" instead of "== None".',
            'severity': 'info'
        },
        # Pattern: Hardcoded input paths in pd.read_csv / PDBParser (allow output .to_csv("raw_data.csv"))
        {
            'pattern': r'pd\.read_csv\s*\(\s*["\'][^"\']*\.csv["\']',
            'message': 'ERROR: Hardcoded CSV path in pd.read_csv() detected. Must use DATA_* variables.',
            'severity': 'error'
        },
        {
            'pattern': r'get_structure\s*\([^,]+,\s*["\'][^"\']*\.pdb["\']',
            'message': 'ERROR: Hardcoded PDB path in get_structure() detected. Must use DATA_* variables.',
            'severity': 'error'
        }
    ]
    
    @classmethod
    def validate_code(cls, code: str) -> Tuple[bool, List[str]]:
        """
        Validate code for common bugs.
        Returns: (is_valid, list of issues)
        """
        issues = []
        
        for bug in cls.COMMON_BUGS:
            if re.search(bug['pattern'], code):
                msg = f"[{bug['severity'].upper()}] {bug['message']}"
                issues.append(msg)
        
        # AST-based checks
        try:
            tree = ast.parse(code)
            cls._check_ast(tree, issues)
        except SyntaxError as e:
            issues.append(f"[ERROR] Syntax error: {e}")
            return False, issues
        
        errors = [i for i in issues if i.startswith('[ERROR]')]
        return len(errors) == 0, issues
    
    @classmethod
    def _check_ast(cls, tree: ast.AST, issues: List[str]):
        """AST-based checks for complex patterns."""
        for node in ast.walk(tree):
            # Check for unused variables
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Simple check - could be enhanced
                        pass
            
            # Check for dangerous eval/exec
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('eval', 'exec'):
                        issues.append("[ERROR] Use of eval/exec is forbidden for security reasons.")


def validate_code_quality(code: str) -> Tuple[bool, List[str]]:
    """Convenience function."""
    return CodeQualityValidator.validate_code(code)
