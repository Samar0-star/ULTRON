# backend/tools/code_executor_tool.py
"""
Code Executor Tool (Cautious Beast)
- Safely execute short Python snippets in a temp dir with timeout and resource limits.
- DEFAULT: allow_exec=False to prevent accidental use.
- For production: run inside Docker or a secure remote sandbox.
"""

import os
import tempfile
import shutil
import subprocess
import uuid
import textwrap
from typing import Dict, Any, Optional

DEFAULT_TIMEOUT = 60  # seconds (Boosted for High-Energy Physics)


def run_python_code(code: str, timeout: int = DEFAULT_TIMEOUT, allow_exec: bool = False) -> Dict[str,Any]:
    """
    Run python code snippet using the Hybrid GodModeSandbox.
    """
    if not allow_exec:
        return {"status":"error","error":"Execution disabled. Set allow_exec=True only in secure sandbox."}
    
    try:
        from backend.execution.sandbox import GodModeSandbox
        sandbox = GodModeSandbox()
        result = sandbox.run(code, timeout=timeout)
        
        return {
            "status": "ok" if result.exit_code == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.exit_code,
            "duration": result.duration
        }
    except Exception as e:
        return {"status":"error","error":str(e)}


# =============================================================================
# LLM-POWERED CODE GENERATION (OpenAI GPT for Stable Code)
# =============================================================================
def generate_and_run(
    task_description: str,
    timeout: int = DEFAULT_TIMEOUT,
    allow_exec: bool = False,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate Python code using LLM (OpenAI GPT via stable_code mode) and execute it.
    
    Args:
        task_description: Natural language description of what the code should do
        timeout: Execution timeout in seconds
        allow_exec: Must be True to actually run the generated code
        max_tokens: Max tokens for code generation
        
    Returns:
        Dict with generated_code, execution result, and metadata
    """
    # Import llm_manager lazily to avoid circular imports
    try:
        from backend.llm_manager import llm_manager
    except ImportError:
        return {"status": "error", "error": "llm_manager not available"}
    
    # Build the BEAST-tier code generation prompt
    code_gen_prompt = f"""

   GODZILLA CODE FORGE  BEAST MODE EXECUTION ENGINE                        


You are the ULTIMATE Python code synthesizer. Your code will be EXECUTED IMMEDIATELY.
Zero margin for error. Production-grade only.

TASK: {task_description}


MANDATORY REQUIREMENTS (VIOLATION = EXECUTION FAILURE)


1.  OUTPUT ONLY VALID PYTHON  No markdown, no explanations, no commentary
2.  IMPORTS FIRST  All necessary imports at the top
3.  PRINT RESULTS  Use print() for ALL output (this captures results)
4.  EXCEPTION HANDLING  Graceful error handling with informative messages
5.  NO NETWORK  No external API calls unless explicitly requested
6.  NO FILE ESCAPE  Do NOT write outside current directory
7.  CONCISE & FOCUSED  Minimal code, maximum impact



PYTHON CODE:"""

    try:
        # Use llm_manager with mode='stable_code' to route to OpenAI GPT
        result = llm_manager.run(
            prompt=code_gen_prompt,
            mode="stable_code",  # Forces OpenAI GPT models
            max_tokens_override=max_tokens,
            temperature=0.1  # Low temperature for deterministic code
        )
        
        generated_code = result.get("text", "").strip()
        model_used = result.get("model", "unknown")
        provider = result.get("provider", "unknown")
        
        # Clean up code (remove markdown fences if present)
        if generated_code.startswith("```python"):
            generated_code = generated_code[9:]
        if generated_code.startswith("```"):
            generated_code = generated_code[3:]
        if generated_code.endswith("```"):
            generated_code = generated_code[:-3]
        generated_code = generated_code.strip()
        
        if not generated_code:
            return {
                "status": "error",
                "error": "LLM returned empty code",
                "model": model_used,
                "provider": provider
            }
        
        # Execute the generated code
        exec_result = run_python_code(generated_code, timeout=timeout, allow_exec=allow_exec)
        
        return {
            "status": exec_result.get("status"),
            "generated_code": generated_code,
            "stdout": exec_result.get("stdout", ""),
            "stderr": exec_result.get("stderr", ""),
            "returncode": exec_result.get("returncode"),
            "model": model_used,
            "provider": provider,
            "error": exec_result.get("error")
        }
        
    except Exception as e:
        return {"status": "error", "error": f"Code generation failed: {str(e)}"}

