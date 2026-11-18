"""
AVON-1 Base Tool Class
Enforces standard run(input: Dict) -> Dict interface for all tools
"""
from typing import Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)


class BaseTool:
    """
    Standard base class for all AVON-1 tools.
    
    Enforces consistent interface:
    - run(input: Dict) -> Dict
    - Standardized output format
    - Built-in error handling
    - Execution timing
    """
    
    name: str = "base_tool"
    description: str = "Base tool"
    version: str = "1.0.0"
    
    def run(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standard interface for tool execution.
        
        Args:
            input: Dict containing all required parameters
            
        Returns:
            {
                "status": "success" | "error",
                "result": Any,  # Main output
                "meta": Dict[str, Any],  # Metadata (timing, provider, version, etc.)
                "error": Optional[str]  # Error message if status == "error"
            }
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement run()")
    
    def validate_input(self, input: Dict[str, Any]) -> None:
        """
        Optional: Validate input before execution.
        Raises ValueError if validation fails.
        """
        pass
    
    def format_output(self, result: Any, **meta) -> Dict[str, Any]:
        """
        Helper to format standard success output.
        
        Args:
            result: The main tool output
            **meta: Additional metadata (provider, timing, etc.)
            
        Returns:
            Standardized success dict
        """
        return {
            "status": "success",
            "result": result,
            "meta": {
                "tool": self.name,
                "version": self.version,
                **meta
            },
            "error": None
        }
    
    def format_error(self, error: str, **meta) -> Dict[str, Any]:
        """
        Helper to format standard error output.
        
        Args:
            error: Error message
            **meta: Additional metadata
            
        Returns:
            Standardized error dict
        """
        return {
            "status": "error",
            "result": None,
            "error": error,
            "meta": {
                "tool": self.name,
                "version": self.version,
                **meta
            }
        }
    
    def execute_with_timing(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute run() with automatic timing.
        
        Returns:
            Standard output with duration_ms in meta
        """
        start_time = time.time()
        
        try:
            self.validate_input(input)
            result = self.run(input)
            
            # Add duration to meta if not already present
            if "meta" in result and "duration_ms" not in result["meta"]:
                result["meta"]["duration_ms"] = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"{self.name} execution failed: {e}")
            return self.format_error(str(e), duration_ms=duration_ms)


class AsyncBaseTool(BaseTool):
    """
    Async variant of BaseTool.
    For tools that need async/await support.
    """
    
    async def run(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of run()."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement async run()")
    
    async def execute_with_timing(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Async version with timing."""
        start_time = time.time()
        
        try:
            self.validate_input(input)
            result = await self.run(input)
            
            if "meta" in result and "duration_ms" not in result["meta"]:
                result["meta"]["duration_ms"] = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"{self.name} execution failed: {e}")
            return self.format_error(str(e), duration_ms=duration_ms)
