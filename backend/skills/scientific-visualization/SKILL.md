---
name: scientific-visualization
description: "Create publication-grade scientific figures from real data using dense non-bar encodings: raw observations, distributions, dose-response curves, heatmaps, contours, trajectories, multivariate panels, uncertainty, colorblind-safe palettes, and journal-ready export audits."
---

# Scientific Visualization

Use this skill when a user asks for scientific plots, manuscript figures,
journal-ready visualizations, statistical graphics, exploratory scientific
panels, or figure export for papers, preprints, posters, or reports.

The job is not to make a pretty chart. The job is to preserve scientific
structure and make it legible at publication size.

## Non-Negotiable Doctrine

Filled summary bars are a last-resort categorical-count encoding, never the
default answer. A publication-grade figure should expose the data geometry:
individual observations, uncertainty from observed replicates, distribution
shape, trajectories, correlations, spatial or matrix structure, dose-response
behavior, model residuals, or multivariate relationships.

Hard gates:

- Do not create bar-only figures unless the data are only categorical counts
  and the user explicitly asks for that encoding.
- Do not invent random jitter, residuals, confidence bands, surfaces, or
  synthetic observations to make a graphic look rich.
- Show raw observations wherever feasible; summary-only figures are weak for
  small and medium datasets.
- Use uncertainty only when it is computed from observed replicates, explicit
  model output, or a documented resampling procedure.
- Use colorblind-safe palettes and redundant encodings: marker shape, line
  dash, labels, facets, texture, or direct annotation.
- Prefer multi-panel figures when one view cannot honestly show the result.
- Label units, transforms, sample sizes, replicate definitions, and model/test
  assumptions in the figure or caption.

## Automatic Figure Selection

Profile the data before choosing the figure. Use the most information-dense
scientifically honest family available.

| Data profile | Figure family | Required layers |
| --- | --- | --- |
| Dose/concentration plus response | Dose-response panel | Raw replicate scatter, mean or model trajectory, observed interval, IC50/EC50 guide only when supported |
| Two or more numeric variables | Multivariate panel | Scatter/density, trend, correlation heatmap, distribution panel, parallel-coordinate or projection panel |
| One numeric endpoint with groups | Distribution panel | Violin/box, individual points, ECDF or quantile view |
| Time series or ordered trajectories | Trajectory panel | Individual traces or group summaries, observed interval bands, event markers |
| Matrix/expression/correlation data | Heatmap or clustered heatmap | Labeled colorbar, perceptual colormap, missingness handling |
| Spatial/image data | Image plus quantitative panels | Scale bar, intensity scale, region summaries, segmentation overlays if available |
| High-dimensional embeddings | Projection panel | UMAP/PCA/t-SNE scatter, method parameters, explained variance where available |
| Network/graph data | Network or adjacency view | Node/edge encodings, legend, layout method note |
| Pure categorical counts | Heatmap, lollipop, dot plot, mosaic | Ranked counts and direct labels |

## Runtime Engine

The executable source of truth for automatic figure generation is:

`scripts/publication_viz_engine.py`

Use it when the user provides tabular data and does not demand a specific plot
type. It profiles the dataframe, selects a figure family, renders Plotly panels,
and emits an audit payload with trace counts, plot family, synthetic-data flag,
and bar-only rejection status.

CLI smoke usage:

```bash
python backend/skills/scientific-visualization/scripts/publication_viz_engine.py data.csv \
  --intent "dose-response IC50 figure" \
  --caption "Observed dose-response" \
  --html figure.html \
  --json figure.json
```

The live `backend/tools/viz_ai_coder.py` adapter must import this skill engine.
Keep plot-selection doctrine in this skill directory. Keep API packaging,
sandbox execution, and `VizResult` wrapping in the tool adapter.

## Minimal Workflow

1. Inspect columns, units, sample size, missingness, replicate structure, and
   whether axes are ordered, log-scaled, categorical, or spatial.
2. Choose an encoding from the selection table. If the data are rich, build a
   multi-panel figure rather than collapsing it into one summary.
3. Apply publication style and colorblind-safe palettes.
4. Draw raw observations and uncertainty from observed data.
5. Export a vector format plus a high-resolution raster preview.
6. Run the audit checks: no synthetic observations, no bar-only output, labeled
   units, accessible colors, readable final-size text, and journal dimensions.

## Matplotlib Quick Start

```python
import numpy as np
import matplotlib.pyplot as plt

from style_presets import apply_publication_style
from figure_export import save_publication_bundle

apply_publication_style("default")

conditions = ["Control", "Low", "High"]
observed = [
    np.array([0.91, 0.88, 0.93, 0.90, 0.89]),
    np.array([0.76, 0.79, 0.74, 0.78, 0.81]),
    np.array([0.52, 0.49, 0.55, 0.51, 0.50]),
]

fig, ax = plt.subplots(figsize=(3.5, 2.4))
for i, values in enumerate(observed):
    x = np.full(values.size, i) + np.linspace(-0.07, 0.07, values.size)
    mean = values.mean()
    sem = values.std(ddof=1) / np.sqrt(values.size)
    ax.scatter(x, values, s=18, alpha=0.75, edgecolor="white", linewidth=0.4)
    ax.errorbar(i, mean, yerr=1.96 * sem, fmt="o", color="black",
                mfc="white", capsize=3, lw=1.1)

ax.set_xticks(range(len(conditions)))
ax.set_xticklabels(conditions)
ax.set_ylabel("Normalized response")

save_publication_bundle(fig, "figure_1", formats=["pdf", "svg", "png"], dpi=600)
```

## Seaborn Patterns

Use seaborn for statistical layers, but do not let it choose weak defaults.

Good patterns:

```python
import seaborn as sns
import matplotlib.pyplot as plt

from style_presets import apply_publication_style

apply_publication_style("default")
sns.set_theme(style="ticks", context="paper", font_scale=1.0)
sns.set_palette(["#E69F00", "#56B4E9", "#009E73", "#D55E00"])

fig, ax = plt.subplots(figsize=(3.5, 2.6))
sns.violinplot(data=df, x="treatment", y="response", inner=None,
               cut=0, linewidth=0.8, ax=ax)
sns.boxplot(data=df, x="treatment", y="response", width=0.22,
            showcaps=True, boxprops={"facecolor": "white", "alpha": 0.75},
            showfliers=False, whiskerprops={"linewidth": 0.8}, ax=ax)
sns.stripplot(data=df, x="treatment", y="response", color="black",
              alpha=0.45, size=3, jitter=0.18, ax=ax)
ax.set_ylabel("Response (a.u.)")
sns.despine()
```

For trends, prefer `sns.lineplot(..., errorbar=("ci", 95))`,
`sns.scatterplot`, `sns.kdeplot`, `sns.ecdfplot`, `sns.heatmap`,
`sns.clustermap`, `sns.jointplot`, and `sns.pairplot` when they match the data.

## Plotly Patterns

Use Plotly for interactive exploration and audited HTML output. Static export
must still obey publication rules.

Required layout defaults:

```python
fig.update_layout(
    template="plotly_white",
    font={"family": "Arial, Helvetica, sans-serif", "size": 12},
    colorway=["#E69F00", "#56B4E9", "#009E73", "#F0E442",
              "#0072B2", "#D55E00", "#CC79A7", "#000000"],
    paper_bgcolor="white",
    plot_bgcolor="white",
)
fig.write_html("figure.html", include_plotlyjs="cdn", full_html=True)
fig.write_image("figure.png", scale=3)
```

Use `audit_plotly_json()` from `scripts/publication_viz_engine.py` before
returning auto-generated Plotly figures.

## Color And Style

Use the assets and scripts in this skill:

- `assets/color_palettes.py`: palette registry, safe colormaps, validators.
- `assets/publication.mplstyle`: general manuscript settings.
- `assets/nature.mplstyle`: small-column journal settings.
- `assets/presentation.mplstyle`: larger on-screen typography.
- `scripts/style_presets.py`: rcParams presets, journal sizing, validation.

Rules:

- Use Okabe-Ito, Wong, or Paul Tol palettes for categories.
- Use `viridis`, `cividis`, `magma`, `inferno`, or `plasma` for sequential
  continuous data.
- Use `RdBu_r`, `PuOr`, or `BrBG` for diverging data with a meaningful center.
- Never use `jet`, `rainbow`, or red-green as the sole encoding.
- Test grayscale readability when figures must work in print.

## Export

Use `scripts/figure_export.py` for final output:

```python
from figure_export import save_publication_bundle, check_figure_size

check_figure_size(fig, journal="nature")
manifest = save_publication_bundle(
    fig,
    "figure_1",
    formats=["pdf", "svg", "png"],
    dpi=600,
    journal="nature",
    audit={"plot_family": "dose_response", "synthetic_points": 0},
)
```

Export rules:

- Vector: PDF or SVG for plots, text, line art, and schematic layers.
- Raster: PNG or TIFF at 300-600 DPI for previews or images.
- Never use JPEG for scientific plots.
- Keep fonts embedded/editable: `pdf.fonttype = 42`, `ps.fonttype = 42`,
  `svg.fonttype = "none"`.
- Save an audit manifest when delivering final figures.

## References

Load only the files needed for the task:

- `references/matplotlib_examples.md`: deterministic non-bar Matplotlib
  patterns using observed arrays.
- `references/publication_guidelines.md`: figure design, statistical rigor,
  annotations, and final checks.
- `references/color_palettes.md`: colorblind-safe palettes and colormap rules.
- `references/journal_requirements.md`: publisher sizes, DPI, and format specs.

## Final Checklist

Before returning a figure or code, verify:

- [ ] The visualization uses measured data, not invented random values.
- [ ] It is not bar-only unless explicitly justified by pure categorical counts.
- [ ] Raw observations or distributions are visible when feasible.
- [ ] Uncertainty is defined and computed from observed data.
- [ ] Axis labels include units and transforms.
- [ ] Color choices are accessible and not decorative.
- [ ] Text is readable at final publication size.
- [ ] Vector and high-resolution raster exports are created where appropriate.
- [ ] The figure has a caption-ready audit: plot family, sample size, replicate
      definition, model/test if used, and export settings.
