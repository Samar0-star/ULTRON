"""
Base experiment interface for SVEL.
All experiments MUST subclass BaseExperiment and implement the run() method.
The system provides the environment; the experiment only provides the logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
import pandas as pd
import numpy as np
import os
import json
from scipy import stats

class BaseExperiment(ABC):
    def __init__(self, data_path: str, results_dir: str, loader_type: str):
        self.data_path = data_path
        self.results_dir = results_dir
        self.loader_type = loader_type
        self.df_main = None

    def load_data(self):
        """Standardized, immutable data loading with automatic delimiter sniffing."""
        if self.loader_type == "CSV":
            comp = 'gzip' if self.data_path.endswith('.gz') else None
            if self.data_path.endswith('.tsv'):
                self.df_main = pd.read_csv(self.data_path, sep='\t', compression=comp)
            else:
                self.df_main = pd.read_csv(self.data_path, sep=',', compression=comp)
                if self.df_main.shape[1] == 1 and len(self.df_main.columns) == 1:
                    col0 = str(self.df_main.columns[0])
                    if ';' in col0:
                        self.df_main = pd.read_csv(self.data_path, sep=';', compression=comp)
                    elif '\t' in col0:
                        self.df_main = pd.read_csv(self.data_path, sep='\t', compression=comp)
            print(f"[AUDIT] Physically loaded df_main. Shape: {self.df_main.shape}")
        else:
            print(f"[AUDIT] No auto-load for {self.loader_type}")

    @abstractmethod
    def run(self):
        """Experimental logic goes here."""
        pass

    def save_artifact(self, filename: str, data: Any):
        """Standardized artifact saving."""
        path = os.path.join(self.results_dir, filename)
        if isinstance(data, pd.DataFrame):
            data.to_csv(path, index=False)
        else:
            # Assume it's a plot/figure for now or handle appropriately
            data.savefig(path)
        print(f"[AUDIT] Saved artifact: {filename}")

    def report(self, results: Dict[str, Any]):
        """Standardized JSON reporting."""
        print(json.dumps(results, indent=2, default=str))
