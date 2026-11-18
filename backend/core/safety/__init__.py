"""
Safety Module for Avon-2 Deep Mode
====================================

Provides operation controls, human approval gates, and budget limits.
"""

from backend.core.safety.operation_guard import (
    OperationGuard,
    ApprovalRequest,
    ApprovalResult,
    request_approval
)
from backend.core.safety.code_scanner import (
    CodeScanner,
    ScanResult,
    scan_code
)

__all__ = [
    "OperationGuard",
    "ApprovalRequest",
    "ApprovalResult",
    "request_approval",
    "CodeScanner",
    "ScanResult",
    "scan_code"
]
