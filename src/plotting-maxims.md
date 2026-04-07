# Plotting Standards (non-negotiable)

## Visual (checkable from rendered image)
<!-- Basics -->
- Data = black errorbar - always. (Pseudodata as well)
- For Data/MC comparisons - MC = filled/stacked.
- Figure must render square in aspect. No compound plots unless plotting a ratio/pull/residual.
- All Figures must have experiement label. Out-of-frame above is mandatory. Must say "Open Data" or "Open Simulation", not bare experiment name if using Open Data. 
- For fits or data/MC: show residual/pull panel below (3:1 height ratio, no gap, y-tick on ratio might need manual tweaking to avoid text overlap).
- Pull panel: draw horizontal reference lines at 0, ±1, ±2 sigmas.
<!-- Legend -->
- Legend must not overlap data. "upper right" is preferred.
    - Prefer to scale axis range, have more columns, adjust legend fontsize down to "xx-small", shorten labels before you move legend. 
    - Legend title at most one tier larger than legend entries ie "small" vs "x-small". Same is ok if needed. 
- No titles on the plot. Context in legend title or caption. Space above plot is for experiment labelling. 
- Legend title: only if genuinely informative. Don't add vague context.
- Fit results in legend: compact notation. `y = 0.029x − 0.001`, use latex formatting when appropriate.
    - Uncertainties can be ommitted if not they cannot be visualized in a compact way. 
    - Yes `r"$y = 5.3^{+1.2}_{-0.9}$"` 
    - NO `r"$y = 0.000005\pm0.00000001$"`
    - Fit results that need more space and have meaningful uncerainties can be shown in a separate text box added to where there is space on the plot. When plotting residuals - the residual panel legend is ideal for this for functional fits.
    - Signal strenght results for template fits also preferrable in separate text box. 
<!-- Labels -->
- Axis labels must be publication-quality with units in brackets where applicable. Use `"(A.U.)"` suffix for normalized y labels.
- No code variable names in labels — human-readable only.
- On 2 panel plots main axis y-label is top aligned. Bottom panel y-label is center aligned. 
- Pull panel y-label: `r"$\frac{Data-MC}{\sigma_{Data}}$"`.
<!-- Other -->
- If χ²/ndf > 10 or fit visibly fails: annotate "FIT FAILED" with distinct styling.
- Error bars on derived quantities (ratios, efficiencies, normalized dists, computed values) must look plausible — not nonsensically large (sign of sqrt(N) on non-counts).

## Code (verifiable in source only)

- Use mplhep throughout. `mh.style.use("CMS")` as base.
- Experiment label via `mh.label.exp_label(...)`. NEVER manual `ax.text` for experiment labels.
- `figsize=(10, 10)`. No exceptions.
- No `ax.set_title()`.
- No absolute `fontsize=` values. Use relative: `'small'`, `'x-small'`, `'xx-small'`.
- Legend `fontsize="small"` or `"x-small"` if many entries. Opportunistically use ncols. 
- Derived quantities MUST have explicit `yerr=` passed to histplot/errorbar and must be physically meaningfully calculated.
- Ratio/pull panel: `gridspec_kw={"height_ratios": [3, 1]}`, `sharex=True`, `hspace=0`.
- Avoid `ax.text` unless 100% sure it's needed. Strongly prefer placing text with `mh.add_text("text", loc)` where loc is in 
`"upper left", "upper right", "lower left", "bottom left", "lower right", "bottom right", "over left", "over right"`.
- Use latex strings as much as possible unless truly plain text. No weird unicode for math/greek leters.
- Use `mpl_magic(ax)` before saving figure as a pen-ultimate step to try to automatically scale y-axis to fit legend/text boxes and avoid overlap. Mind this changes the y-lims. 
- Save PDF + PNG: `bbox_inches="tight"`, `dpi=200`, `transparent=False`.
- Close figure: `plt.close(fig)` after saving.
