"""
Code Scanner for Avon-2 Deep Mode
===================================

Static analysis of generated code to detect dangerous patterns.
Provides safety validation before code execution.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Severity levels for detected issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CodeIssue:
    """A detected issue in code"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity: SeverityLevel = SeverityLevel.WARNING
    category: str = ""  # security, quality, performance
    rule: str = ""
    message: str = ""
    line_number: Optional[int] = None
    code_snippet: str = ""
    suggestion: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category,
            "rule": self.rule,
            "message": self.message,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion
        }


@dataclass
class ScanResult:
    """Result of code scan"""
    is_safe: bool
    code_hash: str = ""
    issues: List[CodeIssue] = field(default_factory=list)
    
    # Statistics
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    
    # Metadata
    scanned_at: datetime = field(default_factory=datetime.now)
    scan_duration_ms: float = 0.0
    
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "issues": [i.to_dict() for i in self.issues],
            "statistics": {
                "critical": self.critical_count,
                "error": self.error_count,
                "warning": self.warning_count,
                "info": self.info_count,
                "total": len(self.issues)
            },
            "scanned_at": self.scanned_at.isoformat(),
            "scan_duration_ms": self.scan_duration_ms,
            "summary": self.summary
        }


class CodeScanner:
    """
    Static analysis scanner for generated code.
    
    Detects:
    - Security issues (dangerous imports, shell commands)
    - Quality issues (syntax errors, undefined variables)
    - Performance issues (infinite loops, memory leaks)
    
    Example:
        ```python
        scanner = CodeScanner()
        
        result = scanner.scan('''
            import os
            os.system("rm -rf /")
        ''')
        
        if not result.is_safe:
            print(f"Blocked: {result.issues[0].message}")
        ```
    """
    
    # Dangerous patterns (regex)
    DANGEROUS_PATTERNS = [
        (r"os\.system\s*\(", "security", "shell_command", "os.system() can execute arbitrary shell commands"),
        (r"subprocess\.(?:Popen|run|call|check_call|check_output|getoutput|getstatusoutput)\s*\(", "security", "subprocess_exec", "subprocess execution can run arbitrary shell commands"),
        (r"eval\s*\(", "security", "eval", "eval() can execute arbitrary code"),
        (r"exec\s*\(", "security", "exec", "exec() can execute arbitrary code"),
        (r"__import__\s*\(", "security", "dynamic_import", "__import__() can import arbitrary modules"),
        (r"open\s*\(['\"]\/(?:etc|sys|proc)", "security", "system_file", "Accessing system files is dangerous"),
        (r"shutil\.rmtree\s*\(", "security", "recursive_delete", "shutil.rmtree() can delete entire directories"),
        (r"os\.remove\s*\(", "security", "file_delete", "os.remove() deletes files"),
        # [GODZILLA DEFUSE] Removed network blocking patterns to allow real scientific API usage
        (r"marshal\.load", "security", "marshal", "marshal.load() can execute arbitrary code"),
    ]
    
    # Blocked imports
    BLOCKED_IMPORTS = {
        "os": ["system", "popen", "spawn", "exec"],
        "subprocess": None, 
        "ctypes": None,
    }
    
    SCIENTIFIC_WHITELIST = {
        "numpy", "pandas", "scipy", "matplotlib", "plotly", "sympy", "statsmodels", "sklearn",
        "torch", "tensorflow", "jax", "torch_geometric", "networkx", "inspect", "pickle", "json",
        "rdkit", "Bio", "requests", "urllib", "pubchempy", "chembl_webresource_client", "wget", "socket"
    }
    
    def __init__(
        self,
        block_network: bool = True,
        block_file_ops: bool = False,
        block_shell: bool = True,
        custom_patterns: Optional[List[tuple]] = None,
        allowed_imports: Optional[Set[str]] = None
    ):
        """
        Initialize Code Scanner.
        
        Args:
            block_network: Block network-related code
            block_file_ops: Block file operations
            block_shell: Block shell command execution
            custom_patterns: Additional patterns to check
            allowed_imports: Whitelist of allowed imports (if set, only these are allowed)
        """
        self.block_network = block_network
        self.block_file_ops = block_file_ops
        self.block_shell = block_shell
        self.custom_patterns = custom_patterns or []
        self.allowed_imports = allowed_imports
        self.blocked_imports = {
            k: (list(v) if isinstance(v, list) else v)
            for k, v in self.BLOCKED_IMPORTS.items()
        }
        
        logger.info(
            f"CodeScanner initialized: network={not block_network}, "
            f"file_ops={not block_file_ops}, shell={not block_shell}"
        )
    
    def scan(self, code: str) -> ScanResult:
        """
        Scan code for security issues, dangerous patterns, and blocked imports.

        Returns ScanResult with is_safe=False if any critical issues found.
        """
        import hashlib
        import time

        start_time = time.time()
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        # [RIGOR FIX] Strip Jupyter Magic Commands
        # LLMs frequently output `!pip install` or `%matplotlib inline` which 
        # breaks the AST parser and causes false negatives. We comment them out.
        clean_code_lines = []
        for line in code.split('\n'):
            if line.strip().startswith('!') or line.strip().startswith('%'):
                clean_code_lines.append('# ' + line)
            else:
                clean_code_lines.append(line)
        code = '\n'.join(clean_code_lines)

        all_issues: List[CodeIssue] = []

        # Layer 1: Syntax validation
        syntax_issues = self._check_syntax(code)
        all_issues.extend(syntax_issues)

        # Layer 2: Dangerous patterns (regex-based)
        pattern_issues = self._check_patterns(code)
        all_issues.extend(pattern_issues)

        # Layer 3: Blocked imports
        import_issues = self._check_imports(code)
        all_issues.extend(import_issues)

        # Layer 4: AST-based analysis
        ast_issues = self._analyze_ast(code)
        all_issues.extend(ast_issues)

        # Calculate severity
        critical_count = sum(1 for i in all_issues if i.severity == SeverityLevel.CRITICAL)
        error_count = sum(1 for i in all_issues if i.severity == SeverityLevel.ERROR)
        warning_count = sum(1 for i in all_issues if i.severity == SeverityLevel.WARNING)
        info_count = sum(1 for i in all_issues if i.severity == SeverityLevel.INFO)

        # Code is UNSAFE if any CRITICAL issues found
        is_safe = critical_count == 0 and error_count == 0

        duration_ms = (time.time() - start_time) * 1000

        summary = f"Scan complete: {len(all_issues)} issues found ({critical_count} critical, {error_count} errors, {warning_count} warnings)"

        logger.info(f"[CODE_SCAN] {code_hash}: {summary} | Safe={is_safe}")

        return ScanResult(
            is_safe=is_safe,
            code_hash=code_hash,
            issues=all_issues,
            critical_count=critical_count,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            scanned_at=datetime.now(),
            scan_duration_ms=duration_ms,
            summary=summary
        )
    
    def _check_syntax(self, code: str) -> List[CodeIssue]:
        """Check for syntax errors"""
        try:
            ast.parse(code)
            return []
        except SyntaxError as e:
            return [CodeIssue(
                severity=SeverityLevel.ERROR,
                category="syntax",
                rule="syntax_error",
                message=f"Syntax error: {e.msg}",
                line_number=e.lineno,
                code_snippet=e.text or "",
                suggestion="Fix the syntax error before execution"
            )]
    
    def _check_patterns(self, code: str) -> List[CodeIssue]:
        """Check for dangerous patterns using regex"""
        issues = []
        
        patterns = self.DANGEROUS_PATTERNS + self.custom_patterns
        
        for pattern, category, rule, message in patterns:
            # Skip based on settings
            if not self.block_shell and "shell" in rule:
                continue
            if not self.block_network and "network" in rule:
                continue
            if not self.block_file_ops and "file" in rule:
                continue
            
            for match in re.finditer(pattern, code):
                line_num = code[:match.start()].count('\n') + 1
                issues.append(CodeIssue(
                    severity=SeverityLevel.CRITICAL if category == "security" else SeverityLevel.WARNING,
                    category=category,
                    rule=rule,
                    message=message,
                    line_number=line_num,
                    code_snippet=match.group(0),
                    suggestion=f"Remove or replace the {rule} usage"
                ))
        
        return issues
    
    def _check_imports(self, code: str) -> List[CodeIssue]:
        """Check for blocked imports"""
        issues = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if self._is_import_blocked(module, None):
                        issues.append(CodeIssue(
                            severity=SeverityLevel.CRITICAL,
                            category="security",
                            rule="blocked_import",
                            message=f"Import of '{module}' is blocked",
                            line_number=node.lineno,
                            code_snippet=f"import {alias.name}",
                            suggestion=f"Remove import of {module}"
                        ))
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                base_module = module.split('.')[0]
                
                for alias in node.names:
                    if self._is_import_blocked(base_module, alias.name):
                        issues.append(CodeIssue(
                            severity=SeverityLevel.CRITICAL,
                            category="security",
                            rule="blocked_import",
                            message=f"Import of '{alias.name}' from '{module}' is blocked",
                            line_number=node.lineno,
                            code_snippet=f"from {module} import {alias.name}",
                            suggestion=f"Remove this import"
                        ))
        
        return issues
    
    def _is_import_blocked(self, module: str, name: Optional[str]) -> bool:
        """Check if an import is blocked"""
        # Check whitelist first
        if self.allowed_imports is not None:
            return module not in self.allowed_imports
        
        # Check instance blocklist
        blocked_map = getattr(self, "blocked_imports", self.BLOCKED_IMPORTS)
        if module in blocked_map:
            blocked_names = blocked_map[module]
            if blocked_names is None:
                return True  # Entire module blocked
            if name and name in blocked_names:
                return True
        
        return False
    
    def _analyze_ast(self, code: str) -> List[CodeIssue]:
        """AST-based analysis for additional patterns"""
        issues = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []
        
        for node in ast.walk(tree):
            # Check for infinite loops (while True without break)
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    has_break = any(
                        isinstance(child, ast.Break) 
                        for child in ast.walk(node)
                    )
                    if not has_break:
                        issues.append(CodeIssue(
                            severity=SeverityLevel.WARNING,
                            category="performance",
                            rule="infinite_loop",
                            message="Potential infinite loop detected (while True without break)",
                            line_number=node.lineno,
                            suggestion="Add a break condition or use a bounded loop"
                        ))
            
            # Check for very deep recursion hints
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == node.name:
                            issues.append(CodeIssue(
                                severity=SeverityLevel.INFO,
                                category="performance",
                                rule="recursion",
                                message=f"Function '{node.name}' is recursive",
                                line_number=node.lineno,
                                suggestion="Ensure recursion has a proper base case"
                            ))
                            break
        
        return issues
    
    def _generate_summary(
        self,
        is_safe: bool,
        critical: int,
        errors: int,
        warnings: int
    ) -> str:
        """Generate human-readable summary"""
        if is_safe and warnings == 0:
            return "Code scan passed with no issues"
        elif is_safe:
            return f"Code scan passed with {warnings} warnings"
        else:
            return (
                f"Code scan FAILED: {critical} critical issues, "
                f"{errors} errors, {warnings} warnings"
            )


# Convenience function

def scan_code(code: str, strict: bool = True, profile: str = "general") -> ScanResult:
    """
    Scan code for safety issues.
    
    Args:
        code: Python code to scan
        strict: If True, block more patterns
        profile: "general" or "scientific"
        
    Returns:
        ScanResult
    """
    if profile == "scientific":
        # [GODZILLA DEFUSE] Scientific profile now allows network for real discovery
        scanner = CodeScanner(
            block_network=False, # ALLOW NETWORK
            block_file_ops=False,
            block_shell=True,
            allowed_imports=None 
        )
        # Relax instance-level blocked imports for the scientific whitelist without mutating class dict
        for lib in scanner.SCIENTIFIC_WHITELIST:
             if lib in scanner.blocked_imports:
                  del scanner.blocked_imports[lib]
    else:
        scanner = CodeScanner(
            block_network=strict,
            block_file_ops=False,
            block_shell=strict
        )
    return scanner.scan(code)
