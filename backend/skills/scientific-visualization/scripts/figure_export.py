#!/usr/bin/env python3
"""Export and audit utilities for publication-grade scientific figures."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

import matplotlib.pyplot as plt


VECTOR_FORMATS = {"pdf", "svg", "eps"}
RASTER_FORMATS = {"png", "tiff", "tif"}
FORBIDDEN_FORMATS = {"jpg", "jpeg", "webp", "gif"}

JOURNAL_EXPORT_SPECS = {
    "nature": {
        "line_art": {"formats": ["pdf", "svg", "png"], "dpi": 1000},
        "photo": {"formats": ["tiff", "png"], "dpi": 300},
        "combination": {"formats": ["pdf", "svg", "png"], "dpi": 600},
    },
    "science": {
        "line_art": {"formats": ["pdf", "eps", "png"], "dpi": 1000},
        "photo": {"formats": ["tiff"], "dpi": 300},
        "combination": {"formats": ["pdf", "png"], "dpi": 600},
    },
    "cell": {
        "line_art": {"formats": ["pdf", "svg", "png"], "dpi": 1000},
        "photo": {"formats": ["tiff"], "dpi": 300},
        "combination": {"formats": ["pdf", "png"], "dpi": 600},
    },
    "plos": {
        "line_art": {"formats": ["pdf", "svg", "png"], "dpi": 600},
        "photo": {"formats": ["tiff", "png"], "dpi": 300},
        "combination": {"formats": ["pdf", "png"], "dpi": 600},
    },
    "acs": {
        "line_art": {"formats": ["pdf", "eps", "png"], "dpi": 600},
        "photo": {"formats": ["tiff"], "dpi": 300},
        "combination": {"formats": ["pdf", "png"], "dpi": 600},
    },
    "ieee": {
        "line_art": {"formats": ["pdf", "eps", "png"], "dpi": 600},
        "photo": {"formats": ["tiff"], "dpi": 300},
        "combination": {"formats": ["pdf", "png"], "dpi": 600},
    },
}

JOURNAL_SIZE_SPECS = {
    "nature": {"single": 89, "onehalf": 120, "double": 183, "max_height": 247},
    "science": {"single": 55, "onehalf": 120, "double": 175, "max_height": 233},
    "cell": {"single": 85, "onehalf": 120, "double": 178, "max_height": 230},
    "plos": {"single": 83, "onehalf": 114, "double": 173, "max_height": 233},
    "acs": {"single": 82.5, "onehalf": 120, "double": 178, "max_height": 247},
    "ieee": {"single": 89, "onehalf": 120, "double": 182, "max_height": 230},
}


def _normalise_formats(formats: Iterable[str]) -> List[str]:
    normalised: List[str] = []
    for fmt in formats:
        clean = str(fmt).lower().lstrip(".")
        if clean in FORBIDDEN_FORMATS:
            raise ValueError(f"Format '{fmt}' is forbidden for scientific figure export.")
        if clean not in VECTOR_FORMATS | RASTER_FORMATS:
            raise ValueError(f"Unsupported export format '{fmt}'.")
        if clean not in normalised:
            normalised.append(clean)
    if not normalised:
        raise ValueError("At least one export format is required.")
    return normalised


def _base_output(filename: Union[str, Path]) -> Path:
    path = Path(filename)
    if path.suffix:
        path = path.with_suffix("")
    output_dir = path.parent if str(path.parent) else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / path.name


def _file_record(path: Path, fmt: str, dpi: int) -> Dict[str, Any]:
    return {
        "path": str(path),
        "format": fmt,
        "kind": "vector" if fmt in VECTOR_FORMATS else "raster",
        "dpi": None if fmt in VECTOR_FORMATS else dpi,
        "bytes": path.stat().st_size if path.exists() else 0,
    }


def validate_export_request(formats: Sequence[str], dpi: int) -> Dict[str, Any]:
    """Validate export formats and DPI before saving."""
    clean_formats = _normalise_formats(formats)
    issues: List[str] = []
    if dpi < 300 and any(fmt in RASTER_FORMATS for fmt in clean_formats):
        issues.append("Raster export DPI is below 300.")
    if not any(fmt in VECTOR_FORMATS for fmt in clean_formats):
        issues.append("No vector format requested; vector is preferred for plots and line art.")
    return {"passes": not issues, "formats": clean_formats, "dpi": dpi, "issues": issues}


def save_publication_figure(
    fig: plt.Figure,
    filename: Union[str, Path],
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 600,
    transparent: bool = False,
    bbox_inches: str = "tight",
    pad_inches: float = 0.04,
    facecolor: str = "white",
    **kwargs: Any,
) -> List[Path]:
    """Save a matplotlib figure in publication-safe formats."""
    clean_formats = _normalise_formats(formats)
    base = _base_output(filename)
    saved_files: List[Path] = []

    for fmt in clean_formats:
        output_file = base.with_suffix(f".{fmt}")
        save_kwargs = {
            "dpi": dpi,
            "bbox_inches": bbox_inches,
            "pad_inches": pad_inches,
            "facecolor": "none" if transparent else facecolor,
            "edgecolor": "none",
            "transparent": transparent,
            "format": fmt,
        }
        if fmt in VECTOR_FORMATS:
            save_kwargs["dpi"] = min(dpi, 600)
        save_kwargs.update(kwargs)
        fig.savefig(output_file, **save_kwargs)
        saved_files.append(output_file)

    return saved_files


def save_publication_bundle(
    fig: plt.Figure,
    filename: Union[str, Path],
    formats: Sequence[str] = ("pdf", "svg", "png"),
    dpi: int = 600,
    journal: Optional[str] = None,
    figure_type: str = "combination",
    audit: Optional[Mapping[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Save a figure plus an audit manifest beside the exported files."""
    request_audit = validate_export_request(formats, dpi)
    saved = save_publication_figure(fig, filename, request_audit["formats"], dpi=dpi, **kwargs)

    width_in, height_in = fig.get_size_inches()
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base": str(_base_output(filename)),
        "journal": journal,
        "figure_type": figure_type,
        "size_inches": {"width": float(width_in), "height": float(height_in)},
        "size_mm": {"width": float(width_in * 25.4), "height": float(height_in * 25.4)},
        "export_request": request_audit,
        "files": [_file_record(path, path.suffix.lstrip(".").lower(), dpi) for path in saved],
        "user_audit": dict(audit or {}),
        "passes": request_audit["passes"],
    }

    manifest_path = _base_output(filename).with_suffix(".audit.json")
    manifest["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def save_for_journal(
    fig: plt.Figure,
    filename: Union[str, Path],
    journal: str,
    figure_type: str = "combination",
    audit: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Save a figure with conservative journal-specific settings."""
    journal_key = journal.lower()
    if journal_key not in JOURNAL_EXPORT_SPECS:
        raise ValueError(f"Unknown journal '{journal}'. Available: {', '.join(JOURNAL_EXPORT_SPECS)}")
    if figure_type not in JOURNAL_EXPORT_SPECS[journal_key]:
        raise ValueError(
            f"Unknown figure_type '{figure_type}'. Available: {', '.join(JOURNAL_EXPORT_SPECS[journal_key])}"
        )

    specs = JOURNAL_EXPORT_SPECS[journal_key][figure_type]
    return save_publication_bundle(
        fig,
        filename,
        formats=specs["formats"],
        dpi=specs["dpi"],
        journal=journal_key,
        figure_type=figure_type,
        audit=audit,
    )


def check_figure_size(fig: plt.Figure, journal: str = "nature", tolerance_mm: float = 5.0) -> Dict[str, Any]:
    """Check whether figure dimensions match common journal columns."""
    journal_key = journal.lower()
    if journal_key not in JOURNAL_SIZE_SPECS:
        raise ValueError(f"Unknown journal '{journal}'. Available: {', '.join(JOURNAL_SIZE_SPECS)}")

    width_inches, height_inches = fig.get_size_inches()
    width_mm = float(width_inches * 25.4)
    height_mm = float(height_inches * 25.4)
    specs = JOURNAL_SIZE_SPECS[journal_key]

    width_matches = {
        name: abs(width_mm - value) <= tolerance_mm
        for name, value in specs.items()
        if name != "max_height"
    }
    column_type = next((name for name, ok in width_matches.items() if ok), None)
    height_ok = height_mm <= specs["max_height"]

    return {
        "journal": journal_key,
        "width_inches": float(width_inches),
        "height_inches": float(height_inches),
        "width_mm": width_mm,
        "height_mm": height_mm,
        "column_type": column_type,
        "width_ok": column_type is not None,
        "height_ok": height_ok,
        "compliant": column_type is not None and height_ok,
        "recommendations": specs,
    }


def verify_font_embedding(pdf_path: Union[str, Path]) -> Optional[bool]:
    """Perform a lightweight PDF readability check.

    A full font-embedding audit requires a dedicated PDF toolchain. This check
    confirms the PDF is readable and leaves detailed inspection to Acrobat,
    Ghostscript, or journal preflight tools.
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return None

    reader = PdfReader(str(pdf_path))
    return len(reader.pages) > 0


if __name__ == "__main__":
    import numpy as np

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    x = np.linspace(0, 10, 100)
    ax.plot(x, np.sin(x), label="sin(x)")
    ax.plot(x, np.cos(x), label="cos(x)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Signal (a.u.)")
    ax.legend()
    print(check_figure_size(fig, "nature"))
    print(save_publication_bundle(fig, "example_figure", audit={"synthetic_points": 0}))
    plt.close(fig)
