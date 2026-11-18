# -*- coding: utf-8 -*-
"""
Discovery Rigor Module - The "Igor Audit" Physical Grounding Bridge.
===================================================================

Provides empirical validation for GNN "dreams" using real physical data.
Specifically optimized for transcriptomic correlation graphs.
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List
from pathlib import Path

from backend.core.validation.statistical_grounding import StatisticalGroundingValidator

logger = logging.getLogger(__name__)

class CorrelationChecker:
    """
    Computes empirical correlations between entities (e.g. genes) 
    to validate GNN predictions.
    """
    
    def __init__(self, data_path: str, compression: Optional[str] = "gzip"):
        self.data_path = data_path
        self.compression = compression
        self.df: Optional[pd.DataFrame] = None
        self.validator = StatisticalGroundingValidator(n_permutations=100)
        self._load_data()

    def _load_data(self):
        """Lazy load and cache the dataset matrix, supporting both column and index formats."""
        try:
            logger.info(f" [RIGOR] Loading dataset matrix from {self.data_path}...")
            df = pd.read_csv(self.data_path, compression=self.compression)
            # If first column is non-numeric (e.g. gene identifiers), use as index
            if df.shape[1] > 1 and not pd.api.types.is_numeric_dtype(df.iloc[:, 0].dtype):
                df = df.set_index(df.columns[0])
            self.df = df
            logger.info(f" [RIGOR] Matrix loaded: {self.df.shape[0]} rows, {self.df.shape[1]} columns.")
        except Exception as e:
            logger.error(f" [RIGOR] Failed to load data matrix: {e}")
            self.df = None

    def check(self, node_a: str, node_b: str) -> Optional[float]:
        """
        Returns absolute Pearson correlation between node_a and node_b.
        Supports both column features (tabular physical data) and row entities (gene expression).
        Returns None if nodes not found.
        """
        if self.df is None or len(node_a) < 2 or len(node_b) < 2:
            return None

        def _get_series(node_query: str) -> Optional[np.ndarray]:
            nq = node_query.strip().lower()
            # 1. Check columns (e.g. materials science, tabular physics)
            col_matches = [c for c in self.df.columns if str(c).lower() == nq]
            if not col_matches:
                col_matches = [c for c in self.df.columns if nq in str(c).lower() or (len(str(c)) >= 3 and str(c).lower() in nq)]
            if col_matches:
                val = self.df[col_matches[0]]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[:, 0]
                arr = pd.to_numeric(val, errors="coerce").to_numpy(dtype=float)
                return arr.flatten()

            # 2. Check index (e.g. transcriptomic gene matrices)
            idx_matches = [idx for idx in self.df.index if str(idx).lower() == nq]
            if not idx_matches and len(nq) >= 3:
                idx_matches = [idx for idx in self.df.index if nq in str(idx).lower() or str(idx).lower() in nq]
            if idx_matches:
                val = self.df.loc[idx_matches[0]]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                arr = pd.to_numeric(val, errors="coerce").to_numpy(dtype=float)
                return arr.flatten()

            return None

        try:
            series_a = _get_series(node_a)
            series_b = _get_series(node_b)

            if series_a is None or series_b is None:
                return None

            valid_mask = np.isfinite(series_a) & np.isfinite(series_b)
            if np.sum(valid_mask) < 3:
                return None

            clean_a = series_a[valid_mask]
            clean_b = series_b[valid_mask]
            if np.std(clean_a) < 1e-8 or np.std(clean_b) < 1e-8:
                return 0.0

            corr = np.corrcoef(clean_a, clean_b)[0, 1]
            if np.isnan(corr):
                return 0.0
            return abs(float(corr))
        except Exception as e:
            logger.warning(f" [RIGOR] Correlation computation failed for {node_a}-{node_b}: {e}")
            return None

def get_gnn_empirical_checker(research_question: str) -> Optional[callable]:
    """
    Factory to create a checker function suitable for GNN Oracle.
    """
    from backend.core.data.data_resolver import resolve_data_for_hypothesis

    try:
        # Resolve data relevant to the research question
        data_paths = resolve_data_for_hypothesis(research_question)
        if not data_paths:
            return None
            
        primary_path = list(data_paths.values())[0]
        compression = "gzip" if primary_path.endswith(".gz") else None
        
        checker = CorrelationChecker(primary_path, compression=compression)
        return checker.check
    except Exception as e:
        logger.warning(f" [RIGOR] Could not initialize empirical checker: {e}")
        return None
