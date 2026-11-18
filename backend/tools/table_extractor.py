try:
    import pdfplumber
except ImportError:
    pdfplumber = None
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import tempfile
import json
import csv
from typing import List, Dict, Any, Union, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GodLevelTableExtractor:
    """
    Advanced PDF table extractor with multiple extraction methods,
    quality assessment, and multiple output formats.
    """
    
    def __init__(self, use_camelot: bool = True, use_tabula: bool = True):
        """
        Initialize the table extractor with optional advanced extraction libraries.
        
        Args:
            use_camelot: Whether to use Camelot for table extraction (if available)
            use_tabula: Whether to use Tabula for table extraction (if available)
        """
        self.use_camelot = use_camelot
        self.use_tabula = use_tabula
        self._camelot_available = False
        self._tabula_available = False
        
        # Check for optional dependencies
        if use_camelot:
            try:
                import camelot
                self._camelot_available = True
                logger.info("Camelot is available for table extraction")
            except ImportError:
                logger.warning("Camelot not available. Install with: pip install camelot-py")
        
        if use_tabula:
            try:
                import tabula
                self._tabula_available = True
                logger.info("Tabula is available for table extraction")
            except ImportError:
                logger.warning("Tabula not available. Install with: pip install tabula-py")
    
    def extract(self,
                input_source: Any,
                output_format: str = "structured",
                **kwargs) -> Dict[str, Any]:
        """
        Simple extract() method for compatibility with agent interface.
        Accepts file path, directory, or data and extracts tables.

        Args:
            input_source: Path to PDF file/directory, or data to extract tables from
            output_format: Output format ("structured", "combined_text", "json", "csv")
            **kwargs: Additional arguments (output_dir, etc.)

        Returns:
            Extracted tables in requested format
        """
        try:
            # If input_source is a string or Path, treat as file/directory path
            if isinstance(input_source, (str, Path)):
                return self.extract_tables(
                    input_path=input_source,
                    output_format=output_format,
                    output_dir=kwargs.get("output_dir")
                )
            else:
                # Unsupported input type - return error
                return {
                    "status": "error",
                    "error": f"Unsupported input type: {type(input_source)}. Expected file/directory path."
                }
        except Exception as e:
            logger.exception("extract() failed")
            return {
                "status": "error",
                "error": str(e)
            }

    def extract_tables(self,
                      input_path: Union[str, Path],
                      output_format: str = "combined_text",
                      output_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Extract tables from PDF files with multiple methods and quality assessment.
        
        Args:
            input_path: Path to a PDF file or directory containing PDFs
            output_format: Format of the output ("combined_text", "structured", "json", "csv")
            output_dir: Directory to save extracted tables (if None, no files are saved)
            
        Returns:
            Extracted tables in the requested format
        """
        input_path = Path(input_path)
        results = {
            "metadata": {
                "extraction_date": datetime.now().isoformat(),
                "input_path": str(input_path),
                "methods_used": ["pdfplumber"]
            },
            "tables": []
        }
        
        # Add available methods to metadata
        if self._camelot_available:
            results["metadata"]["methods_used"].append("camelot")
        if self._tabula_available:
            results["metadata"]["methods_used"].append("tabula")
        
        # Process single file or directory
        if input_path.is_file() and input_path.suffix.lower() == ".pdf":
            pdf_files = [input_path]
        elif input_path.is_dir():
            pdf_files = list(input_path.glob("*.pdf"))
        else:
            raise ValueError("Input path must be a PDF file or a directory containing PDF files")
        
        if not pdf_files:
            return {"error": "No PDF files found"} if output_format != "combined_text" else "No PDF files found"
        
        # Process each PDF file
        for pdf_file in pdf_files:
            file_results = self._process_pdf_file(pdf_file)
            results["tables"].extend(file_results)
        
        # Save results if output directory is specified
        if output_dir:
            self._save_results(results, output_dir, output_format)
        
        # Return in requested format
        return self._format_output(results, output_format)
    
    def _process_pdf_file(self, pdf_file: Path) -> List[Dict[str, Any]]:
        """Process a single PDF file and extract tables using available methods."""
        file_results = []
        
        logger.info(f"Processing PDF: {pdf_file.name}")
        
        # Method 1: pdfplumber (always available)
        plumber_tables = self._extract_with_pdfplumber(pdf_file)
        for table_data in plumber_tables:
            table_data["extraction_method"] = "pdfplumber"
            file_results.append(table_data)
        
        # Method 2: Camelot (if available)
        if self._camelot_available:
            camelot_tables = self._extract_with_camelot(pdf_file)
            for table_data in camelot_tables:
                # Check if this table is substantially different from pdfplumber tables
                if not self._is_duplicate_table(table_data, file_results):
                    table_data["extraction_method"] = "camelot"
                    file_results.append(table_data)
        
        # Method 3: Tabula (if available)
        if self._tabula_available:
            tabula_tables = self._extract_with_tabula(pdf_file)
            for table_data in tabula_tables:
                # Check if this table is substantially different from existing tables
                if not self._is_duplicate_table(table_data, file_results):
                    table_data["extraction_method"] = "tabula"
                    file_results.append(table_data)
        
        # Assess quality of each table
        for table_data in file_results:
            table_data["quality_score"] = self._assess_table_quality(table_data)
        
        return file_results
    
    def _extract_with_pdfplumber(self, pdf_file: Path) -> List[Dict[str, Any]]:
        """Extract tables using pdfplumber."""
        tables = []
        
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    
                    for table_num, table in enumerate(page_tables, 1):
                        if table and any(any(cell is not None for cell in row) for row in table):
                            # Convert to DataFrame for easier manipulation
                            df = pd.DataFrame(table)
                            
                            # Clean the table
                            df_clean = self._clean_dataframe(df)
                            
                            tables.append({
                                "source_file": pdf_file.name,
                                "page_number": page_num,
                                "table_number": table_num,
                                "data": df_clean.values.tolist(),
                                "headers": df_clean.columns.tolist() if not df_clean.empty else [],
                                "shape": df_clean.shape,
                                "method_specific": {"flavor": "pdfplumber"}
                            })
            
            logger.info(f"Extracted {len(tables)} tables with pdfplumber from {pdf_file.name}")
            
        except Exception as e:
            logger.error(f"Error extracting tables with pdfplumber from {pdf_file.name}: {e}")
        
        return tables
    
    def _extract_with_camelot(self, pdf_file: Path) -> List[Dict[str, Any]]:
        """Extract tables using Camelot."""
        tables = []
        
        try:
            import camelot
            
            # Extract tables using Camelot
            camelot_tables = camelot.read_pdf(str(pdf_file), pages='all', flavor='stream')
            
            for i, table in enumerate(camelot_tables, 1):
                if table.df is not None and not table.df.empty:
                    # Clean the table
                    df_clean = self._clean_dataframe(table.df)
                    
                    tables.append({
                        "source_file": pdf_file.name,
                        "page_number": table.page,
                        "table_number": i,
                        "data": df_clean.values.tolist(),
                        "headers": df_clean.columns.tolist(),
                        "shape": df_clean.shape,
                        "method_specific": {
                            "accuracy": table.accuracy,
                            "whitespace": table.whitespace,
                            "order": i
                        }
                    })
            
            logger.info(f"Extracted {len(tables)} tables with Camelot from {pdf_file.name}")
            
        except Exception as e:
            logger.error(f"Error extracting tables with Camelot from {pdf_file.name}: {e}")
        
        return tables
    
    def _extract_with_tabula(self, pdf_file: Path) -> List[Dict[str, Any]]:
        """Extract tables using Tabula."""
        tables = []
        
        try:
            import tabula
            
            # Extract tables using Tabula
            tabula_tables = tabula.read_pdf(str(pdf_file), pages='all', multiple_tables=True)
            
            for i, df in enumerate(tabula_tables, 1):
                if df is not None and not df.empty:
                    # Clean the table
                    df_clean = self._clean_dataframe(df)
                    
                    tables.append({
                        "source_file": pdf_file.name,
                        "page_number": 0,  # Tabula doesn't provide page numbers easily
                        "table_number": i,
                        "data": df_clean.values.tolist(),
                        "headers": df_clean.columns.tolist(),
                        "shape": df_clean.shape,
                        "method_specific": {"library": "tabula"}
                    })
            
            logger.info(f"Extracted {len(tables)} tables with Tabula from {pdf_file.name}")
            
        except Exception as e:
            logger.error(f"Error extracting tables with Tabula from {pdf_file.name}: {e}")
        
        return tables
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize a DataFrame extracted from a PDF table."""
        df_clean = df.copy()
        
        # Remove completely empty rows and columns
        df_clean = df_clean.dropna(how='all')
        df_clean = df_clean.dropna(axis=1, how='all')
        
        # Reset index and ensure unique temporary column indices before cleaning
        df_clean = df_clean.reset_index(drop=True)
        df_clean.columns = list(range(df_clean.shape[1]))
        
        # Fill NaN values with empty strings
        df_clean = df_clean.fillna("")
        
        # Clean string values column by positional index (safe even if headers later duplicate)
        for col_idx in range(df_clean.shape[1]):
            ser = df_clean.iloc[:, col_idx]
            if ser.dtype == 'object':
                df_clean.iloc[:, col_idx] = ser.apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
        
        # Try to promote first row to headers if it looks like a header row, deduplicating column names
        if not df_clean.empty and self._looks_like_header(df_clean.iloc[0]):
            raw_headers = [str(v).strip() or f"col_{i}" for i, v in enumerate(df_clean.iloc[0])]
            seen_headers: Dict[str, int] = {}
            unique_headers = []
            for h in raw_headers:
                if h not in seen_headers:
                    seen_headers[h] = 0
                    unique_headers.append(h)
                else:
                    seen_headers[h] += 1
                    unique_headers.append(f"{h}_{seen_headers[h]}")
            df_clean.columns = unique_headers
            df_clean = df_clean[1:].reset_index(drop=True)
        
        return df_clean
    
    def _looks_like_header(self, row: pd.Series) -> bool:
        """Check if a row looks like it contains header information."""
        if len(row) < 2:
            return False
        
        # Check if most values are strings (not numeric)
        string_count = sum(1 for val in row if isinstance(val, str) and val.strip())
        return string_count / len(row) > 0.7
    
    def _is_duplicate_table(self, new_table: Dict[str, Any], existing_tables: List[Dict[str, Any]]) -> bool:
        """Check if a table is substantially similar to already extracted tables."""
        if not existing_tables:
            return False
        
        new_data = new_table.get("data", [])
        if not new_data:
            return True  # Empty table is considered a duplicate
        
        for existing_table in existing_tables:
            existing_data = existing_table.get("data", [])
            
            # Simple check: if the shapes are very different, they're not duplicates
            if len(new_data) != len(existing_data) or (
                len(new_data) > 0 and len(new_data[0]) != len(existing_data[0])
            ):
                continue
            
            # More advanced check: compare content similarity
            similarity = self._calculate_table_similarity(new_data, existing_data)
            if similarity > 0.8:  # 80% similarity threshold
                return True
        
        return False
    
    def _calculate_table_similarity(self, table1: List[List[Any]], table2: List[List[Any]]) -> float:
        """Calculate similarity between two tables."""
        if not table1 or not table2:
            return 0.0
        
        if len(table1) != len(table2) or len(table1[0]) != len(table2[0]):
            return 0.0
        
        matching_cells = 0
        total_cells = len(table1) * len(table1[0])
        
        for i in range(len(table1)):
            for j in range(len(table1[0])):
                cell1 = str(table1[i][j]).strip().lower()
                cell2 = str(table2[i][j]).strip().lower()
                
                if cell1 and cell2 and cell1 == cell2:
                    matching_cells += 1
        
        return matching_cells / total_cells if total_cells > 0 else 0.0
    
    def _assess_table_quality(self, table_data: Dict[str, Any]) -> float:
        """Assess the quality of an extracted table (0.0 to 1.0)."""
        data = table_data.get("data", [])
        if not data:
            return 0.0
        
        # Calculate quality based on various factors
        quality_score = 0.0
        
        # 1. Completeness: percentage of non-empty cells
        total_cells = len(data) * len(data[0]) if data and len(data[0]) > 0 else 1
        non_empty_cells = sum(1 for row in data for cell in row if cell and str(cell).strip())
        completeness = non_empty_cells / total_cells
        quality_score += completeness * 0.4  # 40% weight
        
        # 2. Structure: table has reasonable dimensions
        rows, cols = len(data), len(data[0]) if data and len(data[0]) > 0 else 0
        structure_score = 1.0 if rows >= 2 and cols >= 2 else 0.5 if rows >= 1 and cols >= 2 else 0.2
        quality_score += structure_score * 0.3  # 30% weight
        
        # 3. Consistency: rows have similar number of columns
        col_counts = [len(row) for row in data]
        if col_counts:
            consistency = 1.0 - (max(col_counts) - min(col_counts)) / max(col_counts)
            quality_score += consistency * 0.3  # 30% weight
        
        return min(1.0, max(0.0, quality_score))
    
    def _save_results(self, results: Dict[str, Any], output_dir: Union[str, Path], output_format: str):
        """Save extraction results to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save metadata
        with open(output_dir / f"extraction_metadata_{timestamp}.json", "w") as f:
            json.dump(results["metadata"], f, indent=2)
        
        # Save tables in requested format
        if output_format == "json":
            with open(output_dir / f"extracted_tables_{timestamp}.json", "w") as f:
                json.dump(results["tables"], f, indent=2, default=str)
        
        elif output_format == "csv":
            # Save each table as a separate CSV file
            for i, table in enumerate(results["tables"]):
                filename = f"table_{i+1}_{table['source_file'].replace('.pdf', '')}_{timestamp}.csv"
                df = pd.DataFrame(table["data"])
                if table["headers"]:
                    df.columns = table["headers"]
                df.to_csv(output_dir / filename, index=False, encoding='utf-8')
        
        logger.info(f"Results saved to {output_dir}")
    
    def _format_output(self, results: Dict[str, Any], output_format: str) -> Any:
        """Format the output according to the requested format."""
        if output_format == "combined_text":
            return self._format_as_combined_text(results)
        elif output_format == "structured":
            return results
        elif output_format == "json":
            return results
        elif output_format == "csv":
            # For CSV format, we return the path to saved files
            return {"message": "Tables saved as CSV files", "tables_count": len(results["tables"])}
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _format_as_combined_text(self, results: Dict[str, Any]) -> str:
        """Format results as combined text (similar to the original function)."""
        if not results["tables"]:
            return "No tables found in the uploaded PDFs."
        
        output_lines = []
        
        for table in results["tables"]:
            output_lines.append(f"From {table['source_file']} page {table['page_number']} "
                              f"(extracted with {table['extraction_method']}, "
                              f"quality: {table['quality_score']:.2f}):")
            
            # Create a text representation of the table
            df = pd.DataFrame(table["data"])
            if table["headers"]:
                df.columns = table["headers"]
            
            output_lines.append(df.to_string(index=False))
            output_lines.append("")  # Empty line between tables
        
        return "\n".join(output_lines)


# Backward compatibility function
def extract_tables(upload_folder="data/uploaded_files", output_format="combined_text"):
    """
    Extract tables from PDF files (backward compatible with the original function).
    
    Args:
        upload_folder: Path to the folder containing PDF files
        output_format: Format of the output ("combined_text", "structured", "json", "csv")
    
    Returns:
        Extracted tables in the requested format
    """
    extractor = GodLevelTableExtractor()
    return extractor.extract_tables(upload_folder, output_format)


# Example usage
if __name__ == "__main__":
    # Initialize the extractor
    extractor = GodLevelTableExtractor()
    
    # Extract tables from a directory
    result = extractor.extract_tables(
        input_path="data/uploaded_files",
        output_format="combined_text",
        output_dir="data/extracted_tables"
    )

    print(result)

# Backward compatibility alias
TableExtractor = GodLevelTableExtractor
