"""
SVEL Column Schema Validator - Anti-Hallucination Gate
=========================================================
Validates that generated code only uses actual column names from data files.
"""

import re
import ast
import logging
from typing import Set, Dict, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class ColumnSchemaValidator:
    """
    [GODZILLA V60] Schema Validation Gate
    Ensures generated code uses only valid column names from real data.
    """
    
    def __init__(self, data_paths: Dict[str, str]):
        self.data_paths = data_paths
        self.valid_columns: Dict[str, Set[str]] = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load column names from all data files with delimiter sniffing."""
        for label, path in self.data_paths.items():
            try:
                if path.lower().endswith(('.csv', '.csv.gz', '.tsv', '.tsv.gz')):
                    comp = 'gzip' if path.lower().endswith('.gz') else None
                    best_cols = set()
                    for sep in [',', ';', '\t']:
                        try:
                            df = pd.read_csv(path, sep=sep, nrows=0, compression=comp)
                            if len(df.columns) > len(best_cols):
                                best_cols = set(df.columns)
                        except Exception:
                            continue
                    if best_cols:
                        self.valid_columns[label] = best_cols
                        logger.info(f"[SCHEMA] Loaded {len(best_cols)} columns from {label}: {list(best_cols)[:20]}")
            except Exception as e:
                logger.warning(f"[SCHEMA] Failed to load schema for {label}: {e}")
    
    def extract_column_references(self, code: str) -> Set[Tuple[str, str]]:
        """
        Extract column name references from code.
        Returns: Set of (data_var, column_name) tuples
        """
        references = set()
        
        # Pattern 1: df['column_name'] or df["column_name"]
        bracket_pattern = r"(\w+)\[['\"]([^'\"]+)['\"]\]"
        for match in re.finditer(bracket_pattern, code):
            var_name = match.group(1)
            col_name = match.group(2)
            references.add((var_name, col_name))
        
        # Pattern 2: df.column_name
        dot_pattern = r"(\w+)\.([a-zA-Z_][a-zA-Z0-9_]*)"
        for match in re.finditer(dot_pattern, code):
            var_name = match.group(1)
            col_name = match.group(2)
            # Filter out method calls (common pandas methods)
            if col_name not in {'head', 'tail', 'shape', 'columns', 'index', 'values', 'dtypes', 'iloc', 'loc', 'at', 'iat', 'copy', 'drop', 'fillna', 'isnull', 'notnull', 'astype', 'apply', 'map', 'groupby', 'merge', 'join', 'concat', 'sort_values', 'reset_index', 'set_index', 'to_csv', 'to_json', 'mean', 'std', 'sum', 'min', 'max', 'count', 'nunique', 'unique', 'value_counts', 'quantile', 'median', 'var', 'cov', 'corr', 'describe', 'info', 'iterrows', 'itertuples', 'items', 'keys', 'to_dict', 'to_numpy', 'tolist', 'T', 'transpose', 'pivot', 'pivot_table', 'melt', 'stack', 'unstack', 'explode', 'squeeze', 'add', 'sub', 'mul', 'div', 'mod', 'pow', 'eq', 'ne', 'lt', 'le', 'gt', 'ge', 'and', 'or', 'xor', 'abs', 'round', 'clip', 'cumsum', 'cumprod', 'cummax', 'cummin', 'pct_change', 'diff', 'shift', 'rolling', 'expanding', 'ewm', 'resample', 'interpolate', 'ffill', 'bfill', 'pad', 'backfill', 'dropna', 'duplicated', 'drop_duplicates', 'isin', 'between', 'isna', 'notna', 'mask', 'where', 'query', 'eval', 'select_dtypes', 'filter', 'take', 'sample', 'pipe', 'agg', 'aggregate', 'transform', 'filter', 'first', 'last', 'nth', 'size', 'idxmin', 'idxmax', 'memory_usage', 'empty', 'ndim', 'axes', 'ndim'}:
                references.add((var_name, col_name))
        
        return references
    
    def validate_code(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate that code only uses valid column names.
        Returns: (is_valid, list of errors)
        """
        errors = []
        references = self.extract_column_references(code)
        
        # Map variable names to data labels
        var_to_label = {}
        for label in self.valid_columns.keys():
            pattern = rf"(\w+)\s*=\s*(?:pd\.read_csv|pd\.read_parquet|load_verified_data)\s*\(\s*{label}"
            for match in re.finditer(pattern, code):
                var_name = match.group(1)
                var_to_label[var_name] = label
                logger.info(f"[SCHEMA] Mapped variable '{var_name}' -> '{label}'")
        
        # Also check direct usage: DATA_XXX['column']
        for label in self.valid_columns.keys():
            # Pattern: LABEL['column']
            pattern = rf"{label}\[['\"]([^'\"]+)['\"]\]"
            for match in re.finditer(pattern, code):
                col_name = match.group(1)
                if col_name not in self.valid_columns.get(label, set()):
                    errors.append(f"[HALLUCINATION] Column '{col_name}' does not exist in {label}. Valid columns: {sorted(self.valid_columns.get(label, set()))}")
        
        # Validate references
        for var_name, col_name in references:
            if var_name in var_to_label:
                label = var_to_label[var_name]
                valid_cols = self.valid_columns.get(label, set())
                if col_name not in valid_cols:
                    errors.append(f"[HALLUCINATION] Variable '{var_name}' (from {label}) uses invalid column '{col_name}'. Valid: {sorted(valid_cols)}")
        
        if errors:
            logger.error(f"[SCHEMA] Validation FAILED with {len(errors)} errors:")
            for e in errors[:5]:  # Log first 5
                logger.error(f"  {e}")
            return False, errors
        
        logger.info("[SCHEMA] Validation PASSED - all column references are valid")
        return True, []


def validate_code_against_schema(code: str, data_paths: Dict[str, str]) -> Tuple[bool, List[str]]:
    """Convenience function for external use."""
    validator = ColumnSchemaValidator(data_paths)
    return validator.validate_code(code)

# [GODZILLA V61] PRE-EXECUTION VALIDATION GATE
# Add this check before running experiment code

import re

def validate_code_before_execution(code: str, data_paths: Dict[str, str]) -> Tuple[bool, str]:
    """
    Pre-execution validation to catch common LLM hallucinations.
    Returns (is_valid, error_message)
    """
    errors = []
    
    # Check 1: pd.read_csv on PDB files
    pdb_vars = [var for var in data_paths.keys() if 'PDB' in var.upper()]
    for pdb_var in pdb_vars:
        # Pattern: pd.read_csv(DATA_PDB_XXX) or pd.read_csv(DATA_PDB_XXX, ...)
        pattern = rf"pd\.read_csv\s*\(\s*{pdb_var}"
        if re.search(pattern, code):
            errors.append(f"INVALID: Using pd.read_csv() on PDB file {pdb_var}. "
                         f"PDB files are NOT CSV. Use Bio.PDB.PDBParser instead.")
    
    # Check 2: Hardcoded column names that don't exist
    # This will be caught at runtime but we can warn here
    
    # Check 3: Missing data loading
    has_loader = any(
        k in code for k in (
            'pd.read_csv', 'pd.read_parquet', 'load_verified_data',
            'DF_PRIMARY', 'DF_', 'sqlite3.connect', 'Bio.PDB', 'PDBParser', 'h5py.File'
        )
    )
    if not has_loader:
        data_vars_used = sum(1 for var in data_paths.keys() if var in code)
        if data_vars_used == 0 and data_paths:
            errors.append("INVALID: Code does not load any data files. "
                         "Must use provided DATA_* variables.")
    
    if errors:
        return False, "; ".join(errors)
    return True, ""
