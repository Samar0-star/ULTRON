import numpy as np
import pandas as pd
import importlib.util
import pytest
from pathlib import Path

from backend.tools.viz_ai_coder import run_ai_coder


def _load_skill_module(relative_path, module_name):
    root = Path(__file__).resolve().parents[2]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_skill_engine():
    return _load_skill_module(
        "backend/skills/scientific-visualization/scripts/publication_viz_engine.py",
        "publication_viz_engine_test",
    )


def _assert_publication_gate(result, expected_family):
    assert result.status == "success"
    assert result.html
    assert result.meta["engine"] == "DeterministicPublicationViz_DeepMindGrade"
    audit = result.meta["audit"]
    assert audit["plot_family"] == expected_family
    assert audit["passes"] is True
    assert audit["bar_traces"] == 0
    assert audit["bar_only"] is False
    assert audit["rich_trace_count"] > 0


def test_dose_response_uses_raw_points_ci_and_distribution_not_bars():
    concentrations = np.logspace(-3, 2, 8)
    rows = []
    for cell_line, ic50 in [("HEK293", 0.5), ("HeLa", 2.5), ("MCF7", 10.0)]:
        for concentration in concentrations:
            expected = 100 / (1 + (concentration / ic50) ** 1.2)
            for replicate, offset in enumerate([-3.0, 0.0, 3.0], start=1):
                rows.append(
                    {
                        "Cell_Line": cell_line,
                        "Drug_Concentration_uM": concentration,
                        "Replicate": replicate,
                        "Cell_Viability_Pct": max(0.0, min(100.0, expected + offset)),
                    }
                )

    result = run_ai_coder(
        pd.DataFrame(rows),
        "Generate a publication-grade dose response IC50 visualization.",
        {"caption": "Dose response regression test"},
    )

    _assert_publication_gate(result, "dose_response")
    trace_counts = result.meta["audit"]["trace_counts"]
    assert trace_counts.get("scatter", 0) >= 6
    assert trace_counts.get("violin", 0) == 3


def test_skill_engine_is_the_direct_publication_figure_source():
    engine = _load_skill_engine()
    df = pd.DataFrame(
        {
            "condition": ["control"] * 4 + ["treated"] * 4,
            "response_score": [1.0, 1.2, 1.1, 1.3, 2.2, 2.4, 2.1, 2.5],
        }
    )

    fig, audit = engine.build_publication_grade_figure(
        df,
        "Compare treatment response distributions.",
        "Skill engine direct test",
    )
    figure_audit = engine.audit_plotly_json(fig.to_plotly_json())

    assert audit["plot_family"] == "distribution"
    assert figure_audit["passes"] is True
    assert figure_audit["bar_traces"] == 0


def test_multivariate_data_gets_scatter_heatmap_violin_and_parallel_coordinates():
    df = pd.DataFrame(
        {
            "treatment": ["A", "A", "A", "B", "B", "B", "C", "C", "C", "C"],
            "time_h": [0, 1, 2, 0, 1, 2, 0, 1, 2, 3],
            "signal_au": [1.0, 1.4, 1.8, 1.1, 2.2, 3.5, 0.9, 1.6, 2.8, 3.9],
            "protein_level": [10, 11, 13, 10, 15, 18, 9, 12, 16, 21],
            "phospho_score": [0.2, 0.3, 0.5, 0.25, 0.55, 0.8, 0.19, 0.4, 0.7, 0.9],
        }
    )

    result = run_ai_coder(
        df,
        "Create a multivariate treatment response figure for a paper.",
        {"caption": "Multivariate regression test"},
    )

    _assert_publication_gate(result, "multivariate")
    trace_counts = result.meta["audit"]["trace_counts"]
    assert trace_counts.get("scatter", 0) >= 3
    assert trace_counts.get("heatmap", 0) == 1
    assert trace_counts.get("violin", 0) >= 1
    assert trace_counts.get("parcoords", 0) == 1


def test_medium_multivariate_data_gets_density_pca_and_audit_payload():
    engine = _load_skill_engine()
    rows = []
    for treatment, offset in [("A", 0.0), ("B", 0.7), ("C", 1.2)]:
        for i in range(12):
            time = i / 2
            rows.append(
                {
                    "treatment": treatment,
                    "time_h": time,
                    "signal_au": 1.0 + offset + 0.28 * time + 0.05 * (i % 3),
                    "protein_level": 10 + 2 * offset + 0.9 * i,
                    "phospho_score": 0.2 + 0.08 * i + 0.15 * offset,
                    "toxicity_score": 0.04 * i + 0.03 * offset,
                }
            )

    fig, audit = engine.build_publication_grade_figure(
        pd.DataFrame(rows),
        "Build a complex multivariate publication figure.",
        "Multivariate density/PCA test",
    )
    figure_audit = engine.audit_plotly_json(fig.to_plotly_json())

    assert audit["plot_family"] == "multivariate"
    assert audit["density_contours"] is True
    assert audit["pca_projection"] is True
    assert audit["synthetic_points"] == 0
    assert figure_audit["trace_counts"].get("histogram2dcontour", 0) >= 1
    assert figure_audit["trace_counts"].get("parcoords", 0) == 1
    assert figure_audit["bar_traces"] == 0


def test_single_endpoint_group_comparison_uses_violin_and_ecdf_not_bars():
    df = pd.DataFrame(
        {
            "condition": ["control"] * 5 + ["treated"] * 5,
            "expression_score": [1.1, 1.0, 1.2, 1.4, 1.3, 2.2, 2.0, 2.5, 2.3, 2.4],
        }
    )

    result = run_ai_coder(
        df,
        "Compare condition distributions with individual points.",
        {"caption": "Distribution regression test"},
    )

    _assert_publication_gate(result, "distribution")
    trace_counts = result.meta["audit"]["trace_counts"]
    assert trace_counts.get("violin", 0) == 2
    assert trace_counts.get("scatter", 0) == 2


def test_skill_support_scripts_reject_low_grade_visual_defaults():
    color_palettes = _load_skill_module(
        "backend/skills/scientific-visualization/assets/color_palettes.py",
        "color_palettes_test",
    )
    figure_export = _load_skill_module(
        "backend/skills/scientific-visualization/scripts/figure_export.py",
        "figure_export_test",
    )
    style_presets = _load_skill_module(
        "backend/skills/scientific-visualization/scripts/style_presets.py",
        "style_presets_test",
    )

    with pytest.raises(ValueError):
        color_palettes.validate_colormap("jet", role="sequential")
    with pytest.raises(ValueError):
        figure_export.validate_export_request(["jpg"], dpi=600)

    style = style_presets.apply_publication_style("default", data_dense=True)
    audit = style_presets.validate_publication_rcparams(style)
    assert audit["passes"] is True
