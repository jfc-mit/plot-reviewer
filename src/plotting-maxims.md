# Plotting Standards (non-negotiable)

## Visual (checkable from rendered image)
<!-- Figure -->
- Figure must render square in aspect. No compound plots unless plotting a ratio/pull/residual.
- All Figures must have experiement label. Out-of-frame above is mandatory. Must say "Open Data" or "Open Simulation", not bare experiment name if using Open Data. 
- For fits or data/MC: show residual/pull panel below (3:1 height ratio, no gap, y-tick on ratio might need manual tweaking to avoid text overlap).
- Absolutely no text overalp. Not on the main plot, not in the labels/ticks, not with the experiment labels.
- No titles on the plot. Context in legend title or caption. Space above plot is for experiment labelling. 
<!-- Plotting -->
- Data = black errorbar - always. (Pseudodata as well). 
    - Labelled "Data" when real data. "Pseudodata" if randomized in any way (redrawn from poisson dist eg.). "Asimov Data" when constructed as sum of MC". 
    - Use small suitable `capsize` when plotting with `ax.errorbar` and `mh.histplot(..., histtype='errorbar')`
    - When plotting data histograms, use xerr that span the binwdith, eg in mh it's `mh.histplot(..., xerr=True)`
- For Data/MC comparisons - MC = filled/stacked. Use "CMS Color scheme" colors preferrentially
- For shape comparisons, say between different data-taking periods. Or distributions matched to different truth classes, "step" (default mh.histplot) style is better. 
- Error bars on derived quantities (ratios, efficiencies, normalized dists, computed values) must look plausible — not nonsensically large (sign of sqrt(N) on non-counts).
- It's crucial to get the uncertainty evaluation to be correct both on main panel, but particularly when plotting any pulls/ratios. Any plotting guidelines should never mislead/obfuscate about what the values that are actually shown are. 
<!-- "Pull" panel -->
- Pull/Ratio/Residuals panel:
    - Draw horizontal reference **lines** (not shaded bands) at exactly 0, ±1, ±2 sigmas, NO extras. Use solid gray for 0, dashed gray for ±1, dotted gray for ±2. Absolutely do NOT use colored fill bands (axhspan, etc...). 
    - Annotate ref lines with subtle gray `r"$1\sigma$"` etc labels on the RIGHT side of the pull panel. Right side is standard — don't move them. The singular exception to overlap rules. Set `zorder` to always show these behind everything else. 
<!-- Legend -->
- Legend must not overlap data. "upper right" is preferred.
    - Prefer to scale axis range, have more columns, adjust legend fontsize down to "xx-small", shorten labels before you move legend. 
    - Legend title: only if genuinely informative. Don't add vague context. Good for "Postfit" or "Prefit" or "Muon CR" or "DL Channel" type labels.
    - Legend title at most one tier larger than legend entries ie "small" vs "x-small". Same is ok if needed. 
<!-- Extra info texts -->
- Uncertainties can be ommitted if not they cannot be visualized in a compact way. 
    - Yes `r"$y = 5.3^{+1.2}_{-0.9}$"` 
    - NO `r"$y = 0.000005\pm0.00000001$"` (info that is too detailed can always be in the caption)
- Fit results in legend: compact notation. `y = 0.029x − 0.001`, use latex formatting when appropriate.
- Fit results that need more space and have meaningful uncerainties can be shown in a separate text box added to where there is space on the plot. If the main panel is busy and the fit results can be reasonably fitted into the residual panel (eg as one line either aligned to top/bottom of the panel) without interfering with the data or only a minor scaling - this can be used instead.
- One value per line unless severaly constrained by avail whitespace — vertical lists are more readable than horizontal ones. Only compress onto fewer lines if genuinely tight on space.
- Signal strenght results for template fits also preferrable in separate text box. 
- No bounding boxes/background for text annotations. It's not needed if you are careful about placement.
<!-- Placement -->
- Optimize whitespace use. LOOK at the plot and put annotations where the data ISN'T. Plotting a narrow peak? The tails are empty — put fit params there. One-sided distribution falling left to right? Top-left is empty — use it. Do NOT default to bottom-right or cram things into the pull panel when the main panel has obvious empty regions. This is one of the most common mistakes — actually think about the data shape before placing text.
<!-- Labels -->
- Axis labels must be publication-quality with units in brackets where applicable. Use `"(A.U.)"` suffix for normalized y labels.
- No code variable names in labels — human-readable only. Established scientific terms are acceptable `r"$m_{ll}$"` or `r"$m_{jj}$"` or `r"$m_{b\bar{b}}$"`. Applies to legend entries too.
- Don't be redundant in labels. If the axis says `r"$m_{jj}$"` you don't also need "Dijet invariant mass" — the symbol IS the name. Pick one: either the descriptive text with units, or the symbol with units. Not both. Prefer symbol-ish labels during processing. Prefer "full names" for flagship/result plots. 
- On 2 panel plots main axis y-label is top aligned (default in style sheet). Bottom panel y-label is center aligned. Labels should have normal spacing from the axis — not crammed against the ticks. 
- Pull panel y-label should be:
    -  For a data/MC "template fit" plot `r"$\frac{Data-MC}{\sigma_{Data}}$"` or `r"$\frac{Data-Bkg.}{\sigma_{Data}}$"` if showing signals separately.
    - For Data/Fit plot `r"$\frac{Data-Model}{\sigma}$"` (or "Fit" instead of "MOdel as appropriate) where \sigma is total uncertainty. 
<!-- Other -->
- If chi2/ndf > 10 or fit visibly fails: annotate "FIT FAILED" with distinct styling. chi2/ndf > 1 still needs flagging and investigation. However, the failure more si slightly diferent. 
<!-- Aesthetics -->
- Maximize visual appeal. These are journal figures — they should look clean and modern.
    - Uncertainty bands: light shaded fill (low alpha, color matching the fit line), NOT hatched. Hatching looks dated.
    - Keep the plot uncluttered. Every element should earn its place. If something adds visual noise without information, remove it.
    - When in doubt, simpler is better.
- When deciding where to place things, think of the expected look of the plot. Plotting a distribution that's peaking in the centre? Single column legend on the top right and any extra info on the top left might be the best way to use the space. Plotting a smoothly falling distribution of many classes? Two column legend on the right and maybe there's still space below it to `add_text` cleanly without having to scale up.

## Code (verifiable in source only)

- Use mplhep throughout. `mh.style.use("CMS")` as base.
    - Experiment label via `mh.label.exp_label(...)`. NEVER manual `ax.text` for experiment labels.
    - STRONGLY PREFER using `mh.histplot()` and `mh.hist2dplot()` for plotting pre-binned histograms 
    - Create all histograms with the `hist` package and `.Weight()` storage type NO EXCEPTIONS. 
        - use syntax like `h = hist.new.Reg(...).<OtherAxType>(...).Weight()`. 
    - Pseudodata generation: generate actual events from the distribution (e.g. `np.random.choice`, `scipy.stats.rv_continuous.rvs`, rejection sampling), then `h.fill(events)`. Do NOT manually stuff bin counts into a Weight histogram — that bypasses proper statistical handling.
    - When plotting anything but raw counts or MC compute your own yerr values and pass them to `histplot(..., yerr=...)`.
    - Pulls/residuals/ratios are derived per-bin quantities, NOT histograms. Plot them with `ax.errorbar()` (or `ax.plot` if no uncertainties on the pull itself). Do not create a `hist` object for pulls.
    - Use `mh.comp.get_comparison(h1, h2, comparison=<comp>)` with eg `comparison='pull'` to get the `[values, lower_uncertainties, upper_uncertainties]` for a particular comparison type to plot "manually" in any complicated/complex setting. 
        - Use `mh.comp.data_model()` or `mh.comp.hists()` as appropriate for quick plots. 
- `figsize=(10, 10)`. No exceptions.
-    Ratio/pull panel: `gridspec_kw={"height_ratios": [3, 1]}`, `sharex=True`, `hspace=0`.
- No `ax.set_title()`.
- No absolute `fontsize=` values. Use relative: `'small'`, `'x-small'`, `'xx-small'`, etc...
- Legend `fontsize="small"` or `"x-small"` if many entries. Opportunistically use ncols. 
- Derived quantities MUST have explicit `yerr=` passed to histplot/errorbar and must be physically meaningfully calculated.
- Pull panel y-label centering: matplotlib quirk — use `ha='center', y=0.5` to actually center the rotated label. Also limit minor ticks on the pull y-axis (`ax_pull.yaxis.set_minor_locator(AutoMinorLocator(2))` or similar) — too many minor ticks look cluttered on a small panel.
    - Do not manually position axis labels. No `set_label_coords`, no `labelpad=`, no `va=` on `set_ylabel`/`set_xlabel`.
- Avoid `ax.text` unless 100% sure it's needed. Strongly prefer placing text with `mh.add_text("text", loc)` where loc is in 
`"upper left", "upper right", "lower left", "bottom left", "lower right", "bottom right", "over left", "over right"`. You can use `mh.append_text` to append additional text with different formatting to the above object if needed. Look up syntax if you need to.
- NEVER use `bbox=` on text annotations. No background boxes, no facecolor, no edgecolor on text. Place text carefully so it doesn't need a box.
- Use latex strings as much as possible unless truly plain text. No weird unicode for math/greek leters.
- Use `mpl_magic(ax)` judiciously. It auto-scales the y-axis to fit legend/text boxes. If the best solution is just to scale up the y-axis — that's fine, use it. But if it creates >30% headroom above the data, you're better off repositioning the legend/text instead (smaller font, more columns, move to emptier region of the plot). Don't blindly call it — check the result makes sense.
- Save PDF + PNG: `bbox_inches="tight"`, `dpi=200`, `transparent=False`.
- Close figure: `plt.close(fig)` after saving.
