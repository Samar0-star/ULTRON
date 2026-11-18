"""
Execution Cage & Sandbox
========================
Provides hermetic Python execution for experiment validation.
Integrates static AST inspection and runtime network lockdowns.
"""

from typing import Dict, Any, Optional
from backend.execution.sandbox import GodModeSandbox, SandboxResult
from backend.sandbox.ast_inspector import inspect_code_safety, ASTSafetyViolation


class CleanroomExecutionCage:
    """
    Two-stage deterministic verification cage for generated experiment scripts.
    1. Static AST Inspection (pre-run)
    2. Hermetic execution in GodModeSandbox (runtime)
    """

    def __init__(self, timeout_seconds: int = 15):
        self.timeout = timeout_seconds
        self.sandbox = GodModeSandbox()

    def execute_experiment(self, code_str: str, session_id: str = "default_session") -> SandboxResult:
        # Stage 1: Static AST Safety Check
        is_safe, violations = inspect_code_safety(code_str)
        if not is_safe:
            raise ASTSafetyViolation(f"AST Safety Cage blocked execution: {'; '.join(violations)}")

        # Stage 2: Runtime Sandbox Execution
        return self.sandbox.execute(code_str, session_id=session_id)


__all__ = ["CleanroomExecutionCage", "SandboxResult", "inspect_code_safety"]
