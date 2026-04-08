# Post-Fix Verification (Haiku)

The executor just applied fixes based on reviewer feedback. Your job is to verify
TWO things:

## 1. Were the requested changes implemented?

Here is the feedback that was given:

{feedback}

For each item, check the plot image and script. Report DONE or MISSED.

## 2. Did the fix introduce any NEW problems?

Compare what you see against common sense:
- Any new text overlap, clipped labels, garbled rendering?
- Did the fix break something that was previously fine (e.g. legend disappeared,
  axis labels gone, plot doesn't render)?
- Any obvious visual artifacts?
- Pull/residual panel: are data point error bars still visible? If errorbars
  disappeared or shrank to invisible after the fix, that is BROKEN.

Only flag NEW problems that weren't there before. Do NOT re-audit the entire spec.

If all feedback items are DONE and no new problems: say exactly PASS
Otherwise list what's MISSED or BROKEN.
