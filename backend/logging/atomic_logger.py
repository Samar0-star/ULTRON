import os
import sys
import logging
from typing import Any

# Optional rich console for hell-level visibility
try:
    from rich.console import Console
    from rich.theme import Theme
    _console = Console(theme=Theme({
        "bus": "bold green",
        "llm": "bold magenta",
        "sandbox": "bold red",
        "world": "bold cyan",
        "agent": "bold yellow"
    }))
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

_ATOMIC_DEBUG = os.getenv("SVEL_ATOMIC_DEBUG", "0") == "1"

class AtomicLogger:
    """
    Centralized interceptor for Hell-Level Atomic Debugging.
    Only activates if SVEL_ATOMIC_DEBUG=1.
    """
    
    @staticmethod
    def is_active() -> bool:
        return _ATOMIC_DEBUG
        
    @staticmethod
    def _safe_str(obj: Any, max_len: int = 1000) -> str:
        try:
            s = str(obj)
            if len(s) > max_len and os.getenv("ATOMIC_DEEP_PAYLOAD", "0") != "1":
                return s[:max_len] + f"... [TRUNCATED {len(s)-max_len} bytes]"
            return s
        except Exception as e:
            return f"<Unserializable Object: {type(obj)} - {str(e)}>"

    @staticmethod
    def log(system: str, event_type: str, details: dict):
        if not _ATOMIC_DEBUG:
            return
            
        try:
            header = f"[{system.upper()}] {event_type}"
            body_parts = []
            for k, v in details.items():
                body_parts.append(f"{k}: {AtomicLogger._safe_str(v)}")
            
            body = " | ".join(body_parts)
            
            if _HAS_RICH:
                style = "white"
                if system == "bus": style = "bus"
                elif system == "llm": style = "llm"
                elif system == "sandbox": style = "sandbox"
                elif system == "world": style = "world"
                elif system == "agent": style = "agent"
                
                _console.print(f"{header} -> {body}", style=style)
            else:
                # Fallback to standard stdout
                print(f"ATOMIC >> {header} -> {body}", flush=True)
                
        except Exception:
            # Silent fail to prevent crashing the main autonomous loop
            pass
