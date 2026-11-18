# Publication-Grade Scientific Visualization Guidelines

Publication-grade visualization is a scientific argument encoded visually. It
must preserve the structure of the data, make uncertainty honest, and remain
readable at final journal size. A polished low-information chart is still a bad
scientific figure.

## Expert Review Standard

Before writing plotting code, answer these questions:

1. What is the scientific claim?
2. What are the experimental units and replicates?
3. Which variables are measured, derived, modeled, or categorical?
4. What uncertainty is available from observed data or model output?
5. What structure could be hidden by a simple aggregate?
6. What would a skeptical reviewer ask to see?

The figure should make those answers visible or caption-ready.

## Figure Family Selection

Choose figure families from the data and claim, not from habit.

| Scientific situation | Strong encodings | Reviewer-grade additions |
| --- | --- | --- |
| Dose-response or inhibition | Log-dose scatter, fitted/model curve, replicate intervals | IC50/EC50 guide, observed range note, residual panel if fit is central |
| Group comparison | Raincloud, violin/box/strip, dot-interval, ECDF | Raw points, n per group, effect size and CI |
| Time course | Individual trajectories, mean curve with interval band, event markers | Aligned baselines, missingness annotation |
| Multivariate table | Scatter/density, correlation heatmap, parallel coordinates, PCA/UMAP | Loadings, explained variance, marginal distributions |
| Matrix/expression/correlation | Heatmap, clustered heatmap, annotated matrix | Colorbar units, missingness, clustering method |
| Model diagnostics | Residuals, calibration curve, prediction interval, Bland-Altman | Error distribution, held-out/test split note |
| Spatial/image data | Image panels with overlays, masks, scale bars | Quantitative companion panel, intensity scale |
| Network data | Node-link plus adjacency/matrix view | Layout method, edge threshold, centrality definition |
| Pure categorical counts | Lollipop, dot plot, co-occurrence heatmap, mosaic | Ranked labels, denominators, confidence if sampled |

Summary rectangles are not an expert default. They hide distribution, sample
size, outliers, and uncertainty provenance.

## Data Fidelity

Hard rules:

- Do not fabricate observations, jitter, residuals, background surfaces, or
  confidence bands for visual drama.
- Do not smooth sparse data into false precision.
- Use log scales only when scientifically meaningful and label them explicitly.
- If axis limits truncate data, mark the truncation and justify it.
- Use the same scale for comparable panels unless the difference is explicitly
  part of the message.
- Preserve missingness when it is scientifically meaningful.

## Uncertainty And Statistics

Every uncertainty mark must have provenance:

- SD: variation among observed samples.
- SEM: uncertainty in the estimated mean, not population spread.
- CI: interval construction must be known; use 95% unless justified.
- Bootstrap: resample observed units only and document unit/resample count.
- Model interval: name the model and interval type.

For group comparisons, prefer effect size plus confidence interval over
asterisk-only significance. If significance markers are used, define the test,
correction, sidedness, and n in the caption.

## Composition

Good scientific panels are dense but controlled:

- Put the primary evidence panel first.
- Use secondary panels for distribution, correlation, residuals, uncertainty,
  or derived summaries.
- Align axes across comparable panels.
- Keep panel labels consistent with the target journal.
- Avoid titles inside manuscript panels unless the panel would be ambiguous
  without them.
- Use direct annotations sparingly for scientific landmarks such as threshold,
  IC50, event time, or clinically meaningful cutoffs.

## Typography

At final print size:

- Axis labels: 7-9 pt.
- Tick labels: 6-8 pt.
- Legends: 6-8 pt.
- Panel labels: 8-12 pt, bold.
- Use sentence case: "Time (hours)", not "TIME (HOURS)".
- Include units in parentheses.
- Use Arial, Helvetica, DejaVu Sans, or the journal-required font.
- Embed/edit fonts in vector output.

## Color

Color must encode information, not decoration.

- Categorical: Okabe-Ito, Wong, or Paul Tol palettes.
- Sequential continuous: viridis, cividis, magma, inferno, plasma.
- Diverging with meaningful center: RdBu_r, PuOr, or BrBG.
- Never use jet, rainbow, hsv, or red-green as the only distinction.
- Add redundant encoding for categories: marker, line dash, label, facet, or
  texture.
- Ensure grayscale interpretability when figures may be printed.

## Export

Use vector output for plots and line art:

- PDF or SVG for editable/scalable plot layers.
- EPS only when a journal specifically requires it.
- PNG or TIFF at 300-600 DPI for raster previews or image-heavy panels.
- 600-1200 DPI for line art when raster export is mandatory.
- Never JPEG for scientific plots.

Save an audit manifest for final figures when possible. It should include:

- File formats and DPI.
- Figure size in inches and millimeters.
- Plot family.
- Whether synthetic visual data were generated.
- Whether raw observations and uncertainty are visible.
- Journal target, if known.

## Failure Modes To Reject

Reject or rewrite figures with these problems:

1. They answer a rich-data question with a single aggregate per group.
2. They hide raw observations for small or moderate n.
3. They show uncertainty but do not define what it is.
4. They use a colormap known to create false boundaries.
5. They use color as the only category distinction.
6. They use decorative 3D, shadows, gradients, or heavy backgrounds.
7. They present interpolated or smoothed curves without method disclosure.
8. They truncate axes in a way that changes the apparent effect.
9. They make text unreadable at final size.
10. They export only a low-resolution raster.

## Final Reviewer Checklist

- [ ] The figure family matches the scientific claim.
- [ ] Raw observations, distribution, or matrix structure are visible when
      scientifically relevant.
- [ ] Uncertainty is computed from observed data or documented model output.
- [ ] Sample size and replicate unit are caption-ready.
- [ ] Axes include units, transforms, and meaningful ranges.
- [ ] Color is accessible and redundant.
- [ ] Panels are aligned, labeled, and logically ordered.
- [ ] The figure remains readable at journal dimensions.
- [ ] Vector and high-resolution raster exports are available.
- [ ] No synthetic data were generated for visual appearance.

See `journal_requirements.md` for publisher dimensions and export rules.
