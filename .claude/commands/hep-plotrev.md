---
description: Review and polish a HEP physics plot to publication quality
argument-hint: <work_dir> [--context "physics context"]
allowed-tools: [Read, Bash, Glob, Grep]
---

# HEP Plot Review

Review a physics plot through the automated feedback loop:
Haiku spec check → 3 Sonnet reviews → executor fix → Haiku verification with diff.

## Arguments

$ARGUMENTS

## Instructions

The user wants to review a plot. Parse the arguments:
- First argument: path to work directory containing `make_plot.py` and `plot.png`
- Optional `--context "..."`: physics context for the reviewers

If no arguments provided, ask the user for the work directory path.

### Steps

1. Verify the work directory exists and contains `plot.png` and `make_plot.py`:
   ```bash
   ls <work_dir>/plot.png <work_dir>/make_plot.py
   ```

2. Show the user the current plot before starting:
   - Read the plot image so the user can see it

3. Run the review loop:
   ```bash
   cd /home/anovak/work/plot-reviewer && python -c "
   import json
   from feedback_loop import review_plot
   result = review_plot(
       work_dir='<work_dir>',
       task_context=<context_or_None>,
   )
   print(json.dumps({
       'passed': result['passed'],
       'physics_ok': result['physics_ok'],
       'analysis_issues': result['analysis_issues'],
       'iterations': result['iterations'],
       'cost': result['cost'],
   }, indent=2))
   "
   ```

4. Show the user the final plot (read the image)

5. Report results:
   - Did it pass? How many iterations? Cost?
   - If there are analysis issues, highlight them prominently — these are physics bugs
   - Show the before/after comparison

6. If the user wants to see details, read `<work_dir>/loop_log.md`
