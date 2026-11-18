"""Color systems for publication-grade scientific visualization.

This module is intentionally opinionated. It provides palettes, colormap
validators, and redundant encodings so automatic figure generation does not
fall back to decorative or inaccessible color choices.
"""

from __future__ import annotations

from itertools import cycle, islice
from typing import Dict, Iterable, List, Mapping, Optional


OKABE_ITO = {
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
    "black": "#000000",
}
OKABE_ITO_LIST = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#000000",
]

WONG = [
    "#000000", "#E69F00", "#56B4E9", "#009E73",
    "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
]

TOL_BRIGHT = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]
TOL_MUTED = ["#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255", "#AA4499"]
TOL_LIGHT = ["#77AADD", "#EE8866", "#EEDD88", "#FFAABB", "#99DDFF", "#44BB99", "#BBCC33", "#AAAA00", "#DDDDDD"]
TOL_HIGH_CONTRAST = ["#004488", "#DDAA33", "#BB5566"]

PALETTE_REGISTRY: Dict[str, List[str]] = {
    "okabe_ito": OKABE_ITO_LIST,
    "okabe-ito": OKABE_ITO_LIST,
    "wong": WONG,
    "tol_bright": TOL_BRIGHT,
    "tol-muted": TOL_MUTED,
    "tol_muted": TOL_MUTED,
    "tol_light": TOL_LIGHT,
    "tol_high_contrast": TOL_HIGH_CONTRAST,
}

SEQUENTIAL_COLORMAPS = [
    "viridis",
    "cividis",
    "magma",
    "inferno",
    "plasma",
    "Blues",
    "Greens",
    "Purples",
    "YlGnBu",
    "YlOrRd",
]

DIVERGING_COLORMAPS_SAFE = [
    "RdBu",
    "RdBu_r",
    "PuOr",
    "PuOr_r",
    "BrBG",
    "BrBG_r",
    "coolwarm",
]

FORBIDDEN_COLORMAPS = {
    "jet",
    "rainbow",
    "gist_rainbow",
    "nipy_spectral",
    "hsv",
    "RdYlGn",
    "RdYlGn_r",
    "RdGn",
    "redgreen",
}

MARKER_SYMBOLS = ["o", "s", "D", "^", "v", "P", "X", "*", "<", ">"]
PLOTLY_MARKER_SYMBOLS = ["circle", "square", "diamond", "triangle-up", "triangle-down", "cross", "x", "star"]
LINE_DASHES = ["solid", "dashed", "dotted", "dashdot", (0, (5, 1)), (0, (3, 1, 1, 1))]
PLOTLY_LINE_DASHES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]

FLUOROPHORES_ACCESSIBLE = {
    "Channel1": "#0072B2",
    "Channel2": "#E69F00",
    "Channel3": "#D55E00",
    "Channel4": "#CC79A7",
    "Channel5": "#F0E442",
}

DNA_BASES_ACCESSIBLE = {
    "A": "#009E73",
    "C": "#0072B2",
    "G": "#E69F00",
    "T": "#D55E00",
    "U": "#D55E00",
}


def _key(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def _cycled(values: Iterable[str], n: Optional[int]) -> List[str]:
    values = list(values)
    if n is None:
        return list(values)
    if n <= len(values):
        return values[:n]
    return list(islice(cycle(values), n))


def available_palettes() -> List[str]:
    """Return canonical palette names."""
    return ["okabe_ito", "wong", "tol_bright", "tol_muted", "tol_light", "tol_high_contrast"]


def get_palette(palette_name: str = "okabe_ito", n: Optional[int] = None, cycle_if_needed: bool = True) -> List[str]:
    """Return a categorical palette.

    Parameters
    ----------
    palette_name:
        Name in ``PALETTE_REGISTRY``.
    n:
        Optional number of colors required.
    cycle_if_needed:
        If True, repeat colors for more categories than the base palette. The
        caller should still add marker/line redundancy for large category sets.
    """
    normalized = _key(palette_name)
    if normalized not in PALETTE_REGISTRY:
        raise ValueError(f"Unknown palette '{palette_name}'. Available: {', '.join(available_palettes())}")

    colors = PALETTE_REGISTRY[normalized]
    if n is not None and n > len(colors) and not cycle_if_needed:
        raise ValueError(
            f"Palette '{palette_name}' has {len(colors)} colors but {n} categories were requested. "
            "Use facets, labels, or redundant encodings."
        )
    return _cycled(colors, n)


def get_plotly_palette(palette_name: str = "okabe_ito", n: Optional[int] = None) -> List[str]:
    """Return a Plotly-compatible discrete color sequence."""
    return get_palette(palette_name, n=n, cycle_if_needed=True)


def apply_palette(palette_name: str = "okabe_ito", n: Optional[int] = None) -> List[str]:
    """Apply a colorblind-safe palette to matplotlib's color cycle."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required to apply palettes") from exc

    colors = get_palette(palette_name, n=n)
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=colors)
    return colors


def validate_colormap(cmap_name: str, role: str = "sequential") -> Mapping[str, object]:
    """Validate a continuous colormap for a scientific role.

    ``role`` can be ``sequential``, ``diverging``, or ``categorical``. This
    function raises on notorious false-color maps because those maps create
    non-existent visual boundaries and fail accessibility tests.
    """
    name = str(cmap_name).strip()
    lower = name.lower()
    forbidden_lower = {item.lower() for item in FORBIDDEN_COLORMAPS}
    if lower in forbidden_lower:
        raise ValueError(f"Colormap '{cmap_name}' is forbidden for publication scientific figures.")

    role_key = _key(role)
    sequential = {item.lower() for item in SEQUENTIAL_COLORMAPS}
    diverging = {item.lower() for item in DIVERGING_COLORMAPS_SAFE}

    if role_key == "sequential" and lower not in sequential:
        return {"name": name, "role": role_key, "allowed": True, "warning": "not in preferred sequential set"}
    if role_key == "diverging" and lower not in diverging:
        return {"name": name, "role": role_key, "allowed": True, "warning": "not in preferred diverging set"}
    if role_key == "categorical":
        raise ValueError("Use a discrete palette for categorical variables, not a continuous colormap.")

    return {"name": name, "role": role_key, "allowed": True, "warning": None}


def choose_colormap(role: str = "sequential", has_meaningful_center: bool = False) -> str:
    """Choose a conservative default colormap."""
    if has_meaningful_center or _key(role) == "diverging":
        return "RdBu_r"
    return "viridis"


def redundant_encoding_plan(
    categories: Iterable[object],
    palette_name: str = "okabe_ito",
    plotly: bool = False,
) -> Dict[str, Dict[str, object]]:
    """Assign color, marker, and line dash for categorical series.

    This prevents color from being the only carrier of meaning, which matters
    for grayscale printing, color-vision deficiency, and crowded panels.
    """
    labels = [str(category) for category in categories]
    colors = get_palette(palette_name, n=len(labels), cycle_if_needed=True)
    markers = PLOTLY_MARKER_SYMBOLS if plotly else MARKER_SYMBOLS
    dashes = PLOTLY_LINE_DASHES if plotly else LINE_DASHES

    plan: Dict[str, Dict[str, object]] = {}
    for idx, label in enumerate(labels):
        plan[label] = {
            "color": colors[idx],
            "marker": markers[idx % len(markers)],
            "dash": dashes[idx % len(dashes)],
        }
    return plan


def luminance(hex_color: str) -> float:
    """Return relative luminance for a hex color."""
    color = hex_color.lstrip("#")
    if len(color) != 6:
        raise ValueError(f"Expected 6-digit hex color, got '{hex_color}'")
    rgb = [int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in rgb
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(hex_a: str, hex_b: str = "#FFFFFF") -> float:
    """Return WCAG-style luminance contrast ratio between two colors."""
    lum_a = luminance(hex_a)
    lum_b = luminance(hex_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def palette_audit(palette_name: str = "okabe_ito", background: str = "#FFFFFF") -> Dict[str, object]:
    """Return a simple audit for palette size and contrast against background."""
    colors = get_palette(palette_name)
    return {
        "palette": palette_name,
        "n_colors": len(colors),
        "background": background,
        "min_contrast_to_background": min(contrast_ratio(color, background) for color in colors),
        "redundant_encoding_required": len(colors) > 6,
        "colors": colors,
    }


if __name__ == "__main__":
    print("Publication-grade scientific palettes")
    for name in available_palettes():
        audit = palette_audit(name)
        print(
            f"{name:18s} colors={audit['n_colors']} "
            f"min_contrast={audit['min_contrast_to_background']:.2f}"
        )
