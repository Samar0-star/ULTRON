"""
Operation Guard for Avon-2
==========================

Runtime interceptor that verifies LLM instructions against a local "Rules of Engagement" DB.
Prevents high-risk operations even if they pass static analysis.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    HIGH_RISK = "high_risk"
    FORBIDDEN = "forbidden"

class OperationGuard:
    """
    Dynamic Safety Enforcement.
    
    Checks specific operation signatures against a policy.
    Unlike CodeScanner (static), this can include runtime context rules.
    """
    
    FORBIDDEN_KEYWORDS = [
        "rm -rf", "mkfs", "dd if=", ":(){ :|:& };:", # fork bomb
        "wget http", "curl http", # unencrypted download
        "chmod 777", "chown root",
        ".bashrc", ".profile", "/etc/shadow",
        "bitcoin", "monero", "miner" # crypto mining
    ]
    
    SENSITIVE_ENV_VARS = {
        "OPENAI_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
        "DATABASE_URL", "POSTGRES_PASSWORD", "S2_API_KEY"
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def check_operation(self, code_snippet: str, context: str = "") -> Dict[str, Any]:
        """
        Verify if an operation is safe.
        """
        # 1. Keyword check (brutal fast fail)
        for kw in self.FORBIDDEN_KEYWORDS:
            if kw in code_snippet:
                return {
                    "allowed": False,
                    "reason": f"Forbidden keyword detected: {kw}",
                    "risk": RiskLevel.FORBIDDEN
                }
                
        # 2. Env Var Leak Check
        for var in self.SENSITIVE_ENV_VARS:
            if var in code_snippet:
                 return {
                    "allowed": False,
                    "reason": f"Potential Environment Variable Leak: {var}",
                    "risk": RiskLevel.HIGH_RISK
                }

        return {"allowed": True, "reason": "Passed operation guard checks", "risk": RiskLevel.SAFE}

    def scrub_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        """
        Remove sensitive keys from an environment dict.
        """
        clean_env = env.copy()
        for key in list(clean_env.keys()):
            if any(s in key.upper() for s in ["KEY", "SECRET", "PASSWORD", "TOKEN", "AUTH"]):
                del clean_env[key]
        return clean_env


@dataclass
class ApprovalRequest:
    """A request for approval of a potentially dangerous operation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    operation: str = ""
    risk_level: RiskLevel = RiskLevel.SAFE
    reason: str = ""
    code_snippet: str = ""
    requested_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "operation": self.operation,
            "risk_level": self.risk_level.value,
            "reason": self.reason,
            "code_snippet": self.code_snippet[:200],
            "requested_at": self.requested_at.isoformat()
        }


@dataclass
class ApprovalResult:
    """Result of an approval request."""
    approved: bool = False
    request_id: str = ""
    reason: str = ""
    approved_by: str = "system"
    approved_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "request_id": self.request_id,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat()
        }


def request_approval(operation: str, code: str = "", context: str = "") -> ApprovalResult:
    """
    Request approval for an operation.
    
    For a private product running unattended, this auto-approves
    anything that passes OperationGuard checks. FORBIDDEN ops are denied.
    """
    guard = OperationGuard()
    check = guard.check_operation(code or operation, context)
    
    req = ApprovalRequest(
        operation=operation,
        risk_level=check["risk"],
        reason=check["reason"],
        code_snippet=code
    )
    
    if not check["allowed"]:
        logger.warning(f"[OPERATION_GUARD] DENIED: {operation}  {check['reason']}")
        return ApprovalResult(
            approved=False,
            request_id=req.id,
            reason=check["reason"],
            approved_by="operation_guard"
        )
    
    logger.debug(f"[OPERATION_GUARD] APPROVED: {operation}")
    return ApprovalResult(
        approved=True,
        request_id=req.id,
        reason="Auto-approved by OperationGuard",
        approved_by="operation_guard"
    )
