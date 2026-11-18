from typing import Dict, Any, List, Optional, Union
import logging
import os
from .base_tool import BaseTool

# Import the God-Level PDF Processor
try:
    from .pdf_reader import GodLevelPDFProcessor
except ImportError:
    # Fallback for different import paths
    try:
        from backend.tools.pdf_reader import GodLevelPDFProcessor
    except ImportError:
        GodLevelPDFProcessor = None

logger = logging.getLogger(__name__)

class DocReaderTool(BaseTool):
    """
    Tool for deep reading of documents (PDF, HTML, Text).
    Powered by GodLevelPDFProcessor for high-rigor extraction.
    """
    name = "doc_reader"
    description = (
        "Deeply reads PDF documents, extracting full text, tables, and images. "
        "Supports single files or batches. Essential for grounding research in full-text literature."
    )
    version = "2.0.0"

    def __init__(self):
        super().__init__()
        # Initialize the processor lazily or here
        self.processor = None
        if GodLevelPDFProcessor:
            try:
                self.processor = GodLevelPDFProcessor(max_workers=4, enable_advanced_features=True)
            except Exception as e:
                logger.error(f"Failed to initialize GodLevelPDFProcessor: {e}")

    def run(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous run wrapper for backward compatibility.
        """
        import asyncio
        # Create a new event loop if necessary or use the existing one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # If we're already in an async loop, this is tricky
            # For tools we can just call a sync version of the processor
            return self._execute_sync(input)
        else:
            return loop.run_until_complete(self.execute(input))

    async def execute(self, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute deep reading.
        tool_spec: {
            "path": "path/to/doc.pdf" or ["path1.pdf", "path2.pdf"],
            "url": str (alias for path),
            "mode": "fast" | "deep" (deep includes tables/images),
            "ocr": bool (default True)
        }
        """
        path = tool_spec.get("path") or tool_spec.get("url") or tool_spec.get("query")
        mode = tool_spec.get("mode", "deep")
        
        if not path:
            return {"status": "failed", "error": "No path or URL provided to DocReader"}

        if not self.processor:
            return {
                "status": "failed", 
                "error": "GodLevelPDFProcessor (PyMuPDF/fitz) not available. Install requirements."
            }

        logger.info(f"DocReader initiating {mode} read for: {path}")

        try:
            # Handle list of paths
            if isinstance(path, list):
                # Use parallel processing for multiple PDFs
                results = self.processor.process_multiple_pdfs(path)
                return {
                    "status": "success",
                    "result": results,
                    "summary": f"Processed {len(path)} documents."
                }
            
            # Handle single path
            if isinstance(path, str):
                # Check if it's a directory
                if os.path.isdir(path):
                    pdf_paths = self.processor.get_all_pdf_paths(path)
                    if not pdf_paths:
                        return {"status": "failed", "error": f"No PDFs found in directory: {path}"}
                    results = self.processor.process_multiple_pdfs(pdf_paths)
                    return {
                        "status": "success",
                        "result": results,
                        "summary": f"Processed {len(pdf_paths)} documents from directory."
                    }
                
                # Check if it's a ZIP
                if path.lower().endswith(".zip"):
                    results = self.processor.process_zip_file(path)
                    return {
                        "status": "success",
                        "result": results,
                        "summary": "Processed ZIP archive content."
                    }

                # Otherwise treat as single PDF file
                if not os.path.exists(path):
                     return {"status": "failed", "error": f"File not found: {path}"}
                
                result = self.processor.process_single_pdf(path)
                
                if "error" in result:
                    return {"status": "failed", "error": result["error"]}
                
                # Flatten the result for easier agent consumption if it's just one file
                return {
                    "status": "success",
                    "result": result,
                    "text": result.get("content", {}).get("text", ""),
                    "tables": result.get("content", {}).get("tables", []),
                    "images_count": len(result.get("content", {}).get("images", [])),
                    "summary": f"Successfully read {os.path.basename(path)}"
                }

            return {"status": "failed", "error": f"Unsupported path type: {type(path)}"}

        except Exception as e:
            logger.exception(f"DocReader execution failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _execute_sync(self, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous version of execute logic."""
        path = tool_spec.get("path") or tool_spec.get("url") or tool_spec.get("query")
        if not self.processor or not path:
             return {"status": "failed", "error": "Processor or path missing"}
             
        try:
            if isinstance(path, str) and os.path.isfile(path):
                result = self.processor.process_single_pdf(path)
                return {
                    "status": "success",
                    "result": result,
                    "text": result.get("content", {}).get("text", ""),
                    "summary": f"Successfully read {os.path.basename(path)}"
                }
            # Fallback for complex cases: just use a minimal version
            return {"status": "failed", "error": "Complex sync reads not yet optimized"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
