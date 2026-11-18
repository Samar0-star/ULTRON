# Matplotlib Patterns For Publication-Grade Scientific Figures

These examples are intentionally deterministic. Replace the small inline arrays
with observed data from the user's experiment, simulation, assay, or model
output. Do not invent random samples to make a figure look richer.

The default hierarchy is:

1. Show raw observations whenever the sample size allows it.
2. Show uncertainty as intervals or bands.
3. Use distributions, density, heatmaps, networks, trajectories, or small
   multiples when those encodings match the science.
4. Use categorical count columns only when the data are truly counts; prefer
   lollipop or dot-interval encodings over filled summary rectangles.

## Base Setup

```python
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

OKABE_ITO = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#000000",
]

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 600,
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "lines.linewidth": 1.4,
    "legend.frameon": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})

def panel_label(ax, label):
    ax.text(
        -0.18, 1.08, label, transform=ax.transAxes,
        fontsize=9, fontweight="bold", va="top", ha="left"
    )
```

## Example 1: Dot-Interval Summary With Raw Observations

Use this when comparing experimental conditions. The figure shows every
measurement and the mean +/- 95% confidence interval without hiding the sample
structure.

```python
conditions = ["Vehicle", "Low dose", "High dose"]
values = [
    np.array([0.92, 0.87, 0.95, 0.90, 0.89, 0.93]),
    np.array([0.74, 0.79, 0.77, 0.72, 0.76, 0.81]),
    np.array([0.48, 0.53, 0.51, 0.46, 0.50, 0.55]),
]

fig, ax = plt.subplots(figsize=(3.35, 2.35))

for i, obs in enumerate(values):
    x = np.full(obs.size, i, dtype=float) + np.linspace(-0.07, 0.07, obs.size)
    mean = obs.mean()
    sem = obs.std(ddof=1) / np.sqrt(obs.size)
    ci95 = 1.96 * sem

    ax.scatter(
        x, obs, s=18, color=OKABE_ITO[i], alpha=0.72,
        edgecolor="white", linewidth=0.4, zorder=2
    )
    ax.errorbar(
        i, mean, yerr=ci95, fmt="o", color="black",
        mfc="white", mec="black", ms=4, lw=1.1, capsize=3, zorder=3
    )

ax.set_xticks(range(len(conditions)))
ax.set_xticklabels(conditions)
ax.set_ylabel("Normalized viability")
ax.set_ylim(0.35, 1.02)
panel_label(ax, "A")
fig.tight_layout()
fig.savefig("dot_interval_raw_observations.pdf")
```

## Example 2: Raincloud-Style Distribution Panel

Use this when the distribution shape is part of the result. Violin shape,
median/quartiles, and raw points expose heterogeneity that a single summary
cannot.

```python
groups = ["WT", "KO"]
observations = [
    np.array([12.1, 11.7, 13.3, 12.8, 14.0, 13.6, 12.5, 11.9]),
    np.array([15.2, 16.1, 14.8, 17.0, 16.4, 15.9, 17.3, 15.5]),
]

fig, ax = plt.subplots(figsize=(2.7, 2.35))
parts = ax.violinplot(
    observations, positions=[0, 1], widths=0.72,
    showmeans=False, showmedians=False, showextrema=False
)

for i, body in enumerate(parts["bodies"]):
    body.set_facecolor(OKABE_ITO[i])
    body.set_edgecolor("black")
    body.set_alpha(0.30)
    body.set_linewidth(0.7)

for i, obs in enumerate(observations):
    jitter = np.linspace(-0.10, 0.10, obs.size)
    q1, med, q3 = np.percentile(obs, [25, 50, 75])
    ax.scatter(i + jitter, obs, s=16, color=OKABE_ITO[i], alpha=0.75,
               edgecolor="white", linewidth=0.35)
    ax.plot([i - 0.18, i + 0.18], [med, med], color="black", lw=1.1)
    ax.plot([i, i], [q1, q3], color="black", lw=2.2, solid_capstyle="round")

ax.set_xticks([0, 1])
ax.set_xticklabels(groups)
ax.set_ylabel("Protein abundance (a.u.)")
panel_label(ax, "B")
fig.tight_layout()
fig.savefig("raincloud_distribution.svg")
```

## Example 3: Dose-Response Curve With Replicates And IC50 Guide

Use a log-scaled x-axis, individual replicate points, mean trajectory, and a
visual IC50 guide. Fit with the actual model used in the analysis when
available; this example shows observed means and interpolation only.

```python
dose = np.array([0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0])
replicates = np.array([
    [98, 97, 99],
    [93, 95, 94],
    [86, 83, 85],
    [71, 69, 73],
    [52, 49, 51],
    [31, 34, 30],
    [18, 16, 20],
])
mean = replicates.mean(axis=1)
sem = replicates.std(axis=1, ddof=1) / np.sqrt(replicates.shape[1])
ci95 = 1.96 * sem

log_dose = np.log10(dose)
ic50 = 10 ** np.interp(50, mean[::-1], log_dose[::-1])

fig, ax = plt.subplots(figsize=(3.35, 2.45))
for r in range(replicates.shape[1]):
    ax.scatter(dose, replicates[:, r], s=16, color=OKABE_ITO[4],
               alpha=0.48, edgecolor="white", linewidth=0.35)

ax.errorbar(dose, mean, yerr=ci95, color=OKABE_ITO[5], marker="o",
            ms=4, lw=1.3, capsize=2.5, label="Mean +/- 95% CI")
ax.axhline(50, color="0.35", lw=0.8, ls="--")
ax.axvline(ic50, color="0.35", lw=0.8, ls="--")
ax.annotate(f"IC50 = {ic50:.2g} uM", xy=(ic50, 50), xytext=(1.8, 70),
            arrowprops={"arrowstyle": "->", "lw": 0.7}, fontsize=7)
ax.set_xscale("log")
ax.set_xlabel("Concentration (uM)")
ax.set_ylabel("Viability (%)")
ax.set_ylim(0, 105)
ax.legend(loc="upper right")
panel_label(ax, "C")
fig.tight_layout()
fig.savefig("dose_response_replicates.pdf")
```

## Example 4: Multivariate Panel With Density, Correlation, ECDF

Use this for high-dimensional or model-output tables. A single panel rarely
does the job; combine complementary encodings.

```python
score = np.array([0.18, 0.22, 0.29, 0.31, 0.35, 0.41, 0.48, 0.55,
                  0.63, 0.69, 0.72, 0.80, 0.84, 0.91, 0.96])
effect = np.array([1.2, 1.0, 1.5, 1.7, 1.6, 2.0, 2.1, 2.7,
                   2.9, 3.1, 3.4, 3.6, 3.9, 4.2, 4.5])
toxicity = np.array([0.05, 0.07, 0.06, 0.11, 0.10, 0.13, 0.18, 0.22,
                     0.25, 0.23, 0.31, 0.34, 0.36, 0.42, 0.45])
matrix = np.corrcoef(np.vstack([score, effect, toxicity]))
labels = ["Score", "Effect", "Toxicity"]

fig, axes = plt.subplots(1, 3, figsize=(6.8, 2.35))

axes[0].hexbin(score, effect, gridsize=8, cmap="viridis", mincnt=1,
               linewidths=0.25, edgecolors="white")
axes[0].scatter(score, effect, s=14, color="black", alpha=0.62)
axes[0].set_xlabel("Model score")
axes[0].set_ylabel("Effect size")
panel_label(axes[0], "A")

im = axes[1].imshow(matrix, vmin=-1, vmax=1, cmap="RdBu_r")
axes[1].set_xticks(range(3))
axes[1].set_yticks(range(3))
axes[1].set_xticklabels(labels, rotation=35, ha="right")
axes[1].set_yticklabels(labels)
for row in range(3):
    for col in range(3):
        axes[1].text(col, row, f"{matrix[row, col]:.2f}",
                     ha="center", va="center", fontsize=7)
fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04, label="Pearson r")
panel_label(axes[1], "B")

for values, name, color in [
    (score, "Score", OKABE_ITO[4]),
    (toxicity, "Toxicity", OKABE_ITO[5]),
]:
    ordered = np.sort(values)
    ecdf = np.arange(1, ordered.size + 1) / ordered.size
    axes[2].plot(ordered, ecdf, marker="o", ms=3, lw=1.2,
                 color=color, label=name)
axes[2].set_xlabel("Observed value")
axes[2].set_ylabel("Empirical cumulative probability")
axes[2].legend(loc="lower right")
panel_label(axes[2], "C")

fig.tight_layout()
fig.savefig("multivariate_publication_panel.pdf")
```

## Example 5: Heatmap With Explicit Scale And Missingness

Use heatmaps for matrices, spatial grids, gene-expression blocks, confusion
matrices, and correlation structures. Always label the color scale and missing
values.

```python
data = np.array([
    [0.12, 0.31, 0.28, np.nan, 0.55],
    [0.22, 0.41, 0.39, 0.44, 0.61],
    [0.18, 0.36, 0.51, 0.59, 0.74],
    [0.05, 0.20, 0.33, 0.49, 0.68],
])
masked = np.ma.masked_invalid(data)
cmap = plt.cm.viridis.copy()
cmap.set_bad(color="#F2F2F2")

fig, ax = plt.subplots(figsize=(3.0, 2.35))
im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=0.8, aspect="auto")
ax.set_xticks(range(data.shape[1]))
ax.set_xticklabels(["T0", "T1", "T2", "T3", "T4"])
ax.set_yticks(range(data.shape[0]))
ax.set_yticklabels(["Gene A", "Gene B", "Gene C", "Gene D"])
ax.set_xlabel("Time point")
ax.set_ylabel("Feature")
fig.colorbar(im, ax=ax, label="Normalized expression")
panel_label(ax, "D")
fig.tight_layout()
fig.savefig("labeled_heatmap.svg")
```

## Export Checklist

Use vector output for line art and text-heavy figures, plus a high-resolution
raster for systems that need preview images.

```python
fig.savefig("figure_1.pdf", dpi=600, bbox_inches="tight", pad_inches=0.04)
fig.savefig("figure_1.svg", dpi=600, bbox_inches="tight", pad_inches=0.04)
fig.savefig("figure_1.png", dpi=600, bbox_inches="tight", pad_inches=0.04)
```

Before final delivery:

1. Check every axis label includes units where applicable.
2. Confirm color encodes a variable, not decoration.
3. Confirm individual observations or uncertainty are visible.
4. Confirm no random values were generated solely for visual appearance.
5. Confirm the caption states sample size, replicate definition, and test/model.
