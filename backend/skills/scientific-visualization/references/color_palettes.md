# Scientific Color Systems

Color in a scientific figure is a measurement channel. Treat it as part of the
analysis, not styling. The palette must be accessible, consistent across panels,
and appropriate for the variable type.

Use `assets/color_palettes.py` for executable palette selection and validation.

## Categorical Palettes

Use categorical palettes for experimental groups, cohorts, classes, treatments,
or discrete model labels.

### Okabe-Ito

```python
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
```

### Wong

```python
WONG = [
    "#000000", "#E69F00", "#56B4E9", "#009E73",
    "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
]
```

### Paul Tol

```python
TOL_BRIGHT = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]
TOL_MUTED = ["#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255", "#AA4499"]
TOL_HIGH_CONTRAST = ["#004488", "#DDAA33", "#BB5566"]
```

Use no more than 7-9 categories in one panel unless the figure also uses
facets, direct labels, marker shapes, or line dashes.

## Continuous Colormaps

Use continuous colormaps only for continuous variables.

Sequential:

- `viridis`
- `cividis`
- `magma`
- `inferno`
- `plasma`
- `Blues`, `Greens`, `Purples` when a single-hue map is preferred

Diverging:

- `RdBu_r`
- `PuOr`
- `BrBG`
- `coolwarm` when contrast is acceptable

Use diverging maps only when the data have a meaningful center such as zero,
baseline, no-change, or chance performance.

## Forbidden Or Dangerous Choices

Reject these for publication scientific figures:

- `jet`
- `rainbow`
- `gist_rainbow`
- `nipy_spectral`
- `hsv`
- red-green as the only category distinction
- red-green diverging maps such as `RdYlGn` for accessibility-critical figures

These maps create artificial visual boundaries, uneven perceptual steps, and
color-vision failures. They make a figure look complex while reducing
scientific truthfulness.

## Redundant Encoding

Color alone is not enough. Use at least one redundant channel when comparing
groups:

- Marker shape for scatter.
- Line dash for trajectories.
- Direct labels for curves or clusters.
- Facets for many groups.
- Texture or outlines for filled regions.
- Annotation for key reference conditions.

Executable pattern:

```python
from color_palettes import redundant_encoding_plan

plan = redundant_encoding_plan(["Control", "Low", "High"], plotly=False)
for group, style in plan.items():
    ax.plot(
        data[group]["x"],
        data[group]["y"],
        color=style["color"],
        marker=style["marker"],
        linestyle=style["dash"],
        label=group,
    )
```

## Plotly

```python
from color_palettes import get_plotly_palette, redundant_encoding_plan

colors = get_plotly_palette("okabe_ito", n=df["condition"].nunique())
style = redundant_encoding_plan(df["condition"].unique(), plotly=True)
```

## Matplotlib

```python
from color_palettes import apply_palette, validate_colormap

apply_palette("okabe_ito")
validate_colormap("viridis", role="sequential")
validate_colormap("RdBu_r", role="diverging")
```

## Seaborn

```python
import seaborn as sns
from color_palettes import get_palette

sns.set_palette(get_palette("tol_muted"))
sns.heatmap(corr, cmap="RdBu_r", center=0)
```

## Domain Notes

Genomics:

- Use sequential maps for expression magnitude.
- Use diverging maps for log fold-change around zero.
- Use accessible DNA base colors from `DNA_BASES_ACCESSIBLE`.

Microscopy:

- Preserve channel identity when required by the field, but avoid red/green
  overlays as the only distinction.
- Pair image panels with quantitative summaries when making a claim.
- Include scale bars and intensity/colorbar information.

Model diagnostics:

- Use one continuous colormap for calibrated scalar scores.
- Use categorical palettes only for true classes or splits.
- Keep train/validation/test color semantics consistent across the manuscript.

## Audit Checklist

- [ ] Variable type matches palette type.
- [ ] Continuous maps have labeled colorbars and units.
- [ ] Diverging maps have a real center.
- [ ] Categorical colors are reused consistently across panels.
- [ ] The figure survives grayscale or has redundant encodings.
- [ ] No forbidden colormap is used.
