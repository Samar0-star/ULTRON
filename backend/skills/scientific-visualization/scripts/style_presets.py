#!/usr/bin/env python3
"""Matplotlib style presets for publication-grade scientific figures.

The presets here are deliberately conservative: small readable typography,
vector-safe fonts, colorblind-safe cycles, no decorative chart junk, and
settings that survive journal export.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
from cycler import Cycler


OKABE_ITO_COLORS = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#000000",
]
WONG_COLORS = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]
TOL_BRIGHT = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]
TOL_MUTED = ["#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255", "#AA4499"]
TOL_HIGH_CONTRAST = ["#004488", "#DDAA33", "#BB5566"]

PALETTES = {
    "okabe_ito": OKABE_ITO_COLORS,
    "wong": WONG_COLORS,
    "tol_bright": TOL_BRIGHT,
    "tol_muted": TOL_MUTED,
    "tol_high_contrast": TOL_HIGH_CONTRAST,
}

JOURNAL_CONFIGS = {
    "nature": {"single_width": 89, "onehalf_width": 120, "double_width": 183, "max_height": 247, "style": "nature"},
    "science": {"single_width": 55, "onehalf_width": 120, "double_width": 175, "max_height": 233, "style": "science"},
    "cell": {"single_width": 85, "onehalf_width": 120, "double_width": 178, "max_height": 230, "style": "cell"},
    "plos": {"single_width": 83, "onehalf_width": 114, "double_width": 173, "max_height": 233, "style": "default"},
    "acs": {"single_width": 82.5, "onehalf_width": 120, "double_width": 178, "max_height": 247, "style": "default"},
    "ieee": {"single_width": 89, "onehalf_width": 120, "double_width": 182, "max_height": 230, "style": "default"},
}


def get_base_style(data_dense: bool = False) -> Dict[str, Any]:
    """Return base rcParams for manuscript figures."""
    marker_size = 3.2 if data_dense else 4.0
    line_width = 1.15 if data_dense else 1.4
    grid_alpha = "0.10" if data_dense else "0.08"

    return {
        "figure.dpi": 120,
        "figure.facecolor": "white",
        "figure.autolayout": False,
        "figure.constrained_layout.use": True,
        "font.size": 8,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.linewidth": 0.6,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "axes.labelweight": "normal",
        "axes.titleweight": "normal",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#111111",
        "axes.labelcolor": "#111111",
        "axes.axisbelow": True,
        "axes.prop_cycle": mpl.cycler(color=OKABE_ITO_COLORS),
        "axes.grid": data_dense,
        "grid.color": "#000000",
        "grid.alpha": grid_alpha,
        "grid.linewidth": 0.35,
        "xtick.major.size": 3,
        "xtick.minor.size": 1.8,
        "xtick.major.width": 0.6,
        "xtick.minor.width": 0.45,
        "xtick.labelsize": 7,
        "xtick.direction": "out",
        "ytick.major.size": 3,
        "ytick.minor.size": 1.8,
        "ytick.major.width": 0.6,
        "ytick.minor.width": 0.45,
        "ytick.labelsize": 7,
        "ytick.direction": "out",
        "lines.linewidth": line_width,
        "lines.markersize": marker_size,
        "lines.markeredgewidth": 0.45,
        "patch.linewidth": 0.6,
        "legend.fontsize": 7,
        "legend.frameon": False,
        "legend.handlelength": 1.4,
        "legend.borderaxespad": 0.4,
        "savefig.dpi": 600,
        "savefig.format": "pdf",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "savefig.transparent": False,
        "savefig.facecolor": "white",
        "image.cmap": "viridis",
        "image.aspect": "auto",
        "contour.linewidth": 0.7,
    }


def _style_overrides(style_name: str) -> Dict[str, Any]:
    style = style_name.lower()
    if style == "nature":
        return {
            "font.size": 7,
            "axes.labelsize": 7,
            "axes.titlesize": 7,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 6,
            "savefig.dpi": 600,
        }
    if style == "science":
        return {
            "font.size": 7,
            "axes.labelsize": 7,
            "axes.titlesize": 7,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 6,
            "savefig.dpi": 600,
        }
    if style == "cell":
        return {
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "savefig.dpi": 600,
        }
    if style == "minimal":
        return {
            "axes.grid": False,
            "axes.linewidth": 0.75,
            "xtick.major.width": 0.75,
            "ytick.major.width": 0.75,
        }
    if style == "presentation":
        return {
            "font.size": 14,
            "axes.labelsize": 15,
            "axes.titlesize": 16,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "legend.fontsize": 12,
            "axes.linewidth": 1.1,
            "lines.linewidth": 2.0,
            "lines.markersize": 6.5,
            "savefig.dpi": 300,
        }
    if style != "default":
        raise ValueError("Unknown style '%s'. Use default, nature, science, cell, minimal, or presentation." % style_name)
    return {}


def apply_publication_style(style_name: str = "default", data_dense: bool = False) -> Dict[str, Any]:
    """Apply a publication rcParams profile and return the applied params."""
    style = get_base_style(data_dense=data_dense)
    style.update(_style_overrides(style_name))
    plt.rcParams.update(style)
    return style


def set_color_palette(palette_name: str = "okabe_ito", n: int | None = None) -> List[str]:
    """Set a colorblind-safe categorical cycle."""
    key = palette_name.lower().replace("-", "_")
    if key not in PALETTES:
        raise ValueError(f"Unknown palette '{palette_name}'. Available: {', '.join(PALETTES)}")
    colors = PALETTES[key]
    if n is not None:
        colors = [colors[i % len(colors)] for i in range(n)]
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=colors)
    return colors


def figure_size_for_journal(journal: str = "nature", figure_width: str = "single", aspect: float = 0.72) -> Tuple[float, float]:
    """Return figure size in inches for a journal column width."""
    journal_key = journal.lower()
    if journal_key not in JOURNAL_CONFIGS:
        raise ValueError(f"Unknown journal '{journal}'. Available: {', '.join(JOURNAL_CONFIGS)}")
    width_key = {
        "single": "single_width",
        "onehalf": "onehalf_width",
        "1.5": "onehalf_width",
        "double": "double_width",
        "full": "double_width",
    }.get(figure_width.lower())
    if width_key is None:
        raise ValueError("figure_width must be single, onehalf, 1.5, double, or full")
    width_mm = JOURNAL_CONFIGS[journal_key][width_key]
    width_in = float(width_mm) / 25.4
    return width_in, width_in * aspect


def configure_for_journal(journal: str, figure_width: str = "single", aspect: float = 0.72, data_dense: bool = False) -> Tuple[float, float]:
    """Apply journal style and set default figure size."""
    journal_key = journal.lower()
    if journal_key not in JOURNAL_CONFIGS:
        raise ValueError(f"Unknown journal '{journal}'. Available: {', '.join(JOURNAL_CONFIGS)}")
    apply_publication_style(JOURNAL_CONFIGS[journal_key]["style"], data_dense=data_dense)
    size = figure_size_for_journal(journal_key, figure_width=figure_width, aspect=aspect)
    plt.rcParams["figure.figsize"] = size
    return size


def validate_publication_rcparams(params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Audit rcParams for common publication failures."""
    rc = params or plt.rcParams
    issues: List[str] = []

    if rc.get("savefig.dpi", 0) < 300:
        issues.append("savefig.dpi is below 300")
    if rc.get("pdf.fonttype") != 42:
        issues.append("pdf.fonttype should be 42 for editable embedded TrueType text")
    if rc.get("ps.fonttype") != 42:
        issues.append("ps.fonttype should be 42")
    if rc.get("svg.fonttype") not in ("none", None):
        issues.append("svg.fonttype should be 'none' for editable text")
    if float(rc.get("axes.labelsize", 0)) < 6:
        issues.append("axes.labelsize is too small for final print")
    if str(rc.get("image.cmap", "")).lower() in {"jet", "rainbow", "gist_rainbow", "nipy_spectral"}:
        issues.append("image.cmap uses a forbidden false-color map")

    return {"passes": not issues, "issues": issues}


@contextmanager
def publication_style_context(style_name: str = "default", data_dense: bool = False) -> Iterator[None]:
    """Temporarily apply a publication style inside a context manager."""
    with plt.rc_context(get_base_style(data_dense=data_dense)):
        plt.rcParams.update(_style_overrides(style_name))
        yield


def create_style_template(output_file: str = "publication.mplstyle", data_dense: bool = False) -> Path:
    """Create a matplotlib style file matching the base style."""
    output = Path(output_file)
    style = get_base_style(data_dense=data_dense)
    with output.open("w", encoding="utf-8") as handle:
        handle.write("# Publication-grade matplotlib style\n")
        handle.write("# Generated from scripts/style_presets.py\n\n")
        for key, value in style.items():
            if isinstance(value, Cycler):
                colors = [entry["color"] for entry in value]
                handle.write(f"axes.prop_cycle : cycler('color', {colors})\n")
            else:
                handle.write(f"{key} : {value}\n")
    return output


def show_color_palettes() -> None:
    """Render available categorical palettes for visual inspection."""
    fig, axes = plt.subplots(len(PALETTES), 1, figsize=(7.0, len(PALETTES) * 0.42))
    if len(PALETTES) == 1:
        axes = [axes]

    for ax, (name, colors) in zip(axes, PALETTES.items()):
        ax.set_xlim(0, len(colors))
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.set_xticks([])
        ax.set_ylabel(name, fontsize=8, rotation=0, ha="right", va="center")
        for i, color in enumerate(colors):
            ax.add_patch(plt.Rectangle((i, 0), 1, 1, facecolor=color, edgecolor="black", linewidth=0.4))
    fig.tight_layout()
    plt.show()


def reset_to_default() -> None:
    """Reset matplotlib to library defaults."""
    mpl.rcdefaults()


if __name__ == "__main__":
    applied = apply_publication_style("default", data_dense=True)
    audit = validate_publication_rcparams(applied)
    print("Matplotlib publication style audit:", audit)
    print("Nature single-column size:", figure_size_for_journal("nature", "single"))
