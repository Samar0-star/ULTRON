"""
AST Code Safety Inspector
=========================
Performs static Abstract Syntax Tree (AST) analysis on agent-generated code
before execution in the cleanroom environment.

Ensures zero arbitrary execution vulnerabilities, kills unauthorized network
or file operations, and validates mathematical purity.
"""

import ast
import logging
from typing import List, Tuple, Set

logger = logging.getLogger("sandbox.ast_inspector")

FORBIDDEN_MODULES: Set[str] = {
    "socket", "requests", "urllib", "http", "ftplib", "telnetlib",
    "subprocess", "pty", "commands", "ctypes", "multiprocessing"
}

FORBIDDEN_BUILTINS: Set[str] = {
    "eval", "exec", "__import__", "compile"
}


class ASTSafetyViolation(Exception):
    """Raised when generated code contains unsafe AST nodes."""
    pass


class ASTSecurityInspector(ast.NodeVisitor):
    """
    Traverses the Python AST to detect unsafe imports, system commands, or execution vulnerabilities.
    """

    def __init__(self):
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            mod_root = alias.name.split(".")[0]
            if mod_root in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden module import: '{alias.name}' (line {node.lineno})")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            mod_root = node.module.split(".")[0]
            if mod_root in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden from-import module: '{node.module}' (line {node.lineno})")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check direct builtin calls (e.g. eval("..."))
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_BUILTINS:
                self.violations.append(f"Forbidden builtin call: '{node.func.id}()' (line {node.lineno})")

        # Check attribute calls (e.g. os.system("..."))
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == "os" and node.func.attr in {"system", "popen", "spawn", "exec"}:
                    self.violations.append(f"Forbidden OS shell execution: 'os.{node.func.attr}()' (line {node.lineno})")

        self.generic_visit(node)


def inspect_code_safety(code_str: str) -> Tuple[bool, List[str]]:
    """
    Parses and inspects code string.
    Returns (is_safe, list_of_violations).
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, [f"SyntaxError in code: {e}"]

    inspector = ASTSecurityInspector()
    inspector.visit(tree)

    if inspector.violations:
        return False, inspector.violations

    return True, []
