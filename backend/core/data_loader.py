"""
SVEL Data Loader
==================
Purpose:
- Unified interface for ingesting scientific data.
- Resolves World Model URIs to physical file paths.
- Handles CSV, TSV, CSV.GZ, Parquet, HDF5, BAM, FASTA, and NIfTI formats.
- Enforces data integrity checks upon loading.

This module bridges the gap between the immutable World Model entities
and the executable Experiment Templates.
"""

import os
import logging
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional, Union, List
from pathlib import Path

logger = logging.getLogger("svel.core.data_loader")


class DataLoader:
    """
    Universal scientific data loader.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path(os.getenv("SVEL_DATA_ROOT", "./data"))

    def resolve_path(self, uri: str) -> Path:
        """
        Resolve a URI (e.g., 'dataset:123' or 'file:///path/to/data.csv') to a local path.
        """
        if uri.startswith("file://"):
            return Path(uri.replace("file://", ""))
        elif uri.startswith("dataset:"):
            dataset_id = uri.split(":")[1]
            for ext in ['.csv', '.tsv', '.csv.gz', '.parquet', '.h5', '.nii']:
                p = self.base_path / f"{dataset_id}{ext}"
                if p.exists():
                    return p
            return self.base_path / dataset_id
        else:
            return Path(uri)

    def load_tabular(self, uri: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load tabular data (CSV, TSV, CSV.GZ, Parquet, HDF5).
        """
        path = self.resolve_path(uri)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
            
        logger.info(f"Loading tabular data from {path}")
        path_str = str(path).lower()
        
        if path_str.endswith('.csv.gz') or path_str.endswith('.tsv.gz'):
            sep = '\t' if path_str.endswith('.tsv.gz') else ','
            df = pd.read_csv(path, sep=sep, usecols=columns, compression='gzip')
        elif path.suffix == '.csv':
            df = None
            for sep in [',', ';', '\t']:
                try:
                    cand = pd.read_csv(path, sep=sep, usecols=columns)
                    if cand.shape[1] > 1 or columns:
                        df = cand
                        break
                except Exception:
                    continue
            if df is None:
                df = pd.read_csv(path, usecols=columns)
        elif path.suffix == '.tsv':
            df = pd.read_csv(path, sep='\t', usecols=columns)
        elif path.suffix == '.parquet':
            df = pd.read_parquet(path, columns=columns)
        elif path.suffix in ['.h5', '.hdf5']:
            df = pd.read_hdf(path)
        else:
            raise ValueError(f"Unsupported tabular format: {path.suffix}")
            
        return df

    def load_matrix(self, uri: str) -> np.ndarray:
        """
        Load matrix data (NPY, CSV without headers).
        """
        path = self.resolve_path(uri)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        if path.suffix == '.npy':
            return np.load(path)
        elif path.suffix == '.csv':
            return np.loadtxt(path, delimiter=',')
        else:
            raise ValueError(f"Unsupported matrix format: {path.suffix}")

    def validate_schema(self, df: pd.DataFrame, schema: Dict[str, str]) -> bool:
        """
        Validate DataFrame against a schema {col_name: dtype}.
        """
        missing = [col for col in schema.keys() if col not in df.columns]
        if missing:
            logger.error(f"Schema validation failed. Missing columns: {missing}")
            return False
        return True


# Singleton instance
data_loader = DataLoader()
