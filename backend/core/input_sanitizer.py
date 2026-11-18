"""
Input Sanitization - Prompt Injection Defense
==============================================
Part of Ultron's Security Layer.

Protects against prompt injection attacks by:
1. Detecting and neutralizing injection patterns
2. Validating input format and content
3. Escaping potentially dangerous sequences
4. Rate limiting suspicious patterns

This is critical for production deployment where users can input arbitrary text.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# INJECTION PATTERNS
# ============================================================================

# Common prompt injection patterns
INJECTION_PATTERNS = [
    # Direct instruction override attempts
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
    r"forget\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
    r"override\s+(system|all)\s+(prompts?|instructions?)",
    
    # System prompt extraction attempts
    r"(show|reveal|display|print|output)\s+(me\s+)?your\s+(system\s+)?(prompt|instructions?|rules?)",
    r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?|rules?)",
    r"repeat\s+(back\s+)?(your\s+)?(initial|system|original)\s+(prompt|instructions?)",
    
    # Role manipulation
    r"you\s+are\s+(now|no\s+longer)\s+a\s+(?:hacker|dan|unrestricted|jailbroken|evil|unfiltered)",
    r"pretend\s+(you\s+are|to\s+be)\s+a\s+(?:hacker|dan|unrestricted|jailbroken|evil|unfiltered)",
    r"act\s+as\s+(if\s+you\s+are\s+)?(?:a\s+)?(?:hacker|dan|unrestricted|jailbroken|evil|unfiltered)",
    r"roleplay\s+as\s+(?:a\s+)?(?:hacker|dan|unrestricted|jailbroken|evil|unfiltered)",
    r"switch\s+to\s+(?:dan|developer|unrestricted|jailbreak|god|admin|sudo)\s+mode",
    r"enter\s+(?:dan|developer|unrestricted|jailbreak|god|admin|sudo)\s+mode",
    
    # Jailbreak attempts
    r"DAN\s+mode",
    r"developer\s+mode",
    r"jailbreak",
    r"bypass\s+(safety|restrictions?|filters?)",
    r"ignore\s+(safety|ethical)\s+(guidelines?|restrictions?)",
    
    # Code injection markers
    r"\[SYSTEM\]",
    r"\[INST\]",
    r"<<SYS>>",
    r"<\|im_start\|>",
    r"<\|im_end\|>",

    # Markdown/HTML injection for XSS (Bounded for F-62 ReDoS Protection)
    r"<script[^>]{0,1000}>",
    r"javascript:",
    r"on\w+\s*=",  # Event handlers

    # Data exfiltration attempts
    r"(send|post|transmit|exfil)\s+(to|data)",
    r"(curl|wget|fetch)\s+http",

    # F-62: ReDoS-safe Shell / JNDI / Env Template Injection (excludes LaTeX math like ${T_c}$)
    r"\$\{(?:IFS|PATH|LD_PRELOAD|SHELL|USER|HOME|PWD|jndi:|env:|sys:|lower:|upper:|base64:)[^}]{0,100}\}",
]

# Compile patterns for performance
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# Suspicious characters that might indicate encoding attacks
SUSPICIOUS_CHARS = [
    "\x00",  # Null byte
    "%00",   # URL-encoded null
]


@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    is_safe: bool
    sanitized_input: str
    original_input: str
    threats_detected: List[str]
    risk_score: float  # 0.0 - 1.0
    details: str


class InputSanitizer:
    """
    Sanitizes user input to prevent prompt injection attacks.
    
    Features:
    - Pattern-based injection detection
    - Input length validation
    - Character encoding normalization
    - Suspicious pattern tracking
    
    Example:
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("My research query...")
        
        if not result.is_safe:
            logger.warning(f"Blocked: {result.threats_detected}")
            return error_response()
        
        # Use result.sanitized_input for processing
    """
    
    def __init__(
        self,
        max_input_length: int = 10000,
        enable_strict_mode: bool = True,
        track_suspicious_ips: bool = True
    ):
        """
        Initialize the sanitizer.
        
        Args:
            max_input_length: Maximum allowed input length
            enable_strict_mode: If True, block any detected injection attempt
            track_suspicious_ips: Track IPs with repeated injection attempts
        """
        self.max_input_length = max_input_length
        self.strict_mode = enable_strict_mode
        self.track_ips = track_suspicious_ips
        
        # IP tracking for rate limiting suspicious users
        self._suspicious_ips: Dict[str, List[datetime]] = defaultdict(list)
        self._blocked_ips: Dict[str, datetime] = {}
        
        logger.info("InputSanitizer initialized")
    
    def sanitize(
        self,
        user_input: str,
        context: str = "query",
        client_ip: Optional[str] = None
    ) -> SanitizationResult:
        """
        Sanitize user input and detect injection attempts.
        
        Args:
            user_input: Raw user input to sanitize
            context: Context of the input (e.g., "query", "hypothesis", "code")
            client_ip: Optional client IP for tracking
        
        Returns:
            SanitizationResult with safety assessment and cleaned input
        """
        threats = []
        risk_score = 0.0
        
        original = user_input
        
        # Check if IP is blocked
        if client_ip and self._is_ip_blocked(client_ip):
            return SanitizationResult(
                is_safe=False,
                sanitized_input="",
                original_input=original,
                threats_detected=["IP temporarily blocked due to repeated violations"],
                risk_score=1.0,
                details="Too many injection attempts from this IP"
            )
        
        # Length check
        if len(user_input) > self.max_input_length:
            threats.append(f"Input exceeds maximum length ({len(user_input)} > {self.max_input_length})")
            risk_score += 0.3
            user_input = user_input[:self.max_input_length]
        
        # Normalize encoding
        user_input = self._normalize_encoding(user_input)
        
        # Check for suspicious characters
        for char in SUSPICIOUS_CHARS:
            if char in user_input:
                threats.append(f"Suspicious character sequence: {repr(char)}")
                risk_score += 0.2
                user_input = user_input.replace(char, "")
        
        # Pattern matching for injection attempts
        for pattern in COMPILED_PATTERNS:
            matches = pattern.findall(user_input)
            if matches:
                threat_desc = f"Injection pattern detected: {pattern.pattern[:50]}..."
                threats.append(threat_desc)
                risk_score += 0.4
                
                if self.strict_mode:
                    # Remove the matched content
                    user_input = pattern.sub("[SANITIZED]", user_input)
        
        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)
        
        # Determine safety
        is_safe = risk_score < 0.5 or not self.strict_mode
        
        # Track suspicious IPs
        if client_ip and threats:
            self._record_suspicious_activity(client_ip, threats)
        
        # Log significant threats
        if threats:
            logger.warning(
                f"Input sanitization detected {len(threats)} threats "
                f"(risk={risk_score:.2f}): {threats[:3]}"
            )
        
        return SanitizationResult(
            is_safe=is_safe,
            sanitized_input=user_input if is_safe else "",
            original_input=original,
            threats_detected=threats,
            risk_score=risk_score,
            details=f"Context: {context}, Threats: {len(threats)}, Risk: {risk_score:.2f}"
        )
    
    def sanitize_for_prompt(
        self,
        user_input: str,
        max_length: Optional[int] = None
    ) -> str:
        """
        Convenience method for sanitizing input destined for LLM prompts.
        
        Returns sanitized string or raises ValueError if unsafe.
        """
        result = self.sanitize(user_input, context="prompt")
        
        if not result.is_safe:
            raise ValueError(f"Input failed sanitization: {result.threats_detected}")
        
        output = result.sanitized_input
        if max_length and len(output) > max_length:
            output = output[:max_length]
        
        return output
    
    def _normalize_encoding(self, text: str) -> str:
        """Normalize text encoding to prevent encoding-based attacks."""
        # Normalize unicode
        import unicodedata
        text = unicodedata.normalize("NFKC", text)
        
        # Remove control characters (except newlines and tabs)
        text = "".join(
            char for char in text 
            if char in "\n\t" or not unicodedata.category(char).startswith("C")
        )
        
        return text
    
    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if an IP is temporarily blocked."""
        if ip in self._blocked_ips:
            block_time = self._blocked_ips[ip]
            if datetime.utcnow() - block_time < timedelta(hours=1):
                return True
            else:
                del self._blocked_ips[ip]
        return False
    
    def _record_suspicious_activity(self, ip: str, threats: List[str]) -> None:
        """Record suspicious activity for an IP."""
        now = datetime.utcnow()
        
        # Clean old entries
        self._suspicious_ips[ip] = [
            t for t in self._suspicious_ips[ip]
            if now - t < timedelta(hours=1)
        ]
        
        # Add new entry
        self._suspicious_ips[ip].append(now)
        
        # Block if too many attempts
        if len(self._suspicious_ips[ip]) >= 10:
            self._blocked_ips[ip] = now
            logger.warning(f"Blocked IP {ip} due to repeated injection attempts")
    
    def get_blocked_ips(self) -> List[str]:
        """Get list of currently blocked IPs."""
        now = datetime.utcnow()
        return [
            ip for ip, block_time in self._blocked_ips.items()
            if now - block_time < timedelta(hours=1)
        ]


def sanitize_research_query(query: str, client_ip: Optional[str] = None) -> Tuple[str, bool]:
    """
    Convenience function for sanitizing research queries.
    
    Returns:
        (sanitized_query, is_safe)
    """
    sanitizer = get_input_sanitizer()
    result = sanitizer.sanitize(query, context="research_query", client_ip=client_ip)
    return result.sanitized_input, result.is_safe


# ============================================================================
# SINGLETON
# ============================================================================

_sanitizer_instance: Optional[InputSanitizer] = None

def get_input_sanitizer() -> InputSanitizer:
    """Get or create the singleton sanitizer instance."""
    global _sanitizer_instance
    if _sanitizer_instance is None:
        _sanitizer_instance = InputSanitizer()
    return _sanitizer_instance
