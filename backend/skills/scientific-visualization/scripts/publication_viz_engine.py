#!/usr/bin/env python3
"""Deterministic publication-grade scientific visualization engine.

This module is deliberately housed inside the scientific-visualization skill so
the skill directory, not a downstream tool adapter, owns plot selection doctrine.
It builds audited Plotly figures from observed data without synthetic samples or
bar-chart fallbacks.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

OKABE_ITO = [
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#000000",  # black
]

MARKER_SYMBOLS = ["circle", "square", "diamond", "cross", "triangle-up", "x", "star"]
LINE_DASHES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]


def _human_label(column: str) -> str:
    """Convert data column names into compact scientific axis labels."""
    label = str(column).strip().replace("_", " ").replace("-", " ")
    replacements = {
        " pct": " (%)",
        " percent": " (%)",
        " percentage": " (%)",
        " um": " (uM)",
        " mm": " (mM)",
        " nm": " (nM)",
        " au": " (a.u.)",
        " a u": " (a.u.)",
    }
    lower = f" {label.lower()}"
    for suffix, unit in replacements.items():
        if lower.endswith(suffix):
            label = label[: -len(suffix.strip())].strip() + unit
            break
    return label[:1].upper() + label[1:]


def _short_label(column: str, max_len: int = 32) -> str:
    label = _human_label(column)
    return label if len(label) <= max_len else f"{label[: max_len - 1]}..."


def _rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return f"rgba(31,119,180,{alpha})"
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _is_name_like(column: str, patterns: List[str]) -> bool:
    normalized = str(column).lower()
    return any(pattern in normalized for pattern in patterns)


def _downsample_deterministic(df: pd.DataFrame, max_rows: int = 5000) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df
    step = max(1, math.ceil(len(df) / max_rows))
    return df.iloc[::step].head(max_rows).copy()


def _profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    working = df.copy()

    # Convert unhashable elements (dicts, lists, sets) to json strings
    for col in working.columns:
        if working[col].dtype == object:
            working[col] = working[col].apply(
                lambda x: json.dumps(x, default=str) if isinstance(x, (dict, list, set)) else x
            )

    # Promote obvious time/date columns without guessing every object column.
    for col in working.columns:
        if _is_name_like(col, ["date", "time", "timestamp"]):
            parsed = pd.to_datetime(working[col], errors="coerce")
            if parsed.notna().mean() >= 0.75:
                working[col] = parsed

    numeric_cols = [
        col for col in working.select_dtypes(include=["number", "bool"]).columns
        if working[col].notna().sum() > 0 and working[col].nunique(dropna=True) > 1
    ]
    datetime_cols = list(working.select_dtypes(include=["datetime", "datetimetz"]).columns)

    categorical_cols = []
    for col in working.columns:
        if col in numeric_cols or col in datetime_cols:
            continue
        try:
            nunique = working[col].nunique(dropna=True)
        except TypeError:
            working[col] = working[col].astype(str)
            nunique = working[col].nunique(dropna=True)
        if 1 < nunique <= min(50, max(10, len(working) // 2)):
            categorical_cols.append(col)

    replicate_cols = [
        col for col in working.columns
        if _is_name_like(col, ["replicate", "rep_", "rep ", "subject", "sample"])
    ]

    return {
        "df": working,
        "numeric": numeric_cols,
        "datetime": datetime_cols,
        "categorical": categorical_cols,
        "replicate": replicate_cols,
        "rows": int(len(working)),
        "columns": int(len(working.columns)),
        "null_fraction": {
            str(col): float(working[col].isna().mean())
            for col in working.columns
        },
    }


def _choose_numeric_column(
    numeric_cols: List[str],
    preferred_patterns: List[str],
    df: pd.DataFrame,
    exclude: Optional[List[str]] = None,
) -> Optional[str]:
    exclude = set(exclude or [])
    candidates = [col for col in numeric_cols if col not in exclude]
    for pattern in preferred_patterns:
        for col in candidates:
            if pattern in str(col).lower():
                return col
    if not candidates:
        return None
    return max(candidates, key=lambda col: float(pd.to_numeric(df[col], errors="coerce").var(skipna=True) or 0.0))


def _choose_group_column(profile: Dict[str, Any], preferred: Optional[List[str]] = None) -> Optional[str]:
    preferred = preferred or ["group", "condition", "treatment", "cell", "class", "label", "cohort", "category"]
    categorical = [col for col in profile["categorical"] if col not in profile["replicate"]]
    if not categorical:
        return None
    for pattern in preferred:
        for col in categorical:
            if pattern in str(col).lower():
                return col
    return min(categorical, key=lambda col: profile["df"][col].nunique(dropna=True))


def _resolve_groups(df: pd.DataFrame, group_col: Optional[str], max_groups: int = 8) -> List[Tuple[str, pd.DataFrame]]:
    if not group_col:
        return [("All observations", df)]
    values = list(df[group_col].dropna().astype(str).value_counts().head(max_groups).index)
    groups = []
    for value in values:
        groups.append((value, df[df[group_col].astype(str) == value]))
    return groups or [("All observations", df)]


def _spearman_or_pearson_corr(df: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
    subset = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    if len(subset) >= 4:
        return subset.corr(method="spearman").fillna(0)
    return subset.corr(method="pearson").fillna(0)


def _estimate_crossing(x_values: pd.Series, y_values: pd.Series, target: float, log_x: bool) -> Optional[float]:
    clean = pd.DataFrame({"x": x_values, "y": y_values}).dropna().sort_values("x")
    clean = clean.groupby("x", as_index=False)["y"].mean().sort_values("x")
    if len(clean) < 2:
        return None

    x = pd.to_numeric(clean["x"], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(clean["y"], errors="coerce").to_numpy(dtype=float)
    if log_x:
        valid = x > 0
        x = np.log10(x[valid])
        y = y[valid]
    if len(x) < 2:
        return None

    deltas = y - target
    for i in range(len(deltas) - 1):
        if deltas[i] == 0:
            crossing = x[i]
            return float(10 ** crossing if log_x else crossing)
        if deltas[i] * deltas[i + 1] < 0:
            denom = y[i + 1] - y[i]
            if denom == 0:
                continue
            crossing = x[i] + (target - y[i]) * (x[i + 1] - x[i]) / denom
            return float(10 ** crossing if log_x else crossing)
    return None


def _style_publication_figure(fig, title: str, height: int, width: int = 1100) -> None:
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        colorway=OKABE_ITO,
        width=width,
        height=height,
        title={
            "text": f"<b>{title}</b>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"family": "Arial, Helvetica, sans-serif", "size": 18, "color": "#111111"},
        },
        font={"family": "Arial, Helvetica, sans-serif", "size": 12, "color": "#111111"},
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.12,
            "xanchor": "center",
            "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.92)",
            "bordercolor": "rgba(0,0,0,0.18)",
            "borderwidth": 1,
        },
        margin={"l": 82, "r": 44, "t": 92, "b": 112},
        hovermode="closest",
    )
    fig.update_xaxes(
        showline=True,
        linewidth=1,
        linecolor="#222222",
        mirror=True,
        gridcolor="rgba(0,0,0,0.08)",
        zerolinecolor="rgba(0,0,0,0.16)",
        ticks="outside",
        title_font={"size": 13},
        tickfont={"size": 11},
    )
    fig.update_yaxes(
        showline=True,
        linewidth=1,
        linecolor="#222222",
        mirror=True,
        gridcolor="rgba(0,0,0,0.08)",
        zerolinecolor="rgba(0,0,0,0.16)",
        ticks="outside",
        title_font={"size": 13},
        tickfont={"size": 11},
    )


def _trace_type_counts(fig_json: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for trace in fig_json.get("data", []):
        trace_type = trace.get("type", "scatter")
        counts[trace_type] = counts.get(trace_type, 0) + 1
    return counts


def audit_plotly_json(fig_json: Dict[str, Any], allow_bar_only: bool = False) -> Dict[str, Any]:
    trace_counts = _trace_type_counts(fig_json)
    total_traces = sum(trace_counts.values())
    bar_traces = trace_counts.get("bar", 0)
    non_bar_traces = total_traces - bar_traces
    rich_types = {
        "scatter", "scattergl", "scatter3d", "heatmap", "contour", "surface",
        "violin", "box", "parcoords", "splom", "histogram", "histogram2d",
        "histogram2dcontour", "densitymapbox", "scatterternary"
    }
    rich_trace_count = sum(count for trace_type, count in trace_counts.items() if trace_type in rich_types)
    
    # BRUTAL DEEPMIND RIGOR: Reject any figure that contains even a single bar chart trace.
    # Bar charts are fundamentally banned in publication-grade scientific contexts here.
    has_bar = bar_traces > 0
    passes = not has_bar and rich_trace_count > 0

    return {
        "passes": bool(passes),
        "trace_counts": trace_counts,
        "total_traces": int(total_traces),
        "bar_traces": int(bar_traces),
        "non_bar_traces": int(non_bar_traces),
        "rich_trace_count": int(rich_trace_count),
        "bar_only": bool(has_bar), # We use this key for legacy compatibility but it flags ANY bar presence.
    }


def extract_plotly_json(stdout: str) -> Dict[str, Any]:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass

    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    start = stdout.find("{")
    end = stdout.rfind("}")
    if start >= 0 and end > start:
        return json.loads(stdout[start:end + 1])
    raise json.JSONDecodeError("No JSON object found in stdout", stdout, 0)


def _build_dose_response_figure(df: pd.DataFrame, profile: Dict[str, Any], intent: str, caption: str):
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    numeric = profile["numeric"]
    x_col = _choose_numeric_column(numeric, ["dose", "concentration", "conc", "drug", "amount"], df)
    y_col = _choose_numeric_column(
        numeric,
        ["viability", "response", "inhibition", "survival", "activity", "signal", "effect"],
        df,
        exclude=[x_col] if x_col else None,
    )
    if not x_col or not y_col:
        raise ValueError("Dose-response figure requested without dose and response columns.")

    group_col = _choose_group_column(profile, ["cell", "treatment", "condition", "group", "compound"])
    log_x = bool((pd.to_numeric(df[x_col], errors="coerce") > 0).all() and _is_name_like(x_col, ["dose", "conc", "concentration"]))
    target = 50.0 if pd.to_numeric(df[y_col], errors="coerce").between(-5, 105).mean() > 0.8 else float(pd.to_numeric(df[y_col], errors="coerce").median())
    crossing_label = "IC50" if target == 50.0 else "Half-response"

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"colspan": 2, "type": "xy"}, None], [{"type": "xy"}, {"type": "xy"}]],
        row_heights=[0.62, 0.38],
        vertical_spacing=0.16,
        horizontal_spacing=0.12,
        subplot_titles=[
            "A. Raw response with measured uncertainty",
            "B. Distribution of observed responses",
            f"C. {crossing_label} estimated from observed means",
        ],
    )

    groups = _resolve_groups(df, group_col)
    crossing_rows = []

    for idx, (group_name, sub) in enumerate(groups):
        color = OKABE_ITO[idx % len(OKABE_ITO)]
        marker = MARKER_SYMBOLS[idx % len(MARKER_SYMBOLS)]
        dash = LINE_DASHES[idx % len(LINE_DASHES)]
        clean = sub[[x_col, y_col]].copy()
        clean[x_col] = pd.to_numeric(clean[x_col], errors="coerce")
        clean[y_col] = pd.to_numeric(clean[y_col], errors="coerce")
        clean = clean.dropna().sort_values(x_col)
        if clean.empty:
            continue

        x_raw = np.log10(clean[x_col]) if log_x else clean[x_col]
        fig.add_trace(
            go.Scatter(
                x=x_raw,
                y=clean[y_col],
                mode="markers",
                name=f"{group_name} raw",
                legendgroup=group_name,
                marker={"color": color, "symbol": marker, "size": 7, "opacity": 0.48, "line": {"color": "white", "width": 0.7}},
                showlegend=False,
                hovertemplate=f"{_human_label(x_col)}=%{{x:.3g}}<br>{_human_label(y_col)}=%{{y:.3g}}<extra>{group_name}</extra>",
            ),
            row=1,
            col=1,
        )

        summary = (
            clean.groupby(x_col, as_index=False)[y_col]
            .agg(["mean", "std", "count"])
            .reset_index()
            .sort_values(x_col)
        )
        summary["std"] = summary["std"].fillna(0.0)
        summary["ci95"] = 1.96 * summary["std"] / np.sqrt(summary["count"].clip(lower=1))
        x_summary = np.log10(summary[x_col]) if log_x else summary[x_col]
        upper = summary["mean"] + summary["ci95"]
        lower = summary["mean"] - summary["ci95"]

        if len(summary) > 1 and summary["count"].sum() > len(summary):
            fig.add_trace(
                go.Scatter(
                    x=list(x_summary) + list(x_summary[::-1]),
                    y=list(upper) + list(lower[::-1]),
                    fill="toself",
                    fillcolor=_rgba(color, 0.18),
                    line={"width": 0},
                    hoverinfo="skip",
                    name=f"{group_name} 95% CI",
                    legendgroup=group_name,
                    showlegend=False,
                ),
                row=1,
                col=1,
            )

        fig.add_trace(
            go.Scatter(
                x=x_summary,
                y=summary["mean"],
                mode="lines+markers",
                name=f"{group_name} mean",
                legendgroup=group_name,
                line={"color": color, "width": 2.4, "dash": dash},
                marker={"symbol": marker, "size": 8, "line": {"color": "white", "width": 0.8}},
                hovertemplate=f"Mean {y_col}: %{{y:.3g}}<br>n=%{{customdata}}<extra>{group_name}</extra>",
                customdata=summary["count"],
            ),
            row=1,
            col=1,
        )

        crossing = _estimate_crossing(summary[x_col], summary["mean"], target, log_x)
        if crossing is not None and np.isfinite(crossing):
            crossing_rows.append({"group": group_name, "crossing": crossing, "color": color})
            x_cross_plot = math.log10(crossing) if log_x and crossing > 0 else crossing
            fig.add_trace(
                go.Scatter(
                    x=[x_cross_plot, x_cross_plot],
                    y=[float(clean[y_col].min()), target],
                    mode="lines",
                    line={"color": color, "width": 1.2, "dash": "dot"},
                    legendgroup=group_name,
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1,
                col=1,
            )

        fig.add_trace(
            go.Violin(
                y=clean[y_col],
                x=[group_name] * len(clean),
                name=group_name,
                legendgroup=group_name,
                showlegend=False,
                box_visible=True,
                meanline_visible=True,
                points="all",
                jitter=0.24,
                marker={"color": color, "opacity": 0.45, "size": 4},
                line={"color": color},
            ),
            row=2,
            col=1,
        )

    if crossing_rows:
        crossing_df = pd.DataFrame(crossing_rows)
        fig.add_trace(
            go.Scatter(
                x=crossing_df["crossing"],
                y=crossing_df["group"],
                mode="markers+text",
                text=[f"{v:.3g}" for v in crossing_df["crossing"]],
                textposition="middle right",
                marker={
                    "color": list(crossing_df["color"]),
                    "size": 12,
                    "line": {"color": "white", "width": 1},
                },
                showlegend=False,
                hovertemplate=f"{crossing_label}: %{{x:.3g}}<extra></extra>",
            ),
            row=2,
            col=2,
        )
    else:
        fig.add_annotation(
            text=f"No {crossing_label} crossing observed in measured range",
            xref="x3 domain",
            yref="y3 domain",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 12, "color": "#555555"},
        )

    fig.add_hline(
        y=target,
        row=1,
        col=1,
        line={"color": "rgba(0,0,0,0.35)", "width": 1, "dash": "dash"},
        annotation_text=f"{crossing_label} target",
        annotation_position="top right",
    )

    x_title = f"log10[{_human_label(x_col)}]" if log_x else _human_label(x_col)
    fig.update_xaxes(title_text=x_title, row=1, col=1)
    fig.update_yaxes(title_text=_human_label(y_col), row=1, col=1)
    fig.update_xaxes(title_text=group_col and _human_label(group_col) or "Group", row=2, col=1)
    fig.update_yaxes(title_text=_human_label(y_col), row=2, col=1)
    fig.update_xaxes(title_text=_human_label(x_col), type="log" if log_x else None, row=2, col=2)
    fig.update_yaxes(title_text=group_col and _human_label(group_col) or "Group", row=2, col=2)

    _style_publication_figure(fig, caption, height=860)
    audit = {
        "plot_family": "dose_response",
        "selection_reason": "Detected concentration/dose axis and response-like endpoint.",
        "x": x_col,
        "y": y_col,
        "group": group_col,
        "uncertainty": "Mean +/- 95% CI from observed replicate measurements only.",
        "synthetic_points": 0,
        "bar_traces": 0,
    }
    fig.update_layout(meta=audit)
    return fig, audit


def _build_multivariate_figure(df: pd.DataFrame, profile: Dict[str, Any], intent: str, caption: str):
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    numeric = profile["numeric"]
    if len(numeric) < 2:
        raise ValueError("Multivariate figure requires at least two numeric columns.")

    x_col = _choose_numeric_column(numeric, ["time", "year", "epoch", "step", "dose", "concentration", "conc"], df)
    y_col = _choose_numeric_column(
        numeric,
        ["response", "score", "metric", "value", "accuracy", "loss", "intensity", "effect", "confidence", "priority", "novelty"],
        df,
        exclude=[x_col] if x_col else None,
    )
    if x_col == y_col or not y_col:
        y_col = [col for col in numeric if col != x_col][0]

    group_col = _choose_group_column(profile)
    plot_df = _downsample_deterministic(df, 3000)

    fig = make_subplots(
        rows=2,
        cols=3,
        specs=[
            [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}, {"type": "domain"}],
        ],
        vertical_spacing=0.17,
        horizontal_spacing=0.12,
        subplot_titles=[
            "A. Raw relationship with density",
            "B. Correlation structure",
            "C. Empirical cumulative distribution",
            "D. Distribution by group",
            "E. Principal-component projection",
            "F. Parallel-coordinate feature geometry",
        ],
    )

    groups = _resolve_groups(plot_df, group_col)
    density_added = False
    for idx, (group_name, sub) in enumerate(groups):
        color = OKABE_ITO[idx % len(OKABE_ITO)]
        clean = sub[[x_col, y_col]].copy()
        clean[x_col] = pd.to_numeric(clean[x_col], errors="coerce")
        clean[y_col] = pd.to_numeric(clean[y_col], errors="coerce")
        clean = clean.dropna()
        if clean.empty:
            continue
        if len(clean) >= 10 and clean[x_col].nunique() > 3 and clean[y_col].nunique() > 3:
            fig.add_trace(
                go.Histogram2dContour(
                    x=clean[x_col],
                    y=clean[y_col],
                    name=f"{group_name} density",
                    contours={"coloring": "lines", "showlabels": False},
                    line={"color": _rgba(color, 0.58), "width": 0.8},
                    opacity=0.42,
                    showscale=False,
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1,
                col=1,
            )
            density_added = True
        fig.add_trace(
            go.Scatter(
                x=clean[x_col],
                y=clean[y_col],
                mode="markers",
                name=group_name,
                marker={
                    "color": color,
                    "size": 6,
                    "opacity": 0.64,
                    "symbol": MARKER_SYMBOLS[idx % len(MARKER_SYMBOLS)],
                    "line": {"color": "white", "width": 0.5},
                },
                hovertemplate=f"{_human_label(x_col)}=%{{x:.3g}}<br>{_human_label(y_col)}=%{{y:.3g}}<extra>{group_name}</extra>",
            ),
            row=1,
            col=1,
        )
        if len(clean) >= 3 and clean[x_col].nunique() > 1:
            x_fit = np.linspace(float(clean[x_col].min()), float(clean[x_col].max()), 60)
            coef = np.polyfit(clean[x_col], clean[y_col], deg=1)
            y_fit = np.polyval(coef, x_fit)
            fig.add_trace(
                go.Scatter(
                    x=x_fit,
                    y=y_fit,
                    mode="lines",
                    name=f"{group_name} least-squares trend",
                    line={"color": color, "width": 1.4, "dash": LINE_DASHES[idx % len(LINE_DASHES)]},
                    legendgroup=group_name,
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1,
                col=1,
            )

        values = pd.to_numeric(sub[y_col], errors="coerce").dropna().sort_values()
        if not values.empty:
            ecdf = np.arange(1, len(values) + 1) / len(values)
            fig.add_trace(
                go.Scatter(
                    x=values,
                    y=ecdf,
                    mode="lines+markers",
                    name=f"{group_name} ECDF",
                    line={"color": color, "width": 1.6, "dash": LINE_DASHES[idx % len(LINE_DASHES)]},
                    marker={"size": 4, "symbol": MARKER_SYMBOLS[idx % len(MARKER_SYMBOLS)]},
                    showlegend=False,
                    hovertemplate=f"{_human_label(y_col)}=%{{x:.3g}}<br>ECDF=%{{y:.2f}}<extra>{group_name}</extra>",
                ),
                row=1,
                col=3,
            )

    corr_cols = numeric[: min(10, len(numeric))]
    corr = _spearman_or_pearson_corr(df, corr_cols)
    fig.add_trace(
        go.Heatmap(
            z=corr.values,
            x=[_short_label(col, 18) for col in corr.columns],
            y=[_short_label(col, 18) for col in corr.index],
            zmin=-1,
            zmax=1,
            zmid=0,
            colorscale="RdBu",
            colorbar={"title": {"text": "rho"}, "len": 0.28, "y": 0.82},
            hovertemplate="%{y} vs %{x}<br>rho=%{z:.2f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    if group_col:
        for idx, (group_name, sub) in enumerate(groups):
            values = pd.to_numeric(sub[y_col], errors="coerce").dropna()
            if values.empty:
                continue
            fig.add_trace(
                go.Violin(
                    y=values,
                    x=[group_name] * len(values),
                    name=f"{group_name} distribution",
                    showlegend=False,
                    box_visible=True,
                    meanline_visible=True,
                    points="all",
                    jitter=0.22,
                    marker={"color": OKABE_ITO[idx % len(OKABE_ITO)], "opacity": 0.46, "size": 4},
                    line={"color": OKABE_ITO[idx % len(OKABE_ITO)]},
                ),
                row=2,
                col=1,
            )
    else:
        melted = df[corr_cols[: min(5, len(corr_cols))]].melt(var_name="metric", value_name="value").dropna()
        for idx, col in enumerate(melted["metric"].unique()):
            values = melted[melted["metric"] == col]["value"]
            fig.add_trace(
                go.Violin(
                    y=values,
                    x=[_short_label(col, 14)] * len(values),
                    showlegend=False,
                    box_visible=True,
                    meanline_visible=True,
                    points=False,
                    marker={"color": OKABE_ITO[idx % len(OKABE_ITO)], "opacity": 0.42},
                    line={"color": OKABE_ITO[idx % len(OKABE_ITO)]},
                ),
                row=2,
                col=1,
            )

    pca_cols = corr_cols[: min(8, len(corr_cols))]
    pca_df = _downsample_deterministic(df[pca_cols + ([group_col] if group_col else [])].copy(), 1200)
    matrix = pca_df[pca_cols].apply(pd.to_numeric, errors="coerce")
    matrix = matrix.fillna(matrix.median(numeric_only=True))
    std = matrix.std(axis=0, ddof=0).replace(0, 1)
    centered = (matrix - matrix.mean(axis=0)) / std
    pca_ok = len(centered) >= 3 and centered.shape[1] >= 2
    explained_ratio = [0.0, 0.0]
    if pca_ok:
        _, singular_values, vt = np.linalg.svd(centered.to_numpy(dtype=float), full_matrices=False)
        scores = centered.to_numpy(dtype=float) @ vt[:2].T
        variance = singular_values ** 2
        total_variance = float(variance.sum()) or 1.0
        explained_ratio = [float(variance[0] / total_variance), float(variance[1] / total_variance)]
        pca_plot = pd.DataFrame({"PC1": scores[:, 0], "PC2": scores[:, 1]})
        if group_col and group_col in pca_df:
            pca_plot[group_col] = pca_df[group_col].astype(str).to_numpy()
            for idx, (group_name, sub) in enumerate(pca_plot.groupby(group_col, sort=False)):
                color = OKABE_ITO[idx % len(OKABE_ITO)]
                fig.add_trace(
                    go.Scatter(
                        x=sub["PC1"],
                        y=sub["PC2"],
                        mode="markers",
                        name=f"{group_name} PCA",
                        marker={"color": color, "size": 6, "opacity": 0.62, "symbol": MARKER_SYMBOLS[idx % len(MARKER_SYMBOLS)]},
                        showlegend=False,
                        hovertemplate="PC1=%{x:.3g}<br>PC2=%{y:.3g}<extra>" + str(group_name) + "</extra>",
                    ),
                    row=2,
                    col=2,
                )
        else:
            fig.add_trace(
                go.Scatter(
                    x=pca_plot["PC1"],
                    y=pca_plot["PC2"],
                    mode="markers",
                    name="PCA projection",
                    marker={"color": pca_df[y_col] if y_col in pca_df else OKABE_ITO[4], "colorscale": "Viridis", "size": 6, "opacity": 0.62, "showscale": True},
                    showlegend=False,
                    hovertemplate="PC1=%{x:.3g}<br>PC2=%{y:.3g}<extra></extra>",
                ),
                row=2,
                col=2,
            )

    par_df = _downsample_deterministic(df[corr_cols + ([group_col] if group_col else [])].copy(), 800)
    dimensions = []
    for col in corr_cols[: min(6, len(corr_cols))]:
        values = pd.to_numeric(par_df[col], errors="coerce")
        fill_value = float(values.median()) if values.notna().any() else 0.0
        values = values.fillna(fill_value)
        dimensions.append({"label": _short_label(col, 20), "values": values})

    if group_col and group_col in par_df:
        codes = pd.Categorical(par_df[group_col].astype(str)).codes
        line = {"color": codes, "colorscale": "Viridis", "showscale": True, "colorbar": {"title": {"text": _short_label(group_col, 16)}}}
    else:
        color_values = pd.to_numeric(par_df[y_col], errors="coerce")
        color_values = color_values.fillna(float(color_values.median()) if color_values.notna().any() else 0.0)
        line = {"color": color_values, "colorscale": "Viridis", "showscale": True, "colorbar": {"title": {"text": _short_label(y_col, 16)}}}

    fig.add_trace(
        go.Parcoords(
            line=line,
            dimensions=dimensions,
            labelfont={"size": 10},
            tickfont={"size": 9},
        ),
        row=2,
        col=3,
    )

    fig.update_xaxes(title_text=_human_label(x_col), row=1, col=1)
    fig.update_yaxes(title_text=_human_label(y_col), row=1, col=1)
    fig.update_xaxes(title_text=_human_label(y_col), row=1, col=3)
    fig.update_yaxes(title_text="Empirical cumulative probability", row=1, col=3)
    fig.update_xaxes(title_text=group_col and _human_label(group_col) or "Metric", row=2, col=1)
    fig.update_yaxes(title_text=_human_label(y_col), row=2, col=1)
    fig.update_xaxes(title_text=f"PC1 ({explained_ratio[0] * 100:.1f}% var.)", row=2, col=2)
    fig.update_yaxes(title_text=f"PC2 ({explained_ratio[1] * 100:.1f}% var.)", row=2, col=2)

    _style_publication_figure(fig, caption, height=980, width=1380)
    audit = {
        "plot_family": "multivariate",
        "selection_reason": "Detected two or more numeric variables; showing raw relation, density, ECDF, correlation, distributions, PCA projection, and feature geometry.",
        "x": x_col,
        "y": y_col,
        "group": group_col,
        "correlation": "spearman" if len(df) >= 4 else "pearson",
        "density_contours": bool(density_added),
        "pca_projection": bool(pca_ok),
        "pca_explained_variance": explained_ratio,
        "synthetic_points": 0,
        "bar_traces": 0,
    }
    fig.update_layout(meta=audit)
    return fig, audit


def _build_distribution_figure(df: pd.DataFrame, profile: Dict[str, Any], intent: str, caption: str):
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    numeric = profile["numeric"]
    if not numeric:
        raise ValueError("Distribution figure requires a numeric column.")
    y_col = _choose_numeric_column(
        numeric,
        ["response", "score", "metric", "value", "accuracy", "loss", "intensity", "effect", "confidence", "priority", "novelty"],
        df,
    )
    group_col = _choose_group_column(profile)

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "xy"}, {"type": "xy"}]],
        horizontal_spacing=0.14,
        subplot_titles=["A. Distribution with individual observations", "B. Empirical cumulative distribution"],
    )

    groups = _resolve_groups(df, group_col)
    for idx, (group_name, sub) in enumerate(groups):
        color = OKABE_ITO[idx % len(OKABE_ITO)]
        values = pd.to_numeric(sub[y_col], errors="coerce").dropna().sort_values()
        if values.empty:
            continue
        fig.add_trace(
            go.Violin(
                y=values,
                x=[group_name] * len(values),
                name=group_name,
                box_visible=True,
                meanline_visible=True,
                points="all",
                jitter=0.26,
                marker={"color": color, "opacity": 0.48, "size": 5},
                line={"color": color},
            ),
            row=1,
            col=1,
        )
        ecdf = np.arange(1, len(values) + 1) / len(values)
        fig.add_trace(
            go.Scatter(
                x=values,
                y=ecdf,
                mode="lines",
                name=f"{group_name} ECDF",
                line={"color": color, "width": 2, "dash": LINE_DASHES[idx % len(LINE_DASHES)]},
                showlegend=False,
                hovertemplate=f"{_human_label(y_col)}=%{{x:.3g}}<br>ECDF=%{{y:.2f}}<extra>{group_name}</extra>",
            ),
            row=1,
            col=2,
        )

    fig.update_xaxes(title_text=group_col and _human_label(group_col) or "Observed sample", row=1, col=1)
    fig.update_yaxes(title_text=_human_label(y_col), row=1, col=1)
    fig.update_xaxes(title_text=_human_label(y_col), row=1, col=2)
    fig.update_yaxes(title_text="Empirical cumulative probability", row=1, col=2)

    _style_publication_figure(fig, caption, height=560)
    audit = {
        "plot_family": "distribution",
        "selection_reason": "Detected one primary numeric endpoint; showing raw observations and ECDF instead of a summary bar chart.",
        "y": y_col,
        "group": group_col,
        "synthetic_points": 0,
        "bar_traces": 0,
    }
    fig.update_layout(meta=audit)
    return fig, audit


def _build_categorical_figure(df: pd.DataFrame, profile: Dict[str, Any], intent: str, caption: str):
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    categorical = profile["categorical"]
    if len(categorical) >= 2:
        row_col, col_col = categorical[:2]
        table = pd.crosstab(df[row_col].astype(str), df[col_col].astype(str))
        table = table.loc[table.sum(axis=1).sort_values(ascending=False).head(20).index]
        table = table[table.sum(axis=0).sort_values(ascending=False).head(20).index]
        fig = make_subplots(rows=1, cols=1, subplot_titles=["A. Category co-occurrence heatmap"])
        fig.add_trace(
            go.Heatmap(
                z=table.values,
                x=list(table.columns),
                y=list(table.index),
                colorscale="Viridis",
                colorbar={"title": {"text": "Count"}},
                hovertemplate=f"{_human_label(row_col)}=%{{y}}<br>{_human_label(col_col)}=%{{x}}<br>count=%{{z}}<extra></extra>",
            )
        )
        fig.update_xaxes(title_text=_human_label(col_col))
        fig.update_yaxes(title_text=_human_label(row_col))
        plot_family = "categorical_heatmap"
        reason = "Detected two categorical variables; using co-occurrence heatmap instead of count bars."
    else:
        col = categorical[0] if categorical else df.columns[0]
        counts = df[col].astype(str).value_counts().head(24).sort_values()
        fig = make_subplots(rows=1, cols=1, subplot_titles=["A. Ranked categorical abundance"])
        y_positions = list(range(len(counts)))
        for y_pos, count in zip(y_positions, counts.values):
            fig.add_shape(
                type="line",
                x0=0,
                x1=float(count),
                y0=y_pos,
                y1=y_pos,
                xref="x",
                yref="y",
                line={"color": "rgba(0,0,0,0.22)", "width": 2},
            )
        fig.add_trace(
            go.Scatter(
                x=counts.values,
                y=y_positions,
                mode="markers+text",
                text=[str(v) for v in counts.values],
                textposition="middle right",
                marker={
                    "color": counts.values, 
                    "colorscale": "Viridis", 
                    "size": 12, 
                    "line": {"color": "white", "width": 1.5},
                    "showscale": True,
                    "colorbar": {"title": "Frequency"}
                },
                showlegend=False,
                hovertemplate="count=%{x}<extra></extra>",
            )
        )
        fig.update_yaxes(tickmode="array", tickvals=y_positions, ticktext=list(counts.index), title_text=_human_label(col))
        fig.update_xaxes(title_text="Count")
        plot_family = "categorical_lollipop"
        reason = "Only categorical data detected; using lollipop marks instead of bars."

    _style_publication_figure(fig, caption, height=700)
    audit = {
        "plot_family": plot_family,
        "selection_reason": reason,
        "synthetic_points": 0,
        "bar_traces": 0,
    }
    fig.update_layout(meta=audit)
    return fig, audit


def build_publication_grade_figure(df: pd.DataFrame, intent: str, caption: str):
    profile = _profile_dataframe(df)
    working = profile["df"]
    numeric = profile["numeric"]
    intent_lower = intent.lower()

    dose_col = _choose_numeric_column(numeric, ["dose", "concentration", "conc"], working)
    response_col = _choose_numeric_column(numeric, ["response", "viability", "inhibition", "survival", "activity"], working, exclude=[dose_col] if dose_col else None)
    if dose_col and response_col and (
        _is_name_like(dose_col, ["dose", "conc", "concentration"]) or
        any(term in intent_lower for term in ["dose", "concentration", "ic50", "response curve"])
    ):
        return _build_dose_response_figure(working, profile, intent, caption)

    if len(numeric) >= 2:
        return _build_multivariate_figure(working, profile, intent, caption)

    if len(numeric) == 1:
        return _build_distribution_figure(working, profile, intent, caption)

    return _build_categorical_figure(working, profile, intent, caption)


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build an audited publication-grade scientific Plotly figure from a CSV file."
    )
    parser.add_argument("csv", help="Input CSV file with observed data.")
    parser.add_argument("--intent", default="publication scientific visualization", help="Scientific visualization intent.")
    parser.add_argument("--caption", default="Publication figure", help="Figure title/caption text.")
    parser.add_argument("--html", default="publication_figure.html", help="Output HTML path.")
    parser.add_argument("--json", default="", help="Optional output Plotly JSON path.")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    fig, audit = build_publication_grade_figure(df, args.intent, args.caption)
    fig_json = json.loads(fig.to_json())
    audit = {**audit, **audit_plotly_json(fig_json)}

    html_path = Path(args.html)
    fig.write_html(html_path, include_plotlyjs="cdn", full_html=True)
    if args.json:
        Path(args.json).write_text(json.dumps(fig_json), encoding="utf-8")

    print(json.dumps({"html": str(html_path), "audit": audit}, indent=2))


if __name__ == "__main__":
    _main()
