from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List


@dataclass
class VizResult:
    """Standard result for scientific visualizations."""
    status: str
    message: str = ''
    fig_json: Optional[Any] = None
    html: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return all fields as a dictionary."""
        return asdict(self)


def get_viz_backend():
    """Mock backend for headless Mac operation."""
    return None


def get_plotly_backend():
    """Returns a mock plotly backend."""
    return None


def safe_df(data: Any):
    """Sanitize data into a Pandas DataFrame."""
    import pandas as pd
    import json
    try:
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            df = pd.DataFrame(data)
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(
                    lambda x: json.dumps(x, default=str) if isinstance(x, (dict, list, set)) else x
                )
        return df
    except Exception:
        return pd.DataFrame()
